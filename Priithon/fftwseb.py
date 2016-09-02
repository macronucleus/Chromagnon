"access to double and single prec SWIG wrapped FFTW module"

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import Priithon_bin.sfftw as _sfftw
import Priithon_bin.dfftw as _dfftw
import numpy as _N

_splans = {}
_dplans = {}
_measure = _sfftw.FFTW_ESTIMATE # ==0
# _measure = _sfftw.FFTW_MEASURE  # == 1

RTYPE = _N.float32
RTYPES = (_N.float32, _N.float64)
CTYPE = _N.complex64
CTYPES = (_N.complex64, _N.complex128)
ncpu = 1

def rfft(a,af=None, inplace=0, nthreads=1):
    #CHECK b type size

    if inplace:
        inplace = _sfftw.FFTW_IN_PLACE     # == 8
        shape = a.shape[:-1]+(a.shape[-1]-2,)
    else:
        shape = a.shape
        inplace = 0
    dir = _sfftw.FFTW_FORWARD
    if a.dtype == _N.float32:
        if af is not None and (not af.flags.carray or af.dtype != _N.complex64):
            raise RuntimeError, "af needs to be well behaved Complex64 array"
        key = ("sr%d"%inplace, shape )

        try:
            p = _splans[ key ]
        except:
            ashape = _N.array(shape, dtype=_N.int32)
            p = _sfftw.rfftwnd_create_plan(len(shape), ashape, dir,
                    _measure | inplace)
            if p is None:
                raise RuntimeError, "could not create plan"
            _splans[ key ] = p

        if inplace:
            #debug print 11111111111111
            _sfftw.rfftwnd_one_real_to_complex(p,a,None)
            if af is None:
                s2 = shape[:-1]+(shape[-1]/2.+1,)
                af = _N.ndarray(buffer=a, shape=s2,dtype=_N.complex64)
                return af
        else:
            #debug print "plan", repr(p)
            #debuf print 22222222222222, a.shape
            #debuf print a.flags, a.dtype.isnative
            if af is None:
                s2 = shape[:-1]+(shape[-1]/2.+1,)
                af = _N.empty(shape=s2, dtype=_N.complex64)
                #debuf print 33333333322222, af.shape
                #debuf print af.flags, af.dtype.isnative
                _sfftw.rfftwnd_one_real_to_complex(p,a,af)
                return af
            else:
                #debuf print 22222222222222, af.shape
                #debuf print af.flags, af.dtype.isnative
                _sfftw.rfftwnd_one_real_to_complex(p,a,af)  


    elif a.dtype == _N.float64:
        if af is not None and (not af.flags.carray or af.dtype != _N.complex128):
            raise RuntimeError, "af needs to be well behaved Complex64 array"
        key = ("dr%d"%inplace, shape )

        try:
            p = _dplans[ key ]
        except:
            p = _dfftw.rfftwnd_create_plan(len(shape), _N.array(shape, dtype=_N.int32), dir,
                    _measure | inplace)
            if p is None:
                raise RuntimeError, "could not create plan"
            _dplans[ key ] = p

        if inplace:
            _dfftw.rfftwnd_one_real_to_complex(p,a,None)
            if af is None:
                s2 = shape[:-1]+(shape[-1]/2.+1,)
                af = _N.ndarray(buffer=a, shape=s2, dtype=_N.complex128)
                return af
        else:
            if af is None:
                s2 = shape[:-1]+(shape[-1]/2.+1,)
                af = _N.empty(shape=s2, dtype=_N.complex128)
                _dfftw.rfftwnd_one_real_to_complex(p,a,af)
                return af
            else:
                _dfftw.rfftwnd_one_real_to_complex(p,a,af)  

    else:
        raise TypeError, "(c)float32 and (c)float64 must be used consistently (%s %s)"%\
              ((a is None and "a is None" or "a.dtype=%s"%a.dtype),
               (af is None and "af is None" or "af.dtype=%s"%af.dtype))

def irfft(af, a=None, inplace=0, copy=1, nthreads=1):
    """if copy==1 (and inplace==0 !!) fftw uses a copy of af to prevent overwriting the original
       (fftw always messes up the input array when inv-fft complex_to_real)
       """
    #CHECK b type size
    global shape,s2

    if copy and not inplace:
        af = af.copy()

    if inplace:
        inplace = _dfftw.FFTW_IN_PLACE     # == 8
        shape = af.shape[:-1] + ((af.shape[-1]-1)*2,)
    else:
        shape = af.shape[:-1] + ((af.shape[-1]-1)*2,)
        inplace = 0
    dir = _sfftw.FFTW_BACKWARD
    if af.dtype == _N.complex64:
        if a is not None and (not a.flags.carray or a.dtype != _N.float32):
            raise RuntimeError, "a needs to be well behaved float32 array"
        key = ("sir%d"%inplace, shape )

        try:
            p = _splans[ key ]
        except:
            p = _sfftw.rfftwnd_create_plan(len(shape), _N.array(shape, dtype=_N.int32), dir,
                    _measure | inplace)
            if p is None:
                raise RuntimeError, "could not create plan"
            _splans[ key ] = p
            

        if inplace:
            _sfftw.rfftwnd_one_complex_to_real(p,af,None)
            if a is None:
                s2 = shape[:-1]+(shape[-1]+2,)
                a = _N.ndarray(buffer=af, shape=s2, dtype=_N.float32)
                return a
        else:
            if a is None:
                s2 = shape
                a = _N.empty(shape=s2, dtype=_N.float32)
                _sfftw.rfftwnd_one_complex_to_real(p,af,a)
                return a
            else:
                _sfftw.rfftwnd_one_complex_to_real(p,af,a)  


    elif af.dtype == _N.complex128:
        if a is not None and (not a.flags.carray or a.dtype != _N.float64):
            raise RuntimeError, "a needs to be well behaved float64 array"
        key = ("dir%d"%inplace, shape )

        try:
            p = _dplans[ key ]
        except:
            p = _dfftw.rfftwnd_create_plan(len(shape), _N.array(shape, dtype=_N.int32), dir,
                    _measure | inplace)
            if p is None:
                raise RuntimeError, "could not create plan"
            _dplans[ key ] = p

        if inplace:
            _dfftw.rfftwnd_one_complex_to_real(p,af,None)
            if a is None:
                s2 = shape[:-1]+(shape[-1]+2,)
                a = _N.ndarray(buffer=af, shape=s2,dtype=_N.float64)
                return a
        else:
            if a is None:
                s2 = shape
                a = _N.empty(shape=s2, dtype=_N.float64)
                _dfftw.rfftwnd_one_complex_to_real(p,af,a)
                return a
            else:
                _dfftw.rfftwnd_one_complex_to_real(p,af,a)  

    else:
        raise TypeError, "(c)float32 and (c)float64 must be used consistently (%s %s)"%\
              ((a is None and "a is None" or "a.dtype=%s"%a.dtype),
               (af is None and "af is None" or "af.dtype=%s"%af.dtype))


def destroy_plans():
    for k in _splans.keys():
        _sfftw.rfftwnd_destroy_plan( _splans[ k ] )
        del _splans[ k ]

    for k in _dplans.keys():
        _dfftw.rfftwnd_destroy_plan( _dplans[ k ] )
        del _dplans[ k ]







'''
>> plan = sfftw.rfftw2d_create_plan(256,256,sfftw.FFTW_FORWARD,
...      sfftw.FFTW_ESTIMATE)
>>> 
>>> a = F.gaussianArr()
>>> a.shape
(256, 256)
>>> af = F.zeroArrC(256,129)
>>> sfftw.rfftwnd_one_real_to_complex(plan,a,af)
>>> Y.view(af)
** split-viewer: complex - used abs()
# window: 0) af
>>> b = F.noiseArr(shape=(256, 256), stddev=1.0, mean=0.0)
>>> bf = F.zeroArrC(256,129)
>>> sfftw.rfftwnd_one_real_to_complex(plan,b,bf)
>>> Y.view(bf)
** split-viewer: complex - used abs()
# window: 1) bf
>>> bb = F.rfft2d(b)
>>> Y.view(bb)
** split-viewer: complex - used abs()
# window: 2) bb
>>> p = {}
>>> p[ ("r",(256,256), sfftw.FFTW_FORWARD) ] = plan

'''


def fft(a,af=None, inplace=0, nthreads=1):
    #CHECK b type size

    if inplace:
        inplace = _sfftw.FFTW_IN_PLACE     # == 8
        shape = a.shape
    else:
        shape = a.shape
        inplace = 0
    dir = _sfftw.FFTW_FORWARD
    if a.dtype == _N.complex64:
        if af is not None and (not af.flags.carray or af.dtype != _N.complex64):
            raise RuntimeError, "af needs to be well behaved complex64 array"
        key = ("s%d"%inplace, shape )

        try:
            p = _splans[ key ]
        except:
            p = _sfftw.fftwnd_create_plan(len(shape), _N.array(shape, dtype=_N.int32), dir,
                    _measure | inplace)
            if p is None:
                raise RuntimeError, "could not create plan"
            _splans[ key ] = p

        if inplace:
            _sfftw.fftwnd_one(p,a,None)
            if af is None:
                s2 = shape
                af = _N.ndarray(buffer=a, shape=s2, dtype=_N.complex64)
                return af
        else:
            if af is None:
                s2 = shape
                af = _N.empty(shape=s2, dtype=_N.complex64)
                _sfftw.fftwnd_one(p,a,af)
                return af
            else:
                _sfftw.fftwnd_one(p,a,af)   


    elif a.dtype == _N.complex128:
        if af is not None and (not af.flags.carray or af.dtype != _N.complex128):
            raise RuntimeError, "af needs to be well behaved complex128 array"
        key = ("d%d"%inplace, shape )

        try:
            p = _dplans[ key ]
        except:
            p = _dfftw.fftwnd_create_plan(len(shape), _N.array(shape, dtype=_N.int32), dir,
                    _measure | inplace)
            if p is None:
                raise RuntimeError, "could not create plan"
            _dplans[ key ] = p

        if inplace:
            _dfftw.fftwnd_one(p,a,None)
            if af is None:
                s2 = shape
                af = _N.ndarray(buffer=a, shape=s2,dtype=_N.complex128)
                return af
        else:
            if af is None:
                s2 = shape
                af = _N.empty(shape=s2, dtype=_N.complex128)
                _dfftw.fftwnd_one(p,a,af)
                return af
            else:
                _dfftw.fftwnd_one(p,a,af)   

    else:
        raise TypeError, "complex64 and complex128 must be used consistently (%s %s)"%\
              ((a is None and "a is None" or "a.dtype=%s"%a.dtype),
               (af is None and "af is None" or "af.dtype=%s"%af.dtype))

def ifft(af, a=None, inplace=0, nthreads=1):
    #CHECK b type size
    global shape,s2

    if inplace:
        inplace = _dfftw.FFTW_IN_PLACE     # == 8
        shape = af.shape
    else:
        shape = af.shape
        inplace = 0
    dir = _sfftw.FFTW_BACKWARD
    if af.dtype == _N.complex64:
        if a is not None and (not a.flags.carray or a.dtype != _N.complex64):
            raise RuntimeError, "a needs to be well behaved complex64 array"
        key = ("si%d"%inplace, shape )

        try:
            p = _splans[ key ]
        except:
            p = _sfftw.fftwnd_create_plan(len(shape), _N.array(shape, dtype=_N.int32), dir,
                    _measure | inplace)
            if p is None:
                raise RuntimeError, "could not create plan"
            _splans[ key ] = p

        if inplace:
            _sfftw.fftwnd_one(p,af,None)
            if a is None:
                s2 = shape
                a = _N.ndarray(buffer=af, shape=s2,dtype=_N.complex64)
                return a
        else:
            if a is None:
                s2 = shape
                a = _N.empty(shape=s2, dtype=_N.complex64)
                _sfftw.fftwnd_one(p,af,a)
                return a
            else:
                _sfftw.fftwnd_one(p,af,a)   


    elif af.dtype == _N.complex128:
        if a is not None and (not a.flags.carray or a.dtype != _N.complex128):
            raise RuntimeError, "a needs to be well behaved complex128 array"
        key = ("di%d"%inplace, shape )

        try:
            p = _dplans[ key ]
        except:
            p = _dfftw.fftwnd_create_plan(len(shape), _N.array(shape, dtype=_N.int32), dir,
                    _measure | inplace)
            if p is None:
                raise RuntimeError, "could not create plan"
            _dplans[ key ] = p

        if inplace:
            _dfftw.fftwnd_one(p,af,None)
            if a is None:
                s2 = shape
                a = _N.ndarray(buffer=af, shape=s2,dtype=_N.complex128)
                return a
        else:
            if a is None:
                s2 = shape
                a = _N.empty(shape=s2, dtype=_N.complex128)
                _dfftw.fftwnd_one(p,af,a)
                return a
            else:
                _dfftw.fftwnd_one(p,af,a)   

    else:
        raise TypeError, "complex64 and complex128 must be used consistently (%s %s)"%\
              ((a is None and "a is None" or "a.dtype=%s"%a.dtype),
               (af is None and "af is None" or "af.dtype=%s"%af.dtype))

