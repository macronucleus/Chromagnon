
import numpy as N
try:
    from . import generalIO
except ImportError:
    import generalIO

READABLE_FORMATS = WRITABLE_FORMATS = []
# 'Image sequence. 0=ZTW, 1=WZT, 2=ZWT (idx = [2,1,0])

class ArrayReader(generalIO.GeneralReader):
    def __init__(self, fn, mode='r', name='array'):
        """
        fn: array or reader
        
        if fn is an array, then the image seq must be (t,w,z,y,x); the shape can be squeezed
        """
        if hasattr(fn, 'fn'):
            ff = fn.fn
        else:
            ff = name#'/test/test.tif'
        generalIO.GeneralReader.__init__(self, ff, mode)
        self.fp = fn
        #self.filename = self.fn = name
        self.flip_required = False

        self.openFile2()

    def openFile(self):
        pass

    def close(self):
        if hasattr(self, 'arr'):
            del self.arr

    def closed(self):
        return not hasattr(self, 'arr')
        
    def openFile2(self):
        #self.fp = self.fn

        if 'r' in self.mode:
            self.readHeader()

       # self.fn = self.name
       # del self.name
                
    def readHeader(self):
        """
        specify your file format here
        """
        self.handle = self.fp
        
        self.dataOffset = 0
        self._secExtraByteSize = 0

        if issubclass(type(self.fp), N.ndarray):
            shape = self.fp.shape
            ny, nx = shape[-2:]
            if len(shape) >= 3:
                nz = shape[-3]
                if len(shape) >= 4:
                    nw = shape[-4]
                    if len(shape) >= 5:
                        nt = shape[-5]
                    else:
                        nt = 1
                else:
                    nw = nt = 1
            else:
                nz = nw = nt = 1
            self.setDim(nx, ny, nz, nt, nw, self.fp.dtype, [], imgSequence=2)
                        
        else:
            self.setDim(self.fp.nx, self.fp.ny, self.fp.nz, self.fp.nt, self.fp.nw, self.fp.dtype, self.fp.wave, imgSequence=2)

    def doOnSetDim(self):
        if issubclass(type(self.fp), N.ndarray):
            self.arr = self.fp.reshape((-1,self.ny, self.nx))
        else:
            self.arr = N.empty((self.nt, self.nw, self.nz, self.ny, self.nx), self.dtype)

            for t in range(self.nt):
                for w in range(self.nw):
                    self.arr[t,w] = self.fp.get3DArr(t=t, w=w)

            self.arr = self.arr.reshape((-1,self.ny,self.nx))

    def seekSec(self, i=0):
        self.currSec = i

    def tellSec(self):
        return self.currSec

    def readSec(self, i=0):
        self.seekSec(i)

        return self.arr[i]
