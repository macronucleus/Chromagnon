"""Priithon Y module: all functions to do with GUI
"""
from __future__ import print_function
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import six
import wx
import numpy as N
from . import PriConfig

_error =  _error0 = '' ## FIXME

# try:
#     _PriConfigPriithonDefaults
# except:
#     #from PriConfig import *
#     import PriConfig as _priConf
#     for k,v in _PriConfigPriithonDefaults.__dict__.iteritems():
#         if k[0] == '_' and k[1] != '_':
#             #__dict__[k] = v
#             exec "%s  = %s" % (k,repr(v))

def _bugXiGraphics(doWorkaround=1):
    from . import viewer
    viewer.bugXiGraphics = doWorkaround
    from . import viewer2
    viewer2.bugXiGraphics = doWorkaround
    from . import mmviewer
    mmviewer.bugXiGraphics = doWorkaround

def _fixGuiExceptHook():
    import sys
    def guiExcept(exctype, value, tb):
        from . import guiExceptionFrame
        # global err_msg
        _app_ = wx.GetApp()
        if _app_.IsMainLoopRunning() and \
                guiExceptionFrame.numberOfOpenExcWindows < PriConfig.maxOpenExceptionsWindows:#Safe to call MessagBox
            wx.CallAfter(guiExceptionFrame.MyFrame, exctype, value, tb)
            #global eee
            #eee = exctype, value, tb
        else:
            #Any time execution reaches here, that means the MainWindow closed because of an error
            sys.__excepthook__(exctype, value, tb)
    sys.excepthook = guiExcept

def _glutInit(argv=[]):
    global _glutInited
    try:
        _glutInited
    except:
        from OpenGL import GLUT
        GLUT.glutInit(argv)
        _glutInited=True

def _setAutosavePath():
    """
    This function should be called once at the startup of the Priithon shell.
    It generates a filename that will be used to do the autosaves
    # this fn (i.e. the time stamp) is generated ONCE at Priithon Shell startup
    """
    import os, time
    PriConfig._autoSaveSessionPath = time.strftime(PriConfig.autoSaveSessionFn)
    dd = PriConfig.autoSaveSessionDir
    if dd:
        # prepend dir part
        if dd[0] != '/':
            from . import useful as U
            dd = os.path.join(U.getHomeDir(), dd)
        
        PriConfig._autoSaveSessionPath = \
            os.path.join(dd, PriConfig._autoSaveSessionPath)

def test():
    """test for  viewer + histogram with colMap band"""
    #q = N.zeros((256,256), dtype=N.uint8)
    #q[:] = N.arange(256)
    import Priithon.fftfuncs as F
    view( 'F.rampArr()' )
def test2():
    """test for  viewer2 + histogram with colMap band"""
    q = N.zeros((3,256,256), dtype=N.uint8)
    q[0,:] = N.arange(256)
    q[1,:] = N.arange(256-1,-1,-1)
    q[2,:] = N.arange(256)[:,None]
    view2(q)



def editor(filename=None, retTextWindow=False):
    """
    if filename is None:
        open new <blank> file
    elif filename is a module:
        open the corresponding .py file if possible 
    if retTextWindow:
        return the wxStyledTextCtrl object
        this can be used to print into
    """
    import os.path
    if type(filename) == type(wx): # module
        if hasattr(filename, "__file__"):
            filename = filename.__file__
            if filename[-4:-1].lower() == '.py':
                filename = filename[:-1]

            if not os.path.isfile(filename):
                raise ValueError("cannot find .py file for %s"%filename)
        else:
            raise ValueError("no __file__ attribute found to help finding .py file for %s"%filename)

    from wx import py
    # ------ fix for python3 -------------
    class Document:
        """Document class."""

        def __init__(self, filename=None):
            """Create a Document instance."""
            self.filename = filename
            self.filepath = None
            self.filedir = None
            self.filebase = None
            self.fileext = None
            if self.filename:
                self.filepath = os.path.realpath(self.filename)
                self.filedir, self.filename = os.path.split(self.filepath)
                self.filebase, self.fileext = os.path.splitext(self.filename)

        def read(self):
            """Return contents of file."""
            if self.filepath and os.path.exists(self.filepath):
                f = open(self.filepath, 'r')#b')
                try:
                    return f.read()
                finally:
                    f.close()
            else:
                return ''

        def write(self, text):
            """Write text to file."""
            try:
                f = open(self.filepath, 'w')#b')
                f.write(text)
            finally:
                if f:
                    f.close()
    py.document.Document = Document

    class MyEditorFrame(py.editor.EditorFrame):
        def __init__(self):
            py.editor.EditorFrame.__init__(self,
                                           parent=None,#, would kill editor without cheking for save !! sys.app.GetTopWindow(),
                                           title="Priithon Editor",
                                           filename=filename)
        def bufferCreate(self, filename=None):
            """Create new buffer."""
            self.bufferDestroy()
            buffer = py.editor.Buffer()
            self.panel = panel = wx.Panel(parent=self, id=-1)
            panel.Bind (wx.EVT_ERASE_BACKGROUND, lambda x: x)
            editor = py.editor.Editor(parent=panel)
            panel.editor = editor
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(editor.window, 1, wx.EXPAND)
            panel.SetSizer(sizer)
            panel.SetAutoLayout(True)
            sizer.Layout()
            buffer.addEditor(editor)
            buffer.open(filename)
            self.setEditor(editor)
            self.editor.setFocus()
            self.SendSizeEvent()

            # added 20180329
            editor.GetColumn = editor.window.GetColumn
            editor.CallTipShow = editor.window.CallTipShow
            editor.buffer.confirmed = True # already confirmed by the dialog

    # -----------------------------------
    
    #f = py.editor.EditorFrame(parent=None,#, would kill editor without cheking for save !! sys.app.GetTopWindow(),
    #                             title="Priithon Editor",
    #                             filename=filename)
    f = MyEditorFrame()
    
    if not filename: # we ALWAYS want bufferCreate - even when filename is "False"
        f.bufferCreate(filename)
        
    f.Show()
    if retTextWindow:
        return f.editor.window

def commands():
    import __main__
    f = wx.Frame(None, -1, "command history") #, size=wx.Size(400,400))
    sizer = wx.BoxSizer(wx.VERTICAL)
    #import __main__
    #cl = __main__.shell.history
    l = wx.ListBox(f, wx.ID_ANY) #, choices=cl) #, wx.LB_SINGLE)
    sizer.Add(l, 1, wx.EXPAND | wx.ALL, 5);
    #wx.EVT_LISTBOX(f, 60, self.EvtListBox)
    def dd(ev):
        #s= ev.GetString()
        s = l.GetStringSelection()
        #print s

        endpos = __main__.shell.GetTextLength()
        __main__.shell.InsertText(endpos, s)
        # __main__.shell.AppendText(len(s), s)
        __main__.shell.SetFocus()

    wx.EVT_LISTBOX_DCLICK(f, l.GetId(), dd)
    # wx.EVT_RIGHT_UP(self.lb1, self.EvtRightButton)

    hsz = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(hsz, 0, wx.EXPAND)
    b1 = wx.Button(f, wx.ID_ANY, "insert")
    hsz.Add(b1, 1, wx.EXPAND|wx.ALL, 2)
    wx.EVT_BUTTON(f, b1.GetId(), dd)
    
    def refreshList(ev):
        cl = list(__main__.shell.history) # copy!
        cl.reverse()
        #not true-20070725 cl = cl[1:] # CHECK - first command is always: print Startup script executed: /jws30/haase/PrLin0/Priithon/includeAll.py
        l.Clear()
        l.InsertItems( cl, 0 )
        if l.GetCount():
            l.SetSelection( l.GetCount()-1 )

    b2 = wx.Button(f, wx.ID_ANY, "refresh")
    hsz.Add(b2, 1, wx.EXPAND|wx.ALL, 2)
    wx.EVT_BUTTON(f, b2.GetId(), refreshList)


    refreshList(None)

    f.SetSizer(sizer)
    #sizer.SetSizeHints(f)
    f.SetAutoLayout(1)
    sizer.Fit(f)
    f.Show()

def load(imgFN=None):
    """open any image file:
          '.fits'  - FITS files
          '.sif'   - Andor SIF files
          '.his'   - Hamamatsu HIS files
          any image file: jpg/bmp/png/... (all PIL formats)
               #20060824 CHECK  in this case the returned arr gets attr: arr._originLeftBottom=0
          'Mrc' (use Mrc.bindFile)
          TODO: "_thmb_<fn.jpg>" files are taken to mean <fn.jpg>
       returns image array
               None on error

       if imgFN is None  call Y.FN()  for you
    """
    from . import useful as U

    if imgFN is None:
        imgFN = FN()
    if not imgFN:
        return
    try:
        return U.load(imgFN)
    except:
        U._raiseRuntimeError("Cannot open file as image\n")

def viewInViewer(id, a, title=None, doAutoscale=1):
    """
    like view but instead of opening a new window
    it reused existing viewer # id
    if that viewer is closed (or was newer opened)
    viewInViewer fails EXCEPT id==-1
      in that case a new viewer is created and gets reused
      for subsequent called with id=-1
    """
    try:
        spv =  viewers[id]
        if spv is None:
            raise RuntimeError
    except:
        if id==-1:
            view(a)
            return
        else:
            raise RuntimeError("viewer %d doesn't exist"%id)

    from .splitND import spv as spv_class
    if not isinstance(spv, spv_class):
        raise RuntimeError("viewer #%d is not a mono-color viewer" % id)

    if isinstance(a, tuple):
        from Priithon.fftfuncs import mockNDarray
        a=mockNDarray(*a)

    if min(a.shape) < 1:
        raise ValueError("array shape contains zeros (%s)"%(a.shape,))
    
    #multicolor = hasattr(spv, "ColorAxisOrig") # HACK FIXME


    #print a.ndim-2, spv.zndim
    if a.ndim-2 != spv.zndim:
        #wx.MessageBox("Dimension mismatch old vs. new",
        #             "Differnt dimesion !?",
        #             style=wx.ICON_ERROR)
        spv.zshape= a.shape[:-2]
        spv.zndim = len(spv.zshape)
        spv.zsec  = [0] * spv.zndim
        spv.zlast = [0]*spv.zndim # remember - for checking if update needed

        spv.putZSlidersIntoTopBox(spv.upperPanel, spv.boxAtTop)
    else:
        spv.zshape= a.shape[:-2]
        for i in range(spv.zndim):
            nz = a.shape[i]
            spv.zzslider[i].SetRange(0, nz-1)
            if spv.zsec[i] >= nz:
                spv.zsec[i] = 0 # maybe better: nz-1
                spv.zlast[i] = 0

    spv.data = a
    spv.helpNewData(doAutoscale=doAutoscale)
    if title is None:
        title=''
        if hasattr(spv.data, 'Mrc'):
            title += "<%s>" % spv.data.Mrc.filename
    title2 = "%d) %s" %(spv.id, title)
    spv.title = title
    spv.title2 = title2
    #20070808spv.frame.SetTitle(title2)
    wx.GetTopLevelParent(spv.viewer).SetTitle(title2) # CHECK

def viewInViewer2(id, a, colorAxis="smart", title=None, doAutoscale=1):
    """
    like view2 but instead of opening a new window
    it reused existing viewer # id
    if that viewer is closed (or was newer opened)
    viewInViewer2 fails EXCEPT id==-1
      in that case a new viewer is created and gets reused
      for subsequent called with id=-1
    """
    try:
        spv =  viewers[id]
        if spv is None:
            raise RuntimeError
    except:
        if id==-1:
            view2(a)
            return
        else:
            raise ValueError("viewer %d doesn't exist"%id)

    from .splitND2 import spv as spv2_class
    if not isinstance(spv, spv2_class):
        raise RuntimeError("viewer #%d is not a multi-color viewer" % id)

    if isinstance(a, tuple):
        from Priithon.fftfuncs import mockNDarray
        a=mockNDarray(*a)

    if a.ndim < 3:
        raise ValueError("array ndim must be at least 3")
    if min(a.shape) < 1:
        raise ValueError("array shape contains zeros (%s)"%(a.shape,))
    
    #multicolor = hasattr(spv, "ColorAxisOrig") # HACK FIXME


    if colorAxis=='smart':
        nonXYshape = list(a.shape[:-2])
        
        # use shortest "z-dimension" as color - use smaller axisIndex if two are of same length
        notShort = 1+ max(nonXYshape) # use this to have   axes of length 1  ignored
        nonXYshape = [x>1 and x or notShort for x in nonXYshape] # ignore axes of length 1
        colorAxis = nonXYshape.index( min(nonXYshape) )
    if colorAxis < 0:
        colorAxis += a.ndim
    if colorAxis < a.ndim - 3:
        a=N.transpose(a, list(range(colorAxis)) + \
                          list(range(colorAxis+1,a.ndim-2))+\
                          [colorAxis,a.ndim-2,a.ndim-1] )
    elif colorAxis == a.ndim - 2:
        a=N.transpose(a, list(range(a.ndim-3)) + [colorAxis, a.ndim-3, a.ndim-1] )

    elif colorAxis == a.ndim - 1:
        a=N.transpose(a, list(range(a.ndim-3)) + [colorAxis, a.ndim-3, a.ndim-2] )

    if a.shape[-3] > 8:
        raise ValueError("You should not use more than 8 colors (%s)"%a.shape[-3])


    #print a.ndim-2, spv.zndim
    if a.ndim-3 != spv.zndim:
        # reinit number of "z sliders" (ndim-3 == colorAxis is excluded)
        spv.zshape= a.shape[:-3]
        spv.zndim = len(spv.zshape)
        spv.zsec  = [0] * spv.zndim
        spv.zlast = [0] * spv.zndim # remember - for checking if update needed

        spv.putZSlidersIntoTopBox(spv.upperPanel, spv.boxAtTop)
    else:
        spv.zshape= a.shape[:-3]
        for i in range(spv.zndim):
            nz = a.shape[i]
            spv.zzslider[i].SetRange(0, nz-1)
            if spv.zsec[i] >= nz:
                spv.zsec[i] = 0 # maybe better: nz-1
                spv.zlast[i] = 0

    if a.shape[-3] != spv.nColors:
        if a.shape[-3] < spv.nColors:
            # delete last images first -> ::-1 (reverse)
            for i in range(a.shape[-3], spv.nColors)[::-1]:
                spv.viewer.delImage(i)
        else:
            # add additional images(=colors)
            imgL =  a[tuple(spv.zsec)]
            spv.viewer.addImgL(imgL[spv.nColors:])
            # NOTE: the image data might get loaded into gfx-card twice - because of setImage call 
            from .splitND2 import _rgbList
            # check what RGB-color are used so far
            for i in range(spv.nColors, a.shape[-3]):
                for rgb in _rgbList:
                    for j in range(i):
                        if tuple(rgb) == tuple(spv.viewer.getColor(j)):
                            break
                    else:
                        break # use the first rgb color from _rgbList that is not yet used
                spv.viewer.setColor(i, rgb, RefreshNow=False)

        # reinit number of color channnels
        spv.nColors = a.shape[-3]
        spv.histsPanel.DestroyChildren()
        spv.initHists()
        for i,h in enumerate(spv.hist):     # set RGB color for hist from already-set viewer
            h.m_histGlRGB = spv.viewer.getColor(i)
        #FIXME spv.splitter.SplitHorizontally(spv.upperPanel, spv.histsPanel, -40*spv.nColors)
        spv.histsPanel.Layout() # triggers redraw

    spv.data = a
    spv.helpNewData(doAutoscale=doAutoscale)
    if title is None:
        title=''
        if hasattr(spv.data, 'Mrc'):
            title += "<%s>" % spv.data.Mrc.filename
    title2 = "%d) %s" %(spv.id, title)
    spv.title = title
    spv.title2 = title2
    #20070808spv.frame.SetTitle(title2)
    wx.GetTopLevelParent(spv.viewer).SetTitle(title2) # CHECK


class _listFilesViewer:
    def __init__(self, dir=None, viewerID=None, autoscale=True, reuse=True, color=False):
        self.viewerID = viewerID
        if dir is None:
            dir = DIR(0)
            if not dir:
                return
        import os
        #self.dir=os.path.abspath(os.path.dirname(self.dir))
        self.dir=os.path.abspath(dir)
        self.fnPat = "*"
        if not os.path.isdir(self.dir):
            self.dir, self.fnPat = os.path.split(self.dir)

        self.frame = wx.Frame(None, -1, '') #, size=wx.Size(400,400))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.lb = wx.ListBox(self.frame, wx.ID_ANY, size=(300,400)) #, choices=cl) #, wx.LB_SINGLE)
        sizer.Add(self.lb, 1, wx.EXPAND | wx.ALL, 5)
        #wx.EVT_LISTBOX(f, 60, self.EvtListBox)
        wx.EVT_MOTION(self.lb, self.onStartDrag)


        # wx.EVT_LISTBOX_DCLICK(self.frame, 1001, onDClick)
        # 20080423ProblemSeeWx-Dev2008Jan("wxlistbox enter") wx.EVT_LISTBOX_DCLICK(self.frame, self.lb.GetId(), lambda ev:onDClick(ev, chdir=True))
        # 20080423ProblemSeeWx-Dev2008Jan("wxlistbox enter") wx.EVT_LISTBOX(self.frame, self.lb.GetId(), lambda ev:onDClick(ev, chdir=False))
        wx.EVT_LISTBOX(self.frame, self.lb.GetId(), lambda ev:self.onDClick(ev, chdir=False))
        wx.EVT_LISTBOX_DCLICK(self.frame, self.lb.GetId(), lambda ev:self.onDClick(ev, chdir=True))
        # wx.EVT_RIGHT_UP(self.lb1, self.EvtRightButton)

        hsz = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(hsz, 0, wx.EXPAND)

        self.txt = wx.TextCtrl(self.frame, wx.ID_ANY, self.getPath())
        hsz.Add(self.txt, 1, wx.EXPAND|wx.ALL, 2)
        wx.EVT_TEXT(self.frame, self.txt.GetId(), self.refreshList)
    
        self.autoscale = wx.CheckBox(self.frame, wx.ID_ANY, "autoscale")
        hsz.Add(self.autoscale, 0, wx.EXPAND|wx.ALL, 2)
        self.autoscale.SetValue(autoscale)
        self.reuse = wx.CheckBox(self.frame, wx.ID_ANY, "reuse")
        hsz.Add(self.reuse, 0, wx.EXPAND|wx.ALL, 2)
        self.reuse.SetValue(reuse)
        self.multicolor = wx.CheckBox(self.frame, wx.ID_ANY, "color")
        hsz.Add(self.multicolor, 0, wx.EXPAND|wx.ALL, 2)
        self.multicolor.SetValue(color)

        #b1 = wx.Button(self.frame, 1002, "show")
        #hsz.Add(b1, 0, wx.EXPAND|wx.ALL, 2)
        #wx.EVT_BUTTON(self.frame, 1002, onDClick)
    
        #b2 = wx.Button(self.frame, 1003, "refresh")
        #hsz.Add(b2, 0, wx.EXPAND|wx.ALL, 2)
        #wx.EVT_BUTTON(self.frame, 1003, refreshList)

        ll = self.txt.GetLastPosition()
        #self.txt.ShowPosition(ll) #makes only LINE of ll visible
        self.txt.SetInsertionPoint(ll)

        self.refreshList(None)

#       if self.lb.GetCount() > 1:
#           if viewerID is None:
#               view(self.dir+"/"+self.lb.GetString(1)) # first is '..'
#               id = len(viewers)-1
#           else:
#               id = viewerID

        self.frame.SetSizer(sizer)
        sizer.SetSizeHints(self.frame)
        self.frame.SetAutoLayout(1)
        sizer.Fit(self.frame)
        self.frame.Show()

        self.dropTarget = self.MyFileDropTarget(self)
        for w in iterChildrenTree(self.frame):
            w.SetDropTarget(self.dropTarget)

    def getPath(self):
        import os
        return os.path.join(self.dir, self.fnPat)

    def onDClick(self, ev, chdir):
        import os
        #s= ev.GetString()
        s = self.lb.GetStringSelection()
        fn = os.path.join(self.dir, s)
        self.fn = fn

        import os.path
        if os.path.isdir(fn):
            if chdir:
                self.dir = os.path.normpath(fn)
                #20051201 n = os.path.basename(self.txt.GetValue())
                #20051201 self.txt.SetValue(os.path.join(self.dir, n))
                _,self.fnPat = os.path.split(self.txt.GetValue())
                self.txt.SetValue(self.getPath())
                self.refreshList()
            return
        a = load(fn) #20051213
        if a is None:
            return
        if     not self.reuse.GetValue() or \
               self.viewerID is None or \
               self.viewerID >= len(viewers) or \
               viewers[self.viewerID] is None:
            if self.multicolor.GetValue():
                # 20071114 added back "title" because of tif files  - FIXME 
                view2(a, title="<%s>" % s) #20071106 splitND.makeFrame auto-appends filename-title:, title="<%s>"%s)
            else:
                # 20071114 added back "title" because of tif files - FIXME 
                view(a, title="<%s>" % s) #20071106 splitND.makeFrame auto-appends filename-title:, title="<%s>" % s) #fn)
            self.viewerID = len(viewers)-1
            title = "files in %s (viewer %s)" % (self.dir, self.viewerID)
            self.frame.SetTitle(title)
        else:
            if self.multicolor.GetValue():
                viewInViewer2(self.viewerID, a, title="<%s>" % s, doAutoscale=self.autoscale.GetValue())
            else:
                viewInViewer(self.viewerID, a, title="<%s>" % s, doAutoscale=self.autoscale.GetValue())
        #print s

    def refreshList(self, ev=None):
        """
        generate list of files:
        1. "../"
        2. all sub dirs
        3. files, only those that match the given file pattern
        """
        import os.path,os
        import glob


#         def u8(s):
#             """
#             returns unicode(s, 'u8') unless s is already unicode
#             """
#             if isinstance(s, unicode):
#                 return s
#             else:
#                 return unicode(s, 'u8')

        
        filesGlob = self.txt.GetValue()
        _,self.fnPat = os.path.split(filesGlob)  # in case text for fnPat has changed
        d,f = os.path.split(filesGlob)
        if f == '':
            f = '*'

        # list of sub-dirs -- add trailing '/'
        try:
            #ddDirs = sorted( [f1+'/' for f1 in map(u8, os.listdir(d)) if os.path.isdir(os.path.join(d,f1))] )
            ddDirs = sorted( [f1+'/' for f1 in os.listdir(d) if os.path.isdir(os.path.join(d,f1))] )
        except OSError:
            ddDirs = []

        #if os.path.isdir(filesGlob):
        #    self.dir = filesGlob
        #    #sort broken: dd= map(os.path.abspath, os.listdir(filesGlob) )
        #    dd = glob.glob(self.getPath())
        #else:
        #    self.dir = os.path.dirname(filesGlob)
        #    dd = glob.glob(filesGlob)
        
        #ddFiles = sorted( [f1 for f1 in map(u8,glob.glob1(d,f)) if not os.path.isdir(os.path.join(d,f1))] )
        ddFiles = sorted( [f1 for f1 in glob.glob1(d,f) if not os.path.isdir(os.path.join(d,f1))] )

        #def mySort(f1,f2):
        #    d1 = int( os.path.isdir(f1) )
        #    d2 = int( os.path.isdir(f2) )
        #    #ddd = d1-d2    # move dirs to end of list
        #    ddd = d2-d1
        #    #print ddd, f1,f2
        #
        #    return ddd or cmp(f1,f2)
        #dd.sort( mySort )
        #dd = [os.path.basename(f) for f in dd]
        #dd[0:0] = ["../"]

        dd = ["../"] + ddDirs + ddFiles

        #di = 1 # just in case for-loop doesn;t run == di used below !!
        ## append trailing '/' to indicate dirs
        #for di in range(1,len(dd)):
        #    if os.path.isdir(self.dir+'/'+dd[di]):
        #        dd[di] += '/'
        #    else:
        #        break
        
        self.lb.Clear()
        self.lb.InsertItems( dd, 0 )
        #if di<self.lb.GetCount():
        #    self.lb.SetSelection( di ) # first is '..'
            
        title = "files in %s (viewer %s)" % (self.dir, self.viewerID)
        self.frame.SetTitle(title)

    def onStartDrag(self, evt):
        if evt.Dragging():
            import os.path
            fn = self.lb.GetStringSelection()
            fn = os.path.join(self.dir, fn)
            data = wx.FileDataObject()
            data.AddFile(fn)
            dropSource = wx.DropSource(self.lb)
            dropSource.SetData(data)
            dropSource.DoDragDrop(1)
        evt.Skip()

    class MyFileDropTarget(wx.FileDropTarget):
        def __init__(self, parent):
            wx.FileDropTarget.__init__(self)
            self.myLFV = parent

        def OnDropFiles(self, x, y, filenames):
            import os.path
            fn = filenames[0]
            
            if os.path.isdir(fn):
                self.myLFV.dir =                 os.path.normpath(fn)
            else:
                self.myLFV.dir,_ = os.path.split(os.path.normpath(fn))

            self.myLFV.txt.SetValue(self.myLFV.getPath())
            self.myLFV.refreshList()


def listFilesViewer(dir=None, viewerID=None, autoscale=True, reuse=True, color=False):
    """
    open a window showing a list of all (image) files in a given directory
    per click these can be displayed in an image viewer
    """
    global _listFilesViewer_obj
    _listFilesViewer_obj = _listFilesViewer(dir,viewerID, autoscale=autoscale, reuse=reuse, color=color)



class _listArrayViewer:
    def __init__(self, modname='__main__', viewerID=None):
        self.viewerID = viewerID
        self.modname  = modname
        import sys
    
        self.frame = wx.Frame(None, -1, "") #, size=wx.Size(400,400))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.lb = wx.ListBox(self.frame, wx.ID_ANY, size=(300,400)) #, choices=cl) #, wx.LB_SINGLE)
        sizer.Add(self.lb, 1, wx.EXPAND | wx.ALL, 5);
        #wx.EVT_LISTBOX(f, 60, self.EvtListBox)
        
        #wx.EVT_LISTBOX_DCLICK(self.frame, self.lb.GetId(), onDClick)
        wx.EVT_LISTBOX(self.frame, self.lb.GetId(), self.onDClick)
        # wx.EVT_RIGHT_UP(self.lb1, self.EvtRightButton)

        hsz = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(hsz, 0, wx.EXPAND)
        
        self.txt = wx.TextCtrl(self.frame, wx.ID_ANY, self.modname)
        hsz.Add(self.txt, 1, wx.EXPAND|wx.ALL, 2)
        wx.EVT_TEXT(self.frame, self.txt.GetId(), self.refreshList)
        
        self.autoscale = wx.CheckBox(self.frame, wx.ID_ANY, "autoscale")
        hsz.Add(self.autoscale, 0, wx.EXPAND|wx.ALL, 2)
        self.autoscale.SetValue(1)
        self.reuse = wx.CheckBox(self.frame, wx.ID_ANY, "reuse")
        hsz.Add(self.reuse, 0, wx.EXPAND|wx.ALL, 2)
        self.reuse.SetValue(1)
        self.multicolor = wx.CheckBox(self.frame, wx.ID_ANY, "color")
        hsz.Add(self.multicolor, 0, wx.EXPAND|wx.ALL, 2)
        #self.multicolor.SetValue(1)
        
        #b1 = wx.Button(self.frame, 1002, "show")
        #hsz.Add(b1, 0, wx.EXPAND|wx.ALL, 2)
        #wx.EVT_BUTTON(self.frame, 1002, onDClick)
        
        b2 = wx.Button(self.frame, wx.ID_ANY, "refresh")
        hsz.Add(b2, 0, wx.EXPAND|wx.ALL, 2)
        wx.EVT_BUTTON(self.frame, b2.GetId(), self.refreshList)
        
        ll = self.txt.GetLastPosition()
        #self.txt.ShowPosition(ll) #makes only LINE of ll visible
        self.txt.SetInsertionPoint(ll)
        
        self.refreshList()
        #onDClick()
        self.frame.SetSizer(sizer)
        sizer.SetSizeHints(self.frame)
        self.frame.SetAutoLayout(1)
        sizer.Fit(self.frame)
        self.frame.Show()
        ##return None # CHECK - still returns self - CHECK
        
    def onDClick(self, ev=None):
        #s= ev.GetString()
        s = self.lb.GetStringSelection()
        mod = __import__(self.modname) # , globals(), locals(), [])
        showdict=mod.__dict__
        a = showdict[s]
        if     not self.reuse.GetValue() or \
               self.viewerID is None or \
               self.viewerID >= len(viewers) or \
               viewers[self.viewerID] is None:

            if self.multicolor.GetValue():
                view2(a, title="%s"%s)
            else:
                view(a, title="%s"%s)
            self.viewerID = len(viewers)-1
            title = "arrays in %s (viewer %s)" % (self.modname, self.viewerID)
            self.frame.SetTitle(title)
        else:
            if self.multicolor.GetValue():
                viewInViewer2(self.viewerID, a, title="%s"%s, doAutoscale=self.autoscale.GetValue())
            else:
                viewInViewer(self.viewerID, a, title="%s"%s, doAutoscale=self.autoscale.GetValue())
#       #print s
        
    def refreshList(self, ev=None):
        self.modname = self.txt.GetValue()
        #       if not self.modname:
        #           global fr,fc, argsn, args
        #           fr = sys._getframe(1)
        #           fc = fr.f_code
        #           showdict = fr.f_locals # .keys()
        #           self.modname = fr.f_globals['__name__']
        
        #           # fr.f_globals['__name__']
        #           # '__main__'
        #           # fr.f_locals['__name__']
        #           # '__main__'
        #       else:
        if not self.modname:
            self.modname = '__main__'
        try:
            #exec('import %(self.modname)s;showdict=%(self.modname)s'%locals())
            mod = __import__(self.modname) # , globals(), locals(), [])
            showdict=mod.__dict__ # eval('%(self.modname)s.__dict__'%locals())
        except ImportError:
            self.frame.SetTitle("module '%s' not found" % self.modname)
            self.lb.Clear()
            return
        varlist = []
        arrs = {}
    
        def sebsort(m1,m2):
            import builtins
            k1 = arrs[ m1 ][1]
            k2 = arrs[ m2 ][1]
            return builtins.cmp(k1,  k2)

        for k in showdict:
            o = showdict[k]

            if isinstance(o, N.ndarray):
                varlist.append(k)
                # 20070731 size = len(o.data)
                # 20070731 memAt = o.ctypes.get_data()
                '''20070731
                f = string.split( repr(o._data) )
                if f[0] == '<memory': # '<memory at 0x50a66008 with size:0x006f5400 held by object 0x092772e8 aliasing object 0x00000000>'
                    fs = string.split( f[4],':' )
                    size   = eval( fs[1] )
                    memAt  = f[2]
                    objNum = f[8]
                elif f[0] == '<MemmapSlice': # '<MemmapSlice of length:7290000 readonly>'
                    fs = string.split( f[2],':' )
                    size   = eval( fs[1] )
                    objNum = 0
                else:
                    #print "# DON'T KNOW: ",     k, repr(o._data)
                    continue
                    '''
                '''20070731
                try:
                    arrs[ memAt ][0] += 1
                    arrs[ memAt ][1].append( k )
                    arrs[ memAt ][2].append( size )
                except:
                    arrs[ memAt ] = [ 1, [k], [size] ]
                '''

        '''20070731 was this to only show an array once - even if there are to names for it in the dictionary !?!?!?
        ms = arrs.keys()
        ms.sort( sebsort )
        #print kStringMaxLen
        for memAt in ms:
            ks   = arrs[ memAt ][1]
            size = arrs[ memAt ][2][0]
            o = showdict[ ks[0] ]
            if len(ks) == 1:
                ks = ks[0]
    
            varlist.append(ks)
        '''
        varlist.sort()


        self.lb.Clear()
        if len(varlist):
            self.lb.InsertItems( varlist, 0 )
            self.lb.SetSelection( 0 )

        title = "arrays in %s (viewer %s)" % (self.modname, self.viewerID)
        self.frame.SetTitle(title)


def listArrayViewer(modname='__main__', viewerID=None):
    """
    open a window showing a list of all numpy arrays in given module
    per click these can be displayed in an image viewer
    """
    global _listArrayViewer_obj
    _listArrayViewer_obj = _listArrayViewer(modname,viewerID)

    
def saveSession(fn=None, autosave=False):
    """
    saves all text from PyShell into a file w/ file name 'fn'
    if fn is None it calls smart 'FN()' for you

    if autosave is True:
       ignore fn and use auto generated filename (see _priConfig.autoSave...)
    """
    
    import sys
    if hasattr(sys, "app"):       # PyShell, PyCrust, ...
        #shell = sys.app.frame.shell
        import __main__
        shell = __main__.shell
#     elif hasattr(sys, "shell"): # embedded in OMX
#         import __main__
#         shell = __main__.shell
#         #shell = sys.shell
    else:
        #raise RuntimeError, "sorry, can't find shell"
        return

    if autosave:
        if fn is not None:
            raise ValueError("you cannot specify a filename when autosave=True")
        
        import os, useful as U
        U.path_mkdir( os.path.dirname(PriConfig._autoSaveSessionPath) )
        fn = PriConfig._autoSaveSessionPath

        # save text file containing only the commands (no return vals or prints)
        if PriConfig.autoSaveSessionCommands:
            #import __main__
            f = file(fn[:-3]+PriConfig.autoSaveSessionCommands, 'w')
            #for c in __main__.shell.history[::-1]:
            for c in shell.history[::-1]:
                print(c, file=f)
            f.close()

    if fn is None:
        import time
        # global _saveSessionDefaultPrefix
        fn = PriConfig.saveSessionDefaultPrefix + time.strftime("%Y%m%d-%H%M.py")
        fn = wx.FileSelector("Please select file", "",fn, flags=wx.SAVE)

    if not fn: # cancel
        return

    f = open(fn, "w")
    #f.write(shell.GetText().replace('\r', ''))
    f.write(shell.GetText().encode("l1").replace('\r', ''))
    #f.write("\n") # append trailing newline, that appears to be missing in shell.GetText
    f.close()
    print("# '%s' saved." %( fn, ))
    
    
def FN_seb(save=0, verbose=1):
    """use mouse to get filename

    if verbose is true: also print filename
    """

    ## frame title, start-dir, default-filename, ??, default-pattern
    if save:
        flags=wx.SAVE
    else:
        flags=0
    fn = wx.FileSelector("Please select file", flags=flags)
    if verbose:
        print(repr(fn))
    return fn

_DIR = None
_WILDCARD = '*'
def FN(save=0):
    if save:
        return FN_seb(save, verbose=0)
    else:
        return FNs_am(multiple=False)

def FNs(verbose=False):
    fns = FNs_am()
    if verbose:
        print(repr(fns))
    return fns

def FNs_am(multiple=True):
    """
    open fileselector dialog
    return fns
    """
    global _DIR, _WILDCARD
    try:
        from PriCommon import guiFuncs as G
        import os
    except ImportError:
        raise NotImplementedError('Please install PriCommon')

    fns = None
    with G.FileSelectorDialog(direc=_DIR, wildcard=_WILDCARD, multiple=multiple) as dlg:
        if dlg.ShowModal():
            fns = dlg.GetPaths()
            if fns:
                _DIR = os.path.dirname(fns[0])
                _WILDCARD = dlg.fnPat
                if not multiple:
                    fns = fns[0]
    return fns

def view3(fns):
    """
    opens a memory efficient viewer with orthogonal view
    """
    try:
        import ndviewer
        import os
    except ImportError:
        raise NotImplementedError('Please install ndviewer')

    return ndviewer.main.main(fns)
        
def DIR(verbose=1):
    """use mouse to get directory name

    if verbose is true: also print dirname
    """

    import os
    try:
        d = os.getcwd() # OSError or Erik's  Laptop
    except:
        d = "/"
    fn = wx.DirSelector("Please select directory", d)
    if verbose:
        print(repr(fn))
    return fn

def cd():
    """change current working directory"""
    import os
    os.chdir( DIR() )

def refresh():
    """use in scripts to refresh PyShell"""
    try:
        import wx
        wx.Yield()
    except:
        pass # maybe we don't have wx...
def sleep(secs=1):
    """resfresh and then sleep"""
    try:
        import wx
        wx.Yield()
        wxSleep(secs)
    except:
        pass # maybe we don't have wx...

def iterChildrenTree(parent, includeParent=True):
    """
    iterate of all children and child's childrens of a `parent` wxWindow
    this is an iterator!
    """
    yield parent
    for c in parent.GetChildren():
        for i in iterChildrenTree(c, True):
            yield i


###############################################################################
###############################################################################
###############################################################################
###############################################################################


#from . import plt
from .usefulP import *



def plotProfileHoriz(img_id, y, avgBandSize=1):#, s='-'):
    if type(img_id) == int:
        img = viewers[ img_id ].img
    else:
        img = img_id
    h,w = img.shape

    if avgBandSize >1:
        vals = N.sum( img[ y:y+avgBandSize ].astype(N.float64), 0 ) / float(avgBandSize)
        ploty( vals, symbolSize=0)#s )
    else:
        ploty( img[ y ], symbolSize=0)#s )
def plotProfileVert(img_id, x, avgBandSize=1):#, s='-'):
    if type(img_id) == int:
        img = viewers[ img_id ].img
    else:
        img = img_id
    h,w = img.shape

    if avgBandSize >1:
        vals = N.sum( img[ :, x:x+avgBandSize ].astype(N.float64), 1 ) / float(avgBandSize)
        ploty( vals, symbolSize=0)#s )
    else:
        ploty( img[ :, x ], symbolSize=0)#s )
def plotProfileZ(img_id, y,x, avgBandSize=1):#, s='-'):
    if type(img_id) == int:
        data = viewers[ img_id ].data
    else:
        data = img_id

    if avgBandSize >1:
        w,h = avgBandSize,avgBandSize
        w2,h2 = w/2., h/2.
        x0,y0,x1,y1 = int(x-w2+.5),int(y-h2+.5),  int(x+w2+.5),int(y+h2+.5)
        #from useful import mean2d
        nz = data.shape[-3]
        prof = N.empty(shape=nz, dtype=N.float64)
        for z in range(nz):
            prof[z] = data[z,  y0:y1, x0:x1].mean()
        ploty( prof, symbolSize=0)#s )
    else:
        ploty( data[ :, int(y), int(x) ], symbolSize=0)#s )

'''

def plotFitAny(f, parms, min=None,max=None,step=None,hold=True,s='-'):
    """
    if min is None defaults to min-x of current plot (dataset 0)
    if max is None defaults to max-x of current plot (dataset 0)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand
    """
    import useful as U
    import __builtin__
    if min is None or max is None:
        dpx = plotDatapoints(0)[0]
        if min is None:
            min = __builtin__.min(dpx)
        if max is None:
            max = __builtin__.max(dpx)
    if step is None:
        step = (max-min)/1000.
    if hold is not None:
        plothold(hold)
    x=N.arange(min,max,step)
    plotxy(x,f(parms,x), s)

def plotFitLine(abTuple, min=None,max=None,step=None,hold=True,s='-'):
    """
    if min is None defaults to min-x of current plot (dataset 0)
    if max is None defaults to max-x of current plot (dataset 0)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand
    """
    import useful as U
    plotFitAny(U._poly,(abTuple[1],abTuple[0]), min,max,step,hold,s)
def plotFitPoly(parms, min=None,max=None,step=None,hold=True,s='-'):
    """
    if min is None defaults to min-x of current plot (dataset 0)
    if max is None defaults to max-x of current plot (dataset 0)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand
    """
    import useful as U
    plotFitAny(U._poly, parms, min,max,step,hold,s)
def plotFitDecay(parms, min=None,max=None,step=None,hold=True,s='-'):
    """
    if min is None defaults to min-x of current plot (dataset 0)
    if max is None defaults to max-x of current plot (dataset 0)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand
    """
    import useful as U
    plotFitAny(U._decay, parms, min,max,step,hold,s)
def plotFitGaussian1D(parms, min=None,max=None,step=None,hold=True,s='-'):
    """
    if min is None defaults to min-x of current plot (dataset 0)
    if max is None defaults to max-x of current plot (dataset 0)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand
    """
    import useful as U
    if   len(parmTuple0) == 2:
        f = U._gaussian1D_2
    elif len(parmTuple0) == 3:
        f = U._gaussian1D_3
    elif len(parmTuple0) == 4:
        f = U._gaussian1D_4
    
    plotFitAny(f, parms, min,max,step,hold,s)

'''










def plotFitAny(func, parms, min=None,max=None,step=None,hold=True,dataset=0,doFit=True, figureNo=None):#s='-', dataset=0, doFit=True, figureNo=None, logY=False, logX=False, logZeroOffset=.01):
    """
    if min is None defaults to min-x of current plot (for given dataset)
    if max is None defaults to max-x of current plot (for given dataset)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand

    if doFit:
      do a curve fit to adjust parms  before plotting
      return (parms, fitFlag)
    """
    import builtins
    if min is None or max is None:
        dpx = plotDatapoints(dataset,figureNo)[0]
        if min is None:
            min = builtins.min(dpx)
        if max is None:
            max = builtins.max(dpx)
    if step is None:
        step = (max-min)/1000.

    x=N.arange(min,max,step)
    if doFit:
        from . import useful as U
        data = N.asarray(plotDatapoints(dataset, figureNo), dtype=N.float64)
        parms, ret = U.fitAny(func, parms, data.T)
        
    #plotxy(x,func(parms,x), s, hold=hold, logY=logY, logX=logX, logZeroOffset=logZeroOffset, figureNo=figureNo)
    plotxy(x,func(parms,x), c='-', hold=hold, figureNo=figureNo)#, symbolSize=0)
    if doFit:
        return parms, ret

def plotFitDecay(parms=(1000,10000,10), min=None,max=None,step=None,hold=True,dataset=0,doFit=True, figureNo=None): #s='-', dataset=0, doFit=True, figureNo=None, logY=False, logX=False, logZeroOffset=.01):
    """
    see U.yDecay.
    if min is None defaults to min-x of current plot (dataset 0)
    if max is None defaults to max-x of current plot (dataset 0)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand
    """
    from . import useful as U
    return plotFitAny(U.yDecay, parms, min,max,step,hold,dataset,doFit, figureNo) #s, dataset, doFit, figureNo=figureNo, logY=logY, logX=logX, logZeroOffset=logZeroOffset)

def plotFitGaussian(parms=(0,10,100), min=None,max=None,step=None,hold=True,dataset=0,doFit=True,figureNo=None):#s='-', dataset=0, doFit=True, figureNo=None, logY=False, logX=False, logZeroOffset=.01):
    """
    see U.yGaussian.
    if min is None defaults to min-x of current plot (dataset 0)
    if max is None defaults to max-x of current plot (dataset 0)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand
    """
    from . import useful as U
    return plotFitAny(U.yGaussian, parms, min,max,step,hold,dataset,doFit, figureNo)#s, dataset, doFit, figureNo=figureNo, logY=logY, logX=logX, logZeroOffset=logZeroOffset)

def plotFitLine(abTuple, min=None,max=None,step=None,hold=True,dataset=0,doFit=True,figureNo=None):#s='-', dataset=0, doFit=True, figureNo=None, logY=False, logX=False, logZeroOffset=.01):
    """
    if min is None defaults to min-x of current plot (dataset 0)
    if max is None defaults to max-x of current plot (dataset 0)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand
    """
    from . import useful as U
    return plotFitAny(U.yLine, abTuple, min,max,step,hold,dataset,doFit, figureNo)#s, dataset, doFit, figureNo=figureNo, logY=logY, logX=logX, logZeroOffset=logZeroOffset)
def plotFitPoly(parms, min=None,max=None,step=None,hold=True,dataset=0,doFit=True,figureNo=None):#s='-', dataset=0, doFit=True, figureNo=None, logY=False, logX=False, logZeroOffset=.01):
    """
    if min is None defaults to min-x of current plot (dataset 0)
    if max is None defaults to max-x of current plot (dataset 0)
    if step is None defautls to 1000 points between min and max
    if hold is not None call Y.plothold(hold) beforehand
    """
    from . import useful as U
    return plotFitAny(U.yPoly, parms, min,max,step,hold,dataset,doFit, figureNo)#s, dataset, doFit, figureNo=figureNo, logY=logY, logX=logX, logZeroOffset=logZeroOffset)


def plotHistogram(a, nBins=None, amin=None,amax=None, histArr=None, norm=False, cumsum=False, exclude_amax=False,
                  #c=plot_defaultStyle, logY=False, logX=False, hold=None, logZeroOffset=.01, figureNo=None):
                  color=None, hold=None, figureNo=None):
    """
    shortcut for Y.plotxy(U.histogramXY(a,...),...)
    """
    from .useful import histogramXY
    plotxy(histogramXY(a, nBins=nBins, amin=amin,amax=amax, histArr=histArr, norm=norm, cumsum=cumsum, exclude_amax=exclude_amax),
             color=color, hold=hold, figureNo=figureNo)#, logY=logY, logX=logX, hold=hold, logZeroOffset=logZeroOffset, figureNo=figureNo)
    
try:
    from .gridviewer import gridview
except ImportError:
    pass

#  try:
from .histogram import hist as histogram
from .mmviewer import mview
from .scalePanel import scalePanel
from .zslider import ZSlider

from .buttonbox import *
from .guiParams import guiParams

#HIST= #dictionary
#VIEW= #dictionary

''' 20080721 unused !?
def hist(viewer, resolution=0):
    """old"""
    import useful as U
    try:
        img  = viewer.m_imgArr
    except:
        img  = viewer.m_imgArrL[0] ## hack !
    mmms = U.mmms(img)
    if not resolution:
        resolution = int(mmms[1]-mmms[0]+2) # e.g. (8.8-0)
        if resolution > 10000:
            print "resolution (max-min = %d) limited to %d"%(resolution, 10000)
            resolution = 10000
        elif resolution < 1000: #CHECK
            resolution = 10000 # CHECK 

    a_h = U.histogram(img, resolution, mmms[0], mmms[1])
    h = histogram(a_h, mmms[0], mmms[1], "hist 4: " + viewer.GetParent().GetTitle())
    def a(l,r):
        try:
            viewer.changeHistogramScaling(l,r)
        except:
            pass
    h.doOnBrace = a
    #v.changeHistogramScaling(mmms[0],mmms[1])
    h.setBraces(mmms[0],mmms[1])
    h.fitXcontrast()
    return h


def vview(img, title='', size=None):
    """old"""

    from viewer import view as view2d

    if img.dtype.type == N.float64:
        print 'view Float as float32'
        return vview(img.astype(N.float32), title, size)
    if img.dtype.type == N.int32:
        print 'view int32 as int16'
        return vview(img.astype(N.int16), title, size)
    if img.dtype.type in (N.complex64,N.complex128) :
        print 'view abs'
        return vview(N.absolute( img ), title, size)

    if len( img.shape ) == 2:
        from Priithon import seb as S
        amin, amax, amean, astddev = S.mmms(img)
        v = view2d(img, title, size)
        import wx
        wx.Yield()
        try:
            v.changeHistogramScaling(amin,amax)
        except:
            print "-Error changeHistogramScaling", amin, amax
        h = hist( v )
        v.hist = h
        return v
    elif len( img.shape ) == 3:
        v = vview(img[0], title)

        v.autoHistUpdate = 1
        h = v.hist
        s = ZSlider(img.shape[0], "zslider 4 " + title)
        def f(newZ):
            imgZ = img[newZ]
            v.setImage( imgZ )

            if v.autoHistUpdate:
                from Priithon import seb as S
                mmms = S.mmms( imgZ )
                resolution = int(mmms[1]-mmms[0]+2)
                if resolution > 10000:
                    #print "resolution (max-min = %d) limited to %d"%(resolution, 10000)
                    resolution = 10000
                elif resolution < 1000: #CHECK
                    resolution = 10000 # CHECK 

                a_h = U.histogram(imgZ, resolution, mmms[0], mmms[1])
                h.setHist(a_h, mmms[0], mmms[1])

        s.doOnZchange = f
        return v
        
    else:
        print " ** what should I do with data - shape=", img.shape
'''

try:
    viewers
except:
    viewers=[]

from .splitND import run as view
from .splitND2 import run as view2


from .DragAndDrop import DropFrame
from .viewerRubberbandMode import viewerRubberbandMode as vROI

def vd(id=-1):
    """
    return data arr of viewer 'id'
    shortcut for: Y.viewers[id].data
    """
    v = viewers[id]
    return v.data

def vTransferFct(id=-1, execStr='', usingXX=True):
    """
    define custom transfer function:
    execStr is evaluted pixelwise
          (more precise: "vectorized" on all pixels (2d array) "in parallel")
    x : pixel value
    x0: left hist brace value ( as float(..) )
    x1: right hist brace value ( as float(..) )
    y:  result needs to get assigned to `y`

    string is evaluated in __main__ as globals
    empty evalStr deactivates custom transfer function (default)
    if result y is ndim 3 (col,y,x): y gets transposed to (y,x,rgb) and interpreted as RBG 

    if usingXX is True: `xx` can be used as shortcut for `N.clip((x-x0)/(x1-x0), 0, 1)`

    Examples:
    `y=N.clip((x-x0)/(x1-x0), 0, 1)`         #  equivalent to default
    `y=N.clip((x-x0)/(x1-x0))**.3, 0, 1)` # gamma value of .3

    NOTE: be care to not create errors ! 
      In case it happens, you will get error infinite messages,
      minimize window, and reset transfer functions quickly !!
    """
    
    vv = viewers[id].viewer
    vv.transferf = execStr
    vv.transferf_usingXX = usingXX
    #CHECK vv.colMap = None
    vv.m_imgChanged = True
    vv.Refresh(False)

def vTransferGamma(id=-1, gamma=.3):
    """
    set transfer function so that
    images gets displayed using given gamma value
    """
    if gamma == 1:
        vTransferFct(id, '')
    else:
        vTransferFct(id, 'y=N.clip(((x-x0)/(x1-x0))**%f, 0, 1)'%gamma, usingXX=False)


#  def viewfn(fn=''):
#   """open file fn memmapped and view it"""
#   if fn is None or fn == '':
#       fn = FN()
#   try:
#       import Mrc
#       a = Mrc.bindFile(fn)
#   except:
#       import sys
#       global _error, _error0  ## FIXME
#       _error0 = sys.exc_info()
#       _error = map(str, _error0)
#       print "*ERROR while opening file (see var _error)"
#       #self.window.WriteText("Error when opening: %s - %s" %\
#       #                      (str(e[0]), str(e[1]) ))
#   else:
#       view(a, '')


def vClose(id='all'):
    """
    close viewer with given id
    id can be a number, a sequence of numbers, or 'all'
    """
    if id is 'all':
        id  = list(range(len(viewers)))
    elif type(id) == int:
        id = [id]

    for i in id:
        v = viewers[i]
        if v:
            wx.GetTopLevelParent(v.viewer).Close()

def vReload(id=-1, autoscale=True):
    """
    "reload" image data from memory into gfx card
    """
    v = viewers[id]
    #vv = v.viewer
    #vv.OnReload()

    # we use setupHistArr=True  because image dtype might have changed
    v.helpNewData(doAutoscale=autoscale, setupHistArr=True)


def vInterpolationSet(v_ids=[-1], magnify=0, minify=0):
    """
    set interpolation mode for OpenGL textures
    magnify: used when "zoomed in": magnification > 1
    minify: used when "zoomed out": magnification < 1

    0: use intensity of "nearest pixel"
    1: use "linear intepolated" intensity of nearby pixels
    """
    if minify:
        minify = GL.GL_LINEAR
    else:
        minify = GL.GL_NEAREST
    if magnify:
        magnify = GL.GL_LINEAR
    else:
        magnify = GL.GL_NEAREST

    try:
        v_ids[0]
    except:
        v_ids = (v_ids,)
    for v_id in v_ids:
        vv=viewers[v_id].viewer
        vv.SetCurrent()
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER, magnify)
        GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MIN_FILTER, minify)
        vReload(v_id, 0)

        


def vArrange(idxs=-1, nx=4, refSizeId=None, doCenter=1, x0=0, y0=0):
    """
    move viewer windows on screen to layout in order on a grid
    nx viewers per row (left to right)
    as many columns as needed
    """
    if idxs==-1:
        idxs = list(range(len(viewers)))
    first = 1
    x,y = x0,y0
    ix,iy = 0,0
    hh=0
    if refSizeId != None:
        s = wx.GetTopLevelParent(viewers[refSizeId].viewer).GetSize()
    for i in idxs:
      try:  
        f = wx.GetTopLevelParent(viewers[i].viewer)
        f.SetPosition( (x,y) )
        if refSizeId != None:
            f.SetSize(s)
        if doCenter:
            wx.Yield()  # CHECK ... FIXME:  HistogramCanvas.OnSize: self.m_w <=0 or self.m_h <=0 170 -2
            viewers[i].viewer.center()
        #f.Raise()
        fl = f
        

        
        h = f.GetSize()[1]
        if hh< h:
            hh=h
        ix += 1
        if ix == nx:
            ix = 0
            x = 0
            iy+=1
            y += hh
        else:
            x += f.GetSize()[0]
      except:
        pass
    rrr = list(idxs)
    rrr.reverse()
    for i in rrr:
      try:
        f = wx.GetTopLevelParent(viewers[i].viewer)
        f.Raise()
      except:
        pass


def vHistSettings(id_src=-2, id_target=-1):
    """
    copy settings from one viewer (viewer2) to another
    """
    from Priithon import splitND
    from Priithon import splitND2
    #isinstance(v, splitND.spv)
    spvFrom=viewers[id_src]
    spvTo = viewers[id_target]

    if spvFrom.__class__ is spvTo.__class__ is splitND2.spv:

        #Y.clipboardSetText([i[4:9] for i in v.viewer.m_imgList], 1)

        #self.m_imgList = [] # each elem.:
        ## 0       1        2       3            4     5   6 7 8   9, 10,11, 12
        ##[gllist, enabled, imgArr, textureID, smin, smax, r,g,b,  tx,ty,rot,mag]

        #li = eval(Y.clipboardGetText().rstrip())
        for i,l in enumerate(spvFrom.viewer.m_imgList):
            spvTo.hist[i].m_sx, spvTo.hist[i].m_tx = spvFrom.hist[i].m_sx, spvFrom.hist[i].m_tx
            spvTo.hist[i].zoomChanged=True
            sss = spvFrom.hist_show[i]
            spvTo.hist_show[i] = sss
            spvTo.hist_toggleButton[i].SetValue( sss )
            spvTo.OnHistToggleButton(i=i)

            #vv.changeHistScale(i, l[0],l[1])
            spvTo.setColor(i, l[6:9], RefreshNow=False)
            spvTo.hist[i].setBraces(spvFrom.hist[i].leftBrace, spvFrom.hist[i].rightBrace)

        spvTo.viewer.Refresh(0)
        spvTo.viewer.GetParent().Refresh(0)

    elif spvFrom.__class__ is spvTo.__class__ is splitND.spv:
        vh = spvFrom.hist
        spvTo.hist.m_sx, spvTo.hist.m_tx = spvFrom.hist.m_sx, spvFrom.hist.m_tx
        spvTo.hist.zoomChanged=True
        amin,amax =  vh.leftBrace, vh.rightBrace
        #spvTo.hist.autoFit(None, amin, amax)
        spvTo.hist.setBraces(amin,amax)
        vColMap(id_target, spvFrom.viewer.colMap)

    else:
        raise ValueError("src and target are different type viewers (%s vs. %s)" %(spvFrom.__class__, spvTo.__class__))

def vGetZSecTuple(id=-1):
    """
    return values of all z-sliders of a given viever as a tuple
    """
    return tuple(viewers[id].zsec)


def vShortcutAdd(id=-1, key=' ', func='Y.wx.Bell()', mod=0):
    """
    appends entry to keyShortcutTable of specified viewer

    key: keyCode (an int) or a char (implicit call of ord(key))
         (lower and upper case are automagically fixed up using SHIFT modifier)
    flags: wx.MOD_NORMAL(0), wx.MOD_ALT(1),wx.MOD_CTRL(2),wx.MOD_SHIFT(2)
    func: function (no args) to call on presseing shortcut key
         if type(func)== str: use exec func in __main__
    """
    v = viewers[id]

    if isinstance(key, six.string_types):
        if key.isupper():
            mod = mod | wx.MOD_SHIFT
        if key.islower():
            key = key.upper()

        key = ord(key)

    if type(func) == str:
        def shortcutFunc():
            import __main__
            exec(func, __main__.__dict__)
    else:
        shortcutFunc = func

    v.keyShortcutTable[ mod, key ] = shortcutFunc

def vShortcutReset(id=-1):
    """
    reset keyShortcutTable of specified viewer to default 
      (FIXME: 'Cmd-W' for closeWindow missing) accel 7777
    """
    v = viewers[id]
    v.keyShortcutTable.clear()

    v.setDefaultKeyShortcuts()
    
def vZoom(v_id, zoomfactor=None, cyx=None, absolute=True, refreshNow=True):
    """
    change zoom settings of viewer id

    depending on `absolute` the new zoom is set to
    zoomfactor or to "currentZoom"*zoomfactor repectively
    if zoomfactor is None:
        zoomfactor stays unchanged

    if cyx is None:
        image center stays center
    otherwise, image will get "re-centered" to cyx beeing the new center
    """
    if type(v_id)  is int:
        v_id = viewers[v_id].viewer

    v_id.zoom(zoomfactor, cyx, absolute, refreshNow)
def vZoomGet(v_id, returnCYX=False):
    """
    return zoomValue and (optionally) image center as shown in viewer id
    if returnCYX:
      return zoomValue, N.array((cy,cx))
    else:
      return zoomValue
    """
    if type(v_id)  is int:
        v_id = viewers[v_id].viewer

    if returnCYX:
        cx=(v_id.m_w/2.-v_id.m_x0) / v_id.m_scale
        cy=(v_id.m_h/2.-v_id.m_y0) / (v_id.m_scale*v_id.m_aspectRatio)
        return v_id.m_scale, N.array((cy,cx))
    else:
        return v_id.m_scale

def vHistScale(id=-1, amin=None, amax=None, autoscale=True):# refreshNow=True):
    """
    set new intensity scaling values
    None mean lowest / highest intensity for min / max respectively
    autoscale: scale displayed range to new left and right braces
    """
    v = viewers[id]
    vh = v.hist
    vh.autoFit(None, amin, amax, autoscale=autoscale)

def vHistScaleGet(id=-1):
    """
    return current leftBrace and rightBrace values used in given viewer
    """

    v = viewers[id]
    vh = v.hist
    return vh.leftBrace, vh.rightBrace

def vHistScale2(id=-1, channel=None, amin=None, amax=None, autoscale=True):# refreshNow=True):
    """
    set new intensity scaling values for a view2 viewer
    if channel is None - set all channels - otherwise only the given channel
    amin, amax:
    None mean lowest / highest intensity for min / max respectively
    autoscale: scale displayed range to new left and right braces
    """
    v = viewers[id]
    if channel is None:
        for ch in range(v.nColors):
            vHistScale2(id=id, channel=ch, amin=amin, amax=amax, autoscale=autoscale)
        return

    vh = v.hist[channel]
    #CHECK
    #     if amin is None:
    #         amin = v.mmms[ch][0]
    #     if amax is None:
    #         amax = v.mmms[ch][1]
    #     vh.setBraces(amin,amax)
    vh.autoFit(None, amin, amax, autoscale)

def vHistScale2Get(id=-1, channel=None):
    """
    return current leftBrace and rightBrace values used in given viewer2 
    for the given channel; 
    if channel is None a list of tuples for all channels is returned
    """
    v = viewers[id]
    if channel is not None:
        vh = v.hist[channel]
        return vh.leftBrace, vh.rightBrace
    else:
        return [(vh.leftBrace, vh.rightBrace) for vh in v.hist]

def vTitleGet(id=-1):
    """
    return title of given viewer window
         (excluding the the leading "1) " part)
    """
    v = viewers[id]
    return v.title

def vTitleSet(id=-1, title=""):
    """
    set title of given viewer window
    the actual text appearing in the frame's title bar will be
    e.g. '1) title' if id=1
    """

    v = viewers[id]
    if id < 0:
        id += len(viewers)
    title2 = "%d) %s" %(id, title)
    v.title = title
    v.title2 = title2
    wx.GetTopLevelParent(v.viewer).SetTitle(title2)

def vColMap(id=-1, colmap="", reverse=0):
    """
    set color map for given viewer
    colmap should be a string; one of:
      ''   <no color map>
      lo[g]       log-scale
      mi[nmaxgray] (both mi or mm work)
      bl[ackbody]
      ra[inbow]
      wh[eel] red-green-blue-red
      wh[eel]XX  (last two characters must be digits: number-of-wheel-cycles)
      
      (only first two letters are checked)

    if colmap is a numpy array, the array is used directly as colmap
       it should be of shape (3, 256)
    """
    v = viewers[id].viewer
    if isinstance(colmap, six.string_types):
        colmap = colmap.lower()
        if colmap == "":
            v.cmnone()
        elif   colmap.startswith("bl"):
            v.cmblackbody(reverse=reverse)
        elif colmap.startswith("ra"):
            v.cmcol(reverse=reverse)
        elif colmap.startswith("lo"):
            v.cmlog()
        elif colmap.startswith("mm") or colmap.startswith("mi"):
            v.cmGrayMinMax()
        elif colmap.startswith("wh"):
            try:
                cycles = int(colmap[-2:])
            except:
                cycles = 1
            v.cmwheel(cycles=cycles)
    elif isinstance(colmap, N.ndarray):
        #20080407  v.colMap = N.zeros(shape=(3, v.cm_size), dtype=N.float32)
        #20080407 v.colMap[:] = colmap
        v.colMap = colmap.copy()

        v.changeHistogramScaling()
        v.updateHistColMap()
# v.cmgray(gamma=1)
# v.cmgray(gamma=12)
# v.cmgray(gamma=.3)
# v.cmgrey(reverse=0)
# v.cmgrey(reverse=1)
# v.cms(colseq=['darkred', 'red', 'orange', 'yellow', 'green', 'blue', 'darkblue', 'violet'], reverse=0)
# v.cms(colseq=['darkred', 'red', 'orange', 'yellow', 'green', 'blue', 'darkblue', 'violet'], reverse=1)

def vSetSlider(v_id=-1, z=0, zaxis=0, autoscale=False): #, refreshNow=False)
    """
    zaxis specifies "which" zaxis should moved to new value z
    """
    if type(v_id)  is int:
        v_id = viewers[v_id]
    v_id.setSlider(z, zaxis)

    if autoscale:
        #20090109     vScale(v_id)
        print("#DEBUG - FIXME 20090109 - autoscale=True in Y.setSlider somehow not implemented....")
def vSetAspectRatio(v_ids=[-1], y_over_x=1, refreshNow=1):
    """
    strech images in y direction
    use negative value to mirror

    if v_ids is a scalar change only for that viewer, otherwise for all viewers in that list
    """
    try:
        v_ids[0]
    except:
        v_ids = (v_ids,)
    for v_id in v_ids:
        vs=viewers[v_id]
        vs.viewer.setAspectRatio(y_over_x, refreshNow)

def vSetCoordsDisplayFormat(v_id=-1, showAsFloat=False, width=None):
    """
    change format of coordinate / value info at to of viewer
    showAsFloat: True / False -- to show decimal x,y coordinates
    width: pixel width reserved for info text (-1 for "default")

    either value can be None to left unchanged
    """
    if type(v_id)  is int:
        v_id = viewers[v_id]
    
    if showAsFloat is not None:
        v_id.showFloatCoordsWhenZoomingIn = showAsFloat
    if width is not None:
        i=len(v_id.boxAtTop.GetChildren())-1
        v_id.boxAtTop.SetItemMinSize(i, (width,-1))
        v_id.boxAtTop.Layout()

def vCenter(v_id=-1, refreshNow=True):
    """
    move displayed image into center of 'visible' area of given viewer
    """
    if type(v_id)  is int:
        v_id = viewers[v_id].viewer
    v_id.center(refreshNow)

def vReadRGBviewport(v_id=-1, clip=False, flipY=True):
    """
    return returns array with r,g,b values from "what-you-see"
       shape(3, height, width)
       dtype=uint8

       v_id is either a number (the "viewer-ID")
               or a "viewer"-object
    """
    if type(v_id)  is int:
        v_id = viewers[v_id].viewer

    return v_id.readGLviewport(clip=clip, flipY=flipY)
        
def vSaveRGBviewport(v_id, fn, clip=True, flipY=True):
    """
    save "what-you-see" into RGB file of type-given-by-filename

       v_id is either a number (the "viewer-ID")
               or a "viewer"-object
    """
    if type(v_id)  is int:
        v_id = viewers[v_id].viewer
    
    from . import useful as U
    a = v_id.readGLviewport(clip=clip, flipY=flipY, copy=True)

    U.saveImg(a, fn)

def vCopyToClipboard(v_id=-1, clip=True):
    """
    copies image as seen on screen into clipboard
    if clip is True, clip backgound
    """
    if type(v_id)  is int:
        v_id = viewers[v_id].viewer

    aa = v_id.readGLviewport(clip=clip, flipY=True, copy=0)
    ny,nx = aa.shape[-2:]

    im = wx.ImageFromData(nx,ny,aa.transpose((1,2,0)).tostring())
    #test im.SaveFile("clipboard.png", wx.BITMAP_TYPE_PNG)
    bi=im.ConvertToBitmap()
    bida=wx.BitmapDataObject(bi)
    if not wx.TheClipboard.Open():
        raise RuntimeError("cannot open clipboard")
    try:
        success = wx.TheClipboard.SetData(bida)
        # success seems to be always True
        #on OS-X (10.5) success is True but nothing in clipboard .... print success
    finally:
        wx.TheClipboard.Close()

def vresizeto(refId=0, idxs=-1, nx=4):
    if idxs==-1:
        idxs = list(range(555))
    s = wx.GetTopLevelParent(viewers[refId].viewer).GetSize()
    
    for i in idxs:
      try:
        f = wx.GetTopLevelParent(viewers[i].viewer)
        #f.Raise()
        f.SetSize(s)
      except:
        pass
    rrr = list(idxs)
    rrr.reverse()
    for i in rrr:
      try:
        f = wx.GetTopLevelParent(viewers[i].viewer)
        f.Raise()
      except:
        pass

def vRotate(v_id, angle=None):
    """
    set displaying-rotation for viewer v_id
    if angle is None open slider GUI

    v_id is either a number (the "viewer-ID")
         or a "viewer"- or a "spv"-object
    """
    if type(v_id)  is int:
        spv = viewers[v_id]
    elif hasattr(v_id, "my_spv"):
        spv = v_id.my_spv
    else:
        spv=v_id
    
    if angle is not None:
        spv.viewer.setRotation(angle)
    else:
        viewerID = spv.id
        class _xx:
            pass
            def flip(self, x):
                self.v.m_aspectRatio *= -1
                self.v.m_y0 -= self.v.pic_ny * self.v.m_scale * self.v.m_aspectRatio
                #if x:
                #else:
                #    self.v.m_y0 -= self.v.pic_ny * self.m_scale * self.v.m_aspectRatio
                    
                self.v.m_zoomChanged=1
                self.v.Refresh(0)
                    
        xx = _xx()
        xx.v = spv.viewer
        xx.tc = 0 # text-change triggered event -- prevent calling circle when txt.SetValue() triggers text-change-event
        # note: first call of onText happend before sli is made
        buttonBox([
                ('c x.SetValue(v.m_aspectRatio<0)\tflip', "_.flip(x)", 0),
                ('l\tangle:', '', 0),
                ('t _.txt=x\t0',         "y=(len(x) or 0) and int(x);_.tc or (hasattr(_,'sli') and sli.SetValue(y));v.setRotation(y);_.tc=0", 0),
                ('sl _.sli=x\t0 0 360', "txt.SetValue(str(x));_.tc=1")],
                  title="rotate viewer %s"%(viewerID,),
                  execModule=xx)

def vzslider(idxs=None, nz=None, title=None):
    """
    show a "common slider" window
    for synchronous z-scrolling through multiple viewer
    idxs is list of indices
    if idxs is None, synchronize all open viewers
    if an index in idxs is given as tuple, it means (viewerID, zaxis)
    default is zaxis=0 otherwise
    """
    if idxs==None:
        idxs = [i for i in range(len(viewers)) if viewers[i] is not None]
    if title is None:
        title = "slide:" + str(idxs)

    if nz is None:
        nz=1
        for i in idxs:
            try:
                i,zaxis = i
            except:
                zaxis=0
            try:
                v = viewers[i]
                if v.zshape[zaxis] > nz:
                    nz = v.zshape[zaxis]
            except:
                pass
    def onz(z):
        for i in idxs:
            try:
                i,zaxis = i
            except:
                zaxis=0
            try:
                v = viewers[i]
                v.setSlider(z, zaxis)
            except:
                pass
    zs = ZSlider(nz, title)
    zs.doOnZchange.append( onz )


def vClearGraphics(id=-1):
    v = viewers[id]
    vv = v.viewer
    def ff0():
        pass
    vv.updateGlList( ff0 )
    vv.SetToolTipString('')


def vLeftClickMarks(id=-1, callFn=None):
    def fg(x,y):
        glCross(int(x), int(y), length=50, color=PriConfig.defaultGfxColor)

    vLeftClickDoes(id, fg, callFn)


_plotprofile_avgSize=1


def vLeftClickHorizProfile(id=-1, avgBandSize=1, s='-'):
    v = viewers[id]
    h,w = v.img.shape

    global _plotprofile_avgSize
    _plotprofile_avgSize = avgBandSize

    def f(x,y):
        if _plotprofile_avgSize >1:
            vals = N.sum( v.img[ y:y+_plotprofile_avgSize ].astype(N.float64), 0 ) / float(_plotprofile_avgSize)
            ploty( vals, symbolSize=0)#s )
        else:
            ploty( v.img[ y ], symbolSize=0)#s )
    def fg(x,y):
        if _plotprofile_avgSize >1:
            glLine(0,y,w,y, PriConfig.defaultGfxColor)
            glLine(0,y+_plotprofile_avgSize,w,y+_plotprofile_avgSize, PriConfig.defaultGfxColor)
        else:
            glLine(0,y+.5,w,y+.5, PriConfig.defaultGfxColor)

    vLeftClickDoes(id, callGlFn=fg, callFn=f)

def vLeftClickVertProfile(id=-1, avgBandSize=1, s='-'):
    v = viewers[id]
    h,w = v.img.shape

    global _plotprofile_avgSize
    _plotprofile_avgSize = avgBandSize

    def f(x,y):
        if _plotprofile_avgSize >1:
            vals = N.sum( v.img[ :, x:x+_plotprofile_avgSize ].astype(N.float64), 1 ) / float(_plotprofile_avgSize)
            ploty( vals, symbolSize=0)#s )
        else:
            ploty( v.img[ :, x ], symbolSize=0)#s )
    def fg(x,y):
        if _plotprofile_avgSize >1:
            glLine(x,0,x,h, PriConfig.defaultGfxColor)
            glLine(x+_plotprofile_avgSize,0,x+_plotprofile_avgSize,h, PriConfig.defaultGfxColor)

        else:
            glLine(x+.55555,0,x+.55555,h, PriConfig.defaultGfxColor)

    vLeftClickDoes(id, callGlFn=fg, callFn=f)

def vLeftClickZProfile(id=-1, avgBoxSize=1, s='-', slice=Ellipsis):
    v = viewers[id]

    data = v.data[slice]

    if data.ndim != 3:
        raise ValueError("ZProfile only works for 3D data (TODO: for 4+D)")
    nz = data.shape[0]

    global _plotprofile_avgSize # 20051025
    _plotprofile_avgSize = avgBoxSize # 20051025

     # 20051025 if avgBoxSize >1:
    v.polyLen = 2
    v.polyI = 0
    v.poly = N.zeros(2*v.polyLen, N.float64)
        
    def f(x,y):
        if _plotprofile_avgSize >1:
            w,h = _plotprofile_avgSize,_plotprofile_avgSize
            w2,h2 = w/2., h/2.
            v.poly[:] = x0,y0,x1,y1 = int(x-w2+.5),int(y-h2+.5),  int(x+w2+.5),int(y+h2+.5)
            from .useful import mean2d
            prof = N.empty(shape=nz, dtype=N.float)
            for z in range(nz):
                prof[z] = data[z,  y0:y1, x0:x1].mean()
            #prof = mean2d(a[:,  y0:y1, x0:x1])   ##->  TypeError: Can't reshape non-contiguous numarray
            ploty( prof, symbolSize=0)#s )
        else:
            ploty( data[ :, int(y), int(x) ], symbolSize=0)#s )
    def fg(x,y):
        if _plotprofile_avgSize >1:
            x0,y0,x1,y1 = v.poly
            glBox(x0,y0,x1,y1, PriConfig.defaultGfxColor)
        else:
            glCross(int(x)+0.55555, int(y)+0.55555, length=50, color=PriConfig.defaultGfxColor)
    vLeftClickDoes(id, callGlFn=fg, callFn=f, roundCoords2int=(_plotprofile_avgSize==0))

def vLeftClickLineProfile(id=-1, abscissa='line', s='-'):
    """abscissa can be
    'x'       to plot intensity along line against x-coordinate
    'y'       against y-coord
    else      against length
    """
    v = viewers[id]

    v.polyLen = 2
    v.polyI = 0
    v.poly = N.zeros(2*v.polyLen, N.float64)
    def f(x,y):
        v.poly[2*v.polyI : 2*v.polyI+2] = x,y # int(x) +.5, int(y) +.5
        v.polyI = (v.polyI+1) % v.polyLen

        x0,y0,x1,y1 = v.poly
        dx,dy = x1-x0, y1-y0

        l = N.sqrt(dx*dx + dy*dy)
        if l>1:
            ddx = dx/l
            ddy = dy/l
            #print dx,dy,l, x0,y0,x1,y1
            xs = list(map(int, N.arange(x0, x1, ddx)+.5))
            ys = list(map(int, N.arange(y0, y1, ddy)+.5))
            #print len(xs), len(ys)
            try:
                vs = v.img[ ys,xs ]
                if abscissa == 'x':
                    plotxy(xs, vs, s)#symbolSize=0)#s)
                elif abscissa == 'y':
                    plotxy(ys, vs, s)#symbolSize=0)#s)
                else:
                    ploty(vs, s)#symbolSize=0)#s)
            except:
                raise #print "line profile bug:", len(xs), len(ys)

        #print v.poly
        
    def fg(x,y):
        x0,y0,x1,y1 = v.poly
        glLine(x0,y0,x1,y1, PriConfig.defaultGfxColor)

    vLeftClickDoes(id, callGlFn=fg, callFn=f)







def vLeftClickLineMeasure(id=-1, roundCoords2int=False):
    v = viewers[id]

    v.polyLen = 2
    v.polyI = 0
    v.poly = N.zeros(2*v.polyLen, N.float64)
    def f(x,y):
        v.poly[2*v.polyI : 2*v.polyI+2] = x,y # int(x) +.5, int(y) +.5
        v.polyI = (v.polyI+1) % v.polyLen

        x0,y0,x1,y1 = v.poly
        dx,dy = x1-x0, y1-y0

        s = "length: %s" % (N.sqrt(dx*dx+dy*dy), )
        print(s)
        v.viewer.SetToolTipString(s)
        
    def fg(x,y):
        x0,y0,x1,y1 = v.poly
        glLine(x0,y0,x1,y1, PriConfig.defaultGfxColor)

    vLeftClickDoes(id, callGlFn=fg, callFn=f,roundCoords2int=roundCoords2int)


def vLeftClickTriangleMeasure(id=-1, roundCoords2int=0):
    v = viewers[id]

    v.polyLen = 3
    v.polyI = 0
    v.poly = N.zeros(2*v.polyLen, N.float64)
    def f(x,y):
        v.poly[2*v.polyI : 2*v.polyI+2] = x,y # int(x) +.5, int(y) +.5
        v.polyI = (v.polyI+1) % v.polyLen

        x0,y0,x1,y1,x2,y2 = v.poly
        dx21,dy21 = x1-x0, y1-y0
        dx31,dy31 = x2-x0, y2-y0
        dx32,dy32 = x2-x1, y2-y1

        a2,b2,c2 =  \
                 dx21**2 + dy21**2, \
                 dx31**2 + dy31**2, \
                 dx32**2 + dy32**2

        try:
            R = N.sqrt(        a2*b2*c2  / \
                                (-a2**2 + 2*a2*b2 - b2**2 + 2*a2*c2 + 2*b2*c2 - c2**2) \
                                )

            px,py = x0+dx21/2.  ,  y0+dy21/2.
            poLen = N.sqrt(1-b2/4*R*R) * R

            #nnx     = dx21
            #cx,cy 

        
            area = N.abs(dx21*dy31-dy21*dx31) / 2.

            if area > 0:
                a21 = x1*x1-x0*x0 + y1*y1-y0*y0
                a32 = x2*x2-x1*x1 + y2*y2-y1*y1         

                yyc = ( a21/(2.*dx21*dy21) - a32/(2.*dx32*dy21) ) \
                       / (1.-(dy32/dy21))

                yyc = .5 * ( a32/dx32 - a21/dx21 ) \
                         /( dy32/dx32 - dy21/dx21 )

                xxc = .5*a21/dx21 - yyc*dy21/dx21




                #print "area: %.2f   radius: %.2f    CX,CY: %5.1f %5.1f" % \
                #     (area, R,cx,cy)

                # s=    "outerCircle=> area: %.2f   radius: %.2f   diameter: %.2f" %      (area, R, 2*R)
                # s=    "outerCircle=> area: %.2f   r: %.2f  diameter: %.2f" %    (area, R, 2*R)
                s= "outerCircle=> cx,cy: %.1f %.1f   r: %.1f  diameter: %.1f" %       (xxc,yyc, R, 2*R)
            else:
                s= "outerCircle=> area: %.2f" % (area,)
            print(s)
            v.viewer.SetToolTipString(s)
        except ZeroDivisionError:
            pass
        
    def fg(x,y):
        x0,y0,x1,y1,x2,y2 = v.poly
        color=PriConfig.defaultGfxColor
        #20050520 GL.glDisable(GL.GL_TEXTURE_2D)
        GL.glColor( color )
        GL.glBegin( GL.GL_LINE_LOOP )
        GL.glVertex2f( x0,y0 )
        GL.glVertex2f( x1,y1 )
        GL.glVertex2f( x2,y2 )
        GL.glEnd()
        #20050520 GL.glEnable( GL.GL_TEXTURE_2D)


    vLeftClickDoes(id, callGlFn=fg, callFn=f, roundCoords2int=roundCoords2int)













def vLeftClickBox(id=-1, fixSize=None, roundCoords2int=1):
    """
    if fixSize is None:
       every click sets one corner (the opposite corner from last click)
    if    fixSize is   (width,height)-tuple
    or if fixSize is   scalar (box is square)
        every click sets center
    """
    v = viewers[id]
    h,w = v.img.shape

    v.polyLen = 2
    v.polyI = 0
    v.poly = N.zeros(2*v.polyLen, N.float64)
    def f(x,y):
        if fixSize is None:
            if roundCoords2int:
                x,y = int(x+.5), int(y+.5)
            v.poly[2*v.polyI : 2*v.polyI+2] = x,y # int(x) +.5, int(y) +.5
            v.polyI = (v.polyI+1) % v.polyLen

        else:
            try:
                w,h = fixSize
            except:
                w,h = fixSize,fixSize

            w2,h2 = w/2., h/2.
            if roundCoords2int:
                v.poly[:] = int(x-w2+.5),int(y-h2+.5),      int(x+w2+.5),int(y+h2+.5)
            else:
                v.poly[:] = x-w2,y-h2,      x+w2,y+h2

        
    def fg(x,y):
        x0,y0,x1,y1 = v.poly
        glBox(x0,y0,x1,y1, PriConfig.defaultGfxColor)

    vLeftClickDoes(id, callGlFn=fg, callFn=f, roundCoords2int=0)





def vLeftViewSubRegion(id=-1, color=False, gfxWhenDone='hide'):
    """
    use left mouse button to select a square sub region in viewer "id"
    a new Y.view window will show that region

    if color, use Y.view2 instead of Y.view

    gfxWhenDone should be one of: 'hide', 'remove', None
    """
    if id <0:
        id += len(viewers)
    v = viewers[id]
    rub = vROI(id,
               rubberWhat="box",
               color=(0, 1, 0),
               gfxWhenDone=gfxWhenDone)

    if color:
        viewCmd=view2
    else:
        viewCmd=view

    def doThisAlsoOnDone():
        y0,x0 = rub.yx0
        y1,x1 = rub.yx1
        viewCmd( v.data[..., y0:y1+1,x0:x1+1],
              title="%s [...,%d:%d,%d:%d]" % (v.title, y0,y1+1,x0,x1+1) )
        vHistSettings(id,-1)
    rub.doThisAlsoOnDone = doThisAlsoOnDone
    






def vLeftClickDoes(id=-1, callGlFn=None, callFn=None, roundCoords2int=True):
    """
    register left-click handler functions for viewer id
    for v=viewers[id] v.lastLeftClick_atYX  gets set to remember 
        the y,x coordinates of the last click (as N.array)

    if callGlFn is not None: function to be called with arguments x,y (in that order!)  
                 this is to be used to set up a GL list 
    if callFn is not None: function to be called with arguments x,y (in that order!) 

    if roundCoords2int  coordinates are integers, 
           otherwise float (first pixel is between -.5 .. +.5)
    """
    v = viewers[id]
    vv = v.viewer

    if callGlFn is None:
        def x(x,y):
            pass
        callGlFn = x

    def fff(x,y, ev):
        if roundCoords2int:
            x = int(round(x))
            y = int(round(y))
        #20060726 v.data.x = x
        #20060726 v.data.y = y
        import numpy as N
        v.lastLeftClick_atYX = N.array((y,x)) #20060726 
        def ff0():
            callGlFn(x,y)
            
        if callFn is not None:
            callFn(x,y)
        vv.updateGlList( ff0)

    #20080707 vv.doLDown = fff
    _registerEventHandler(vv.doOnLDown, newFcn=fff, newFcnName='vLeftClickDoes')

def vLeftClickNone(id=-1, delAll=False):
    """
    unregister left-click handler functions for viewer id
    there were registered via vLeftClickDoes

    if delAll: unregister all, otherwise only the last such function
    """
    #vLeftClickDoes(id,None,None)
    v = viewers[id]
    vv = v.viewer
    #20080707 def x(x,y):
    #20080707         pass
    #20080707 vv.doLDown = x 

    _registerEventHandler(vv.doOnLDown, oldFcnName='vLeftClickDoes', delAll=delAll)




def vAddGraphics(id, fn): #, where=1):
    """ try e.g. fn=lambda:Y.glCircle(100,100)
    #   where:  1 - append
#          -1 - prepend
#          0  - remove old graphics

if fn is a list of functions each gets called

    Note: remember ... doesnt work in loop !?
    """
    v = viewers[id]
    vv = v.viewer

#   try:
#       n = len(fn)
#       fffn=fn
#       def fn():
#           for f in fffn:
#               f()
#   except:
#       pass

#   old_defGlList = vv.defGlList
#
#
#   if where == 1:
#       def ff0():
#           old_defGlList()
#           fn()
#   elif where == -1:
#       def ff0():
#           fn()
#           old_defGlList()
#   else:
#       def ff0():
#           fn()

    vv.addGlList( fn  )
    

# vFollowMouse: connect mouse pointer of XY-view with a 
#    "moving cross" in other XY or XZ views of same data set
#               disconnect mouse pointer again, if xyViewers=xzViewers=yzViewers=[]

# vgMarkIn3D: place marker at 3D position, 
#      above and below markerZ show marker in different color 
#      default: green above (z+), red below (z-)
#      outside z +/- zPlusMinus: don't show marker at all - default: zPlusMinus=1000

def vFollowMouse(v_id, xyViewers=[], xzViewers=[], yzViewers=[],
                 zAxis=0, crossColor=PriConfig.defaultGfxColor, setSliderInXYviewers=True, 
                 followZoomInXYviewers=True, followZoomInSideviewers=True):
    """
    if viewer v_id has more than one z-slider, 
       zAxis specifies which zaxis of v_id to use for z coordinate in xz-,yz-Viewers

    if all lists (xyViewers, xzViewers and yzViewers) are empty, 
    reset v_id  to NOT follow mouse cursor

    TODO: FIXME: cyclic - recursive calls through setslider .... (20080902)
    """
    if not hasattr(xyViewers, '__len__'):
        xyViewers = [xyViewers]
    if not hasattr(xzViewers, '__len__'):
        xzViewers = [xzViewers]
    if not hasattr(yzViewers, '__len__'):
        yzViewers = [yzViewers]

    v = viewers[v_id]

    if len(xyViewers)==len(xzViewers)==len(yzViewers)==0:
        _registerEventHandler(v.viewer.doOnMouse, oldFcnName='vFollowMouse')
        _registerEventHandler(v.doOnSecChanged, oldFcnName='vFollowMouse')
        return
    last_X = [0]  # use a list here to get a mutable object
    last_Y = [0]  # use a list here to get a mutable object
    nx=v.data.shape[-1]
    ny=v.data.shape[-2]

    zAxisSliders=[]
    for vid in xzViewers:  # smart finding of which zSlider to use in that viewer
        v1 = viewers[vid]
        try:
            zaxis = list(v1.zshape).index(ny)
        except ValueError:
            zaxis=None
        zAxisSliders.append(zaxis)
                    
    xzViewers__zAxisSliders = list(zip(xzViewers, zAxisSliders))
    del zAxisSliders

    zAxisSliders=[]
    for vid in yzViewers:  # smart finding of which zSlider to use in that viewer
        v1 = viewers[vid]
        try:
            zaxis = list(v1.zshape).index(nx)
        except ValueError:
            zaxis=None
        zAxisSliders.append(zaxis)

    yzViewers__zAxisSliders = list(zip(yzViewers, zAxisSliders))
    del zAxisSliders

    def onMouseFollower(x,y, ev):
        last_X[0] = x
        last_Y[0] = y
        if len(xzViewers__zAxisSliders) or len(yzViewers__zAxisSliders):
            # zAxis might be (rather: *is*) "undefined" for 2D viewers -- no xz or yz viewers 
            z = v.zsec[zAxis]
        s=None
        if (followZoomInXYviewers or followZoomInSideviewers) and ev.GetEventObject().m_zoomChanged:
            s,cyx = vZoomGet(v_id, returnCYX=True)
        for vid in xyViewers:
           try:
               v1 = viewers[vid]
               vv = v1.viewer
               if ev.Leaving():
                   vgEnable(vv, idx='vFollowMouse', on=False)
               else:
                   if s is not None and followZoomInXYviewers:
                       vZoom(vv, s,cyx, refreshNow=False)
                   vgAddCrosses(vv, [(y,x,-10)], color=crossColor, idx='vFollowMouse')
                   #def ff0():
                   #    #Y.glCross(x+.5, y+.5, length=10, color=crossColor)
                   #    glPlus(x+.55555, y+.55555, length=10, color=crossColor)
                   #vv.updateGlList(ff0, refreshNow=True)

           except AttributeError: # viewer might have been closed
               pass

        for vid,zslider in xzViewers__zAxisSliders:
           try:
               v1 = viewers[vid]
               vv = v1.viewer
               if ev.Leaving():
                   vgEnable(vv, idx='vFollowMouse', on=False)
               else:
                   if s is not None and followZoomInXYviewers:
                       #s2,cyx2 = vZoomGet(vv, returnCYX=True)
                       #vZoom(vid, s,(cyx2[0], cyx[1]), refreshNow=False)
                       vZoom(vid, s,(z, cyx[1]), refreshNow=False)
                   vgAddCrosses(vv, [(z,x,-10)], color=crossColor, idx='vFollowMouse')
                   #def ff0():
                   #    glPlus(x+.55555, z+.55555, length=10, color=crossColor)
                   #vv.updateGlList(ff0, refreshNow=True)
                   if zslider is not None and 0<= y < ny:
                       if y != v1.zsec[zslider]: # having "if" prevents recursive calling
                           v1.setSlider(y,zslider)
           except AttributeError: # viewer might have been closed
               pass

        for vid,zslider in yzViewers__zAxisSliders:
           try:
               v1 = viewers[vid]
               vv = v1.viewer
               if ev.Leaving():
                   vgEnable(vv, idx='vFollowMouse', on=False)
               else:
                   if s is not None and followZoomInXYviewers:
                       #s2,cyx2 = vZoomGet(vv, returnCYX=True)
                       #vZoom(vid, s,(cyx2[0], cyx[1]), refreshNow=False)
                       vZoom(vid, s,(cyx[0], z), refreshNow=False)
                   vgAddCrosses(vv, [(y,z,-10)], color=crossColor, idx='vFollowMouse')
                   #def ff0():
                   #    glPlus(x+.55555, z+.55555, length=10, color=crossColor)
                   #vv.updateGlList(ff0, refreshNow=True)
                   if zslider is not None and 0<= x < nx:
                       if x != v1.zsec[zslider]: # having "if" prevents recursive calling
                           v1.setSlider(x,zslider)
           except AttributeError: # viewer might have been closed
               pass

        #TODO FIXME - if multiple viewers are "listed" only first one responds fast
        # 200902: COMMENT: was this a problem on XP - seems to work on OS-X
        #         def refreshAll():
        #             for vid,zslider in xzViewers__zAxisSliders:
        #                 viewers[vid].viewer.Refresh(0)
        #             for vid in xyViewers:
        #                 viewers[vid].viewer.Refresh(0)
        #         import wx
        #         wx.CallAfter(refreshAll)

    _registerEventHandler(v.viewer.doOnMouse, newFcn=onMouseFollower, newFcnName='vFollowMouse')

    if zAxis is not None and len(v.zsec):
        def doNewSec(zTup, self):
            x = last_X[0]
            y = last_Y[0]
            z = v.zsec[zAxis]
            if setSliderInXYviewers:
                for vid in xyViewers:
                    v1 = viewers[vid]
                    try:
                        if z != v1.zsec[zAxis]: # having "if" prevents recursive calling
                            v1.setSlider(z, zAxis)
                    except:
                        pass

            for vid,zslider in xzViewers__zAxisSliders:
                try:
                    v1 = viewers[vid]
                    vv = v1.viewer   
                    vgAddCrosses(vid, [(z,x,-10)], color=crossColor, idx='vFollowMouse')
                    #def ff0():
                    #    glPlus(x+.55555, z+.55555, length=10, color=crossColor)
                    #vv.updateGlList(ff0, refreshNow=True)
                except AttributeError: # viewer might have been closed
                   pass

            for vid,zslider in yzViewers__zAxisSliders:
                try:
                    v1 = viewers[vid]
                    vv = v1.viewer   
                    vgAddCrosses(vid, [(y,z,-10)], color=crossColor, idx='vFollowMouse')
                    #def ff0():
                    #    glPlus(x+.55555, z+.55555, length=10, color=crossColor)
                    #vv.updateGlList(ff0, refreshNow=True)
                except AttributeError: # viewer might have been closed
                   pass

        _registerEventHandler(v.doOnSecChanged,     newFcn=doNewSec,  newFcnName='vFollowMouse')

    
def vgMarkIn3D(v_id=-1, zyx = (None,200,200), kind='Cross', 
               s=4,
               zPlusMinus=9999,
               colAtZ   = (1,1,1),
               colLessZ = (1,0,0),
               colMoreZ = (0,1,0),
               widthAtZ   = 2,
               widthLessZ = 1,
               widthMoreZ = 1,
               name="mark3D",
               refreshNow=True
               ): # , zAxis = 0):
    """
    kind is one of 'Cross', 'Circle', 'Box'

    zyx is 3-tuple: if z is None use current

    col: color
    AtZ    - in Z section at z
    LessZ  - in Z section smaller than z
    MoreZ  - in Z section larger than z

    zPlusMinus - how many sections above/below z should be marked (at most)
    """
    v = viewers[v_id]
        
    nz = v.zshape[0]

    z,y,x = zyx
    yx=y,x

    z = int(z+.5)

    zShown = v.zsec[0]
    if z is None:
        z = zShown

    if kind.lower().startswith('ci'): 
        fffff=vgAddCircles
    if kind.lower().startswith('cr'): 
        fffff=vgAddCrosses
    if kind.lower().startswith('b'): 
        fffff=vgAddBoxes
        s *=.5

    z0 = z-zPlusMinus
    if z0<0:
        z0 = 0
    z1 = z+zPlusMinus
    if z1>nz:
        z1 = nz

    ids = []
    for i in range(z0,z):
        q=fffff(v_id, [yx], s, color=colLessZ, width=widthLessZ, 
                name=["markedIn3D", name,(i,)], idx=None, enable=i==zShown, refreshNow=False)
        ids.append(q)

    for i in range(z+1,z1):
        q=fffff(v_id, [yx], s, color=colMoreZ, width=widthMoreZ, 
                name=["markedIn3D", name,(i,)], idx=None, enable=i==zShown, refreshNow=False)
        ids.append(q)
        
    q=fffff(v_id, [yx], s, color=colAtZ, width=widthAtZ, 
            name=["markedIn3D", name,(z,)], idx=None, enable=z==zShown, refreshNow=refreshNow)
    ids.append(q)

    return ids











def vm(id):
    """return mountain viewer window of id"""
    return viewers[id].m
def vmScale(id, zscale):
    """scale mountain viewer window of id"""
    return viewers[id].m.setZScale(zscale)



from OpenGL import GL
# def glTex2Don():
#   pass# #20050520 GL.glEnable( GL.GL_TEXTURE_2D)
# def glTex2Doff():
#   pass# #20050520 GL.glDisable(GL.GL_TEXTURE_2D)
def glCross(x0,y0, length=50, color=None):
    if color is not None:
        GL.glColor( color )
    GL.glBegin( GL.GL_LINES )
    GL.glVertex2f( x0-length,y0-length )
    GL.glVertex2f( x0+length,y0+length )
    GL.glVertex2f( x0-length,y0+length )
    GL.glVertex2f( x0+length,y0-length )
    GL.glEnd()
def glPlus(x0,y0, length=50, color=None):
    if color is not None:
        GL.glColor( color )
    GL.glBegin( GL.GL_LINES )
    GL.glVertex2f( x0-length,y0 )
    GL.glVertex2f( x0+length,y0 )
    GL.glVertex2f( x0,y0-length )
    GL.glVertex2f( x0,y0+length )
    GL.glEnd()
def glLine(x0,y0,x1,y1, color=None):
    if color is not None:
        GL.glColor( color )
    GL.glBegin( GL.GL_LINES )
    GL.glVertex2f( x0,y0 )
    GL.glVertex2f( x1,y1 )
    GL.glEnd()

def glLineYxDyx(yx0,dyx, color=None):
    if color is not None:
        GL.glColor( color )
    GL.glBegin( GL.GL_LINES )
    GL.glVertex2f( float(yx0[1]), float(yx0[0]) ) ## using float() because SWIG<->numpy troubles: a 'float' is expected, 'numpy.float32(31.2506)' is received
    GL.glVertex2f( float(yx0[1]+dyx[1]), float(yx0[0]+dyx[0]) )## using float() because SWIG<->numpy troubles: a 'float' is expected, 'numpy.float32(31.2506)' is received
    GL.glEnd()

def glBox(x0,y0,x1,y1, color=None):
    if color is not None:
        GL.glColor( color )
    GL.glBegin( GL.GL_LINE_LOOP )
    GL.glVertex2f( x0,y0 )
    GL.glVertex2f( x0,y1 )
    GL.glVertex2f( x1,y1 )
    GL.glVertex2f( x1,y0 )
    GL.glEnd()

try:
    from glSeb import glCircle_seb
    def glCircle(x0,y0,r=10, nEdges=60, color=None):
        if color is not None:
            GL.glColor( color )
        glCircle_seb(x0,y0,r, nEdges)
except ImportError:
    def glCircle(x0,y0,r=10, nEdges=60, color=None):
        if color is not None:
            GL.glColor( color )

        ps = [(x0+r*N.cos(a),
                       y0+r*N.sin(a)) for a in N.arange(0,2*N.pi, 2*N.pi/nEdges)]
        GL.glBegin( GL.GL_LINE_LOOP )
        for x,y in ps:
            GL.glVertex2f( x,y )
        GL.glEnd()

try:
    from glSeb import glEllipse_seb
    def glEllipse(x0,y0,rx=10, ry=5, phi=0, nEdges=60, color=None):
        if color is not None:
            GL.glColor( color )
        glEllipse_seb(x0,y0,rx,ry,phi, nEdges)
except ImportError:
    def glEllipse(x0,y0,rx=10, ry=5, phi=0, nEdges=60, color=None):
        if color is not None:
            GL.glColor( color )
        ps = [(x0+rx*N.cos(a),
                       y0+ry*N.sin(a)) for a in N.arange(phi,phi+2*N.pi, 2*N.pi/nEdges)]
        GL.glBegin( GL.GL_LINE_LOOP )
        for x,y in ps:
            GL.glVertex2f( x,y )
        GL.glEnd()

#  except:
#   print " * trouble with OpenGL stuff"
#   import traceback
#   traceback.print_exc()

def glutText(str, posXYZ=None, size=None, mono=0, color=None, enableLineSmooth=False):
    """
    use GLUT to draw some text
    font type GLUT_STROKE_ROMAN      ( == 0) -> mono=0
    font type GLUT_STROKE_MONO_ROMAN ( == 1) -> mono=1
    if posXYZ is not None: posXYZ is EITHER (x,y) OR (x,y,z)
    if size is not None: set size scale (EITHER scalar, (sx,sy) or (sx,sy,sz)
       [GLUT stroke font size of 1 is 100 "pixels" high for the letter `A`]

    if color is not None: call glColor3f(color)
    if enableLineSmooth  bracket code with glEnable/glDisable GL_LINE_SMOOTH

    # GLUT_STROKE_ROMAN
    #         A proportionally spaced  Roman  Simplex  font  for
    #         ASCII  characters  32 through 127. The maximum top
    #         character in the font is 119.05 units; the  bottom
    #         descends 33.33 units.
    # GLUT_STROKE_MONO_ROMAN
    #         A  mono-spaced  spaced  Roman  Simplex  font (same
    #         characters as GLUT_STROKE_ROMAN) for ASCII charac-
    #         ters  32 through 127. The maximum top character in
    #         the font is  119.05  units;  the  bottom  descends
    #         33.33  units. Each character is 104.76 units wide.
    """
    from OpenGL import GLUT
    stroke = {0: GLUT.GLUT_STROKE_ROMAN,
              1: GLUT.GLUT_STROKE_MONO_ROMAN}
    if posXYZ is not None:
        try:
            x,y,z = posXYZ
        except:
            x,y = posXYZ
            z=0
    if color is not None:
        GL.glColor3fv( color )
    if enableLineSmooth:
        GL.glEnable(GL.GL_LINE_SMOOTH)
    GL.glPushMatrix()
    if posXYZ is not None:
        GL.glTranslatef(x, y, z)
    if size is not None:
        import numpy as N
        if N.isscalar(size): # type(size) == type(1) or type(size) == type(1.0):
            GL.glScale(size,size,size)
        elif len(size) == 2:
            GL.glScale(size[0],size[1],1)
        else:
            GL.glScale(size[0],size[1],size[2])

    for letter in str:
        try:
            strk = stroke[mono]
        except TypeError: # unhashable
            strk = mono
        GLUT.glutStrokeCharacter(strk, ord(letter))
    GL.glPopMatrix()
    if enableLineSmooth:
        GL.glDisable(GL.GL_LINE_SMOOTH)

def crust(showLinesNumbers=True, wrapLongLines=True):
    """open a new pyCrust terminal.
    this combines a shell with an inspect panel (and more)
    """
    #20070715 from wx import py
    #import py # from Priithon
    from wx import py
    f = py.crust.CrustFrame()
    #20070715(this somehow disappeared from editwindow.py) f.shell.setDisplayLineNumbers(showLinesNumbers)
    f.shell.wrap(wrapLongLines)
    f.Show(1)

def shell(showLinesNumbers=True, wrapLongLines=True, clone=False):
    """
    open a new pyShell terminal.
    if clone: new shell will be another (linked) "view" of main shell window
    """
    #20070715 from wx import py
    #import py # from Priithon
    from wx import py

    title = "Priithon shell"
    if clone:
        title += " (clone)"

    f = py.shell.ShellFrame( title=title )
    #20070715(this somehow disappeared from editwindow.py)     f.shell.setDisplayLineNumbers(showLinesNumbers)
    f.shell.wrap(wrapLongLines)

    if clone:
        import __main__
        f.shell.SetDocPointer(__main__.shell.GetDocPointer())

    f.Show(1)

def inspect(what=None):
    """
    open a new pyFilling window.
    this is what you want to investigate all the variables, modules,
    and more
    
    if what is None: defautls to `locals()` in `__main__` (i.e. `__main__.__dict__`)
    """
    #import py # from Priithon
    from wx import py

    if what is None:
        import __main__
        what = __main__
    #     import sys
    #     fr = sys._getframe(1)
    #     #print dir(fr)
    #     # fc = fr.f_code
    #     locs = fr.f_globals
    #     #print locs.keys()

    try:
        whatLabel=what.__name__
    except AttributeError:
        try:
            whatLabel=['__name__']
        except:
            whatLabel=None
    title = 'Inspect: %s'%whatLabel

    c = py.filling.FillingFrame(parent=None, id=-1,
                            title=title,
                            #####pos=wx.wxPoint(-1, -1),
                            #pos=wx.wxPoint(680, 0),
                            ######size=wx.wxSize(-1, -1),
                            #size=wx.wxSize(600, 1000),
                            #style=541068864,
                            rootObject=what, rootLabel=whatLabel,
                            rootIsNamespace=False,
                            static=False)
    c.Show(1)
    

def shellMessage(msg):
    """
    write a message into (main) shell window - or into terminal if no wx shell exists

    msg should end on r'\\n'
    """
    import __main__
    try:
        __main__.shell.InsertText(__main__.shell.promptPosStart, msg)
        __main__.shell.promptPosStart += len(msg)
        __main__.shell.promptPosEnd += len(msg)
    except:
        print(msg, end=' ')# in case there is no main.shell

def shellMenuAppendNewCommand(cmd, menuText="new command", menuCtrlKey='D', menu=0, bell=True, execModule=None):
    """
    register a new menu command with Ctrl key shortcut
    cmd:
       if cmd is callable it will get called: cmd()
       else: cmd will get exec'ed w/ execModule as globals
            if execModule is None: use __main__

    if cmd == "":
       no new command will be installed, only the old one might get deleted (see below)

    if bell:
       let bell sound before calling f()

    if the menu already contains an item with `menuText`, is gets replaced
    """
    import __main__
    import wx
    frame=__main__.shell.GetTopLevelParent()
    mb = frame.GetMenuBar()
    mf = mb.GetMenu(0)
    eid = wx.NewId()

    label = menuText+"\tCtrl-"+menuCtrlKey.upper()
    
    for i in range(mf.GetMenuItemCount()):
        mi = mf.FindItemByPosition(i)
        #wx2.8.6if mi.GetItemLabelText() == menuText:
        if mi.GetLabel() == menuText:  # wx2.8.4 ==> 2.8.6: This function is deprecated in favour of GetItemLabelText.
            break
    else:
        i+=1

    if i<mf.GetMenuItemCount():
        #existingID = mf.FindItem(menuText)
        #if existingID > 0:
        #mi = mf.FindItemById(existingID)
        mf.DeleteItem(mi)
        

    #mi = mf.GetMenuItems()[mf.GetMenuItemCount()-1]
    #if mi.GetItemLabel() == label:
    #    mf.DeleteItem(mi)

    if cmd == "":
        return

    #mf.Append(eid, label)
    mf.Insert(i, eid, label)

    if execModule is None:
        execModule = __main__

    def onAS(ev):
        if bell:
            wx.Bell()
            refresh()
        if callable(cmd):
            cmd()
        else:
            exec(cmd, execModule.__dict__) # , {'x':ev.GetString(), '_':self.execModule}        

    frame.Bind(wx.EVT_MENU, onAS, id=eid)


def assignNdArrToVarname(arr, arrTxt):
    v = wx.GetTextFromUser("assign %dd-data to varname:"%arr.ndim, 'new variable')
    if v=='':
        return
    import __main__
    try:
        exec('__main__.%s = arr' % v)
    except:
        import sys
        e = sys.exc_info()
        wx.MessageBox("Error when assigning data to __main__.%s: %s - %s" %\
                      (v, str(e[0]), str(e[1]) ),
                      "Bad Varname  !?",
                      style=wx.ICON_ERROR)
    else:
        shellMessage("### %s = %s\n"% (v, arrTxt))
        return v




def ColourDialog():
    #global dlg
    frame = None # shell.GetParent()
    dlg = wx.ColourDialog(frame)
    #dlg.GetColourData().SetChooseFull(True) #only windows, but default anyway
    if dlg.ShowModal() == wx.ID_OK:
        data = dlg.GetColourData()
    else:
        data = None
    dlg.Destroy()
    #print 'You selected: %s\n' % str(data.GetColour().Get()))
    if data is None:
        return None
    return data.GetColour().Get()



def clipboardGetText():
    """
    read out system clipboard
    and return string if there was some text to get
    returns None if no text available
    """
    # inspired by http://wiki.wxpython.org/ClipBoard

    do = wx.TextDataObject()
    if not wx.TheClipboard.Open():
        raise RuntimeError("cannot open clipboard")
    try:
        success = wx.TheClipboard.GetData(do)
    finally:
        wx.TheClipboard.Close()
    if success:
        return do.GetText()
    else:
        return None
def clipboardSetText(obj, useRepr=False):
    """
    write text into system clipboard

    if useRepr:  converts any obj into text using repr()
    """
    # inspired by http://wiki.wxpython.org/ClipBoard

    if useRepr:
        obj = repr(obj)
    do = wx.TextDataObject()
    do.SetText(obj)
    if not wx.TheClipboard.Open():
        raise RuntimeError("cannot open clipboard")
    try:
        wx.TheClipboard.SetData(do)
    finally:
        wx.TheClipboard.Close()

def clipboardImageSaveToFile(fn=None):
    """
    save a bitmap currently in the clipboard to an image file
    if fn is None: uses FN()
    """
    if not wx.TheClipboard.Open():
        raise RuntimeError("cannot open clipboard")
    try:
        if not wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_BITMAP)):
            raise RuntimeError("no bitmap in clipboard")

        if fn is None:
            fn = FN(save=1)
        if not fn:
            return
        do = wx.BitmapDataObject()
        wx.TheClipboard.GetData(do)
        bmp = do.GetBitmap()

        # FIXME should vbe a function in wxPython = but which ?
        if   fn[-4:].lower() == '.png':
            typ = wx.BITMAP_TYPE_PNG
        elif fn[-4:].lower() == '.jpg':
            typ = wx.BITMAP_TYPE_JPEG
        elif fn[-4:].lower() == '.bmp':
            typ = wx.BITMAP_TYPE_BMP
        elif fn[-4:].lower() == '.tif':
            typ = wx.BITMAP_TYPE_TIFF
        elif fn[-4:].lower() == '.gif':
            typ = wx.BITMAP_TYPE_GIF
        else:
            raise ValueError("Unknow file extention")

        bmp.SaveFile(fn, typ) #, wx.BITMAP_TYPE_PNG
    finally:
        wx.TheClipboard.Close()


def clipboardGetText2array(transpose=False, comment='#', sep=None, convFcn = None, convertDecimalKomma=False):
    """
    Return an array containing the data currently as text in the clipboard. This
    function works for arbitrary data types (every array element can be
    given by an arbitrary Python expression), but at the price of being
    slow. 
   
    if convFcn is not None:
        convFcn is called for each "cell" value - a string !.
        useful here: "N.float32"  # WRONG !! THIS DOES NOT WORK FIXME !
    else:
        "eval" is called for each cell

    if sep is None, any white space is seen as field separator
    ignore all lines that start with any character contained in comment

    if convertDecimalKomma:
       convert e.g. "10,2" to "10.2"
    """
 
    txt = clipboardGetText()
    from . import useful as U
    return U.text2array(txt, transpose=transpose, comment=comment, sep=sep, 
                        convFcn = convFcn, convertDecimalKomma=convertDecimalKomma)

try:
    def vtkInit():
        import sys

        p1 = '/jws18/haase/VTK-4.2-20040703/VTK/Wrapping/Python'
        p2 = '/jws18/haase/VTK-4.2-20040703/VTK/bin'
        if not p1 in sys.path:
            sys.path.append(p1)
            sys.path.append(p2)

    def vtkWxDemoCone(resolution=8):
        vtkInit()

        import wx, vtkpython

        #A simple VTK widget for wxPython.  Note that wxPython comes
        #with its own wxVTKRenderWindow in wxPython.lib.vtk.  Try both
        #and see which one works better for you.
        from vtk.wx.wxVTKRenderWindow import wxVTKRenderWindow


        # create the widget
        frame = wx.Frame(None, -1, "wxRenderWindow", size=wx.Size(400,400))
        widget = wxVTKRenderWindow(frame, -1)

        ren = vtkpython.vtkRenderer()
        widget.GetRenderWindow().AddRenderer(ren)

        cone = vtkpython.vtkConeSource()
        cone.SetResolution( resolution )

        coneMapper = vtkpython.vtkPolyDataMapper()
        coneMapper.SetInput(cone.GetOutput())

        coneActor = vtkpython.vtkActor()
        coneActor.SetMapper(coneMapper)

        ren.AddActor(coneActor)

        # show the window

        frame.Show(1)

    class vtkMountain:
    
        def __init__(self, arr2d, title="wxRenderWindow"):
            self.arr2d = arr2d


            try:
                import vtk
            except:
                vtkInit()
                import vtk


            #from vtk.wx.wxVTKRenderWindow import wxVTKRenderWindow
            #from vtk import vtkImageImport

            #global f, w, ren, ii, h,w, mi,ma,  geom,warp, mapper, carpet, _vtktypedict 

            self._vtktypedict = {N.uint8:vtk.VTK_UNSIGNED_CHAR,
                            N.uint16:vtk.VTK_UNSIGNED_SHORT,
                            N.uint32:vtk.VTK_UNSIGNED_INT,
                            N.int8:vtk.VTK_CHAR,
                            N.int16:vtk.VTK_SHORT,
                            N.int32:vtk.VTK_INT,
                            #N.int32:vtk.VTK_LONG,
                            #N.uint8:vtk.VTK_FLOAT,
                            #N.uint8:vtk.VTK_DOUBLE,
                            N.float32:vtk.VTK_FLOAT,
                            N.float64:vtk.VTK_DOUBLE }



            from vtk.wx.wxVTKRenderWindow import wxVTKRenderWindow
            from vtk import vtkImageImport

            self.f = wx.Frame(None, -1, title, size=wx.Size(400,400))
            self.w = wxVTKRenderWindow(self.f, -1)
            self.ren = vtk.vtkRenderer()
            self.w.GetRenderWindow().AddRenderer(self.ren)

            self.ii = vtkImageImport()

            #size = len(a.flat)  * a.itemsize()
            #ii.SetImportVoidPointer(a.flat, size)
            ####use tostring instead    self.ii.SetImportVoidPointer(arr2d._data, len(arr2d._data))
            self.ii.SetImportVoidPointer(arr2d._data, len(arr2d._data))
            self.ii.SetDataScalarType( self._vtktypedict[arr2d.dtype]) 

            h,w = arr2d.shape[-2:]
            self.ii.SetDataExtent (0,w-1, 0,h-1, 0,0)
            self.ii.SetWholeExtent(0,w-1, 0,h-1, 0,0)
            from . import useful as U
            self.mi,self.ma = U.mm( arr2d )


            self.geom = vtk.vtkImageDataGeometryFilter()
            self.geom.SetInput(self.ii.GetOutput())
            self.warp = vtk.vtkWarpScalar()
            self.warp.SetInput(self.geom.GetOutput())
            self.mapper = vtk.vtkPolyDataMapper()
            self.mapper.SetInput(self.warp.GetPolyDataOutput())
            self.carpet = vtk.vtkActor()
            self.carpet.SetMapper(self.mapper)
            self.carpet.SetScale(1,1, 50)


            self.mapper.SetScalarRange(self.mi,self.ma)
            self.ren.AddActor(self.carpet)

        def setZScale(self, zscale):
            self.carpet.SetScale(1,1, zscale)
            self.w.Refresh()
        
except:
    import sys
    global exc_info
    exc_info = sys.exc_info()
    #import traceback
    #traceback.print_exc()
    print("* no VTK *")
    pass


# ===========================================================================
# ===========================================================================
# line graphics
# ===================
# ===========================================================================
# OLD: implicitly adjusts all coordinates yx  by .5,.5
# OLD:     so that a cross would go through the center of pixel yx
# NEW 20080701:  in new coord system, integer pixel coord go through the center of pixel
#
# ===========================================================================
#
# if name is not None: add this to a named gfx-list
# if name is a list (! not tuple !) EACH list-items is used
# if name is a tuple this gfx will automagically enabled/disabled for z-sec ==/!= name
# if idx is not None: reuse/overwrite existing gfx entry 

# width is open-GL LineWidth
# color is rgb-tuple for color
# if refreshNow: call Refresh(0)  when done

# ===========================================================================
# function definition uses hand-made "templating" 
#  all function have this scheme
# def vgAdd...(id, .... color=PriConfig.defaultGfxColor, width=1, name=None, idx=None, enable=True, refreshNow=True):
#     """
#     viewer line graphics - returns GLList index(idx)

#     ...
#     """
#     from OpenGL import GL
#     if type(id) is int:
#         v = viewers[id].viewer
#     else:
#         v=id
#     v.newGLListNow(name,idx)
#     try:
#         GL.glLineWidth(width)
#         GL.glColor( color )
    
#         ....
#     except:
#         import traceback
#         traceback.print_exc() #limit=None, file=None)
#         v.newGLListAbort()
#     else:
#         return v.newGLListDone(enable, refreshNow)

def _define_vgAddXXX(addWhat, extraArgs, extraDoc, extraCode):
    exec('''
def vgAdd%(addWhat)s  (id, %(extraArgs)s 
                       color=PriConfig.defaultGfxColor, width=1, name=None, idx=None, enable=True, refreshNow=True):
    """
    viewer line graphics - returns GLList index(idx)

    %(extraDoc)s
    """
    from OpenGL import GL
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    v.newGLListNow(name,idx)
    try:
        GL.glLineWidth(width)
        GL.glColor( color )
        GL.glBlendFunc(GL.GL_ONE, GL.GL_ZERO)
  
        %(extraCode)s
        GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE)
    except:
        v.newGLListAbort()
        if PriConfig.raiseEventHandlerExceptions:
           raise
        else:
           import traceback
           traceback.print_exc() #limit=None, file=None)
    else:
        return v.newGLListDone(enable, refreshNow)
''' % locals(), globals())

# vgAddBoxes
# vgAddCircles
# vgAddEllipses
# vgAddCrosses
# vgAddArrows
# vgAddArrowsDelta
# vgAddLineStrip
# vgAddLines
# vgAddRectFilled
# vgAddRect
# vgAddTexts


_define_vgAddXXX('Crosses', 
                 extraArgs='ps, l=4,',
                 extraDoc='''ps is a point list of Y-X tuples  OR
       an entry might contain a third value used as l for that point
    l is the (default) length of the crosses; if length <0: draw plus instead of cross''',
                 extraCode='''for yx in ps:
            y,x = yx[:2]
            if len(yx)>2:
                ll = yx[2]
                if ll>0:
                   glCross(x,y, ll)
                else:
                   glPlus(x,y, -ll)
            else:
                ll=l
                glCross(x,y, ll)
''')

_define_vgAddXXX('Boxes', 
                 extraArgs='ps, l=4,',
                 extraDoc='''ps is a point list of Y-X tuples  OR
       an entry might contain a third value used as l for that point
    l is the (default) side length of the boxes''',
                 extraCode='''
        l=l/2.
        for yx in ps:
            y,x = yx[:2]
            if len(yx)>2:
                ll_2 = yx[2] / 2.
            else:
                ll_2 =l
            glBox(x-ll_2,y-ll_2, x+ll_2,y+ll_2)
''')
_define_vgAddXXX('Circles', 
                 extraArgs='ps, r=4, nEdges=20,',
                 extraDoc='''    ps is a point list of Y-X tuples  (circle centers) OR
       an entry might contain a third value used as r for that point
    r is the (default) radius of the circles
 ''',
                 extraCode='''for yx in ps:
            y,x = yx[:2]
            if len(yx)>2:
                rr = yx[2]
            else:
                rr=r
            glCircle(x,y, r, nEdges)
''')
_define_vgAddXXX('Ellipses', 
                 extraArgs='ps, nEdges=20,',
                 extraDoc='''    ps is a point list of tuples (circle centers, radius)
Y-X-R  or Y-X-RY-RX or Y-X-RY-RX-PHI
 ''',
                 extraCode='''for yx in ps:
            y,x = yx[:2]
            ry=yx[2]
            if len(yx)>3:
                rx = yx[3]
            else:
                rx=ry
            if len(yx)>4:
                phi = yx[4]
            else:
                phi=0
            glEllipse(x,y, rx, ry, phi, nEdges=nEdges)
''')
_define_vgAddXXX('Arrows', 
                 extraArgs='ps, qs, factor=1,',
                 extraDoc='''    ps is a point list of Y-X tuples
    qs is a point list of Y-X tuples
    lines are being drawn from a point in ps to the corresponding
    point in qs
    factor  'stretches' the lines "beyond" the b-point
 ''',
                 extraCode='''for yx0,b in zip(ps,qs):
            dyx = b-yx0
            glLineYxDyx(yx0, dyx*factor)
''')
_define_vgAddXXX('ArrowsDelta', 
                 extraArgs='ps, ds, factor=1,',
                 extraDoc='''    ps is a point list of Y-X tuples
    ds is a point list of delta Y-X tuples
    lines are being drawn from a point in ps to the corresponding
    point at p + delta
    factor  'stretches' the lines "beyond" the arrow-end
 ''',
                 extraCode='''for yx0,dyx in zip(ps,ds):
            glLineYxDyx(yx0, dyx*factor)
''')
_define_vgAddXXX('LineStrip', 
                 extraArgs='ps, ',
                 extraDoc='''    ps is a point list of Y-X tuples
    lines are being drawn connecting all points in as from the first to
    the last
 ''',
                 extraCode='''GL.glBegin(GL.GL_LINE_STRIP);
        for yx in ps:
            GL.glVertex2f( yx[1],yx[0] )
        GL.glEnd()
''')
_define_vgAddXXX('Lines', 
                 extraArgs='ps, ltype=1, ',
                 extraDoc='''    ps is a point list of Y-X tuples
    lines are being drawn connecting all points in ps; 
       the ltypes are:
       >>> GL.GL_LINES       #  o--o o--o ...
       1
       >>> GL.GL_LINE_LOOP   #  x--o--o--o--x (x is "looped back")...
       2
       >>> GL.GL_LINE_STRIP  #  o--o--o--o ...
       3
       >>> GL.GL_POINTS      #  .  .  .  .
       0
       >>> GL.GL_POLYGON     #  like loop, but filled
       9       
 ''',
                 extraCode='''GL.glBegin(ltype);
        for yx in ps:
            GL.glVertex2f( yx[1],yx[0] )
        GL.glEnd()
''')

_rectCode='''
        y0,x0 = ps[0]
        y1,x1 = ps[1]
        if y0>y1:
            y0,y1 = y1,y0
        if x0>x1:
            x0,x1 = x1,x0
        if enclose:
            x0 -=.5
            y0 -=.5
            x1 +=.5
            y1 +=.5
        GL.glVertex2f( x0,y0 )
        GL.glVertex2f( x1,y0 )
        GL.glVertex2f( x1,y1 )
        GL.glVertex2f( x0,y1 )
        GL.glEnd()
'''
_define_vgAddXXX('RectFilled', 
                 extraArgs='ps, enclose=False, ',
                 extraDoc='''    ps is a pair of Y-X tuples
    if enclose: boxes are enlarged by .5 in each direction(CHECK!)
 ''',
                 extraCode='''GL.glBegin(GL.GL_POLYGON);'''+_rectCode
)
_define_vgAddXXX('Rect', 
                 extraArgs='ps, enclose=False, ',
                 extraDoc='''    ps is a pair of Y-X tuples
    if enclose: boxes are enlarged by .5 in each direction(CHECK!)
 ''',
                 extraCode='''GL.glBegin(GL.GL_LINE_LOOP);'''+_rectCode
)
_define_vgAddXXX('Texts', 
                 extraArgs='ps, size=.1, mono=False, enumLabel=None, ',
                 extraDoc='''    ps is a point list of Y-X-text tuples (if enumLabel is None)
    size, mono is for Y.glutText
    [GLUT stroke font size of 1 is 100 "pixels" high for the letter `A`]
    ps can be Y-X tuples if enumLabel is a number, label-text is auto-generated as 1,2,3,...(first used value is enumLabel 
 ''',
                 extraCode='''
        if enumLabel is None:
            for yxt in ps:
                y,x,text = yxt
                glutText(str(text), posXYZ=(x,y), size=size, mono=mono, color=color, enableLineSmooth=False)
        else:
            for i,yx in enumerate(ps):
                y,x = yx
                glutText(str(enumLabel+i), posXYZ=(x,y), size=size, mono=mono, color=color, enableLineSmooth=False)
''')
    
def vgRemove(id=-1, idx=-1, refreshNow=True, ignoreError=True):
    """
    viewer line graphics -

    remove GLList index idx

    if ignoreError: invalid `idx` will be silently ignored
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    try:
        v.newGLListRemove(idx, refreshNow)
    except (KeyError, IndexError):
        if not ignoreError:
            raise

def vgRefresh(id=-1):
    """
    viewer line graphics - or not (CHECK!)

    refresh (= redraw) viewer
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    
    v.Refresh(0)


def vgEnabledMaster(id=-1):
    """
    viewer line graphics -

    return if master-enable is on or off (for all GLLists)
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    return v.m_moreMaster_enabled

def vgEnableMaster(id=-1, on=True, refreshNow=True):
    """
    viewer line graphics -

    dis-/enable all GLList
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    v.m_moreMaster_enabled = on
    
    if refreshNow:
        v.Refresh(0)

def vgEnable(id=-1, idx=-1, on=True, refreshNow=True, ignoreError=True):
    """
    viewer line graphics -

    disable GLList index idx
    if ignoreError: invalid `idx` will be silently ignored
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    if type(idx) in (tuple, list):
        for i in idx:
            try:
                v.newGLListEnable(i, on, refreshNow)
            except KeyError:
                if not ignoreError:
                    raise
    else:
        try:
            v.newGLListEnable(idx, on, refreshNow)
        except (KeyError, IndexError):
            if not ignoreError:
                raise

def vgEnabled(id=-1, idx=-1):
    """
    viewer line graphics -

    return if GLList index idx is enabled
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id

    if isinstance(idx, six.string_types):
        idx=v.m_moreGlLists_NamedIdx[idx]
    return v.m_moreGlLists_enabled[idx]

def vgNameEnable(id=-1, name='', on=True, skipBlacklisted=False, refreshNow=True):
    """
    en-/dis-able all 'viewer line graphics' with given name
    if skipBlacklisted: do nothing for gfx which are blacklisted
    """
    
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id

    v.newGLListEnableByName(name, on, skipBlacklisted, refreshNow)

def vgNameRemove(id=-1, name='', refreshNow=True, ignoreKeyError=True):
    """
    remove all 'viewer line graphics' with given name
    """
    
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id

    try:
        v.newGLListRemoveByName(name, refreshNow)
    except KeyError:
        if not ignoreKeyError:
            raise

def vgNameBlacklist(id=-1, name='', add=True):
    """
    blacklisted line grpahics are (can be) ignored by vgNameEnable()
    used especially by auto-on/off trigged via "z-section change"
    all idx with given name are added (add=True) or removed (add=False) from
    blacklist. (noop if `name` doesn't exist)
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    
    try:
        idxs = v.m_moreGlLists_dict[name]
    except KeyError:
        return

    for idx in idxs:
        if add:
            v.m_moreGlLists_nameBlacklist.add(idx)
        else:
            v.m_moreGlLists_nameBlacklist.discard(idx)

def vgNameToggle(id=-1, name='', on=None):
    """
    toggle on/off (en-/dis-able) gfx with given name
    if on is None:
        toggle based on curr. state of first idx having "name" being blacklisted
    otherwise switch to 'on'(True) or 'off' (False)

    switching to 'on' might either enable all gfx having "name"
    or enable all gfx having the current section tuple name
     (heuristic: if first idx of "name" has also a tuple as name)
    
    """
    vv = viewers[id].viewer
    if on is None:
        # turn on if currently blacklisted, and vice versa
        on = vv.m_moreGlLists_dict[name][0] in vv.m_moreGlLists_nameBlacklist
    
    vgNameBlacklist(id, name, add=not on)
    if on:
        nameGoesWithSectTuples = any((isinstance(k,tuple) for k in list(vv.m_moreGlLists_dict.keys()) if vv.m_moreGlLists_dict[name][0] in vv.m_moreGlLists_dict[k]))
        if nameGoesWithSectTuples:
            # trigger redraw of all gfxs in current section, instead of all gfxs having "name" (which would be accross many z-sections)
            name = vGetZSecTuple(id)
        vgNameEnable(id, name, on=True, skipBlacklisted=True, refreshNow=True)
            
    else:
        vgNameEnable(id, name, on=False)

def vgNameEnablerGUIbox(id=-1):
    """
    open GUI window for easy on/off switching of named GFXs

    (this is implemented with the help of vgNameBlacklist 
     to overwrite auto on/off when changing z-sections)
    """
    if id < 0:
        id += len(viewers)

    import sys
    buttonBox(
        [
            ("tb x.SetValue(0==len(viewers[%d].viewer.m_moreGlLists_nameBlacklist.intersection( viewers[%d].viewer.m_moreGlLists_dict['%s'] )))\t%s"%(id,id, name,name), "vgNameToggle(%d, name='%s', on=x)"%(id,name))
            for name in sorted(viewers[id].viewer.m_moreGlLists_dict.keys()) if isinstance(name, six.string_types)],
        title="named GFXs for viewer %d"%(id,),
        execModule=sys.modules['Priithon.usefulX'], #__import__(__name__),
        )#, layout="boxVert")
#             ("tb x.SetValue(0==len(viewers[%d].viewer.m_moreGlLists_nameBlacklist.intersection( viewers[%d].viewer.m_moreGlLists_dict['%s'] )))\t%s"%(id,id, name,name), "vgNameBlacklist(%d, name='%s', add=not x);vgNameEnable(%d, vGetZSecTuple(%d), on=True, skipBlacklisted=True, refreshNow=True) if x else vgNameEnable(%d, name='%s', on=x)"%(id,name,  id,id,id,name))
#             for name in sorted(viewers[id].viewer.m_moreGlLists_dict.keys()) if isinstance(name, basestring)],



def vgIdxAddName(id=-1, idx=0, name=''):
    """
    add idx into list given by name (IOW: give idx an additional name)
    name can be a list of names, than each name is applied
    silently ignore names that idx was already part of
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    v.newGLListNameAdd(idx, name)
def vgIdxRemoveName(id=-1, idx=0, name=''):
    """
    remove idx from list given by name (IOW: idx no longer has that name)
    name can be a list of names, than each name is applied
    silently ignore names that idx was not even part of
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    v.newGLListNameRemove(idx, name)

    

def vgRemoveAll(id=-1, refreshNow=True):
    """
    viewer line graphics -

    this really removes(!) all line graphics (GLList) stuff
    idx values will restart at 0
    here nothing gets "only" set to None
    """
    if type(id) is int:
        v = viewers[id].viewer
    else:
        v=id
    v.newGLListRemoveAll(refreshNow)
# ===========================================================================A


def vDrawingReset(v_id=-1):
    v = viewers[v_id]
    _registerEventHandler(v.viewer.doOnMouse, oldFcnName='Y_vDrawing')

def vDrawingCircles(v_id=-1, 
                    allZsecs=False,
                    channel=None,  r=10, val = 1, add=False):
    """
    if allZsecs:
        drawing fills all z sections the same
    else:
        draw only into current z-sec

    use channel != None for drawing into that channel of a viewer2 window
    otherwise all channels will be drawn in the same (viewer2 only)

    if add: add value is used as multiplier and then added to image,  
    otherwise image is substituted where brush>0 
    """
    from . import fftfuncs as F

    v = viewers[v_id]

    from .splitND import spv as spv_class
    #from splitND2 import spv as spv2_class
    

    if isinstance(v, spv_class):
        def rel():
            #v.OnReload()
            v.helpNewData(doAutoscale=False, setupHistArr=True)
    else: # viewer2
        def rel():
            v.helpNewData(doAutoscale=False, setupHistArr=True)
        
    def onMouseDraw(x,y, ev):
        if v.viewer._onMouseEvt.LeftIsDown():
            a = v.data
            if not allZsecs:
                a = a[tuple(v.zsec)]
            if channel is not None:
                a = a[...,channel,:,:]

            brush2D_unity = F.discArr(a.shape[-2:], r, (y,x))

            if add:
                a += brush2D_unity * val
            else:
                for zsec in N.ndindex(a.shape[:-2]):
                    a[zsec] = N.where(brush2D_unity, val, a[zsec])

            rel()

    _registerEventHandler(v.viewer.doOnMouse, newFcn=onMouseDraw, newFcnName='Y_vDrawing')

    

def vShowPixelGrid(v_id=-1, spacingY=1, spacingX=1, color=PriConfig.defaultGfxColor, width=1):
    v = viewers[v_id]
    v.viewer.drawPixelGrid(spacingY, spacingX, color, width)

def _registerEventHandler(handlerList, newFcn=None, newFcnName=None, oldFcnName='', delAll=False):
    """
    use this for event-handler function lists.
    handlerList could be e.g. Y.viewers[-1].viewer.doOnMouse

    to append a new handler function:
        set newFcn to handler function
        set newFcnName to a string, if you want to rename newFcn
        set oldFcnName to None

    to remove functions by name:
        set newFcn to None (default)
        set oldFcnName to the handler function name that should be removed
        if delAl: not only the last, but all, such handlers will get removed


    to replace a given handler function:
        set oldFcnName and newFcn and (optionally) newFcnName
        the default oldFcnName('') is a shortcut for oldFcnName=newFcnName
        the last(!) function in list that matches oldFcnName gets replaced
        if delAll, "other" functions in that list, that have name oldFcnName are removed,
        otherwise, these would be left unchanged 

    if both newFcn and oldFcnName are not None, and oldFcnName does NOT already exist in the list,
        the new handler is appended

    if newFcn is a string: it is executed in `__main__` with `args` containing the handler arguments
    """
    
    if isinstance(newFcn, six.string_types):
        newFcnStr=newFcn
        def myCmdString(*args):#selfExecMod, x, b, ev, cmd=cmd):
            import __main__
            exec(newFcnStr, __main__.__dict__, {'args':args}) #'_':selfExecMod, '_ev':ev, '_b':b, 'x':x}
        newFcn = myCmdString

    if newFcnName:
        try:
            newFcn.__name__ = newFcnName
        except AttributeError:
            # HACK for instance methods:
            # http://www.velocityreviews.com/forums/t395502-why-cant-you-pickle-instancemethods.html
            newFcn.__func__.__name__ = newFcnName

    if oldFcnName is None:  # append new
        handlerList.append( newFcn )
        
    else:
        if oldFcnName == '':
            oldFcnName = newFcn.__name__

        ## iterate backwards, so that we can delete items
        for i in range(len(handlerList)-1,-1,-1):
            if handlerList[i].__name__ == oldFcnName:
                if newFcn is not None:
                    handlerList[i] = newFcn
                    newFcn = None
                else:
                    del handlerList[i]

                if not delAll:
                    break
        if newFcn is not None:
            handlerList.append( newFcn )



def vAnimate(vids=-1):
    #class animateClass:
    #def __init__(self):
    #    self.animationRunning = False

    # now animateStart() is renamed and contains the start/stop function itself
    #def animateStartStop(self):
    #    if self.animationRunning:
    #        self.animationRunning = False
    #    else:
    #        self.animateStart()
    def animateStartStop(self, _val=0,_name='', singleStep=0):
        import time
        nn = 0
        t0 = time.time()
        if not self.animationRunning and not singleStep:
            return
        if self.animationRunning and singleStep: 
            # safety for called on "reentrance"
            self.animationRunning = False
            
        # #         if self.animationRunning: # safety for called on "reentrance"
        # #             self.animationRunning = False
        # #             return

        # self.animationRunning = True
        animationZ = 0
        while self.animationRunning or singleStep:
            try:
                vids = list(map(int, self.animateVids.split()))
                axes = list(map(int, self.animateAxes.split()))
                if len(axes) < len(vids):
                    axes += axes[-1:]*(len(vids)-len(axes))
                strideStr = self.animateStrides
                if '/' in strideStr:
                    strideStr, minMaxStr=strideStr.split('/',1)
                    minMax = list(map(int, minMaxStr.split()))
                    if len(minMax)>1:
                        minZ = minMax[0]
                        maxZ = minMax[1]
                    else:
                        minZ = minMax[0]
                        maxZ = None
                else:
                    minZ = 0
                    maxZ = None
                    
                strides = list(map(int, strideStr.split()))
                if len(strides) < len(vids):
                    strides += strides[-1:]*(len(vids)-len(strides))
                #autoscales = map(int, self.animateAutoscale.split())
                #if len(autoscales) < len(vids):
                #    autoscales += autoscales[-1:]*(len(vids)-len(autoscales))

                if singleStep:
                    direction = singleStep
                else:
                    direction = self.direction

                for i,vid in enumerate(vids):
                    zaxis = axes[i] 
                    z = vGetZSecTuple(id=vid) [zaxis]
                    z  = z+strides[i]*direction
                    zMax = vd(vid).shape[zaxis] -1  if (maxZ is None) else maxZ
                    if z > zMax:
                        z=minZ
                    elif z<minZ:
                        z = zMax
                    vSetSlider(vid, z, zaxis=zaxis, autoscale=False) #autoscales[i])
            except:
                pass
                #raise # debug
            refresh()
            t1 = time.time()
            nn += 1
            dt = t1 - t0
            if dt > 1:
                self.fpsTxtCtrl.SetValue("%.1f"%(nn/dt,))
                nn = 0
                t0 = time.time()
            try:
                animateMS = float(self.animateMS) / 1000.
                if animateMS>0:
                    time.sleep( animateMS )
            except:
                pass
            if singleStep:
                singleStep = 0
                #self._holdParamEvents('animationRunning', True)
                #self.animationRunning = False
                #self._holdParamEvents('animationRunning', False)
                
                
        self.fpsTxtCtrl.SetValue("--")


    #global animateObj
    #animateObj = animateClass()
    #global gp

    gp = guiParams()
    #gp.animationRunning = False
    import new
    gp.animateStartStop = new.instancemethod(animateStartStop, gp, guiParams)
    #gp.animateStart = new.instancemethod(animateStart, gp, guiParams)

    gp.direction = 1

    def onClose(bb,ev):
        gp.animationRunning = False

    if not hasattr(vids, "__len__"):
        vids = [vids]
    
    vids = [v%len(viewers) for v in vids] # normilize to substitute negative viewers ids
    vidsStr = " ".join(map(str,vids))
    buttonBox([
    ("l\tvids"),
    ("t\t%s"%(vidsStr,), "_.animateVids = x", 1,True,
     """id or ids of one or more viewers to animate"""),
    '\n',
    ("l\taxes:"),
    ("t\t0", "_.animateAxes = x", 1,True,
     """z-axis of respective viewer(s) to animate"""), 
    '\n',
    ("l\tstrides [ / first [last] ]:"),
    ("t\t1", "_.animateStrides = x", 1,True,
     """stride (step size) of respective viewer axis used
add '/'  to specify min (optionally) and max value
"""),
#    '\n',
#    ("l\tpause[ms]:"),
#    ("t\t0", "_.animateMS = x"),
    '\n',
    ("l\tcurrent frame rate [Hz]:"),
    ("t _.fpsTxtCtrl = x\t--", "--"),
    '\n',] +
    gp._bboxInt("pause[ms]: ", 'animateMS', v=0, slider=True, slmin=0, slmax=1000, newLine=True) +
    #("l\tautoscale:"),
    #("t\t0", "_.animateAutoscale = x"),
    #'\n',
    gp._bboxBool("start / stop", 'animationRunning', v=0, controls='tb 1 1')+[
    #("tb\tstart / stop", "_.animateStartStop()"),
    ("b\t<", "_.animateStartStop(singleStep=-1)", 0, True, "single step backwards"),
    ("b\t>", "_.animateStartStop(singleStep=1)", 0, True, "single step forward"),
    ("tb\treverse", "_.direction*=-1", 0),
    #], title='vAnimate', execModule=animateObj)
    ], title='vAnimate', execModule=gp)

    buttonBoxes[-1].gp = gp # for debugging
    wx.FindWindowByLabel('<', buttonBoxes[-1].frame).SetMinSize((30,-1))
    wx.FindWindowByLabel('>', buttonBoxes[-1].frame).SetMinSize((30,-1))

    _registerEventHandler(buttonBoxes[-1].doOnClose, onClose)
    _registerEventHandler(gp._paramsDoOnValChg['animationRunning'], gp.animateStartStop)
