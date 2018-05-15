import numpy as N
import os, sys
try:
    import pycuda.autoinit
    GPU = True
except:# ImportError or pycuda._driver.LogicError if NVIDIA graphic card is not available
    GPU = False

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

    def _rfft(a, nthreads=ncpu):
        if a.shape[-1] % 2:
            a = N.ascontiguousarray(a[...,:-1])
        shape = list(a.shape)
        shape[-1] = shape[-1] // 2 + 1
        b = N.empty(shape, RTYPES[a.dtype.type])

        return _fft3(a, b, nthreads=nthreads, direction='forward', realtypes='halfcomplex r2c')

    def _irfft(a, normalize=True, nthreads=ncpu):
        a = a.copy() # irfft of fftw3 mess up the input
        shape = list(a.shape)
        shape[-1] = (shape[-1] - 1) * 2
        b = N.empty(shape, CTYPES[a.dtype.type])

        if normalize:
            vol = N.product(a.shape[:-1])
            vol *= (a.shape[-1]-1)*2
        else:
            vol = 1
                
        return _fft3(a, b, nthreads=nthreads, direction='backward', realtypes='halfcomplex r2c') / vol

    def _fft3(a, b, nthreads=ncpu, **kwds):
        if 0 in a.shape:
            raise ValueError('This array cannot be transformed, shape: %s' % str(a.shape))
        modul = MODULS.get(a.dtype.type, fftw3)
        plan = modul.Plan(a, b, nthreads=nthreads, **kwds)
        plan()
        return b

    def fft(a, nthreads=ncpu):
        b = N.empty_like(a) # assuming complex type
        return _fft3(a, b, nthreads=nthreads, direction='forward')

    def ifft(a, normalize=True, nthreads=ncpu):
        a = a.copy() # irfft of fftw3 mess up the input
        b = N.empty_like(a) # assuming complex type

        if normalize:
            vol = N.product(a.shape)
        else:
            vol = 1
        return _fft3(a, b, nthreads=nthreads, direction='backward') / vol


else:
    import numpy.fft as fftw

    ncpu = 1
    
    RTYPE = N.float32
    RTYPES = (N.float32, N.float64)
    CTYPE = N.complex64
    CTYPES = (N.complex64, N.complex128)

    def _rfft(a, nthreads=ncpu):
        return fftw.rfftn(a)

    def _irfft(a, normalize=True, nthreads=ncpu):
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

if GPU:
    # only rfft can be done with skcuda
    # other GPU-based FFT is not compatible with ND arrays
    from pycuda import gpuarray
    from pycuda import driver
    from skcuda import fft

    G_RTYPES = {N.float32: N.complex64,
              N.float64: N.complex128}
    G_CTYPES = {N.complex64: N.float32,
              N.complex128: N.float64}
    G_RTYPE = N.float32
    G_CTYPE = N.complex64

    # child thread cannot use context from the main thread..., call this from the main thread
    def detach_gpu_context():
        pycuda.autoinit.context.pop() # empty context stack -> cannot pop non-current context
        pycuda.autoinit.context.detach()
    
    def is_memory_enough(a):
        try:
            rest, total = driver.mem_get_info()
        except driver.LogicError: # child thread cannot use context from the main thread...
            # the following does not work yet

            from pycuda import tools
            import skcuda
            
            driver.init()
            context = tools.make_default_context() # try to make as new context, but cannot deactivate the old context stack
            device = context.get_device()
            skcuda.misc.init_context(device)
            rest, total = driver.mem_get_info()
            
        if (sys.getsizeof(a) * 2) < rest:
            return True
    
    def rfft(a, nthreads=0):
        if is_memory_enough(a):
            arg = gpuarray.to_gpu(a)
            shape = [s for s in a.shape]
            shape[-1] = shape[-1]//2 + 1
            ctype = G_RTYPES[a.dtype.type]
            afg = gpuarray.empty(shape, ctype)
            plan = fft.Plan(shape, a.dtype.type, ctype)
            print(shape, a.dtype.type, ctype)
            fft.fft(arg, afg, plan)
            return afg.get()
        else:
            return _rfft(a)

    def irfft(a, normalize=True, nthreads=0):
        if is_memory_enough(a):
            arg = gpuarray.to_gpu(a)
            shape = [s for s in a.shape]
            shape[-1] = (shape[-1]-1)*2
            rtype = G_CTYPES[a.dtype.type]
            afg = gpuarray.empty(shape, rtype)
            plan = fft.Plan(shape, a.dtype.type, rtype)
            fft.ifft(arg, afg, plan)
            return afg.get()
        else:
            return _irfft(a)

else:
    rfft  = _rfft
    irfft = _irfft
    fft   = fft
    ifft  = ifft
