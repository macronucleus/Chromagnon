"""Priithon F module: F as in FFT (todo: cleanup) and
                        as in Fields (think, physics - or German)
"""
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import numpy as N

from . import fftmanager as fftw #fftwam as fftw
from functools import reduce

defshape = (256,256)  #use this default shape to make testing easy

def __fromfunction(f, s, t):
    return N.fromfunction(f,s).astype(t)

def _normalize_shape(shape):
    """
    return shape 
    in case a scalar was given:
    return (shape,) 
    """
    try:
        len(shape)
        return shape
    except TypeError:
        return (shape,)
def _normailze_ndparm(ndparm, rank):
    """
    check that nd parm is either scalar or of length rank
    if scalar return (ndparm,)*rank
    """
    try:
        if len(ndparm) != rank:
            raise ValueError("ndparm must be of length %d"%rank)
        return ndparm
    except TypeError:
        return (ndparm,)*rank

    
def zeroArr(dtype, *shape):
    """allocates and returns array of given dtype and shape"""
    if type(shape[0]) == tuple:
        shape = shape[0]
    return N.zeros(dtype=dtype, shape=shape)
def zeroArrF(*shape):
    """allocates and returns 'single prec. float' array of given shape"""
    return zeroArr(N.float32, *shape)
def zeroArrD(*shape):
    """allocates and returns 'double prec. float' array of given shape"""
    return zeroArr(N.float64, *shape)
def zeroArrC(*shape):
    """allocates and returns 'single prec. complex' array of given shape"""
    return zeroArr(N.complex64, *shape)
def zeroArrCC(*shape):
    """allocates and returns 'double prec. complex' array of given shape"""
    return zeroArr(N.complex128, *shape)
def zeroArrU(*shape):
    """allocates and returns '16bit unsigned int' array of given shape"""
    return zeroArr(N.uint16, *shape)
def zeroArrI(*shape):
    """allocates and returns '32bit signed int' array of given shape"""
    return zeroArr(N.int32, *shape)
def zeroArrS(*shape):
    """allocates and returns '16bit signed int' array of given shape"""
    return zeroArr(N.int16, *shape)
def zeroArrB(*shape):
    """allocates and returns '8 bit unsigned int' array of given shape"""
    return zeroArr(N.uint8, *shape)
#emptyArrF=zeroArrF


def copyPadded(a,b, pad=0):
    """
    copy (smaller) array a into center of (larger) array b
    set border values in b to 'pad'
    if a is really larger than b than it is the inverse operation
    (and 'pad' is ignored)
    """

    if a.ndim != b.ndim:
        raise ValueError("arrays need to be of same ndim")
    
    ######## print
    dS = N.subtract(b.shape, a.shape)
    # if padding wanted and if NOT all UN-padding
    if pad is not None and not N.alltrue( dS <= 0 ):
        b[:] = pad #HACK - because not very efficient !?
       
    for i in range(a.ndim):
        a = N.transpose(a, [a.ndim-1]+list(range(a.ndim-1)))
        b = N.transpose(b, [b.ndim-1]+list(range(b.ndim-1)))
        dS = b.shape[0] - a.shape[0]
        d2 = dS//2
        #print i, "AA)", a.shape[0], b.shape[0], dS, d2
        if dS > 0:
            b = b[d2:d2+ a.shape[0] ]
        elif dS < 0:
            if dS % 2:  # otherwise going from odd size to even size and back shifts by 1
                d2+=1
            a = a[-d2:-d2+ b.shape[0] ]
    b[:] = a


def getByteSwapped(arr):
    """
    returns byteswapped version of arr
    all values should be the same as in arr
    only memory representation and byteorder-flag are changed
    """
    return arr.byteswap().view(arr.dtype.newbyteorder())
def getWithoutBorder(arr, border=10):
    """
    returns 'view' of arr excluding border

    if border is a scalar:
       border elements get cut out on both ends in each axis
    if border is an array 
       the number of cut out elements in axis a in taken from border[a]
       if border length is to short, border gets extended with its "last" entry
          -> e.g. arr.ndim=3, border=(0,10) --> border gets changed to (0,10,10)

    array will not be contiguous
    """
    a = N.asanyarray(arr)
    border = N.asarray(border)
    if border.ndim == 0:
        border.shape=1
    lb = len(border)
    if len(border) < a.ndim:
        border = N.resize(border, a.ndim)
        border[lb:] = border[lb-1]
    # CHECK should we raise if lower or upper outside a !?

    for i in range(a.ndim):
        lower = border[-i]
        upper = len(a)-border[-i]
        a = a[lower:upper]
        a = N.transpose(a, [a.ndim-1]+list(range(a.ndim-1)))
        #border[:] = [border[-1]]+border[:-1]
    return a
    
def getPadded(a, shape, pad=0, dtype=None): 
    """
    create and return array b of given shape and dtype(default: use a.dtype)
    copy (smaller) array a into center of (larger) array b
    set border values in b to 'pad'
    in case that 'a' is larger than 'b' then it the inverse operation is done
      (and 'pad' is ignored)
    """
    if dtype is None:
        dtype=a.dtype
    b = N.empty(shape, dtype)
    copyPadded(a,b,pad)
    return b

def getThresholded(arr, min=0, force0Base=False):
    """
    creates new array with same values as 
    arr except where arr is less than min.
    Those are set to min, unless 

    if force0Base is true:
      new min is set to 0; all other pixels are subtracted by min
    """
    arr = N.asarray(arr)
    if force0Base:
        return N.where(  arr > min, arr-min, 0   )
    else:
        return N.where(  arr > min, arr, min   )


def bin2d(inArr, outArr, binX=2, binY=2):
    from . import useful as U
    U.checkGoodArrayF(outArr, 1, (inArr.shape[0]//binY, inArr.shape[1]//binX))

    if inArr.dtype.isnative:
        inArr = N.ascontiguousarray(inArr)
    else:
        inArr = N.ascontiguousarray(inArr, inArr.dtype.newbyteorder('='))
    import Priithon_bin.seb as S
    S.bin2d(inArr, outArr, binX, binY)


def getXZview(arr, zaxis=-3):
    s = list(range(arr.ndim))
    s[zaxis],s[-2] = s[-2],s[zaxis]
    return N.transpose(arr, s)
def getYZview(arr, zaxis=-3):
    s = list(range(arr.ndim))
    s[zaxis],s[-1] = s[-1],s[zaxis]
    return N.transpose(arr, s)
    

def getHistEqualizedF(arr, histYX=None, nBins=None):
    """
    calculate and return the histogram equalized copy of arr 
        (dtype=float32, min..max = 0..1)

    histYX, is the histogram of `a` -- a tuple(binCount, binPixelValue)
    if histYX is None:
       calculate histogram using nBins bins
        if nBins is None:
            nBins = int(amax-amin+1)
            if arr is of float dtype   and nBins < 1000:
                nBins = 1000
    """
    from .useful import histogramYX

    if histYX is None:
        if nBins is None:
            amin, amax = arr.min(), arr.max()
            nBins = int(amax-amin+1)
            if N.issubdtype(float, arr.dtype) and nBins < 1000:
                nBins = 1000
        h,x = histogramYX(arr, nBins=nBins)
    else:
        h,x = histYX

    hcs = N.cumsum(h, dtype=N.float32)
    hcs /= hcs[-1]

    xMin = float(x[0])
    xRange = float(x[-1]) - xMin
    nBins = len(h)
    scale = (nBins-1)/xRange
    aHistEq = hcs[ N.array(.5+scale*(arr-xMin), dtype=N.int) ]
    return aHistEq

###################################################################
## generate some arrays
###################################################################


def radialPhiArr(shape, func, orig=None, dtype=N.float32):
    """generates and returns radially symmetric function sampled in volume(image) of shape shape
    if orig is None the origin defaults to the center
    func is a 1D function with 2 paramaters: r,phi

    
    dtype is Float32
    """
    shape = _normalize_shape(shape)
    if orig is None:
        orig = (N.array(shape, dtype=N.float)-1) / 2.
    else:
        try:
            oo = float(orig)
            orig = N.ones(shape=len(shape)) * oo
        except:
            pass
    
    if len(shape) != len(orig):
        raise ValueError("shape and orig not same dimension")

    if len(shape) == 2:
        y0,x0 = orig
        return __fromfunction(lambda y,x: func(
                                             N.sqrt( \
            (x-x0)**2 + (y-y0)**2 ), N.arctan2((y-y0), (x-x0)) ), shape, dtype)
    elif len(shape) == 3:
        z0,y0,x0 = orig
        return __fromfunction(lambda z,y,x: func(
                                             N.sqrt( \
            (x-x0)**2 + (y-y0)**2 + (z-z0)**2 ), N.arctan2((y-y0), (x-x0)) ),
                              shape, dtype)
    else:
        raise ValueError("only defined for 1< dim <= 3")


def radialArr(shape, func, orig=None, wrap=False, dtype=N.float32):
    """generates and returns radially symmetric function sampled in volume(image) of shape shape
    if orig is None the origin defaults to the center
    func is a 1D function with 1 paramater: r

    if shape is a scalar uses implicitely `(shape,)`
    wrap tells if functions is continued wrapping around image boundaries
    wrap can be True or False or a tuple same length as shape:
       then wrap is given for each axis sperately
    """
    shape = _normalize_shape(shape)
    try:
        len(shape)
    except TypeError:
        shape = (shape,)

    if orig is None:
        orig = (N.array(shape, dtype=N.float)-1) / 2.
    else:
        try:
            oo = float(orig)
            orig = N.ones(shape=len(shape)) * oo
        except:
            pass
                
    if len(shape) != len(orig):
        raise ValueError("shape and orig not same dimension")

    try: 
        if len(wrap) != len(shape):
            raise ValueError("wrap tuple must be same length as shape")
    except TypeError:
        wrap = (wrap,)*len(shape)

    def wrapIt(ax, q):
        if wrap[ax]:
            nq = shape[ax]
            return N.where(q>nq/2.,q-nq, q)
        else:
            return q

#     if wrap:
#         def wrapIt(q, nq):
#             return N.where(q>nq/2,q-nq, q)
#     else:
#         def wrapIt(q, nq):
#             return q

#     if len(shape) == 1:
#         x0 = orig[0] # 20060606: [0] prevents orig (as array) promoting its dtype (e.g. Float64) into result
#         nx = shape[0]
#         return __fromfunction(lambda x: func(wrapIt(N.absolute(x-x0),nx)), shape, dtype)
#     elif len(shape) == 2:
#         y0,x0 = orig
#         ny,nx=shape
#         return __fromfunction(lambda y,x: func(
#                                              N.sqrt( \
#             (wrapIt((x-x0),nx))**2 + (wrapIt((y-y0),ny))**2 ) ), shape, dtype)
#     elif len(shape) == 3:
#         z0,y0,x0 = orig
#         nz,ny,nx=shape
#         return __fromfunction(lambda z,y,x: func(
#                                              N.sqrt( \
#             (wrapIt((x-x0),nx))**2 + (wrapIt((y-y0),ny))**2 + (wrapIt((z-z0),nz))**2 ) ), shape, dtype)
    if len(shape) == 1:
        x0 = orig[0] # 20060606: [0] prevents orig (as array) promoting its dtype (e.g. Float64) into result
        return __fromfunction(lambda x: func(wrapIt(0,N.absolute(x-x0))), shape, dtype)
    elif len(shape) == 2:
        y0,x0 = orig
        return __fromfunction(lambda y,x: func(
                                             N.sqrt( \
            (wrapIt(-1,x-x0))**2 + (wrapIt(-2,y-y0))**2 ) ), shape, dtype)
    elif len(shape) == 3:
        z0,y0,x0 = orig
        return __fromfunction(lambda z,y,x: func(
                                             N.sqrt( \
            (wrapIt(-1,x-x0))**2 + (wrapIt(-2,y-y0))**2 + (wrapIt(-3,z-z0))**2 ) ), shape, dtype)
    else:
        raise ValueError("only defined for dim < 3 (TODO)")

def maxNormRadialArr(shape, func, orig=None, wrap=0, dtype=N.float32):
    """like radialArr but instead of using euclidian distance to determine r
       (r = (dx**2 + dy**2) **.5)
       this using the a maximum funtion:
      r = max(dx,dy)
       """
    shape = _normalize_shape(shape)
    if orig is None:
        orig = (N.array(shape, dtype=N.float)-1) / 2.
    else:
        try:
            oo = float(orig)
            orig = N.ones(shape=len(shape)) * oo
        except:
            pass
    
    if len(shape) != len(orig):
        raise ValueError("shape and orig not same dimension")

    if wrap:
        def wrapIt(q, nq):
            return N.where(q>nq/2.,q-nq, q)
    else:
        def wrapIt(q, nq):
            return q

    if len(shape) == 1:
        x0 = orig[0] # 20060606: [0] prevents orig (as array) promoting its dtype (e.g. Float64) into result
        nx = shape[0]
        return __fromfunction(lambda x: func(N.absolute(wrapIt(x-x0,nx))), shape, dtype)
    elif len(shape) == 2:
        y0,x0 = orig
        ny,nx=shape
        return __fromfunction(lambda y,x: func(
                                             N.maximum( \
            N.absolute(wrapIt(x-x0,nx)), N.absolute(wrapIt(y-y0,ny)) ) ), shape, dtype)
    elif len(shape) == 3:
        z0,y0,x0 = orig
        nz,ny,nx=shape      
        return __fromfunction(lambda z,y,x: func(
             N.maximum.reduce(  \
            (N.absolute(wrapIt(x-x0,nx)) , N.absolute(wrapIt(y-y0,ny)) , N.absolute(wrapIt(z-z0,nz)) )) ), shape, dtype)
    else:
        raise ValueError("only defined for dim < 3 (TODO)")




###### Mexican Hat ###########


_mexhatNorm = 2./N.sqrt(3.) * N.pi ** -.25

def mexhat(r, dim=1):
    """use LoG instead for proper scaling and normalization in dim>1"""
    global _mexhatNorm
    return _mexhatNorm * (dim-r**2) * N.exp(-r**2 * .5)

def LoG(r,sigma=None, dim=1, r0=None, peakVal=None):
    """note:
         returns *negative* Laplacian-of-Gaussian (aka. mexican hat)
         zero-point will be at sqrt(dim)*sigma
         integral is _always_ 0
         if peakVal is None:  uses "mathematical" "gaussian derived" norm
         if r0 is not None: specify radius of zero-point (IGNORE sigma !!)
    """
    r2 = r**2

    if sigma is None:
        if r0 is not None:
            sigma = float(r0) / N.sqrt(dim)
        else:
            raise ValueError("One of sigma or r0 have to be non-None")
    else:
        if r0 is not None:
            raise ValueError("Only one of sigma or r0 can be non-None")
    s2 = sigma**2
    dsd = dim*sigma**dim

    if peakVal is not None:
        norm = peakVal / dsd
    else:
        norm = 1./(s2 * (2.*N.pi * sigma)**(dim/2.))
    return N.exp(-r2/(2.*s2)) * (dsd - r2) * norm

###### Mexican Hat ###########

def LoGArr(shape=defshape, r0=None, sigma=None, peakVal=None, orig=None, wrap=0, dtype=N.float32):
    """returns n-dim Laplacian-of-Gaussian (aka. mexican hat)
    if peakVal   is not None
         result max is peakVal
    if r0 is not None: specify radius of zero-point (IGNORE sigma !!)
    """
    shape = _normalize_shape(shape)
    dim=len(shape)
    return radialArr(shape,
                     lambda r: LoG(r,sigma=sigma,dim=dim,r0=r0,peakVal=peakVal),
                     orig, wrap, dtype)
def cone(r, dim=1, Yscale=1.):
    top = 1.
    a = top - N.absolute(r)
    return N.where(a<0,0,a * Yscale )


def coneArr(shape=defshape, radius=30, integralScale=1.0, orig=None, wrap=0, dtype=N.float32):
    shape = _normalize_shape(shape)
    d= len(shape)
    if d ==1:
        V = radius
    else:
        V = N.pi * radius **d / 3.
        # CHECK:  raise "todo: coneArr for dimension > 3"
    return radialArr(shape, 
                     lambda r: cone(r/float(radius), d, 1./V * integralScale),
                     orig, wrap, dtype)

def discArr(shape=defshape, radius=30, orig=None, valIn=1, valOut=0, wrap=0, dtype=N.float32):
    return radialArr(shape,
                     lambda r: N.where(r<=radius, valIn, valOut),
                     orig, wrap, dtype)

def ringArr(shape=defshape, radius1=20, radius2=40, orig=None, wrap=0, dtype=N.float32):
    a = radialArr(shape,
                     lambda r: N.where(r<=radius1, 0, r),
                     orig, wrap, dtype)
    a[ a > radius2 ] = 0
    a[ a > 0 ]       = 1
    return a


def squareArr(shape=defshape, radius=30, orig=None, valIn=1, valOut=0, wrap=0, dtype=N.float32):
    return maxNormRadialArr(shape,
                            lambda r: N.where(r<=radius, valIn, valOut),
                            orig, wrap, dtype)

def mexhatArr(shape=defshape, scaleHalfMax=30, orig=None, wrap=0, dtype=N.float32):
    scaleHalfMax = float(scaleHalfMax)
    """deprecated !! use LoGArr instead for proper scaling and normalization in dim>1"""

    shape = _normalize_shape(shape)
    d= len(shape)
    return radialArr(shape,
                     lambda r: mexhat(r/float(scaleHalfMax), d),
                     orig, wrap, dtype)

def cosSqDiscArr(shape=defshape, radius=30, orig=None, wrap=0,crop=0, dtype=N.float32):
    """ radius is r-distance where functions == 0
        if crop is True forces all values at r > radius to 0
    """
    radius2 = radius/(N.pi/2)
    if crop:
        return radialArr(shape,
                            lambda r: N.where(r>radius,0,N.cos(r/radius2)**2),
                            orig, wrap, dtype)
    else:
        return radialArr(shape,
                            lambda r: N.cos(r/radius2)**2,
                            orig, wrap, dtype)

def sinc(r):
    #numoy as opposed to numarray ignores 'divide' error by default !
    a = N.where(r, N.divide(N.sin(r),r), 1)
    return a
def sincArr(shape=defshape, radius=30, orig=None, wrap=0,crop=0, dtype=N.float32):
    """ radius is r-distance where functions == 0
        if crop is True forces all values at r > radius to 0
    """
    radius2 = radius/(N.pi/2)
    if crop:
        return radialArr(shape,
                            lambda r: N.where(r>radius,0,sinc(r/radius2)),
                            orig, wrap, dtype)
    else:
        return radialArr(shape,
                            lambda r: sinc(r/radius2), \
                            orig, wrap, dtype)


def gaussian(r, dim=1, sigma=1., integralScale=None, peakVal=None):
    """returns n-dim Gaussian centered at 0
    if integralScale is not None
         result.sum() == integralScale
    if peakVal       is not None
         result max is peakVal
    if both are None
         results defaults to integralScale==1
    """
    #sigma = _normalize_ndparm(sigma)
    # sigma = float(sigma)
    if integralScale is None and peakVal is None:
        integralScale = 1.
    if integralScale is not None:
        # *N.prod(sigma))
        f = 1./ ( N.sqrt(2.*N.pi) * sigma)**dim   * integralScale
    elif peakVal is not None:
        f = peakVal

    f2 = 2. * sigma**2
    return f*N.exp(-r**2/f2)

def gaussianArr(shape=defshape, sigma=30, integralScale=None, peakVal=None,
                orig=None, wrap=0, dtype=N.float32):
    """returns n-dim Gaussian
    if integralScale is not None
         result.sum() == integralScale
    if peakVal       is not None
         result max is peakVal
    if both are None
         results defaults to integralScale==1
    """
    shape = _normalize_shape(shape)
    return radialArr(shape,
                     lambda r:gaussian(r, len(shape), sigma, integralScale, peakVal),
                     orig, wrap, dtype)

def lorentzian(r, dim=1, sigma=1., integralScale=None, peakVal=None):
    """returns n-dim Lorentzian (Cauchy) function centered at 0
    if integralScale is not None
         result.sum() == integralScale
    if peakVal       is not None
         result max is peakVal
    if both are None
         results defaults to integralScale==1
    """
    from . import useful as U

    ff = 1.
    if integralScale is not None:
        ff = integralScale
    elif peakVal is not None:
        ff = peakVal/lorentzian(0,dim,sigma)

    S = N.abs(sigma)
    n1_2 = (dim+1)*.5
    f = ff*  U.gamma(n1_2)/(N.pi**n1_2 * S)

    return f*(1+r**2/S)**-n1_2
    
def lorentzianArr(shape=defshape, sigma=30, integralScale=None, peakVal=None,
                orig=None, wrap=0, dtype=N.float32):
    """returns n-dim Lorentzian (Cauchy) function
    if integralScale is not None
         result.sum() == integralScale
    if peakVal       is not None
         result max is peakVal
    if both are None
         results defaults to integralScale==1
    """
    shape = _normalize_shape(shape)
    return radialArr(shape,
                     lambda r:lorentzian(r, len(shape), sigma, integralScale, peakVal),
                     orig, wrap, dtype)


def sigmoid(x, x0=0, b=1): #, dtype=N.float32):
    """
    returns the sigmoid function at x.
    parameters:
       x0: center of "input intensity"
       b: range or width of "input intensity" (will map into 27-73% range of output)
    """
    #x  = N.asanyarray(x,dtype)
    #x0 = N.asanyarray(x0,dtype)
    #b  = N.asanyarray(b, dtype)
    x0 = float(x0)
    b = float(b)
    return 1. / (1. + N.exp(-(x-x0)/b))

def noiseArr(shape=defshape, stddev=1., mean=0.0, dtype=N.float32):
    return N.random.normal(mean, stddev,shape).astype(dtype)
def poissonArr(shape=defshape, mean=1, dtype=N.uint16):
    if mean == 0:
        return zeroArrF(shape)
    elif mean < 0:
        raise ValueError("poisson not defined for mean < 0")
    else:
        return N.random.poisson(mean, shape).astype(dtype)

def poissonize(arr, dtype=N.uint16):
    return N.where(arr<=0, 0, N.random.poisson(arr)).astype(dtype)


# what was this for ????
#   oh yeah - to test my "roating and flipping" CCD cameras
def testImgR(shape=defshape, dtype=N.float32):
    """
    some  non symmetric test image (weird "R shape")
    """
    a = zeroArr(dtype, shape)
    h,w = shape[-2:]

    x25 = int(w*.25)
    y2 = int(h*.2)
    y8 = int(h*.8)
    y5 = int(h*.5)

    x5 = int(w*.5)
    x6 = int(w*.6)
    y55 = int(h*.55)

    a[..., y2:y8,  x25] += 1

    for x in range(x25, x6):
        a[..., y8-x,x] +=1
    for p in N.arange(N.pi/2, -N.pi/4, -.01):
        x,y = x25+N.cos(p)*x25,  y55+N.sin(p)*x25
        a[..., int(y),int(x)] +=1
    
    return a

def rampArr(shape=defshape, axis=-1, start=0,stop=None, dtype=None):
    """
    return arr with values increasing along `axis`
    starting with start

    if stop is None: values will go from start..start+N-1 (N being the length of the given axis)
    if start is None: values will be the reverse of when only stop is None 
    if dtype is None:
        dtype = N.int16 if start or stop is None
        dtype = N.float32 otherwise
    """
    if dtype is None:
        if stop is None or start is None:
            dtype = N.int16
        else:
            dtype = N.float32
    if start is None:
        if stop is None:
            stop = 0
        start = stop+shape[axis]-1
    elif stop is None:
        stop = start+shape[axis]-1

    num = shape[axis]
    arr = N.empty(shape, dtype)
    if axis <0:
        axis += len(shape)
    numNewAxes=len(shape)-1-axis
    idxTup = (slice(None),)+(None,)*numNewAxes
    arr[:] = N.linspace(start,stop, num, endpoint=True, retstep=False)[idxTup]
    return arr

def binaryStructure_Zero(rank, connectivity):
    """
    returns  nd.generate_binary_structure

    but also sets structure[0] =  structure[-1] = False
    #old  if zeroBothEndsAxis is not None:
    #old  overide 
    """
    structure = nd.generate_binary_structure(rank, connectivity)
    structure[0] =  structure[-1] = False
    return structure

def binaryStructure_2dDisc_in3d(shape2d=(5,5), r=2.5):
    """
    returns bool array shape=(3,<shape2d>)

    first and last z section all False
    middle z section is a F.discArr with given r
    """
    structure = zeroArr(bool, (3,)+tuple(shape2d))
    structure[1] = discArr(shape2d, r, dtype=bool)

    return structure


    

###################################################################
## FFT   
###################################################################

def shuffle4irfft(arr):
    global ny,nx,nx2,nx21,ny2, a
    ny,nx = arr.shape[-2:]
    if nx % 2 or ny %2:
        raise RuntimeError("TODO")
    else:
        nx2 = nx // 2
        nx21 = nx2 + 1
        ny2 = ny // 2
        pass

    

    a = zeroArrF(arr.shape[:-1] + (nx21,))
    
    a[..., :ny2, :nx2] = arr[..., ny2:,nx2:]
    a[..., ny2:, :nx2] = arr[..., :ny2,nx2:]
    a[..., :ny2, nx2] = arr[..., ny2:,0]
    a[..., ny2:, nx2] = arr[..., :ny2,0]

    return a

def shift(arr, delta=None): #20081113 , dtype=N.float32):
    """
    returns new array: arr shifted by delta (tuple)
       it uses rfft, multiplying with "shift array", irfft
    delta defaults to half of arr.shape 

    #20081113 dtype option removed (FIXME TODO)
    """
    #20081113 from numpy import fft
    shape = arr.shape
    if delta is None:
        delta = N.array(shape) / 2.
    elif not hasattr(delta, '__len__'):
        delta = (delta,)*len(shape)
    elif len(shape) != len(delta):
        raise ValueError("shape and delta not same dimension")

    return irfft(fourierRealShiftArr(shape, delta) *
                                    rfft(arr))
#     else:
#         ax = range(-len(shape),0)
#         return fft.irfftn(fourierRealShiftArr(shape, delta) *
#                           fft.rfftn(arr, axes=ax), axes=ax).astype(dtype)


    
def fourierRealShiftArr(shape=defshape, delta=None, dtype=N.float32):
    return fourierShiftArr(shape, delta, 1, dtype)

def fourierShiftArr(shape=defshape, delta=None, meantForRealFFT=False, dtype=N.float32):
    if delta is None:
        delta = N.array(shape) / 2.
    
    if len(shape) != len(delta):
        raise ValueError("shape and delta not same dimension")

    if meantForRealFFT:
        nx = shape[-1]
        if nx % 2:
            raise ValueError("shape must be even sized in last dimension if meantForRealFFT")

    f = 2j*N.pi

    if len(shape) == 1:
        nX = shape[0]
        dx = delta[0]
        dx = - float(dx) / float(nX)
        if meantForRealFFT:
            shape = shape[:-1] + ( shape[-1]//2 + 1 ,)
        return __fromfunction(lambda x: \
                               N.exp(f*x* dx), shape, dtype)
    elif len(shape) == 2:
        nY,nX = shape
        dy,dx = delta
        dy = - float(dy) / float(nY)
        dx = - float(dx) / float(nX)
        if meantForRealFFT:
            shape = shape[:-1] + ( shape[-1]//2 + 1 ,)
        return __fromfunction(lambda y,x: \
                               N.exp(f*(y* dy +
                                         x* dx )), shape, dtype)
    elif len(shape) == 3:
        nZ,nY,nX = shape
        dz,dy,dx = delta
        dz = - float(dz) / float(nZ)
        dy = - float(dy) / float(nY)
        dx = - float(dx) / float(nX)
        if meantForRealFFT:
            shape = shape[:-1] + ( shape[-1]//2 + 1 ,)
        return __fromfunction(lambda z,y,x: \
                               N.exp(f*(z* dz +
                                         y* dy +
                                         x* dx )) , shape, dtype)
    
'''
    dim = N.array(shape, dtype=N.float)
    dr = N.array(delta, dtype=N.float)
    dr *= -1. / dim 
    print shape, dr
    if meantForRealFFT:
            shape = shape[:-1] + ( shape[-1]/2 + 1 ,)
    return __fromfunction(lambda *r: \
                               N.exp(f*(N.dot(N.array(r), dr))), shape)
'''


###############from numarray import fft as FFT
#shortcuts

#  fft    = FFT.fftnd
#  fft2d  = FFT.fft2d
#  fft1d  = FFT.fft

#  rfft    = FFT.real_fftnd
#  rfft2d  = FFT.real_fft2d
#  rfft1d  = FFT.real_fft

#  ifft    = FFT.inverse_fftnd
#  ifft2d  = FFT.inverse_fft2d
#  ifft1d  = FFT.inverse_fft

#  irfft    = FFT.inverse_real_fftnd
#  irfft2d  = FFT.inverse_real_fft2d
#  irfft1d  = FFT.inverse_real_fft


def fft(a, minCdtype=fftw.CTYPE):
    """
    calculate nd fourier transform
    performs full, i.e. non-real, fft

    `a` should be a complex array,
      otherwise it gets converted to
      minCdtype
    """
    if a.dtype.type not in fftw.CTYPES:
        a = N.asarray(a, minCdtype)

    return fftw.fft(a)
def ifft(af, minCdtype=fftw.CTYPE):#normalize=True, minCdtype=fftw.CTYPE):
    """
    calculate nd inverse fourier transform
    performs full, i.e. non-real, ifft
    
    fftw does NOT normalize (divide by product of shape)
    they argue that the normalization can often be combined with other
    operation and thus save a loop through the data

    if normalize is True: the division is done -- and normilized data is returned

    `af` should be a complex array,
      otherwise it gets converted to
      minCdtype
    """
    if af.dtype.type not in fftw.CTYPES:
        af = N.asarray(af, minCdtype)

    return fftw.ifft(af)#, normalize=normalize)

def fft2d(a):#, minCdtype=fftw.CTYPE):
    func = fft
    return _process2d(func, a)#, minCdtype)

def ifft2d(a):#, minCdtype=fftw.CTYPE):
    func = ifft
    return _process2d(func, a)#, minCdtype)

def _process2d(func, a, minCdtype=fftw.CTYPE):
    if a.dtype.type not in fftw.CTYPES:
        aDtype = minCdtype
    else:
        aDtype = a.dtype.type # ensures native byte-order ?

    s2 = a.shape
    af = N.empty(shape=s2, dtype=aDtype)
    
    for tup in N.ndindex(a.shape[:-2]):
        af[tup] = func(N.asarray(a[tup], aDtype))#, nthreads=nthreads)
    return af

def sfft(a):
    """
    center shifted full fft
    """
    return N.fft.ifftshift(fft(N.fft.fftshift(a)))

def isfft(af):
    """
    center shifted full ifft
    """
    return N.fft.fftshift(ifft(N.fft.ifftshift(af)))
        
def rfft(a, minFdtype=fftw.RTYPE, nthreads=fftw.ncpu):
    """
    calculate nd fourier transform
    performs real- fft, i.e. the return array has shape with last dim halfed+1

    `a` should be a real array,
      otherwise it gets converted to
      minFdtype
    """
    if a.dtype.type not in fftw.RTYPES:
        a = N.asarray(a, minFdtype)

    return fftw.rfft(a, nthreads=nthreads)
def irfft(af, minCdtype=fftw.CTYPE, nthreads=fftw.ncpu):#normalize=True, minCdtype=fftw.CTYPE, nthreads=fftw.ncpu):
    """
    calculate nd inverse fourier transform
    performs real- ifft, i.e. the input array has shape with last dim halfed+1

    fftw does NOT normalize (divide by product of shape)
    they argue that the normalization can often be combined with other
    operation and thus save a loop through the data

    if normalize is True: the division is done -- and normilized data is returned

    `af` should be a complex array,
      otherwise it gets converted to
      minCdtype
    """
    if af.dtype.type not in fftw.CTYPES:
        af = N.asarray(af, minCdtype)

    return fftw.irfft(af, nthreads=nthreads)

def rfft2d(a, minFdtype=fftw.RTYPE, nthreads=fftw.ncpu):
    """
    calculate (section-wise) 2d fourier transform
    performs real- fft, i.e. the return array has shape with last dim halfed+1

    `a` should be a real array,
      otherwise it gets converted to
      minFdtype
    """
    if a.dtype.type not in fftw.RTYPES:
        aDtype = minFdtype
    else:
        aDtype = a.dtype.type # ensures native byte-order ?

    nx = a.shape[-1]
    if nx % 2:
        raise ValueError("a must be even sized in last dimension")
    s2 = a.shape[:-1]+(nx//2+1,)

    
    if aDtype == N.float32:
        af = N.empty(shape=s2, dtype=N.complex64)
    elif aDtype == N.float64:
        af = N.empty(shape=s2, dtype=N.complex128)
    else:
        raise TypeError("a must be of dtype float32 or float64 (%s given)"%a.dtype) 
    for tup in N.ndindex(a.shape[:-2]):
        af[tup] = fftw.rfft(N.asarray(a[tup], aDtype), nthreads=nthreads)
    return af

def irfft2d(af, preserve=True, minCdtype=fftw.CTYPE, nthreads=fftw.ncpu):#normalize=True, minCdtype=fftw.CTYPE, nthreads=fftw.ncpu):
    """
    calculate (section-wise) 2d inverse fourier transform
    performs real- ifft, i.e. the input array has shape with last dim halfed+1

    the (fftw) implementation of irfft would overwrite the original af array
    to preserve af  when preserve is True - a copy is made first

    fftw does NOT normalize (divide by product of shape)
    they argue that the normalization can often be combined with other
    operation and thus save a loop through the data
    if normalize is True: the division is done -- and normilized data is returned

    `af` should be a complex array,
      otherwise it gets converted to
      minCdtype
    """
    if af.dtype.type not in fftw.CTYPES:
        afDtype = minCdtype
    else:
        afDtype = af.dtype.type # ensures native byte-order ?
    
    shape = af.shape[:-1] + ((af.shape[-1]-1)*2,)

    if   afDtype == N.complex64:
        a = N.empty(shape=shape, dtype=N.float32)
    elif afDtype == N.complex128:
        a = N.empty(shape=shape, dtype=N.float64)
    else:
        raise TypeError("af must be of dtype complex64 or complex128 (%s given)"%af.dtype) 

    for tup in N.ndindex(af.shape[:-2]):
        if preserve :
            myAF = N.array(af[tup], afDtype, copy=1)
        else:
            myAF = N.asarray(af[tup], afDtype)
        a[tup] = fftw.irfft(myAF, nthreads=nthreads)#), normalize=normalize, nthreads=nthreads)
    return a

'''
def fft1d(a, n=None, axis=-1):
    """
    Will return the n point discrete Fourier transform of a. n defaults to the
    length of a. If n is larger than a, then a will be zero-padded to make up
    the difference. If n is smaller than a, the first n items in a will be
    used.

    The packing of the result is "standard": If A = fft(a, n), then A[0]
    contains the zero-frequency term, A[1:n/2+1] contains the
    positive-frequency terms, and A[n/2+1:] contains the negative-frequency
    terms, in order of decreasingly negative frequency. So for an 8-point
    transform, the frequencies of the result are [ 0, 1, 2, 3, 4, -3, -2, -1].

    This is most efficient for n a power of two. This also stores a cache of
    working memory for different sizes of fft's, so you could theoretically
    run into memory problems if you call this too many times with too many
    different n's.

    Seb converts result to single prec.
    """
    return FFT.fft(a, n, axis).astype(N.complex64)

def fft2d(a, s=None, axes=(-2,-1)):
    """
    The 2d fft of a. This is really just fftnd with different default
    behavior.
    
    Seb converts result to single prec.
    """
    return FFT.fft2d(a,s,axes).astype(N.complex64)


def fft(a, s=None, axes=None):
    """
    The n-dimensional fft of a. s is a sequence giving the shape of the input
    an result along the transformed axes, as n for fft. Results are packed
    analogously to fft: the term for zero frequency in all axes is in the
    low-order corner, while the term for the Nyquist frequency in all axes is
    in the middle.

    If neither s nor axes is specified, the transform is taken along all
    axes. If s is specified and axes is not, the last len(s) axes are used.
    If axes are specified and s is not, the input shape along the specified
    axes is used. If s and axes are both specified and are not the same
    length, an exception is raised.

    Seb converts result to single prec.
    """
    return FFT.fftnd(a, s, axes).astype(N.complex64)



def ifft1d(a, n=None, axis=-1):
    """
    Will return the n point inverse discrete Fourier transform of a.  n
    defaults to the length of a. If n is larger than a, then a will be
    zero-padded to make up the difference. If n is smaller than a, then a will
    be truncated to reduce its size.

    The input array is expected to be packed the same way as the output of
    fft, as discussed in its documentation.

    This is the inverse of fft: inverse_fft(fft(a)) == a within numerical
    accuracy.

    This is most efficient for n a power of two. This also stores a cache of
    working memory for different sizes of fft's, so you could theoretically
    run into memory problems if you call this too many times with too many
    different n's.

    Seb converts result to single prec.
    """

    return FFT.inverse_fft(a, n, axis).astype(N.complex64)


def ifft2d(a, s=None, axes=(-2,-1)):
    """
    The inverse of fft2d. This is really just ifft with different
    default behavior.
    
    Seb converts result to single prec.
    """

    return FFT.inverse_fft2d(a,s,axes)

def ifft(a, s=None, axes=None):
    """
    The inverse of fft.

    Seb converts result to single prec.
    """
    
    return FFT.inverse_fftnd(a, s, axes).astype(N.complex64)




def rfft1d(a, n=None, axis=-1):
    """
    Will return the n point discrete Fourier transform of the real valued
    array a. n defaults to the length of a. n is the length of the input, not
    the output.

    The returned array will be the nonnegative frequency terms of the
    Hermite-symmetric, complex transform of the real array. So for an 8-point
    transform, the frequencies in the result are [ 0, 1, 2, 3, 4]. The first
    term will be real, as will the last if n is even. The negative frequency
    terms are not needed because they are the complex conjugates of the
    positive frequency terms. (This is what I mean when I say
    Hermite-symmetric.)

    This is most efficient for n a power of two.

    Seb converts result to single prec.
    """

    return FFT.real_fft(a, n, axis).astype(N.complex64)




def rfft2d(a, s=None, axes=(-2,-1)):
    """
    The 2d fft of the real valued array a. This is really just rfftnd with
    different default behavior.

    Seb converts result to single prec.
    """
    
    return FFT.real_fftnd(a, s, axes).astype(N.complex64)

def rfft(a, s=None, axes=None):
    """
    The n-dimensional discrete Fourier transform of a real array a. A real
    transform as real_fft is performed along the axis specified by the last
    element of axes, then complex transforms as fft are performed along the
    other axes.

    Seb converts result to single prec.
    """
    
    return FFT.real_fftnd(a, s, axes).astype(N.complex64)



def irfft1d(a, n=None, axis=-1):
    """
    Will return the real valued n point inverse discrete Fourier transform of
    a, where a contains the nonnegative frequency terms of a Hermite-symmetric
    sequence. n is the length of the result, not the input. If n is not
    supplied, the default is 2*(len(a)-1). If you want the length of the
    result to be odd, you have to say so.

    If you specify an n such that a must be zero-padded or truncated, the
    extra/removed values will be added/removed at high frequencies. One can
    thus resample a series to m points via Fourier interpolation by: a_resamp
    = inverse_real_fft(real_fft(a), m).

    This is the inverse of real_fft:
    inverse_real_fft(real_fft(a), len(a)) == a
    within numerical accuracy.

    Seb converts result to single prec.
    """

    return FFT.inverse_real_fft(a,n,axis).astype(N.float32)


def irfft2d(a, s=None, axes=(-2,-1)):
    """
    The inverse of rfft2d. This is really just irfft with
    different default behavior.
    """
    
    return FFT.inverse_real_fftnd(a, s, axes).astype(N.float32)

def irfft(a, s=None, axes=None):
    """
    The inverse of rfft. The transform implemented in ifft is
    applied along all axes but the last, then the transform implemented in
    inverse_real_fft is performed along the last axis. As with
    inverse_real_fft, the length of the result along that axis must be
    specified if it is to be odd.

    Seb converts result to single prec.
    """
    
    return FFT.inverse_real_fftnd(a,s,axes).astype(N.float32)
'''



def convolve(a,b, conj=0, killDC=0, minFdtype=N.float32):
    """
    calculate convolution of `a` and `b`
       (using rfft, multiplication, then irfft)
    if  `conj` is true:
       calculate correlation instead ! 
       (after the fft the `bf` is conjucated)

    a and b  have to be same shape

    if `a` or `b` are not dtype of float32 or float64
    they are converted to minFdtype
       unless one of `a` or `b` is float64, then float64 is used
    """
    if a.dtype.type == N.float64 or \
       b.dtype.type == N.float64:
        minFdtype = N.float64

    if a.dtype.type not in (N.float32, N.float64):
        a = N.asarray(a, minFdtype)
    if b.dtype.type not in (N.float32, N.float64):
        b = N.asarray(b, minFdtype)
    

    af = rfft(a)
    bf = rfft(b)

    if killDC:
        af.flat[0] = 0
        bf.flat[0] = 0

    if conj:
        bf = bf.conjugate()

    cf = af * bf

    c = irfft(cf)

    return c




def drawLine(a, p0, p1, val=1., includeLast=True):
    p = N.asarray(p0, N.float)
    p1= N.asarray(p1)
    delta = p1-p
    steppingAxis = delta.argmax()
    iNum  = int(delta[steppingAxis])
    deltaStep = delta /delta[steppingAxis]
    
    for i in range(iNum):
        a[ tuple((p+.5).astype(N.int32)) ] += val
        p += deltaStep
    if includeLast:
        a[ tuple((p+.5).astype(N.int32)) ] += val

def drawHexPattern2d(a, d=20, sizeYX=None, yx0=(0,0), val=1):
    """
    fill (each section 2d of) a with pixel value 'val'
    at the (rounded) pixel-position of a hexagonal grid
    grid size is d
    grid strats at corner pixel yx0
    """
    if sizeYX is None:
        sizeYX = N.array(a.shape, dtype=N.float) - yx0
        
    for i in range(int(float(sizeYX[1])/d)):
        for j in range(int(sizeYX[0]/(3.**.5/2 * d))):
            y = 3**.5/2 * d * j
            x = d*i + d*.5 * (1-(-1)**j)*.5
            yy,xx= int(yx0[0]+y+.5), int(yx0[1]+x+.5)
            a[...,yy,xx] = val


def zzern_r(n,m,r):
    from .useful import fac
    if n==m==0:
        return 1
    rr = 0
    for s in range(n-m+1):
        rr += (-1)**s * fac(2*n-m-s) /               \
             (fac(s)*fac(n-s)*fac(n-m-s)) *   \
             r**(2*(n-s)-m)
    return rr

def zzern_rcos(n,m,r, phi):
    return zzern_r(n,m,r) * N.cos(m*phi)
def zzern_rsin(n,m,r, phi):
    return zzern_r(n,m,r) * N.sin(m*phi)


def zzernikeNMCosArr(shape=defshape, n=3,m=3, crop=1, radius=None, orig=None, dtype=N.float32):
    if radius is None:
        radius = reduce(min, shape) / 2.0
    if crop:
        return radialPhiArr(shape,
                            lambda r,p: N.where(r<=radius,
                                                 zzern_rcos(n,m, r/radius,p),0), orig)
    else:
        return radialPhiArr(shape,
                            lambda r,p: zzern_rcos(n,m, r/radius,p), orig)

def zzernikeNMSinArr(shape=defshape, n=3,m=3, crop=1, radius=None, orig=None, dtype=N.float32):
    if radius is None:
        radius = reduce(min, shape) / 2.0
    if crop:
        return radialPhiArr(shape,
                            lambda r,p: N.where(r<=radius,
                                                 zzern_rsin(n,m, r/radius,p),0), orig)
    else:
        return radialPhiArr(shape,
                            lambda r,p: zzern_rsin(n,m, r/radius,p), orig)

def zzernikeN0Arr(shape=defshape, n=3, crop=1, radius=None, orig=None, dtype=N.float32):
    if radius is None:
        radius = reduce(min, shape) / 2.
    if crop:
        return radialArr(shape,
                         lambda r: N.where(r<=radius,
                                            zzern_r(n,0, r/radius),0), orig)
    else:
        return radialArr(shape,
                         lambda r:    zzern_r(n,0, r/radius), orig)
    

def zzernikeArr(shape=defshape, no=9, crop=1, radius=None, orig=None, dtype=N.float32):

    n = int( N.sqrt(no) )
    
    m = n - (no - n**2) // 2

    if m==0:
        return zzernikeN0Arr(shape, n, crop, radius, orig)
    elif (no - n**2) % 2:
        return zzernikeNMSinArr(shape, n,m, crop, radius, orig)
    else:
        return zzernikeNMCosArr(shape, n,m, crop, radius, orig)




def lowPassGaussFilter(a, sigma=5):
    """
    still something left for TODO:
       nx = s[0] # FIXME HACK
       sigma=1/(2.*N.pi*sigma)*nx    
    """
    s = N.array(a.shape)
    if N.any(s % 2):
        raise ValueError("only shape % 2 == 0 supported")
    s2 = s/2.

    nx = s[0] # FIXME HACK
    sigma=1/(2.*N.pi*sigma)*nx
    g = gaussianArr(tuple(s[:-1]) + (int(s2[-1])+1,),
                    sigma, peakVal=1, orig=0, wrap=(1,)*(a.ndim-1)+(0,))

    af = rfft(a)

    af *= g
    #af[:sy2] *= g[sy2:]
    #af[sy2:] *= g[:sy2]

    return irfft(af)


def mexF2d(a, sigma2d):
    """
    calculate -nd.gaussian_laplace sectionwise, using
    output=None, mode="reflect", cval=0.0

    forcing float32 output
    """
    from scipy.ndimage import gaussian_laplace
    out = zeroArrF(a.shape)

    for tup in N.ndindex(a.shape[:-2]):
        gaussian_laplace(a[tup], sigma2d, output=out[tup], mode="reflect", cval=0.0)
        out[tup] *= -1

    return out



class mockNDarray(object):
    def __init__(self, *arrs):
        def conv(a):
            if hasattr(a,'view'):
                return a.view()   # we use view(), so that we can fix it up
            if hasattr(a,'__len__'):
                return mockNDarray(*a)
            if a is None:
                return mockNDarray()
            raise ValueError("don't know how to mockify %s" %(a,))
        self._arrs = [conv(a) for a in arrs]
        self._mockAxisSet(0)

    def _mockAxisSet(self, i):
        """
        this is the workhorse function, that makes the internal state consistent
        sets:
           self._mockAxis
           self._ndim
           self._shape
        """
        self._mockAxis = i
        if len(self._arrs)==0:
            self._ndim     = 0
            self._shape    = ()
            return
        self._ndim     = 1+max((a.ndim for a in self._arrs))
        self._shape    = [1]*self._ndim

        #fix up shape of sub array so that they all have ndim=self._ndim-1
        #  fill shape by prepending 1s
        #  unless ndim was 0, then set shape to tuple of 0s
        nd1 = self._ndim-1
        for a in self._arrs:
            if a.ndim == nd1:
                continue
            if isinstance(a, mockNDarray):
                if a._ndim ==0:
                    a._ndim= nd1
                    a._shape = (0,)*nd1
            else:
                if a.ndim == 0:
                    a.shape = (0,)*nd1
                else:
                    a.shape = (1,)*(nd1-a.ndim)+a.shape

        # fixup the shape to reflext the "biggest" shape possible, like a "convex hull"
        iSub=0 # equal to i, except for i>_mockAxis: its one less
        for i in range(self._ndim):
            if i == self._mockAxis:
                self._shape[i] = len(self._arrs)
                continue
            for a in self._arrs:
                # OLD: the a.ndim>iSub check here means, that sub arrays may be "less dimensional" then `self` would imply if it was not "mock"
                # OLD:   if a.ndim <= self._ndim and a.ndim>iSub:
                if self._shape[i] < a.shape[iSub]:
                    self._shape[i] = a.shape[iSub]
            iSub+=1
        self._shape = tuple( self._shape )

    def _getshape(self):
        return self._shape
    def _setshape(self, s):
        # minimal "dummy" implementation
        #  useful for functions like U.mean2d, which want to set shape to -1,s[-2],s[-1]
        __setShapeErrMsg = "mockNDarray supports only trivial set_shape functionality"
        foundMinus=False
        if len(self._shape) != len(s):
            raise ValueError(__setShapeErrMsg)
        for i in range(len(self._shape)):
            if s[i] == -1:
                if foundMinus:
                    raise ValueError(__setShapeErrMsg)
                else:
                    foundMinus = True
            elif s[i] != self._shape[i]:
                    raise ValueError(__setShapeErrMsg)

    shape = property( _getshape,_setshape )


    def _getndim(self):
        return self._ndim
    ndim = property( _getndim )

    def _getdtype(self):
        return min((a.dtype for a in self._arrs))
    dtype = property( _getdtype )

    def __len__(self):
        return self._shape[0]

    def __getitem__(self, idx):
        import copy
        if isinstance(idx, int):
            if self._mockAxis == 0:
                return self._arrs[idx]
            else:
                s = copy.copy(self)
                s._arrs = [a[idx] for a in self._arrs]
                s._mockAxisSet( self._mockAxis-1 )
                return s
        elif isinstance(idx, tuple):
            if idx == ():
                return self
            if Ellipsis in idx:
                # expand Ellipsis [...] to make slice-handling easier ....
                dimsGiven = len(idx)-1
                for EllipsisIdx in range(len(idx)):
                    if idx[EllipsisIdx] is Ellipsis:
                        break
                idx = idx[:EllipsisIdx ] + (slice(None),)*(self._ndim-dimsGiven) + idx[EllipsisIdx+1:]

            if len(idx) <= self._mockAxis:
                mockIdx = slice(None)
                idxSkipMock = idx
            else:
                mockIdx = idx[self._mockAxis]
                idxSkipMock = idx[:self._mockAxis] + idx[self._mockAxis+1:]
            

            if isinstance(mockIdx, slice):
                s = copy.copy(self)
                
                s._arrs = [a[idxSkipMock] for a in self._arrs[mockIdx]]
                shiftMockAxisBecauseOfInt = sum((1 for i in idx[:self._mockAxis] if not isinstance(i, slice)))
                s._mockAxisSet( self._mockAxis-shiftMockAxisBecauseOfInt )          
                return s
            elif mockIdx is None:
                s = copy.copy(self)
                s._arrs = [a[None][idxSkipMock] for a in self._arrs]
                s._mockAxisSet( self._mockAxis+1 )
                idxSkipMock = (slice(None),)+idxSkipMock  # adjust idxSkipMock to keep new axis 
                return s[idxSkipMock]
                
            else: # mockIdx is "normal" int - CHECK
                # return non-mock ndarray, (or mockNDarray, if there are nested ones)
                return self._arrs[mockIdx][idxSkipMock]

        elif idx is Ellipsis:
            return self
        elif isinstance(idx, slice):
            #raise RuntimeError, "mockarray: slice indices not implemented yet"
            s = copy.copy(self)

            if self._mockAxis ==0:
                s._arrs = self._arrs[idx]
                #s._shape[0] = len(self._arrs)
            else:
                s._arrs = [a[idx] for a in self._arrs[mockIdx]]
                #s._shape[0] = len(self._arrs[0])
            #shiftMockAxisBecauseOfInt = sum((1 for i in idx[:self._mockAxis] if not isinstance(i, slice)))
            s._mockAxisSet( self._mockAxis )
            return s
        elif idx is None: # N.newaxis:
            s = copy.copy(self)
            s._arrs = [a[None] for a in self._arrs]
            s._mockAxisSet( self._mockAxis+1 )
            return s


        raise IndexError("should not get here .... ") 

    def transpose(self, *axes):
        try:
            axes = axes[0] # convert  transpose(self, axes) to  transpose(self, *axes)
        except:
            pass
        if len(axes) != self._ndim:
            raise ValueError("axes don't match mockarray")

        for newMockAxis in range(self._ndim):
            if axes[newMockAxis] == self._mockAxis:
                break
        else:
            raise ValueError("axes don't contain mockAxis")

        othersAxes = (ax if ax<newMockAxis else ax-1 for ax in axes[:newMockAxis] + axes[newMockAxis+1:])

        othersAxes = tuple(othersAxes)
        import copy
        s = copy.copy(self)
        s._mockAxisSet(newMockAxis)
        #s._shape = tuple(N.array(s._shape)[list(axes)])

        for i,a in enumerate(s._arrs):
            s._arrs[i] = a.transpose( *othersAxes )

        return s

    def view(self):
        from copy import copy
        return copy(self)
