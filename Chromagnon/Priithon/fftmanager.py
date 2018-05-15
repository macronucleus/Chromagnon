from __future__ import print_function
import os, sys
if sys.version_info.major >= 3:
    from importlib import reload
import multiprocessing as mp
import threading as th

## ----- default numpy fft -----
import numpy as N

## ----- fftw -----
try:
    import pyfftw
    FFTW = True
    ncpu = mp.cpu_count()
except ImportError:
    FFTW = False
    ncpu = 1

## ------ gpu fft ------
## in python2, multithreading application is not supported yet..
CUDA = False
SCIK = False
REIK = False
INIT = False
try:
    import pycuda.autoinit
    INIT = True
    from pycuda import gpuarray
    from pycuda import driver
    from pycuda import tools
    from skcuda import fft
    CUDA = True
    SCIK = True
    
    G_RTYPES = {N.float32: N.complex64,
              N.float64: N.complex128}
    G_CTYPES = {N.complex64: N.float32,
              N.complex128: N.float64}
    G_RTYPE = N.float32
    G_CTYPE = N.complex64
except:# ImportError or pycuda._driver.LogicError if NVIDIA graphic card is not available
    pass

try:
    from reikna import cluda
    from reikna.fft import FFT

    from reikna.cluda.dtypes import complex_for
    from reikna.core import Type
    from reikna.transformations import combine_complex, broadcast_const
    REIK = True
    try:
        import pycuda.autoinit
        #api = cluda.cuda_api() #get_api('cuda')
        CUDA = True
        INIT = True
    except ImportError:
        try:
            import pyopencl
        except ImportError:
            REIK = False
        #api = cluda.ocl_api()
except ImportError:
    pass
##  ------ available data types -------
RTYPE = N.float32
RTYPES = (N.float32, N.float64)
CTYPE = N.complex64
CTYPES = (N.complex64, N.complex128)

print('FFTW: ', FFTW)
print('SCIK: ', SCIK)
print('REIK: ', REIK)

# disable GPU functions
SCIK = False
REIK = False
## ------ funcs and classes -----------

def register():
    thread = th.current_thread()
    thread.fftmanager = FFTManager()
    return True

class FFTManager(object):
    def __init__(self):

        self.tid = self.get_current_thread()
        self.pid = self.get_current_process()
        self.ncpu = mp.cpu_count()

        self.init = False
        
        self.make_cuda_context()
        self.init_reikna()

    def __del__(self):
        self.detach_cuda_context()
        
    def make_cuda_context(self):
        global INIT
        if not INIT:
            if CUDA:
                reload(pycuda.autoinit)
                #doing pycuda.autoinit manually
                #driver.init()
                #self.context = tools.make_default_context()

            #self.init = True
            INIT = True

    def detach_cuda_context(self):
        global INIT
        if INIT and CUDA:
            if pycuda.autoinit.context:
                pycuda.autoinit._finish_up()
                pycuda.autoinit.atextit.unregister(_finish_up)
            INIT = False
            #self.context.pop() # empty context stack
            #self.context.detach()
            #tools.clear_context_caches()

    def init_reikna(self):
        if REIK:
            if CUDA:
                self.api = cluda.cuda_api()
            else:
                self.api = cluda.ocl_api()
            self.dev = self.api.get_platforms()[0].get_devices()[0]

    # ---- multithreading --------
    def get_current_thread(self):
        if sys.version_info.major >= 3:
            return th.get_ident()
        else:
            return 1  # FIXME!! how to identify thread in python2??

    def is_same_thread(self):
        return self.tid == self.get_current_thread()

    def get_previous_thread(self):
        thread = [e for e in th.enumerate() if e.ident == self.tid]
        if thread:
            return thread[0]
        else:
            raise ValueError('The previous thread %i was not found' % self.tid)

    def detach_previous_context(self):
        if not self.is_same_thread():
            thread = self.get_previous_thread()
            thread.fftmanager.detach_cuda_context()
        
    # ----- multiprocesses ---------
    def get_current_process(self):
        process = mp.current_process()
        return process.pid

    def is_same_process(self):
        return self.pid == self.get_current_process()

    def get_previous_process(self):
        process = [p for p in mp.active_children() if p.pid == self.pid]
        if process:
            return process[0]
        else:
            #raise ValueError('The previous process %i was not found' % self.pid)
            return mp.current_process()

    # ------ helper funcs ------------------
    def is_gpu_memory_enough(self, a):
        if CUDA:
            rest, total = driver.mem_get_info()
            
            if (sys.getsizeof(a) * 2) < rest:
                return True
        else:
            return True

    def check_array(self, a, types, mintype):
        self.make_cuda_context()
        
        if a.dtype.type not in types:
            a = N.asarray(a, mintype)
        return a

    ### -----fftw -----
    def _fftw(self, a, func, nthreads=ncpu):
        if 0 in a.shape:
            raise ValueError('This array cannot be transformed, shape: %s' % str(a.shape))

        axes = [i - a.ndim for i in range(a.ndim)]
        af = pyfftw.empty_aligned(a.shape, dtype=a.dtype.type.__name__)
        plan = func(af, axes=axes, threads=nthreads)
        af[:] = a[:]
        return plan()

    # ---- scikit cuda -----
    def _fft_scik(self, a, func, shape, dtype):
        arg = gpuarray.to_gpu(a)
        afg = gpuarray.empty(shape, dtype)
        plan = fft.Plan(shape, a.dtype.type, dtype)
        func(arg, afg, plan)
        return afg.get()

    # ---- fft funcs ----------
    
    def rfft(self, a, nthreads=ncpu):
        a = self.check_array(a, RTYPES, RTYPE)
        
        if SCIK and self.is_gpu_memory_enough(a):
            shape = [s for s in a.shape]
            shape[-1] = shape[-1]//2 + 1
            dtype = G_RTYPES[a.dtype.type]
            func = fft.fft
            af = self._fft_scik(a, func, shape, dtype)
            
        elif REIK and self.is_gpu_memory_enough(a):
            thr = self.api.Thread(self.dev)

            plan  = FFT(Type(complex_for(a.dtype), a.shape))

            # combines two real-valued inputs into a complex-valued input of the same shape
            cc = combine_complex(plan.parameter.input)
            # supplies a constant output
            bc = broadcast_const(cc.imag, 0)

            plan.parameter.input.connect(cc, cc.output, real_input=cc.real, imag_input=cc.imag)
            plan.parameter.imag_input.connect(bc, bc.output)

            fftc = plan.compile(thr, fast_math=True)

            a_dev   = thr.to_device(a)
            a_out_dev = thr.empty_like(plan.parameter.output)

            fftc(a_out_dev, a_dev)

            af = a_out_dev.get()
            af = N.fft.fftshift(af)

        elif FFTW:
            func = pyfftw.builders.rfftn

            af = self._fftw(a, func, nthreads)
        else:
            af = N.fft.rfftn(a)

        return af
        
    def irfft(self, a, nthreads=0):
        a = self.check_array(a, CTYPES, CTYPE)
        
        if SCIK and is_memory_enough(a):
            shape = [s for s in a.shape]
            shape[-1] = (shape[-1]-1)*2
            dtype = G_CTYPES[a.dtype.type]
            func = fft.ifft
            af = self._fft_scik(a, func, shape, dtype)

            
        elif FFTW:
            func = pyfftw.builders.irfftn
                
            af = self._fftw(a, func, nthreads=nthreads)

        else:
            af = N.fft.irfftn(a)

        return af

    def fft(self, a, nthreads=ncpu):
        a = self.check_array(a, CTYPES, CTYPE)
        
        if FFTW:
            func = pyfftw.builders.fftn

            af = self._fftw(a, func, nthreads)
        else:
            af = N.fft.fftn(a)
            
        return af

    def ifft(self, a, nthreads=ncpu):
        a = self.check_array(a, CTYPES, CTYPE)
        
        if FFTW:
            func = pyfftw.builders.ifftn
        
            af = self._fftw(a, func, nthreads=nthreads)
        else:
            af = N.fft.ifftn(a)
            
        return af

man = FFTManager()

def rfft(a, nthreads=ncpu):
    return man.rfft(a, nthreads)

def irfft(a, nthreads=ncpu):
    return man.irfft(a, nthreads)

def fft(a, nthreads=ncpu):
    return man.fft(a, nthreads)

def ifft(a, nthreads=ncpu):
    return man.ifft(a, nthreads)
