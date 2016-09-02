from Priithon import Mrc
import numpy as N
from PriCommon import generalIO


# 'Image sequence. 0=ZTW, 1=WZT, 2=ZWT (idx = [2,1,0])

class MrcReader(generalIO.GeneralReader):
    def __init__(self, fn, mode='r'):
        generalIO.GeneralReader.__init__(self, fn, mode)


    def openFile(self):
        self.fp = Mrc3(self.fn, self.mode)
        self.handle = self.fp._f

        if 'r' in self.mode:
            self.readHeader()

    def readHeader(self):

        self.dataOffset = self.fp._dataOffset
        self._secExtraByteSize = 0
        
        nx = self.fp.hdr.Num[0]
        ny = self.fp.hdr.Num[1]
        nt = self.fp.hdr.NumTimes
        nw = self.fp.hdr.NumWaves
        nz = self.fp.hdr.Num[2] // (nt * nw)
        dtype = self.fp._dtype
        wave = self.fp.hdr.wave[:nw]
        imgseq = self.fp.hdr.ImgSequence
        
        self.setDim(nx, ny, nz, nt, nw, dtype, wave, imgseq)

        self.fp.setByteOrder()
        self.pxlsiz = self.fp.hdr.d[::-1]

        self.hdr = self.fp.hdr

        self.fp._secByteSize = self._secByteSize


    def getArr(self, t=0, z=0, w=0):
        i = self.findFileIdx(t, z, w)

        return self.fp.readSec(i)


class MrcWriter(generalIO.GeneralWriter):
    def __init__(self, outfn, hdr, extInts=None, extFloats=None, byteorder='='):
        """
        prepare your hdr and output filename
        """
        generalIO.GeneralWriter.__init__(self, outfn, mode='w')

        self.writeHeader(hdr, extInts, extFloats, byteorder)

        old="""
        nx = self.fp.hdr.Num[0]
        ny = self.fp.hdr.Num[1]
        nt = self.fp.hdr.NumTimes
        nw = self.fp.hdr.NumWaves
        nz = self.fp.hdr.Num[2] // (nt * nw)
        dtype = self.fp._dtype
        wave = self.fp.hdr.wave[:nw]
        imgseq = self.fp.hdr.ImgSequence
        
        self.setDim(nx, ny, nz, nt, nw, dtype, wave, imgseq)"""

        self.setDimFromMrcHdr(hdr)

        self.init()
        
    def openFile(self):
        if hasattr(self, 'fp'):
            self.mode = 'r+'
        self.fp = Mrc3(self.fn, self.mode)

        self.handle = self.fp._f

    def init(self):
        self.fp._secByteSize = self._secByteSize
        #self.fp._dtype = self.dtype
        
        
    def writeHeader(self, hdr, extInts=None, extFloats=None, byteorder='='):
        
        Mrc.initHdrArrayFrom(self.fp.hdr, hdr)
        self.fp.hdr.Num = hdr.Num
        self.fp.hdr.PixelType = hdr.PixelType

        self.fp._initWhenHdrArraySet()

        if extInts is not None or extFloats is not None:
            if extInts is None:
                extInts = N.zeros((1,1))
            if extFloats is None:
                extFloats = N.zeros((1,1))
                
            self.fp = addExtHdrFromExt(self.fp, hdr.NumIntegers,
                                        hdr.NumFloats, extInts, extFloats)
            self.fp.hdr.NumIntegers = self.fp.extInts.shape[-1]
            self.fp.hdr.NumFloats = self.fp.extFloats.shape[-1]

        self.fp.setByteOrder(byteorder)

        self.fp.writeHeader()
        if hasattr(self.fp, 'extInts') or hasattr(self.fp, 'extFloats'):
            self.fp.writeExtHeader(True)


        self.hdr = self.fp.hdr

    def writeArr(self, arr2D, w=0, t=0, z=0):
        i = self.findFileIdx(t, z, w)

        self.fp.writeSec(arr2D, i)


# functions

def init_simple(hdr, mode, nxOrShape, ny=None, nz=None):
    '''note: if  nxOrShape is tuple it is nz,ny,nx (note the order!!)
    '''
    if ny is nz is None:
        if len(nxOrShape) == 2:
            nz,(ny,nx)  = 1, nxOrShape
        elif len(nxOrShape) == 1:
            nz,ny,nx  = 1, 1, nxOrShape
        elif len(nxOrShape) == 3:
            nz,ny,nx  = nxOrShape
        else:
            ny,nx  = nxOrShape[-2:]
            nz     = N.prod(nxOrShape[:-2])
            
    else:
        nx = nxOrShape

    for field in hdr.__slots__:
        if field == 'Num': hdr.Num = (nx,ny,nz)
        elif field == 'PixelType': hdr.PixelType = mode
        elif field in ('mst', 'tilt', 'zxy0'): exec('hdr.%s = (0,0,0)' % field)
        elif field in ('wave'): exec('hdr.%s = (0,0,0,0,0)' % field)
        elif field in ('m', 'd'): exec('hdr.%s = (1,1,1)' % field)
        elif field in ('angle'): exec('hdr.%s = (90,90,90)' % field)
        elif field in ('axis'): exec('hdr.%s = (1,2,3)' % field)
        elif field in ('mm1'): exec('hdr.%s = (0,100000,5000)' % field)
        elif field in ('mm2, mm3, mm4, mm5'): exec('hdr.%s = (0,10000)' % field)
        elif field == 'divid': hdr.divid = 0xc0a0
        elif field == 'title': hdr.title = '\0' * 80
        elif field in ('NumTimes', 'NumWaves'): exec('hdr.%s = 1' % field)
        elif field.startswith('_'): continue
        else: exec('hdr.%s = 0' % field)

def makeHdr_like(hdrSrc):
    hdr = Mrc.makeHdrArray()
    init_simple(hdr, hdrSrc.PixelType, hdrSrc.Num[::-1])
    Mrc.initHdrArrayFrom(hdr, hdrSrc)
    hdr.NumTimes = hdrSrc.NumTimes
    hdr.NumWaves = hdrSrc.NumWaves
    hdr.NumIntegers = hdrSrc.NumIntegers
    hdr.NumFloats = hdrSrc.NumFloats
    return hdr

def addExtHdrFromExt(hdl, numInts=0, numFloats=0, extInts=None, extFloats=None):
    nSecs = hdl.hdr.Num[2]
    #numInts, numFloats = extInts.shape[-1], extFloats.shape[-1]
    hdl.makeExtendedHdr(numInts, numFloats, nSecs=nSecs) # this creates many instances

    hdl.extInts = _reshapeExtHdr(hdl.extInts)
    hdl.extFloats = _reshapeExtHdr(hdl.extFloats)
    extInts = _reshapeExtHdr(extInts)
    extFloats = _reshapeExtHdr(extFloats)    

    hdl.extInts[:nSecs,:numInts] = extInts[:nSecs,:numInts]
    hdl.extFloats[:nSecs,:numFloats] = extFloats[:nSecs,:numFloats]

    return hdl

def _reshapeExtHdr(extHdr):
    if extHdr.ndim == 1:
        extHdr = extHdr.reshape(extHdr.shape + (1,))
    return extHdr


#### imgManager ####
def shapeFromNum(Num, NumWaves=1, NumTimes=1, imgSequence=1):
    nz = Num[2] // (int(NumWaves) * int(NumTimes)) # int() to avoid byte swap
    if imgSequence == 0:
        shape = [NumWaves, NumTimes, nz, Num[1], Num[0]]
    elif imgSequence == 1:
        shape = [NumTimes, nz, NumWaves, Num[1], Num[0]]
    elif imgSequence == 2:
        shape = [NumTimes, NumWaves, nz, Num[1], Num[0]]
    elif imgSequence == 3:
        shape = [NumWaves, nz, NumTimes, Num[1], Num[0]]
    return _slimShape(shape)

def shapeFromHdr(hdr):
    return shapeFromNum(hdr.Num, hdr.NumWaves, hdr.NumTimes, hdr.ImgSequence)

def _slimShape(shape): # N.squeeze does it
    shape = list(shape)
    ones = shape.count(1)
    for i in range(ones):
        shape.remove(1)
    return tuple(shape)


def getWaveFromHdr(hdr, wave):
    """
    return wavelength
    """
    wave = int(wave)
    nw = hdr.NumWaves
    if wave in hdr.wave[:nw]:
        return wave
    elif wave < nw: # idx
        return hdr.wave[wave]
    else:
        raise ValueError, 'no such wave exists %s' % wave

def getWaveIdxFromHdr(hdr, wave):
    """
    return index
    """
    wave = int(wave)
    nw = hdr.NumWaves
    if wave in hdr.wave[:nw]:
        wave = list(hdr.wave).index(wave)
        return wave
    elif wave < nw:
        return wave
    else:
        raise ValueError, 'no such wave exists %s' % wave


def recalcMinMax(fn):
    """
    update scale in the header
    """
    h = MrcReader(fn)
    hdr = makeHdr_like(h.hdr)

    o = Mrc3(fn, 'r+')

    for w in xrange(h.nw):
        mi, ma = None, None
        su = 0
        for t in xrange(h.nt):
            a = h.get3DArr(t=t, w=w)
            mi0 = a.min()
            if mi is None or mi0 < mi:
                mi = mi0
            ma0 = a.max()
            if ma is None or ma0 > ma:
                ma = ma0
            su += a.sum()
        if w == 0:
            me = su / (h.nt * h.nz)
            o.hdr.mmm1 = mi, ma, me
        else:
            exec('o.hdr.mm%i = %f, %f' % (w+1, mi, ma))

    h.close()

    o.writeHeader()
    
    o.close()
    
#####


class Mrc3(Mrc.Mrc2):
    """
    The adapter for SoftWorx compatible Mrc format
    """
    def __init__(self, path, mode='r'):
        """
        path is filename
        mode: same as for Python's open function
            ('b' is implicitely appended !)
            'r'   read-only
            'r+'  read-write
            'w'   write - erases old file !!
        """
        Mrc.Mrc2.__init__(self, path, mode)


    def setByteOrder(self, byteorder='<'):
        """
        This method is intended to turn Mrc files into the SoftWorx-compatible format
        this should be called before writing down data and header
        """
        if self._mode in ['r+', 'w'] and (byteorder != '=' or (byteorder == '=' and self._fileIsByteSwapped)):
            pxtype = self.hdr.PixelType
            if pxtype == 0:
                dt = '%su1'
            elif pxtype == 1:
                dt = '%si2'
            elif pxtype == 2:
                dt = '%sf4'
            elif pxtype == 3:
                raise ValueError, 'Complex 2 signed 16-bit integers??'
            elif pxtype == 4:
                dt = '%sc8'
            elif pxtype == 5:
                dt = '%si2'
            elif pxtype == 6:
                dt = '%su2'
            elif pxtype == 7:
                dt = '%si4'
            dt = dt % byteorder
            self._dtype = dt
            self._fileIsByteSwapped = True

            for slot in self.hdr.__slots__:
                val = self.hdr.__getattr__(slot)
                dtype = val.dtype.str
                if dtype[0] != '|':
                    dtype = byteorder + dtype[1:]
                    self.hdr.__setattr__(slot, val.astype(dtype))
        
            # this is for ImageJ
            if not self.hdr.NumFloats and not self.hdr.NumIntegers:
                self.makeExtendedHdr(1, 1)
                self.hdr.NumFloats = 1 
                self.hdr.NumIntegers = 1


    def readSec(self, i=None):
        """ if i is None read "next" section at current position
        """
        if i is not None:
            self.seekSec(i)

        a = N.fromfile(self._f, self._dtype, N.prod(self._shape2d))

        if self._fileIsByteSwapped:
            a = a.byteswap()

        if not len(a):
            return a
        a.shape = self._shape2d

        return a

    def next(self):
        """
        adapter for iterator
        """
        return self.readSec()

    def readStack(self, nz, i=None):
        """ if i is None read "next" section at current position
        """
        if i is not None:
            self.seekSec(i)

        a = N.fromfile(self._f, self._dtype, nz*N.prod(self._shape2d))
        if self._fileIsByteSwapped:
            a = a.byteswap()
        a.shape = (nz,)+self._shape2d
        return a

    def writeSec(self, a, i=None):
        """ if i is None write "next" section at current position
        """
        if i is not None:
            self.seekSec(i)

        # todo check type, shape
        if self._fileIsByteSwapped:
            a = a.astype(self._dtype)

        return a.tofile(self._f)



