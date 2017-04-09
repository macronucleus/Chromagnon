from __future__ import with_statement
from PriCommon.ndviewer import main as aui
from PriCommon import guiFuncs as G, mrcIO, commonfuncs as C
import wx, wx.lib.mixins.listctrl as listmix
import os, sys, csv
from Priithon import Mrc
from . import aligner, alignfuncs as af, chromformat
import numpy as N

SIZE_COL0=70
SIZE_COLS=90


class ChromagnonEditor(aui.ImagePanel):
    """
    This is the page accomodating ChromagnonPanel and TestViewPanel
    It inherits methods from ImagePanel
    """
    def __init__(self, parent, fn):
        """
        fn: a chromagnon file
        """
        aui.ImagePanel.__init__(self, parent)

        #self.parent = parent # overwrite self.parent
        
        self.cpanel = ChromagnonPanel(self, fn)
        self._mgr.AddPane(self.cpanel, wx.aui.AuiPaneInfo().Name('cpanel').Caption("cpanel").CenterPane().Position(0))

        self.tpanel = TestViewPanel(self)
        self._mgr.AddPane(self.tpanel, wx.aui.AuiPaneInfo().Name('tpanel').Caption("tpanel").CenterPane().Position(1))
        
        self._mgr.Update()


class ChromagnonPanel(wx.Panel):
    """
    This panel provides main interface and parameters are displayed with ChromagnonList (clist)
    """
    def __init__(self, parent, fn):
        """
        fn: a chromagnon file
        """
        wx.Panel.__init__(self, parent, -1)
        
        self.clist = ChromagnonList(self, fn)
        self.fn = fn

        # start drawing
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # \n
        box = G.newSpaceV(sizer)
        G.makeTxt(self, box, fn)

        # \n
        box = G.newSpaceV(sizer)
        if self.clist.map_str != 'None':
            G.makeTxt(self, box, 'Local: ')
            self.local_label = G.makeTxt(self, box, self.clist.map_str)
            self.viewLocalButton = G.makeButton(self, box, self.onViewLocal, title='View', tip='View local distortion as a image')
            # \n
            box = G.newSpaceV(sizer)
            G.makeTxt(self, box, "The file is a .ome.tif file, and the alignment parameters are stored in it's metadata.")
        else:
            # \n
            box = G.newSpaceV(sizer)
            G.makeTxt(self, box, 'The file is a text file: rename to ".csv" to open as a spread sheet.')

        # \n\n
        box = G.newSpaceV(sizer)
        G.makeTxt(self, box, ' ')
        box = G.newSpaceV(sizer)
        G.makeTxt(self, box, 'Pixel size ZYX (um): %.3f  %.3f  %.3f' % tuple(self.clist.creader.pxlsiz))

        if self.clist.nt > 1:
            # \n
            box = G.newSpaceV(sizer)
            label, self.tSliderBox = G.makeTxtBox(self, box, 'T', defValue=str(self.clist.t), tip='enter time idx', style=wx.TE_PROCESS_ENTER)
            
            self.tSliderBox.Bind(wx.EVT_TEXT_ENTER, self.OnTSliderBox)

            G.makeTxt(self, box, r'/'+str(self.clist.nt-1))

            self.tSlider = wx.Slider(self, wx.ID_ANY, 0, 0,
                                     self.clist.nt-1,
                                     size=wx.Size(150,-1),
                                     style = wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)
            box.Add(self.tSlider, 6, wx.ALL|wx.ALIGN_LEFT, 2)
            wx.EVT_SLIDER(self, self.tSlider.GetId(), self.OnTSlider)

        
        # \n
        box = G.newSpaceV(sizer)
        box.Add(self.clist)

        # \n
        box = G.newSpaceV(sizer)

        self.saveButton = G.makeButton(self, box, self.onSave, title='Save as...', tip='Save editted parameter into a chromagnon file')#, enable=False)

        #self.exportButton = G.makeButton(self, box, self.onExport, title='Export as .csv', tip='Save editted parameter into a comma separated file')

        self.clearButton = G.makeButton(self, box, self.clearSelected, title='Remove selected', tip='Remove one wavelength')

        self.addButton = G.makeButton(self, box, self.addRow, title='add wavelength', tip='Add one wavelength')

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.clist)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemSelected, self.clist)

        
    def onViewLocal(self, evnt=None, gridStep=10):
        """
        save a '.local' file and opens new image viewer
        """
        parent = self.GetParent()
        book = parent.GetTopLevelParent()

        mapyx = self.clist.mapyx
        name = self.clist.basename + '.Local'

        if hasattr(parent.doc, 'saveNonlinearImage'):
            parent.doc.mapyx = mapyx
            out = parent.doc.saveNonlinearImage(gridStep=gridStep)

        else:
            out = os.path.extsep.join((self.fn, 'local'))
            self.clist.mapyx = mapyx
            out = chromformat.makeNonliearImg(self.clist, out, gridStep)
            
        an = aligner.Chromagnon(out)
        newpanel = aui.ImagePanel(book, an)
        book.imEditWindows.AddPage(newpanel, name, select=True)
            
    
    def OnTSliderBox(self, evt):
        """
        called when enter is pressed in the t slider text box
        """
        t = int(self.tSliderBox.GetValue())
        if t >= self.clist.nt:
            t = self.clist.nt - 1
        while t < 0:
            t = self.clist.nt + t
        self.clist.set_tSlice(t)
        self.tSlider.SetValue(t)

    def OnTSlider(self, event):
        """
        called when t slider was moved
        """
        t = event.GetInt()
        self.clist.set_tSlice(t)
        self.tSliderBox.SetValue(str(t))

        
    def onSave(self, evt=None):
        """
        saves self.clist.alignParms into a chromagnon file
        """
        # prepare output file name
        base, ext = os.path.splitext(self.clist.basename)
        defname = base + '_EDIT' + ext
        out = ''
        dlg = wx.FileDialog(self, 'Please select a file', self.clist.dirname, defname, '*.chromagnon', wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            out = dlg.GetPath()
        dlg.Destroy()
        
        if not out:
            return
        
        parent = self.GetParent()
        # if viewer is available..., the use aligner.Chromaognon.saveParm function
        if hasattr(parent.doc, 'saveParm'):
            if self.clist.map_str != 'None':
                setMapyx(self.clist.fn, parent.doc)

            parent.doc.saveParm(out)

        else:
           # if self.clist.map_str != 'None':
                
            self.clist.mapyx = None#self.clist.map_str
            #self.refwave = self.clist.refwave
            self.clist.alignParms = self.clist.alignParms.reshape((self.clist.nt, self.clist.nw, aligner.NUM_ENTRY))
            #self.ny = self.clist.n
            
            self.cwriter = chromformat.ChromagnonWriter(out, self.clist, self.clist)


    def onExport(self, evt=None):
        """
        export self.clist.alignParms as a .csv file
        """
        # prepare output file name
        base, ext = os.path.splitext(self.clist.basename)
        defname = base + '.csv'
        out = ''
        dlg = wx.FileDialog(self, 'Please select a file', self.clist.dirname, defname, '*.csv', wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            out = dlg.GetPath()
        dlg.Destroy()
            
        if not out:
            return
        
        with open(out, 'w') as w:
            writer = csv.writer(w)
            writer.writerow(['time','wavelength']+aligner.ZYXRM_ENTRY)
            for t in xrange(self.clist.nt):
                for w, wave in enumerate(self.clist.waves):
                    l = list(self.clist.alignParms[t,w])
                    writer.writerow([t,wave]+l)

    def OnItemSelected(self, evt=None):
        """
        check selected items and enable buttons that works with selected items

        set self.clearButton enable
        """
        self.selected = [i for i in range(self.clist.GetItemCount()) if self.clist.IsSelected(i)]

        if self.selected:
            self.clearButton.Enable(1)
        else:
            self.clearButton.Enable(0)

        
    def clearSelected(self, evt=None):
        """
        clear selected item from the list and self.clist.alignParms
        """
        inds = self.selected

        refwave_deleted = False
        for i in inds[::-1]:
            
            self.clist.DeleteItem(i)
            self.clist.alignParms = N.delete(self.clist.alignParms, i, axis=1)
            if self.clist.waves[i] == self.clist.refwave:
                refwave_deleted = True
            self.clist.waves = N.delete(self.clist.waves, i)

        if refwave_deleted:
            self.clist.refwave = self.clist.waves[0]
        self.clist.nw = len(self.clist.waves)
            
        self.OnItemSelected()
        wx.Yield()

    def addRow(self, evt=None):
        """
        add a row to the list and self.clist.alignParms
        """
        if self.clist.nw >= 5:
            G.openMsg(self, 'The maximum wavelength is 5', 'I am sorry for that')
            return 
        
        index = self.clist.InsertStringItem(sys.maxint, '0')

        self.clist.alignParms = N.insert(self.clist.alignParms, self.clist.alignParms.shape[1], 0, axis=1)
        self.clist.alignParms[:,-1,-3:] = 1

        waves = list(self.clist.waves)
        waves.append(0)
        self.clist.waves = N.array(waves)
        self.clist.nw = len(self.clist.waves)
        
        for i, p in enumerate(self.clist.alignParms[self.clist.t,index]):
            self.clist.SetStringItem(index, i+1, str(p))
        
class ChromagnonList(wx.ListCtrl,
                     listmix.ListCtrlAutoWidthMixin,
                     listmix.TextEditMixin):
    """
    The list to display alignment parameters
    The actual data is stored in self.alignParms
    """
    def __init__(self, parent, fn):
        """
        fn: a chromagnon file
        """
        sizeX = SIZE_COL0 + SIZE_COLS * aligner.NUM_ENTRY
        sizeY = 23 * 5 # 5 is the maximum number of wavelengths
        wx.ListCtrl.__init__(self, parent, wx.NewId(), pos=wx.DefaultPosition, size=(sizeX, sizeY), style=wx.LC_REPORT|wx.BORDER_NONE|wx.LC_SORT_ASCENDING)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

        self.fn = fn
        self.dirname, self.basename = os.path.split(fn)
        
        self.readFile()
        self.populate()
        listmix.TextEditMixin.__init__(self)

    def readFile(self):
        """
        get header information
        set self.alignParms
        """
        self.creader = chromformat.ChromagnonReader(self.fn, self, self)
        #print self.alignParms.shape
        self.waves = self.wave[:self.nw]
        self.t = 0

        if not hasattr(self, 'mapyx'):
            self.map_str = 'None'
        else:
            maxval = self.mapyx.max()
            if self.nz == 1:
                self.map_str = 'Projection (max shift %.3f pixel)' % maxval
            else:
                self.map_str = 'Section-wise'


    def populate(self):
        """
        fill the list using information in the chromagnon file
        """
        # column 0
        self.InsertColumn(0, "wavelength", wx.LIST_FORMAT_RIGHT)
        self.SetColumnWidth(0, SIZE_COL0)
        # subsequent columns
        for i, entry in enumerate(aligner.ZYXRM_ENTRY):
            self.InsertColumn(i+1, entry, wx.LIST_FORMAT_RIGHT)
            self.SetColumnWidth(i+1,  SIZE_COLS)

        for w, wave in enumerate(self.waves):
            # column 0
            index = self.InsertStringItem(sys.maxint, str(wave))
            # subsequent columns
            for i, p in enumerate(self.alignParms[self.t,w]):
                self.SetStringItem(index, i+1, str(p))

    def set_tSlice(self, t=0):
        """
        changes list contents according to the current time frame
        if viewer is present, redraw the image
        """
        parent = self.GetParent().GetParent() # chromagnonPanel->chromagnonEditor
        if hasattr(parent, 'tSlider'):
            parent.tSlider.SetValue(t)
            parent.tSliderBox.SetValue(str(t))
            parent.set_tSlice(t)
        
        self.t = t
        for index in xrange(len(self.waves)):
            for i, p in enumerate(self.alignParms[t, index]):
                self.SetStringItem(index, i+1, str(p))
        for w in range(self.nw):
            self.applyGraphics(w)

        
    def SetStringItem(self, index, col, data):
        """
        Called when the user try to edit the list
        (also called in populate())

        changes self.alignParms and upadte graphics.

        index: wavelength idx
        col: column
        data: string
        """
        val = eval(data)
        if col:
            self.alignParms[self.t, index, col-1] = val
        else:
            self.waves[index] = val

        self.applyGraphics(index)

        wx.ListCtrl.SetStringItem(self, index, col, data)


    def applyGraphics(self, w=0):
        """
        update graphics according to the current self.alignParms
        w: wave idx
        """
        parent = self.GetParent().GetParent() # chromagnonPanel->chromagnonEditor
        pps = parent._mgr.GetAllPanes()
        if any([pp.name == 'XY' for pp in pps]):
            parent.doc.setAlignParam(self.alignParms)
            alignParm = self.alignParms[self.t, w]
            for v in parent.viewers:
                v.updateAlignParm(w, alignParm)

            parent.updateGLGraphics(range(len(parent.viewers)))

        
class TestViewPanel(wx.Panel):
    """
    This panel waits image file to view
    """
    def __init__(self, parent):

        sizeX = parent.GetSize()[0] - parent.cpanel.clist.GetSize()[0]
        wx.Panel.__init__(self, parent, -1, size=(sizeX,-1))
        #self.parent = parent
        
        # start drawing
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # \n
        box = G.newSpaceV(sizer)
        G.makeTxt(self, box, 'Drag and drop a file to preview the parameters\n or click the button to select a file')

        # \n
        box = G.newSpaceV(sizer)
        self.testButton = G.makeButton(self, box, self.onChooseFile, title='Open')

        dropTarget = ViewFileDropTarget(self)
        self.SetDropTarget(dropTarget)

    def onChooseFile(self, evnt):
        """
        get image file
        call self.view()
        """
        confdic = C.readConfig()
        lastpath = confdic.get('lastpath', '')
        #parent = self.GetTopLevelParent()
        if os.name == 'posix':
            dlg = G.FileSelectorDialog(self, lastpath)
        else:
            dlg = wx.FileDialog(self, 'Choose a file', defaultDir=lastpath)

        if dlg.ShowModal() == wx.ID_OK:
            fn = dlg.GetPath()
        else:
            return

        self.view(fn)

        C.saveConfig(lastpath=os.path.dirname(fn))
            
    def view(self, fn):
        """
        opens viewer and hide itself.
        """
        try:
            self.doc = aligner.Chromagnon(fn)
        except:
            G.openMsg(self, 'This file is not a valid image file', 'Error')
            return

        self.loadParm()

        parent = self.GetParent()
        parent._mgr.GetPane('tpanel').Hide()
        parent.addImageXY()

        

    def loadParm(self):
        """
        fit alignment parameters to the current image
        """
        parent = self.GetParent()
        cpanel = parent.cpanel
        #ll = cpanel.getList()

        creader = cpanel.clist.creader
        creader.rdr = self.doc.img
        creader.holder = self.doc
        creader.loadParm()

        old="""
        dratio = cpanel.clist.pxlsiz / self.doc.img.hdr.d
        dratio = dratio[::-1] # zyx
        
        pwaves = list(cpanel.clist.waves)#[l[0] for l in ll]
        twaves = list(self.doc.img.hdr.wave[:self.doc.img.nw])
        tids = [twaves.index(wave) for wave in pwaves if wave in twaves]
        pids = [pwaves.index(wave) for wave in twaves if wave in pwaves]
        refwave = cpanel.clist.refwave
        somewaves = [w for w, wave in enumerate(pwaves) if wave in twaves]

        if refwave in twaves:
            self.doc.refwave = twaves.index(refwave)
        elif len(somewaves) >= 1: # the reference wavelength was not found but some found
            self.doc.refwave = somewaves[0]
            from PriCommon import guiFuncs as G
            message = 'The original reference wavelength %i was not found in the target %s' % (refwave, self.doc.file)
            G.openMsg(msg=message, title='WARNING')

        else:
            from PriCommon import guiFuncs as G
            message = 'No common wavelength was found in %s and %s' % (os.path.basename(cpanel.fn), self.doc.file)
            G.openMsg(msg=message, title='WARNING')
            return

        # obtain affine parms
        target = N.zeros((cpanel.clist.nt, self.doc.img.nw, aligner.NUM_ENTRY), cpanel.clist.dtype)
        target[:,:,4:] = 1

        target[:,tids] = cpanel.clist.alignParms[:,pids]
        for w in [w for w, wave in enumerate(twaves) if wave not in pwaves]:
            target[:,w] = cpanel.clist.alignParms[:,self.doc.refwave]
        target[:,:,:3] *= dratio

        self.doc.setAlignParam(target)"""

        parent.doc = self.doc

        #parent.cpanel.clist.alignParms = target
        parent.cpanel.clist.set_tSlice(0)

def setMapyx(fn, doc):
    """
    set doc.mapyx from the filename(fn)
    """
    arr = Mrc.bindFile(fn)
    nz = arr.Mrc.hdr.Num[-1] / (arr.Mrc.hdr.NumTimes * arr.Mrc.hdr.NumWaves * 2)
    arr = arr.reshape((arr.Mrc.hdr.NumTimes, 
                       arr.Mrc.hdr.NumWaves, 
                       nz, 
                       2, 
                       arr.Mrc.hdr.Num[1], 
                       arr.Mrc.hdr.Num[0]))
    doc.mapyx = arr

        
class ViewFileDropTarget(wx.FileDropTarget):
    """
    drop target for TestViewPanel
    """
    def __init__(self, parent):
        wx.FileDropTarget.__init__(self)
        self.testViewPanel = parent

    def OnDropFiles(self, x, y, filenames):
        self.testViewPanel.view(filenames[0])


