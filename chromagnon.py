#!/usr/bin/env pythonw

### chromagnon.py #####################################################################
# This is the main GUI window for alignment software
# 
# Load image file, make calibration file and then apply calibration to image file
##################################################################################

#  prepare for __main__
if __name__ == '__main__':
    ## windows support for py2exe
    import multiprocessing
    multiprocessing.freeze_support()

    import warnings
    warnings.simplefilter('ignore')
    
# ------------- import basic modules
import sys, os
import six
import numpy as N

try:
    from common import commonfuncs as C
    import imgio
except (ValueError, ImportError):
    from Chromagnon.common import commonfuncs as C
    from Chromagnon import imgio

## for packaging, here the relative import was impossible to run this script as __main__
try:
    if sys.version_info.major == 2:
        import aligner, cutoutAlign, alignfuncs as af, threads, chromformat, version
    elif sys.version_info.major >= 3:
        from .Chromagnon import aligner, cutoutAlign, alignfuncs as af, threads, chromformat, version
except ImportError: # run as __main__
    from Chromagnon import aligner, cutoutAlign, alignfuncs as af, threads, chromformat, version

#----------- Global constants
C.CONFPATH = 'Chromagnon.conf'
FILTER = '*'
LOCAL_CHOICE = ['None', 'Projection']#, 'Section-wise']

# ---------- GUI specific modules and constants
try:
    import wx
    try:
        from common import guiFuncs as G, listbox
        from ndviewer import main as aui
    except (ValueError, ImportError):
        from Chromagnon.common import guiFuncs as G, listbox
        from Chromagnon.ndviewer import main as aui
        
    try:
        if sys.version_info.major == 2:
            import chromeditor, flatfielder, extrapanel
        elif sys.version_info.major >= 3:
            from .Chromagnon import chromeditor, flatfielder, extrapanel
    except ImportError: # run as __main__
        from Chromagnon import chromeditor, flatfielder, extrapanel

    # GUI constants
    LISTSIZE_X=sum([val for key, val in listbox.__dict__.items() if key.startswith('SIZE_COL')])
    LISTSPACE=10
    FRAMESIZE_X= LISTSIZE_X * 2 + LISTSPACE
    FRAMESIZE_Y=220

    if sys.platform.startswith('win'):
        LIST_Y=140
        FRAMESIZE_Y += 10
    elif sys.platform.startswith('darwin'):
        LIST_Y=155
    else:
        LIST_Y=150
        
except ImportError:
    if __name__ != '__main__' or len(sys.argv) > 1: # commandline use
        # a dummy class for wx
        class wx(object):
            def __init__(self):
                pass
            class Panel(object):
                def __init__(self):
                    pass
    else:
        raise
    
#----------- Execute this function to start
def _main(sysarg=None, title="Chromagnon v%s" % version.version):
    """
    start up the GUI
    return the frame object
    """
    aui.initglut()
    
    frame = wx.Frame(None, title=title, size=(FRAMESIZE_X, FRAMESIZE_Y))
    frame.panel = BatchPanel(frame)
    wx.Yield()
    frame.Show()
    wx.Yield()

    return frame

def main(sysarg=None, title="Chromagnon v%s" % version.version):
    
    if wx.GetApp():
        frame = _main(sysarg=sysarg, title=title)
    else:
        sys.app = wx.App()
        frame = _main(sysarg=sysarg, title=title)
        sys.app.MainLoop()
        
        imgio.uninit_javabridge()

    return frame

#------------ GUI -------------------
class BatchPanel(wx.Panel):
    def __init__(self, frame):
        """
        This panel is the main panel to do batch alignment
        """
        wx.Panel.__init__(self, frame)
        self.parent = frame

        # constants
        self.aui = None

        # fill in the contents
        self.makePanel()

    def makePanel(self):
        # config
        confdic = C.readConfig()
        self.lastpath = confdic.get('lastpath', '')
        self.extra_parms = {}

        # draw / arrange
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # ---- reference ------
        # \n
        box = G.newSpaceV(sizer)
        self.refAddButton = G.makeButton(self, box, lambda ev:self.OnChooseImgFiles(ev,'ref'), title='Reference files', tip='', enable=True)

        self.refClearButton = G.makeButton(self, box, lambda ev:self.clearSelected(ev, 'ref'), title='Clear selected', tip='', enable=False)

        self.parmSuffixLabel, self.parm_suffix_txt = G.makeTxtBox(self, box, 'Suffix ', defValue=confdic.get('parm_suffix_txt', ''), tip='A suffix for the file extention for the chromagnon file name', sizeX=100)

        self.extraButton = G.makeButton(self, box, self.OnExtraParamButton, title='Extra parameters')
        
        # ---- target ------

        refsize = self.refAddButton.GetSize()[0] + self.refClearButton.GetSize()[0] + self.parmSuffixLabel.GetSize()[0] + self.parm_suffix_txt.GetSize()[0] + self.extraButton.GetSize()[0]
        G.newSpaceH(box, LISTSIZE_X+LISTSPACE-refsize)

        self.tgtAddButton = G.makeButton(self, box, lambda ev:self.OnChooseImgFiles(ev,'target'), title='Target files', tip='', enable=True)
        
        self.tgtClearButton = G.makeButton(self, box, lambda ev:self.clearSelected(ev, 'tareget'), title='Clear selected', tip='', enable=False)

        self.cutoutCb = G.makeCheck(self, box, "crop margins", tip='', defChecked=bool(confdic.get('cutout', True)))

        self.img_suffix_label, self.img_suffix_txt = G.makeTxtBox(self, box, 'Suffix ', defValue=confdic.get('img_suffix_txt', aligner.IMG_SUFFIX), tip='A suffix for the file name', sizeX=100)

        self.outext_choices = [os.path.extsep + form for form in aligner.WRITABLE_FORMATS]
        label, self.outextch = G.makeListChoice(self, box, '', self.outext_choices, defValue=confdic.get('format', aligner.WRITABLE_FORMATS[0]), tip='tif: ImageJ format, dv: DeltaVision format, ome.tif: OME-tif format (slow)', targetFunc=self.OnOutFormatChosen)
        if not self.outextch.GetStringSelection():
            self.outextch.SetSelection(0)
        
        ## --- list ----
        # \n
        box = G.newSpaceV(sizer)
        
        self.listRef = listbox.FileListCtrl(self, wx.NewId(),
                                 style=wx.LC_REPORT
                                 | wx.BORDER_NONE,
                                 size=(LISTSIZE_X, LIST_Y)
                                 )
        box.Add(self.listRef)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda ev:self.OnItemSelected(ev, 'reference'), self.listRef)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.listRef)
        self.listRef.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        
        G.newSpaceH(box, LISTSPACE)

        self.listTgt = listbox.FileListCtrl(self, wx.NewId(),
                                 style=wx.LC_REPORT
                                 | wx.BORDER_NONE,
        size=(LISTSIZE_X, LIST_Y)
                                 )
        box.Add(self.listTgt)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda ev:self.OnItemSelected(ev, 'target'), self.listTgt)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.listTgt)
        self.listTgt.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)

        self.listRef.setDefaultFileLoadFunc(self._load_func)
        self.listTgt.setDefaultFileLoadFunc(self._load_func)
        #------- execute ------

        # \n
        box = G.newSpaceV(sizer)
        
        self.goButton = G.makeToggleButton(self, box, self.OnGo, title='Run all', tip='', enable=False)

        if sys.platform.startswith('win'):
            ft = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        elif sys.platform.startswith('linux'):
            ft = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        else:
            ft = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        self.goButton.SetFont(ft)
        self.listRef.setOnDrop(self.goButton.Enable, 1)
        self.listTgt.setOnDrop(self.goButton.Enable, 1)
        
        self.averageCb = G.makeCheck(self, box, "average references  ", tip='Multiple reference images are maximum intensity projected to make a single high SNR image for shift calculation.', defChecked=bool(confdic.get('average', False)))

        self.localChoice = LOCAL_CHOICE
        self.local_label, self.localListChoice = G.makeListChoice(self, box, 'Local align ', self.localChoice, defValue=confdic.get('local', 'None'), targetFunc=self.OnLocalListChose)

        self.min_pxls_label, self.min_pxls_choice = G.makeListChoice(self, box, 'minimum window size', af.MIN_PXLS_YXS, defValue=confdic.get('min_pxls_yx', af.MIN_PXLS_YXS[1]), tip='Minimum number of pixel to divide as elements of local alignment')

        self.OnLocalListChose()

        self.progress = wx.Gauge(self, -1, 100, size=(100,-1))
        box.Add(self.progress)
        
        self.label = G.makeTxt(self, box, ' ', style=wx.ALIGN_LEFT)

        _col_sizes=[(key, val) for key, val in listbox.__dict__.items() if key.startswith('SIZE_COL')]
        _col_sizes.sort()

        LISTSIZE_X2 = sum([val for key, val in _col_sizes[:3]])
        LIST_Y2 = 30
        
        #------ flat fielder --------

        self.flatButton = wx.Button(self, -1, 'Open Flat Fielder')
        self.flatButton.SetToolTip(wx.ToolTip('Open a graphical interphase to flat field images'))

        flatsize = self.goButton.GetSize()[0] + self.averageCb.GetSize()[0] + self.local_label.GetSize()[0] + self.localListChoice.GetSize()[0] + self.min_pxls_label.GetSize()[0] + self.min_pxls_choice.GetSize()[0] + self.progress.GetSize()[0] + self.flatButton.GetSize()[0] + 5

        G.newSpaceH(box, FRAMESIZE_X-flatsize)

        box.Add(self.flatButton)
        frame = self.GetTopLevelParent()
        frame.Bind(wx.EVT_BUTTON, self.onFlatFielder, self.flatButton)
        
        # ----- finishing -----
        self.Layout()
        self.parent.Layout()

        self.checkGo()

    def _load_func(self, fn):
        if chromformat.is_chromagnon(fn):
            h = chromformat.ChromagnonReader(fn)
        else:
            try:
                h = imgio.Reader(fn)
            except ValueError as e:
                return listbox.imgio_dialog(e, self)

            if aligner.hasSameWave(h):
                dlg = wx.MessageDialog(self, 'The image contains multiple channels with the same wavelength. Please use a unique wavelength for each channel', 'Error in channel wavelengths', wx.OK | wx.ICON_EXCLAMATION)
                if dlg.ShowModal() == wx.ID_OK:
                    return
                
            if 0:#h.nseries > 1:
                try:
                    name = h.metadata['Image'][0]['Name']
                    dlg = wx.MessageDialog(self, 'The file contains %i series, but only the first image (%s) is used by Chromagnon' % (h.nseries, name), 'Warning for image series', wx.OK | wx.ICON_EXCLAMATION)
                    dlg.ShowModal()
                except:
                    raise
                    dlg = wx.MessageDialog(self, 'Multiple series data sets are not allowed, please make a file with a single image in a file', 'Error in image file', wx.OK | wx.ICON_EXCLAMATION)
                    if dlg.ShowModal() == wx.ID_OK:
                        return

        self.lastpath = os.path.dirname(fn)
        C.saveConfig(lastpath=self.lastpath)
        return h

    def OnItemSelected(self, evt=None, rt='reference'):
        """
        check selected items and enable buttons that works with selected items

        set self.refselected, self.tgtselected
        """
        self.refselected = [i for i in range(self.listRef.GetItemCount()) if self.listRef.IsSelected(i)]
        self.tgtselected = [i for i in range(self.listTgt.GetItemCount()) if self.listTgt.IsSelected(i)]

        if self.refselected:
            self.refClearButton.Enable(1)
        else:
            self.refClearButton.Enable(0)
            
        if self.tgtselected:
            self.tgtClearButton.Enable(1)
        else:
            self.tgtClearButton.Enable(0)

        if evt:
            self.currentItem = [rt, evt.Index]

    def OnDoubleClick(self, evt=None):
        # on windows
        if not hasattr(self, 'currentItem'):
            self.currentItem = [None, evt.Index]
            
        if self.currentItem[0] == 'reference':
            ll = self.listRef
        elif self.currentItem[0] == 'target':
            ll = self.listTgt
        elif self.currentItem[0] == 'initGuess':
            ll = self.initGuess
        fn = os.path.join(*ll.getFile(self.currentItem[1])[:2])
        self.view(fn)

        
    def OnChooseImgFiles(self, evt, listtype='ref'):
        """
        set reference files
        """
        confdic = C.readConfig()
        if listtype == 'ref':
            ll = self.listRef
            wildcard = confdic.get('lastwildcardref', FILTER)
        else:
            ll = self.listTgt
            wildcard = confdic.get('lastwildcardtgt', FILTER)

        if os.name == 'posix':
            dlg = G.FileSelectorDialog(self, self.lastpath, wildcard=wildcard)
        else:
            dlg = wx.FileDialog(self, 'Choose %s files' % listtype, defaultDir=self.lastpath, style=wx.FD_MULTIPLE)
            
        if dlg.ShowModal() == wx.ID_OK:
            fns = dlg.GetPaths()

            if not fns:
                return
            if os.name == 'posix':
                wildcard = dlg.fnPat
            if isinstance(fns, six.string_types):
                fns = [fns]

            ll.addFiles(fns)
            if listtype != 'ref':
                if any([nw > 5 for nw in ll.nws]) and self.outextch.GetStringSelection() == (os.path.extsep + aligner.WRITABLE_FORMATS[1]):
                    self.outextch.SetStringSelection(os.path.extsep + aligner.WRITABLE_FORMATS[0])
                    G.openMsg(parent=self, msg='Since number of wavelength in some image file is more than 5,\nthe output file format was changed to tiff', title="Output file format change")
            
            self.lastpath = os.path.dirname(fns[0])
            if listtype == 'ref':
                C.saveConfig(lastwildcardref=wildcard, lastpath=self.lastpath)
            else:
                C.saveConfig(lastwildcardtgt=wildcard, lastpath=self.lastpath)

            self.checkGo()

    def OnChooseInitGuess(self, evt=None):
        """
        set reference files
        """
        wildcard = '*.chromagnon*'

        if os.name == 'posix':
            dlg = G.FileSelectorDialog(self, direc=self.lastpath, wildcard=wildcard, multiple=False)
        else:
            dlg = wx.FileDialog(self, 'Choose chromagnon files', defaultDir=self.lastpath, wildcard=wildcard)
            
        if dlg.ShowModal() == wx.ID_OK:
            fn = dlg.GetPath()
            if chromformat.is_chromagnon(fn, True):
                self._setInitGuess(fn)
            else:
                G.openMsg(parent=self, msg='The file is not a valid chromagnon file', title="Warning")

    def _setInitGuess(self, fn):
        self.initGuess.clearAll()
        self.initGuess.addFile(fn)
        self.clearInitguessButton.Enable(1)
        C.saveConfig(initguess=fn)

    def OnClearInitGuess(self, evt=None):
        """
        cealr initial guess
        """
        self.initGuess.clearAll()
        self.clearInitguessButton.Enable(0)

    def OnExtraParamButton(self, evt=None):
        confdic = C.readConfig()

        dlg = extrapanel.ExtraDialog(self, self.listRef, confdic, outdir=self.extra_parms.get('outdir'), refwave=str(self.extra_parms.get('refwave')))
        val = dlg.ShowModal()

        self.outdir = self.refwave = self.zacuur = None
        if val == wx.ID_OK:
            if not (dlg.outdir_cb.GetValue()):
                self.extra_parms['outdir'] = dlg.outdir
                C.saveConfig(outdir=dlg.outdir)
            if hasattr(dlg, 'refwave_cb') and not (dlg.refwave_cb.GetValue()):
                refwave = dlg.refwave_choice.GetStringSelection()
                try:
                    refwave = eval(refwave)
                except (TypeError, ValueError):
                    pass
                self.extra_parms['refwave'] = refwave

            if hasattr(dlg, 'tseriesListChoice'):
                self.extra_parms['tseries4wave'] = dlg.tseriesListChoice.GetStringSelection()
                
            self.extra_parms['zacuur'] = eval(dlg.accurListChoice.GetStringSelection())
            C.saveConfig(accur=self.extra_parms['zacuur'])

            self.extra_parms['max_shift'] = eval(dlg.maxshift_text.GetValue())
            C.saveConfig(max_shift=self.extra_parms['max_shift'])

            self.extra_parms['calibfn'] = dlg.calibfn

            self.extra_parms['dorot4time'] = dlg.dorot4time_cb.GetValue()
            #C.saveConfig(dorot4time=self.extra_parms['dorot4time'])

            self.extra_parms['doZ'] = dlg.doZ_cb.GetValue()
            #C.saveConfig(doZ=self.extra_parms['doZ'])

        dlg.Destroy()
        
    def checkGo(self, evt=None):
        """
        enable "Go" button according to the entry of the file list
        """
        if self.listRef.columnkeys:
            self.goButton.Enable(1)
        else:
            self.goButton.Enable(0)


    def clearSelected(self, evt=None, listtype='ref'):
        """
        clear selected item from the list
        """
        if listtype == 'ref':
            inds = self.refselected
            ll = self.listRef
        else:
            inds = self.tgtselected
            ll = self.listTgt

        [ll.clearRaw(i) for i in inds[::-1]]
        self.checkGo()
        self.OnItemSelected()

    def buttonsEnable(self, enable=0):
        """
        enable or disable buttons that should not be hit while running the program
        """
        buttons = [self.refAddButton, self.refClearButton, self.tgtAddButton, self.tgtClearButton, self.cutoutCb, self.parmSuffixLabel, self.parm_suffix_txt, self.extraButton, self.img_suffix_label, self.img_suffix_txt, self.outextch, self.averageCb, self.local_label, self.localListChoice, self.min_pxls_label, self.min_pxls_choice]

        [button.Enable(enable) for button in buttons]
        
        # fix for min_pxls_choice
        if enable:
            if not self.localListChoice.GetCurrentSelection():
                self.min_pxls_choice.Enable(0)

    def OnOutFormatChosen(self, evt=None):
        outext = self.outextch.GetStringSelection()
        if outext == 'ome.tif' and 'ome.tif' not in imgio.multitifIO.WRITABLE_FORMAT and not imgio.bioformatsIO.HAS_JDK:
            listbox.imgio_dialog('Writing the file format (%s) requres Java Development Kit (JDK)' % outext)
            confdic = C.readConfig()
            outext = confdic.get('format', aligner.WRITABLE_FORMATS[0])
            self.outextch.SetStringSelection(outext)
        
    def OnLocalListChose(self, evt=None):
        local = self.localListChoice.GetStringSelection()
        if local == self.localChoice[0]:
            self.min_pxls_label.Enable(0)
            self.min_pxls_choice.Enable(0)
        else:
            self.min_pxls_label.Enable(1)
            self.min_pxls_choice.Enable(1)

        
    def OnGo(self, ev=None):
        """
        run or cancel the alignment program

        The actual sequence of processes is written in threads.ThreadWithExc.run()
        """
        if self.goButton.GetValue():
            
            if not self.listRef.columnkeys:
                return

            fns = [os.path.join(*self.listRef.getFile(index)[:2]) for index in self.listRef.columnkeys]
            targets = [os.path.join(*self.listTgt.getFile(index)[:2]) for index in self.listTgt.columnkeys]

            # other parameters
            confdic = C.readConfig()

            form = self.outextch.GetStringSelection()
            if not form:
                self.quit('Please select the output file format next to the Suffix text box', title="The format type is missing")
                return

            # check wavelengths
            waves1 = [list(map(int, map(float, self.listRef.getFile(index)[2].split(',')))) for index in self.listRef.columnkeys]
            waves2 = [list(map(int, map(float, self.listTgt.getFile(index)[2].split(',')))) for index in self.listTgt.columnkeys]
            nts = all([t == 1 for t in self.listRef.nts])

            # combine wavelengths
            ref_is_temp = False
            if len(fns) > 1 and nts and all([len(waves) == 1 for waves in waves1]):
                print('combine refs')
                fns = af.combineWavelength(fns)
                self.listRef.clearAll()
                self.listRef.addFile(fns[0])
                waves1 = [list(map(int, self.listRef.getFile(index)[2].split(','))) for index in self.listRef.columnkeys]
                self.averageCb.SetValue(0)
                ref_is_temp = True
                

            fns_is_temp = False
            if len(targets) > 1 and nts and all([len(waves) == 1 for waves in waves2]):
                print('combine targets')
                targets = af.combineWavelength(targets)
                self.listTgt.clearAll()
                self.listTgt.addFile(fns[0])
                waves2 = [list(map(int, self.listTgt.getFile(index)[2].split(','))) for index in self.listTgt.columnkeys]
                fns_is_temp = True

            # check wavelength consistency
            ids = af.checkWaves(waves1, waves2)
            if ids is not None and nts:
                for i, listbox in zip(ids, (self.listRef, self.listTgt)):
                    listbox.SetItemTextColour(i, 'purple')
                    #listbox.SetBackGroundColour(i, 'gray')
                msg = 'Less than two Common wavelengths were found at least in %s and %s\n\nThe program will not run.' % (self.listRef.getFile(ids[0])[1], self.listTgt.getFile(ids[1])[1])
                self.quit(msg, title='Error in input files')
                return

            
            # averaging
            if self.averageCb.GetValue() and len(fns) > 1:
                if any([waves1[0] != ws1 for ws1 in waves1[1:]]):
                    self.quit('There are inconsistency in channel composition in the reference files', title="Reference files are not appropriate for averaging")
                    return
                
                self.label.SetLabel('averaging...')
                self.label.SetForegroundColour('red')
                wx.Yield()

                # log
                outdir = self.extra_parms.get('outdir')
                if outdir and not os.path.isdir(outdir):
                    raise ValueError('Output directory does not exist')
                elif outdir:
                    logh = open(os.path.join(outdir, 'Chromagnon.log'), 'a')
                else:
                    logh = open(os.path.join(os.path.dirname(fns[0]), 'Chromagnon.log'), 'a')
                try:
                    ave_fn = af.averageImage(fns, ext=form)
                except Exception as e:
                    self.quit(e.args[0], title="Reference files are not appropriate for averaging")
                    return         

                import time
                tstf = time.strftime('%Y %b %d %H:%M:%S', time.gmtime())
                logh.write('\n**Averaging at %s' % tstf)
                for fn in fns:
                    logh.write('\n    * %s' % fn)
                logh.close()
                    
                self.listRef.clearAll()
                self.listRef.addFile(ave_fn)
                fns = [ave_fn]
            elif self.averageCb.GetValue() and len(fns) == 1:
                self.averageCb.SetValue(0)


            accur = self.extra_parms.get('zacuur', confdic.get('accur', aligner.ACCUR_CHOICE[0]))
            if accur in aligner.ACCUR_CHOICE_DIC:
                accur = aligner.ACCUR_CHOICE_DIC[accur]
            
            # parameters
            parms = [self.cutoutCb.GetValue(),
                     self.extra_parms.get('outdir'),
                     self.localListChoice.GetStringSelection(),
                     self.extra_parms.get('refwave'),
                     int(accur),
                    self.parm_suffix_txt.GetValue(),
                        self.img_suffix_txt.GetValue(),
                     self.extra_parms.get('tseries4wave', 'time'),
                     form,
                     int(self.min_pxls_choice.GetStringSelection()),
                         self.extra_parms.get('max_shift', af.MAX_SHIFT),
                         self.extra_parms.get('calibfn', ''),
                         self.extra_parms.get('dorot4time', True),
                         self.extra_parms.get('doZ', True),
                         (ref_is_temp, fns_is_temp)
                         ] 
                        
            if not parms[6]:
                G.openMsg(parent=self, msg='The default suffix will be used', title="The file suffix is missing")
                parms[6] = aligner.IMG_SUFFIX
                self.img_suffix_txt.SetValue(parms[6])

            # save current settings
            C.saveConfig(cutout=parms[0], local=parms[2], accur=parms[4], parm_suffix_txt=parms[5], img_suffix_txt=parms[6], format=parms[8], min_pxls_yx=parms[9])
            
            # run program
            gui = threads.GUImanager(self, __name__)
            
            self.th = threads.ThreadWithExc(gui, self.localChoice, fns, targets, parms)
            self.th.start()

        else:
            tid = self.th._get_my_tid()
            threads.async_raise(tid, threads.MyError)

    def quit(self, message='', title='ERROR'):
        if message:
            G.openMsg(parent=self, msg=message, title=title)
        self.goButton.SetValue(0)
        self.label.SetLabel('')

    def view(self, target):
        """
        view with viewer
        """
        #if sys.platform in ('linux2'):
        #    return# 20210105 Ubuntu18.04LTS may not have the right videocard driver
        # prepare viewer
        if not self.aui:
            self.aui = aui.MyFrame(parent=self)
            self.aui.Show()


        if isinstance(target, six.string_types) and chromformat.is_chromagnon(target):
            newpanel = chromeditor.ChromagnonEditor(self.aui, target)
        else:
            # linux problem is here...-> viewer2.py OnPaint()
            newpanel = aui.ImagePanel(self.aui, target)

        if isinstance(target, six.string_types):
            name = os.path.basename(target)
        else:
            name = target.file


        if sys.platform in ('linux2', 'win32'):
            wx.CallAfter(self.aui.imEditWindows.addPage, newpanel, name, select=True)
        else:
            self.aui.imEditWindows.addPage(newpanel, name, select=True)

    def onFlatFielder(self, ev):
        self.flat = flatfielder.main(parent=self)
    

## command line behavior
def command_line():
    if len(sys.argv) == 1:
        main()
            

    else:
        import argparse, glob

        description = r"""
           Chromagnon is an adaptive channel alignment program for fluorescnece microscope images.
           If no image file is supplied, a GUI will open to feed multiple files.

           If you supply image file, the program starts as a console program.
           When you have mutiple reference files, do like the 'usage':
           """
        usage = '%(prog)s target1 target2 -R reference1 reference2 [options]'
        
        p = argparse.ArgumentParser(description=description, usage=usage)
        p.add_argument('--version', '-v', action='version', version='%s' % version.version)

        p.add_argument('targets', nargs='*',
                     help='target images files')
        p.add_argument('--reference', '-R', required=True, nargs='*',
                     help='reference image or chromagnon files (required)')
        p.add_argument('--local', '-l', action='store_true',#default=LOCAL_CHOICE[0], choices=LOCAL_CHOICE,
                     help='use this option to use local alignment (default=None)')#'choose from %s (default=%s)' % (LOCAL_CHOICE, LOCAL_CHOICE[0]))
        p.add_argument('--localMinWindow', '-w', default=af.MIN_PXLS_YXS[1], choices=af.MIN_PXLS_YXS,
                     help='choose from %s (default=%s)' % (af.MIN_PXLS_YXS, af.MIN_PXLS_YXS[1]))
        p.add_argument('--maxShift', '-s', default=af.MAX_SHIFT, type=float,
                     help='maximum shift in micrometers possibily misaligned in your system (default=%.2f um)' % af.MAX_SHIFT)
        p.add_argument('--not_crop_margins', '-c', action='store_true',
                     help='do not crop margins after alignment (default=False; do crop margins)')
        p.add_argument('--average_references', '-a', action='store_true',
                     help='average reference image (default=False)')
        p.add_argument('--parm_suffix', '-P', default='',
                     help='suffix for the chromagnon files (default=None)')
        p.add_argument('--img_suffix', '-S', default=aligner.IMG_SUFFIX,
                     help='suffix for the target files (default=%s)' % aligner.IMG_SUFFIX)
        p.add_argument('--img_format', '-E', default=aligner.WRITABLE_FORMATS[0], choices=aligner.WRITABLE_FORMATS,
                     help='file extension for the target files, choose from %s (default=%s)' % (aligner.WRITABLE_FORMATS, aligner.WRITABLE_FORMATS[0]))

        # extra parameters
        p.add_argument('--output_directory', '-O', default=None,
                     help='output directory different from the directory of the input files (same as the input)')
        p.add_argument('--reference_wavelength', '-r', default=None,
                     help='reference channel that is never moved (default=auto)')
        p.add_argument('--n3diter', '-z', default=aligner.MAXITER_3D, type=int,
                     help='number of iteration for 3D phase correlation (default=%i)' % aligner.MAXITER_3D)
        p.add_argument('--microscope_calib', '-M', default='',
                     help='local calibration file of your microscope (default=None)')
        p.add_argument('--donotRot4Time', '-t', action='store_true',
                     help='turn off rotation calculation for time series (default=False, i.e. calculate rotation)')
        p.add_argument('--donotZ', '-n', action='store_true',
                     help='turn off Z-axis calculation (default=False, i.e. calculate Z-axis)')
        
        options = p.parse_args(sys.argv[1:])

        # references
        refs = []
        for ref in options.reference:
            refs += glob.glob(os.path.expandvars(os.path.expanduser(ref)))

        nts = []
        nws = []
        for fn in refs:
            h = imgio.Reader(fn)
            nts.append(h.nt)
            nws.append(h.nw)
            h.close()

        ref_is_temp = False
        if len(refs) > 1 and all([nt == 1 for nt in nts]) and all([nw == 1 for nw in nws]):
            print('combine refs')
            refs = af.combineWavelength(refs)
            ref_is_temp = True

        # average refs
        if options.average_references:
            refs = [af.averageImage(refs, ext=options.img_format)]
            print('averaged image was saved as %s' % refs)
            
        # target fns
        fns = []
        for fn in options.targets:
            fns += glob.glob(os.path.expandvars(os.path.expanduser(fn)))
        nts = []
        nws = []
        for fn in fns:
            h = imgio.Reader(fn)
            nts.append(h.nt)
            nws.append(h.nw)
            h.close()

        fns_is_temp = False
        if len(fns) > 1 and all([nt == 1 for nt in nts]) and all([nw == 1 for nw in nws]):
            print('combine targets')
            fns = af.combineWavelength(fns)
            fns_is_temp = True



        if options.reference_wavelength:
            options.reference_wavelength = eval(options.reference_wavelength)

        if options.local:
            options.local = LOCAL_CHOICE[1]

        parms = [not options.not_crop_margins,
                options.output_directory,
                options.local,
                options.reference_wavelength,
                options.n3diter,
                options.parm_suffix,
                options.img_suffix,
                nts,
                options.img_format,
                int(options.localMinWindow),
                options.maxShift,
                options.microscope_calib,
                not(options.donotRot4Time), # dorot4time
                not(options.donotZ),# doZ
                      (ref_is_temp, fns_is_temp)] 

        th = threads.ThreadWithExc(None, LOCAL_CHOICE, refs, fns, parms)
        th.start()
        th.join()
        print('done')

        #if ref_is_temp:
            #print('removing file %s' % refs[0])
        #    os.remove(fns[0])
        
        #if fns_is_temp:
            #print('removing file %s' % fns[0])
        #    os.remove(fns[0])

        
if __name__ == '__main__':

    command_line()
    imgio.uninit_javabridge()
