from __future__ import print_function
import sys, os, six, itertools
import  wx
import  wx.lib.mixins.listctrl  as  listmix
#try:
#    from agw import hyperlink as hl
#except ImportError: # if it's not there locally, try the wxPython lib.
#    import wx.lib.agw.hyperlink as hl
from . import commonfuncs as C
try:
    import imgio
    from PriCommon import guiFuncs as G
except ImportError:
    from .. import imgio
    from ..PriCommon import guiFuncs as G

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
        self.counter = itertools.count()
        self.last_index = 0
        self.Populate()

        self.initialize()

        self.dropTarget = MyFileDropTarget(self)
        self.SetDropTarget(self.dropTarget)

        self.setDefaultFileLoadFunc()#bioformatsIO.load)


    def initialize(self):
        """
        initialize all the constants
        """
        self.columnkeys = [] # (raw_index)

        #self.waves = []
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

        #self.waves.pop(index)
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

    def setDefaultFileLoadFunc(self, func=None):
        if not func:
            self.load_func = imgio.Reader
        else:
            self.load_func = func


    def SetStringItem(self, index, col, data):
        if wx.version().startswith('3'):
            wx.ListCtrl.SetStringItem(self, index, col, data)
        else:
            wx.ListCtrl.SetItem(self, index, col, data)
        
    def addFiles(self, fns):
        """
        fns: bioformats compatible files
        """

        if self.multiple:
            for fn in fns:
                self.addFile(fn)

        else:
            self.clearAll()
            fn = fns[0]
            self.addFile(fn)
        
    def addFile(self, fn):
        """
        fill in the first 4 columns
        """
        if not os.path.exists(fn):
            raise ValueError('The input file is not a valid file')
        
        dd, ff = os.path.split(fn)

        
        try:
            h = self.load_func(fn)
        except (ValueError, AttributeError) as e:
            imgio_dialog(e, self)
            return ''
            old="""
            dlg = wx.MessageDialog(self, ' '.join(e.args), 'Error reading image file', wx.OK | wx.ICON_EXCLAMATION)
            raise
            if dlg.ShowModal() == wx.ID_OK:
                return"""
        except:
            print('file %s was not recognized..., skip' % fn)
            raise
            return

        # column 0
        index0 = len(self.columnkeys)
        if wx.version().startswith('3') and not sys.platform.startswith('win'):
            index = self.InsertStringItem(sys.maxsize, dd)
        elif wx.version().startswith('3') and sys.platform.startswith('win'):
            index = self.InsertStringItem(next(self.counter), dd)
        else:
            index = self.InsertItem(next(self.counter), dd)#sys.maxsize, dd)

        # column 1
        self.SetStringItem(index, 1, ff)

        # column 2

        nw = []
        for w in h.wave[:h.nw]:
            if w % 1:
                nw.append(str(int(round(w))))
            else:
                nw.append(str(w))
        #nw = [str(w) for w in h.wave[:h.nw]]
        wstr = ','.join(nw)
        self.SetStringItem(index, 2, wstr)

        self.nws.append(len(nw))

        seq = imgio.generalIO.IMGSEQ[h.imgSequence]
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
        if self.GetItemCount():
            return [self.GetItem(index, col).GetText() for col in range(self.nColums)]
        else:
            return []
            

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

        if self.multiple:
            for fn in fns:
                self.addFile(fn)
        else:
            fn = fns[0]
            self.addFile(fn)

        
    def addFile(self, fn):
        """
        fill in the first 4 columns
        """
        if not os.path.exists(fn):
            raise ValueError('The input file is not a valid file')
        
        dd, ff = os.path.split(fn)

        try:
            h = self.load_func(fn)
        except (ValueError, AttributeError) as e:
            old="""
            dlg = wx.MessageDialog(self, ' '.join(e.args), 'Error reading image file', wx.OK | wx.ICON_EXCLAMATION)

            if dlg.ShowModal() == wx.ID_OK:
                return"""
            imgio_dialog(e, self)
            return ''
        if not h:
            return
        old="""
        if chromformat.is_chromagnon(fn):
            h = chromformat.ChromagnonReader(fn)
        else:
            try:
                h = bioformatsIO.load(fn)#aligner.Chromagnon(fn)
            except ValueError:
                dlg = wx.MessageDialog(self, '%s is not a valid image file!' % ff, 'Error reading image file', wx.OK | wx.ICON_EXCLAMATION)
                raise
                if dlg.ShowModal() == wx.ID_OK:
                    return"""

        # column 0
        index0 = len(self.columnkeys)
        if wx.version().startswith('3') and not sys.platform.startswith('win'):
            index = self.InsertStringItem(sys.maxsize, dd)
        elif wx.version().startswith('3') and sys.platform.startswith('win'):
            index = self.InsertStringItem(next(self.counter), dd)
        else:
            index = self.InsertItem(next(self.counter), dd)#self.GetItemCount(), dd)

        # column 1
        self.SetStringItem(index, 1, ff)

        # column 2
        nw = []
        for w in h.wave[:h.nw]:
            if not isinstance(w, six.string_types) and w % 1:
                nw.append(str(int(round(w))))
            else:
                nw.append(str(w))
        #nw = [str(w) for w in h.wave[:h.nw]]
        wstr = ','.join(nw)
        self.SetStringItem(index, 2, wstr)

        self.nws.append(len(nw))
        #self.waves.append(h.wave[:h.nw])

        # column 3
        nt = h.nt
        self.SetStringItem(index, 3, str(nt))

        self.nts.append(nt)

        # column 4
        nz = h.nz
        self.SetStringItem(index, 4, str(nz))
        
        # column 5
        seq = imgio.generalIO.IMGSEQ[h.imgSequence]
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

        return True

#####
def imgio_dialog(e=None, parent=None):
    """
    e: error or messege string

    opens a dialog to navigate to install JDK
    """
    if isinstance(e, six.string_types) or e.args[0].startswith(imgio.JDK_MSG[:10]):
        if os.name == 'nt':
            sysname = 'Windows'
            arch = os.getenv('PROCESSOR_ARCHITECTURE')
        else:
            uname = os.uname()
            if sys.version_info.major == 2:
                sysname = uname[0]
                machine = uname[-1]
            else:
                sysname = uname.sysname
                machine = uname.machine
            sysname = sysname.replace('Darwin', 'macOS')
            arch = machine.replace('x86_64', 'x64')

        if isinstance(e, six.string_types):
            msg0 = e
        else:
            msg0 = ' '.join(e.args)
        msg = msg0 + '\n\nWould you like to obtain JDK?'
        extra = '\nYour platform: %s %s' % (sysname, arch)
        
        if sysname.startswith('Linux'):
            extra += '\n\nYou can also obtain JDK by your package manager.'

        dlg = wx.MessageDialog(parent,  msg, 'Your image requires JDK', style=wx.YES_NO)
        dlg.SetExtendedMessage(extra)
        if dlg.ShowModal() == wx.ID_YES:
            import webbrowser
            webbrowser.open(imgio.bioformatsIO.URL)
            return False
        else:
            return False
    else:
        dlg = wx.MessageDialog(parent, ' '.join([str(aa) for aa in e.args]), 'Error reading image file', wx.OK | wx.ICON_EXCLAMATION)
        raise
        if dlg.ShowModal() == wx.ID_OK:
            return False
