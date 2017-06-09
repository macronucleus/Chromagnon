
import os
try: # inside package
    from ..Priithon.all import Mrc, Y, N
except ValueError: # Attempted relative import beyond toplevel package
    from Priithon.all import Mrc, Y, N
from scipy import ndimage as nd
import wx
import mrcIO, imgResample, imgfileIO, fntools, guiFuncs as G


# load img as a reader object
def load(fns):
    """
    fns: can be either...
    1. class of MrcReader or ImgReader
    2. a single file of common images or Mrc
    3.  list of img file

    return Reader
    """
    # 1. class of MrcReader or ImgReader
    if hasattr(fns, 'get3DArr'):
        img = fns
    # 2. a single file of ...
    elif isinstance(fns, basestring):
        # 2-1. image
        if fns.lower().endswith(tuple(imgfileIO.IMGEXTS_MULTITIFF)):
            img = imgfileIO.MultiTiffReader(fns)
            img.makeHdr()
        # 2-2. Mrc file
        else:
            img = mrcIO.MrcReader(fns)
    # 3. list of img file
    elif fns[0].lower().endswith(tuple(imgfileIO.IMGEXTS)):
        img = imgfileIO.ImgReader(fns)
    # 4. what else??
    else:
        raise ValueError, 'cannot determine img type'
    return img


class ImageManager(object):
    '''
    doc as in doc-view; the view class being ImEditPanel
    '''
    def __init__(self, fns):
        """
        fns
        """
        # input types
        self.img = load(fns)
                
        # copy attributes
        self.nt = self.img.nt
        self.nw = self.img.nw
        self.nz = self.img.nz
        self.ny = self.img.ny
        self.nx = self.img.nx
        self.dtype = self.img.dtype
        self.hdr = self.img.hdr
        self.dirname = os.path.dirname(self.img.filename)#path)
        self.file = self.path = os.path.basename(self.img.filename)#path)
        self.shape = N.asarray(mrcIO.shapeFromNum(self.hdr.Num,self.nw,self.nt,self.hdr.ImgSequence))
        self.ndim = int(self.nz > 1) + int(self.nw > 1) + int(self.nt > 1) + 2
        zwt = ['z', 'w', 't']
        num = [self.nz, self.nw, self.nt]
        maxdim = max(num)
        self.maxaxs = zwt[num.index(maxdim)]
        
        # slicing parameter
        self.ignor_color_axis = False
        self.sld_axs = 't'
        
        # cropping region
        self.cropbox_l = N.array([0, 0, 0], N.int32)
        self.cropbox_u = N.array([self.nz, self.ny, self.nx], N.int32)
        self.setMstUse(False) # this has to be False since original shape cannot be known
        self.tSlice = 0
        self.setIndices(range(self.nw), range(self.nt), range(self.nz), self.hdr.ImgSequence, self.dtype)

        self.sliceIdx = [self.nz//2, self.ny//2, self.nx//2]
        self.selectZsecs()

        # output
        self.byteorder = '='
        self.interporder = imgResample.ORDER

        # viewer
        self.vid = None
        self._rub = None
        self.vid_single = None

        # aui
        self.t = 0
        self.w = 0
        self.z = self.nz // 2
        self.y = self.ny // 2
        self.x = self.nx // 2

    def __getitem__(self, idx):
        try:
            idx = int(idx)
            if idx < 0:
                idx = self.shape[0] + idx

            ws = range(self.nw)
            ts = range(self.nt)
            zs = range(self.nz)
            if self.maxaxs == 'w' and not self.ignor_color_axis:
                ws = [idx]
                self.sld_axs = 'w'
            elif self.maxaxs == 't' or (self.ignor_color_axis and self.ndim > 4):
                ts = [idx]
                self.sld_axs = 't'
            elif self.maxaxs == 'z' or (self.ignor_color_axis and self.ndim == 4):
                zs = [idx]
                self.sld_axs = 'z'
            else:
                raise ValueError, 'section axis not determined'
            if self.hdr.ImgSequence == 0:
                e = N.empty((len(ws), len(ts), len(zs), self.ny, self.nx), self.dtype)
                for wo, wi in enumerate(ws):
                    for to, ti in enumerate(ts):
                        for zo, zi in enumerate(zs):
                            e[wo,to,zo] = self.img.getArr(w=wi,t=ti,z=zi)
            elif self.hdr.ImgSequence == 1:
                e = N.empty((len(ts), len(zs), len(ws), self.ny, self.nx), self.dtype)
                for to, ti in enumerate(ts):
                    for zo, zi in enumerate(zs):
                        for wo, wi in enumerate(ws):
                            e[to,zo,wo] = self.img.getArr(w=wi,t=ti,z=zi)
            elif self.hdr.ImgSequence == 2:
                e = N.empty((len(ts), len(ws), len(zs), self.ny, self.nx), self.dtype)
                for to, ti in enumerate(ts):
                    for wo, wi in enumerate(ws):
                        for zo, zi in enumerate(zs):
                            e[to,wo,zo] = self.img.getArr(w=wi,t=ti,z=zi)

        except TypeError:
            pass

        return N.squeeze(e)


    def __del__(self):
        self.close()

    def close(self):
        if hasattr(self, 'img') and hasattr(self.img, 'close'):
            self.img.close()

        if hasattr(self, '_zslider') and self._zslider:
            try:
                self._zslider.Close()
            except TypeError:
                pass #print 'already closed', self._zslider

    # cropping funcs
    def setMstUse(self, useMst=None):
        self.cxoff = self.hdr.mst[0]
        self.cyoff = self.hdr.mst[1]
        self.useMst = useMst

    def selectYX(self, yxMM):
        """
        yxMM: ([ymin,ymax],[xmin,xmax]) or (*,sliceY,sliceX)
        stores region info
        """
        if type(yxMM[-1]) == slice:
            self._yxSlice = yxMM[-2:]
            self._yxslice2crop()
        else:
            self._yxSlice = slice(yxMM[0][0],yxMM[0][1]), slice(yxMM[1][0],yxMM[1][1])
            self._yxslice2crop()

        sy, sx = self._yxSlice
        y0,y1 = sy.start, sy.stop
        x0,x1 = sx.start, sx.stop
        self._yxSize = N.array((y1-y0,x1-x0))
        return

    def selectWaves(self, wave=[0]):
        if wave is None:
            return
        waveIdx = [mrcIO.getWaveIdxFromHdr(self.hdr, w) for w in wave]
        waveIdx.sort()
        self._wIdx = waveIdx

    def selectTimes(self, start=None, stop=None, pattern=[1], pickWhich=1):
        """
        stores section indices to be picked up when doing copy region

        pattern:  smallest pattern of elements eg. [1,1,0,2]
        pickWich: sections corresponding this number in the pattern is picked up
        """
        if stop is None:
            stop = self.nt
        if start is None:
            start = 0
  
        unit = len(pattern)

        idx = N.arange(self.nt)
        repeat = N.ceil(self.nt / float(unit))
        repPat = N.tile(pattern, repeat)[:len(idx)]
        ids = N.compress(repPat == pickWhich, idx)
        self._tIdx = [i for i in ids if i >= start and i < stop]

        self._tPtrn = pattern
        self._tPick = pickWhich

    def selectZsecs(self, start=0, stop=None, pattern=[1], pickWhich=1):
        """
        stores section indices to be picked up when doing copy region

        pattern:  smallest pattern of elements eg. [1,1,0,2]
        pickWich: sections corresponding this number in the pattern is picked up
        """
        if stop is None:
            stop = self.cropbox_u[0]
        if start is None:
            start = self.cropbox_l[0]
  
        unit = len(pattern)

        idx = N.arange(self.nz)
        repeat = N.ceil(self.nz / float(unit))
        repPat = N.tile(pattern, repeat)[:self.nz]
        ids = N.compress(repPat == pickWhich, idx)
        self._zIdx = [i for i in ids if i >= start and i < stop]
        if not self._zIdx:
            self._zIdx = [0]
            print self._zIdx

        self.cropbox_l[0] = start
        self.cropbox_u[0] = stop
        if self.cropbox_l[0] == self.cropbox_u[0]:
            self.cropbox_u[0] += 1

        self._zPtrn = pattern
        self._zPick = pickWhich

    def setIndices(self, widx=[], tidx=[], zidx=[], imgSeq=None, dtype=None):
        if widx:
            self._wIdx = [mrcIO.getWaveIdxFromHdr(self.hdr, w) for w in widx]

        if tidx:
            self._tIdx = tidx

        if zidx:
            self._zIdx = zidx
        elif len([p for p in self._zPtrn if p != self._zPick]):
            pass # does not use cropbox
        else:
            self._zIdx = range(self.cropbox_l[0], self.cropbox_u[0])

        self._yxSlice = [slice(self.cropbox_l[1], self.cropbox_u[1]),
                         slice(self.cropbox_l[2], self.cropbox_u[2])]
        self._yxSize = (self._yxSlice[0].stop - self._yxSlice[0].start,
                        self._yxSlice[1].stop - self._yxSlice[1].start)

        if imgSeq is not None:
            self._ImgSequence = imgSeq

        if self.useMst:
            self.cxoff = 512/2. - (self.hdr.mst[0] + self.nx/2.)
            if self.ny == 128:
                # In this case, assume orignal data was 512x128 in shape !!!
                self.cyoff = 128/2. - (self.hdr.mst[1] + self.ny/2.)
            else:
                self.cyoff = 512/2. - (self.hdr.mst[1] + self.ny/2.)
        else:
            self.cxoff = self.cyoff = 0

    def showSelection(self):
        sentence = []
        sep = ': '
        d = 'default (%i)'
        u = 'unknown'

        s = 'start---%3d   stop---%3d   step---%s (%i)'
        things = [('time', self.nt, self._tIdx),
                  ('zsec', self.nz, self._zIdx),
                  ('wave', self.nw, self._wIdx),
                  ('y   ', self.shape[-2], self._yxSlice[0]),
                  ('x   ', self.shape[-1], self._yxSlice[1])]

        for title, n, idxNow in things:
            if type(idxNow) == slice:
                start = idxNow.start
                if start is None:
                    start = 0
                stop = idxNow.stop
                step = idxNow.step
                if step is None:
                    step = 1
                idxNow = range(int(start), int(stop), int(step))
            else:
                start = idxNow[0]
                stop = idxNow[-1] + 1          

            listed = list(idxNow)
            nn = len(listed)
            if listed == range(int(n)):
                sentence.append(sep.join((title, d % nn)))
            else:
                stepGuess = N.ceil((stop-start) / float(len(idxNow)))
                if N.alltrue(idxNow == range(start, stop, int(stepGuess))):
                    step = str(int(stepGuess))
                    sentence.append(sep.join((title, s % (start ,stop, step, nn))))
                else:
                    step = u
                    sentence.append(sep.join((title, s % (start ,stop, step, nn))))
                    if nn > 20:
                        tail = '...'
                    else:
                        tail = ''
                    sentence.append(' '*(len(title)+len(sep)) + ','.join([str(a) for a in listed[:20]]) + tail)

        return '\n'.join(sentence)

    def getYXslice(self, PriismFormat=None):
        """
        if PriismFormat is True, (X.start, X.size), (Y.start, Y.size)
        otherwise, yxslice
        """
        if PriismFormat: # XY start, size
            return ((self._YXslice[1].start, self._YXsize[1]), 
                    (self._YXslice[0].start, self._YXsize[0]))
        else:
            return self._YXslice

    def get3DArr(self, w=0, t=None, zs=None):
        """
        t: if None, use self.tSlice
        zs: if None, all z secs, else supply sequence of z sec
        
        return as (z,y,x) shape
        if self.useTinplaceofZ is True, return as (t,y,x) shape
        """
        if t is None:
            t = self.tSlice
        if zs is None:
            zs = range(self.nz)

        nz = len(zs)

        arr = N.empty((nz, self.ny, self.nx), self.dtype)
        for i, z in enumerate(zs):
            arr[i] = self.img.getArr(t=t, w=w, z=z)

        return arr

    # aui funcs
    def _yxslice2crop(self):
        self.cropbox_l[1] = self._yxSlice[0].start # y0
        self.cropbox_u[1] = self._yxSlice[0].stop # y1
        self.cropbox_l[2] = self._yxSlice[1].start # x0
        self.cropbox_u[2] = self._yxSlice[1].stop # x1


    # output funcs
    def setByteOrder(self, byteorder='<'):
        self.byteorder = byteorder

    
    # misc
    def view(self, idx=0, color=None):
        """
        idx: if viewer if already open, simply go to this idx
        """
        global _ZSLIDER
        if self.vid is None or Y.viewers[self.vid] is None:
            if color:
                old_ignor_color_axis = self.ignor_color_axis
                self.ignor_color_axis = True # don't know how to disable this
            arr = self[idx]
            
            if color and self.nw >= 2 and self.hdr.ImgSequence in [1,2]:
                #colorAxis = mrcIO.findAxis(self.hdr, self.shape, tzw='w')
                if self.hdr.ImgSequence in (0, 2):
                    colorAxis = 0
                elif self.hdr.ImgSequence == 1:
                    colorAxis = -3
                Y.view2(arr, colorAxis, self.file, originLeftBottom=1)
            else:
                Y.view(arr, self.file, originLeftBottom=1)

            viewer = Y.viewers[-1]
            self.vid = viewer.id

            if (self.nt * self.nz) > 1 or (self.nw > 1 and not color):
                nz = self.__getattribute__('n%s' % self.sld_axs)
                self._zslider = vzslider(self, self.vid, nz=nz, title='slide: axis %s of [%i]' % (self.sld_axs, self.vid))
                viewer.setSlider2 = _setSlider

                self._zslider.zslider.SetValue(idx)
                _ZSLIDER = self._zslider
            viewer._zslider = self._zslider
        else:
            if (self.nt * self.nz) > 1:
                import wx
                try:
                    self._setSlider(idx)
                    self._zslider.zslider.SetValue(idx)
                except wx.PyDeadObjectError:
                    self.vid = None
                    self.view(idx)

    def viewOneSec(self, t=0, z=0, w=0, dtype=None):
        i = mrcIO.sectIdx(t, self.nt, z, self.nz, w, self.nw, self.hdr.ImgSequence)
        a = self.Mrc.readSec(i)
        if dtype:
            a = a.astype(dtype)

        if self.vid_single is None:
            Y.view(a, originLeftBottom=1)
            viewer = Y.viewers[-1]
            self.vid_single = viewer.id
        else:
            try:
                v = Y.viewers[self.vid_single]
                v.viewer.my_spv.data[:] = a[:]
                v.viewer.m_imgChanged = True
                v.viewer.Refresh()
            except AttributeError:
                self.vid_single = None
                self.viewOneSec(t,z,w)

    def _setSlider(self, z, zaxis=0): #copied from viewerCommon
        '''
        overloaded used for viewer for MrcHandler
        zaxis is a dummy argument, axis is always zero
        '''
        if zaxis == 0:
            arr = self[z]
            v = Y.viewers[self.vid]
            v.viewer.my_spv.data[:] = arr[:]
            Y.vReload(self.vid)
        else:
            pass

### slider

def _setSlider(v, handle, z, zaxis=0): #copied from viewerCommon
    '''
    overloaded used for viewer for MrcHandler
    zaxis is a dummy argument, axis is always zero
    '''
    if zaxis == 0:
        arr = handle[z]
        v.viewer.my_spv.data[:] = arr[:]
        Y.vReload(v.id)
    else:
        pass

def vzslider(handler, idx=-1, nz=2, zaxis=0, title=None):
    """
    show a 'personal slider' window
    idx: for Y.view viewer id
    """
    v = Y.viewers[idx]
    if title is None:
        title = "slide:" + str(v.id)

    def onz(z, dummy=None):
        v.setSlider2(v, handler, z, zaxis)
    def onclose():
        try:
            id = v.id
            f = v.viewer.GetTopLevelParent()
            f.Destroy()
            Y.viewers[id] = None
        except:
            pass

    zs = MyZSlider(nz, title)
    if zs.Prii == 'new':
        zs.doOnZchange = [onz]
    else:
        zs.doOnZchange = onz
    zs.doOnClose = onclose
    return zs

try:
    try: # inside package
        from ..Priithon import zslider
    except ValueError: # Attempted relative import beyond toplevel package
        from Priithon import zslider
    #from Priithon import zslider

    class MyZSlider(zslider.ZSlider):
        """
        added functions --  key operations + flexible closing
        """
        def __init__(self, nz, title=''):
            import wx
            zslider.ZSlider.__init__(self, nz, title)
            self.z = 0
            self.zmax = nz

            if type(self.doOnZchange) == list:
                self.Prii = 'new'
            else:
                self.Prii = 'old'
            wx.EVT_KEY_DOWN(self, self.OnKeys)
            wx.EVT_CLOSE(self, self.OnCloseWindow)

        def __del__(self):
            self.OnCloseWindow()

        def OnCloseWindow(self, evt):
            global _ZSLIDER
            self.doOnClose()
            self.Destroy()
            _ZSLIDER = None

        def doOnClose(self):
            pass

        def OnKeys(self, evt):
            import wx
            code = evt.KeyCode
            altDown = evt.AltDown()

            if altDown and code == wx.WXK_LEFT:
                self.z = 1
            if altDown and code == wx.WXK_RIGHT:
                self.z = self.zmax
            elif code == wx.WXK_LEFT:
                self.z = self.zslider.GetValue() - 1
                if self.z < 0:
                    self.z = self.zmax
            elif code == wx.WXK_RIGHT:
                self.z = self.zslider.GetValue() + 1
                if self.z >= self.zmax:
                    self.z = 0

            if self.Prii == 'new':
                for f in self.doOnZchange:
                    f(int(self.z))
            else:
                self.doOnZchange(int(self.z))
            self.zslider.SetValue(self.z)

except ImportError:
    pass

_COLORS =['P', 'B', 'C', 'G', 'Y', 'R', 'IR']
_COLOR_NAME=['purple', 'blue', 'cyan', 'green', 'yellow', 'red', 'black']
_WAVES=[400, 450, 500, 530, 560, 600, 700]


class DimDialog(wx.Dialog):
    def __init__(self, parent=None, fns=[]):
        """
        dimension selection dialog for multipage tif

        fns: filenames

        use like
        >>> dlg = FileSelectorDialog()
        >>> if dlg.ShowModal() == wx.ID_OK:
        >>>     fns = dlg.GetPaths()
        """
        wx.Dialog.__init__(self, parent, -1, title='Image Dimensions')

        nfns = len(fns)
        
        sizer = wx.BoxSizer(wx.VERTICAL)

        hsz = wx.FlexGridSizer(nfns+1, 13, 0, 0)
        sizer.Add(hsz, 0, wx.EXPAND)

        # header
        G.makeTxt(self, hsz, 'Directory')
        G.makeTxt(self, hsz, 'Filename')
        G.makeTxt(self, hsz, 'Sequence')
        G.makeTxt(self, hsz, 'time')
        G.makeTxt(self, hsz, '    color: ')
        for i, col in enumerate(_COLORS):
            b = G.makeTxt(self, hsz, col)
            b.SetForegroundColour(_COLOR_NAME[i])
        G.makeTxt(self, hsz, '     Z')

        # file
        self.holders = []
        for fn in fns:
            h = DimDataHolder(fn)
            self.holders.append(h)
            
            G.makeTxt(self, hsz, h.direc)
            G.makeTxt(self, hsz, h.basename)

            label, h.seqChoice = G.makeListChoice(self, hsz, '', imgfileIO.generalIO.IMGSEQ, defValue=h.seq, targetFunc=self.onSeq)#imgfileIO.generalIO.IMGSEQ[h.seq], targetFunc=self.onSeq)
            
            comm_divs = [str(i) for i in range(1, h.nsec+1) if not h.nsec % i]
            label, h.ntChoice = G.makeListChoice(self, hsz, '', comm_divs, defValue=h.nt, targetFunc=self.onNumTimes)

            G.makeTxt(self, hsz, '')
            defcols = [_COLORS[_WAVES.index(w)] for w in h.waves]
            h.nwChecks = [G.makeCheck(self, hsz, "", defChecked=(col in defcols), targetFunc=self.onWaves) for col in _COLORS]
            
            h.nzlabel = G.makeTxt(self, hsz, str(int(h.getZ())), flag=wx.ALIGN_RIGHT)

        bsz = wx.StdDialogButtonSizer()
        sizer.Add(bsz, 0, wx.EXPAND)

        button = wx.Button(self, wx.ID_CANCEL)
        bsz.AddButton(button)
        
        self.okbutton = wx.Button(self, wx.ID_OK)
        bsz.AddButton(self.okbutton)

        bsz.Realize()
            
        self.SetSizer(sizer)
        sizer.Fit(self)

    def onSeq(self, evt=None):
        ID = evt.GetId()
        h = self.findItem(ID, 'seq')

        h.seq = h.seqChoice.GetStringSelection()
        
    def onNumTimes(self, evt=None):
        """
        
        """
        ID = evt.GetId()
        h = self.findItem(ID, 'nt')

        h.nt = int(h.ntChoice.GetStringSelection())
        self.setZ(h)

    def onWaves(self, evt=None):
        ID = evt.GetId()
        h = self.findItem(ID, 'nw')

        h.waves = [_WAVES[i] for i, ch in enumerate(h.nwChecks) if ch.GetValue()]

        h.nw = len(h.waves)
        self.setZ(h)
        
    def setZ(self, h):
        z = h.getZ()
        if z % 1:
            h.nzlabel.SetLabel(str(z))
            h.nzlabel.SetForegroundColour('Red')
            self.okbutton.Enable(0)
        else:
            h.nzlabel.SetLabel(str(int(z)))
            h.nzlabel.SetForegroundColour('Black')
            self.okbutton.Enable(1)
            

    def findItem(self, ID, what='nt'):
        found = False
        for h in self.holders:
            ids = h.getId(what)
            if (what in ['nt', 'seq'] and ids == ID) or (what == 'nw' and ID in ids):
                found = True
                break
        if not found:
            raise ValueError, 'the corresponding id not found'

        return h

class DimDataHolder(object):
    def __init__(self, fn):
        self.fn = fn

        self.direc, self.basename = os.path.split(fn)

        img = load(fn)
        self.nsec = img.hdr.Num[-1]
        img.close()

        self.seqChoice = None
        self.seq = imgfileIO.generalIO.IMGSEQ[img.hdr.ImgSequence]
        
        self.nt = img.hdr.NumTimes
        self.ntChoice = None
        self.nw = img.hdr.NumWaves
        colors = ['R', 'G', 'B'][:self.nw]
        self.waves = [_WAVES[_COLORS.index(c)] for c in colors]
        self.nwChecks = []
        self.nzlabel = None

    def getZ(self):
        return self.nsec / (self.nt * self.nw)

    def getId(self, what='nt'):
        """
        what: nt or nw or seq
        return nt->ID, or nw->list_of_IDs
        """
        if what == 'nt' and self.ntChoice:
            return self.ntChoice.GetId()
        elif what == 'nw':
            return [ch.GetId() for ch in self.nwChecks]
        elif what == 'seq':
            return self.seqChoice.GetId()
