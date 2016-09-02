
import numpy as N
from PriCommon import imgFilters, xcorr

CTHRE=0.065
MIN_PXLS_YX = 30
MIN_PXLS_Z = MIN_PXLS_YX // 3 # resolution is about 3 times lower in Z

def canBe3DNonLinear(nz, zmin=MIN_PXLS_Z):
    """
    return True if possible to do 3D non linear
    """
    return nz > (zmin * 2)

def makeShape3D(shape, 

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

def xcorNonLinear(arr, ref, npxls=32, threshold=None, phaseContrast=True, cthre=CTHRE):
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
    
    tslcs, arrs = chopImageND(arr, npxls)
    rslcs, refs = chopImageND(ref, npxls)


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
                    yxs[:,y,x] = yx
                    regions[0,y,x] = 1
                del c

    del arrs, refs#, c
    return yxs, regions, cs

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
            if echofunc:
                echofunc('  no region was found to be good enough')
                break

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
