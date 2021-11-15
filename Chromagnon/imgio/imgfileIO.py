
# This module is not used anymore...


from . import generalIO, microscope
import six

try: # multitiff
    import tifffile
except ImportError:
    pass

try: # general images
    from PIL import Image
    import sys
except ImportError:
    try:
        import Image
        import sys
    except ImportError:
        pass
import numpy as N
import re
from . import fntools
#try:
#    from ..Priithon.all import U
#except ValueError:
#    from Priithon.all import U

try: # dimension reader
    import wx
    from . import guiFuncs as G
    import os
except ImportError:
    pass


# dimension reader colors
_COLORS =['P', 'B', 'C', 'G', 'Y', 'R', 'IR']
_COLOR_NAME=[c for c in microscope.COLOR_NAME[:7]]#'purple', 'blue', 'cyan', 'green', 'yellow', 'red', 'black']
_WAVES=[w - 10 for w in microscope.WAVE_CUTOFF]#400, 450, 500, 530, 560, 600, 700]
        
###---------- multipage tif -----------####

IMGEXTS_MULTITIFF=('tif', 'tiff')


class MultiTiffReader(generalIO.GeneralReader):
    def __init__(self, fn):
        """
        fn: file name
        """
        generalIO.GeneralReader.__init__(self, fn)

    def openFile(self):
        """
        open a file for reading
        """
        self.fp = tifffile.TiffFile(self.fn)
        self.handle = self.fp.filehandle
        
        self.readHeader()

    def readHeader(self):
        
        s = self.fp.series[0]
        shape = s.shape
        axes = s.axes.replace('S', 'W')    # sample (rgb)
        axes = axes.replace('C', 'W')      # color, emission wavelength
        axes = axes.replace('E', 'W')      # excitation wavelength
        if 'Z' not in axes:
            axes = axes.replace('I', 'Z')  # general sequence, plane, page, IFD
        elif 'W' not in axes:
            axes = axes.replace('I', 'W')
        elif 'T' not in axes:
            axes = axes.replace('I', 'T')
        if 'Z' not in axes:
            axes = axes.replace('Q', 'Z') # other
        elif 'W' not in axes:
            axes = axes.replace('Q', 'W')
        elif 'T' not in axes:
            axes = axes.replace('Q', 'T')

        nz = nt = nw = 1
        if 'Z' in axes:
            zaxis = axes.index('Z')
            nz = shape[zaxis]

        if 'T' in axes:
            taxis = axes.index('T')
            nt = shape[taxis]
        
        if 'W' in axes:
            waxis = axes.index('W')
            nw = shape[waxis]
            if nw > 5:
                # other systems are not always limited to 5 wavelengths
                temp="""
                if nz == 1:
                    nz = nw
                    nw = 1
                elif nt == 1:
                    nt = nw
                    nw = 1
                else:
                    maxw = 5
                    while nw % maxw:
                        maxw -= 1
                    nz *= nw // maxw
                    nw = maxw"""
        waves = [600, 500, 450, 700, 400][:nw]

        #print waves
        imgSeq = self.findImgSequence(axes[:-2])
        
        p = self.fp.pages[0]

        self.dataOffset = p._byte_counts_offsets[1][0]
        if len(self.fp.pages) > 1:
            self._secExtraByteSize = self.fp.pages[1]._byte_counts_offsets[1][0] - self.fp.pages[0]._byte_counts_offsets[1][0] - self.fp.pages[0]._byte_counts_offsets[0][0]
        else:
            self._secExtraByteSize = 0

        self.setDim(p.image_width, p.image_length, nz, nt, nw, s.dtype, waves, imgSeq, p.samples_per_pixel)
        
        self.axes = p.axes # axis of one section
        self.compress = p.compression

        # since imageJ stores all image metadata in the first page
        if self.fp.is_imagej or self.readSec(0).ndim > 2:
            self.arr = self.fp.pages[0].asarray()
            
        
    def seekSec(self, i=0):
        p = self.fp.pages[i]
        byte_counts, offsets = p._byte_counts_offsets

        self.handle.seek(offsets[0])
        
    def readSec(self, i=None):
        """
        return the section at the number i in the file
        if i is None: return current position (not fast though)
        """
        if i is None:
            i = self.tellSec() + 1 # handle go back to the beggining of the page after reading...

        if self.fp.is_imagej or hasattr(self, 'arr'):
            return self.arr[int(i)]
        else:
            return self.fp.pages[int(i)].asarray() 


class MultiTiffWriter(generalIO.GeneralWriter):
    def __init__(self, fn, mode=None, imagej=False):
        """
        mode is 'wb' whatever the value is...
        """
        self.imagej = imagej
        generalIO.GeneralWriter.__init__(self, fn, mode)

        self.initialized = False

    def openFile(self):
        """
        open a file for reading
        """
        self.fp = tifffile.TiffWriter(self.fn, bigtiff=not(self.imagej), imagej=self.imagej)

        self.handle = self.fp._fh
        self.dataOffset = self.handle.tell()
        self.imgSequence = 2 # my code uses t->w->z, suite yourself...
        
        self.setParameters()
        
    def setParameters(self, compress=None, colormap=None, metadata={}):
        self.compress = compress
        self.colormap = colormap
        if hasattr(self, 'metadata'):
            self.metadata.update(metadata)
        else:
            self.metadata = metadata

    def doOnSetDim(self):
        ### unfortunately, below code does not work...
        imgseq_str = generalIO.IMGSEQ[self.imgSequence]
        if self.nt == 1:
            imgseq_str = imgseq_str.replace('T', '')
        if self.nz == 1:
            imgseq_str = imgseq_str.replace('Z', '')
        if self.nw == 1:
            imgseq_str = imgseq_str.replace('W', '')
        else:
            imgseq_str = imgseq_str.replace('W', 'C')

        ### so, all image data become ZYX...
        self.metadata.update({'axes': 'ZYX'})#imgseq_str + 'YX'})
        
    def writeSec(self, arr, i=None):
        self.fp.save(arr, compress=self.compress, colormap=self.colormap, metadata=self.metadata, contiguous=True)

    def write3DArr(self, arr, t=0, w=0):
        """
        write a 3D stack according to the given dimensions
        """
        if arr.ndim != 3:
            raise ValueError('arr must be 3-dimensions')

        # this does not work... 
        if 0:#self.imgSequence in [0, 2]:
            idx = self.findFileIdx(t=t, z=0, w=w)
            self.seekSec(idx)
            self.setParameters(metadata={'axes': 'ZYX'})
            self.fp.save(arr, compress=self.compress, colormap=self.colormap, metadata=self.metadata)
        # all image data are written as they go.
        else:
            for z, a in enumerate(arr):
                self.writeArr(a, t=t, w=w, z=z)


###---------- sequence of images -----------###

class ImgSeqReader(generalIO.GeneralReader):
    def __init__(self, fns, mode='r'):
        """
        The fns must be a sequence of simgle image files.
        RGB images are not accepted.
        """
        if isinstance(fns, six.string_types) and os.path.isdir(fns):
            fns = [os.path.join(fns, fn) for fn in os.listdir(fns)]
        elif type(fns) not in [list, set, tuple]:
            raise ValueError('fns must be a directry, or list, set or tuple of filenames')

        self.fns = fns
        generalIO.GeneralReader.__init__(self, fns[0])

    def closed(self):
        return hasattr(self, 'fp')
        
    def openFile(self):
        #self.fns = self.filename
        self.fns.sort()
        self.file = os.path.commonprefix([os.path.basename(fn) for fn in self.fns])
        self.filename = os.path.commonprefix(self.fns)

        self.i = 0

        if 'r' in self.mode:
            self.readHeader()

    def readHeader(self):
        self.fp = Image.open(self.fn)
        t,nc, ny,nx, isSwapped = _getImgMode(self.fp)

        nztw, imgSeq = self.determineDimFromName()
        wrange = range(nztw[2] or 1)
        waves = [RGB for i, RGB in enumerate([515, 625, 450, 700, 350]) if i in wrange]

        self.isSwapped = isSwapped
        self.setDim(nx, ny, nztw[0] or 1, nztw[1] or 1, nztw[2] or 1, t, waves, imgSeq)#, isSwapped=isSwapped)

    def determineDimFromName(self):
        fns = [os.path.basename(fn) for fn in self.fns]
        nztw = []
        name = []
        for ds in ['[zZ]', '[tT]', '[wcWC]']:
            #val = self.__getattribute__(ds)
            if 1:#val:
                pat = re.compile('_%s[0-9]+' % ds)
                ndim = pat.findall(fns[0])
                if ndim:
                    nn = len(set([pat.findall(fn)[-1][2:] for fn in fns]))
                    nztw.append(nn)
                    name.append(ds)
                else:
                    nztw.append(None)

        # 0=ZTW, 1=WZT, 2=ZWT, 3=TZW
        # determine imgseq
        if len(name) == 1:
            imgseq = 0
        elif len(name) == 2:
            patstr = '_%s[0-9]+_%s[0-9]+'
            table = {0: [('[wcWC]','[tT]'), ('[wcWC]', '[zZ]'), ('[tT]', '[zZ]')],
                     1: [('[tT]', '[wcWC]'), ('[zZ]', '[wcWC]')],
                     3: [('[zZ]', '[tT]')]}
            for _imgseq, stlist in table.items():
                for st in stlist:
                    pat = re.compile(patstr % tuple(st))
                    if pat.search(self.fns[0]):
                        imgseq = _imgseq
                        break
        elif len(name) == 3:
            patstr = '_%s[0-9]+_%s[0-9]+_%s[0-9]+'
            pats = [seq.lower() for seq in [('[zZ]', '[tT]', '[wcWC]'), ('[wcWC]', '[zZ]', '[tT]'), ('[zZ]', '[wcWC]', '[tT]')]]#IMGSEQ]#['ztw', 'wzt', 'zwt']
            for imgseq, st in enumerate(pats):
                pat = re.compile(patstr % tuple(st))
                if pat.search(self.fns[0]):
                    break

        return nztw, imgseq


    # getting array

    def readSec(self, i=0):
        if self.fp.filename != self.fns[i]:
            self.fp = Image.open(self.fns[i])
        
        self.fp.seek(0)

        a = N.fromstring(self.fp.tobytes(), self.dtype)
        a.shape = (self.ny, self.nx)

        if self.isSwapped:
            a.byteswap(True)
            
        return a

def _getImgMode(im):
    """
    This function is from Priithon.Useful.py
    """
    cols = 1
    BigEndian = False
    if im.mode   == "1":
        t = N.uint8
        cols = -1
    elif im.mode == "L" or \
         im.mode == "P": #(8-bit pixels, mapped to any other mode using a colour palette)
        t = N.uint8
    elif im.mode == "I;16":
        t = N.uint16
    elif im.mode == "I":
        t = N.uint32
    elif im.mode == "F":
        t = N.float32
    elif im.mode == "RGB":
        t = N.uint8
        cols = 3
    elif im.mode in ("RGBA", "CMYK", "RGBX"):
        t = N.uint8
        cols = 4
    elif im.mode == "I;16B":  ## big endian
        t = N.uint16
        BigEndian = True
    else:
        raise ValueError("can only convert single-layer images (mode: %s)" % (im.mode,))

    nx,ny = im.size

    isSwapped = (BigEndian and sys.byteorder=='little' or not BigEndian and sys.byteorder == 'big')
        
    return t,cols, ny,nx, isSwapped


#------ Below, not yet done -----#

class ImgSeqWriter(generalIO.GeneralWriter):
    def __init__(self, basefn, mode='w'):
        """
        multipage: need to use setHdr() or setDim()
        rgbOrder: rgb, rgba etc... 
        """
        generalIO.GeneralWriter.__init__(self, basefn, mode)
        
        base, self.format = os.path.splitext(basefn)
        
        if self.format.lower() not in Image.EXTENSION:
            raise ValueError('Please supply file extension')

        self.rgbOrder = 'rgb'
        self._rescaleTo8bit = False
        self.saveOptions = {}

    def openFile(self):
        self.fp = None
        
    # funcs for output
    def rescaleTo8bit(self, arr=None):
        """
        arr: your whole array
        if multipage: you have to execute this function before writing arr
        if arr is None, then rescale section-wise
        """
        if hasattr(self, 'nw') and self.nw != len(self.rgbOrder):
            if arr is not None and self.nw in arr.shape:
                shape = list(arr.shape)
                self.setColorAxis(shape.index(self.nw))
            else:
                print('WARNING: number of wavelength %i does not match with rgbOrder %s, use setColorAxis() to set color axis' % (self.nw, self.rgbOrder))

        if arr is None:
            self._rescaleTo8bit = True
        else:
            ma, mi = float(arr.max()), float(arr.min())
            self._rescaleTo8bit = (mi, ma-mi)

        # refresh suffix
        if hasattr(self, 'dtype') and not hasattr(self, 'outsuf'):
            self._setSuffix()

        self.dtype = N.uint8

    def setSaveOptions(self, **options):
        """
        jpg: quality, optimized, progressive etc...
        """
        self.saveOptions.update(options)

        
    # functions for series
    def setDim(self, nx, ny, nz, nt, nw, dtype, wave=[], imgSequence=0):
        self.wave = wave
        self.nw = nw
        self.nt = nt
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.imgSequence = imgSequence
        self.dtype = dtype

        #if self.multipage:
        #    self._setSecSize()
        #else:
        self._setSuffix()

    def setDimFromMrcHdr(self, hdr):
        try:
            from . import Mrc
        except ImportError:
            import Mrc
        self.wave = hdr.wave
        self.nw = hdr.NumWaves
        self.nt = hdr.NumTimes
        self.nx = hdr.Num[0]
        self.ny = hdr.Num[1]
        self.nz = hdr.Num[2] // (self.nt * self.nw)
        self.imgSequence = hdr.ImgSequence
        self.dtype = Mrc.MrcMode2dtype(hdr.PixelType)

        #if self.multipage:
        #    self._setSecSize()
        #else:
        self._setSuffix()

    # funcs for single imgs
    def _setSuffix(self):
        suffix = ''
        imgseq = generalIO.IMGSEQ[self.imgSequence].lower()
        if (self._rescaleTo8bit or self.dtype == N.uint8) and self.rgbOrder:
            imgseq = imgseq.replace('w', '')
            
        for d in generalIO.IMGSEQ[self.imgSequence].lower():
            ns = self.__getattribute__('n%s' % d) - 1
            if ns:
                digit = int(N.log10(ns*10))
                prefix = '_%s' % d
                suffix +=  prefix + '%0' + str(digit) + 'd'
        self.outsuf = fntools.appendToBasename(self.fn, suffix)
        self.wtz_name = [wtz[0] for wtz in suffix.split('_')[1:]]

    def _getOutFn(self, t=0, w=0, z=0):
        dic = {'w': w, 't': t, 'z': z}
        return self.outsuf % tuple([dic[name] for name in self.wtz_name])

    # writing
    def writeSec(self, arr, i=0, singleOutFn=None):
        if self._rescaleTo8bit:
            if self._rescaleTo8bit is True:
                self.rescaleTo8bit(arr)
            arr = (arr-self._rescaleTo8bit[0])*255./self._rescaleTo8bit[1]

        # astype changes byteorder as well
        arr = arr.astype(self.dtype)
        
        img = U.array2image(arr, rgbOrder=self.rgbOrder)

        if not singleOutFn:
            singleOutFn = self.outfn
        img.save(singleOutFn, **self.saveOptions)

    def writeArrSingle(self, arr):
        self.writeSec(arr)

    def writeArr(self, arr, t=0, w=0, z=0):
        # fill rgb
        if self.rgbOrder and self._rescaleTo8bit:
            nemptycol = len(self.rgbOrder) - self.nw
            if nemptycol <= 4 and nemptycol > 0:
                fill = N.zeros((nemptycol, self.ny, self.nx), arr.dtype.type)
                arr = N.concatenate((arr.reshape((1,self.ny,self.nx)), fill))
            else:
                self.rgbOrder = None

        # write out
        outfn = self._getOutFn(t=t, w=w, z=z)
        self.writeSec(arr, singleOutFn=outfn)


    def write3DArr(self, arr, t=0, w=0):
        # RGB color axis correction -> 1
        if arr.ndim == 4 and self.rgbOrder and (self._rescaleTo8bit or self.dtype == N.uint8):
            shapezw = list(arr.shape[:-2])
            if self.nw not in shapezw:
                raise ValueError('number of wavelength %i was not found in the given array shape %s' % (self.nw, self.shape))
            # color axis
            waxis = shapezw.index(self.nw)
            if waxis == 0:
                arr = arr.transpose((1,0,2,3))


        for z, a in enumerate(arr):
            self.writeArr(a, t=t, w=w, z=z)


## ------ Dimension dialog --------------------
            
class DimDialog(wx.Dialog):
    def __init__(self, parent=None, fns=[], defPxlSiz=0.1):
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

        hsz = wx.FlexGridSizer(nfns+1, 14, 0, 0)
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
        G.makeTxt(self, hsz, 'Pixel size (um)')

        # file
        self.holders = []
        for fn in fns:
            h = DimDataHolder(fn, defPxlSiz)
            self.holders.append(h)
            
            G.makeTxt(self, hsz, h.direc)
            G.makeTxt(self, hsz, h.basename)

            label, h.seqChoice = G.makeListChoice(self, hsz, '', generalIO.IMGSEQ, defValue=h.seq, targetFunc=self.onSeq)#imgfileIO.generalIO.IMGSEQ[h.seq], targetFunc=self.onSeq)
            
            comm_divs = [str(i) for i in range(1, h.nsec+1) if not h.nsec % i]
            label, h.ntChoice = G.makeListChoice(self, hsz, '', comm_divs, defValue=h.nt, targetFunc=self.onNumTimes)

            G.makeTxt(self, hsz, '')
            defcols = [_COLORS[_WAVES.index(w)] for w in h.waves]
            h.nwChecks = [G.makeCheck(self, hsz, "", defChecked=(col in defcols), targetFunc=self.onWaves) for col in _COLORS]
            
            h.nzlabel = G.makeTxt(self, hsz, str(int(h.getZ())), flag=wx.ALIGN_RIGHT)

            h.pxlsiz_txt = wx.TextCtrl(self, -1, '%.2f' % h.pxlsiz, size=(50,-1))
            hsz.Add(h.pxlsiz_txt)
            #label, self.pxlsiz_txt = G.makeTxtBox(self, hsz, '', '0.10', tip='The size of a pixel after magnification', sizeX=50)
            wx.EVT_TEXT(self, h.pxlsiz_txt.GetId(), self.onPxlSiz)
            
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
            if (what in ['nt', 'seq', 'pxlsiz'] and ids == ID) or (what == 'nw' and ID in ids):
                found = True
                break
        if not found:
            raise ValueError('the corresponding id not found')

        return h

    def onPxlSiz(self, evt=None):
        ID = evt.GetId()
        h = self.findItem(ID, 'pxlsiz')
        try:
            h.pxlsiz = float(h.pxlsiz_txt.GetValue())
        except (TypeError, ValueError):
            pass
    
class DimDataHolder(object):
    def __init__(self, fn, defPxlSiz=0.1):
        self.fn = fn

        self.direc, self.basename = os.path.split(fn)

        img = load(fn)
        self.nsec = img.hdr.Num[-1]
        img.close()

        self.seqChoice = None
        self.seq = generalIO.IMGSEQ[img.hdr.ImgSequence]
        
        self.nt = img.hdr.NumTimes
        self.ntChoice = None
        self.nw = img.hdr.NumWaves
        colors = ['R', 'G', 'B'][:self.nw]
        self.waves = [_WAVES[_COLORS.index(c)] for c in colors]
        self.nwChecks = []
        self.nzlabel = None
        self.pxlsiz = defPxlSiz#0.1

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
        elif what == 'pxlsiz':
            return self.pxlsiz_txt.GetId()
