### Here all kinds of fitting
from __future__ import print_function
try:
    from ..Priithon.all import N, U
except ValueError:
    from Priithon.all import N, U
try:
    from . import imgFilters, imgGeo
except ValueError:
    from PriCommon import imgFilters, imgGeo
except ImportError: # python 2
    import imgFilters, imgGeo
#import exceptions

#from packages import logger
#logger = logger.getLogger('imgFit')

class FittingError(Exception): pass#exceptions.Exception): pass

ERROR = [] # Error, message
RAISE = None

def fitFailedAppend(msg, err=FittingError, verbose=None):
    """
    append [err, msg] to global ERROR
    return number of ERROR so far
    """
    global ERROR
    if verbose:
        print(err, msg)
    ERROR.append([err, msg])
    if RAISE:
        raise err(msg)
    return len(ERROR)

def fitFailedClear():
    """
    clear global ERROR
    """
    global ERROR
    ERROR = []

def fitAny(func, data, t, p0):
    """
    func: your function
    data: 1D data
    t:    1D coordinate (same length as data)
    p0:   parameter tuple
    """
    data = N.asarray(data, N.float64)
    t = N.asarray(t, N.float64)
    def f(p):
        return func(p, t) - data

    x0 = p0
    from scipy import optimize
    try:
        ret = optimize.leastsq(f, x0, warning=None)
    except TypeError: # python 2.6
        ret = optimize.leastsq(f, x0)
    return ret

############  Multi-dimensional Gaussian #########################
# (fast enough!!)
################################################

def fitGaussianND(img, zyx, sigma=0.5, window=5, mean_max=None, rot=0):
    """
    img:      can be any dimensions
    zyx:      point of object in the img (same dimension as img)
    sigma:    scaler or [sigmaz, sigmay, sigmax]
    window:   window size for fitting (scaler)
    mean_max: tuple of (mean, max), if already known
    rot:      counter-clockwise, xy-plane (window should be even)

    returns [[mean, peakVal, [z, y,] x, [sigmaz, sigmay,] sigmax], check]
    check is 2 if single answer was found, while 5 if not
    """
    slices = imgGeo.nearbyRegion(img.shape, N.floor(zyx), window)
    inds, LD = rotateIndicesND(slices, dtype=N.float64, rot=rot)
   # inds, LD = indicesFromSlice(slices, dtype=N.float64)
    #slices, inds, LD = _sliceIndLD(window, zyx, img.shape)
    return _fitGaussianND(img[slices], inds, zyx, sigma, mean_max)

def _scalerToSeq(sclOrSeq, ndim):
    """
    convert scaler or sequence to n-dimensional sequence (tuple in default)
    """
    try:
        if len(sclOrSeq) != ndim:
            raise ValueError('dimension does not match')
    except TypeError:
        sclOrSeq = (sclOrSeq, ) * ndim
    return sclOrSeq

def indicesFromSlice(slicelist, dtype=N.float64):
    """
    return inds, LD
    """
    shape = []
    LD = []
    for sl in slicelist:
        if isinstance(sl, slice):
            shape.append(sl.stop - sl.start)
            LD.append(sl.start)
    inds = N.indices(shape, dtype)
    for i, ld in enumerate(LD):
        inds[i] += ld
    return inds, LD

def _fitGaussianND(img, inds, zyx, sigma=0.5, mean_max=None):
    """
    img: already cut out
    """
    ndim = img.ndim
    if mean_max is None:
        mi, ma, me, sd = U.mmms(img)
    else:
        me, ma = mean_max

    try:
        if len(sigma) == ndim:
            sigma = [float(s) for s in sigma]
    except (ValueError, TypeError):
        sigma = [float(sigma) for i in range(ndim)]
    param0 = [me, float(ma-me)] + list(zyx) + sigma
    param0 = N.asarray(param0, N.float64)

    img = img.flatten()
    sidx = 2 + ndim
    def func(p, inds, sidx):
        return yGaussianND(p, inds, sidx) - img

    from scipy import optimize
    inds = [inds[i].flatten().astype(N.float64) for i in range(ndim)]
    if hasattr(optimize, 'least_squares'):
        ret = optimize.least_squares(func, param0, args=(inds, sidx))
        check = ret.status
        if check == -1:
            check = 5
        ret = ret.x
    else:
        try:
            ret, check = optimize.leastsq(func, param0,
                                          args=(inds,sidx), warning=None)
        except TypeError: # python2.6
            ret, check = optimize.leastsq(func, param0,
                                          args=(inds,sidx))
    #ret[2:5] -= 0.5
  #  ret[2:5] += 0.5 # use pixel center
    ret[sidx:] = N.abs(ret[sidx:])
    return ret, check

def yGaussianND(param, inds, sidx):
    """
    param: (mean, max - mean, z, y, x, sigmaz, sigmay, sigmax)
    ind:   coordinate as N.indices (float32)
    sidx:  idx of param where sigma starts (2 + ndim)
    """
    s = 2. * param[sidx:] * param[sidx:] # sigma
    zyx = param[2:sidx] #- 0.5 # use pixel center
    DST = N.zeros(inds[0].shape, inds[0].dtype.type)
    for i in range(sidx - 2):
        IND = zyx[i] - inds[i]
        DST -= (IND * IND) / s[i]

    return param[0] + param[1] * N.exp(DST)

### Skewed gaussian #######

def fitSkew1D(img, ts=None, sigma=0.5, exp=0):
    """
    img: 1D array containg one skewd gaussian peak
    """
    mi, ma, me, sd = U.mmms(img)
    ma, _1, _2, t = U.findMax(img)
    if ts is not None:
        t = ts[t]
        img = list(zip(ts, img))

    return U.fitAny(ySkew, (mi, ma-mi, t, sigma, exp), img, warning=None)

def ySkew(param, ts):
    """
    param: (mean, max - mean, t, sigma, exp)
    ind:   coordinate as N.indices (float32)
    sidx:  idx of param where sigma starts (2 + ndim)
    """
    s = 2. * (param[3]**2) # sigma
    ss = ts ** param[4] # exponential
    ss *= s # sigma skewed by exp
    t = param[2] - 0.5 # use pixel center
    IND = t - ts
    DST = -(IND * IND) / ss

    return param[0] + param[1] * N.exp(DST)

### belows are old ##################

def fitGaussian2D(img, y, x, sigma=[2.,2.], window=5, mean_max=None):
    """
    y, x:     point of object in the img
    sigma:    scaler or [sigmay, sigmax]
    window:   window size for fitting
    mean_max: tuple of (mean, max), if already known

    returns [[mean, peakVal, y, x, sigma], check]
    check is 2 if single answer was found, while 5 if not
    """
    #yi, xi, LD = _indLD(window, y, x)
    sl = imgGeo.nearbyRegion(img.shape, N.floor((y,x)), window)
    inds, LD = indicesFromSlice(sl, dtype=N.float64)
  #  sl, inds, LD = _sliceIndLD(window, (y,x), img.shape)
    yi, xi = inds

    #return _fitGaussian2D(img[yi, xi], yi, xi, y, x, sigma, mean_max)
    return _fitGaussian2D(img[sl], yi, xi, y, x, sigma, mean_max)


def _indLD(win, y, x):
    """
    return yi, xi, LD
    """
    try:
        len(win)
        yi, xi = N.indices(int(win))
    except TypeError:
        yi, xi = N.indices((int(win), int(win)))
    yx = N.asarray((y, x))
    LD = yx - win/2. + 0.5 # use pixel center
    yi += LD[0]
    xi += LD[1]
    return yi, xi, LD

def _fitGaussian2D(img, indy, indx, y, x, sigma=[2.,2.], mean_max=None):
    """
    img: already cut out with indy, indx
    """
    if mean_max is None:
        mi, ma, me, sd = U.mmms(img)
        #ma = img[y,x]
    else:
        me, ma = mean_max

    try:
        sigma, sigma2 = sigma
        param0 = (me, float(ma-me), y, x, float(sigma), float(sigma2))
       # func = _gaussian2D_ellipse
    except (ValueError, TypeError):
        try: 
            len(sigma)
            sigma = [0]
        except TypeError:
            pass
        param0 = (me, float(ma-me), y, x, float(sigma))
        #func = _gaussian2D

    img = img.flatten()
    def func(p, indy, indx):
        return yGaussian2D(p, indy, indx) - img

    from scipy import optimize
    ret, check = optimize.leastsq(func, param0,
                           args=(indy.flatten(), indx.flatten()), warning=None)
    ret[2:4] += 0.5 # use pixel center
    ret[4:] = N.abs(ret[4:])
    return ret, check

def yGaussian1D(param, t=0):
    """
    param:  (mean, max - mean, y, sigma)
           or (mean, max - mean, y, sigma, sigmaSkew, sgimaSkew2)
           latter may be sensitive to initial guess
    """
    yyi = param[2]-t
    dist = -(yyi)*(yyi)
    
    if len(param) == 4:
        c = 2.
    elif len(param) == 6:
        c = param[4]*t+param[5]
    else:
        raise ValueError('param must be tuple of length 4 or 6')
    sigma  = (param[3]*param[3]) * c
    return param[0] + param[1] * N.exp(dist /sigma)



def _gaussian2D(param, indy, indx, vals):
    """
    param: (mean, max - mean, y, x, sigma)
    """
    yyi = param[2]-indy
    xxi = param[3]-indx
    dist = -(yyi)*(yyi) -(xxi)*(xxi)

    sigma  = 2. * (param[4]*param[4])
    return param[0] + param[1] * N.exp(dist /sigma) - vals

def _gaussian2D_ellipse(param, indy, indx, vals):
    """
    param: (mean, max - mean, y, x, sigmay, sigmax)
    """
    sy = 2. * (param[4]*param[4])
    sx = 2. * (param[5]*param[5])
    yyi = param[2]-indy
    xxi = param[3]-indx
    dist = -(yyi)*(yyi)/sy -(xxi)*(xxi)/sx

    return param[0] + param[1] * N.exp(dist) - vals

def yGaussian2D(param, indy, indx):
    """
    param:      (mean, max - mean, y, x, sigma[y], [sigmax])
    indy, indx: coordinate of y and x as N.indices
    """
    sy = 2. * (param[4]*param[4])
    if len(param) == 6:
        sx = 2. * (param[5]*param[5])
    else:
        sx = sy
    yyi = param[2]-indy
    xxi = param[3]-indx # int32 -> float64
 #   print yyi.dtype.type
    dist = -(yyi)*(yyi)/sy -(xxi)*(xxi)/sx
    return param[0] + param[1] * N.exp(dist)


####    depth dependence ##############

def yPoly(parms=(1,1,1,1,0,0), t=0):
    '''
    t can be a scalar or a vector
    returns y value(s) of a polygon model
    parms:
      baseline, first-order coeff, 2nd, ...
    '''
    r = 0.0
    for i in range(0, len(parms), 2):
        c = parms[i] * t + parms[i+1]
        r = r + c*N.power(t, i)
    return r

def psf__wPSF_yPolyInv(t, *parm):
    """
    abs()
    """
    if len(parm) == 1:
        parm = parm[0]
    r = psf__wPSF_yPolyInv_bare(t, parm)
    return N.abs(r)

def psf__wPSF_yPolyInv_bare(t, *parm):
    """
    before abs
    """
    if len(parm) == 1:
        parm = parm[0]
    r = 0.0
    for i in range(len(parm)):
        r = r + parm[i]*N.power(t, i)
    return r

def psf__wPSF(parm, t):
    """
    parm: s0, c, d, A, B
    example  (72, 125, 246, 1, 1)
    """
    s0, c, d, A, B = parm
    com = (t - c) / d
    sq = 1 + N.power(com, 2) + A * N.power(com, 3) + B * N.power(com, 4)
    return s0 * N.sqrt(sq)

def psf__wPSF_fromSigma(t, parm):
    """
    t: now this is sigma that you got
    parm: s0, c, d, A, B (use parm form psf__wPSF fit)
    """
    s0, c, d, A, B = parm
    com = (t - c) / d
    sq = 1 + N.power(com, 2) + A * N.power(com, 3) + B * N.power(com, 4)
    return s0 * N.sqrt( 1 + sq)

#### Rotated gaussian #############################
def fitGaussian2DR(img, y, x, sigma=[2,2], window=5, rot=0, searchRot=None):
    """
    img:    2D
    y, x:   approximate peak pos
    sigma:  [y,x]
    window: window for gaussian fit
    rot:    scaler (counter clockwise)
    searchRot: examine rotation angle

    works slower

    return: [mean, max - mean, y, x, sigmay, sigmax, [rot]]
    """

    yi, xi, LD = _indLD(window, y, x)
    img = img[yi,xi]
    return _fitGaussian2DR(img, LD, y, x, sigma, None, window, rot, searchRot)

def _fitGaussian2DR(img, LD, y, x, sigma=[2.,2.], mean_max=None, window=5, rot=0, searchRot=None):
    """
    img: already cut out with indy, indx
    """
    if mean_max is None:
        mi, ma, me, sd = U.mmms(img)
        #ma = img[y,x]
    else:
        me, ma = mean_max

    if searchRot:
        param0 = (me, float(ma-me), y, x, float(sigma[0]), float(sigma[1]), rot)
    else:
        param0 = (me, float(ma-me), y, x, float(sigma[0]), float(sigma[1]))

    img = img.flatten()
    def func(p, shape, LD, rot):
        return yGaussian2DR(p, shape, LD, rot).flatten() - img

    from scipy import optimize
    ret, check = optimize.leastsq(func, param0,
                           args=((window,window), LD, rot), warning=None)
    if searchRot and ret[-1] < 0:
        ret[-1] += 90
    ret[4:] = N.abs(ret[4:])
    return ret, check

def yGaussian2DR(param, shape, LD, rot=0):
    """
    param: (mean, max - mean, y, x, sigma[y], [sigmax], [rot])
    shape: (y,x)
    rot:   scaler (counter clockwise) if len(param) < 7
    LD:    left down coordinate (offset)
    """
    if len(param) == 7:
        rot = parm[-1]
    sy = 2. * (param[4]*param[4])
    sx = 2. * (param[5]*param[5])
  #  import imgFilters
    yx = N.subtract(param[2:4], LD)
#    ll.append(yx)
    yyi, xxi = rotateIndices2D(shape, rot, yx) # return float64

    dist = -(yyi)*(yyi)/sy -(xxi)*(xxi)/sx
    return param[0] + param[1] * N.exp(dist)

INDS_DIC = {}

def rotateIndicesND(slicelist, dtype=N.float64, rot=0, mode=2, store_shape=False):
    """
    slicelist: even shape works much better than odd shape
    rot:       counter-clockwise, xy-plane
    mode:      testing different ways of doing, (1 or 2 and the same result)

    return inds, LD
    """
    global INDS_DIC
    shape = []
    LD = []
    
    for sl in slicelist:
        if isinstance(sl, slice):
            shape.append(sl.stop - sl.start)
            LD.append(sl.start)

    shapeTuple = tuple(shape+[rot])
    if shapeTuple in INDS_DIC:
        inds = INDS_DIC[shapeTuple]
    else:
        shape = N.array(shape)
        ndim = len(shape)
        odd_even = shape % 2

        s2 = N.ceil(shape * (2**0.5))

        if mode == 1: # everything is even
            s2 = N.where(s2 % 2, s2 + 1, s2)
        elif mode == 2: # even & even or odd & odd
            for d, s in enumerate(shape):
                if (s % 2 and not s2[d] % 2) or (not s % 2 and s2[d] % 2):
                    s2[d] += 1
        cent = s2 / 2.
        dif = (s2 - shape) / 2.
        dm = dif % 1
       # print s2, cent, dif, dm
        slc = [Ellipsis] + [slice(int(d), int(d)+int(shape[i])) for i, d in enumerate(dif)]
        # This slice is float which shift array when cutting out!!

        s2 = tuple([int(ss) for ss in s2]) # numpy array cannot use used for slice
        inds = N.indices(s2, N.float32)
        ind_shape = inds.shape
        nz = N.product(ind_shape[:-2])
        nsec = nz / float(ndim)
        if ndim > 2:
            inds = N.reshape(inds, (nz,)+ind_shape[-2:])
        irs = N.empty_like(inds)
        for d, ind in enumerate(inds):
            idx = int(d//nsec)
            c = cent[idx]
            if rot and inds.ndim > 2:
                U.trans2d(ind - c, irs[d], (0,0,rot,1,0,1))
                irs[d] += c - dif[idx]
            else:
                irs[d] = ind - dif[idx]

        if len(ind_shape) > 2:
            irs = N.reshape(irs, ind_shape)

        irs = irs[tuple(slc)]
        if mode == 1 and N.sometrue(dm):
            inds = N.empty_like(irs)
           # print 'translate', dm
            for d, ind in enumerate(irs):
                U.trans2d(ind, inds[d], (-dm[1], -dm[0], 0, 1, 0, 1))
        else:
            inds = irs
        if store_shape:
            INDS_DIC[shapeTuple] = inds

    r_inds = N.empty_like(inds)
    for d, ld in enumerate(LD):
        r_inds[d] = inds[d] + ld

    return r_inds, LD



def rotateIndices2D(shape, rot, orig=None, dtype=N.float64):
    """
    shape: 2D
    rot:   anti-clockwise
    orig:  (y, x)

    return: yi, xi
    """
    # FIX ME Rot is something wrong!! 081027

    shape = N.asarray(shape, N.int)
    
    if orig is None:
        y, x = shape / 2.
    else:
        y, x = orig

    if not rot:
        yi,xi = N.indices(shape, dtype=N.float64)
        yi -= y - 0.5 # remove pix center
        xi -= x - 0.5
        return yi,xi

    # twice as large window
   # mo = N.abs(N.mod(shape, 2) + [-1,-1])
    s2 = shape * 2 #+ mo  # always odd for even shape, even for odd shape

    yi, xi = N.indices(s2, dtype=N.float32)

    mm = N.ceil(shape / 2.)#(s2 -1 - shape)//2 # offset always int
    yi -= mm[0]
    xi -= mm[1]

    pxc = imgGeo.RotateXY((0.5,0.5), rot) # remove pix center
    yi += pxc[0]
    xi += pxc[1]

    y0, x0 = shape / 2. #N.ceil(shape / 2) # img center
    yc = y0 - y # delta rotation center
    xc = x0 - x

    yi = U.trans2d(yi, None, (xc,yc,rot,1,0,1))
    xi = U.trans2d(xi, None, (xc,yc,rot,1,0,1))
    yi = U.trans2d(yi, None, (-xc,-yc,0,1,0,1))
    xi = U.trans2d(xi, None, (-xc,-yc,0,1,0,1))

    yi = yi.astype(dtype)
    xi = xi.astype(dtype)

    yi -= y
    xi -= x

    yi = imgFilters.cutOutCenter(yi, shape)
    xi = imgFilters.cutOutCenter(xi, shape)
    return yi, xi

def rotateIndices2DNew(shape, rot, orig=None, dtype=N.float64):
    """
    shape: 2D
    rot:   anti-clockwise
    orig:  (y, x)

    return: yi, xi
    """
    # FIX ME Rot is something wrong!! 081027

    shape = N.asarray(shape, N.int)
    
    if orig is None:
        y, x = shape / 2.
    else:
        y, x = orig

    print(y,x)
    if not rot:
        yi,xi = N.indices(shape, dtype=N.float64)
        yi -= y - 0.5 # remove pix center
        xi -= x - 0.5
        return yi,xi

    # twice as large window
   # mo = N.abs(N.mod(shape, 2) + [-1,-1])
    s2 = shape * 2 #+ mo  # always odd for even shape, even for odd shape

    yi, xi = N.indices(s2, dtype=N.float32)

    mm = N.ceil(shape / 2.)#(s2 -1 - shape)//2 # offset always int
    yi -= mm[0]
    xi -= mm[1]

    pxc = imgGeo.RotateXY((0.5,0.5), rot) # remove pix center
    yi += pxc[0]
    xi += pxc[1]

    y0, x0 = shape / 2. #N.ceil(shape / 2) # img center
    yc = y0 - y # delta rotation center
    xc = x0 - x

    yi = U.trans2d(yi, None, (xc,yc,rot,1,0,1))
    xi = U.trans2d(xi, None, (xc,yc,rot,1,0,1))
    yi = U.trans2d(yi, None, (-xc,-yc,0,1,0,1))
    xi = U.trans2d(xi, None, (-xc,-yc,0,1,0,1))

    yi = yi.astype(dtype)
    xi = xi.astype(dtype)

    yi -= y
    xi -= x

    yi = imgFilters.cutOutCenter(yi, shape)
    xi = imgFilters.cutOutCenter(xi, shape)
    return yi, xi

def yExpProb(rhamda=1, t=0):
    t = N.asarray(t)
    return rhamda * N.exp(-rhamda * t)

def yExpDecay(rhamda=1, t=0, n0=100):
    """
    rhamda: paramter
    n0:     the first value of the data
    """
    tt = N.asarray(t)
    try:
        if tt[0]:
            tt = tt.copy()
            tt -= tt[0]
    except TypeError:
        pass
    return n0 * N.exp(-rhamda * tt)

def fitExpDecay(data, t, p0=1):
    """
    return rhamda, mean_lifetime, half_life, check
    """
    data = N.asarray(data, N.float64)
    t = N.asarray(t, N.float64)

    def f(p, n0):
        return yExpDecay(p, t, n0) - data

    x0 = p0
    from scipy import optimize
    rhamda, check = optimize.leastsq(f, x0, args=(data[0],))
    if check in [1,2,3,4]:
        mean_lifetime = 1./rhamda + t[0]
        half_life = N.log(2.) * mean_lifetime
    else:
        mean_lifetime=half_life=0
    return rhamda, mean_lifetime, half_life, check

def yCos(parm, r=0):
    """
    parm: (amp,freq,phase,mean)
    amp * N.sin(freq*r + phase(deg)) + mean
    r:    degree (not radian!!)
    """
    a, b, c, d = parm
    r = U.deg2rad(r)
    c = U.deg2rad(c)
    #return  a * N.cos(b*r + c) + d
    return a * N.cos(b*(r - c)) + d

def rot2D(img2D, yx, sigma, rlist, mean_max=None, win=11):
    y, x = yx
    yi, xi, LD = _indLD(win, y, x)
    imgP = img2D[yi,xi]
    if mean_max is None:
        mi, ma, me, sd = U.mmms(imgP)
    else:
        me, ma = mean_max

    yy = []
    for r in rlist:
        ret, check = _fitGaussian2DR(imgP, LD, y, x, sigma, [me,ma], win, r)
        syx = ret[4] / ret[5] # width y / x
        yy.append(syx)
    return yy

def rotND(img, zyx, sigma, rlist, mean_max=None, win=10):
   # y, x = yx
   # yi, xi, LD = _indLD(win, y, x)
    slices = imgGeo.nearbyRegion(img.shape, zyx, win)
    imgP = img[slices]
    if mean_max is None:
        mi, ma, me, sd = U.mmms(imgP)
    else:
        me, ma = mean_max

    yy = []
    for r in rlist:
        ret, check = fitGaussianND(img, zyx, sigma, win, [me, ma], r)#_fitGaussian2DR(imgP, LD, y, x, sigma, [me,ma], win, r)
        syx = ret[4] / ret[5] # width y / x
        yy.append(syx)
    return yy

def airy1D(x, amp=1):
    from scipy import special
    bessel = special.j1(x)
    return amp * (2. * bessel / x) ** 2
