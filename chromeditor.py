from __future__ import with_statement
from PriCommon.ndviewer import main as aui
from PriCommon import guiFuncs as G, mrcIO
import wx, wx.lib.mixins.listctrl as listmix
import os, sys, csv
from Priithon import Mrc
import aligner, alignfuncs as af
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
        G.makeTxt(self, box, 'Local: ')
        self.local_label = G.makeTxt(self, box, self.clist.map_str)
        if self.clist.map_str != 'None':
            self.viewLocalButton = G.makeButton(self, box, self.onViewLocal, title='View', tip='View local distortion as a image')

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

        self.saveButton = G.makeButton(self, box, self.onSave, title='Save as...', tip='Save editted parameter into a chromagnon file', enable=False)

        self.exportButton = G.makeButton(self, box, self.onExport, title='Export as .csv', tip='Save editted parameter into a comma separated file')

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

        name = self.clist.basename + '.Local'

        mapyx = Mrc.bindFile(self.clist.fn)
        hdr = mapyx.Mrc.hdr
        nz = hdr.Num[-1] / (hdr.NumTimes * hdr.NumWaves * 2)
        mapyx = mapyx.reshape((hdr.NumTimes,
                               hdr.NumWaves,
                               nz,
                               2,
                               hdr.Num[1], 
                               hdr.Num[0]))  
        
        if hasattr(parent.doc, 'saveNonlinearImage'):
            parent.doc.mapyx = mapyx
            out = parent.doc.saveNonlinearImage(gridStep=gridStep)

        else:
            out = os.path.extsep.join((self.fn, 'local'))
            

            
            arr = N.zeros(mapyx.shape[:3]+mapyx.shape[-2:], N.float32)
            for t in xrange(self.clist.nt):
                arr[t,:,:,::gridStep,:] = 1.
                arr[t,:,:,:,::gridStep] = 1.
            affine = N.zeros((7,), N.float64)
            affine[-3:] = 1

            canvas = N.empty_like(arr)
            for t in xrange(self.clist.nt):
                for w in xrange(self.clist.nw):
                    canvas[t,w] = af.remapWithAffine(arr[t,w], mapyx[t,w], affine)
                    
            hdr = mrcIO.makeHdr_like(hdr)
            hdr.ImgSequence = 2
            hdr.Num[-1] = N.prod(mapyx.shape[:3])

            Mrc.save(N.squeeze(canvas), out, hdr=hdr, ifExists='overwrite')
            
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
        saves self.clist.parm into a chromagnon file
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

            hdr = Mrc.makeHdrArray()
            Mrc.init_simple(hdr, Mrc.dtype2MrcMode(N.float32), aligner.NUM_ENTRY, 1, self.clist.nt*self.clist.nw)
            hdr.ImgSequence = 2
            hdr.PixelType = 2
            hdr.NumWaves = self.clist.nw
            hdr.NumTimes = self.clist.nt
            hdr.wave[:self.clist.nw] = self.clist.waves[:]
            hdr.d = self.clist.pxlsiz
            hdr.n1 = list(self.clist.waves).index(self.clist.refwave)
            hdr.type = aligner.IDTYPE

            if self.clist.map_str == 'None':
                hdr.n2 = 1

                # squeeze shape
                parm = N.squeeze(self.clist.parm.reshape((self.clist.nt, self.clist.nw, aligner.NUM_ENTRY)))
                #parm = N.squeeze(parm)
                parm = parm.reshape(parm.shape[:-1] + (1,1) + (parm.shape[-1],))

                Mrc.save(parm, out, hdr=hdr, ifExists='overwrite')
            else:
                hdr.NumFloats = self.clist.parm.shape[-1]
                hdr.NumIntegers = 1

                parm = self.clist.parm.reshape((self.clist.nt * self.clist.nw, aligner.NUM_ENTRY))
                extFloats = N.zeros((self.clist.nt * self.clist.nw * self.clist.nz * 2, aligner.NUM_ENTRY), N.float32)

                extFloats[:self.clist.nt * self.clist.nw] = parm

                mapyx = Mrc.bindFile(self.clist.fn)
                nz = mapyx.Mrc.hdr.Num[-1] / (mapyx.Mrc.hdr.NumTimes * mapyx.Mrc.hdr.NumWaves * 2)
                mapyx = mapyx.reshape((mapyx.Mrc.hdr.NumTimes,
                                       mapyx.Mrc.hdr.NumWaves,
                                       nz*2,
                                       mapyx.Mrc.hdr.Num[1], 
                                       mapyx.Mrc.hdr.Num[0]))                                       

                hdr.Num[0] = mapyx.shape[-1]
                hdr.Num[1] = mapyx.shape[-2]
                hdr.Num[2] = N.prod(mapyx.shape[:-2])
                hdr.n2 = 2

                o = mrcIO.MrcWriter(out, hdr, extFloats=extFloats)
                for t in range(self.clist.nt):
                    for w in range(self.clist.nw):
                        o.write3DArr(mapyx[t,w], w=w, t=t)
                o.close()


    def onExport(self, evt=None):
        """
        export self.clist.parm as a .csv file
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
                    l = list(self.clist.parm[t,w])
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
        clear selected item from the list and self.clist.parm
        """
        inds = self.selected

        refwave_deleted = False
        for i in inds[::-1]:
            
            self.clist.DeleteItem(i)
            self.clist.parm = N.delete(self.clist.parm, i, axis=1)
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
        add a row to the list and self.clist.parm
        """
        if self.clist.nw >= 5:
            G.openMsg(self, 'The maximum wavelength is 5', 'I am sorry for that')
            return 
        
        index = self.clist.InsertStringItem(sys.maxint, '0')

        self.clist.parm = N.insert(self.clist.parm, self.clist.parm.shape[1], 0, axis=1)
        self.clist.parm[:,-1,-3:] = 1

        waves = list(self.clist.waves)
        waves.append(0)
        self.clist.waves = N.array(waves)
        self.clist.nw = len(self.clist.waves)
        
        for i, p in enumerate(self.clist.parm[self.clist.t,index]):
            self.clist.SetStringItem(index, i+1, str(p))
        
class ChromagnonList(wx.ListCtrl,
                     listmix.ListCtrlAutoWidthMixin,
                     listmix.TextEditMixin):
    """
    The list to display alignment parameters
    The actual data is stored in self.parm
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
        set self.parm
        """
        arr = Mrc.bindFile(self.fn)
        self.pxlsiz = arr.Mrc.hdr.d
        self.waves = arr.Mrc.hdr.wave[:arr.Mrc.hdr.NumWaves].copy()
        self.refwave = self.waves[arr.Mrc.hdr.n1]
        self.XYsize = arr.Mrc.hdr.Num[:2]
        self.nt = arr.Mrc.hdr.NumTimes
        self.nw = len(self.waves)
        self.t = 0
        self.dtype = arr.dtype.type

        if arr.Mrc.hdr.n2 == 1:
            parm = arr
            nentry = aligner.NUM_ENTRY
            self.map_str = 'None'
        else:
            parm = arr.Mrc.extFloats[:arr.Mrc.hdr.NumTimes * arr.Mrc.hdr.NumWaves,:arr.Mrc.hdr.NumFloats]
            nentry = arr.Mrc.hdr.NumFloats
            self.nz = arr.Mrc.hdr.Num[-1] / (arr.Mrc.hdr.NumTimes * arr.Mrc.hdr.NumWaves * 2)
            if self.nz == 1:
                self.map_str = 'Projection'
            else:
                self.map_str = 'Section-wise'
        parm = parm.reshape((arr.Mrc.hdr.NumTimes, arr.Mrc.hdr.NumWaves, nentry))
        self.parm = parm.copy() # writable

        del arr, parm

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
            for i, p in enumerate(self.parm[self.t,w]):
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
            for i, p in enumerate(self.parm[t, index]):
                self.SetStringItem(index, i+1, str(p))
        for w in range(self.nw):
            self.applyGraphics(w)

        
    def SetStringItem(self, index, col, data):
        """
        Called when the user try to edit the list
        (also called in populate())

        changes self.parm and upadte graphics.

        index: wavelength idx
        col: column
        data: string
        """
        val = eval(data)
        if col:
            self.parm[self.t, index, col-1] = val
        else:
            self.waves[index] = val

        self.applyGraphics(index)

        wx.ListCtrl.SetStringItem(self, index, col, data)


    def applyGraphics(self, w=0):
        """
        update graphics according to the current self.parm
        w: wave idx
        """
        parent = self.GetParent().GetParent() # chromagnonPanel->chromagnonEditor
        pps = parent._mgr.GetAllPanes()
        if any([pp.name == 'XY' for pp in pps]):
            parent.doc.setAlignParam(self.parm)
            alignParm = self.parm[self.t, w]
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
        if os.name == 'posix':
            dlg = G.FileSelectorDialog(self)
        else:
            dlg = wx.FileDialog(self, 'Choose a file')

        if dlg.ShowModal() == wx.ID_OK:
            fn = dlg.GetPath()

        self.view(fn)
            
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
            message = 'The original reference wavelength %i was not found in the target %s' % (refwave, os.path.basename(fn))
            G.openMsg(msg=message, title='WARNING')

        else:
            from PriCommon import guiFuncs as G
            message = 'No common wavelength was found in %s and %s' % (os.path.basename(cpanel.fn), os.path.basename(fn))
            G.openMsg(msg=message, title='WARNING')
            return

        # obtain affine parms
        target = N.zeros((cpanel.clist.nt, self.doc.img.nw, aligner.NUM_ENTRY), cpanel.clist.dtype)
        target[:,:,4:] = 1

        target[:,tids] = cpanel.clist.parm[:,pids]
        for w in [w for w, wave in enumerate(twaves) if wave not in pwaves]:
            target[:,w] = cpanel.clist.parm[:,self.doc.refwave]
        target[:,:,:3] *= dratio

        self.doc.setAlignParam(target)

        parent.doc = self.doc

        parent.cpanel.clist.parm = target
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


