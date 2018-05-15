
import sys, os
import  wx
import  wx.lib.mixins.listctrl  as  listmix
#import aligner
from PriCommon import bioformatsIO, commonfuncs as C

SIZE_COL0=180
SIZE_COL1=280
SIZE_COL2=100
SIZE_COL3=30
SIZE_COL4=30
#SIZE_COL5=45


class BasicFileListCtrl(wx.ListCtrl,
                   listmix.ListCtrlAutoWidthMixin):

    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, multiple=True):
        """
        multiple: support handling multiple files
        """
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)

        listmix.ListCtrlAutoWidthMixin.__init__(self)

        self.multiple = multiple
        self.last_index = 0
        self.Populate()

        self.initialize()

        self.dropTarget = MyFileDropTarget(self)
        self.SetDropTarget(self.dropTarget)

        self.setDefaultFileLoadFunc(bioformatsIO.load)


    def initialize(self):
        """
        initialize all the constants
        """
        self.columnkeys = [] # (raw_index)

        self.nws = []
        self.nts = []
        self.seqs = []
        self.pxszs = []

    def removeConstants(self, index=-1):
        """
        remove constants for a single raw
        """
        idx = self.columnkeys.index(index)
        self.columnkeys = self.columnkeys[:idx] + [i - 1 for i in self.columnkeys[idx+1:]]#.pop(index)

        self.nws.pop(index)
        self.nts.pop(index)
        self.seqs.pop(index)
        self.pxszs.pop(index)
        
    def Populate(self):
        """
        create columns
        """
        self.InsertColumn(0, "directory")
        self.InsertColumn(1, "file name")
        self.InsertColumn(2, "wavelength", wx.LIST_FORMAT_RIGHT)

        self.SetColumnWidth(0, SIZE_COL0)
        self.SetColumnWidth(1, SIZE_COL1)#wx.LIST_AUTOSIZE)
        self.SetColumnWidth(2, SIZE_COL2)#wx.LIST_AUTOSIZE)

        self.nColums = 3

        self.currentItem = 0

    def setDefaultFileLoadFunc(self, func):
        self.load_func = func


    def SetStringItem(self, index, col, data):
        wx.ListCtrl.SetStringItem(self, index, col, data)

    old='''
    def addFiles(self, fns):
        """
        """
        if multiple:
            for fn in fns:
                self.addFile(fn)
        else:
            self.clearAll()
            self.addFile(fns[0])'''
        
    def addFiles(self, fns):
        """
        add tif or mrc
        """
        old="""
        tifs = [fn for fn in fns if fn.lower().endswith(tuple(imgfileIO.IMGEXTS_MULTITIFF))]
        if tifs:
            confdic = C.readConfig()
            dlg = imgfileIO.DimDialog(self, tifs, float(confdic.get('defPxlSiz', self.defPxlSiz)))
            if dlg.ShowModal() == wx.ID_OK:
                holders = dlg.holders
            else:
                return"""

        if self.multiple:
            for fn in fns:
                self.addFile(fn)
                old="""
                if fn in tifs:
                    i = tifs.index(fn)
                    h = holders[i]
                    self.SetStringItem(self.last_index, 2, ','.join([str(wave) for wave in h.waves]))
                    #self.SetStringItem(self.last_index, 3, str(h.nt))
                    #self.SetStringItem(self.last_index, 4, str(int(h.getZ())))
                    #self.SetStringItem(self.last_index, 5, str(h.seq))
                    self.nts[-1] = h.nt
                    self.nws[-1] = h.nw
                    self.seqs[-1] = h.seq
                    self.pxszs[-1] = h.pxlsiz
                    C.saveConfig(defPxlSiz=h.pxlsiz)"""
        else:
            self.clearAll()
            fn = fns[0]
            self.addFile(fn)
            old="""
            if fn in tifs:
                i = tifs.index(fn)
                h = holders[i]
                self.SetStringItem(self.last_index, 2, ','.join([str(wave) for wave in h.waves]))
                #self.SetStringItem(self.last_index, 3, str(h.nt))
                #self.SetStringItem(self.last_index, 4, str(int(h.getZ())))
                #self.SetStringItem(self.last_index, 5, str(h.seq))
                self.nts[-1] = h.nt
                self.nws[-1] = h.nw
                self.seqs[-1] = h.seq
                self.pxszs[-1] = h.pxlsiz
                C.saveConfig(defPxlSiz=h.pxlsiz)"""
            
        
    def addFile(self, fn):
        """
        fill in the first 4 columns
        """
        if not os.path.isfile(fn):
            raise ValueError('The input file is not a valid file')
        
        dd, ff = os.path.split(fn)

        try:
            h = self.load_func(fn)
        except ValueError:
            dlg = wx.MessageDialog(self, '%s is not a valid image file!' % ff, 'Error reading image file', wx.OK | wx.ICON_EXCLAMATION)
            raise
            if dlg.ShowModal() == wx.ID_OK:
                return

        # column 0
        index0 = len(self.columnkeys)
        index = self.InsertStringItem(sys.maxsize, dd)

        # column 1
        self.SetStringItem(index, 1, ff)

        # column 2

        nw = [str(w) for w in h.wave[:h.nw]]
        wstr = ','.join(nw)
        self.SetStringItem(index, 2, wstr)

        self.nws.append(len(nw))

        seq = bioformatsIO.generalIO.IMGSEQ[h.imgSequence]
        self.seqs.append(seq)

        self.pxszs.append(h.pxlsiz[0])
        
        # final step
        self.columnkeys.append(index0)

        self.last_index = index

        h.close()

        return 0

    
    def getFile(self, index):
        """
        return directory, basefilename, waves, nt
        """
        return [self.GetItem(index, col).GetText() for col in range(self.nColums)]#5)]#6)]
            

    def clearRaw(self, index):
        """
        remove a single raw
        """
        if index in self.columnkeys:
            self.removeConstants(index)
            self.DeleteItem(index)
        
    def clearAll(self):
        """
        clear up all the raws
        """
        self.DeleteAllItems()
        self.initialize()

    def setOnDrop(self, funcs=[], args=[]):
        #dropTarget = self.GetDropTarget()
        self.dropTarget.setOnDrop(funcs, args)


class FileListCtrl(BasicFileListCtrl):

    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, multiple=True):
        BasicFileListCtrl.__init__(self, parent, ID, pos, size, style, multiple)

        self.defPxlSiz = 0.1 # for tif file

    def Populate(self):
        """
        create columns
        """
        self.InsertColumn(0, "directory")
        self.InsertColumn(1, "file name")
        self.InsertColumn(2, "wavelength", wx.LIST_FORMAT_RIGHT)
        self.InsertColumn(3, "t", wx.LIST_FORMAT_RIGHT)
        self.InsertColumn(4, "z", wx.LIST_FORMAT_RIGHT)
        #self.InsertColumn(5, "imgSeq", wx.LIST_FORMAT_RIGHT)

        self.SetColumnWidth(0, SIZE_COL0)
        self.SetColumnWidth(1, SIZE_COL1)#wx.LIST_AUTOSIZE)
        self.SetColumnWidth(2, SIZE_COL2)#wx.LIST_AUTOSIZE)
        self.SetColumnWidth(3, SIZE_COL3)#wx.LIST_AUTOSIZE)
        self.SetColumnWidth(4, SIZE_COL4)#wx.LIST_AUTOSIZE)
        #self.SetColumnWidth(5, SIZE_COL5)#wx.LIST_AUTOSIZE)

        self.nColums = 5
        
        self.currentItem = 0

        
    def addFiles(self, fns):
        """
        add tif or mrc
        """
        old="""
        tifs = [fn for fn in fns if fn.lower().endswith(tuple(imgfileIO.IMGEXTS_MULTITIFF))]
        if tifs:
            confdic = C.readConfig()
            dlg = imgfileIO.DimDialog(self, tifs, float(confdic.get('defPxlSiz', self.defPxlSiz)))
            if dlg.ShowModal() == wx.ID_OK:
                holders = dlg.holders
            else:
                return"""

        if self.multiple:
            for fn in fns:
                self.addFile(fn)
                old="""
                if fn in tifs:
                    i = tifs.index(fn)
                    h = holders[i]
                    self.SetStringItem(self.last_index, 2, ','.join([str(wave) for wave in h.waves]))
                    self.SetStringItem(self.last_index, 3, str(h.nt))
                    self.SetStringItem(self.last_index, 4, str(int(h.getZ())))
                    #self.SetStringItem(self.last_index, 5, str(h.seq))
                    self.nts[-1] = h.nt
                    self.nws[-1] = h.nw
                    self.seqs[-1] = h.seq
                    self.pxszs[-1] = h.pxlsiz
                    C.saveConfig(defPxlSiz=h.pxlsiz)"""
        else:
            fn = fns[0]
            self.addFile(fn)
            old="""
            if fns in tifs:
                i = tifs.index(fns)
                h = holders[i]
                self.SetStringItem(self.last_index, 2, ','.join([str(wave) for wave in h.waves]))
                self.SetStringItem(self.last_index, 3, str(h.nt))
                self.SetStringItem(self.last_index, 4, str(int(h.getZ())))
                #self.SetStringItem(self.last_index, 5, str(h.seq))
                self.nts[-1] = h.nt
                self.nws[-1] = h.nw
                self.seqs[-1] = h.seq
                self.pxszs[-1] = h.pxlsiz
                C.saveConfig(defPxlSiz=h.pxlsiz)"""
        
        
    def addFile(self, fn):
        """
        fill in the first 4 columns
        """
        if not os.path.isfile(fn):
            raise ValueError('The input file is not a valid file')
        
        dd, ff = os.path.split(fn)

        try:
            h = bioformatsIO.load(fn)#aligner.Chromagnon(fn)
        except ValueError:
            dlg = wx.MessageDialog(self, '%s is not a valid image file!' % ff, 'Error reading image file', wx.OK | wx.ICON_EXCLAMATION)
            raise
            if dlg.ShowModal() == wx.ID_OK:
                return

        # column 0
        index0 = len(self.columnkeys)
        index = self.InsertStringItem(sys.maxsize, dd)

        # column 1
        self.SetStringItem(index, 1, ff)

        # column 2

        nw = [str(w) for w in h.wave[:h.nw]]
        wstr = ','.join(nw)
        self.SetStringItem(index, 2, wstr)

        self.nws.append(len(nw))

        # column 3
        nt = h.nt
        self.SetStringItem(index, 3, str(nt))

        self.nts.append(nt)

        # column 4
        nz = h.nz
        self.SetStringItem(index, 4, str(nz))
        
        # column 5
        seq = bioformatsIO.generalIO.IMGSEQ[h.imgSequence]
        #self.SetStringItem(index, 5, seq)
        self.seqs.append(seq)

        self.pxszs.append(h.pxlsiz[0])

        # final step
        self.columnkeys.append(index0)

        self.last_index = index

        h.close()

        return 0

        
        
class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, parent):
        wx.FileDropTarget.__init__(self)
        self.list = parent
        self.funcs = []

    def setOnDrop(self, funcs=[], args=[]):
        try:
            len(funcs)
            self.funcs = funcs
        except TypeError:
            self.funcs = [funcs]

        try:
            if len(args) == len(funcs):
                self.args = args
            else:
                raise ValueError('len(args) must be the same as len(funcs)')
        except TypeError:
            self.args = [args for i in range(len(self.funcs))]
            

    def OnDropFiles(self, x, y, filenames):
        self.list.addFiles(filenames)
        #[self.list.addFile(fn) for fn in filenames if os.path.isfile(fn)]
                    
        frame = wx.GetTopLevelParent(self.list)

        for i, func in enumerate(self.funcs):
            func(self.args[i])


