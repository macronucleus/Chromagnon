import numpy as N
import os, sys
try:
    import fftw3
    FFTW = True
except ImportError:
    FFTW = False

if FFTW:
    MODULS = {N.float64: fftw3,
              N.complex128: fftw3}
    RTYPES = {N.float64: N.complex128}
    CTYPES = {N.complex128: N.float64}
    RTYPE = N.float64
    CTYPE = N.complex128

    try:
        import fftw3f
        MODULS[N.float32] = fftw3f
        MODULS[N.complex64] = fftw3f
        RTYPES[N.float32] = N.complex64
        CTYPES[N.complex64] = N.float32
        osbit = 32
        if sys.platform == 'win32':
            if sys.maxsize > (2**32):
                osbit = 64
        elif os.uname()[-1] != 'x86_64':
            osbit = 64
        if osbit == 64:
            RTYPE = N.float32
            CTYPE = N.complex64
    except ImportError:
        RTYPES[N.float32] = N.complex128
        CTYPES[N.complex64] = N.float64
    if hasattr(N, 'float128'):
        try:
            import fftw3l
            MODULS[N.float128] = fftw3l
            MODULS[N.complex256] = fftw3l
            RTYPES[N.float128] = N.complex256
            CTYPES[N.complex256] = N.float128
        except ImportError:
            RTYPES[N.float128] = N.complex128
            CTYPES[N.complex256] = N.float64
    else:
        pass
        #print 'WARNING: your numpy does not support fftw3 long-double'

    try:
        import multiprocessing as mp
        ncpu = mp.cpu_count()
    except ImportError:
        ncpu = 1

    def rfft(a):
        if a.shape[-1] % 2:
            a = N.ascontiguousarray(a[...,:-1])
        shape = list(a.shape)
        shape[-1] = shape[-1] // 2 + 1
        b = N.empty(shape, RTYPES[a.dtype.type])

        return _fft(a, b, direction='forward', realtypes='halfcomplex r2c')

    def irfft(a):
        a = a.copy() # irfft of fftw3 mess up the input
        shape = list(a.shape)
        shape[-1] = (shape[-1] - 1) * 2
        b = N.empty(shape, CTYPES[a.dtype.type])
        return _fft(a, b, direction='backward', realtypes='halfcomplex r2c')

    def _fft(a, b, **kwds):
        if 0 in a.shape:
            raise ValueError, 'This array cannot be transformed, shape: %s' % str(a.shape)
        modul = MODULS.get(a.dtype.type, fftw3)
        plan = modul.Plan(a, b, nthreads=ncpu, **kwds)
        plan()
        return b

    def fft(a):
        b = N.empty_like(a) # assuming complex type
        return _fft(a, b, direction='forward')

    def ifft(a):
        a = a.copy() # irfft of fftw3 mess up the input
        b = N.empty_like(a) # assuming complex type
        return _fft(a, b, direction='backward')


else:
    import numpy.fft as fftw

    RTYPE = N.float32
    RTYPES = (N.float32, N.float64)
    CTYPE = N.complex64
    CTYPES = (N.complex64, N.complex128)

    def rfft(a):
        return fftw.rfftn(a)

    def irfft(a): # not required to normalize
        return fftw.irfftn(a)

    def fft(a):
        return fftw.fftn(a)

    def ifft(a):
        return fftw.ifftn(a)
