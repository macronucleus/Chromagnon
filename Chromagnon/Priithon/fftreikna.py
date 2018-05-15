import numpy as np
from reikna import cluda
from reikna.fft import FFT

from reikna.cluda.dtypes import complex_for
from reikna.core import Type
from reikna.transformations import combine_complex, broadcast_const

try:
    import pycuda.autoinit
    api = cluda.cuda_api() #get_api('cuda')
except ImportError:
    import pyopencl
    api = cluda.ocl_api()

dev = api.get_platforms()[0].get_devices()[0]

def rfft(a):
    thr = api.Thread(dev)

    fft  = FFT(Type(complex_for(a.dtype), a.shape))

    # combines two real-valued inputs into a complex-valued input of the same shape
    cc = combine_complex(fft.parameter.input)
    # supplies a constant output
    bc = broadcast_const(cc.imag, 0)

    fft.parameter.input.connect(cc, cc.output, real_input=cc.real, imag_input=cc.imag)
    fft.parameter.imag_input.connect(bc, bc.output)

    fftc = fft.compile(thr, fast_math=True)

    a_dev   = thr.to_device(a)
    a_out_dev = thr.empty_like(fft.parameter.output)

    fftc(a_out_dev, a_dev)

    a_out = a_out_dev.get()

    return a_out
