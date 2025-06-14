import os, re
import numpy as N

IMGSEQ = ['WTZ', 'TZW', 'TWZ', 'WZT', 'ZTW', 'ZWT']

WAVE_START = 0
WAVE_STEP  =  1

READABLE_FORMATS = WRITABLE_FORMATS = ['npy']

NA=None#1.4
N1=None#1.515
MAG=None

class ImageIOError(Exception):
    """
    general image file IO error
    """
    pass

class Reader(object):
    def __init__(self, fn, mode='r'):
        """
        fn: file name
        """
        self.filename = self.fn = fn
        self.dr, self.file = os.path.split(fn)
        self.pxlsiz = N.ones((3,), N.float32) # z,y,x
        self.nseries = 1
        self.series = 0
        self.imgseqs = IMGSEQ
        self.metadata = {}
        self.ex_metadata = {}
        self.optics_data = {}
        #self.useROI2getArr = False
        self.flip_required = True
        
        self.mode = mode
        self.axes = 'YX' # axes of one section
        self.axes_w = 0

        self.mag= MAG
        self.na = NA
        self.n1 = N1


        # current positions
       # self.t = self.w = self.z = self.y = self.x = 0

        self.openFile()

    def __str__(self):
        if hasattr(self, 'nt'):
            return self.__class__.__name__ + '(' + self.filename + ' nt=%i, nw=%i, nz=%i)' % (self.nt, self.nw, self.nz)
        else:
            return self.__class__.__name__ + '(' + self.filename + ')'

    def __repr__(self):
        if hasattr(self, 'nt'):
            return self.__class__.__name__ + '(' + self.filename + ' nt=%i, nw=%i, nz=%i)' % (self.nt, self.nw, self.nz)
        else:
            return self.__class__.__name__ + '(' + self.filename + ')'

    def __enter__(self):
        return self

    def __exit__(self, errtype=None, errval=None, traceback=None):
        self.close()
        if errtype:
            raise errtype(errval)
    
    def close(self):
        """
        closes the current file
        """
        if hasattr(self, 'fp') and hasattr(self.fp, 'close'):
            self.fp.close()
            #del self.fp
        elif hasattr(self, 'fp'):
            del self.fp

    def __del__(self):
        if not self.closed():
            self.close()
        
    # initial call
    def openFile(self):
        """
        open a file for reading
        """
        self.fp = open(self.fn, self.mode)

        if 'r' in self.mode:
            self.readHeader()

    def closed(self):
        if hasattr(self, 'handle') and hasattr(self.handle, 'closed'):
            return self.handle.closed

    def init(self):
        pass
            
    def readHeader(self):
        """
        specify your file format here
        """
        self.handle = self.fp
        
        self.dataOffset = 0
        self._secExtraByteSize = 0

        # usually, the header contains information
        self.setDim(256, 256, 10, 1, 1, N.uint16, [500])

    def findImgSequence(self, axis_order_string=''):
        """
        find the appropriate imgSeq value from sring like 'Z' or 'WZ'
        
        return imgSeq value
        """
        axes = axis_order_string.upper()
        axes = ''.join([a for a in axes if a in self.imgseqs[0]])
        if len(axes) <= 1:
            ## because my code tend to use t->w->z, here imgSeq = 2,
            ## however, 0 is more prevalent in the rest of world...
            imgSeq = 2
        elif len(axes) == 2:
            wc = '.*?'
            pattern = re.compile(wc + axes[0] + wc + axes[1] + wc)
            ids = [i for i, seq in enumerate(self.imgseqs) if pattern.match(seq)]
            imgSeq = ids[0]
        elif axes in self.imgseqs:
            imgSeq = self.imgseqs.index(axes)
        else:
            raise ValueError('The given axis was not found %s' % axes)
        return imgSeq
    
    def setDim(self, nx=None, ny=None, nz=None, nt=None, nw=None, dtype=None, wave=[], imgSequence=0):
        """
        set dimensions of the current file
        """
        if nx:
            self.nx = int(nx)
            self.x = self.nx // 2
        elif nx == 0:
            raise ValueError('nx cannot be 0')
        if ny:
            self.ny = int(ny)
            self.y = self.ny // 2
        elif ny == 0:
            raise ValueError('ny cannot be 0')
        if nz:
            self.nz = int(nz)
            self.z = self.nz // 2
        elif nz == 0:
            raise ValueError('nz cannot be 0')

        if nw:
            self.nw = int(nw)
        elif nw == 0:
            raise ValueError('nw cannot be 0')
        if nt:
            self.nt = int(nt)
        elif nt == 0:
            raise ValueError('nt cannot be 0')

        if type(dtype) == N.dtype or dtype: # dtype can be false in python2.7 numpy1.12 scipy0.18 tifffile0.15.1
            self.dtype = dtype

        if len(wave):
            if len(wave) > 1 and len(set(wave)) == 1:#wave[0] == wave[-1]:
                self.wave = self.makeWaves()#N.arange(400, 700, 300//self.nw)[:self.nw]
            else:
                self.wave = wave
        elif (hasattr(self, 'wave') and not len(self.wave)) and not len(wave) and self.nw:
            self.wave = self.makeWaves()#N.arange(400, 700, 300//self.nw)[:self.nw]
        elif not (hasattr(self, 'wave')):
            self.wave = self.makeWaves()#N.arange(400, 700, 300//self.nw)[:self.nw]

            
        if imgSequence is not None:
            self.imgSequence = imgSequence

        self.organize()

                
    def organize(self):
        """
        set some attributes using dimension information
        """
        self.shape = (self.ny, self.nx)
        self.ndim = len([d for d in (self.nx, self.ny, self.nz, self.nw, self.nt) if d > 1])
        self.nsec = self.nt * self.nw * self.nz
        #self.roi_start = N.zeros((3,), N.int16)
        #self.roi_size = N.array((self.nz, self.ny, self.nx), N.int16)
        self.resetROI()
        self.setSecSize()


    def setSecSize(self, size=None):
        """
        this function is supporsed to be executed after setHdr() or setDim()
        """
        if size:
            self._secByteSize = size
        else:
            if not hasattr(self, '_secExtraByteSize'):
                self._secExtraByteSize = 0
            npxls = self.ny * self.nx
            try:
                self._secByteSize = int(N.dtype(self.dtype.__name__).itemsize * npxls) + self._secExtraByteSize
            except(AttributeError):
                self._secByteSize = int(N.dtype(self.dtype).itemsize * npxls) + self._secExtraByteSize
        self.doOnSetDim()

    def doOnSetDim(self):
        """
        add more functions to do when dimensions are set
        """
        pass

    def setPixelSize(self, pz=1, py=1, px=1):
        self.pxlsiz[:] = pz, py, px
        try:
            self.doOnSetDim() # cannot be called before calling setDim
        except:
            pass

    def setRoi(self, zyx_start, zyx_size):
        """
        zyx_start: up to 3D, (z0,y0,x0)
        zyx_size: up to 3D, (zs,ys,xs)
        """
        self.roi_start[-len(zyx_start):] = zyx_start
        self.roi_size[-len(zyx_size):] = zyx_size

    def resetROI(self):
        """
        reset 'roi_start', 'roi_size', 't','w','z','y','x'
        """
        self.roi_start = N.zeros((3,), N.int16)
        self.roi_size = N.array((self.nz, self.ny, self.nx), N.int16)
        # current positions
        self.t = self.nt // 2
        self.w = self.nw // 2
        self.z = self.nz // 2
        self.y = self.ny // 2
        self.x = self.nx // 2
        #self.t = self.w = self.z = self.y = self.x = 0

    def isRoiSet(self):
        """
        return True if roi is different from the whole image size
        """
        maxshape = N.array((self.nz, self.ny, self.nx), N.int16)
        if N.any(self.roi_size < maxshape) or N.any(self.roi_start > 0):
            return True
 
    def getRoiSlice(self):
        """
        return (slice(), slice(), slice())
        """
        return tuple([slice(s, self.roi_size[d]+s) for d, s in enumerate(self.roi_start)])
        
        
    def getWaveIdx(self, wave):
        """
        return index
        """
        wave = int(wave)
        # work around for eg. 450.000000000001 vs 450
        try:
            check = [i for i, w in enumerate(self.wave[:self.nw]) if abs(w - wave) < 0.000001]
        except TypeError:
            check = []
        #print check
        if wave in self.wave[:self.nw]:
            wave = list(self.wave).index(wave)
            return wave
        elif len(check) == 1:
            return check[0] 
        elif wave < self.nw:
            return wave
        else:
            raise ValueError('no such wave exists %s' % wave)

    def getWaveIdx(self, wave):
        """
        return index
        """
        # 20170331 with Horikoshi san (Hiroshima U)
        # Zeiss czi file may contain wavelength like
        # [697.245, 592.1879475, 520.9980515000001, 442.26000000000005]
        # This information seems to keep updating over time.
        # This is a work around...
        wave = int(round(wave))
        waves = [int(round(w)) for w in self.wave[:self.nw]]
        if wave in waves:
            return waves.index(wave)
        elif  wave < self.nw:
            return wave
        else:
            raise ValueError('no such wave exists %s' % wave)

    def getWaveFromIdx(self, w):
        """
        return wavelength (nm)
        """
        w = int(w)
        if w in self.wave[:self.nw]:
            return w
        elif w < self.nw: # idx
            return self.wave[w]
        else:
            raise ValueError('no such wavelength index exists %s' % w)
    def getWave(self, w):
        return self.getWaveFromIdx(w)

    def makeWaves(self):
        return makeWaves(self.nw)

    def makeShape(self, squeeze=True):
        """
        return a shape according to imgSequence
        """
        yx = (self.ny, self.nx)
        if self.axes == 'YX':
            if self.imgSequence == 0:
                shape = (self.nw,self.nt,self.nz) + yx
            elif self.imgSequence == 1:
                shape = (self.nt,self.nz,self.nw) + yx
            elif self.imgSequence == 2:
                shape = (self.nt,self.nw,self.nz) + yx
            elif self.imgSequence == 3:
                shape = (self.nw,self.nz,self.nt) + yx
            elif self.imgSequence == 4:
                shape = (self.nz,self.nt,self.nw) + yx
            elif self.imgSequence == 5:
                shape = (self.nz,self.nw,self.nt) + yx
        elif len(self.axes) == 3 and self.axes[0] in ('S', 'C', 'W'):
            if self.imgSequence <= 2:
                shape = (self.nt, self.nz, self.nw) + yx
            else:
                shape = (self.nz, self.nt, self.nw) + yx
        elif len(self.axes) == 3 and self.axes[-1] in ('S', 'C', 'W'):
            yxw = yx + (self.nw,)
            if self.imgSequence <= 2:
                shape = (self.nt, self.nz) + yxw
            else:
                shape = (self.nz, self.nt) + yxw

        if squeeze:
            shape = tuple((i for i in shape if i != 1))
                    
        return shape

    def makeDimensionStr(self, squeeze=True):
        dstr = IMGSEQ[self.imgSequence] + 'YX'
        if squeeze:
            shape = self.makeShape(False)
            dstr =  ''.join([ds for i, ds in enumerate(dstr) if shape[i] > 1])
        return dstr
        
    def seekSec(self, i=0):
        """
        go to the section number in the file
        """
        
        if not hasattr(self, '_secByteSize'):
            raise NotImplementedError('call setSecSize before calling this function')
        self.handle.seek(self.dataOffset + i * self._secByteSize)

    def tellSec(self):
        """
        return the section number in the file
        """
        pos = self.handle.tell()

        return (pos - self.dataOffset) // self._secByteSize
        
    # reading file
    def findFileIdx(self, t=0, z=0, w=0):
        """
        return section_number in the file
        """
        if self.axes == 'YX':
            if self.imgSequence == 0:
                i = w*self.nt*self.nz + t*self.nz + z
            elif self.imgSequence == 1:
                i = t*self.nz*self.nw + z*self.nw + w
            elif self.imgSequence == 2:
                i = t*self.nz*self.nw + w*self.nz + z
            elif self.imgSequence == 3:
                i = w*self.nz*self.nt + z*self.nt + t
            elif self.imgSequence == 4:
                i = z*self.nt*self.nw + t*self.nw + w
            elif self.imgSequence == 5:
                i = z*self.nw*self.nt + w*self.nt + t
        elif len(self.axes) == 3 and self.axes[0] in ('S', 'C', 'W'):
            if self.imgSequence <= 2:
                i = (t*self.nz + z) #* 2 # what is "*2"?? 20190514
            else:
                i = (z*self.nt + t) #* 2
            self.axes_w = w
        elif len(self.axes) == 3 and self.axes[-1] in ('S', 'C', 'W'):
            if self.imgSequence <= 2:
                i = (t*self.nz + z) #* 2
            else:
                i = (z*self.nt + t) #* 2
            self.axes_w = w
            
        return int(i)

    def findDimFromIdx(self, i=0):
        if self.imgSequence == 0:
            z = i % (self.nw * self.nt)
            t = ((i-z) / (self.nz)) % self.nt
            w = (i-z)//(self.nz*self.nt)
        elif self.imgSequence == 1:
            w = i % (self.nt * self.nz)
            z = ((i-w) / (self.nw)) % self.nz
            t = (i-w)//(self.nw*self.nz)
        elif self.imgSequence == 2:
            z = i % (self.nw * self.nt)
            w = ((i-z) / (self.nz)) % self.nw
            t = (i-z)//(self.nz*self.nw)
        elif self.imgSequence == 3:
            t = i % (self.nw * self.nz)
            z = ((i-t) / (self.nt)) % self.nz
            w = (i-t) / (self.nz*self.nt)
        elif self.imgSequence == 4:
            w = i % (self.nt * self.nz)
            t = ((i-w) / (self.nw)) % self.nt
            z = (i-w) / (self.nw*self.nt)
        elif self.imgSequence == 5:
            t = i % (self.nw * self.nz)
            w = ((i-t) / (self.nt)) % self.nw
            z = (i-t) / (self.nw*self.nt)
        return t, w, z

    def readSec(self, i=None):
        """
        override this function for format-specific reader

        return the section at the number i in the file
        if i is None: return current position
        """
        if i is not None:
            self.seekSec(i)

        xy0 = self.roi_start[1:]
        xy1 = xy0 + self.roi_size[1:]
        a = N.fromfile(self.fp, self.dtype, N.prod(self.shape))
        return a.reshape((self.ny, self.nx))[xy0[0]:xy1[0], xy0[1]:xy1[1]]

    def flipY(self, arr):
        """
        priithon uses the left-down position as the origin
        while rest of the world uses the left-up positon as the origin
        We follows priithon coordinate...
        """
        if self.flip_required:
            if self.axes[0] in ('S', 'C', 'W'):
                arr = arr[:,::-1]
            else:
                arr = arr[::-1]
        return arr
        

    def getArr(self, t=0, z=0, w=0, useROI=False):
        """
        return a single section according to the dimension and current ROI
        """
        idx = self.findFileIdx(t=t, z=z, w=w)

        arr = self.readSec(idx)
        arr = self.flipY(arr)
        if useROI:
            slc = (Ellipsis,) + self.getRoiSlice()[-2:]
            arr = arr[slc]
        return arr

    def get3DArr(self, t=0, w=0, zs=None, useROI=False):
        """
        zs: if None, all z secs, else supply sequence of z sec
        
        return a 3D stack
        """
        if zs is None:
            if useROI:
                zs = list(range(self.roi_start[0], self.roi_start[0]+self.roi_size[0]))
            else:
                zs = list(range(self.nz))

        nz = len(zs)

        if useROI:
            ny = self.roi_size[1]
            nx = self.roi_size[2]
        else:
            ny = self.ny
            nx = self.nx
            
        arr = N.empty((nz, ny, nx), self.dtype)
        
        for i, z in enumerate(zs):
            arr[i] = self.getArr(t=t, z=z, w=w, useROI=useROI)
        return arr

    def get3DArrGenerator(self, ws=None, ts=None, ret_w_t=False, zs=None):
        """
        ws: indices of w
        ts: indices of t
        ret_w_t: if False, yield 3D arr (w1(tttt) -> w2(tttt))
                 if True, yield (w,t,3Darr)
        """
        ws = ws or range(self.nw)
        ts = ts or range(self.nt)

        for w in ws:
            for t in ts:
                arr = self.get3DArr(t=t, w=w, zs=zs)

                if ret_w_t:
                    yield w,t,arr
                else:
                    yield arr

    def getRange(self, Range=None, what='t'):
        """
        range: list or slice
        """
        n = self.__dict__['n%s' % what.lower()]  # self.nw, self.nt,...
        if Range is None:
            return list(range(n))#C.Ranger(n)
        elif type(Range) == slice:
            stop = Range.stop
            if stop is None:
                stop = n
            start = Range.start
            if start is None:
                start = 0
            step = Range.step
            if step is None:
                step = 1
            return list(range(int(start), int(stop), int(step)))#C.Ranger(Range.start, stop, Range.step)
        elif what == 'w':
             return [self.getWaveIdx(w) for w in Range]
        else:
             return list(Range)

    def asarray(self, useROI=False):
        """
        return numpy array as shape (nt, nw, nz, ny, nx)
        """
        if useROI:
            shape3D = tuple(self.roi_size)
        else:
            shape3D = (self.nz, self.ny, self.nx)

        img = N.empty((self.nt, self.nw) + shape3D, self.dtype)
        #img = N.empty((self.nt, self.nw, self.nz, self.ny, self.nx), self.dtype)
        for t in range(self.nt):
            for w in range(self.nw):
                img[t,w] = self.get3DArr(t=t, w=w, useROI=useROI)
        return img

    def arr_with_header(self, useROI=False):
        """
        return numpy array as shape squeeze(nt, nw, nz, ny, nx) with header and ROI (if useROI is True, then ROI is still that of the parent array)
        """
        class header:
            def __init__(cls):
                attrs = ('nt', 'nw', 'nz', 'ny', 'nx', 'metadata', 'fn', 'pxlsiz', 'wave', 'ex_metadata')
                for att in attrs:
                    setattr(cls, att, getattr(self, att))

        class roi:
            def __init__(cls):
                attrs = ('roi_start', 'roi_size', 't', 'w', 'z', 't', 'x')
                for att in attrs:
                    setattr(cls, att, getattr(self, att))
        
        # https://stackoverflow.com/questions/67509913/add-an-attribute-to-a-numpy-array-in-runtime
        class ndarray_in_imgio(N.ndarray):
            def __new__(cls, arr, header=None, roi=None):
                obj = N.asarray(arr).view(cls)
                obj.header = header
                obj.roi = roi
                return obj
            
            def __array_finalize__(self,obj):
                if obj is None: return
                self.header = getattr(obj, 'header', None)
                self.roi = getattr(obj, 'roi', None)

        data = N.squeeze(self.asarray(useROI=useROI)) 
        
        data = ndarray_in_imgio(data, header(), roi())

        return data

class Writer(Reader):
    def __init__(self, fn, mode='wb'):
        """
        fn: file name
        mode: 'w' will overwrite if the file already exists
        """
        self.dataOffset = 0
        self._secExtraByteSize = 0
        
        # call self.openFile()
        Reader.__init__(self, fn, mode)

    def setFromReader(self, rdr):
        """
        read dimensions, imgSequence, dtype, pixelsize from a reader
        """
        self.setPixelSize(*rdr.pxlsiz)
        self.metadata.update(rdr.metadata)# = rdr.metadata
        self.ex_metadata = rdr.ex_metadata
        self.setDim(rdr.roi_size[-1], rdr.roi_size[-2], rdr.roi_size[-3], rdr.nt, rdr.nw, rdr.dtype, rdr.wave, rdr.imgSequence)


        #print self.wave
        
    def writeHeader(self):
        """
        write a header according to the given dimensions
        """
        pass
        
    def writeSec(self, arr, i=None):
        """
        override this function for format-specific writer

        write a section into the file
        if i is None: write at the current position
        """
        if arr.ndim != 2:
            raise ValueError('arr must be 2-dimensions')

        if i is not None:
            self.seekSec(i)

        arr.tofile(self.fp)

    def writeArr(self, arr, t=0, w=0, z=0):
        """
        write array according to the given dimensions
        """
        if arr.ndim != len(self.axes):
            raise ValueError('arr must be %i-dimensions' % len(self.axes))

        arr = self.flipY(arr)
        idx = self.findFileIdx(t=t, z=z, w=w)

        self.writeSec(arr, idx)

    def write3DArr(self, arr, t=0, w=0):
        """
        write a 3D stack according to the given dimensions
        """
        if arr.ndim != (len(self.axes) + 1):
            raise ValueError('arr must be %i-dimensions' % (len(self.axes)+1))
        
        for z, a in enumerate(arr):
            self.writeArr(a, t=t, w=w, z=z)

    def mergeMetadataFromReaders(self, rdrs, along='t'):
        """
        rdrs: list of Reader objects
        """
        pass


def makeWaves(nw, start=WAVE_START, step=WAVE_STEP):
    return N.arange(start, start+step*nw, step)
