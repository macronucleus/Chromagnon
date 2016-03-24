import os, re
import numpy as N
try:
    from Priithon import Mrc
except ImportError:
    pass

IMGSEQ = ['WTZ', 'TZW', 'TWZ', 'WZT']


class GeneralReader(object):
    def __init__(self, fn, mode='r'):
        """
        fn: file name
        """
        self.filename = self.fn = fn
        self.dr, self.file = os.path.split(fn)

        self.mode = mode
        
        self.openFile()



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
            ids = [i for i, seq in enumerate(IMGSEQ) if pattern.match(seq)]
            imgSeq = ids[0]
        elif axes in IMGSEQ:
            imgSeq = IMGSEQ.index(axes)
        else:
            raise ValueError, 'The given axis was not found %s' % axes
        return imgSeq
    
    def setDim(self, nx, ny, nz, nt, nw, dtype, wave=[], imgSequence=0, nc=1, isSwapped=False):
        """
        set dimensions of the current file
        """
        self.wave = wave
        self.nw = nw
        self.nt = nt
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.dtype = dtype
        self.imgSequence = imgSequence

        self.nc = nc
        self.isSwapped = isSwapped

        # current positions
        self.t = 0
        self.w = 0
        self.z = self.nz // 2
        self.y = self.ny // 2
        self.x = self.nx // 2
        
        self.organize()

                
    def organize(self):
        """
        set some attributes using dimension information
        """
        self.shape = (self.ny, self.nx)
        self.ndim = len([d for d in (self.nx, self.ny, self.nz, self.nw, self.nt) if d > 1])
        self.nsec = self.nt * self.nw * self.nz
        self.setSecSize()


    def setSecSize(self, size=None):
        """
        this function is supporsed to be executed after setHdr() or setDim()
        """
        if size:
            self._secByteSize = size
        else:
            npxls = self.ny * self.nx
            self._secByteSize = int(N.nbytes[self.dtype] * npxls) + self._secExtraByteSize
        self.doOnSetDim()

    def doOnSetDim(self):
        """
        add more functions to do when dimensions are set
        """
        pass

            
    def setDimFromMrcHdr(self, hdr):
        """
        set dimensions using a Mrc header
        """
        nz = hdr.Num[2] // (hdr.NumWaves * hdr.NumTimes)
        dtype = Mrc.MrcMode2dtype(hdr.PixelType)

        self.setDim(hdr.Num[0], hdr.Num[1], nz, hdr.NumTimes, hdr.NumWaves, dtype, hdr.wave, hdr.ImgSequence, 1, False)
        
    def makeHdr(self):
        """
        make a Mrc header using the available dimension information to export
        """
        hdr = Mrc.makeHdrArray()
        Mrc.init_simple(hdr, Mrc.dtype2MrcMode(self.dtype), self.shape)
        hdr.ImgSequence = self.imgSequence
        hdr.NumTimes = self.nt
        hdr.NumWaves = self.nw
        hdr.Num[-1] = self.nt * self.nw * self.nz
        if self.wave:
            hdr.wave[:self.nw] = self.wave[:self.nw]

        self.hdr = hdr


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
        return i

    def readSec(self, i=None):
        """
        return the section at the number i in the file
        if i is None: return current position
        """
        if i is not None:
            self.seekSec(i)

        a = N.fromfile(self.fp, self.dtype, N.prod(self.shape))
        return a.reshape((self.ny, self.nx))

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
            zs = range(self.nz)

        nz = len(zs)
        arr = N.empty((nz, self.ny, self.nx), self.dtype)
        
        for i, z in enumerate(zs):
            arr[i] = self.getArr(t=t, z=z, w=w)
        return arr


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
