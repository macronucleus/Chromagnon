#try:
#    from . import Mrc
#except (ValueError, ImportError): # interactive mode
#    import Mrc
import numpy as N
import six
try:
    from . import generalIO, Mrc
except ImportError:
    import generalIO, Mrc

READABLE_FORMATS = WRITABLE_FORMATS = ('mrc', 'dv')
# 'Image sequence. 0=ZTW, 1=WZT, 2=ZWT (idx = [2,1,0])

LENS_ID={
    # Olympus
    10205: (20, 0.75, 1),
    10404: (40, 0.85, 1),
    10410: (40, 1.15, 1.333),
    10403: (40, 1.35, 1.518),
    10603: (60, 1.20, 1.333),
    10602: (60, 1.40, 1.518),
    10612: (60, 1.42, 1.518),
    10003: (100, 1.35, 1.40),
    10002: (100, 1.40, 1.518),
    10007: (100, 1.40, 1.518)
             }

class Reader(generalIO.Reader):
    def __init__(self, fn, mode='r'):
        generalIO.Reader.__init__(self, fn, mode)
        self.flip_required = False

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
        nt = int(self.fp.hdr.NumTimes[0]) # change data type
        nw = int(self.fp.hdr.NumWaves[0])
        nz = int(self.fp.hdr.Num[2]) // (nt * nw)
        dtype = self.fp._dtype
        wave = self.fp.hdr.wave[:nw]
        imgseq = self.fp.hdr.ImgSequence[0]
        
        self.setDim(nx, ny, nz, nt, nw, dtype, wave, imgseq)

        self.fp.setByteOrder()
        self.pxlsiz = self.fp.hdr.d[::-1]

        self.hdr = self.fp.hdr
        #self.metadata['title'] = self.hdr.title
        for ttl in self.hdr.title:
            if type(ttl) == N.bytes_:
                ttl = ttl.decode('UTF-8', 'ignore')
            if '=' in ttl: # this does not find separation of =
                kvs = ttl.split('=')
                nvs = len(kvs)
                for i in range(nvs//2):
                    kv = kvs[i*2:(i+1)*2]
                    if len(kv) == 2:
                        key, val = kv
                        key = key.strip()
                        val = val.strip()
                        
                        try:
                            val = eval(val)
                        except:
                            self.metadata[key] = val
                            #pass
            else:
                key = ttl
                val = ''
                if key:
                    self.metadata[key] = val

        self.fp._secByteSize = self._secByteSize

        # excitation wavelength
        if hasattr(self.fp, 'extFloats') and self.fp.extFloats.ndim >= 2 and self.fp.extFloats.shape[-1] >= 32:
            self.exc = N.zeros((nw,), dtype=N.float32)
            for w in range(nw):
                i = self.findFileIdx(w=w)
                if i < self.fp.extFloats.shape[0]:
                    self.exc[w] = self.fp.extFloats[i,10]

        # objective
        self.mag, self.na, self.n1 = LENS_ID.get(int(self.fp.hdr.LensNum), (generalIO.MAG, generalIO.NA, generalIO.N1))
            
            #self.exc = self.fp.extFloats[:nw,10]

    def makeHdr(self):
        """
        make a Mrc header using the available dimension information to export
        """
        if not self.hdr:
            hdr = Mrc.makeHdrArray()
            Mrc.init_simple(hdr, Mrc.dtype2MrcMode(self.dtype), self.shape)
            hdr.ImgSequence = self.imgSequence
            hdr.NumTimes = self.nt
            hdr.NumWaves = self.nw
            hdr.Num[-1] = self.nt * self.nw * self.nz
            if len(self.wave):
                hdr.wave[:self.nw] = self.wave[:self.nw]
            hdr.d = self.pxlsiz[::-1]
            if 'Instrument' in self.metadata:
                hdr.hdr.LensNum = eval(self.metadata['Instrument']['Objective']['ID'].split(':')[1])

            self.hdr = hdr


    def readSec(self, i):
        return self.fp.readSec(i)

    old='''
    def asarray(self, useROI=False):
        """
        return numpy array as shape (nt, nw, nz, ny, nx)
        """
        if useROI:
            nz, ny, nx = tuple(self.roi_size)
        else:
            nz, ny, nx = (self.nz, self.ny, self.nx)
        
        a = Mrc.bindFile(self.fn)
        if self.imgSequence == 0:
            a = a.reshape(self.nw, self.nt, nz, ny, nx)
            a = a.transpose((1,0,2,3,4))
        elif self.imgSequence == 1:
            a = a.reshape(self.nt, nz, self.nw, ny, nx)
            a = a.transpose((0,2,1,3,4))
        elif self.imgSequence == 2:
            a = a.reshape(self.nt, self.nw, nz, ny, nx)
        elif self.imgSequence == 3:
            a = a.reshape(self.nw, nz, self.nt, ny, nx)
            a = a.transpose((2,0,1,3,4))
        elif self.imgSequence == 4:
            a = a.reshape(nz, self.nt, self.nw, ny, nx)
            a = a.transpose((1,2,0,3,4))
        elif self.imgSequence == 5:
            a = a.reshape(nz, self.nw, self.nt, ny, nx)
            a = a.transpose((2,1,0,3,4))

        
        return a '''


class Writer(generalIO.Writer):
    def __init__(self, outfn, hdr=None, extInts=None, extFloats=None, metadata={}):
        """
        prepare your hdr and output filename

        metadata: goes to title (number of keys <= 10)
        """
        generalIO.Writer.__init__(self, outfn, mode='w')
        self.flip_required = False
        
        self.hdr = hdr
        self.metadata = metadata
        self.setExtHdr(extInts=extInts, extFloats=extFloats)
        if outfn.endswith('.dv'):
            self.byteorder = '<' # deltavision format
        else:
            self.byteorder = '='

        if self.hdr:
            self.setDimFromMrcHdr(self.hdr)

    def openFile(self):
        if hasattr(self, 'fp'):
            self.mode = 'r+'
        self.fp = Mrc3(self.fn, self.mode)

        self.handle = self.fp._f

    def doOnSetDim(self):
        pixelType = Mrc.dtype2MrcMode(self.dtype)
        num = self.nx, self.ny, self.nz * self.nw * self.nt
        if not self.hdr:
            self.hdr = Mrc.makeHdrArray()
            init_simple(self.hdr, pixelType, num)
        self.hdr.Num = num
        self.hdr.NumTimes = self.nt
        self.hdr.NumWaves = self.nw
        self.hdr.PixelType = pixelType
        self.hdr.ImgSequence = self.imgSequence
        self.hdr.wave[:self.nw] = self.wave[:self.nw]
        self.hdr.d[:] = self.pxlsiz[::-1]
        self.hdr.LensNum = findLens(self.mag, self.na)

        self.writeHeader(self.hdr)

    def setFromReader(self, rdr, calcmm=True):
        """
        read dimensions, imgSequence, dtype, pixelsize from a reader
        """
        if isinstance(rdr, Reader):
            if hasattr(rdr.fp, 'extInts'):
                self.setExtHdr(extInts=rdr.fp.extInts, extFloats=rdr.fp.extFloats)
            self.setDimFromMrcHdr(rdr.hdr)
        else:
            self.setPixelSize(*rdr.pxlsiz)
            self.setDim(rdr.roi_size[-1], rdr.roi_size[-2], rdr.roi_size[-3], rdr.nt, rdr.nw, rdr.dtype, rdr.wave, rdr.imgSequence)
            self.metadata = rdr.metadata

        if calcmm:
            mis = N.zeros((rdr.nt, rdr.nw), rdr.dtype)
            mas = N.zeros((rdr.nt, rdr.nw), rdr.dtype)
            mes = N.zeros((rdr.nt,), rdr.dtype)
            for t in range(rdr.nt):
                for w in range(rdr.nw):
                    arr = rdr.get3DArr(w=w, t=t, useROI=True)
                    mis[t,w] = N.min(arr)
                    mas[t,w] = N.max(arr)
                    if w == 0:
                        mes[t] = N.mean(arr)
            for w in range(rdr.nw):
                mi = N.min(mis[:,w])
                ma = N.max(mas[:,w])
                if w == 0:
                    me = N.mean(mes)
                    self.hdr.__setattr__('mmm1', [mi, ma, me])
                else:
                    self.hdr.__setattr__('mm%i' % (w+1), [mi, ma])
        
    def setDimFromMrcHdr(self, hdr):
        """
        set dimensions using a Mrc header
        """
        self.hdr = makeHdr_like(hdr)
        self.setPixelSize(*hdr.d[::-1])
        nz = int(hdr.Num[2]) // (int(hdr.NumWaves[0]) * int(hdr.NumTimes[0]))
        if nz < 1:
            raise ValueError('number of Z is less than 1 (nt: %i, nw: %i)' % (int(hdr.NumWaves[0]), int(hdr.NumTimes[0])))
        dtype = Mrc.MrcMode2dtype(hdr.PixelType[0])

        self.setDim(hdr.Num[0], hdr.Num[1], nz, hdr.NumTimes[0], hdr.NumWaves[0], dtype, hdr.wave, hdr.ImgSequence[0])

    def setExtHdr(self, extInts=None, extFloats=None):
        self.extFloats = extFloats
        self.extInts = extInts
        
    def writeHeader(self, hdr=None):
        if hdr is None:
            hdr = self.hdr
        Mrc.initHdrArrayFrom(self.fp.hdr, hdr)
        self.fp.hdr.Num = hdr.Num
        self.fp.hdr.PixelType = hdr.PixelType[0]

        self.fp._initWhenHdrArraySet()

        if self.byteorder == '<':
            self.hdr.dvid = -16224 # little_indian number

        # writing metadata into title
        for key, val in self.metadata.items():
            if val:
                msg = '%s = %s' % (key, val)
            else:
                msg = key

            # escape from unicode characters
            msg = msg.encode('ascii', errors='ignore').decode()

            if N.bytes_(msg) in self.hdr.title:
                continue

            # try to write
            try:
                Mrc.setTitle(self.hdr, msg)
            except ValueError:
                written = False
                for i, s in enumerate(self.hdr.title):
                    if not s:
                        Mrc.setTitle(hdr, msg, i)
                        written = True
                        break
                if not written:
                    print('WARNING: title is full, metadata "%s" is not written' % key)

        if (self.extInts is not None or self.extFloats is not None) or self.byteorder == '<':
            # old ImageJ assumes that the dv format (byteorder == <) has extended header
            if self.extInts is None:
                self.extInts = N.zeros((1,8))
            nInts = self.extInts.shape[-1]
                
            if self.extFloats is None:
                self.extFloats = N.zeros((1,32))
            nFloats = self.extFloats.shape[-1]
                
            self.fp = addExtHdrFromExt(self.fp, nInts,
                                        nFloats, self.extInts, self.extFloats)
            self.fp.hdr.NumIntegers = self.fp.extInts.shape[-1]
            self.fp.hdr.NumFloats = self.fp.extFloats.shape[-1]

        self.fp.setByteOrder(self.byteorder)

        self.fp.writeHeader()
        if hasattr(self.fp, 'extInts') or hasattr(self.fp, 'extFloats'):
            self.fp.writeExtHeader(True)


        self.hdr = self.fp.hdr

    def writeArr(self, arr2D, w=0, t=0, z=0):
        i = self.findFileIdx(t, z, w)

        self.fp.writeSec(arr2D, i)

    def mergeMetadataFromReaders(self, rdrs, along='t'):
        """
        only for mrc formats
        """
        nt = 0
        nw = 0
        nz = 0

        ni = 0
        nf = 0
        ns = 0

        for rdr in rdrs:
            if along == 't':
                nt += rdr.nt
            else:
                nt = rdr.nt
            if along == 'w':
                nw += rdr.nw
            else:
                nw = rdr.nw
            if along == 'z':
                nz += rdr.nz
            else:
                nz = rdr.nz

            if hasattr(rdr.fp.hdr.NumIntegers, 'shape'):
                ni = rdr.fp.hdr.NumIntegers[0]
            else:
                ni = rdr.fp.hdr.NumIntegers
            if hasattr(rdr.fp.hdr.NumFloats, 'shape'):
                nf = rdr.fp.hdr.NumFloats[0]
            else:
                nf = rdr.fp.hdr.NumFloats
        
        ns = nt * nw * nz
            
        self.fp.makeExtendedHdr(ni, nf, nSecs=ns) # this creates many instances
        #self.fp = addExtHdrFromExt(self.fp, ni,nf)
                                       # nf, self.fp.extInts, self.fp.extFloats)
        #self.fp.

        #print(self.fp.extFloats.shape, ns, ni, nf, self.fp._extHdrBytesPerSec)
        d2 = 0
        for h in rdrs:
            for t in range(h.nt):
                for w in range(h.nw):
                    for z in range(h.nz):
                        i = h.findFileIdx(t=t, w=w, z=z)
                        ei = h.fp.extInts[i]
                        ef = h.fp.extFloats[i]
                        if along == 't':
                            j = self.findFileIdx(t=d2+t, w=w, z=z)
                        elif along == 'w':
                            j = self.findFileIdx(t=t, w=w+d2, z=z)
                        elif along == 'z':
                            j = self.findFileIdx(t=t, w=w, z=z+d2)

                        if j < self.fp.extInts.shape[0]:
                            self.fp.extInts[j] = ei
                            self.fp.extFloats[j] = ef
                            #if z==0 and t==0:
                            #    print(w, j, ef[10],self.fp._extHdrArray.field('float')[j][10])
                            
            if along == 't':
                d2 += h.nt
            elif along == 'w':
                d2 += h.nw
            elif along == 'z':
                d2 += h.nz

        self.fp.hdr.NumIntegers = self.fp.extInts.shape[-1]
        self.fp.hdr.NumFloats = self.fp.extFloats.shape[-1]
        self.fp.writeHeader()

        self.fp.writeExtHeader(True)


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
    """
    hdrSrc: header of the source
    return header
    """
    hdr = Mrc.makeHdrArray()
    init_simple(hdr, hdrSrc.PixelType[0], hdrSrc.Num[::-1])
    Mrc.initHdrArrayFrom(hdr, hdrSrc)
    hdr.NumTimes = hdrSrc.NumTimes[0]
    hdr.NumWaves = hdrSrc.NumWaves[0]
    hdr.NumIntegers = hdrSrc.NumIntegers[0]
    hdr.NumFloats = hdrSrc.NumFloats[0]
    return hdr

def makeHdrFromRdr(rdr):
    """
    rdr: reader object
    return header
    """
    if hasattr(rdr, 'hdr'):
        hdr = makeHdr_like(rdr.hdr)
    else:
        old="""
        hdr = Mrc.makeHdrArray()
        Mrc.init_simple(hdr, Mrc.dtype2MrcMode(rdr.dtype), rdr.shape)
        hdr.ImgSequence = rdr.imgSequence
        hdr.NumTimes = rdr.nt
        hdr.NumWaves = rdr.nw
        hdr.Num[-1] = rdr.nt * rdr.nw * rdr.nz
        if len(rdr.wave):
            if [1 for wave in rdr.wave[:rdr.nw] if isinstance(wave, six.string_types)]:
                hdr.wave[:rdr.nw] = 0
            else:
                hdr.wave[:rdr.nw] = rdr.wave[:rdr.nw]"""
        hdr = makeHdrFromDim(nx=rdr.nx, ny=rdr.ny, nz=rdr.nz, nt=rdr.nt, nw=rdr.nw, dtype=rdr.dtype, wave=rdr.wave, imgSequence=rdr.imgSequence)
        hdr.d = rdr.pxlsiz[::-1]
        if 'Instrument' in rdr.metadata:
            hdr.LensNum = eval(rdr.metadata['Instrument']['Objective']['ID'].split(':')[1])

    return hdr

def setTitle(hdr, title):
    if hdr.NumTitles < 9:
        Mrc.setTitle(hdr, title)

def makeHdrFromDim(nx, ny, nz, nt, nw, dtype, wave=[], imgSequence=0):
    hdr = Mrc.makeHdrArray()
    Mrc.init_simple(hdr, Mrc.dtype2MrcMode(dtype), nx, ny, nz*nt*nw)
    hdr.ImgSequence = imgSequence
    hdr.NumTimes = nt
    hdr.NumWaves = nw
    if len(wave):
        if [1 for wav in wave[:nw] if isinstance(wav, six.string_types)]:
            hdr.wave[:nw] = 0
        else:
            hdr.wave[:nw] = wave[:nw]
    return hdr


def addExtHdrFromExt(hdl, numInts=0, numFloats=0, extInts=None, extFloats=None):
    if extInts is not None:
        nSecs = extInts.shape[0]
    elif extFloats is not None:
        nSecs = extFloats.shape[0]
    else:
        nSecs = hdl.hdr.Num[2]
    hdl.makeExtendedHdr(numInts, numFloats, nSecs=nSecs) # this creates many instances

    hdl.extInts = _reshapeExtHdr(hdl.extInts)
    hdl.extFloats = _reshapeExtHdr(hdl.extFloats)
    if extInts is not None:
        extInts = _reshapeExtHdr(extInts)
        hdl.extInts[:nSecs,:numInts] = extInts[:nSecs,:numInts]
    if extFloats is not None:
        extFloats = _reshapeExtHdr(extFloats)    
        hdl.extFloats[:nSecs,:numFloats] = extFloats[:nSecs,:numFloats]

    return hdl

def _reshapeExtHdr(extHdr):
    if extHdr.ndim == 1:
        extHdr = extHdr.reshape(extHdr.shape + (1,))
    return extHdr

def makeHdrFromArr(ref, targetArr=None):
    if not hasattr(ref, 'header'):
        raise ValueError('The reference array must have the "header" attribute')

    hdr = ref.header
    
    if targetArr is not None:
        ny, nx = targetArr.shape[-2:]
        nsecs = N.prod(targetArr.shape[:-2])
        dtype = targetArr.dtype
        if N.prod((ref.header.nt, ref.header.nz, ref.header.nw)) != nsecs:
            print('Number of sections is different, please edit nt, nw, and Num')
    else:
        ny, nx = ref.header.ny, ref.header.nx
        dtype = ref.dtype
        print('Please edit nw, nt, Num, dtype if they are different in the target array')


    
    hdr = makeHdrFromDim(nx, ny, ref.header.nz, ref.header.nt, ref.header.nw, dtype=dtype, wave=ref.header.wave, imgSequence=0)

    hdr.d[:] = ref.header.pxlsiz[::-1]

    for i, meta in enumerate(ref.header.metadata.keys()):
        if i < 10:
            Mrc.setTitle(hdr, meta, i)

    return hdr
    


#### imgManager ####
def shapeFromNum(Num, NumWaves=1, NumTimes=1, imgSequence=1, squeeze=True):
    nz = int(Num[2]) // (int(NumWaves) * int(NumTimes)) # int() to avoid byte swap
    if imgSequence == 0:
        shape = [NumWaves, NumTimes, nz, Num[1], Num[0]]
    elif imgSequence == 1:
        shape = [NumTimes, nz, NumWaves, Num[1], Num[0]]
    elif imgSequence == 2:
        shape = [NumTimes, NumWaves, nz, Num[1], Num[0]]
    elif imgSequence == 3:
        shape = [NumWaves, nz, NumTimes, Num[1], Num[0]]
    if squeeze:
        shape = _slimShape(shape)
    return tuple(shape)

def shapeFromHdr(hdr):
    return shapeFromNum(hdr.Num, hdr.NumWaves[0], hdr.NumTimes[0], hdr.ImgSequence[0])

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
    nw = hdr.NumWaves[0]
    if wave in hdr.wave[:nw]:
        return wave
    elif wave < nw: # idx
        return hdr.wave[wave]
    else:
        raise ValueError('no such wave exists %s' % wave)

def getWaveIdxFromHdr(hdr, wave):
    """
    return index
    """
    wave = int(wave)
    nw = hdr.NumWaves[0]
    if wave in hdr.wave[:nw]:
        wave = list(hdr.wave).index(wave)
        return wave
    elif wave < nw:
        return wave
    else:
        raise ValueError('no such wave exists %s' % wave)


def recalcMinMax(fn):
    """
    update scale in the header
    """
    h = Reader(fn)
    hdr = makeHdr_like(h.hdr)

    o = Mrc3(fn, 'r+')

    for w in range(h.nw):
        mi, ma = None, None
        su = 0
        for t in range(h.nt):
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
            pxtype = self.hdr.PixelType[0]
            if pxtype == 0:
                dt = '%su1'
            elif pxtype == 1:
                dt = '%si2'
            elif pxtype == 2:
                dt = '%sf4'
            elif pxtype == 3:
                raise ValueError('Complex 2 signed 16-bit integers??')
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
            #if not self.hdr.NumFloats and not self.hdr.NumIntegers:
            #    self.makeExtendedHdr(1, 1)
            #    self.hdr.NumFloats = 1 
            #    self.hdr.NumIntegers = 1


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

    def __next__(self):
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


def nt_uint_switch(on=True):
    if on:
        Mrc.mrcHdrFormats[-8] = '1u2'
        ret = 1
    else:
        Mrc.mrcHdrFormats[-8] = '1i2'
        ret = 0
    Mrc.mrcHdr_dtype = list(zip(Mrc.mrcHdrNames, Mrc.mrcHdrFormats))
    return ret

def findLens(mag=60, na=1.42):
    for key, val in LENS_ID.items():
        if val[0] == mag and val[1] == na:
            return key
    return 0
