
#import OMXlab as O
#from Data import data as D
import os
#exec('import %s as O' % os.path.basename(D.WORKDIR))
try:
    from ..Priithon.all import N, U, F
except ValueError:
    from Priithon.all import N, U, F
from . import imgFilters, imgFit, imgGeo, imgResample

# cross-correlation
PHASE=True
NYQUIST=0.2#0.6


def _findMaxXcor(c, win, gFit=True, niter=2):
    if gFit:
        for i in range(niter):
            v, zyx, s = findMaxWithGFit(c, win=win+(i*2))
            if v:
                if N.any(zyx > N.array(c.shape)) or N.any(zyx < 0):
                    vzyx = N.array(U.findMax(c))#continue
                    v = vzyx[0]
                    zyx = vzyx[-c.ndim:] + 0.5 # pixel center
                    s = 2.5
                else:
                    break

        if not v:
            v = U.findMax(c)[0]
    else:
        vzyx = U.findMax(c)
        v = vzyx[0]
        zyx = N.array(vzyx[-c.ndim:]) + 0.5 # pixel center
        s = 2.5
    return v, zyx, s

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
        shape = N.array(af.shape)
        shape[-1] = (shape[-1] - 1) * 2
        szyx = shape / 2.

        if _G is not None and N.alltrue(_G_SHAPE == shape):
            g = _G
        else:
            g = imgFilters.gaussianArrND(shape, highpassSigma, peakVal=1, orig=szyx)
            g = F.shift(g)[...,:af.shape[-1]]

            _G = g
            _G_SHAPE = N.asarray(g.shape)
        g += wiener
        af /= g

    # kill DC
    af.flat[0] = 0
    # kill lowest freq in YX
    for d in range(af.ndim-2, af.ndim):
        upperdim = ':,' * d
        exec('af[%s0:cutoffFreq] = 0' % upperdim)
    
    return af

def findMaxWithGFit(img, sigma=0.5, win=11):
    '''
    find sub-pixel peaks from input img using n-dimensional Guassian fitting

    sigma: scaler or [simgaZ,sigmaY..]
    window: a window where the Guassian fit is performed on

    return [v, zyx, sigma]
    '''
    vzyx = N.array(U.findMax(img))
    ndim = img.ndim
    try:
        ret, check = imgFit.fitGaussianND(img, vzyx[-ndim:], sigma, win)
    except IndexError: # too close to the edge
        imgFit.fitFailedAppend("at %s" % str(vzyx[-ndim:]))
        sigma = imgFit._scalerToSeq(sigma, ndim)
        return vzyx[0:1], vzyx[-ndim:], list(sigma)

    if check == 5 or N.any(ret[2:2+ndim] > (vzyx[-ndim:] + win)) or  N.any(ret[2:2+ndim] < (vzyx[-ndim:] - win)):
        imgFit.fitFailedAppend("at %s, %s, check=%i" % (str(vzyx[-ndim:]), str(ret), check))
        sigma = imgFit._scalerToSeq(sigma, ndim)
        return [vzyx[0:1], vzyx[-ndim:], sigma]
    #x= (vzyx[0:1] + [vzyx[-ndim:]] + [sigma])
    #    print x
    #    return x
    else:
        v = ret[1]
        zyx = ret[2:2+ndim]
        sigma = ret[2+ndim:2+ndim*2]
        return [v,zyx,sigma]

# Filters for Xcorr
def prefilter(arr, mexSize=2., sobel=True):
    """
    pixSizZ: only needed when bandStop is True
    """
    if arr is None:
        return arr

    if mexSize:
        arr = mexhatFilter(arr, mexSize)

    if sobel:
        arr = U.nd.sobel(arr)
        arr = imgFilters.maskEdgeWithValue2D(arr)

    return arr

# highpass filters

def bandStopFilter(arr, x=4):
    """
    to remove large pixelation artifact in Z
    """
    #shape = N.asarray(arr.shape)
    #shape = N.where(shape % 2, shape+1, shape)
    #if N.sometrue(shape > arr.shape):
    #    arr = imgFilters.paddingMed(arr, shape)

    fa = F.rfft2d(arr)
    fa[:x,1:] = 0
    fa[-x:,1:] = 0
    return F.irfft2d(fa)

def mexhatFilter(a, mexSize=1):#, trimRatio=0.9):
    """
    returned array is trimmed to remove edge
    """
    global mexhatC, mexhatC_size, mexhatCf

    a = imgFilters.evenShapeArr(a)
    from Priithon.all import F as fftw
    try:
        if mexhatC.shape != a.shape:
            raise ValueError('go to except')
        if mexhatC_size != mexSize:
            raise ValueError('go to except')
    except NameError as ValueError:
        mexhatC_size = mexSize
        shape = N.asarray(a.shape, N.int)#N.float32)
        mexhatC = F.shift(F.mexhatArr(shape, scaleHalfMax=mexhatC_size, orig=None)) # orig 0.5 pixel does not work...
        mexhatCf = fftw.rfft(mexhatC) / N.multiply.reduce( shape )

    ar = fftw.irfft( fftw.rfft(a.astype(N.float32)) * mexhatCf )
    
    #if trimRatio < 1:
    #    ar = trim3D(ar, trimRatio)
    #ar = imgFilters.maskEdgeWithValue2D(ar) # 2 pixels at the edges
    return ar

GAUSS=None

def phaseContrastFilter(a, inFourier=False, nyquist=NYQUIST):
    global GAUSS
    if inFourier:
        af = a.copy()
    else:
        af = F.rfft(a)

    # here is the phase contrast
    phase = N.arctan2(af.imag, af.real)
    afa = N.empty_like(af)
    afa.real = N.cos(phase)
    afa.imag = N.sin(phase)

    # lowpass gaussian filter of phase image
    if nyquist: # since this takes long time, gaussian array is re-used if possible
        if GAUSS is not None and GAUSS[0] == nyquist and GAUSS[1].shape == afa.shape:
            nq, gf = GAUSS
        else:
            gshape = N.array(a.shape)
            if inFourier:
                gshape[-1] -= 1
                gshape[-1] *= 2
            sigma = gshape * nyquist
            #print('sigma', sigma, 'gshape', gshape, 'nyquist', nyquist)
            gf = imgFilters.gaussianArrND(gshape, sigma, peakVal=1)
            gf = N.fft.fftshift(gf)[Ellipsis, :af.shape[-1]]
            
            GAUSS = (nyquist, gf)
        afa *= gf

    if inFourier:
        ap = afa
    else:
        ap = F.irfft(afa)
    return ap

#DATA=[]

def Xcorr(a, b, phaseContrast=PHASE, nyquist=NYQUIST, gFit=True, win=11, ret=None, searchRad=None, napo=10):#npad=4):
    """
    sigma uses F.gaussianArr in the Fourier domain
    if ret is None:
        return zyx, xcf
    elif ret is 2:
        return s, v, zyx, xcf
    elif ret is 3:
        return zyx, xcf, a_phase_cotrast, b_phase_contrast
    elif ret:
        return v, zyx, xcf
    """
    #print 'phase contrast: %s' % str(phaseContrast)
    #global DATA
    # correct odd shape particularly Z axis
    a = N.squeeze(a)
    b = N.squeeze(b)
    a = imgFilters.evenShapeArr(a)
    b = imgFilters.evenShapeArr(b)
    shape = N.array(a.shape)

    # padding strange shape
    #nyx = max(shape[-2:])
    #pshape = N.array(a.shape[:-2] + (nyx,nyx))

    # apodize
    #a = paddAndApo(a, npad)
    #b = paddAndApo(b, npad)
    if napo:
        a = apodize(a, napo)
        b = apodize(b, napo)

    # fourier transform
    af = F.rfft(a.astype(N.float32))
    bf = F.rfft(b.astype(N.float32))
    del a, b

    # phase contrast filter (removing any intensity information)
    if phaseContrast:
        afa = phaseContrastFilter(af, True, nyquist=nyquist)
        bfa = phaseContrastFilter(bf, True, nyquist=nyquist)
    else:
        afa = af
        bfa = bf
    del af, bf

    targetShape = shape #+ (npad * 2)

    # shift array
    delta = targetShape / 2.
    shiftarr = F.fourierRealShiftArr(tuple(targetShape), delta)
    bfa *= shiftarr

    # cross correlation
    bfa = bfa.conjugate()
    #c = cc = F.irfft(afa * bfa)
    c = F.irfft(afa * bfa)

    # 20180214 the padded region was cutout before finding the peak.
    #c = cc = imgFilters.cutOutCenter(c, N.array(c.shape) - (npad * 2), interpolate=False)
    cc = c
    center = N.divide(c.shape, 2)
    if searchRad:
        slc = imgGeo.nearbyRegion(c.shape, center, searchRad)
        cc = N.zeros_like(c)
        cc[slc] = c[slc]
    v, zyx, s = _findMaxXcor(cc, win, gFit=gFit)
    #return cc
    #print(zyx, center)
    zyx -= center

    #c = imgFilters.cutOutCenter(c, N.array(c.shape) - (npad * 2), interpolate=False)
    #c = imgFilters.cutOutCenter(c, shape, interpolate=False)

    if ret == 3:
        return zyx, c, F.irfft(afa), F.irfft(bfa)
    elif ret == 2:
        return s, v, zyx, c
    elif ret:
        return v, zyx, c
    else:
        return zyx, c



def normalizedXcorr(a, b):
    std = N.std(a) * N.std(b)
    a_ = (a - N.mean(a)) / std
    b_ = (b - N.mean(b)) / std

    c = F.convolve(a_, b_, conj=1)# / a.size
    
    return c

def paddAndApo(img, npad=4, shape=None):
    if shape is None:
        shape = N.array(img.shape)
    else:
        shape = N.array(shape)
    return imgFilters.paddingMed(img, shape + (npad * 2), smooth=npad)


def apodize_old(img, napodize=10, doZ=True):
    """
    softens the edges of a singe xy section to reduce edge artifacts and improve the fits

    return copy of the img
    """
    img = img.copy()
    img = img.astype(N.float32) # casting rule

    # determine napodize
    shape = N.array(img.shape) // 2
    napodize = N.where(shape < napodize, shape, napodize)
    if doZ and img.ndim >= 3 and img.shape[0] > 3:
        rr = list(range(-3,0))
    else:
        rr = list(range(-2,0))
    for idx in rr:
        fact = N.arange(1./napodize[idx],napodize[idx],1./napodize[idx], dtype=N.float32)[:napodize[idx]]
        for napo in range(napodize[idx]):
            slc0 = [Ellipsis,slice(napo, napo+1)] + [slice(None)] * abs(idx+1)
            if not napo:
                slc1 = [Ellipsis,slice(-(napo+1),None)] + [slice(None)] * abs(idx+1)
            else:
                slc1 = [Ellipsis,slice(-(napo+1),-(napo))] + [slice(None)] * abs(idx+1)
            img[tuple(slc0)] *= fact[napo]
            img[tuple(slc1)] *= fact[napo]
                #img[slc0] = img[slc0] * fact[napo] # casting rule
                #img[slc1] = img[scl1] * fact[napo]
    return img

def apodize(img, napodize=10, doZ=True):
    """
    softens the edges of a single xy section to reduce edge artifacts and improve the fits

    return copy of the img
    """
    if napodize:
        if doZ and img.ndim >= 3:
            shape = img.shape[-3:]
        else:
            shape = img.shape[-2:]

        one = N.ones(shape, N.float32)
        ones = [F.getPadded(one[(slice(i,-i),)*len(shape)], shape) for i in range(1,napodize+1)]
        fact = N.mean(ones, axis=0)
        val = img[:] * fact

        frame = (1 - fact) * N.median(img)

        return val + frame
    else:
        return img

def iteration(a, b, niter=5, phaseContrast=PHASE, nyquist=NYQUIST, gFit=True, win=11, ret=None, searchRad=None, npad=4):
    """
    iterative xcorr

    if ret is None:
        reutrn zyx
    elif ret is 1:
        retunr zyx, N.array((a0, b0))
    """
    zyx, c = Xcorr(a, b, phaseContrast, nyquist, gFit, win, searchRad=searchRad, npad=npad)
    for i in range(niter):
        b0 = imgResample.trans3D_affine(b, zyx)
        slc = _makeSlice(zyx)
        b0 = b0[slc]
        a0 = a[slc]
        zyx0, c = Xcorr(a0, b0, phaseContrast, nyquist, gFit, win, searchRad=searchRad, npad=npad)
        zyx += zyx0

    if ret is None:
        return zyx
    elif ret is 1:
        return zyx, N.array((a0, b0))
    elif ret is True:
        return zyx, c
        
def _makeSlice(zyx):
    slcs = []
    for x in zyx:
        if x >= 0:
            slc = slice(int(N.ceil(x)), None, None)
        else:
            slc = slice(0, -int(N.ceil(abs(x))))
        slcs.append(slc)
    return slcs
