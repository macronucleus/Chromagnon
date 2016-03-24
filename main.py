#!/usr/bin/env priithon

### main.py #####################################################################
# This is the main GUI window for alignment software
# 
# Load image file, make calibration file and then apply calibration to image file
##################################################################################


import sys, os

import wx, threading#, exceptions
from PriCommon import guiFuncs as G, imgfileIO, commonfuncs as C
from PriCommon.ndviewer import main as aui
from Priithon.all import U, N, Mrc
import aligner, listbox, cutoutAlign, alignfuncs as af, threadSafe, chromeditor
#import stopit

#----------- Global constants
C.CONFPATH = 'Chromagnon.conf'

LISTSIZE_X=sum([val for key, val in listbox.__dict__.iteritems() if key.startswith('SIZE_COL')])
LISTSPACE=10
FRAMESIZE_X= LISTSIZE_X * 2 + LISTSPACE
#FRAMESIZE_X=1270
FRAMESIZE_Y=250

if sys.platform.startswith('win'):
    LIST_Y=140
elif sys.platform.startswith('darwin'):
    LIST_Y=155
else:
    LIST_Y=150

FILTER = '*.dv*'

#----------- Execute this function to start
def main(sysarg=None, title="Chromagnon"):
    """
    start up the GUI
    return the frame object
    """
    if sys.platform in ('linux2', 'win32'):
        aui.initglut()
    
    frame = wx.Frame(None, title=title, size=(FRAMESIZE_X, FRAMESIZE_Y))
    frame.panel = BatchPanel(frame)
    wx.Yield()
    frame.Show()
    wx.Yield()

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

    def __del__(self, evt=None):
        self.OnClose()
        
    def OnClose(self, evt=None):
        if self.aui:
            self.aui.Close()
        evt.Skip()

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

        label, self.maxShift = G.makeTxtBox(self, box, 'max shift allowed (um)', defValue=confdic.get('maxShift', af.MAX_SHIFT), tip='maximum possible shift of each channel', sizeX=50)

        self.forceZmag = G.makeCheck(self, box, "force to calculate Z mag", tip='z mag calculation is often omitted if the z stack does not contain sufficient information', defChecked=confdic.get('forceZmag', False))
        # ---- target ------
        refsize = self.refAddButton.GetSize()[0] + self.refClearButton.GetSize()[0] + self.forceZmag.GetSize()[0] + label.GetSize()[0] + self.maxShift.GetSize()[0]
        G.newSpaceH(box, LISTSIZE_X+LISTSPACE-refsize)

        self.tgtAddButton = G.makeButton(self, box, lambda ev:self.OnChooseImgFiles(ev,'target'), title='Target files', tip='', enable=True)
        
        self.tgtClearButton = G.makeButton(self, box, lambda ev:self.clearSelected(ev, 'tareget'), title='Clear selected', tip='', enable=False)

        self.cutoutCb = G.makeCheck(self, box, "crop margins", tip='', defChecked=confdic.get('cutout', True))

        ## --- list ----
        # \n
        box = G.newSpaceV(sizer)
        
        self.listRef = listbox.FileListCtrl(self, wx.NewId(),
                                 style=wx.LC_REPORT
                                 | wx.BORDER_NONE
                                 | wx.LC_SORT_ASCENDING,
    size=(LISTSIZE_X, LIST_Y)#300+200+100+30,LIST_Y)
                                 )
        #self.listRef.defPxlSiz = confdic.get('defPxlSiz', self.listRef.defPxlSiz)
        box.Add(self.listRef)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda ev:self.OnItemSelected(ev, 'reference'), self.listRef)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.listRef)
        self.listRef.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        
        G.newSpaceH(box, 10)

        self.listTgt = listbox.FileListCtrl(self, wx.NewId(),
                                 style=wx.LC_REPORT
                                 | wx.BORDER_NONE
                                 | wx.LC_SORT_ASCENDING,
        size=(LISTSIZE_X, LIST_Y)#300+200+100+30,LIST_Y)
                                 )
        #self.listTgt.defPxlSiz = confdic.get('defPxlSiz', self.listTgt.defPxlSiz)
        box.Add(self.listTgt)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda ev:self.OnItemSelected(ev, 'target'), self.listTgt)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.listTgt)
        self.listTgt.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)

        #------- execute ------

        # \n
        box = G.newSpaceV(sizer)
        
        #self.viewButton = G.makeButton(self, box, self.OnViewSelected, title='Preview selected', tip='', enable=False)

        self.goButton = G.makeToggleButton(self, box, self.OnGo, title='Run all', tip='', enable=False)

        self.localChoice = ['None', 'Projection', 'Section-wise']
        label, self.localListChoice = G.makeListChoice(self, box, 'Local align', self.localChoice, defValue=confdic.get('local', 'None'))


        #label, self.cthretxt = G.makeTxtBox(self, box, 'CC SNR threshold (0-0.3)', defValue=confdic.get('cthre', af.CTHRE), tip='threshold for cross-correlation quality', sizeX=50)
        #label, self.cthretxt = G.makeTxtBox(self, box, 'CC SNR threshold (0-0.3)', defValue=af.CTHRE, tip='threshold for cross-correlation quality', sizeX=50)
        #------ initial guess -------
        self.label = G.makeTxt(self, box, ' ')

        # \n
        box = G.newSpaceV(sizer)
        
        self.initguessButton = G.makeButton(self, box, self.OnChooseInitGuess, title='Initial guess', tip='', enable=True)
        label, self.initGuess = G.makeTxtBox(self, box, '', tip='Initial guess file name', sizeX=550)

        dropTarget = MyFileDropTarget(self.initGuess)
        self.initGuess.SetDropTarget(dropTarget)
        
        self.clearInitguessButton = G.makeButton(self, box, self.OnClearInitGuess, title='Clear', tip='', enable=True)
        # ----- finishing -----
        self.Layout()
        self.parent.Layout()

        self.checkGo()

    def OnItemSelected(self, evt=None, rt='reference'):
        """
        check selected items and enable buttons that works with selected items

        set self.refselected, self.tgtselected
        """
        self.refselected = [i for i in range(self.listRef.GetItemCount()) if self.listRef.IsSelected(i)]
        self.tgtselected = [i for i in range(self.listTgt.GetItemCount()) if self.listTgt.IsSelected(i)]

        #if self.refselected or self.tgtselected:
        #    self.viewButton.Enable(1)
        #elif not self.refselected and not self.tgtselected:
        #    self.viewButton.Enable(0)

        if self.refselected:
            self.refClearButton.Enable(1)
        else:
            self.refClearButton.Enable(0)
            
        if self.tgtselected:
            self.tgtClearButton.Enable(1)
        else:
            self.tgtClearButton.Enable(0)
            
        if evt:
            self.currentItem = (rt, evt.m_itemIndex) # for doubleclick

    def OnDoubleClick(self, evt=None):
        if self.currentItem[0] == 'reference':
            ll = self.listRef
        else:
            ll = self.listTgt
        fn = os.path.join(*ll.getFile(self.currentItem[1])[:2])
        self.makeExtraInfo(*self.currentItem[:2])
        self.view(fn)#viewSingle(fn)

    def makeExtraInfo(self, which='ref', index=0):
        """
        set self.einfo
        """
        if which.startswith('r'):
            ll = self.listRef
        else:
            ll = self.listTgt

        item = ll.getFile(index)
        einfo = {}
        einfo['nt'] = int(item[3])
        waves = [int(wave) for wave in item[2].split(',')]
        einfo['nw'] = len(waves)
        einfo['waves'] = waves
        einfo['seq'] = ll.seqs[index]
        einfo['pixsiz'] = ll.pxszs[index]

        self.einfo = einfo
        
    def OnChooseImgFiles(self, evt, listtype='ref'):
        """
        set reference files
        """
        confdic = C.readConfig()
        if listtype == 'ref':
            ll = self.listRef
            wildcard = confdic.get('lastwildcard', FILTER)
        else:
            ll = self.listTgt
            wildcard = confdic.get('lastwildcard', FILTER)

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
            C.saveConfig(lastwildcard=wildcard, lastpath=self.lastpath)

            self.checkGo()

    def OnChooseInitGuess(self, evt=None):
        """
        set reference files
        """
        wildcard = '*.chromagnon*'

        if os.name == 'posix':
            dlg = G.FileSelectorDialog(self, direc=self.lastpath, wildcard=wildcard, multiple=False)
        else:
            dlg = wx.FileDialog(self, 'Choose chromagnon files', defaultDir=self.lastpath, style=wx.FD_MULTIPLE, wildcard=wildcard)
            
        if dlg.ShowModal() == wx.ID_OK:
            fn = dlg.GetPath()
            an = aligner.Chromagnon(fn)
            if an.img.hdr.type == aligner.IDTYPE:
                self.initGuess.SetValue(fn)
                self.initGuess.SetForegroundColour(wx.BLACK)
            else:
                G.openMsg(parent=self, msg='The file is not a valid chromagnon file', title="Warning")
            an.close()

    def OnClearInitGuess(self, evt=None):
        """
        cealr initial guess
        """
        self.initGuess.SetValue('')

    def checkReferences(self, evt=None):
        """
        return indices of reference if they are chromagnon files.
        """
        boolean = [index for index in self.listRef.columnkeys if self.listRef.getFile(index)[1].endswith(aligner.PARM_EXT)]

        return boolean
        
            
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
            #stillselected = self.tgtselected
        else:
            inds = self.tgtselected
            ll = self.listTgt
            #stillselected = self.refselected

        [ll.clearRaw(i) for i in inds[::-1]]
        self.checkGo()
        self.OnItemSelected()

        #if stillselected:
        #    self.viewButton.Enable(1)
        #else:
        #    self.viewButton.Enable(0)

    def buttonsEnable(self, enable=0):
        """
        enable or disable buttons that should not be hit while running the program
        """
        buttons = [self.refAddButton, self.refClearButton, self.tgtAddButton, self.tgtClearButton, self.cutoutCb, self.initguessButton, self.clearInitguessButton]

        [button.Enable(enable) for button in buttons]

    def OnGo(self, ev=None):
        """
        run or cancel the alignment program

        The actual sequence of processes is written in threadSafe.ThreadWithExc.run()
        """
        if self.goButton.GetValue():
            if not self.listRef.columnkeys:
                return


            fns = [os.path.join(*self.listRef.getFile(index)[:2]) for index in self.listRef.columnkeys]
            targets = [os.path.join(*self.listTgt.getFile(index)[:2]) for index in self.listTgt.columnkeys]

            # tif support
            extrainfo = {'ref': {}, 'target': {}}
            for what in ['ref', 'target']:
                if what == 'ref':
                    ffs = fns
                    ll = self.listRef
                else:
                    ffs = targets
                    ll = self.listTgt
                for index, fn in enumerate(ffs):
                    if fn.endswith(tuple(imgfileIO.IMGEXTS_MULTITIFF)):
                        item = ll.getFile(index)
                        extrainfo[what][fn] = {}
                        extrainfo[what][fn]['nt'] = int(item[3])
                        waves = [int(wave) for wave in item[2].split(',')]
                        extrainfo[what][fn]['nw'] = len(waves)
                        extrainfo[what][fn]['waves'] = waves
                        extrainfo[what][fn]['seq'] = ll.seqs[index]#item[5]
                        extrainfo[what][fn]['pixsiz'] = ll.pxszs[index]

            # other parameters
            parms = [self.cutoutCb.GetValue(),
                     self.initGuess.GetValue(),
                     self.localListChoice.GetStringSelection(),
                     self.forceZmag.GetValue(),
                     float(self.maxShift.GetValue()),
                        #float(self.cthretxt.GetValue()),
                     [nt for nt in self.listRef.nts]] # copy

            C.saveConfig(cutout=parms[0], local=parms[2], forceZmag=parms[3], maxShift=parms[4])

            gui = threadSafe.GUImanager(self, __name__)
            
            self.th = threadSafe.ThreadWithExc(gui, self.localChoice, fns, targets, parms, extrainfo)
            self.th.start()

        else:
            tid = self.th._get_my_tid()
            #stopit.async_raise(tid, threadSafe.MyError)
            async_raise(tid, threadSafe.MyError)


    old='''
    def OnViewSelected(self, ev=None, calib=None, target=None):
        """
        preview selected items
        """
        rinds = [os.path.join(*self.listRef.getFile(i)[:2]) for i in self.refselected]
        tinds = [os.path.join(*self.listTgt.getFile(i)[:2]) for i in self.tgtselected]

        mids = max((len(rinds), len(tinds)))
        rinds += [None for i in range(mids - len(rinds))]
        tinds += [None for i in range(mids - len(tinds))]

        for target, calib in zip(tinds, rinds):
            self.viewSingle(target, calib)

    def viewSingle(self, target):#=None, calib=None):
        """
        view a single combination of target and calib
        """
        initGuess = self.initGuess.GetValue()

        if target:
            if calib and calib.endswith(aligner.PARM_EXT):
                self.view(target, calib)
            elif calib:
                self.view(calib)
                self.view(target)
            else:
                self.view(target)

        else:
            if calib and calib.endswith(aligner.PARM_EXT):
                arr = N.squeeze(Mrc.bindFile(calib))
                if arr.ndim <= 2:
                    try:
                        from matplotlib import pyplot as P
                        P.hold(0)
                        for a in arr:
                            P.plot(a)
                            P.hold(1)
                        P.hold(0)
                    except ImportError:
                        from Priithon import usefulP as P
                        #from Priithon.all import Y
                        #if hasattr(Y, 'ploty'):
                        for i, a in enumerate(arr):
                            P.ploty(a, hold=i)
                else:
                    self.view(calib)
                    
            elif initGuess:
                self.view(calib, initGuess)
            else:
                self.view(calib)'''

    def view(self, target):
        """
        view with viewer
        """
        # prepare viewer
        if not self.aui:
            self.aui = aui.MyFrame(parent=None)
            self.aui.Show()

        # draw
        if isinstance(target, basestring):
            an = aligner.Chromagnon(target)
            ext = os.path.splitext(target)[1][1:]
            exts = imgfileIO.IMGEXTS_MULTITIFF + ('dv', 'mrc')
            if ext == aligner.PARM_EXT:
                target_is_image = False
            elif ext in imgfileIO.IMGEXTS_MULTITIFF:
                target_is_image = True
                an.setExtrainfo(self.einfo)
                an.restoreDimFromExtra()
            elif ext in ('dv', 'mrc'):
                target_is_image = True
            else:
                if an.hdr.type == aligner.IDTYPE:
                    target_is_image = False
                else:
                    target_is_image = True
        else:
            an = target
            target_is_image = True

        if target_is_image:
            newpanel = aui.ImagePanel(self.aui, an)#target)

        else:
            an.close()
            newpanel = chromeditor.ChromagnonEditor(self.aui, target)

        if isinstance(target, basestring):
            name = os.path.basename(target)
        else:
            name = target.file
        if sys.platform in ('linux2', 'win32'):
            wx.CallAfter(self.aui.imEditWindows.AddPage, newpanel, name, select=True)
        else:
            self.aui.imEditWindows.AddPage(newpanel, name, select=True)
            

class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, parent):
        wx.FileDropTarget.__init__(self)
        self.txt = parent

    def OnDropFiles(self, x, y, filenames):
        self.txt.SetValue(filenames[-1])

# from stopit
def async_raise(target_tid, exception):
    """Raises an asynchronous exception in another thread.
    Read http://docs.python.org/c-api/init.html#PyThreadState_SetAsyncExc
    for further enlightenments.

    :param target_tid: target thread identifier
    :param exception: Exception class to be raised in that thread
    """
    import ctypes
    # Ensuring and releasing GIL are useless since we're not in C
    # gil_state = ctypes.pythonapi.PyGILState_Ensure()
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid),
                                                     ctypes.py_object(exception))
    # ctypes.pythonapi.PyGILState_Release(gil_state)
    if ret == 0:
        raise ValueError("Invalid thread ID {}".format(target_tid))
    elif ret > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

    
if __name__ == '__main__':
    from Priithon import PriApp
    PriApp._maybeExecMain()
    
