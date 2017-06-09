import os, re
import numpy as N

IMGSEQ = ['WTZ', 'TZW', 'TWZ', 'WZT']

class GeneralReader(object):
    def __init__(self, fn, mode='r'):
        """
        fn: file name
        """
        self.filename = self.fn = fn
        self.dr, self.file = os.path.split(fn)
        self.pxlsiz = N.ones((3,), N.float32)#[1.,1.,1.] # z,y,x
        self.nseries = 1
        self.series = 0
        self.imgseqs = IMGSEQ
        self.metadata = {}

        self.mode = mode

        # current positions
        self.t = self.w = self.z = self.y = self.x = 0

        self.openFile()

    def __str__(self):
        return self.__class__.__name__ + '(' + self.filename + ')'

    def __repr__(self):
        return self.__class__.__name__ + '(' + self.filename + ')'

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
            raise ValueError, 'The given axis was not found %s' % axes
        return imgSeq
    
    def setDim(self, nx=None, ny=None, nz=None, nt=None, nw=None, dtype=None, wave=[], imgSequence=0):
        """
        set dimensions of the current file
        """
        if nx:
            self.nx = int(nx)
            self.x = self.nx // 2
        if ny:
            self.ny = int(ny)
            self.y = self.ny // 2
        if nz:
            self.nz = int(nz)
            self.z = self.nz // 2

        if nw:
            self.nw = int(nw)
        if nt:
            self.nt = int(nt)

        if dtype:
            self.dtype = dtype

        if len(wave):
            if len(wave) > 1 and wave[0] == wave[-1]:
                self.wave = N.arange(400, 700, 300//self.nw)[:self.nw]
            else:
                self.wave = wave
        elif (hasattr(self, 'wave') and not len(self.wave)) and not len(wave) and self.nw:
            self.wave = N.arange(400, 700, 300//self.nw)[:self.nw]
        elif not (hasattr(self, 'wave')):
            self.wave = N.arange(400, 700, 300//self.nw)[:self.nw]

            
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
        self.roi_start = N.zeros((3,), N.int16)
        self.roi_size = N.array((self.nz, self.ny, self.nx), N.int16)
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
            self._secByteSize = int(N.nbytes[self.dtype] * npxls) + self._secExtraByteSize
        self.doOnSetDim()

    def doOnSetDim(self):
        """
        add more functions to do when dimensions are set
        """
        pass

    def setPixelSize(self, pz=1, py=1, px=1):
        self.pxlsiz[:] = pz, py, px

    def setRoi(self, zyx_start, zyx_size):
        self.roi_start[:] = zyx_start
        self.roi_size[:] = zyx_size
        
 

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
            raise ValueError, 'no such wave exists %s' % wave

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
        else:
            raise ValueError, 'no such wave exists %s' % wave

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
            raise ValueError, 'no such wavelength index exists %s' % w
        

    def seekSec(self, i=0):
        """
        go to the section number in the file
        """
        
        if not hasattr(self, '_secByteSize'):
            raise NotImplementedError, 'call setSecSize before calling this function'
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
        return int(i)

    def readSec(self, i=None):
        """
        return the section at the number i in the file
        if i is None: return current position
        """
        if i is not None:
            self.seekSec(i)

        xy0 = self.roi_start[1:]
        xy1 = xy0 + self.roi_size[1:]
        a = N.fromfile(self.fp, self.dtype, N.prod(self.shape))
        return a.reshape((self.ny, self.nx))[xy0[0]:xy1[0], xy0[1]:xy1[1]]

    def getArr(self, t=0, z=0, w=0):
        """
        return a single section according to the dimension
        """
        idx = self.findFileIdx(t=t, z=z, w=w)

        return self.readSec(idx)

    def get3DArr(self, t=0, w=0, zs=None):
        """
        zs: if None, all z secs, else supply sequence of z sec
        
        return a 3D stack
        """
        if zs is None:
            zs = range(self.roi_start[0], self.roi_start[0]+self.roi_size[0])#range(self.nz)

        nz = len(zs)
        ny = self.roi_size[1]
        nx = self.roi_size[2]
        arr = N.empty((nz, ny, nx), self.dtype)
        
        for i, z in enumerate(zs):
            arr[i] = self.getArr(t=t, z=z, w=w)
        return arr

    def get3DArrGenerator(self, ws=None, ts=None, ret_w_t=False, zs=None):
        """
        ws: indices of w
        ts: indices of t
        ret_w_t: if False, yield 3D arr (w1(tttt) -> w2(tttt))
                 if True, yield (w,t,3Darr)
        """
        ws = ws or xrange(self.nw)
        ts = ts or xrange(self.nt)

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
            return range(n)#C.Ranger(n)
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
            return range(int(start), int(stop), int(step))#C.Ranger(Range.start, stop, Range.step)
        elif what == 'w':
             return [getWaveIdxFromHdr(self.hdr, w) for w in Range]
        else:
             return list(Range)

class GeneralWriter(GeneralReader):
    def __init__(self, fn, mode='wb'):
        """
        fn: file name
        mode: 'w' will overwrite if the file already exists
        """
        self.dataOffset = 0
        self._secExtraByteSize = 0
        
        # call self.openFile()
        GeneralReader.__init__(self, fn, mode)

    def setFromReader(self, rdr):
        """
        read dimensions, imgSequence, dtype, pixelsize from a reader
        """
        self.setDim(rdr.roi_size[-1], rdr.roi_size[-2], rdr.roi_size[-3], rdr.nt, rdr.nw, rdr.dtype, rdr.wave, rdr.imgSequence)
        self.setPixelSize(*rdr.pxlsiz)
        self.metadata = rdr.metadata

        #print self.wave
        
    def writeHeader(self):
        """
        write a header according to the given dimensions
        """
        pass
        
    def writeSec(self, arr, i=None):
        """
        write a section into the file
        if i is None: write at the current position
        """
        if arr.ndim != 2:
            raise ValueError, 'arr must be 2-dimensions'

        if i is not None:
            self.seekSec(i)

        arr.tofile(self.fp)

    def writeArr(self, arr, t=0, w=0, z=0):
        """
        write array according to the given dimensions
        """
        if arr.ndim != 2:
            raise ValueError, 'arr must be 2-dimensions'
        
        idx = self.findFileIdx(t=t, z=z, w=w)

        self.writeSec(arr, idx)

    def write3DArr(self, arr, t=0, w=0):
        """
        write a 3D stack according to the given dimensions
        """
        if arr.ndim != 3:
            raise ValueError, 'arr must be 3-dimensions'
        
        for z, a in enumerate(arr):
            self.writeArr(a, t=t, w=w, z=z)
