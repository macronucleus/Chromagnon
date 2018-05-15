import numpy as N
import os, sys
try:
    import pyfftw
    FFTW = True
except ImportError:
    FFTW = False

if FFTW:
    import multiprocessing as mp
    ncpu = mp.cpu_count()

    def _fft(a, func, nthreads=ncpu, **kwds):
        if 0 in a.shape:
            raise ValueError('This array cannot be transformed, shape: %s' % str(a.shape))

        axes = [i - a.ndim for i in range(a.ndim)]
        af = pyfftw.empty_aligned(a.shape, dtype=a.dtype.type.__name__)
        plan = func(af, axes=axes, threads=nthreads)
        af[:] = a[:]
        return plan()

    def rfft(a, nthreads=ncpu):
        func = pyfftw.builders.rfftn

        return _fft(a, func, nthreads)

    def irfft(a, nthreads=ncpu):
        func = pyfftw.builders.irfftn
                
        return _fft(a, func, nthreads=nthreads)


    def fft(a, nthreads=ncpu):
        func = pyfftw.builders.fftn

        return _fft(a, func, nthreads)

    def ifft(a, nthreads=ncpu):
        func = pyfftw.builders.ifftn
        
        return _fft(a, func, nthreads=nthreads)


else:
    import numpy.fft as fftw

    ncpu = 1
    
    RTYPE = N.float32
    RTYPES = (N.float32, N.float64)
    CTYPE = N.complex64
    CTYPES = (N.complex64, N.complex128)

    def rfft(a, nthreads=ncpu):
        return fftw.rfftn(a)

    def irfft(a, normalize=True, nthreads=ncpu):
        if normalize:
            return fftw.irfftn(a)
        else:
            return fftw.irfft(a)

    def fft(a, nthreads=ncpu):
        return fftw.fftn(a)

    def ifft(a, normalize=True, nthreads=ncpu):
        if normalize:
            return fftw.ifftn(a)
        else:
            return fftw.ifft(a)
