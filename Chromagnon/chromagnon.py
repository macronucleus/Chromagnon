#!/usr/bin/env pythonw

### chromagnon.py #####################################################################
# This is the main GUI window for alignment software
# 
# Load image file, make calibration file and then apply calibration to image file
##################################################################################

import sys, os
import six

# ------------- import modules
import wx
try:
    from PriCommon import guiFuncs as G, commonfuncs as C, listbox
    from ndviewer import main as aui
    from Priithon.all import U, N, Mrc
    import imgio
except (ValueError, ImportError):
    from Chromagnon.PriCommon import guiFuncs as G, commonfuncs as C, listbox
    from Chromagnon.ndviewer import main as aui
    from Chromagnon.Priithon.all import U, N, Mrc
    from Chromagnon import imgio

## for packaging, here the relative import was impossible to run this script as __main__
try:
    if sys.version_info.major == 2:
        import aligner, cutoutAlign, alignfuncs as af, threads, chromeditor, chromformat, flatfielder, version
    elif sys.version_info.major >= 3:
        from .Chromagnon import aligner, cutoutAlign, alignfuncs as af, threads, chromeditor, chromformat, flatfielder, version
except ImportError: # run as __main__
    from Chromagnon import aligner, cutoutAlign, alignfuncs as af, threads, chromeditor, chromformat, flatfielder, version

#----------- Global constants
C.CONFPATH = 'Chromagnon.conf'

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

FILTER = '*.dv*'

LOCAL_CHOICE = ['None', 'Projection']#, 'Section-wise']

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

        # draw / arrange
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # ---- reference ------
        # \n
        box = G.newSpaceV(sizer)
        self.refAddButton = G.makeButton(self, box, lambda ev:self.OnChooseImgFiles(ev,'ref'), title='Reference files', tip='', enable=True)

        self.refClearButton = G.makeButton(self, box, lambda ev:self.clearSelected(ev, 'ref'), title='Clear selected', tip='', enable=False)

        maxShiftLabel, self.maxShift = G.makeTxtBox(self, box, 'max shift allowed (um)', defValue=confdic.get('maxShift', af.MAX_SHIFT), tip='maximum possible shift of each channel', sizeX=50)

        parmSuffixLabel, self.parm_suffix_txt = G.makeTxtBox(self, box, 'Suffix', defValue=confdic.get('parm_suffix_txt', ''), tip='A suffix for the file extention for the chromagnon file name', sizeX=100)

        #self.refwave = G.makeButton(self, box, lambda ev:self.clearSelected(ev, 'ref'), title='Ref channel', tip='', enable=True)
        # ---- target ------

        refsize = self.refAddButton.GetSize()[0] + self.refClearButton.GetSize()[0] + parmSuffixLabel.GetSize()[0] + self.parm_suffix_txt.GetSize()[0] + maxShiftLabel.GetSize()[0] + self.maxShift.GetSize()[0]
        G.newSpaceH(box, LISTSIZE_X+LISTSPACE-refsize)

        self.tgtAddButton = G.makeButton(self, box, lambda ev:self.OnChooseImgFiles(ev,'target'), title='Target files', tip='', enable=True)
        
        self.tgtClearButton = G.makeButton(self, box, lambda ev:self.clearSelected(ev, 'tareget'), title='Clear selected', tip='', enable=False)

        self.cutoutCb = G.makeCheck(self, box, "crop margins", tip='', defChecked=bool(confdic.get('cutout', True)))

        label, self.img_suffix_txt = G.makeTxtBox(self, box, 'Suffix', defValue=confdic.get('img_suffix_txt', aligner.IMG_SUFFIX), tip='A suffix for the file name', sizeX=100)

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
                                 #| wx.LC_SORT_ASCENDING,
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
                                # | wx.LC_SORT_ASCENDING,
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
        
        #self.zmaglabel, self.zmagch = G.makeListChoice(self, box, '  Z mag', aligner.ZMAG_CHOICE, defValue=confdic.get('Zmag', aligner.ZMAG_CHOICE[0]), tip='if "Auto" is chosen, then z mag calculation is done if the z stack contains more than 30 Z sections with a sufficient contrast')
        self.averageCb = G.makeCheck(self, box, "average references  ", tip='Multiple reference images are averaged to make a single high SNR image for shift calculation.', defChecked=bool(confdic.get('average', False)))
        
        self.localChoice = LOCAL_CHOICE
        label, self.localListChoice = G.makeListChoice(self, box, 'Local align', self.localChoice, defValue=confdic.get('local', 'None'), targetFunc=self.OnLocalListChose)

        self.min_pxls_label, self.min_pxls_choice = G.makeListChoice(self, box, 'min window size', af.MIN_PXLS_YXS, defValue=confdic.get('min_pxls_yx', af.MIN_PXLS_YXS[1]), tip='Minimum number of pixel to divide as elements of local alignment')

        self.OnLocalListChose()

        self.progress = wx.Gauge(self, -1, 100, size=(100,-1))
        box.Add(self.progress)
        
        self.label = G.makeTxt(self, box, ' ')

        _col_sizes=[(key, val) for key, val in listbox.__dict__.items() if key.startswith('SIZE_COL')]
        _col_sizes.sort()

        LISTSIZE_X2 = sum([val for key, val in _col_sizes[:3]])
        LIST_Y2 = 30
        
        #------ flat fielder --------

        self.flatButton = wx.Button(self, -1, 'Open Flat Fielder')
        self.flatButton.SetToolTip(wx.ToolTip('Open a graphical interphase to flat field images'))

        flatsize = self.goButton.GetSize()[0] + self.averageCb.GetSize()[0] + label.GetSize()[0] + self.localListChoice.GetSize()[0] + self.min_pxls_label.GetSize()[0] + self.min_pxls_choice.GetSize()[0] + self.progress.GetSize()[0] + self.flatButton.GetSize()[0] + 5 #self.zmaglabel.GetSize()[0] + self.zmagch.GetSize()[0] 

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
                
            if h.nseries > 1:
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
            if isinstance(fns, six.string_types):#str):
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
        buttons = [self.refAddButton, self.refClearButton, self.tgtAddButton, self.tgtClearButton, self.cutoutCb]

        [button.Enable(enable) for button in buttons]

    def OnOutFormatChosen(self, evt=None):
        outext = self.outextch.GetStringSelection()
        if outext == self.outext_choices[-1] and not imgio.bioformatsIO.HAS_JDK:
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
            initguess = ''

            form = self.outextch.GetStringSelection()
            if not form:
                G.openMsg(parent=self, msg='Please select the output file format next to the Suffix text box', title="The format type is missing")
                self.goButton.SetValue(0)
                self.label.SetLabel('')
                return

            # averaging
            #ref_all_image = all([not chromformat.is_chromagnon(fn) for fn in fns])
            if self.averageCb.GetValue() and len(fns) > 1:# and ref_all_image:
                try:
                    self.label.SetLabel('averaging...')
                    self.label.SetForegroundColour('red')
                    wx.Yield()
                    ave_fn = af.averageImage(fns, ext=form)
                except Exception as e:
                    G.openMsg(parent=self, msg=e.args[0], title="Reference files are not appropriate for averaging")
                    self.goButton.SetValue(0)
                    self.label.SetLabel('')
                    return         
                self.listRef.clearAll()
                self.listRef.addFile(ave_fn)
                fns = [ave_fn]
            elif self.averageCb.GetValue() and len(fns) == 1:
                self.averageCb.SetValue(0)
            
                
            parms = [self.cutoutCb.GetValue(),
                     initguess,
                     self.localListChoice.GetStringSelection(),
                     self.maxShift.GetValue(),
                     None, # empty after removing zmag slection
                     #self.zmagch.GetStringSelection(),
                    self.parm_suffix_txt.GetValue(),
                        self.img_suffix_txt.GetValue(),
                     [nt for nt in self.listRef.nts], # copy
                     form,
                     int(self.min_pxls_choice.GetStringSelection())] 

            # check the user-inputs
            try:
                parms[3] = float(parms[3])
            except ValueError:
                G.openMsg(parent=self, msg='The default value (%.2f um) will be used' % af.MAX_SHIFT, title="The value for max shift allowed is missing")
                parms[3] = af.MAX_SHIFT
                self.maxShift.SetValue(str(parms[3]))
                        
            if not parms[6]:
                G.openMsg(parent=self, msg='The default suffix will be used', title="The file suffix is missing")
                parms[6] = aligner.IMG_SUFFIX
                self.img_suffix_txt.SetValue(parms[6])

            # save current settings
            C.saveConfig(cutout=parms[0], local=parms[2], maxShift=parms[3], Zmag=parms[4], parm_suffix_txt=parms[5], img_suffix_txt=parms[6], format=parms[8], min_pxls_yx=parms[9])

            # run program
            gui = threads.GUImanager(self, __name__)
            
            self.th = threads.ThreadWithExc(gui, self.localChoice, fns, targets, parms)
            self.th.start()

        else:
            tid = self.th._get_my_tid()
            threads.async_raise(tid, threads.MyError)


    def view(self, target):
        """
        view with viewer
        """
        # prepare viewer
        if not self.aui:
            self.aui = aui.MyFrame(parent=self)
            self.aui.Show()


        if isinstance(target, six.string_types) and chromformat.is_chromagnon(target):
            newpanel = chromeditor.ChromagnonEditor(self.aui, target)
        else:
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
        p.add_argument('targets', nargs='*',
                     help='target images files')
        p.add_argument('--reference', '-R', required=True, nargs='*',
                     help='reference image or chromagnon files (required)')
        p.add_argument('--local', '-l', default=LOCAL_CHOICE[0], choices=LOCAL_CHOICE,
                     help='choose from %s (default=%s)' % (LOCAL_CHOICE, LOCAL_CHOICE[0]))
        p.add_argument('--localMinWindow', '-w', default=af.MIN_PXLS_YXS[1], choices=af.MIN_PXLS_YXS,
                     help='choose from %s (default=%s)' % (af.MIN_PXLS_YXS, af.MIN_PXLS_YXS[1]))
        p.add_argument('--maxShift', '-s', default=af.MAX_SHIFT, type=float,
                     help='maximum um possibily misaligned in your system (default=%.2f um)' % af.MAX_SHIFT)
        p.add_argument('--not_crop_mergins', '-c', action='store_false',
                     help='crop mergins after alignment (default=False; do crop mergins)')
        p.add_argument('--average_references', '-a', action='store_true',
                     help='average reference image (default=False)')
        p.add_argument('--parm_suffix', '-P', default='',
                     help='suffix for the chromagnon files (default=None)')
        p.add_argument('--img_suffix', '-S', default=aligner.IMG_SUFFIX,
                     help='suffix for the target files (default=%s)' % aligner.IMG_SUFFIX)
        p.add_argument('--img_format', '-E', default=aligner.WRITABLE_FORMATS[0], choices=aligner.WRITABLE_FORMATS,
                     help='file extension for the target files, choose from %s (default=%s)' % (aligner.WRITABLE_FORMATS, aligner.WRITABLE_FORMATS[0]))
        options = p.parse_args(sys.argv[1:])

        refs = []
        for ref in options.reference:
            refs += glob.glob(os.path.expandvars(os.path.expanduser(ref)))
        
        fns = []
        for fn in options.targets:
            fns += glob.glob(os.path.expandvars(os.path.expanduser(fn)))
        nts = []
        for fn in fns:
            h = imgio.Reader(fn)
            nts.append(h.nt)
            h.close()

        if options.average_references:
            refs = af.averageImage(refs, ext=options.img_format)
            print('averaged image was saved as %s' % refs)

        parms = [not options.not_crop_mergins,
                None,#options.initguess,
                options.local,
                options.maxShift,
                None,#options.zmag,
                options.parm_suffix,
                options.img_suffix,
                nts,
                options.img_format,
                int(options.localMinWindow)]

        th = threads.ThreadWithExc(None, LOCAL_CHOICE, refs, fns, parms)
        th.start()
        th.join()
        print('done')

        
if __name__ == '__main__':
    ## windows support for py2exe
    import multiprocessing
    multiprocessing.freeze_support()

    command_line()
    imgio.uninit_javabridge()
