import numpy as N
from Priithon.all import U
from PriCommon import xcorr, imgResample, imgGeo,imgFilters
import sys
if hasattr(sys, 'app'):
    from PriCommon import ppro
else:
    from PriCommon import ppro26 as ppro
import cutoutAlign
from scipy import ndimage
import exceptions


class AlignError(exceptions.Exception): pass

CTHRE=0.065
MAX_SHIFT = 2 #0.4 # um
MIN_PXLS_YX = 30

QUADRATIC_AREA=['Right-Top', 'Left-Top', 'Left-Bottom', 'Right-Bottom']



def prep2D(a3d, zs=None):
    """
    simply makes maximum projection of best z sections

    return 2D-array
    """
    if zs is None:
        zs = findBestRefZs(a3d)

    aa = a3d[zs]
    return N.max(aa, axis=0)

def chopImg(a2d, center=None):
    """
    return a tuple of quadratic images
    """
    if center is None:
        center = N.array(a2d.shape) // 2
    r1 = a2d[center[0]:,center[1]:]
    r2 = a2d[center[0]:,:center[1]]
    r3 = a2d[:center[0],:center[1]]
    r4 = a2d[:center[0],center[1]:]
    return r1, r2, r3, r4


def estimate2D(a2d, ref, center=None, phaseContrast=True, cqthre=CTHRE/10., max_shift_pxl=5):
    """
    return [ty,tx,r,my,mx]
    """
    if center is None:
        shape = N.array(a2d.shape)
        center = shape // 2

    # quadratic cross correlation
    a1234 = chopImg(ref, center)
    b1234 = chopImg(a2d, center)

    ab = zip(a1234, b1234)
    try:
        yxcs = [xcorr.Xcorr(a, b, phaseContrast=phaseContrast, searchRad=max_shift_pxl) for a, b in ab]
    except IndexError:
        return N.array((0,0,0,1,1), N.float32), [0,0], range(4)
    except (ValueError, ZeroDivisionError):
        raise AlignError
    yxs = [yx for yx, c in yxcs]
    
    # quality check
    cqvs = [c.max() - c[c.shape[0]//4].std() for yx, c in yxcs]
    del yxcs, ab, c
    
    cqs = [cv > cqthre for cv in cqvs]

    ids = [idx for idx, cq in enumerate(cqs) if cq == False]

    # translation
    tyx = getTranslation(yxs)

    # magnification
    myx = getMagnification(yxs, center)

    # rotation
    theta, offset = getRotation(yxs, center)

    return list(tyx) + [theta] + list(myx), offset, ids

def getTranslation(yxs):
    """
    cqs: cross-correlation quality
    
    return [ty,tx]
    """
    tyx1 = (yxs[0] + yxs[2]) / 2.
    tyx2 = (yxs[1] + yxs[3]) / 2.

    tyx = N.array((tyx1, tyx2)).mean(axis=0)

    return tyx

def getMagnification(yxs, center):
    """
    return [my,mx]
    """
    my1 = (yxs[0][0] - yxs[3][0]) / 2.
    my2 = (yxs[1][0] - yxs[2][0]) / 2.

    my = (my1 + my2) / 2.

    mx2 = (yxs[0][1] - yxs[1][1]) / 2.
    mx1 = (yxs[3][1] - yxs[2][1]) / 2.

    mx = (mx1 + mx2) / 2.

    myx = N.array((my, mx), N.float32)
    myx = (myx + center) / center

    #print my1, my2, mx1, mx2
    return myx


def getRotation(yxs, center):
    """
    return r, offset_rotation
    """
    # angle increases toward left-up, thus y is plus while x is minus
    asiny1 = (yxs[0][0] - yxs[1][0]) / 2.
    asiny2 = (yxs[3][0] - yxs[2][0]) / 2.

    asiny = (asiny1 + asiny2) / 2.

    asinx1 = (yxs[3][1] - yxs[0][1]) / 2.
    asinx2 = (yxs[2][1] - yxs[1][1]) / 2.

    asinx = -(asinx1 + asinx2) / 2.

    # rotation center but something is wrong...
    if asinx1 and asinx2:
        offy = asiny2 - asiny1
        offx = asinx2 - asinx1
        offset = [offy, offx]
    else:
        offset = [0,0]
    
    # the center of the quadratic image should be determined
    center2 = center/2.
    cdeg = N.degrees(N.arctan2(*center2))
    ryx = center2 + (asiny, asinx)
    theta = N.degrees(N.arctan2(*ryx)) - cdeg

    #print asiny1, asiny2, asinx1, asinx2, offset
    return theta, offset

def iteration(a2d, ref, maxErr=0.01, niter=10, phaseContrast=True, initguess=None, echofunc=None, max_shift_pxl=5, if_failed='simplex'):
    """
    iteratively do quadratic cross correlation

    a2d: image to be aligned
    ref: reference image
    maxErr: iteration is terminated when the calculated shift become less than this value (in pixel)
    niter: maximum number of iteration
    max_shift_pxl: number of pixels for you to allow the images to shift
    if_failed: 'terminate' or else

    return [ty,tx,r,my,mx] if_failed is 'terminate' and failed, return None
    """
    shape = N.array(a2d.shape)
    center = shape // 2

    ret = N.zeros((5,), N.float32)
    ret[3:] = 1
    if initguess is None or N.all(initguess[:2] == 0):
        yx, c = xcorr.Xcorr(ref, a2d, phaseContrast=phaseContrast)
        ret[:2] = yx
    else:
        print 'in iteration, initial geuss is', initguess
        ret[:] = initguess[:]

    if if_failed == 'force_simplex':
        goodImg = False
    else:
        goodImg = True
    rough = True
                    
    offset = N.zeros((2,), N.float32)
    for i in range(niter):

        if i == 0 and initguess is None:
            b = a2d
            c = ref
            startYX = [0,0]
        else:
            b = applyShift(a2d, [0]+list(ret), offset)

            # cut out
            # because irregular size of the quadratic images are not favorable,
            # the smallest window will be used
            shiftZYX = cutoutAlign.getShift([0]+list(ret), [0]+list(shape))
            maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
            maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
            slc = [slice(maxcutY, shape[0]-maxcutY),
                   slice(maxcutX, shape[1]-maxcutX)]
            b = b[slc]
            c = ref[slc]

            startYX = [maxcutY, maxcutX]

        if goodImg:
            ll, curroff, checks = estimate2D(b, c, center-startYX+offset, phaseContrast=phaseContrast, max_shift_pxl=max_shift_pxl)
            if len(checks) <= 1:
                ret[:3] += ll[:3]
                ret[3:] *= ll[3:]

            # the quality of quadratic correlation affects resolution.
            # instead of using low-correlation results, such images are sent to alternative calculation.
            if len(checks):
                if if_failed == 'terminate':
                    return
                
                elif echofunc:
                    regions = [QUADRATIC_AREA[idx] for idx in checks]
                    echofunc('%s quadratic regions had too-low correlation, using alternative, slow algorithm' % regions)
                else:
                    regions = [QUADRATIC_AREA[idx] for idx in checks]
                    print '%s quadratic regions had too-low correlation, using alternative, slow algorithm' % regions
                goodImg = False
                checks = []
                if initguess is not None:
                    ret[:] = initguess[:]
            #elif i > 5:
                #offset += curroff

        else:
            ll = simplex(b, c, phaseContrast, rough=rough)
            ret[:3] += ll[:3]
            ret[3:] *= ll[3:]
            rough = False
            #if echofunc:
            #echofunc('%i: %s' % (i, ll))#ref))
        print i, ret
        errs = errPxl(ll, center)
        if N.all(errs < maxErr):
            break


    return ret#, offset

def errPxl(yxrm, center):
    """
    align parameters are converted to pixel values

    yxrm: [ty,tx,r,my,mx]
    center: [cy,cx]

    return error value in pixel of [ty,tx,r,my,mx]
    """
    center = center / 2.
    radius = N.hypot(*center)

    # rotation
    r = yxrm[2]
    x = radius * N.cos(r) - radius
    y = radius * N.sin(r)
    rerr = N.hypot(x, y)
    
    # magnification
    myerr = (yxrm[3] * radius) - radius
    mxerr = (yxrm[4] * radius) - radius

    errlist = list(yxrm[:2]) + [rerr, myerr, mxerr]

    return N.abs(N.array(errlist))

def iterationXcor(a2d, ref, maxErr=0.01, niter=20, phaseContrast=True, initguess=None, echofunc=None):
    """
    find out translation along X axis
    this function is used for alignment of the Z axis
    parameters are the same as 'iteration'

    return [ty,tx]
    """
    shape = N.array(a2d.shape)
    yxs = N.zeros((2,), N.float32)
    if initguess is not None:
        yxs[:] = initguess
        #if echofunc:
        #    echofunc('initguess Xcorr: %s' % yxs)
        print 'initguess Xcorr:', yxs
    
    for i in xrange(niter):
        if i == 0 and initguess is None:
            b = a2d
            c = ref
            #startYX = [0,0]
        else:
            b = applyShift(a2d, [0]+list(yxs)+[0,1,1])#, offset)
            # cut out
            shiftZYX = cutoutAlign.getShift([0]+list(yxs)+[0,1,1], [0]+list(shape))
            maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
            maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
            slc = [slice(shiftZYX[2], shiftZYX[3]),
                   slice(shiftZYX[4], shiftZYX[5])]
            b = b[slc]
            c = ref[slc]

        yx = xcorr.Xcorr(c, b, phaseContrast=phaseContrast)[0]
        yxs += yx
        print 'xcorr', i, yxs
        #if echofunc:
        #    echofunc('xcorr %i: %s' % (i, yx))

        if yx[1] < maxErr:
            break

    return yxs


###----- simplex (alternative) method
def simplex(a, b, phaseContrast=True, rough=True):
    from scipy import optimize


    yxrm = N.zeros((5,), N.float64)
    #yxrm[:2] += yx
    yxrm[-2:] = 1

    # rough estimate
    if rough:
        yxrm[2] = roughRotMag(b, a, yxrm, 2, 0.02, 20)
        yxrm[3] = roughRotMag(b, a, yxrm, 3, 0.005, 20)
        yxrm[4] = roughRotMag(b, a, yxrm, 4, 0.005, 20)
    
    yxrm = optimize.fmin(_compCost, yxrm, (b, a), disp=0)

    # since xcorr is much better at yx estimation, yx part is replaced.
    #try:
    #    yx, c = xcorr.Xcorr(b, a, phaseContrast=phaseContrast)
    #    yxrm[:2] = yx
    #except (ValueError, ZeroDivisionError):
    #    raise AlignError

    return yxrm

def _compCost(yxrm, a, b):
    zyxrm = N.zeros((7,), N.float64)
    zyxrm[1:4] = yxrm[:3]
    zyxrm[5:] = yxrm[3:]
    
    b = applyShift(b, zyxrm)

    shape = a.shape
    shiftZYX = cutoutAlign.getShift([0]+list(yxrm), [0]+list(shape))
    maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
    maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
    slc = [slice(maxcutY, shape[0]-maxcutY),
           slice(maxcutX, shape[1]-maxcutX)]
    a = a[slc]
    b = b[slc]

    v = 1/ calcPearson(a, b)

    return v


def roughRotMag(a, b, yxrm, idx, step=0.02, nstep=20):
    guess = yxrm[idx]
    
    Range = (guess - (step*nstep), guess + (step * nstep), step)
    xs = N.arange(*Range)
    yxrms = N.empty((len(xs),)+yxrm.shape, yxrm.dtype.type)
    yxrms[:] = yxrm
    yxrms[:,idx] = xs
    #for r in Range:
    #    yxrm2 = N.copy(yxrm)
    #    yxrm2[idx] = r
    #    yxrms.append(yxrm2)

    pp = ppro.pmap(_compCost, yxrms, ppro.NCPU, a, b)
    #pp = [_compCost(yx, a, b) for yx in yxrms]
    xi = N.argmin(pp)
    pmin = pp[xi]

    base = max(pp)
    if pmin == base: # failed to get the curve for some reason
        # usually this happens if one used ndimage.zoom() in scipy
        # ndimage.zoom only interpolate pixel-wise.
        # no subpixel interpolation is done...
        x = int(idx >= 3)
        check = 5
    else: # go ahead and fit poly
        x = xs[xi]
        data = zip(xs,pp)
        fit, check = U.fitPoly(data, p=(1,1,1,1,1,1,1))

    if check == 5:
        answer = x
    else:
        xx = U.nd.zoom(xs, 100)
        yy = U.yPoly(fit, xx)
        ii = N.argmin(yy)
        answer = xx[ii]

    return answer

        

####


def findBestRefZs(ref, sigma=1):
    """
    PSF spread along the Z axis is often tilted in the Y or X axis.
    Thus simple maximum intensity projection may lead to the wrong answer to estimate rotation and magnification.
    On the other hands, taking a single section may also contain out of focus flare from neighboring sections that are tilted.
    Therefore, here sections with high complexity are selected and projected.

    ref: 3D array
    return z idx at the focus
    """
    nz = ref.shape[0]
    if ref.ndim == 2:
        return [0]
    elif nz <= 3:
        return range(nz)

    # Due to the roll up after FFT, the edge sections in Z may contain different information among the channels. Thus these sections are left unused.
    ms = N.zeros((nz -2,), N.float32)
    for z in range(1, nz-1):
        arr = ref[z]
        ms[z-1] = N.prod(U.mmms(arr)[-2:]) # mean * std

    mi,ma,me,st = U.mmms(ms)
    thr = me + st * sigma

    ids = [idx for idx in range(1,nz-1) if ms[idx-1] > thr]
    if not ids:
        ids = range(1,nz-1)

    return ids

def findBestRefZs(ref, sigma=0.5):
    """
    PSF spread along the Z axis is often tilted in the Y or X axis.
    Thus simple maximum intensity projection may lead to the wrong answer to estimate rotation and magnification.
    On the other hands, taking a single section may also contain out of focus flare from neighboring sections that are tilted.
    Therefore, here sections with high complexity are selected and projected.

    An intensity-based method does not work for most (eg. tissue or bright field) images.
    Using variance is not enough for bright field image where the right focus loses contrast.
    Thus here we used sections containing higher frequency.

    ref: 3D array
    return z idx at the focus
    """
    from Priithon.all import F
    nz = ref.shape[0]
    if ref.ndim == 2:
        return [0]
    elif nz <= 3:
        return range(nz)

    # ring array
    ring = F.ringArr(ref.shape[-2:], radius1=ref.shape[-1]//10, radius2=ref.shape[-2]//4, orig=(0,0), wrap=1)
    
    # Due to the roll up after FFT, the edge sections in Z may contain different information among the channels. Thus these sections are left unused.
    ms = N.zeros((nz -2,), N.float32)
    for z in xrange(1, nz-1):
        af = F.rfft(N.ascontiguousarray(ref[z]))
        ar = af * ring[:,:af.shape[-1]]
        ms[z-1] = N.sum(N.abs(ar))
        
        #ms[z-1] = N.prod(U.mmms(arr)[-2:]) # mean * std
    del ring, af, ar

    mi,ma,me,st = U.mmms(ms)
    thr = me + st * sigma

    ids = [idx for idx in range(1,nz-1) if ms[idx-1] > thr]
    if not ids:
        ids = range(1,nz-1)

    return ids


def applyShift(arr, zyxrm, dyx=(0,0)):
    """
    zyxrm: [tz,ty,tx,r,mz,my,mx]
    dyx: shift from the center of rotation & magnification

    return interpolated array
    """
    if N.any(zyxrm[:4]) or N.any(zyxrm[4:] != 1):
        zmagidx = 4

        if arr.ndim == 2:
            zyxrm = N.copy(zyxrm)
            zyxrm[0] = 0
            if len(zyxrm) == 7:
                zyxrm[-3] = 1
            zmagidx = -2

        arr = imgResample.trans3D_affine(arr, zyxrm[:3], zyxrm[3], zyxrm[zmagidx:], dyx)

    return arr

# ------ non linear  ------

def trans3D_affineVertical(img, affine):
    tzyx = (affine[0], 0, 0)
    r = 0
    mag = (affine[4], 1, 1)

    if tzyx[0] or (mag[0] != 1):
        return imgResample.trans3D_affine(img, tzyx=tzyx, r=r, mag=mag)
    else:
        return img

def remapWithAffine(img, mapzyx, affine, interp=2):
    """
    move alongZ then do remapping in 2D
    
    img: 3D image to be remapped
    mapzyx: index array with shape (z,2,y,x) or (2,y,x)
    affine: affine transform parameter as [tz,ty,yx,r,mz,my,mx]
    interp: interpolation order for remap (see imgResample.remap)

    return remapped image
    """
    if mapzyx.ndim == 4 and mapzyx.shape[0] == 1:
        mapzyx = mapzyx[0]
        #print 'mapzyx.ndim', mapzyx.ndim
    if mapzyx.ndim == 4:
        mapzyx = resizeLocal3D(mapzyx, img.shape[-3:])
    elif mapzyx.ndim == 3:
        mapzyx = resizeLocal2D(mapzyx, img.shape[-2:])

    if img.ndim > 2 and img.shape[-3] > 1:
        img = trans3D_affineVertical(img, affine)
    
    ret = N.indices(img.shape[-2:], N.float32)
    tyx = -affine[1:3] # minus to match with the cv coordinate
    r = affine[3]
    mag = affine[5:7]
    ret = imgGeo.affine_index(ret, r, mag, tyx)

    do = N.sum(affine[1:4]) + N.sum(affine[5:] - 1)

    arr2 = N.empty_like(img)
    for z, a in enumerate(img):
        if mapzyx.ndim == 4:
            mapy, mapx = mapzyx[z]
            do += mapzyx[z].sum()
        else:
            mapy, mapx = mapzyx

        if do or mapy.max() or mapx.max():
            arr2[z] = imgResample.remap(a, ret[0]+mapy, ret[1]+mapx)
        else:
            arr2[z] = a
    return arr2


# ------ non linear functions ------

def chopShapeND(shape, npxls=(32,32)):
    """
    shape: original image shape
    npxls: number of pixels to divide ((z,)y,x) or scaler
    
    return list of [[[start, stop],...,], [[start, stop],...,]]
    """
    try:
        if len(npxls) != len(shape):
            raise ValueError, 'length of the list of npxls must be the same as len(shape)'
    except TypeError:
        npxls = [npxls for d in range(len(shape))]
        
    mimas = []
    for d, s in enumerate(shape):
        ndiv = s // npxls[d]
        mms = []
        start = (s - (npxls[d] * ndiv)) // 2
        for n in range(ndiv):
            mms += [[start, start + npxls[d]]]
            start += npxls[d]
        mimas.append([slice(*m) for m in mms])
    return mimas

def chopImage2D(arr, npxls=(32,32)):
    """
    arr: image to be split
    npxls: number of pixels to divide (y,x) or scaler

    return (list_of_slice, list_of_arrs)
    """
    try:
        if len(npxls) != arr.ndim:
            raise ValueError, 'length of the list of npxls must be the same as arr.ndim'
    except TypeError:
        npxls = [npxls for d in range(arr.ndim)]
        
    chopSlcs = chopShapeND(arr.shape, npxls)

    #zslc = chopSlcs[0]
    yslc = chopSlcs[0]
    xslc = chopSlcs[1]

    arrs = []
    slcs = []
    #for zs in zslc:
    for ys in yslc:
        slc = [[ys,xs] for xs in xslc]
        arrs.append([arr[s] for s in slc])
        slcs.append(slc)
    return slcs, arrs

def chopImageND(arr, npxls=(32,32)):
    """
    arr: image to be split
    npxls: number of pixels to divide (y,x) or scaler

    return (list_of_slice, list_of_arrs)
    """
    try:
        if len(npxls) != arr.ndim:
            raise ValueError, 'length of the list of npxls must be the same as arr.ndim'
    except TypeError:
        npxls = [npxls for d in range(arr.ndim)]
        
    chopSlcs = chopShapeND(arr.shape, npxls)

    if len(chopSlcs) == 3:
        zslc = chopSlcs[-3]
    yslc = chopSlcs[-2]
    xslc = chopSlcs[-1]

    arrs = []
    slcs = []

    if len(chopSlcs) == 3:
        for zs in zslc:
            for ys in yslc:
                slc = [[zs,ys,xs] for xs in xslc]
                arrs.append([arr[s] for s in slc])
                slcs.append(slc)
    else:
        for ys in yslc:
            slc = [[ys,xs] for xs in xslc]
            arrs.append([arr[s] for s in slc])
            slcs.append(slc)
            
    return slcs, arrs

def calcPearson(a0, a1):
    a0div = a0 - N.average(a0)
    a1div = a1 - N.average(a1)

    r0 = N.sum(a0div * a1div)
    r1 = (N.sum(a0div**2) * N.sum(a1div**2)) ** 0.5
    return r0 / r1

def xcorNonLinear(arr, ref, npxls=32, threshold=None, phaseContrast=True, cthre=CTHRE, pxlshift_allow=0.5):
    """
    arr: image to be registered
    ref: iamge to find the alignment parameter
    nplxs: number of pixels to divide (y,x) or scaler
    threshold: threshold value to decide if the region is to be cross correlated
    pahseContrast: phase contrast filter in cross correlation

    return (yx_arr, px_analyzed_arr[bool,var,cqual], result_arr)
    """
    try:
        if len(npxls) != len(arr.shape):
            raise ValueError, 'length of the list of npxls must be the same as len(shape)'
    except TypeError:
        npxls = [npxls for d in range(len(arr.shape))]
    
    tslcs, arrs = chopImage2D(arr, npxls)
    rslcs, refs = chopImage2D(ref, npxls)


    if threshold is None:
        variance = (arr.var() + ref.var()) / 2.
        threshold = variance * 0.1

    nsplit = (len(tslcs), len(tslcs[0]))
    yxs = N.zeros((2,)+tuple(nsplit), N.float32)
    regions = N.zeros((3,)+tuple(nsplit), N.float32)
    cs = N.zeros_like(arr)
    for y, ay in enumerate(arrs):
        for x, a in enumerate(ay):
            b = refs[y][x]

            av = imgFilters.cutOutCenter(a, 0.5, interpolate=False)
            bv = imgFilters.cutOutCenter(b, 0.5, interpolate=False)
            var = (N.var(av) + N.var(bv)) / 2. # crop to throw away the tip object
            regions[1,y,x] = var
            if var > threshold:
                yx, c = xcorr.Xcorr(a, b, phaseContrast=phaseContrast)
                cs[tslcs[y][x]] = c
                csd = c[:c.shape[0]//4].std()
                cqual = c.max() - csd
                regions[2,y,x] = cqual
                if cqual >= cthre: # 0.3 is the max
                    if N.abs(yx).max() < pxlshift_allow:
                        #print yx.max()
                        yxs[:,y,x] = yx
                        regions[0,y,x] = 1
                        #else:
                        #print 'yx too large', yx
                del c

    del arrs, refs#, c
    return yxs, regions, cs

def cleanUpNonLinear(yxs, region):
    """
    fill the hold in the array (yxs) with median filtering
    the empty pixels were found using region

    return filled_yxs
    """
    medfilt = N.empty_like(yxs)

    for d, a in enumerate(yxs):
        medfilt[d] = ndimage.filters.median_filter(a, size=5)#3)

    return N.where(region, yxs, medfilt)

def findNonLinearSection(arr_ref_guess, npxl=MIN_PXLS_YX, affine=None, threshold=None, phaseContrast=True, maxErr=0.01):
    arr, ref, guess = arr_ref_guess
    return iterNonLinear(arr, ref, npxl=npxl, affine=affine, initGuess=guess, threshold=threshold, phaseContrast=phaseContrast, maxErr=maxErr)

def iterWindowNonLinear(arr, ref, minwin=MIN_PXLS_YX, affine=None, initGuess=None, threshold=None, phaseContrast=True, niter=10, maxErr=0.01, cthre=CTHRE, echofunc=None):
    """
    return (yx_arr, px_analyzed_arr, result_arr)
    """
    shape = N.array(arr.shape)

    if affine is not None:
        shiftZYX = cutoutAlign.getShift(affine, [0]+list(shape))
        maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
        maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
        shape = N.subtract(shape, (maxcutY*2, maxcutX*2))
        #shape -= (maxcutY*2, maxcutX*2) # casting rule
    win0 = float(min(shape//2))

    series = int(N.sqrt(win0 / minwin)) + 1
    wins = win0 / (2 ** N.arange(series))
    
    for win in wins:
        win = int(win)
        if win % 2:
            win -= 1
        if echofunc:
            echofunc('--current window size: %i' % win)
        yxs, regions, arr2 = iterNonLinear(arr, ref, npxl=win, affine=affine, initGuess=initGuess, threshold=threshold, phaseContrast=phaseContrast, niter=niter, maxErr=maxErr, cthre=cthre, echofunc=echofunc)

        if not regions.max():
            if echofunc:
                echofunc('  no region was found to be good enough')
                break
        else:
            initGuess = yxs

    return yxs, regions, arr2
        
def resizeLocal2D(arr, targetShape):
    """
    arr: mapzyx with shape (2,ny,nx)
    targetShape: (ny, nx)
    return resized 2D array
    """
    shape = N.array(arr.shape)
    tshape = N.array((2,)+tuple(targetShape))
    if N.all(shape == tshape):
        return arr
    elif N.all(shape >= tshape):
        return imgFilters.cutOutCenter(arr, tshape, interpolate=False)
    elif N.all(shape <= tshape):
        return imgFilters.paddingValue(arr, tshape, value=0, smooth=10, interpolate=False)
    else:
        raise NotImplementedError, 'The size of image does not match with the local distortion map'

def resizeLocal3D(arr, targetShape):
    """
    return resized 2D array
    """
    shape = N.array(arr.shape)
    targetShape = tuple(targetShape)
    tshape = N.array(targetShape[:1]+(2,)+targetShape[1:])
    if N.all(shape == tshape):
        return arr
    elif shape[0] < tshape[0]:
        canvas = N.zeros(tshape, arr.dtype.type)
        z0 = (tshape[0] - shape[0])//2
        for z, zt in enumerate(range(z0,shape[0]+z0)):
            canvas[zt] = resizeLocal2D(arr[z], targetShape[1:])
        return canvas
    elif shape[0] > tshape[0]:
        canvas = N.zeros(tshape, arr.dtype.type)
        z0 = (shape[0] - tshape[0])//2
        for zt, z in enumerate(range(z0,tshape[0]+z0)):
            canvas[zt] = resizeLocal2D(arr[z], targetShape[1:])
        return canvas

def paddYX(yx, npxl, shape, maxcutY=0, maxcutX=0):
    """
    """
    yx = ndimage.zoom(yx, zoom=(1,npxl,npxl))

    #-- fill the mergin
    shape = N.array(shape)
    ndiv = shape // npxl
    start = (shape - (npxl * ndiv)) // 2
    stop = start + (npxl * ndiv)

    zeros = N.zeros((2,)+tuple(shape), N.float32)
    zeros[:,start[0]+maxcutY:start[0]+yx.shape[1]+maxcutY,start[1]+maxcutX:start[1]+yx.shape[2]+maxcutX] += yx

    for d in xrange(2):
        # left
        for x in xrange(int(start[1]+maxcutX)):
            zeros[d,:start[0]+maxcutY,x] += yx[d,0,0]
            zeros[d,start[0]+maxcutY:start[0]+maxcutY+yx.shape[1],x] += yx[d,:,0]
            zeros[d,start[0]+maxcutY+yx.shape[1]:,x] += yx[d,-1,0]
        # right
        for x in xrange(int(start[1]+maxcutX+yx.shape[2]),int(zeros.shape[-1])):
            zeros[d,:start[0]+maxcutY,x] += yx[d,0,-1]
            zeros[d,start[0]+maxcutY:start[0]+maxcutY+yx.shape[1],x] += yx[d,:,-1]
            zeros[d,start[0]+maxcutY+yx.shape[1]:,x] += yx[d,-1,-1]
        # bottom
        for y in xrange(int(start[0]+maxcutY)):
            zeros[d,y,:start[1]+maxcutX] += yx[d,0,0]
            zeros[d,y,:start[1]+maxcutX] /= 2.
            zeros[d,y,start[1]+maxcutX:start[1]+maxcutX+yx.shape[2]] += yx[d,0,:]
            zeros[d,y,start[1]+maxcutX+yx.shape[2]:] += yx[d,0,-1]
            zeros[d,y,start[1]+maxcutX+yx.shape[2]:] /= 2.
        # top
        for y in xrange(int(start[0]+maxcutY+yx.shape[1]),int(zeros.shape[-2])):
            zeros[d,y,:start[1]+maxcutX] += yx[d,-1,0]
            zeros[d,y,:start[1]+maxcutX] /= 2.
            zeros[d,y,start[1]+maxcutX:start[1]+maxcutX+yx.shape[2]] += yx[d,-1,:]
            zeros[d,y,start[1]+maxcutX+yx.shape[2]:] += yx[d,-1,-1]
            zeros[d,y,start[1]+maxcutX+yx.shape[2]:] /= 2.

    return zeros


def iterNonLinear(arr, ref, npxl=MIN_PXLS_YX, affine=None, initGuess=None, threshold=None, phaseContrast=True, niter=10, maxErr=0.01, cthre=CTHRE, echofunc=None):
    """
    arr: image to be registered
    ref: image to find the alignment parameter
    nplx: number of pixels to divide, a scaler
    initGuess: initGuess of the nonlinear parameter
    affine: affine transform parameter as [tz,ty,yx,r,mz,my,mx]
    threshold: threshold value to decide if the region is to be cross correlated
    pahseContrast: phase contrast filter in cross correlation
    niter: maximum number of iteration
    maxErr: minimum error in pixel to terminate iterations

    return (yx_arr, px_analyzed_arr)
    """
    shape = arr.shape
    last_shape = None
    
    #-- prepare output array
    ret = N.indices(arr.shape, N.float32) # hold affine + mapyx + initial_guess
    yxs = N.zeros_like(ret) # hold mapyx + initial_guess
    
    maxcutY = maxcutX = 0
    if affine is not None:
        tyx = -affine[1:3] # minus to match cv coordinate
        r = affine[3]
        mag = affine[5:7]
        ret = imgGeo.affine_index(ret, r, mag, tyx)

        # cut out
        shiftZYX = cutoutAlign.getShift(affine, [0]+list(shape))
        maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
        maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
        slc = [slice(maxcutY, shape[0]-maxcutY),
               slice(maxcutX, shape[1]-maxcutX)]

    if initGuess is not None:
        ret += initGuess
        yxs += initGuess
        
    for i in range(niter):
        #-- first apply the initial guess
        if i or affine is not None:
            arr2 = imgResample.remap(arr, ret[0], ret[1])

            if affine is not None:
                arr2 = arr2[slc]
                ref2 = ref[slc]
            else:
                ref2 = ref
        else:
            arr2 = arr
            ref2 = ref

        #-- calculate local cross corelation
        if threshold is None:
            variance = (arr2.var() + ref2.var()) / 2.
            threshold = variance * 0.1
        yx, region, cs = xcorNonLinear(arr2, ref2, npxl, threshold, phaseContrast, cthre)
        try:
            regions
        except NameError:
            regions = N.zeros(region[0].shape, N.uint16)
        #regions += region[0]
        regions = N.add(regions, region[0]) # DEBUG: ufunc casting rule
        if not region[0].sum():
            if N.any(region[1] > threshold):
                if echofunc:
                    echofunc('variance high enough (%.1f > %.1f) but quality of CC too low (%.3f)' % (region[1].max(), threshold, region[2].max()))
            else:
                if echofunc:
                    echofunc('variance too low (%.1f < %.1f)' % (region[1].max(), threshold))
            break

        npxls = region[0].sum()
        err = N.abs(yx).sum() / float(npxls)
        rgn = N.nonzero(region[0].ravel())[0]
        ccq = region[2].ravel()[rgn]
        if echofunc:
            echofunc('    iteration %i: npxls=%i, min_cc=%.4f, mean_pxl_shift=%.4f' % (i, npxls, ccq.min(), err))

        #-- smoothly zoom up the non-linear alignment parameter
        yxc = yx#cleanUpNonLinear(yx, region[0])

        yx = paddYX(yxc, npxl, arr.shape, maxcutY, maxcutX)
        
        #-- combine result
        ret += yx
        yxs += yx

        if err < maxErr:
            break

        # although returning yxc is more interesting, it does not hold information from initguess
        # thus only the zoomed and padded information can be returned...

    return yxs, regions, N.array((ref2, arr2, cs))

## ---- remove outside of significant signals -----

def iterNonLinear(arr, ref, npxl=MIN_PXLS_YX, affine=None, initGuess=None, threshold=None, phaseContrast=True, niter=10, maxErr=0.01, cthre=CTHRE, echofunc=None):
    """
    arr: image to be registered
    ref: image to find the alignment parameter
    nplx: number of pixels to divide, a scaler
    initGuess: initGuess of the nonlinear parameter
    affine: affine transform parameter as [tz,ty,yx,r,mz,my,mx]
    threshold: threshold value to decide if the region is to be cross correlated
    pahseContrast: phase contrast filter in cross correlation
    niter: maximum number of iteration
    maxErr: minimum error in pixel to terminate iterations

    return (yx_arr, px_analyzed_arr)
    """
    shape = arr.shape
    last_shape = None
    
    #-- prepare output array
    ret = N.indices(arr.shape, N.float32) # hold affine + mapyx + initial_guess
    yxs = N.zeros_like(ret) # hold mapyx + initial_guess

    # to return something similar to yxc in case of no iteration was done.
    tslcs, arrs = chopImage2D(arr, npxl)
    nsplit = (len(tslcs), len(tslcs[0]))
    yxc = N.zeros((2,)+tuple(nsplit), N.float32)

    maxcutY = maxcutX = 0
    if affine is not None:
        tyx = -affine[1:3] # minus to match cv coordinate
        r = affine[3]
        mag = affine[5:7]
        ret = imgGeo.affine_index(ret, r, mag, tyx)

        # cut out
        shiftZYX = cutoutAlign.getShift(affine, [0]+list(shape))
        maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
        maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
        slc = [slice(maxcutY, shape[0]-maxcutY),
               slice(maxcutX, shape[1]-maxcutX)]

    if initGuess is not None:
        ret += initGuess
        yxs += initGuess
        
    for i in range(niter):
        #-- first apply the initial guess
        if i or affine is not None:
            arr2 = imgResample.remap(arr, ret[0], ret[1])

            if affine is not None:
                arr2 = arr2[slc]
                ref2 = ref[slc]
            else:
                ref2 = ref
        else:
            arr2 = arr
            ref2 = ref

        #-- calculate local cross corelation
        if threshold is None:
            variance = (arr2.var() + ref2.var()) / 2.
            threshold = variance * 0.1
        yx, region, cs = xcorNonLinear(arr2, ref2, npxl, threshold, phaseContrast, cthre)
        try:
            regions
        except NameError:
            regions = N.zeros(region[0].shape, N.uint16)
        #regions += region[0]
        regions = N.add(regions, region[0]) # DEBUG: ufunc casting rule
        if not region[0].sum():
            if N.any(region[1] > threshold):
                if echofunc:
                    echofunc('variance high enough (%.1f > %.1f) but quality of CC too low (%.3f)' % (region[1].max(), threshold, region[2].max()))
            else:
                if echofunc:
                    echofunc('variance too low (%.1f < %.1f)' % (region[1].max(), threshold))
            break

        npxls = region[0].sum()
        err = N.abs(yx).sum() / float(npxls)
        rgn = N.nonzero(region[0].ravel())[0]
        ccq = region[2].ravel()[rgn]
        if echofunc:
            echofunc('(nplxs: %i) iteration %i: num_regions=%i, min_cc=%.4f, pxl_shift_mean=%.4f, max=%.4f' % (npxl, i, npxls, ccq.min(), err, N.abs(yx).max()))

        #-- smoothly zoom up the non-linear alignment parameter
        yxc = yx#cleanUpNonLinear(yx, region[0])

        yx = paddYX(yxc, npxl, arr.shape, maxcutY, maxcutX)
        
        #-- combine result
        ret += yx
        yxs += yx

        if err < maxErr:
            break

        # although returning yxc is more interesting, it does not hold information from initguess
        # thus only the zoomed and padded information can be returned...

    return yxc, regions, N.array((ref2, arr2, cs))

def iterWindowNonLinear(arr, ref, minwin=MIN_PXLS_YX, affine=None, initGuess=None, threshold=None, phaseContrast=True, niter=10, maxErr=0.01, cthre=CTHRE, echofunc=None):
    """
    return (yx_arr, px_analyzed_arr, result_arr)
    """
    shape = N.array(arr.shape)

    maxcutY = maxcutX = 0
    if affine is not None:
        shiftZYX = cutoutAlign.getShift(affine, [0]+list(shape))
        maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
        maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
        shape = N.subtract(shape, (maxcutY*2, maxcutX*2))
        #shape -= (maxcutY*2, maxcutX*2) # casting rule
    win0 = float(min(shape//2))

    series = int(N.sqrt(win0 / minwin)) + 1
    wins0 = win0 / (2 ** N.arange(series))
    wins = []
    for win in wins0:
        win = int(win)
        if win % 2:
            win -= 1
        wins.append(win)

    currentGuess = initGuess
    yx_acc = N.zeros((2,) + tuple(shape//wins[-1]), N.float32) #2**series, 2**series), N.float32)
    
    for i, win in enumerate(wins):
        old="""
        win = int(win)
        if win % 2:
            win -= 1"""
        if echofunc:
            echofunc('--current window size: %i' % win)
        yxc, regions, arr2 = iterNonLinear(arr, ref, npxl=win, affine=affine, initGuess=currentGuess, threshold=threshold, phaseContrast=phaseContrast, niter=niter, maxErr=maxErr, cthre=cthre, echofunc=echofunc)

        print 'shape', yxc.shape, yx_acc.shape, arr.shape
        #for d in xrange(2):
        #    yx_acc[d] += U.nd.zoom(yxc[d], zoom=(2**(series-1-i)))
        yxz = paddYX(yxc, 2**(series-1-i), yx_acc.shape[-2:])#U.nd.zoom(yxc, zoom=N.divide(yx_acc.shape, yxc.shape))#(1, 2**(series-1-i), 2**(series-1-i)))
        yx_acc += yxz

        if currentGuess is None:
            currentGuess = paddYX(yxc, win, arr.shape, maxcutY, maxcutX)
        else:
            currentGuess += paddYX(yxc, win, arr.shape, maxcutY, maxcutX)

        rmax = regions.max()
        if not rmax:
            #print 'no regions was good enough, rmax: %.2f' % rmax
            if echofunc:
                echofunc('  no region was found to be good enough')
            break
        else:
            print 'rmax: %.2f, -- continue' % rmax

    # throw away regions with low contrast
    if rmax:
        thre = N.where(regions == rmax, 1, 0)
        yx_acc[:] *= thre#N.where(regions == rmax, 1, 0)
        yxs = paddYX(yx_acc, wins[-1], arr.shape, maxcutY, maxcutX)
    else:
        yxs = N.zeros((2,)+arr.shape, N.float32)

    if initGuess is not None:
        yxs += initGuess
        
    return yxs, regions, arr2#, thre, yx_acc


# this does not work and possibly even slower
def xcorNonLinear_para(arr, ref, npxls=32, threshold=None, phaseContrast=True, cthre=CTHRE):
    """
    arr: image to be registered
    ref: iamge to find the alignment parameter
    nplxs: number of pixels to divide (y,x) or scaler
    threshold: threshold value to decide if the region is to be cross correlated
    pahseContrast: phase contrast filter in cross correlation

    return (yx_arr, px_analyzed_arr[bool,var,cqual], result_arr)
    """
    from PriCommon import ppro26
    
    try:
        if len(npxls) != len(arr.shape):
            raise ValueError, 'length of the list of npxls must be the same as len(shape)'
    except TypeError:
        npxls = [npxls for d in range(len(arr.shape))]
    
    tslcs, arrs = chopImage2D(arr, npxls)
    rslcs, refs = chopImage2D(ref, npxls)


    if threshold is None:
        variance = (arr.var() + ref.var()) / 2.
        threshold = variance * 0.1

    nsplit = (len(tslcs), len(tslcs[0]))
    yxs = N.zeros((2,)+tuple(nsplit), N.float32)
    regions = N.zeros((3,)+tuple(nsplit), N.float32)
    cs = N.zeros_like(arr)

    abyxs = []
    for y, ay in enumerate(arrs):
        for x, a in enumerate(ay):
            b = refs[y][x]
            abyxs.append((a, b, y, x))
            old="""

            av = imgFilters.cutOutCenter(a, 0.5, interpolate=False)
            bv = imgFilters.cutOutCenter(b, 0.5, interpolate=False)
            var = (N.var(av) + N.var(bv)) / 2. # crop to throw away the tip object
            regions[1,y,x] = var
            if var > threshold:
                yx, c = xcorr.Xcorr(a, b, phaseContrast=phaseContrast)
                cs[tslcs[y][x]] = c
                csd = c[:c.shape[0]//4].std()
                cqual = c.max() - csd
                regions[2,y,x] = cqual
                if cqual >= cthre: # 0.3 is the max
                    yxs[:,y,x] = yx
                    regions[0,y,x] = 1
                del c"""


    if 0:#ppro26.NCPU > 1:
        print 'multi'
        ccy = ppro26.pmap(_xcorNonLinear, abyxs, threshold=threshold, phaseContrast=phaseContrast)
    else:
        print 'single'
        ccy = [_xcorNonLinear(ab, threshold=threshold, phaseContrast=phaseContrast) for ab in abyxs]

    for c, var, cqual, yx, y, x in ccy:
        regions[1,y,x] = var
        if var > threshold:
            regions[2,y,x] = cqual
            if cqual >= cthre:
                yxs[:,y,x] = yx
                regions[0,y,x] = 1
                cs[tslcs[y][x]] = c
            del c

    del arrs, refs#, c
    return yxs, regions, cs

def _xcorNonLinear(abyx, threshold, phaseContrast):
    a, b, y, x = abyx
    av = imgFilters.cutOutCenter(a, 0.5, interpolate=False)
    bv = imgFilters.cutOutCenter(b, 0.5, interpolate=False)
    var = (N.var(av) + N.var(bv)) / 2. # crop to throw away the tip object
    #regions[1,y,x] = var
    if var > threshold:
        yx, c = xcorr.Xcorr(a, b, phaseContrast=phaseContrast)
        #cs[tslcs[y][x]] = c
        csd = c[:c.shape[0]//4].std()
        cqual = c.max() - csd
        #regions[2,y,x] = cqual
        #if cqual >= cthre: # 0.3 is the max
            #yxs[:,y,x] = yx
            #regions[0,y,x] = 1
            # del c
    else:
        c = None
        cqual = 0
        yx = 0
    return c, var, cqual, yx, y, x

# old func
def iterNonLinear_old(arr, ref, npxl=32, affine=None, initGuess=None, threshold=None, phaseContrast=True, niter=10, maxErr=0.01, cthre=CTHRE, echofunc=None):
    """
    arr: image to be registered
    ref: image to find the alignment parameter
    nplx: number of pixels to divide, a scaler
    initGuess: initGuess of the nonlinear parameter
    affine: affine transform parameter as [tz,ty,yx,r,mz,my,mx]
    threshold: threshold value to decide if the region is to be cross correlated
    pahseContrast: phase contrast filter in cross correlation
    niter: maximum number of iteration
    maxErr: minimum error in pixel to terminate iterations

    return (yx_arr, px_analyzed_arr)
    """
    arr = arr.astype(N.float32)
    ref = arr.astype(N.float32)
    
    shape = arr.shape
    last_shape = None
    
    #-- prepare output array
    ret = N.indices(arr.shape, N.float32) # hold affine + mapyx + initial_guess
    yxs = N.zeros_like(ret) # hold mapyx + initial_guess
    
    maxcutY = maxcutX = 0
    if affine is not None:
        tyx = -affine[1:3] # minus to match cv coordinate
        r = affine[3]
        mag = affine[5:7]
        ret = imgGeo.affine_index(ret, r, mag, tyx)

        # cut out
        shiftZYX = cutoutAlign.getShift(affine, [0]+list(shape))
        maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
        maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
        slc = [slice(maxcutY, shape[0]-maxcutY),
               slice(maxcutX, shape[1]-maxcutX)]

    if initGuess is not None:
        ret += initGuess
        yxs += initGuess
        
    for i in range(niter):
        #-- first apply the initial guess
        if i or affine is not None:
            arr2 = imgResample.remap(arr, ret[0], ret[1])

            if affine is not None:
                arr2 = arr2[slc]
                ref2 = ref[slc]
            else:
                ref2 = ref
        else:
            arr2 = arr
            ref2 = ref

        #-- calculate local cross corelation
        if threshold is None:
            variance = (arr2.var() + ref2.var()) / 2.
            threshold = variance * 0.1
        yx, region, cs = xcorNonLinear(arr2, ref2, npxl, threshold, phaseContrast, cthre)
        try:
            regions
        except NameError:
            regions = N.zeros(region[0].shape, N.uint16)
        #regions += region[0]
        regions = N.add(regions, region[0]) # DEBUG: ufunc casting rule
        if not region[0].sum():
            if N.any(region[1] > threshold):
                if echofunc:
                    echofunc('variance high enough (%.1f > %.1f) but quality of CC too low (%.3f)' % (region[1].max(), threshold, region[2].max()))
            else:
                if echofunc:
                    echofunc('variance too low (%.1f < %.1f)' % (region[1].max(), threshold))
            break

        npxls = region[0].sum()
        err = N.abs(yx).sum() / float(npxls)
        rgn = N.nonzero(region[0].ravel())[0]
        ccq = region[2].ravel()[rgn]
        if echofunc:
            echofunc('iteration %i: num_regions=%i, min_cc=%.4f, pxl_shift_mean=%.4f, max=%.4f' % (i, npxls, ccq.min(), err, N.abs(yx).max()))

        #-- smoothly zoom up the non-linear alignment parameter
        yxc = yx#cleanUpNonLinear(yx, region[0])

        yx = paddYX(yxc, npxl, arr.shape, maxcutY, maxcutX)
        
        #-- combine result
        ret += yx
        yxs += yx

        if err < maxErr:
            break

        # although returning yxc is more interesting, it does not hold information from initguess
        # thus only the zoomed and padded information can be returned...

    return yxs, regions, N.array((ref2, arr2, cs))


