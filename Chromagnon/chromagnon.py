#!/usr/bin/env pythonw

### chromagnon.py #####################################################################
# This is the main GUI window for alignment software
# 
# Load image file, make calibration file and then apply calibration to image file
##################################################################################


import sys, os

#### javabridge for py2exe
# following workaround should be put before importing anything involved.
INIT = False
import imp
def main_is_frozen():
   return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze

def init_java_home():
    global INIT
    if not INIT:
        if sys.platform.startswith('win'):
            # py2exe emit warnings as error messages if it is not supressed.
            import warnings
            warnings.simplefilter('ignore')

        if main_is_frozen(): # py2exe
            cwd = os.path.dirname(os.path.abspath(sys.argv[0]))
            if sys.platform.startswith('win'):
                jdk = os.path.join(cwd, 'jdk')
            elif sys.platform.startswith('darwin'):
                jdk = os.path.join(os.path.dirname(cwd), 'Resources', 'jdk')
            #print 'jdk is', jdk
            if not os.getenv('JDK_HOME'):
                os.environ['JDK_HOME'] = jdk
            if not os.getenv('JAVA_HOME'):
                os.environ['JAVA_HOME'] = jdk
                
            INIT = True

init_java_home()

import wx, threading
try:
    from PriCommon import guiFuncs as G, bioformatsIO, commonfuncs as C, listbox
    from PriCommon.ndviewer import main as aui
    from Priithon.all import U, N, Mrc
except:
    from Chromagnon.PriCommon import guiFuncs as G, bioformatsIO, commonfuncs as C, listbox
    from Chromagnon.PriCommon.ndviewer import main as aui
    from Chromagnon.Priithon.all import U, N, Mrc
## for py2exe, here the relative import was impossible to run this script as __main__
from Chromagnon import aligner, cutoutAlign, alignfuncs as af, threads, chromeditor, chromformat, flatfielder, version

#----------- Global constants
C.CONFPATH = 'Chromagnon.conf'

LISTSIZE_X=sum([val for key, val in listbox.__dict__.iteritems() if key.startswith('SIZE_COL')])
LISTSPACE=10
FRAMESIZE_X= LISTSIZE_X * 2 + LISTSPACE
FRAMESIZE_Y=250

if sys.platform.startswith('win'):
    LIST_Y=140
elif sys.platform.startswith('darwin'):
    LIST_Y=155
else:
    LIST_Y=150

FILTER = '*.dv*'

LOCAL_CHOICE = ['None', 'Projection']

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
        _main(sysarg=sysarg, title=title)
    else:
        sys.app = wx.App()
        _main(sysarg=sysarg, title=title)
        sys.app.MainLoop()
        
    bioformatsIO.uninit_javabridge()

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

    def makePanel(self, tif=False):
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

        # ---- target ------

        refsize = self.refAddButton.GetSize()[0] + self.refClearButton.GetSize()[0] + parmSuffixLabel.GetSize()[0] + self.parm_suffix_txt.GetSize()[0] + maxShiftLabel.GetSize()[0] + self.maxShift.GetSize()[0]
        G.newSpaceH(box, LISTSIZE_X+LISTSPACE-refsize)

        self.tgtAddButton = G.makeButton(self, box, lambda ev:self.OnChooseImgFiles(ev,'target'), title='Target files', tip='', enable=True)
        
        self.tgtClearButton = G.makeButton(self, box, lambda ev:self.clearSelected(ev, 'tareget'), title='Clear selected', tip='', enable=False)

        self.cutoutCb = G.makeCheck(self, box, "crop margins", tip='', defChecked=confdic.get('cutout', True))

        label, self.img_suffix_txt = G.makeTxtBox(self, box, 'Suffix', defValue=confdic.get('img_suffix_txt', aligner.IMG_SUFFIX), tip='A suffix for the file name', sizeX=100)

        choices = [os.path.extsep + form for form in aligner.WRITABLE_FORMATS]
        label, self.outextch = G.makeListChoice(self, box, '', choices, defValue=confdic.get('format', aligner.WRITABLE_FORMATS[0]), tip='Choose image file formats, for reading with ImageJ, dv is recommended.')
        if not self.outextch.GetStringSelection():
            self.outextch.SetSelection(0)
        
        ## --- list ----
        # \n
        box = G.newSpaceV(sizer)
        
        self.listRef = listbox.FileListCtrl(self, wx.NewId(),
                                 style=wx.LC_REPORT
                                 | wx.BORDER_NONE
                                 | wx.LC_SORT_ASCENDING,
                                 size=(LISTSIZE_X, LIST_Y)
                                 )
        box.Add(self.listRef)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda ev:self.OnItemSelected(ev, 'reference'), self.listRef)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.listRef)
        self.listRef.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        
        G.newSpaceH(box, LISTSPACE)

        self.listTgt = listbox.FileListCtrl(self, wx.NewId(),
                                 style=wx.LC_REPORT
                                 | wx.BORDER_NONE
                                 | wx.LC_SORT_ASCENDING,
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
        
        self.zmaglabel, self.zmagch = G.makeListChoice(self, box, '  Z mag', aligner.ZMAG_CHOICE, defValue=confdic.get('Zmag', aligner.ZMAG_CHOICE[0]), tip='if "Auto" is chosen, then z mag calculation is done if the z stack contains more than 30 Z sections with a sufficient contrast')
        
        self.localChoice = LOCAL_CHOICE
        label, self.localListChoice = G.makeListChoice(self, box, 'Local align', self.localChoice, defValue=confdic.get('local', 'None'))

        #------ initial guess -------
        self.label = G.makeTxt(self, box, ' ')

        # \n
        box = G.newSpaceV(sizer)
        
        self.initguessButton = G.makeButton(self, box, self.OnChooseInitGuess, title='Initial guess', tip='', enable=True)

        _col_sizes=[(key, val) for key, val in listbox.__dict__.iteritems() if key.startswith('SIZE_COL')]
        _col_sizes.sort()

        LISTSIZE_X2 = sum([val for key, val in _col_sizes[:3]])
        LIST_Y2 = 30
        self.initGuess = listbox.BasicFileListCtrl(self, wx.NewId(),
                                 style=wx.LC_REPORT
                                 | wx.BORDER_NONE
                                 | wx.LC_SORT_ASCENDING
                                 | wx.LC_NO_HEADER,
                                 size=(LISTSIZE_X2, LIST_Y2),
                                 multiple=False
                                 )
        self.initGuess.setDefaultFileLoadFunc(chromformat.ChromagnonReader)
        
        initguess = confdic.get('initguess', '')
        if os.path.isfile(initguess):
            self.initGuess.addFile(initguess)
        
        box.Add(self.initGuess)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda ev:self.OnItemSelected(ev, 'initGuess'), self.initGuess)
        self.initGuess.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)

        
        self.clearInitguessButton = G.makeButton(self, box, self.OnClearInitGuess, title='Clear', tip='', enable=True)
        self.clearInitguessButton.Enable(0)

        #------ flat fielder --------

        self.flatButton = wx.Button(self, -1, 'Open Flat Fielder')
        self.flatButton.SetToolTipString('Open a graphical interphase to flat field images')
        flatsize = self.initguessButton.GetSize()[0] + LISTSIZE_X2 + self.clearInitguessButton.GetSize()[0] + self.flatButton.GetSize()[0]

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
                h = bioformatsIO.load(fn)
            except ValueError:
                dlg = wx.MessageDialog(self, '%s is not a valid image file!' % ff, 'Error reading image file', wx.OK | wx.ICON_EXCLAMATION)
                if dlg.ShowModal() == wx.ID_OK:
                    return
                
            if h.nseries > 1:
                dlg = wx.MessageDialog(self, 'Multiple series data sets are not allowed, please make a file with a single image in a file', 'Error in image file', wx.OK | wx.ICON_EXCLAMATION)
                if dlg.ShowModal() == wx.ID_OK:
                    return
        return h

    def OnItemSelected(self, evt=None, rt='reference'):
        """
        check selected items and enable buttons that works with selected items

        set self.refselected, self.tgtselected
        """
        self.refselected = [i for i in range(self.listRef.GetItemCount()) if self.listRef.IsSelected(i)]
        self.tgtselected = [i for i in range(self.listTgt.GetItemCount()) if self.listTgt.IsSelected(i)]
        self.initselected = [i for i in range(self.initGuess.GetItemCount()) if self.initGuess.IsSelected(i)]

        if self.refselected:
            self.refClearButton.Enable(1)
        else:
            self.refClearButton.Enable(0)
            
        if self.tgtselected:
            self.tgtClearButton.Enable(1)
        else:
            self.tgtClearButton.Enable(0)

        if self.initselected:
            self.clearInitguessButton.Enable(1)
        else:
            self.clearInitguessButton.Enable(0)
            
        if evt:
            self.currentItem = [rt, evt.m_itemIndex] # for doubleclick

    def OnDoubleClick(self, evt=None):
        # on windows
        if not hasattr(self, 'currentItem'):
            self.currentItem = [None, evt.m_itemIndex]
            
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
            dlg = wx.FileDialog(self, 'Choose %s files' % listtype, defaultDir=self.lastpath, style=wx.FD_MULTIPLE)#, wildcard=wildcard)
            
        if dlg.ShowModal() == wx.ID_OK:
            fns = dlg.GetPaths()

            if not fns:
                return
            if os.name == 'posix':
                wildcard = dlg.fnPat
            if isinstance(fns, basestring):
                fns = [fns]

            ll.addFiles(fns)
            
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
        buttons = [self.refAddButton, self.refClearButton, self.tgtAddButton, self.tgtClearButton, self.cutoutCb, self.initguessButton, self.clearInitguessButton]

        [button.Enable(enable) for button in buttons]

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
            if self.initGuess.columnkeys:
                initguess = os.path.join(*self.initGuess.getFile(0)[:2])
            else:
                initguess = ''

            form = self.outextch.GetStringSelection()
            if not form:
                G.openMsg(parent=self, msg='Please select the output file format next to the Suffix text box', title="The format type is missing")
                self.goButton.SetValue(0)
                return
                
            parms = [self.cutoutCb.GetValue(),
                     initguess,
                     self.localListChoice.GetStringSelection(),
                     self.maxShift.GetValue(),
                     self.zmagch.GetStringSelection(),
                    self.parm_suffix_txt.GetValue(),
                        self.img_suffix_txt.GetValue(),
                     [nt for nt in self.listRef.nts], # copy
                     form] 

            # check the user-inputs
            try:
                parms[3] = float(parms[3])
            except ValueError:
                G.openMsg(parent=self, msg='The default value (%.2f um) will be used' % af.MAX_SHIFT, title="The value for max shift allowed is missing")
                parms[3] = af.MAX_SHIFT
                self.maxShift.SetValue(str(parms[3]))
                        
            if not parms[6]:
                G.openMsg(parent=self, msg='The default suffix will be used', title="The file suffix is missing")
                parms[6] = alginer.IMG_SUFFIX
                self.img_suffix_txt.SetValue(parms[6])

            # save current settings
            C.saveConfig(cutout=parms[0], local=parms[2], maxShift=parms[3], Zmag=parms[4], parm_suffix_txt=parms[5], img_suffix_txt=parms[6], format=parms[8], initguess=initguess)

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


        if isinstance(target, basestring) and target.endswith('chromagnon'):
            newpanel = chromeditor.ChromagnonEditor(self.aui, target)
        else:
            newpanel = aui.ImagePanel(self.aui, target)

        if isinstance(target, basestring):
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
if __name__ == '__main__':
    ## windows support for py2exe
    import multiprocessing
    multiprocessing.freeze_support()
    
    if len(sys.argv) == 1:
        main()
        old="""
        if wx.GetApp():
            main()
        else:
            sys.app = wx.App()
            main()
            sys.app.MainLoop()"""
        #from Priithon import PriApp
        #PriApp._maybeExecMain()

    else:
        import argparse, glob

        description = r"""
           Chromagnon is an adaptive channel alignment program for fluorescnece microscope images.
           Feed one reference file each time.
           If no image file is supplied, a GUI will open to feed multiple files"""
        
        p = argparse.ArgumentParser(description=description)
        p.add_argument('targets', nargs='*',
                     help='target images files (required)')
        p.add_argument('--reference', '-R', required=True,
                     help='a reference image or chromagnon file (required)')
        p.add_argument('--local', '-l', default=LOCAL_CHOICE[0], choices=LOCAL_CHOICE,
                     help='choose from %s (default=%s)' % (LOCAL_CHOICE, LOCAL_CHOICE[0]))
        p.add_argument('--initguess', '-I', default=None,
                     help='a chromagnon file name for initial guess (default=None)')
        p.add_argument('--maxShift', '-s', default=af.MAX_SHIFT, type=float,
                     help='maximum um possibily misaligned in your system (default=%.2f um)' % af.MAX_SHIFT)
        p.add_argument('--zmag', '-z', default=aligner.ZMAG_CHOICE[0], choices=aligner.ZMAG_CHOICE,
                     help='choose from %s (default=%s)' % (aligner.ZMAG_CHOICE, aligner.ZMAG_CHOICE[0]))
        p.add_argument('--parm_suffix', '-P', default='',
                     help='suffix for the chromagnon files (default=None)')
        p.add_argument('--img_suffix', '-S', default=aligner.IMG_SUFFIX,
                     help='suffix for the target files (default=%s)' % aligner.IMG_SUFFIX)
        options = p.parse_args()

        ref = glob.glob(os.path.expandvars(os.path.expanduser(options.reference)))
        
        fns = []
        for fn in options.targets:
            fns += glob.glob(os.path.expandvars(os.path.expanduser(fn)))
        nts = []
        for fn in fns:
            h = bioformatsIO.load(fn)
            nts.append(h.nt)
            h.close()

        parms = [True, # crop mergins
                options.initguess,
                options.local,
                options.maxShift,
                options.zmag,
                options.parm_suffix,
                options.img_suffix,
                nts]

        th = threads.ThreadWithExc(None, LOCAL_CHOICE, ref, fns, parms)
        th.start()
        bioformatsIO.uninit_javabridge()
