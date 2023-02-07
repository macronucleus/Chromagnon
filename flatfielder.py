#!/usr/bin/env priithon

### main.py #####################################################################
# This is the main GUI window for alignment software
# 
# Load image file, make calibration file and then apply calibration to image file
##################################################################################

import sys, os
import six
import wx

try:
    from common import guiFuncs as G, commonfuncs as C, listbox
    import imgio
    from ndviewer import main as aui
    from PriCommon import flatConv
except ImportError:
    from Chromagnon.common import guiFuncs as G, commonfuncs as C, listbox
    from Chromagnon import imgio
    from Chromagnon.ndviewer import main as aui
    from Chromagnon.PriCommon import flatConv


try:
    from . import chromformat, aligner, chromeditor, threads
except ValueError:
    from Chromagnon import chromformat, aligner, chromeditor, threads
except ImportError:
    import chromformat, aligner, chromeditor, threads

#----------- Global constants

LISTSIZE_X=sum([val for key, val in listbox.__dict__.items() if key.startswith('SIZE_COL')])
FRAMESIZE_X= LISTSIZE_X
FRAMESIZE_Y=0#110

if sys.platform.startswith('win'):
    LIST_Y=140
elif sys.platform.startswith('darwin'):
    LIST_Y=155
else:
    LIST_Y=150
LIST_Y2 = 65

FRAMESIZE_Y += LIST_Y + LIST_Y2 + (30 * 3)

FILTER = '*.dv*'

#----------- Execute this function to start
def main(sysarg=None, title="Flat Fielder", parent=None):
    """
    start up the GUI
    return the frame object
    """
    if sys.platform in ('linux2', 'win32'):
        aui.initglut()

    # positioning just below the parent
    if parent:
        dw, dh = wx.DisplaySize()
        px, py = parent.GetTopLevelParent().GetPosition()
        sx, sy = parent.GetTopLevelParent().GetSize()
        x, y = (px, py+sy)
        if (y + FRAMESIZE_Y) > dh:
            y -= (y + FRAMESIZE_Y) - dh
        position = (x, y)
    else:
        position = wx.DefaultPosition

    # draw frame
    frame = wx.Frame(parent, title=title, pos=position, size=(FRAMESIZE_X, FRAMESIZE_Y))
    frame.panel = BatchPanel(frame, parent=parent)
    wx.Yield()
    frame.Show()
    wx.Yield()

    return frame

#------------ GUI -------------------
class BatchPanel(wx.Panel):
    def __init__(self, frame, parent=None):
        """
        This panel is the main panel to do batch alignment
        """
        wx.Panel.__init__(self, frame)
        self.parent = parent
        if parent:
            self.aui = self.parent.aui
        else:
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
        self.refAddButton = G.makeButton(self, box, self.OnChooseReferenceFile, title='Reference file', tip='', enable=True)

        self.refClearButton = G.makeButton(self, box, lambda ev:self.clearSelected(ev, 'ref'), title='Clear selected', tip='', enable=False)

        flatSuffixLabel, self.flat_suffix_txt = G.makeTxtBox(self, box, 'Suffix', defValue=confdic.get('flat_suffix_txt', ''), tip='A suffix before the file extention for the .flat file name', sizeX=100)
        
        #------- execute ------

        self.goButton = wx.ToggleButton(self, -1, 'Run all')

        if sys.platform.startswith('win'):
            ft = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        elif sys.platform.startswith('linux'):
            ft = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        else:
            ft = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD)
        self.goButton.SetFont(ft)
        #self.goButton.SetToolTipString('Open a graphical interphase to flat field images')
        gosize = self.refAddButton.GetSize()[0] + self.refClearButton.GetSize()[0] + self.goButton.GetSize()[0] + flatSuffixLabel.GetSize()[0] + self.flat_suffix_txt.GetSize()[0]

        G.newSpaceH(box, LISTSIZE_X-gosize)

        box.Add(self.goButton)
        frame = self.GetTopLevelParent()
        frame.Bind(wx.EVT_TOGGLEBUTTON, self.OnGo, self.goButton)

        
        ## --- list reference ----
        # \n
        box = G.newSpaceV(sizer)

        
        self.listRef = listbox.FileListCtrl(self, wx.NewId(),
                                 style=wx.LC_REPORT
                                 | wx.BORDER_NONE
                                 | wx.LC_SORT_ASCENDING,
                                 size=(LISTSIZE_X, LIST_Y2),
                                 multiple=False)
        box.Add(self.listRef)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda ev:self.OnItemSelected(ev, 'reference'), self.listRef)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.listRef)
        self.listRef.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)

        flatfn = confdic.get('flatfn', '_FLAT')
        if os.path.isfile(flatfn):
            self.listRef.addFile(flatfn)
        
        self.listRef.setDefaultFileLoadFunc(self._load_func)
        # ---- list target ------

        # \n
        box = G.newSpaceV(sizer)

        self.tgtAddButton = G.makeButton(self, box, self.OnChooseTargetFiles, title='Target files', tip='', enable=True)
        
        self.tgtClearButton = G.makeButton(self, box, lambda ev:self.clearSelected(ev, 'tareget'), title='Clear selected', tip='', enable=False)

        label, self.flatimg_suffix_txt = G.makeTxtBox(self, box, 'Suffix', defValue=confdic.get('flatimg_suffix_txt', flatConv.SUF), tip='A suffix for the output file name', sizeX=100)

        choices = [os.path.extsep + form for form in aligner.WRITABLE_FORMATS]
        label, self.outextch = G.makeListChoice(self, box, '', choices, defValue=confdic.get('flat_format', choices[0]), tip='Choose image file formats; for reading with ImageJ, dv is recommended.')
        
        # \n
        box = G.newSpaceV(sizer)
        
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

        self.listTgt.setDefaultFileLoadFunc(self._load_func)
        # ---- Drop befavior ----
        self.listRef.setOnDrop(self.checkGo, 1)#goButton.Enable, 1)
        self.listTgt.setOnDrop(self.checkGo, 1)#goButton.Enable, 1)

        
        # ---- Output ------

        # \n
        box = G.newSpaceV(sizer)
        self.label = G.makeTxt(self, box, ' ')


        # ----- finishing -----
        self.Layout()
        #self.parent.Layout()

        self.checkGo()

        
    def _load_func(self, fn):
        try:
            h = imgio.Reader(fn)#bioformatsIO.load(fn)
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

        if self.refselected:
            self.refClearButton.Enable(1)
        else:
            self.refClearButton.Enable(0)
            
        if self.tgtselected:
            self.tgtClearButton.Enable(1)
        else:
            self.tgtClearButton.Enable(0)
            
        if evt: # for doubleclick
            if wx.version().startswith('3'):
                self.currentItem = (rt, evt.m_itemIndex) 
            else:
                self.currentItem = (rt, evt.Index)

    def OnDoubleClick(self, evt=None):
        if self.currentItem[0] == 'reference':
            ll = self.listRef
        elif self.currentItem[0] == 'target':
            ll = self.listTgt
        fn = os.path.join(*ll.getFile(self.currentItem[1])[:2])

        self.view(fn)

    def OnChooseReferenceFile(self, evt):
        """
        set reference files
        """
        confdic = C.readConfig()
        wildcard = confdic.get('lastwildcard', FILTER)

        ll = self.listRef
        if os.name == 'posix':
            dlg = G.FileSelectorDialog(self, direc=self.lastpath, wildcard=wildcard, multiple=False)
        else:
            dlg = wx.FileDialog(self, 'Choose %sfiles'  % listtype, defaultDir=self.lastpath, wildcard=wildcard)
            
        if dlg.ShowModal() == wx.ID_OK:
            fn = dlg.GetPath()

            if not fn:
                return
            if os.name == 'posix':
                wildcard = dlg.fnPat

            ll.clearAll()
            ll.addFiles([fn])
            
            self.lastpath = os.path.dirname(fn)
            C.saveConfig(lastwildcard=wildcard, lastpath=self.lastpath)

            self.checkGo()
        
    def OnChooseTargetFiles(self, evt):
        """
        set reference files
        """
        confdic = C.readConfig()
        wildcard = confdic.get('lastwildcard', FILTER)

        ll = self.listTgt

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
            
            self.lastpath = os.path.dirname(fns[0])
            C.saveConfig(lastwildcard=wildcard, lastpath=self.lastpath)

            self.checkGo()

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

    def _setFlat(self, fns):
        #ids = range(len(fns))
        #ids.reverse()
        #[self.listRef.clearRaw(i) for i in ids]
        self.listRef.clearAll()
        for i, fn in enumerate(fns):
            self.listRef.addFile(fn)
        C.saveConfig(flatfn=fns[0])
            
    def checkGo(self, evt=None):
        """
        enable "Go" button according to the entry of the file list
        """
        if self.listRef.columnkeys:
            self.goButton.Enable(1)
        else:
            self.goButton.Enable(0)

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

            # run program
            parms = [self.flat_suffix_txt.GetValue(),
                     self.flatimg_suffix_txt.GetValue(),
                     self.outextch.GetStringSelection()]

            if not parms[1]:
                G.openMsg(parent=self, msg='The default suffix will be used', title="The file suffix is missing")
                parms[1] = flatConv.SUF
                self.flatimg_suffix_txt.SetValue(parms[1])

            gui = threads.GUImanager(self, __name__)
            
            self.th = threads.ThreadFlat(gui, None, fns, targets, parms)#, extrainfo)
            self.th.start()

            C.saveConfig(flat_suffix_txt=parms[0], flatimg_suffix_txt=parms[1], flatfn=fns[0], flat_format=parms[2])
            
        else:
            tid = self.th._get_my_tid()
            #stopit.async_raise(tid, threads.MyError)
            threads.async_raise(tid, threads.MyError)
            
    def buttonsEnable(self, enable=0):
        """
        enable or disable buttons that should not be hit while running the program
        """
        buttons = [self.refAddButton, self.refClearButton, self.tgtAddButton, self.tgtClearButton]

        [button.Enable(enable) for button in buttons]
        
    def view(self, target):
        """
        view with viewer
        """
        # prepare viewer
        if not self.aui:
            if self.parent and not self.parent.aui:
                self.aui = aui.MyFrame(parent=self.parent)
                self.parent.aui = self.aui
                self.aui.Show()
            elif not self.parent:
                self.aui = aui.MyFrame(parent=self)

                self.aui.Show()
            
            elif self.parent and self.parent.aui:
                self.aui = self.parent.aui

        # draw
        if isinstance(target, six.string_types):

            if chromformat.is_chromagnon(target):
                target_is_image = False
            else:
                target_is_image = True
                an = aligner.Chromagnon(target)
        else:
            an = target
            target_is_image = True

        if target_is_image:
            newpanel = aui.ImagePanel(self.aui, an.img)

        else:
            #an.close()
            newpanel = chromeditor.ChromagnonEditor(self.aui, target)

        if isinstance(target, six.string_types):
            name = os.path.basename(target)
        else:
            name = target.file
        if sys.platform in ('linux2', 'win32'):
            wx.CallAfter(self.aui.imEditWindows.addPage, newpanel, name, select=True)
        else:
            self.aui.imEditWindows.addPage(newpanel, name, select=True)


if __name__ == '__main__':
    from Priithon import PriApp
    PriApp._maybeExecMain()
    

