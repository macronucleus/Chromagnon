"""
MRC file format: refer to
http://www.msg.ucsf.edu/IVE/IVE4_HTML/IM_ref2.html

Mrc class uses memory mapping (file size limit about 1GB (more or less)
Mrc2 class section wise file/array I/O
"""
from __future__ import print_function
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import sys
import numpy as N

def bindFile(fn, writable=0):
    """open existing Mrc file

    returns memmaped array
    array has special 'Mrc' attribute 
    """

    mode = 'r'
    if writable:
        mode = 'r+'
    a = Mrc(fn, mode)

    return a.data_withMrc()

class Mrc:
    def __init__(self, path, mode='r', extHdrSize=0, extHdrNints=0, extHdrNfloats=0):
        """
        mode can be 'r' or 'r+'
        """
        import os
        self.path     = os.path.abspath(path)
        self.filename = os.path.basename(path)

        #self.m
        #self.h
        #self.hdrArray
        #self.hdr = self.hdrArray[0].field
        #self.data_offset = = 1024 + self.hdr.next
        #self.d
        #self._nzBeforeByteOrder

        #self.e  = self.m[1024:self.data_offset]
        #self.numInts = self.hdr.NumIntegers
        #self.numFloats = self.hdr.NumFloats
        #self.extHdrArray
        #self.extInts   = self.extHdrArray.field('int')
        #self.extFloats = self.extHdrArray.field('float')
        #self.data

        if extHdrSize and extHdrSize % 1024:
            raise ValueError("extended header size needs to be integer multiple of 1024")
        #20060818 if not extHdrSize and (extHdrNints or extHdrNfloats):
        #20060818     raise "extHdrNints and extHdrNfloats must be 0 if no extHdrSize"

        self.m = N.memmap(path, mode=mode)
        self.h = self.m[:1024]
        
        
        #20060818 self._hdrArray = makeHdrArray(self.h)
        #20060818 self.hdr = implement_hdr( self._hdrArray )
        self.hdr = makeHdrArray(self.h)
        
        nzBeforeByteOrder = self.hdr.Num[0]
        if nzBeforeByteOrder<0 or \
               nzBeforeByteOrder>10000:

            #newbyteorder()
            self.hdr._array.dtype = self.hdr._array.dtype.newbyteorder() 
            self.isByteSwapped = True
        else:    
            self.isByteSwapped = False
            
        self.data_offset = 1024 + self.hdr.next #__next__
        self.d = self.m[self.data_offset:]


        self.e = self.m[1024:self.data_offset]

        self.doDataMap()

        self.numInts = self.hdr.NumIntegers
        self.numFloats = self.hdr.NumFloats
        
        if self.numInts > 0 or self.numFloats > 0:
            self.doExtHdrMap()

        else:
            self.extHdrArray = None

    ## this could prevent garbage collector ... 
    # http://arctrix.com/nas/python/gc/

    # Circular references which are garbage are detected when the optional cycle detector is enabled (it's on by default), but can only be cleaned up if there are no Python-level __del__() methods involved. Refer to the documentation for the 'gc' module for more information about how __del__() methods are handled by the cycle detector, particularly the description of the garbage value. Notice: [warning] Due to the precarious circumstances under which __del__() methods are invoked, exceptions that occur during their execution are ignored, and a warning is printed to sys.stderr instead. Also, when __del__() is invoked in response to a module being deleted (e.g., when execution of the program is done), other globals referenced by the __del__() method may already have been deleted. For this reason, __del__() methods should do the absolute minimum needed to maintain external invariants.



#   def __del__(self):
#       print "debug: Mrc.__del__ (close()) called !"
#       try:
#           #self.m.close()
#           self.close()
#       except:
#           pass

    def insertExtHdr(self, numInts, numFloats, nz=-1):
        """20051201 - test failed - data did NOT get shifted my next bytes !!!"""
        
        if numInts == numFloats == 0:
            raise ValueError("what ??")
        if self.data_offset != 1024:
            raise ValueError("what 2 ??")
        if self.hdr.next != 0:
            raise ValueError("what 3 ??")
        if nz <= 0:
            nz = self.hdr.Num[-1]

        bytes = 4 * (numInts + numFloats) * nz
        next = 1024 * ((bytes % 1024 != 0)+ bytes // 1024)
        self.hdr.next         = next
        self.hdr.NumIntegers  = numInts
        self.hdr.NumFloats    = numFloats

        self.numInts   = numInts
        self.numFloats = numFloats

        self.data_offset = 1024 + next
        self.e = self.m.insert(1024, next)
        
        self.doExtHdrMap()

    def doExtHdrMap(self, nz=0):
        """maps the extended header space to a recarray
        if nz==0: then it maps 'NumSecs' tuples
        if nz==-1 then it maps the _maximal_ available space
             then self.extHdrArray will likely have more entries then the 'NumSecs'
        """
        if nz == 0:
            nz = self.hdr.Num[-1]

        maxnz = int( len(self.e) / ((self.numInts + self.numFloats) * 4) )
        if nz < 0 or nz>maxnz:
            nz=maxnz

        byteorder = '=' # 20070206 self.isByteSwapped and '>' or '<'
        #         self.extHdrArray = N.rec.frombuffer(self.e, formats="%di4,%df4"%(self.numInts,self.numFloats),
        #                                         names='int,float',
        #                                         shape=nz,
        #                                         byteorder=byteorder)
        type_descr = [("int",   "%s%di4"%(byteorder,self.numInts)),
                      ("float", "%s%df4"%(byteorder,self.numFloats))]

        #self.extHdrArray = self.e.view()
        #self.extHdrArray.__class__ = N.recarray
        #self.extHdrArray.dtype = type_descr
        self.extHdrArray = N.recarray(shape=nz, dtype=type_descr, buf=self.e)
        if self.isByteSwapped:
            self.extHdrArray = self.extHdrArray.newbyteorder()
        
        self.extInts   = self.extHdrArray.field('int')
        self.extFloats = self.extHdrArray.field('float')
        
    def doDataMap(self):
        dtype = MrcMode2dtype( self.hdr.PixelType )
        shape = shapeFromHdr(self.hdr)
                
        self.data = self.d.view()
        self.data.dtype = dtype
        n0 = self.data.shape[0]
        if n0 != N.prod(shape):  # file contains INCOMPLETE sections
            nPixPerSec = N.prod(shape[-2:])
            s0 =  n0 // nPixPerSec - N.prod(shape[:-2]) # //-int-division (rounds down)

            if n0 > N.prod(shape):
                print('real data:', n0, 'data from hdr:', N.prod(shape))
                print("** WARNING **: found extra sections in file: %d sections; while shape from header: %s"%(s0, shape))
            else:
                print("** WARNING **: file truncated to %d sections; while shape from header: %s"%(s0, shape))

            shape = (s0,) + shape[1:]
            self.data = self.data[:N.prod(shape)]

        self.data.shape = shape
            
        if self.isByteSwapped:
            self.data = self.data.newbyteorder()

    def setTitle(self, s, i=-1):
        """set title i (i==-1 means "append") to s"""
        setTitle(self.hdr, s, i)
        
        
    def axisOrderStr(self, onlyLetters=True):
        """return string indicating meaning of shape dimensions
        ## 
        ## ZTW   <- non-interleaved
        ## WZT   <- OM1 ( easy on stage)
        ## ZWT   <- added by API (used at all ??)
        ## ^
        ## |
        ## +--- first letter 'fastest'

        fixme: possibly wrong when doDataMap found bad file-size
        """
        return axisOrderStr(self.hdr, onlyLetters)

    def looksOK(self, verbose=1):
        """do some basic checks like filesize, ..."""
        # print "TODO"
        shape = self.data.shape
        b = self.data.dtype.itemsize
        eb = N.prod( shape ) * b
        ab = len(self.d)
        secb = N.prod( shape[-2:] ) * b

        anSecs = ab / float(secb)
        enSecs = eb / float(secb)

        if verbose >= 3:
            print("expected total data bytes:", eb)
            print("data bytes in file       :", ab)
            print("expected total secs:", enSecs)
            print("file has total secs:", anSecs)
        
        if eb==ab:
            if verbose >= 2:
                print("OK")
            return 1
        elif eb<ab:
            if verbose >= 1:
                print("* we have %.2f more (hidden) section in file" % ( anSecs-enSecs ))
            return 0
        else:
            if verbose >= 1:
                print("* file MISSES %.2f sections " % ( enSecs-anSecs ))
                print("PLEASE SET shape to ", anSecs, "sections !!! ")
            return 0
            

    def info(self):
        """print useful information from header"""

        hdrInfo(self.hdr)


    def data_withMrc(self):
        """use this to get 'spiffed up' array"""

        import weakref
        #NOT-WORKING:  self.data.Mrc = weakref.proxy( self )

        #20071123: http://www.scipy.org/Subclasses
        class ndarray_inMrcFile(N.ndarray):
            def __array_finalize__(self,obj):
                self.Mrc = getattr(obj, 'Mrc', None)
#         class ndarray_inMrcFile(N.memmap):
#             pass
#             def __new__(subtype, data, info=None, dtype=None, copy=False):
#                 #subarr = N.array(data, dtype=dtype, copy=copy)
#                 #subarr = subarr.view(subtype)
#                 subarr = data.view(subtype)
#                 return subarr

#             def __array_finalize__(self,obj):
#                 self.Mrc = getattr(obj, 'Mrc', None)

        data = self.data
        data.__class__ = ndarray_inMrcFile
        ddd = weakref.proxy( data )
        self.data = ddd
        data.Mrc = self

        return data
        
    def close(self):
        #if self.mode == 'w+':
        #    self.calcMMM()
        self.m.close()
    #     def sync(self):
    #         self.m.sync()
    #     def flush(self):
    #         self.m.flush()



###########################################################################
###########################################################################
###########################################################################
###########################################################################

def open(path, mode='r'):
    return Mrc2(path, mode)

def load(fn):
    """return 3D array filled with the data
    (non memmap)
    """
    m = open(fn)
    a = m.readStack(m.hdr.Num[2])
    return a

def save(a, fn, ifExists='ask', zAxisOrder=None,
         hdr=None, hdrEval='',
         calcMMM=True,
         extInts=None, extFloats=None):
    """
    ifExists shoud be one of
       ask
       raise
       overwrite
       skip

    (only first letter is checked)

     use zAxisOrder if arr.ndim > 3:
       zAxisOrder is given in order conform to python(last is fastest)
          (spaces,commas,dots,minuses  are ignored)
       examples:
          4D: time,z,y,x          -->  zAxisOrder= 't z'
          5D: time, wave, z,y,x   -->  zAxisOrder= 't,z,w'
       refer to Mrc spec 'ImgSequence' (interleaved or not)
       zAxisOrder None means:
          3D: 'z'
          4D: 'tz'
          5D: 'tzw'

    if hdr is not None:  copy all fields(except 'Num',...)
    if calcMMM:  calculate min,max,mean of data set and set hdr field
    if hdrEval:  exec this string ("hdr" refers to the 'new' header)

    TODO: not implemented yet, extInts=None, extFloats=None
    """
    import os
    if os.path.exists(fn):
        if ifExists[0] == 'o':
            pass
        elif ifExists[0] == 'a':
            yes = input("overwrite?").lower() == 'y'
            if not yes:
                raise RuntimeError("not overwriting existing file '%s'"%fn)
        elif ifExists[0] == 's':
            return
        else:
            raise RuntimeError("not overwriting existing file '%s'"%fn)
            
    m = Mrc2(fn, mode='w')

    m.initHdrForArr(a, zAxisOrder)
    if hdr is not None:
        initHdrArrayFrom(m.hdr, hdr)

    if calcMMM:
        from . import useful as U
        wAxis = axisOrderStr(m.hdr).find('w')
        if wAxis < 0:
            m.hdr.mmm1 = U.mmm(a)
        else:
            nw = m.hdr.NumWaves
            m.hdr.mmm1 = U.mmm(a.take((0,),wAxis))
            if nw >=2:
                m.hdr.mm2 = U.mm(a.take((1,),wAxis))
            if nw >=3:
                m.hdr.mm3 = U.mm(a.take((2,),wAxis))
            if nw >=4:
                m.hdr.mm4 = U.mm(a.take((3,),wAxis))
            if nw >=5:
                m.hdr.mm5 = U.mm(a.take((4,),wAxis))

    if extInts is not None or  extFloats is not None:
        raise NotImplementedError("todo: implement ext hdr")

    if hdrEval:
        import sys
        fr = sys._getframe(1)
        loc = { 'hdr' : m.hdr }
        loc.update(fr.f_locals)
        glo = fr.f_globals
        exec(hdrEval, loc, glo)
    m.writeHeader()
    m.writeStack(a)
    m.close()



###########################################################################
###########################################################################
###########################################################################
###########################################################################

class Mrc2:
    """
    this class is for NON-memmapped access of Mrc files
    sections can be read and written on a by-need basis
    the Mrc2 object itself only handles
       the file-object and
       the header and
       extended header data
       BUT NOT ANY image data


    mode indicates how the file is to be opened: 
        'r' for reading, 
        'w' for writing (truncating an existing file), 
        ['a' does not really make sense here]
        Modes 'r+', 'w+' [and 'a+'] open the file for updating (note that 'w+' truncates the file). 
     ('b' for binary mode, is implicitely appended)
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
        import os# , builtins
        if sys.version_info.major == 2:
            import __main__
            from __main__ import __builtins__ as builtins
        else:
            import builtins
        self._f = builtins.open(path, mode+'b')
        self._path = path
        self._name = os.path.basename(path)
        self._mode = mode

        self._hdrSize    = 1024
        self._dataOffset = self._hdrSize

        self._fileIsByteSwapped = False
        
        if mode in ('r', 'r+') :
            self._initFromExistingFile()

            #111 - now we will have real extHdr support
            #111 self._dataOffset += self.hdr.next #HACK
            self.seekSec(0)
        else:
            #20060818 self._hdrArray = makeHdrArray()
            #20060818 self.hdr = implement_hdr( self._hdrArray )
            self.hdr = makeHdrArray()

            self._shape   = None
            self._shape2d = None
            self._dtype   = None    # scalar data type of pixels
            self._secByteSize = 0


    def initHdrForArr(self, arr, zAxisOrder=None):
        """
        use zAxisOrder if arr.ndim > 3:
          zAxisOrder is given in order conform to python(last is fastest)
             (spaces,commas,dots,minuses  are ignored)
          examples:
             4D: time,z,y,x          -->  zAxisOrder= 't z'
             5D: time, wave, z,y,x   -->  zAxisOrder= 't,z,w'
          refer to Mrc spec 'ImgSequence' (interleaved or not)
          zAxisOrder None means:
             3D: 'z'
             4D: 'tz'
             5D: 'tzw'
        """
        if zAxisOrder is None:
            if   arr.ndim ==3:
                zAxisOrder = 'z'
            elif arr.ndim ==4:
                zAxisOrder = 'tz'
            else:
                zAxisOrder = 'tzw'
        else:
            import string
            # remove delimiter characters '-., '
            zAxisOrder = zAxisOrder.translate(
                string.join([chr(i) for i in range(256)],''), '-., ').lower()

        mrcmode = dtype2MrcMode(arr.dtype.type)
        init_simple(self.hdr, mrcmode, arr.shape)
        if arr.ndim == 2:
            pass
        elif arr.ndim == 3:
            if   zAxisOrder[0] == 'z':
                self.hdr.ImgSequence = 0
            elif zAxisOrder[0] == 'w':
                self.hdr.ImgSequence = 1
                self.hdr.NumWaves = arr.shape[-3]
            elif zAxisOrder[0] == 't':
                self.hdr.ImgSequence = 0
                self.hdr.NumTimes = arr.shape[-3]
            else:
                raise ValueError("unsupported axis order (%s)"%(zAxisOrder,))
        elif arr.ndim == 4:
            #if   zAxisOrder[:2] == 'zt':
            #    #WRONG !self.hdr.ImgSequence = 2
            #    raise ValueError, "zAxisOrder z slower than t is not supported my Mrc format"
            #    self.hdr.NumTimes = arr.shape[-3]
            if   zAxisOrder[:2] == 'tz':
                self.hdr.ImgSequence = 0
                self.hdr.NumTimes = arr.shape[-4]
            elif zAxisOrder[:2] == 'wz':
                self.hdr.ImgSequence = 0
                self.hdr.NumWaves = arr.shape[-4]
            elif zAxisOrder[:2] == 'zw':
                self.hdr.ImgSequence = 1
                self.hdr.NumWaves = arr.shape[-3]
            else:
                raise ValueError("unsupported axis order (%s)"%(zAxisOrder,))
        elif arr.ndim == 5:
            if   zAxisOrder[:3] == 'wtz':
                self.hdr.ImgSequence = 0
                self.hdr.NumTimes = arr.shape[-4]
                self.hdr.NumWaves = arr.shape[-5]
            elif zAxisOrder[:3] == 'tzw':
                self.hdr.ImgSequence = 1
                self.hdr.NumTimes = arr.shape[-5]
                self.hdr.NumWaves = arr.shape[-3]
            elif zAxisOrder[:3] == 'twz':
                self.hdr.ImgSequence = 2
                self.hdr.NumTimes = arr.shape[-5]
                self.hdr.NumWaves = arr.shape[-4]
            else:
                raise ValueError("unsupported axis order (%s)"%(zAxisOrder,))

        else:  
             raise ValueError("unsupported array ndim (%s)"%(arr.ndim,))
         

        self._initWhenHdrArraySet()

    def _initFromExistingFile(self):
        self.seekHeader()
        hdrArray =  N.rec.fromfile(self._f, dtype=mrcHdr_dtype, shape=1)

        self.hdr = implement_hdr( hdrArray )
  
        self._nzBeforeByteOrder = self.hdr.Num[0]
        if self._nzBeforeByteOrder<0 or \
               self._nzBeforeByteOrder>10000:
            self.hdr._array.dtype = self.hdr._array.dtype.newbyteorder()
            self._fileIsByteSwapped = True

        self._extHdrSize        = self.hdr.next
        self._extHdrNumInts     = self.hdr.NumIntegers
        self._extHdrNumFloats   = self.hdr.NumFloats
        self._extHdrBytesPerSec = (self._extHdrNumInts + self._extHdrNumFloats) * 4
        self._dataOffset   = self._hdrSize + self._extHdrSize

        if self._extHdrSize>0 and (self._extHdrNumInts>0 or self._extHdrNumFloats>0):
            nSecs = int( self._extHdrSize / self._extHdrBytesPerSec )
            byteorder = '=' ## self._fileIsByteSwapped and '>' or '<'
            type_descr = [("int",   "%s%di4"%(byteorder, self._extHdrNumInts)),
                          ("float", "%s%df4"%(byteorder, self._extHdrNumFloats))]

            self._extHdrArray = N.rec.fromfile(self._f,
                                             dtype=type_descr,
                                             shape=nSecs  )

            if self._fileIsByteSwapped:
                self._extHdrArray = self._extHdrArray.newbyteorder()

            self.extInts   = self._extHdrArray.field('int')
            self.extFloats = self._extHdrArray.field('float')

        self._initWhenHdrArraySet()

    def _initWhenHdrArraySet(self):
        nx, ny, nsecs =  self.hdr.Num
        self._shape = (nsecs, ny,nx) # todo: wavelenths , times
        self._shape2d = self._shape[-2:]
        self._dtype  = MrcMode2dtype( self.hdr.PixelType )
        self._secByteSize = N.nbytes[self._dtype] * N.prod( self._shape2d )
        
    def setHdrForShapeType(self, shape, type ):
        mrcmode = dtype2MrcMode(type)
        self.hdr.PixelType =  mrcmode
        self.hdr.Num = shape[-1],shape[-2],  N.prod(shape[:-2])
        self._initWhenHdrArraySet()
        #       self._shape = shape
        #       self._shape2d = self._shape[-2:]
        #       self._dtype  = type
        #       self._secByteSize = self._dtype.itemsize * N.prod( self._shape2d )
        #       #init_simple(self._hdrArray, mrcmode, shape)


    def makeExtendedHdr(self, numInts, numFloats, nSecs=None):
        self._extHdrNumInts     = self.hdr.NumIntegers = numInts
        self._extHdrNumFloats   = self.hdr.NumFloats   = numFloats
        self._extHdrBytesPerSec = (self._extHdrNumInts + self._extHdrNumFloats) * 4

        if nSecs is None:
            nSecs = self._shape[0]

        self._extHdrSize        = self.hdr.next = minExtHdrSize(nSecs,self._extHdrBytesPerSec)
        self._dataOffset   = self._hdrSize + self._extHdrSize

        if self._extHdrSize>0 and (self._extHdrNumInts>0 or self._extHdrNumFloats>0):
            nSecs = int( self._extHdrSize / self._extHdrBytesPerSec )
            self._extHdrArray = N.recarray(nSecs,#None,#self._f,
                                           formats="%di4,%df4"%(self._extHdrNumInts,
                                                                self._extHdrNumFloats),
                                           names='int,float')
                                           # shape=nSecs)#  ,
                                           #byteorder=byteorder)

            self.extInts   = self._extHdrArray.field('int')
            self.extFloats = self._extHdrArray.field('float')

    
    def info(self):
        """print useful information from header"""

        hdrInfo(self.hdr)

    def close(self):
        self._f.close()
    def flush(self):
        self._f.flush()
        
    def seekSec(self, i):
        if self._secByteSize == 0: # type is None or self._shape2d is None:
            raise ValueError("not inited yet - unknown shape, type")
        self._f.seek( self._dataOffset + i * self._secByteSize )

    def seekHeader(self):
        self._f.seek(0)

    def seekExtHeader(self):
        self._f.seek(self._hdrSize)

    def readSec(self, i=None):
        """ if i is None read "next" section at current position
        """
        if i is not None:
            self.seekSec(i)

        a = N.fromfile(self._f, self._dtype, N.prod(self._shape2d))
        a.shape = self._shape2d
        return a

    def writeSec(self, a, i=None):
        """ if i is None write "next" section at current position
        """
        if i is not None:
            self.seekSec(i)

        # todo check type, shape

        return a.tofile(self._f)


    def readStack(self, nz, i=None):
        """ if i is None read "next" section at current position
        """
        if i is not None:
            self.seekSec(i)

        a = N.fromfile(self._f, self._dtype, nz*N.prod(self._shape2d))
        a.shape = (nz,)+self._shape2d
        return a

    def writeStack(self, a, i=None):
        """ if i is None write "next" section at current position
        """
        if i is not None:
            self.seekSec(i)

        # todo check type, shape

        return a.tofile(self._f)


    def writeHeader(self, seekTo0=False):
        self.seekHeader()
        self.hdr._array.tofile( self._f )
        if seekTo0:
            self.seekSec(0)
        
    def writeExtHeader(self, seekTo0=False):
        self.seekExtHeader()
        self._extHdrArray.tofile( self._f )
        if seekTo0:
            self.seekSec(0)
        

###########################################################################
###########################################################################
###########################################################################
###########################################################################


def minExtHdrSize(nSecs, bytesPerSec):
    """return smallest multiple of 1024 to fit extHdr data
    """
    import math
    return int( math.ceil(nSecs * bytesPerSec / 1024.)*1024 )


def MrcMode2dtype(mode):
    PixelTypes = (N.uint8, N.int16, N.float32,  # 0 1 2
                  N.float32, # FIXME               # 3
                  N.complex64,                    # 4
                  N.int16,                        # 5 (IW_EMTOM)
                  N.uint16,                       # 6
                  N.int32                         # 7
                  )

    if mode<0 or mode>7:
        raise ValueError("Priism file supports pixeltype 0 to 7 (%d given)" % mode)
    
    return PixelTypes[ int(mode) ]

def dtype2MrcMode(dtype):
    if dtype == N.uint8:
        return 0
    if dtype == N.int16:
        return 1
    if dtype == N.float32:
        return 2
#      if type == N.int8:
#          return 3
    if dtype == N.complex64:
        return 4
#      if type == N.In:
#          return 5
    if dtype == N.uint16:
        return 6
    if dtype == N.int32:
        return 7
    raise TypeError("MRC does not support %s (%s)"% (dtype.__name__, dtype))


def shapeFromHdr(hdr, verbose=0):
    """
    return "smart" shape  
    considering numTimes, numWavelenth and hdr.ImgSequence

    if verbose:
        print somthing like: w,t,z,y,x  ot z,y,x
    """
    zOrder = hdr.ImgSequence # , 'Image sequence. 0=ZTW, 1=WZT, 2=ZWT. '),
    nt,nw = hdr.NumTimes, hdr.NumWaves
    nx, ny, nsecs =  hdr.Num
    if nt == 0:
        #20051213(ref."other's" MRC) print " ** NumTimes is zero - I assume 1."
        nt=1
    if nw == 0:
        #20051213(ref."other's" MRC) print " ** NumWaves is zero - I assume 1."
        nw=1
    nz = nsecs // nt // nw

    if nt == nw == 1:
        shape = (nz, ny, nx)
        orderLetters = "zyx"
    elif nz == 1 == nw:
        shape = (nt, ny, nx)
        orderLetters = "tyx"
    elif nt == 1 or nw == 1:
        if zOrder == 0 or zOrder == 2:
            nn = nt
            if nt == 1:
                nn = nw
                orderLetters = "wyx"
            else:
                orderLetters = "tyx"
            shape = (nn, nz, ny, nx)
        else: # if zOrder == 1:
            if nt == 1:
                shape = (nz, nw, ny, nx)
                orderLetters = "zwyx"
            else:
                shape = (nt, nz, ny, nx)
                orderLetters = "tzyx"
        
    else: # both nt and nw > 1
        if zOrder == 0:
            shape = (nw, nt, nz, ny, nx)
            orderLetters = "wtzyx"
        elif zOrder == 1:
            shape = (nt, nz, nw, ny, nx)
            orderLetters = "tzwyx"
        else: # zOrder == 2:
            shape = (nt, nw, nz, ny, nx)
            orderLetters = "twzyx"


    if verbose:
        print(",".join(orderLetters))
    return shape



# my hack to allow thinks like a.Mrc.hdr.d = (1,2,3)
def implement_hdr(hdrArray):
    class hdr(object):
        __slots__ = mrcHdrNames[:] + ['_array']
        def __init__(s):
            pass    
        def __setattr__(s, n, v):
            #20070131 hdrArray.field(n)[0] = v
            hdrArray[n][0] = v
        def __getattr__(s, n):
            if n == '_array':
                return hdrArray   # 20060818
            #20070131 return hdrArray.field(n)[0]
            return hdrArray[n][0]
        def __dir__(self): # added to work on Priithon 20210716
            return self.__slots__

        ## depricated !!
        #def __call__(s, n):
        #    return hdrArray.field(n)[0]


    return hdr()


# class function
def makeHdrArray(buffer=None):
    if buffer is not None:
        #20070131  h = buffer.view()
        #20060131  h.__class__ = N.recarray
        h=buffer
        h.dtype = mrcHdr_dtype
        import weakref         #20070131   CHECK if this works
        h = weakref.proxy( h ) #20070131   CHECK if this works
    else:
        h = N.recarray(1, mrcHdr_dtype)

    #20060818 return h
    return implement_hdr(h)

# class function
def hdrInfo(hdr):
    shape = hdr.Num[::-1]    
    nz = shape[0]
    numInts = hdr.NumIntegers
    numFloats = hdr.NumFloats

    
    print("width:                      ", shape[2])
    print("height:                     ", shape[1])
    print("# total slices:             ", shape[0])

    nt,nw = hdr.NumTimes, hdr.NumWaves

    if nt == 0  or nw == 0:
        print(" ** ERROR ** : NumTimes or NumWaves is zero")
        print("NumTimes:", nt)
        print("NumWaves:", nw)
    else:
        if nt == 1  and  nw == 1:
            print()
        elif nw == 1: # TODO: make comment about order
            print("  (%d times for %d zsecs)"% (nt, nz/nt))
        elif nt == 1:
            print("  (%d waves in %d zsecs)"% (nw, nz/nw))
        else:
            print("  (%d times for %d waves in %d zsecs)"% (nt,
                                                           nw,
                                                           nz/nw/nt))
            
    if nt != 1  or  nw != 1:
        print("# slice order:        %d (0,1,2 = (wtz, tzw or twz)"% hdr.ImgSequence)

    print("pixel width x    (um):      ", hdr.d[0])
    print("pixel width y    (um):      ", hdr.d[1])
    print("pixel height     (um):      ", hdr.d[2])

    print("# wavelengths:              ", nw)
    print("   wavelength 1  (nm):      ", hdr.wave[0])
    print("    intensity min/max/mean: ", hdr.mmm1[0], hdr.mmm1[1], hdr.mmm1[2])
    if nw >1:
        print("   wavelength 2  (nm):      ", hdr.wave[1])
        print("    intensity min/max:      ", hdr.mm2[0], hdr.mm2[1])
    if nw >2:
        print("   wavelength 3  (nm):      ", hdr.wave[2])
        print("    intensity min/max:      ", hdr.mm3[0], hdr.mm3[1])
    if nw >3:
        print("   wavelength 4  (nm):      ", hdr.wave[3])
        print("    intensity min/max:      ", hdr.mm4[0], hdr.mm4[1])
    if nw >4:
        print("   wavelength 5  (nm):      ", hdr.wave[4])
        print("    intensity min/max:      ", hdr.mm5[0], hdr.mm5[1])
    
    #/  ostr + "# times:              " + num_times + '\n';
    #/  ostr += "# slice order:        " + 0 or 1 or 2 (ZTW or WZT or ZWT) + '\n';
    
    
    #/  ostr +="filetype:              " += filetype ... 0=normal, ..., 2=stereo ...
    #/    ostr += "n1, n2, v1, v2:          " +=  depend on filetype ....
    
    print("lens type:                  ", hdr.LensNum, end=' ')
    if hdr.LensNum == 12:
        print(" (60x)")
    elif hdr.LensNum == 13:
        print(" (100x)")
    else:
        print("(??)")

    print("origin   (um) x/y/z:        ", hdr.zxy0[1], hdr.zxy0[2], hdr.zxy0[0])

    print("# pixel data type:            ", end=' ')
    if hdr.PixelType == 0:
        print("8 bit (unsigned)")
    elif hdr.PixelType == 1:
        print("16 bit (signed)")
    elif hdr.PixelType == 2:
        print("32 bit (signed real)")
    elif hdr.PixelType == 3:
        print("16 bit (signed complex integer)")
    elif hdr.PixelType == 4:
        print("32 bit (signed complex real)")
    elif hdr.PixelType == 5:
        print("16 bit (signed) IW_EMTOM")
    elif hdr.PixelType == 6:
        print("16 bit (unsigned short)")
    elif hdr.PixelType == 7:
        print("32 bit (signed long)")
    else                         :
        print(" ** undefined ** ")

    #//ostr += "bytes before image data:     " + 1024+inbsym + '\n';
    print("# extended header size:       ", hdr.next, end=' ')
    if hdr.next > 0:
        n = numInts + numFloats
        if n>0:
            print(" (%d secs)" % (hdr.next/(4. * n) ,))
        else:
            print(" (??? secs)")
        print("  (%d ints + %d reals per section)"% (numInts, numFloats))
    else:
        print()
    if hdr.NumTitles < 0:
        print(" ** ERROR ** : NumTitles less than zero (NumTitles =", hdr.NumTitles, ")")
    elif hdr.NumTitles >0:
        n = hdr.NumTitles
        if n>10:
            print(" ** ERROR ** : NumTitles larger than 10 (NumTitles =", hdr.NumTitles,")")
            n=10
        for i in range( n ):
            print("title %d: %s"%(i, hdr.title[i]))

    
def axisOrderStr(hdr, onlyLetters=True):
    """return string indicating meaning of shape dimensions
    ## 
    ## wtz   <- non-interleaved
    ## tzw   <- OM1 ( easy on stage)
    ## twz   <- added by API (used at all ??)
    ## ^
    ## |
    ## +--- first letter 'fastest'

    fixme: possibly wrong when doDataMap found bad file-size
    """
    zOrder = int(hdr.ImgSequence) # , 'Image sequence. 0=ZTW, 1=WZT, 2=ZWT. '),
    nt,nw = hdr.NumTimes, hdr.NumWaves
    if nt == nw == 1:
        orderLetters= "zyx"
    elif nt == 1:
        orderLetters= ("wzyx", "zwyx", "wzyx")[zOrder]
    elif nw == 1:
        orderLetters= ("tzyx", "tzyx", "tzyx")[zOrder]
    else:
        orderLetters= ("wtzyx", "tzwyx", "twzyx")[zOrder]

    if onlyLetters:
        return orderLetters
    else:
        return "["+",".join(orderLetters)+"]"




def init_simple(hdr, mode, nxOrShape, ny=None, nz=None):
    """note: if  nxOrShape is tuple it is nz,ny,nx (note the order!!)
    """
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

    hdr.Num = (nx,ny,nz)
    hdr.PixelType = mode
    hdr.mst = (0,0,0) # 20060614: bugfixed was: (1,1,1))
    hdr.m   = (1,1,1)  # CHECK : should be nx,ny,nz ??
    hdr.d   = (1,1,1)
    hdr.angle = (90,90,90) # 20060202: changed alpha,beta,gamma to 90 (was:0)
    hdr.axis = (1,2,3)
    hdr.mmm1=  (0,100000,5000)
    hdr.type= 0
    hdr.nspg= 0
    hdr.next= 0
    hdr.dvid= 0xc0a0  # CHECK - should "priithon" get it own ID !?
    #20090402 hdr.blank= 0 #CHECK Hans: add ntst to record time domain offset
    hdr.nblank=0   #20090402
    hdr.ntst=0     #20090402
    hdr.extra=0    #20090402
    hdr.NumIntegers= 0
    hdr.NumFloats= 0
    hdr.sub= 0
    hdr.zfac= 0
    hdr.mm2= (0,10000)
    hdr.mm3= (0,10000)
    hdr.mm4= (0,10000)
    hdr.ImageType= 0
    hdr.LensNum= 0
    hdr.n1= 0
    hdr.n2= 0
    hdr.v1= 0
    hdr.v2= 0
    hdr.mm5= (0,10000)
    hdr.NumTimes= 1
    hdr.ImgSequence= 0 # Zero => not interleaved. That means z changes
    #//                           // fastest, then time, then waves;
    #//                           // 1 => interleaved. That means wave changes fastest,
    #//                           // then z, then time.
    hdr.tilt= (0,0,0)
    hdr.NumWaves= 1
    hdr.wave= (0,0,0,0,0)
    hdr.zxy0= (0,0,0)
    hdr.NumTitles= 0
    hdr.title= '\0' * 80



def initHdrArrayFrom(hdrDest, hdrSrc): #, mode, nxOrShape, ny=None, nz=None):
    """copy all field of the header
       EXCEPT  shape AND PixelType AND all fields related to extended hdr
    """
    
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
    '''
    #  hdrDest.PixelType = .hdr.PixelType
    hdrDest.mst = hdrSrc.mst
    hdrDest.m = hdrSrc.m
    hdrDest.d = hdrSrc.d
    hdrDest.angle = hdrSrc.angle
    hdrDest.axis =  hdrSrc.axis
    hdrDest.mmm1 =  hdrSrc.mmm1
    hdrDest.type =  hdrSrc.type
    hdrDest.nspg =  hdrSrc.nspg
    #   hdrDest.next =  hdrSrc.next
    hdrDest.next =          0
    hdrDest.dvid =  hdrSrc.dvid
    #20090402 hdrDest.blank = hdrSrc.blank
    hdrDest.nblank = hdrSrc.nblank   #20090402
    hdrDest.ntst = hdrSrc.ntst       #20090402
    hdrDest.extra = hdrSrc.extra      #20090402
    hdrDest.NumIntegers = 0 #hdrSrc.NumIntegers
    hdrDest.NumFloats =   0 #hdrSrc.NumFloats
    hdrDest.sub =         hdrSrc.sub
    hdrDest.zfac =        hdrSrc.zfac
    hdrDest.mm2 = hdrSrc.mm2
    hdrDest.mm3 = hdrSrc.mm3
    hdrDest.mm4 = hdrSrc.mm4
    hdrDest.ImageType = hdrSrc.ImageType
    hdrDest.LensNum =   hdrSrc.LensNum
    hdrDest.n1 =        hdrSrc.n1
    hdrDest.n2 =        hdrSrc.n2
    hdrDest.v1 =        hdrSrc.v1
    hdrDest.v2 =        hdrSrc.v2
    hdrDest.mm5 =       hdrSrc.mm5
    hdrDest.NumTimes =  hdrSrc.NumTimes
    hdrDest.ImgSequence = hdrSrc.ImgSequence
    hdrDest.tilt = hdrSrc.tilt
    hdrDest.NumWaves = hdrSrc.NumWaves
    hdrDest.wave =     hdrSrc.wave
    hdrDest.zxy0 =     hdrSrc.zxy0
    hdrDest.NumTitles = hdrSrc.NumTitles
    hdrDest.title = hdrSrc.title

def setTitle(hdr, s, i=-1):
    """set title i (i==-1 means "append") to s"""

    n = hdr.NumTitles

    if i < 0:
        i = n
    if i>9:
        raise ValueError("Mrc only support up to 10 titles (0<=i<10)")
    if len(s) > 80:
        raise ValueError("Mrc only support title up to 80 characters")
    if i>=n:
        hdr.NumTitles = i+1

    if len(s) == 80:
        hdr.title[i] = s
    else:
        hdr.title[i] = s+'\0'
    


mrcHdrFields = [
    ('3i4', 'Num'),   # (nx,ny,nSecs)
    ('1i4', 'PixelType'),
    ('3i4', 'mst'),
    ('3i4', 'm'),
    ('3f4', 'd'),
    ('3f4', 'angle'),
    ('3i4', 'axis'),
    ('3f4', 'mmm1'),
    ('1i2', 'type'),
    ('1i2', 'nspg'),
    ('1i4', 'next'),
    ('1i2', 'dvid'),
#20090402    ('30i1', 'blank'),
    ('1i2', 'nblank'),
    ('1i4', 'ntst'),    
    ('24u1', 'extra'),
    ('1i2', 'NumIntegers', 'Number of 4 byte integers stored in the extended header per section. '),
    ('1i2', 'NumFloats', 'Number of 4 byte floating-point numbers stored in the extended header per section. '),
    ('1i2', 'sub', 'Number of sub-resolution data sets stored within the image. Typically, this equals 1. '),
    ('1i2', 'zfac', 'Reduction quotient for the z axis of the sub-resolution images. '),
    ('2f4', 'mm2', 'Minimum intensity of the 2nd wavelength image. '),
    ('2f4', 'mm3', 'Minimum intensity of the 2nd wavelength image. '),
    ('2f4', 'mm4', 'Minimum intensity of the 2nd wavelength image. '),
    ('1i2', 'ImageType', 'Image type. See Image Type table below. '),
    ('1i2', 'LensNum', 'Lens identification number.'),
    ('1i2', 'n1', 'Depends on the image type.'),
    ('1i2', 'n2', 'Depends on the image type.'),
    ('1i2', 'v1', 'Depends on the image type. '),
    ('1i2', 'v2', 'Depends on the image type. '),
    ('2f4', 'mm5', 'Minimum intensity of the 2nd wavelength image. '),
    ('1i2', 'NumTimes', 'Number of time points.'),#u2', 'NumTimes', 'Number of time points.'),
    ('1i2', 'ImgSequence', 'Image sequence. 0=ZTW, 1=WZT, 2=ZWT. '),
    ('3f4', 'tilt', 'X axis tilt angle (degrees). '),
    ('1i2', 'NumWaves', 'Number of wavelengths.'),
    ('5i2', 'wave', 'Wavelength 1, in nm.'),
    ('3f4', 'zxy0', 'X origin, in um.'),   # 20050920  ## fixed: order is z,x,y NOT x,y,z
    ('1i4', 'NumTitles', 'Number of titles. Valid numbers are between 0 and 10. '),
    ('10a80', 'title', 'Title 1. 80 characters long. '),
]

mrcHdrNames = []
mrcHdrFormats = []
for ff in mrcHdrFields:
    mrcHdrFormats.append(ff[0])
    mrcHdrNames.append(ff[1])
del ff
del mrcHdrFields
mrcHdr_dtype = list(zip(mrcHdrNames, mrcHdrFormats))
