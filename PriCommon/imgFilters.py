#!/usr/bin/env python

from Priithon.all import N, U, Y, F, Mrc
from scipy import optimize
import mrcIO, imgFit
import os
try:
    from packages import Eext
except:
    pass

# basic contrast operations

def arr_invert(arr):
    canvas = N.empty_like(arr)
    canvas[:] = U.max(arr)
    return canvas - arr

def arr_log(arr):
    logArr = N.log(arr)
    return N.where(logArr < 0, 0, logArr)

def arr_normalize(a, normalize_with='intens'):
    """
    normalize_with: intens or std
    """
    choices = ('intens', 'std')
    mi, ma, me, sd = U.mmms(a)
    if normalize_with == choices[0]:
        a = (a-mi) / (ma-mi)
    elif normalize_with == choices[1]:
        a = (a - me) / sd
    else:
        raise ValueError, 'normalize only with %s' % choices
    return a

def arr_histStretch(img, imgMin=None, imgMax=None, scaleMax=None):
    """
    scaleMax = None: use maximum possible for the dtype
    """
    if imgMin is None:
        imgMin = img.min()
    if imgMax is None:
        imgMax = img.max()
    if scaleMax is None:
        img = N.asarray(img)
        scaleMax = 1 << (img.nbytes // img.size) * 8
        scaleMax -= 1

    img = img - imgMin#img.min()
    ratio = float(scaleMax) / imgMax#img.max()

    return N.asarray(ratio * img, img.dtype.type)

def arr_edgeFilter(img, sigma=1.5):
    """
    average-deviation with a gaussian prefilter
    img must be in an even shape
    """
    if sigma:
        g = gaussianArrND(img.shape, sigma)
        g = F.shift(g)
        img = F.convolve(img.astype(N.float32), g)
    gr = N.gradient(img.astype(N.float32))
    ff = N.sum(N.power(gr, 2), 0)
    return ff 


        

# cross-correlation

def Xcorr(a, b, highpassSigma=2.5, wiener=0.2, cutoffFreq=3,
forceSecondPeak=None, acceptOrigin=True, maskSigmaFact=1., removeY=None, removeX=None, ret=None, normalize=True, gFit=True, lap=None, win=11):
    """
    returns (y,x), image
    if ret is True, returns [v, yx, image]

    to get yx cordinate of the image,
    yx += N.divide(picture.shape, 2)

    a, b:            2D array
    highpassSigma:   sigma value used for highpass pre-filter
    wiener:          wiener value used for highpass pre-filter
    cutoffFreq:      kill lowest frequency component from 0 to this level
    forceSecondPeak: If input is n>0 (True is 1), pick up n-th peak
    acceptOrigin:    If None, result at origin is rejected, look for the next peak
    maskSigmaFact:   Modifier to remove previous peak to look for another peak
    removeYX:        Rremove given number of pixel high intensity lines of the Xcorr
                     Y: Vertical, X: Horizontal
    normalize:       intensity normalized
    gFit:            peak is fitted to 2D gaussian array, if None use center of mass
    win:             window for gFit

    if b is a + (y,x) then, answer is (-y,-x)
    """
    shapeA = N.asarray(a.shape)
    shapeB = N.asarray(b.shape)
    shapeM = N.max([shapeA, shapeB], axis=0)
    shapeM = N.where(shapeM % 2, shapeM+1, shapeM)
    center = shapeM / 2.

    arrs = [a,b]
    arrsS = ['a','b']
    arrsF = []
    for i, arr in enumerate(arrs):
        if arr.dtype not in [N.float32, N.float64]:
            arr = N.asarray(arr, N.float32)
        # this convolution has to be done beforehand to remove 2 pixels at the edge
        if lap == 'nothing':
            pass
        elif lap:
            arr = arr_Laplace(arr, mask=2)
        else:
            arr = arr_sorbel(arr, mask=1)
    
        if N.sometrue(shapeA < shapeM):
            arr = paddingMed(arr, shapeM)

        if normalize:
            mi, ma, me, sd = U.mmms(arr)
            arr = (arr - me) / sd
    
        if i ==1:
            arr = F.shift(arr)
        af = F.rfft(arr)

        af = highPassF(af, highpassSigma, wiener, cutoffFreq)
        arrsF.append(af)

    # start cross correlation
    af, bf = arrsF
    bf = bf.conjugate()
    cf = af * bf

    # go back to space domain
    c = F.irfft(cf)
  #  c = _changeOrigin(cr)

    # removing lines
    if removeX:
        yi, xi = N.indices((removeX, shapeM[-1]))#sx))
        yi += center[-2] - removeX/2.#sy/2 - removeX/2
        c[yi, xi] = 0
    if removeY:
        yi, xi = N.indices((shapeM[-2], removeY))#sy, removeY))
        xi += center[-1] - removeY/2.#sx/2 - removeY/2
        c[yi, xi] = 0

    # find the first peak
    if gFit:
        v, yx, s = findMaxWithGFit(c, win=win)#, window=win, gFit=gFit)
        if v == 0:
            v, yx, s = findMaxWithGFit(c, win=win+2)#, window=win+2, gFit=gFit)
            if v == 0:
                v = U.findMax(c)[0]
        yx = N.add(yx, 0.5)
        #yx += 0.5
    else:
        vzyx = U.findMax(c)
        v = vzyx[0]
        yx = vzyx[-2:]
        s = 2.5

    yx -= center

    if N.alltrue(N.abs(yx) < 1.0) and not acceptOrigin:
        forceSecondPeak = True

    # forceSecondPeak:
    if not forceSecondPeak:
        forceSecondPeak = 0
    for i in range(int(forceSecondPeak)):
        print '%i peak was removed' % (i+1) #, sigma: %.2f' % (i+1, s)
        yx += center
        g = gaussianArr2D(c.shape, sigma=s/maskSigmaFact, peakVal=v, orig=yx)
        c = c - g
        #c = mask_gaussian(c, yx[0], yx[1], v, s)
        if gFit:
            v, yx, s = findMaxWithGFit(c, win=win)#, window=win, gFit=gFit)
            if v == 0:
                v, yx, s = findMaxWithGFit(c, win=win+2)#, window=win+2, gFit=gFit)
                if v == 0:
                    v = U.findMax(c)[0]
            yx -= (center - 0.5)
        else:
            vzyx = U.findMax(c)
            v = vzyx[0]

    if not gFit:
        yx = centerOfMass(c, vzyx[-2:]) - center
    if lap is not 'nothing':
        c = paddingValue(c, shapeM+2)

    if ret == 2:
        return yx, af, bf.conjugate()
    elif ret:
        return v, yx, c
    else:
        return yx, c

_G = None
_G_SHAPE = None

def highPassF(af, highpassSigma=2.5, wiener=0.2, cutoffFreq=3):
    """
    fourie space operations
    af: array after rfft
    half_nyx: half shape required for highpass filter
    highpassSigma: highpass filter, if 0, highpass is not done
    wiener: wiener coefficient for highpass filte
    cutoffFreq: band-pass around origin

    return: array BEFORE irfft

    WARNING: af will be changed, so use copy() if necessary
    """
    global _G, _G_SHAPE
    if highpassSigma:
       # if half_nyx is None:
        ny, nx = af.shape
        sy2 = ny / 2.
        sx2 = nx - 1
        shape = (sy2*2,sx2+1)
        if _G is not None and N.alltrue(_G_SHAPE == shape):
            g = _G
        else:
            g = gaussianArr2D(shape, highpassSigma, peakVal=1, orig=(sy2,0))
            _G = g
            _G_SHAPE = N.asarray(shape)
        g += wiener
        af[:sy2] /= g[sy2:]
        af[sy2:] /= g[:sy2]

    # kill DC
    af.flat[0] = 0
    # kill lowest freq
    af[0:cutoffFreq] = 0
    af[:,0:cutoffFreq] = 0
    
    return af

_F = None
def fourierFilterF(af, func='gaussian', radius=1, operation='+', kwd={}, wiener=0.2, copy=True):
    """
    fourie space operations
    af: array after rfft
    func: string name of a function name in F module or function (the first argument must be shape)
    radius: radius or the 2nd argument of the func
    operation: +, -, *, / etc...
    kwd: will be passed to the func
    wiener: wiener coefficient
    copy: make a copy, otherwise, af will be changed

    return: array BEFORE irfft

    WARNING: af will be changed, so use copy() if necessary
    """
    global _F
    shape = af.shape
    sy2 = shape[-2] / 2.
    if copy:
        af = af.copy()

    kwd['orig'] = (sy2,0)
    if type(func) in [type(''), type(u'')]:
        if func.startswith('g'):
            g = gaussianArr2D(shape, radius, peakVal=1, **kwd)
        else:
            if func[-3:] != 'Arr':
                func += 'Arr'
            try:
                exec('g = F.%s(shape, radius, **kwd)' % func)
            except:
                raise ValueError, '%s is not recognized' % func
    else:
        g = func(shape, radius, **kwd)

    g += wiener
    _F = g
    exec('af[:sy2] %s= g[sy2:]' % operation)
    exec('af[sy2:] %s= g[:sy2]' % operation)
    
    return af


## array genometric

def cutOutCenter(arr, windowSize, sectWise=None, interpolate=True):
    """
    windowSize:  scalar (in pixel or as percent < 1.) or ((z,)y,x)
    sectWise:    conern only XY of windowSize
    """
    shape = N.array(arr.shape)
    center = shape / 2.
    return pointsCutOutND(arr, [center], windowSize, sectWise, interpolate)[0]

def pointsCutOutND(arr, posList, windowSize=100, sectWise=None, interpolate=True):
    """
    array:       nd array
    posList:     ([(z,)y,x]...)
    windowSize:  scalar (in pixel or as percent < 1.) or ((z,)y,x)
                 if arr.ndim > 2, and len(windowSize) == 2, then
                 cut out section-wise (higher dimensions stay the same)
    sectWise:    conern only XY of windowSize (higher dimensions stay the same)
    interpolate: shift array by subpixel interpolation to adjust center

    return:      list of array centered at each pos in posList
    """
    shape = N.array(arr.shape)
    center = shape / 2.
    # prepare N-dimensional window size
    try:
        len(windowSize) # seq
        if sectWise:
            windowSize = windowSize[-2:]
        if len(windowSize) != arr.ndim:
            dim = len(windowSize)
            windowSize = tuple(shape[:-dim]) + tuple(windowSize)
    except TypeError: # scaler
        if windowSize < 1 and windowSize > 0: # percentage
            w = shape * windowSize
            if sectWise:
                w[:-2] = shape[:-2]
            windowSize = w.astype(N.uint16)
        else:
            windowSize = N.where(shape >= windowSize, windowSize, shape)
            if sectWise:
                windowSize = arr.shape[:-2] + windowSize[-2:]
    windowSize = N.asarray(windowSize)

    # cutout individual position
    arrList=[]
    for pos in posList:
        # prepare N-dimensional coordinate
        n = len(pos)
        if n != len(windowSize):
            temp = center.copy()
            center[-n:] = pos
            pos = center
        
        # calculate idx
        ori = pos - (windowSize / 2.) # float value
        oidx = N.ceil(ori) # idx
        subpxl = oidx - ori # subpixel mod
        if interpolate and N.sometrue(subpxl): # comit to make shift
            SHIFT = 1
        else:
            SHIFT = 0

        # prepare slice
        # when comitted to make shift, first cut out window+1,
        # then make subpixle shift, and then cutout 1 edge
        slc = [Ellipsis] # Ellipsis is unnecessary, just in case...
        slc_edge = [slice(1,-1,None)] * arr.ndim
        for d in range(arr.ndim):
            start = oidx[d] - SHIFT
            if start < 0: 
                start = 0
                slc_edge[d] = slice(0, slc_edge[d].stop, None)
            stop = oidx[d] + windowSize[d] + SHIFT
            if stop > shape[d]: 
                stop = shape[d]
                slc_edge[d] = slice(slc_edge[d].start, shape[d], None)
            slc += [slice(int(start), int(stop), None)]

        # cutout, shift and cutout
        try:
            canvas = arr[slc]
            if SHIFT:
                canvas = U.nd.shift(canvas, subpxl)
                canvas = canvas[slc_edge]
            check = 1
        except IndexError:
            print 'position ', pos, ' was skipped'
            check = 0
            raise
        if check:
            arrList += [N.ascontiguousarray(canvas)]

    return arrList

def paddingValue(img, shape, value=0, shift=None, smooth=0, interpolate=True):
    """
    shape:       in the same dimension as img
    value:       value in padded region, can be scaler or array with the shape
    shift:       scaler or in the same dimension as img and shape (default 0)
    smooth:      scaler value to smoothen border (here value must be scaler)
    interpolate: shift array by subpixel interpolation to adjust center

    return:      padded array with shape
    """
    # create buffer
    dtype = img.dtype.type
    canvas = N.empty(shape, dtype)
    canvas[:] = value

    # calculate position
    shape = N.array(shape)
    shapeS = img.shape
    center = N.divide(shape, 2)
    if shift is None:
        shift = 0#[0] * len(shapeS)
    shapeL = shape#N.add(shapeS, center+shift)
    start, stop = (shapeL - shapeS)/2., (shapeL + shapeS)/2.
    slc = [slice(start[d], stop[d], None) for d in range(img.ndim)]
    #print slc, shapeS, shapeL

    # shift if necessary
    if interpolate:
        subpx_shift = start % 1 # should be 0.5 or 0
        if N.sometrue(subpx_shift):
            img = U.nd.shift(img, subpx_shift)
    # padding
    canvas[slc] = img
    if smooth:
        canvas = _smoothBorder(canvas, start, stop, smooth, value)
    canvas = N.ascontiguousarray(canvas)
    #print shapeS, shapeL, slc
    return canvas

def _smoothBorder(arr, start, stop, smooth, value):
    """
    start, stop: [z,y,x]
    """
    # prepare coordinates
    shape = N.array(arr.shape)
    start = N.ceil(start).astype(N.int16)
    stop = N.ceil(stop).astype(N.int16)
    smooth_start = start - smooth
    smooth_stop = stop + smooth
    smooth_start = N.where(smooth_start < 0, 0, smooth_start)
    smooth_stop = N.where(smooth_stop > shape, shape, smooth_stop)
    #print smooth_start, smooth_stop

    import copy
    sliceTemplate = [slice(None,None,None)] * arr.ndim
    shapeTemplate = list(shape)
    for d in range(arr.ndim):
        smooth_shape = shapeTemplate[:d] + shapeTemplate[d+1:]

        # make an array containing the edge value
        edges = N.empty([2] + smooth_shape, N.float32)
        # start side
        slc = copy.copy(sliceTemplate)
        slc[d] = slice(start[d], start[d]+1, None)
        edges[0] = arr[slc].reshape(smooth_shape)
        # stop side
        slc = copy.copy(sliceTemplate)
        slc[d] = slice(stop[d]-1, stop[d], None)
        edges[1] = arr[slc].reshape(smooth_shape)

        edges = (edges - value) / float(smooth + 1) # this value can be array??

        # both side
        for s, side in enumerate([start, stop]):
            if s == 0:
                rs = range(smooth_start[d], start[d])
                rs.sort(reverse=True)
            elif s == 1:
                rs = range(stop[d], smooth_stop[d])
            # smoothing
            for f,i in enumerate(rs):
                slc = copy.copy(sliceTemplate)
                slc[d] = slice(i,i+1,None)
                edgeArr = edges[s].reshape(arr[slc].shape)
                #arr[slc] += edgeArr * (smooth - f) 
                arr[slc] = arr[slc] + edgeArr * (smooth - f) # casting rule

    arr = N.ascontiguousarray(arr)
    return arr

def paddingFourier(arr, shape, value=0, interpolate=True):
    """
    arr:         assuming origin at 0, rfft product (half x size), up to 3D
    shape:       target shape
    value:       the value to fill in empty part 
    interpolate: shift by interpolation if necessary

    return array with target shape
    """
    # prepare buffer
    dtype = arr.dtype.type
    canvas = N.empty(shape, dtype)
    canvas[:] = value
    
    # calc and shift
    shapeS = N.array(arr.shape)
    shapeL = N.asarray(shape)
    halfS = shapeS / 2.
    subpx_shift = halfS % 1
    if interpolate and N.sometrue(subpx_shift):
        arr = U.nd.shift(arr, subpx_shift)

    # create empty list for slices
    nds = arr.ndim - 1
    choices = ['slice(halfS[%i])', 'slice(-halfS[%i], None)']
    nchoices = len(choices)
    nds2 = nds**2
    slcs = []
    for ns in range(nds2):
        slcs.append([])
        for n in range(nchoices*nds):
            slcs[ns].append([Ellipsis]) # Ellipsis help to make arbitray number of list

    # fill the empty list by slice (here I don't know how to use 4D..)
    for i in range(nds2):
        for d in range(nds):
            for x in range(nds):
                for c, choice in enumerate(choices):
                    if d == 0 and x == 0:
                        idx = x*(nchoices) + c
                    else: # how can I use 4D??
                        idx = x*(nchoices) + (nchoices-1) - c
                    exec('content=' + choice % d)
                    slcs[i][idx] += [content]

    # cutout and paste
    for slc in slcs:
        for s in slc:
            s.append(slice(shapeS[-1]))
            #print s
            canvas[s] = arr[s]
    return canvas


def paddingMed(img, shape, shift=None, smooth=10):
    """
    pad with median
    see doc for paddingValue
    """
    try:
        med = N.median(img, axis=None)
    except TypeError: # numpy version < 1.1
        med = U.median(img)
    return paddingValue(img, shape, med, shift, smooth)

def evenShapeArr(a):
    """
    return even shaped array
    """
    shapeA = N.asarray(a.shape)
    shapeM = shapeA.copy()
    for i,s in enumerate(shapeM):
        if not i and s == 1:
            continue
        elif s % 2:
            shapeM[i] -= 1
    #sy,sx = shapeA
    #if sx % 2:# or sy %2:
    #    sx += 1
    #if sy % 2:
    #    sy += 1
    #shapeM = N.array([sy, sx])
    
    if N.sometrue(shapeA < shapeM):
        a = paddingMed(a, shapeM)
    elif N.sometrue(shapeA > shapeM):
        a = cutOutCenter(a, shapeM, interpolate=False)
    return a

def resolutionLimit(wave_nm, NA, n):
    """
    returns diffraction limit in um
    """
    return (0.61 * wave_nm) / (n * NA) 

#--- Make Gaussian arr -----------------------------
def gaussianArrND(shape=(256,256), sigma=2., peakVal=None, orig=None, rot=0):
    try:
        ndim = len(shape)
    except TypeError:
        shape = [shape]
        ndim = 1
    sidx = ndim + 2
    slices = [Ellipsis] + [slice(0,m) for m in shape]
    inds, LD = imgFit.rotateIndicesND(slices, N.float32, rot)
    #inds = N.indices(shape, N.float32)

    try:
        if len(sigma) != ndim:
            raise ValueError, 'len(sigma) must be the same as len(shape)'
    except TypeError:
        sigma = [sigma] * ndim

    if orig is None:
        c = N.asarray(shape, N.float32)/2.
    else:
        c = N.asarray(orig, N.float32)

    if peakVal:
        k0 = peakVal
    else:
        k0 = 1. / (N.average(sigma) * ((2*N.pi)**0.5))

    param = [0, k0] + list(c) + list(sigma)
    param = N.asarray(param, N.float32)
    return imgFit.yGaussianND(param, inds, sidx)

def gaussianArr2D(shape=(256,256), sigma=[2.,2.], peakVal=None, orig=None, rot=0):
    """
    >1.5x faster implemetation than gaussianArrND
    shape: (y,x)
    sigma: scaler or [sigmay, sigmax]
    orig: (y,x)
    rot:   scaler anti-clockwise

    return N.float32
    """
    shape = N.asarray(shape, N.uint)
    try:
        if len(sigma) == len(shape):
            sy = 2*(sigma[0]*sigma[0])
            sx = 2*(sigma[1]*sigma[1])
        elif len(sigma) == 1:
            sx = sy = 2*(sigma[0]*sigma[0])
        else:
            raise ValueError, 'sigma must be scaler or [sigmay, sigmax]'
    except TypeError: # sigma scaler
        sx = sy = 2*(sigma*sigma)


   # print y, x
    if rot:
        yyi, xxi = imgFit.rotateIndices2D(shape, rot, orig, N.float32)
    else:
        if orig is None:
            y, x = shape / 2. - 0.5 # pixel center remove
        else:
            y, x = N.subtract(orig, 0.5) # pixel center remove

        yi, xi = N.indices(shape, dtype=N.float32)
        yyi = y-yi
        xxi = x-xi
    k1 = -(yyi)*(yyi)/(sy) - (xxi)*(xxi)/(sx)

    if peakVal:
        k0 = peakVal
    else:
        k0 = 1. / ((sx+sy)/2. * ((2*N.pi)**0.5))
    return k0 * N.exp(k1)

# finding points

def findMaxWithGFit(img, sigma=0.5, win=11):
    '''
    find sub-pixel peaks from input img using n-dimensional Guassian fitting

    sigma: scaler or [simgaZ,sigmaY..]
    window: a window where the Guassian fit is performed on

    return [v, zyx, sigma]
    '''
    imgFit.fitFailedClear()
    vzyx = U.findMax(img)
    ndim = img.ndim
    try:
        ret, check = imgFit.fitGaussianND(img, vzyx[-ndim:], sigma, win)
    except IndexError: # too close to the edge
        imgFit.fitFailedAppend("at %s" % str(vzyx[-ndim:]))
        sigma = imgFit._scalerToSeq(sigma, ndim)
        return list(vzyx)[0:1] + [vzyx[-ndim:]] + [list(sigma)]

    if check == 5:
        imgFit.fitFailedAppend("at %s, %s, check=%i" % (str(vzyx[-ndim:]), str(ret), check))
        sigma = imgFit._scalerToSeq(sigma, ndim)
        return list(vzyx)[0:1] + [vzyx[-ndim:]] + [sigma]
    else:
        v = ret[1]
        zyx = ret[2:2+ndim]
        sigma = ret[2+ndim:2+ndim*2]
        return [v,zyx,sigma]

def centerOfMass(img, yx, window=5):
    """
    find peak by center of mass in a 2D image

    img:    a 2D image array
    yx:     (y,x) in the image
    window: a window where CM calculation is performed on

    return yx
    """
    # prepare small image
    s = N.array([window,window])
    c = s/2.
    yx = N.round_(yx)
    yx -= c
    yi, xi = N.indices(s)
    yi += yx[0]
    xi += yx[1]
    cc = img[yi,xi]

    # calculate center of mass
    yxi = N.indices(s)
    yxi *= cc
    yxi = yxi.T
    vv = N.sum(yxi, axis=0)
    vv = N.sum(vv, axis=0)
    yxs = vv / float(N.sum(cc))
    yxs += yx
    return yxs

# removing points

def mask_value(arr, zyx, r=2.5, value=0):
    ''' Edit the pixels around zyx to be zero '''
    import imgGeo
    sls = imgGeo.nearbyRegion(arr.shape, zyx, 2*N.asarray(r)+1)
    arr[sls] = value


def mask_gaussianND(arr, zyx, v, sigma=2., ret=None, rot=0, clipZero=True):
    ''' 
    subtract elliptical gaussian at y,x with peakVal v
    if ret, return arr, else, arr itself is edited
    '''
    import imgGeo
    zyx = N.asarray(zyx)
    ndim = arr.ndim
    shape = N.array(arr.shape)
    try:
        if len(sigma) != ndim:
            raise ValueError, 'len(sigma) must be the same as len(shape)'
        else:
            sigma = N.asarray(sigma)
    except TypeError:#(TypeError, ValueError):
        sigma = N.asarray([sigma]*ndim)

    # prepare small window
    slc = imgGeo.nearbyRegion(shape, N.floor(zyx), sigma * 10)
    inds, LD = imgFit.rotateIndicesND(slc, dtype=N.float32, rot=rot)
    param = (0, v,) + tuple(zyx) + tuple(sigma)
    sidx = 2 + ndim
    g = imgFit.yGaussianND(N.asarray(param), inds, sidx).astype(arr.dtype.type)
    roi = arr[slc]
    if clipZero:
        g = N.where(g > roi, roi, g)

    if ret:
        e = N.zeros_like(arr)
        e[slc] = g  # this may be faster than copy()
        return arr - e
    else:
        arr[slc] -= g

##-- Mask edge--
def maskEdgeWithValue2D(arr, val=None):
    """
    overwrite 2D image edge (s[:-2,2:]) with value **in place**
    
    if val is None, use median
    """
    if not val:
        val = U.median(arr[:-2,2:])
    arr[-2:] = val
    arr[:,:2] = val
    return arr

#----PALM functions-----------------
def mode(arr):
    arr1D = arr.ravel()
    y, x = N.histogram(arr1D, len(arr1D))
    yx = zip(y,x)
    return max(yx)[1]


### radialAverage
# http://stackoverflow.com/questions/21242011/most-efficient-way-to-calculate-radial-profile
def radialaverage(data, center=None, useMaxShape=False):
    """
    data: ND array
    center: coordinate of center of radii
    useMinShape: the output uses the maximum shape available

    return 1D array
    """
    if center is None:
        center = N.array(data.shape) // 2
    if len(center) != data.ndim:
        raise ValueError, 'dimension of center (%i) does not match the dimension of data (%i)' % (len(center), data.ndim)

    zyx = N.indices((data.shape))
    r = N.zeros(data.shape, N.float32)
    for i, t in enumerate(zyx):
        r += (t - center[i])**2
    r = N.sqrt(r)
    #y, x = N.indices((data.shape))
    #r = N.sqrt((x - center[0])**2 + (y - center[1])**2) # distance from the center
    r = r.astype(N.int)

    if data.dtype.type in (N.complex64, N.complex128):
        rbin = N.bincount(r.ravel(), data.real.ravel())
        ibin = N.bincount(r.ravel(), data.imag.ravel())
        tbin = N.empty(rbin.shape, data.dtype.type)
        tbin.real = rbin
        tbin.imag = ibin
        
    else:
        tbin = N.bincount(r.ravel(), data.ravel())
    nr = N.bincount(r.ravel())
    radialprofile = tbin / nr.astype(N.float32)

    if not useMaxShape:
        minShape = min(list(N.array(data.shape) - center) + list(center))
        radialprofile = radialprofile[:minShape]
    return radialprofile 

def radialAverage2D(arr, center=None, useMaxShape=False):
    """
    2D-wise radial average
    arr: ND (>2) array
    center: 2D center to radial average

    return ND-1 array
    """
    if arr.ndim == 2:
        return radialaverage(arr, center, useMaxShape)
    
    for t, img in enumerate(arr):
        if img.ndim >= 3:
            ra = radialaverage2D(img, center, useMaxShape)
        else: # 2D
            ra = radialaverage(img, center, useMaxShape)

        try:
            canvas[t] = ra
        except NameError: # canvas was not defined yet
            canvas = N.empty((arr.shape[0],) + ra.shape, ra.dtype.type)
            canvas[t] = ra
    return canvas
                

def shiftFullFFT(arr, delta=None):
    """
    returns new array: arr shifted by delta (tuple)
       it uses fft (not rfft), multiplying with "shift array", ifft
    delta defaults to half of arr.shape 
    """
    shape = arr.shape
    if delta is None:
        delta = N.array(shape) / 2.
    elif not hasattr(delta, '__len__'):
        delta = (delta,)*len(shape)
    elif len(shape) != len(delta):
        raise ValueError, "shape and delta not same dimension"

    return F.ifft(F.fourierShiftArr(shape, delta) * F.fft(arr))

def shiftZ(af):
    """
    af: 3D array in fourier space

    return Z shifted array
    """
    nz = af.shape[0]
    cz = nz // 2
    
    bf = N.empty_like(af)
    bf[cz:] = af[:(nz-cz)]
    bf[:(nz-cz)] = af[cz:]
    return bf
    
def getFourierZprofile(arr3D):
    """
    arr3D: image array

    return 
    """
    af = F.rfft(arr3D)
    nk = min(arr3D.shape[-2:])
    afr = radialAverage2D(af, center=(0,0), useMaxShape=True)
    afz = shiftZ(afr[:,:nk])
    return afz
    
def getSphericalAbbe(arr3D, kmin=2, kmax=60, plot=False):
    """
    compare frequency above and below the focus

    return amplitude var(above)/var(below)
    """
    afz = getFourierZprofile(arr3D)

    # get z profile around the reasonable frequency
    aa = N.average(N.abs(afz[:,kmin:kmax]), axis=1)

    # findMax
    inds = N.indices(aa.shape, dtype=N.float64)
    v, _0, _1, z = U.findMax(aa)
    parm, check = imgFit.fitGaussianND(aa, [z], window=len(aa))
    if check == 5:
        raise RuntimeError, 'Peak not found check=%i' % check

    gg = imgFit.yGaussianND(parm, inds, 3)
    amg = aa - gg

    z0 = parm[2]
    mask = (parm[-1] * 3) / 2. # sigma * 3 / 2
    ms0 = N.ceil(z0 - mask)
    ms1 = N.ceil(z0 + mask)
    amg[ms0:ms1] = 0
    
    below = N.var(amg[:ms0])
    above = N.var(amg[ms1:])

    if plot:
        Y.ploty(N.array((aa, gg, amg)))
        print 'below: ', below
        print 'above: ', above
        print ms0, ms1, z0

    return above / (above + below)#above / below


## polar transform

## from
# http://stackoverflow.com/questions/9924135/fast-cartesian-to-polar-to-cartesian-in-python
import numpy as np

def polar2cart2D(r, theta, center):

    y = r  * np.sin(theta) + center[0]
    x = r  * np.cos(theta) + center[1]
    return y, x# x, y

def img2polar2D(img, center, final_radius=None, initial_radius = None, phase_width = 360):
    """
    img: array
    center: coordinate y, x
    final_radius: ending radius
    initial_radius: starting radius
    phase_width: npixles / circle
    """
    if img.ndim > 2 or len(center) > 2:
        raise ValueError, 'this function only support 2D, you entered %i-dim array and %i-dim center coordinate' % (img.ndim, len(center))
    
    if initial_radius is None:
        initial_radius = 0

    if final_radius is None:
        rad0 = N.ceil(N.array(img.shape) - center)
        final_radius = min((min(rad0), min(N.ceil(center))))

    if phase_width is None:
        phase_width = N.sum(img.shape[-2:]) * 2

    theta , R = np.meshgrid(np.linspace(0, 2*np.pi, phase_width), 
                            np.arange(initial_radius, final_radius))

    Ycart, Xcart = polar2cart2D(R, theta, center)

    Ycart = N.where(Ycart >= img.shape[0], img.shape[0]-1, Ycart)
    Xcart = N.where(Xcart >= img.shape[1], img.shape[1]-1, Xcart)
    
    Ycart = Ycart.astype(int)
    Xcart = Xcart.astype(int)


    polar_img = img[Ycart,Xcart]
    polar_img = np.reshape(polar_img,(final_radius-initial_radius,phase_width))

    return polar_img

