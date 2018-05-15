from __future__ import print_function
import numpy as N

try:
    from Priithon.all import P, U, Mrc

    from PriCommon import xcorr, imgGeo
    import imgio
except ImportError:
    from Chromagnon.Priithon.all import P, U, Mrc
    from Chromagnon.PriCommon import xcorr, imgGeo
    from Chromagnon import imgio

from . import aligner, alignfuncs

import os, tempfile

def prepImg4AffineZ(fn, w=None, phaseContrast=True):
    an = aligner.Chromagnon(fn)
    an.findBestChannel()
    an.setRefImg()

    ref = an.img.get3DArr(w=an.refwave, t=0)
    prefyx = U.project(ref)
    #prefyz = U.project(ref, -1)
    
    if w is None:
        waves = list(range(an.img.nw))
        waves.remove(an.refwave)
        w = waves[0]
    img = an.img.get3DArr(w=w, t=0)

    pimgyx = U.project(img)
    #pimgyz = U.project(img, -1)

    #yz, c = xcorr.Xcorr(prefyz, pimgyz, phaseContrast=phaseContrast)
    yx, c = xcorr.Xcorr(prefyx, pimgyx, phaseContrast=phaseContrast)

    xs = N.round_(an.refxs-yx[1]).astype(N.int)
    if xs.max() >= an.img.nx:
        xsbool = (xs < an.img.nx)
        xsinds = N.nonzero(xsbool)[0]
        xs = xs[xsinds]
     
    imgyz = alignfuncs.prep2D(img.T, zs=xs)

    #return an.refyz, imgyz

    a1234 = alignfuncs.chopImg(an.refyz)
    b1234 = alignfuncs.chopImg(imgyz)

    ab = list(zip(a1234, b1234))

    yxcs = [xcorr.Xcorr(a, b, phaseContrast=phaseContrast) for a, b in ab]
    yxs = [yx for yx, c in yxcs]
    cqs = [c.max() - c[c.shape[0]//4].std() for yx, c in yxcs]

    return ab, cqs, [c for yx, c in yxcs], yxs, an    

def prepImg4Affine(fn, w=None, phaseContrast=True):
    an = aligner.Chromagnon(fn)
    an.findBestChannel()
    an.setRefImg()

    ref = an.img.get3DArr(w=an.refwave, t=0)
    prefyx = N.max(ref, axis=0)
    
    if w is None:
        waves = list(range(an.img.nw))
        waves.remove(an.refwave)
        w = waves[0]
    img = an.img.get3DArr(w=w, t=0)
    pimgyx = N.max(img, axis=0)

    yx, c = xcorr.Xcorr(prefyx, pimgyx, phaseContrast=phaseContrast)
    
    xs = N.round_(an.refxs-yx[1]).astype(N.int)
    if xs.max() >= an.img.nx:
        xsbool = (xs < an.img.nx)
        xsinds = N.nonzero(xsbool)[0]
        xs = xs[xsinds]
        
    imgyz = alignfuncs.prep2D(img.T, zs=xs)

    yz = alignfuncs.iterationXcor(imgyz, an.refyz, maxErr=an.maxErrZ, niter=an.niter, phaseContrast=an.phaseContrast, echofunc=an.echofunc)

    zs = N.round_(an.refzs-yz[1]).astype(N.int)
    if zs.max() >= an.img.nz:
        zsbool = (zs < an.img.nz)
        zsinds = N.nonzero(zsbool)[0]
        zs = zs[zsinds]

    imgyx = alignfuncs.prep2D(img, zs=zs)

    a1234 = alignfuncs.chopImg(imgyx)
    b1234 = alignfuncs.chopImg(an.refyx)

    ab = list(zip(a1234, b1234))

    yxcs = [xcorr.Xcorr(a, b, phaseContrast=phaseContrast) for a, b in ab]
    yxs = [yx for yx, c in yxcs]
    cqs = [c.max() - c[c.shape[0]//4].std() for yx, c in yxcs]
    
    return ab, cqs, [c for yx, c in yxcs], yxs, an

def getAffineyx(arr, ref):
    a1234 = alignfuncs.chopImg(arr)
    b1234 = alignfuncs.chopImg(ref)

    ab = list(zip(a1234, b1234))
    
    yxcs = [xcorr.Xcorr(a, b) for a, b in ab]
    yxs = [yx for yx, c in yxcs]

    return yxs

def getRotVectors(yxs, center=(200,200)):
    asiny1 = (yxs[0][0] - yxs[1][0]) / 2.
    asiny2 = (yxs[3][0] - yxs[2][0]) / 2.

    asiny = (asiny1 + asiny2) / 2.

    asinx1 = (yxs[3][1] - yxs[0][1]) / 2.
    asinx2 = (yxs[2][1] - yxs[1][1]) / 2.

    asinx = -(asinx1 + asinx2) / 2.

    theta = getTheta(asiny, asinx, center)
    
    return asiny1, asiny2, asiny, asinx1, asinx2, asinx, theta

def getTheta(asiny, asinx, center=(200,200)):
    center = N.array(center, N.float32)
    center2 = center/2.
    cdeg = N.degrees(N.arctan2(*center2))
    ryx = center2 + (asiny, asinx)
    return N.degrees(N.arctan2(*ryx)) - cdeg
    

def getRotFromImg(a, b, windowSize=(400,400)):
    from PriCommon import imgFilters
    ac = imgFilters.cutOutCenter(a, windowSize, interpolate=False)
    bc = imgFilters.cutOutCenter(b, windowSize, interpolate=False)

    yxs = getAffineyx(ac, bc)

    return getRotVectors(yxs, N.divide(windowSize, 2))

def prepareImg(fn, chrom=None, aligned=False, z=None, w=None):
    """
    return (arr, ref), an
    """
    an = aligner.Chromagnon(fn)
    an.findBestChannel()
    if chrom:
        an.loadParm(chrom)
        an.setRefImg()
    else:
        an.findAlignParamWave()
        an.saveParm()

    if z is None:
        ref = an.refyx
    else:
        try:
            len(z)
            ref = N.max(an.get3DArr(w=an.refwave, zs=z), axis=0)
        except TypeError:
            ref = an.img.getArr(w=an.refwave, z=z)

    if w is None:
        waves = list(range(an.img.nw))
        waves.remove(an.refwave)
        w = waves[0]
    if aligned:
        an.mapyx = N.zeros((an.img.nt, an.img.nw, 2, an.img.ny, an.img.nx), N.float32)
        arr3D = an.get3DArrayAligned(w=w)
        if z is None:
            arr = alignfuncs.prep2D(arr3D, zs=an.refzs)
        else:
            arr = arr3D[z]
            if arr.ndim == 3:
                arr = N.max(arr, axis=0)
    elif z is None:
        arr3D = an.get3DArr(w=w)
        zs = N.round_(an.refzs-an.alignParms[0,w,0]).astype(N.int)
        arr = alignfuncs.prep2D(arr3D, zs=zs)
    else:
        #z0 = int(round(z - an.alignParms[0,w,0]))
        try:
            len(z)
            z0 = N.round_(N.array(z) - an.alignParms[0,w,0])
            arr = N.max(an.get3DArr(w=w, zs=z0.astype(N.int)), axis=0)
        except TypeError:
            z0 = int(round(z - an.alignParms[0,w,0]))
            arr = an.img.getArr(w=w, z=z0)
        
    an.setRegionCutOut()
    arr = arr[an.cropSlice[-2:]]#[Ellipsis]+an._yxSlice]
    ref = ref[an.cropSlice[-2:]]#[Ellipsis]+an._yxSlice]
    an.close()

    return N.array((arr, ref)), an

def prepareImgSimple(fn, w=None):
    an = aligner.Chromagnon(fn)
    an.findBestChannel()
    an.setRefImg()
    if w is None:
        waves = list(range(an.img.nw))
        waves.remove(an.refwave)
        w = waves[0]
        print('wave: %i with refwave %i' % (w, an.refwave))
    arr3D = an.get3DArr(w=w)
    arr = alignfuncs.prep2D(arr3D, zs=an.refzs)

    return arr, an.refyx
        

def testNonlinear(arr, ref, npxls=32, phaseContrast=True, centerDot=True):
    """
    fn = '***.dv'
    chrom = '***.csv'
    ar, an = prepareImg(fn, chrom=chrom, aligned=True)
    yxs, abc, qual, yxq = testNonLinear(*ar)
    """
    try:
        if len(npxls) != len(arr.shape):
            raise ValueError('length of the list of npxls must be the same as len(shape)')
    except TypeError:
        npxls = [npxls for d in range(len(arr.shape))]

    arr = arr.astype(N.float32)
    ref = ref.astype(N.float32)
        
    tslcs, arrs = alignfuncs.chopImage2D(arr, npxls)
    rslcs, refs = alignfuncs.chopImage2D(ref, npxls)

    nsplit = (len(tslcs), len(tslcs[0]))
    yxs = N.zeros((2,)+tuple(nsplit), N.float32)

    quality = N.zeros((4,)+nsplit, N.float32)

    cs = N.zeros_like(arr)

    variance = (arr.var() + ref.var()) / 2.

    agrid = arr.copy()
    bgrid = ref.copy()

    ame = agrid.max() / 2.
    bme = bgrid.max() / 2.

    for y, yslc in enumerate(tslcs):
        agrid[(yslc[0][0].start-1):(yslc[0][0].start+1),:] = ame
        bgrid[(yslc[0][0].start-1):(yslc[0][0].start+1),:] = bme
    agrid[(yslc[0][0].stop-1):(yslc[0][0].stop+1),:] = ame
    bgrid[(yslc[0][0].stop-1):(yslc[0][0].stop+1),:] = bme

    for x, slc in enumerate(yslc):
        agrid[:,(slc[1].start-1):(slc[1].start+1)] = ame
        bgrid[:,(slc[1].start-1):(slc[1].start+1)] = bme
    agrid[:,(slc[1].stop-1):(slc[1].stop+1)] = ame
    bgrid[:,(slc[1].stop-1):(slc[1].stop+1)] = bme  

    for y, ay in enumerate(arrs):
        for x, a in enumerate(ay):
            b = refs[y][x]
            slc = tslcs[y][x]

            s, v, yx, c = xcorr.Xcorr(a, b, phaseContrast=phaseContrast, ret=2)
            yxs[:,y,x] = yx
            cs[slc] = c
            quality[0,y,x] = ((N.var(a[2:-2,2:-2]) + N.var(b[2:-2,2:-2])) / 2.) / variance
            pea = alignfuncs.calcPearson(a, b)
            quality[1,y,x] = pea
            #cme = c[:c.shape[0]//4].mean()
            csd = c[:c.shape[0]//4].std()
            quality[2,y,x] = c.max() - csd#me
            quality[3,y,x] = N.mean(s)#.mean()#c.max() - csd

    agrid = normalize(agrid) * 0.3
    bgrid = normalize(bgrid) * 0.3
    #cs = normalize(cs)
    
    cme = cs.max() / 2.
    for y, yslc in enumerate(tslcs):
        cs[(yslc[0][0].start-1):(yslc[0][0].start+1),:] = cme
        if centerDot:
            cs[(yslc[0][0].start-1+npxls[0]//2):(yslc[0][0].start+1+npxls[0]//2),::10] = cme
    cs[(yslc[0][0].stop-1):(yslc[0][0].stop+1),:] = cme

    for x, slc in enumerate(yslc):
        cs[:,(slc[1].start-1):(slc[1].start+1)] = cme
        if centerDot:
            cs[::10,(slc[1].start-1+npxls[1]//2):(slc[1].start+1+npxls[1]//2)] = cme
    cs[:,(slc[1].stop-1):(slc[1].stop+1)] = cme
    
    v = N.where(quality[0] > 0.1, 1, 0)
    q = N.where(quality[2] > 0.065, 1, 0)
    yxq = yxs * v * q
    return yxs, N.array((agrid, bgrid, cs)), quality, N.abs(yxq)

def normalize(arr):
    arr -= arr.min()
    arr /= arr.max()
    return arr

def testCorrelation(arr, win=64):
    from Priithon.all import U
    half = win/2.
    arr = arr.copy()
    for i in range(10):
        v, z, y, x = U.findMax(arr)
        if y-half >= 0 and y+half < arr.shape[0] and x-half >= 0 and x+half < arr.shape[1]:
            a = arr[y-half:y+half,x-half:x+half]
            break
        else:
            arr[y,x] = 0
    b = a.copy()
    yx, c = xcorr.Xcorr(a, b, phaseContrast=True)
    cme = c[:c.shape[0]//4].mean()
    return c.max() - cme

def beads_analyzeBeads(fn, thre_sigma=1., beads_sigma_max=3, refwave=0, nbeads=60, win=5, maxdist=100, maxrefdist=5, edge=30, zyxs=None):#0.6, maxrefdist=0.005):
    """
    maxdist: nm
    maxrefdist: nm

    return dic, zyx
    """
    from PriCommon import imgFilters, imgFit, imgGeo, microscope
    from Priithon.all import Y
    h = imgio.Reader(fn)#mrcIO.MrcReader(fn)
    if refwave >= h.nw:
        raise ValueError('reference wave does not exists')
    shape = h.hdr.Num[::-1].copy()
    shape[0] /= (h.hdr.NumTimes * h.hdr.NumWaves)
    pzyx = h.hdr.d[::-1]
    mst1 = h.hdr.mst[::-1]

    NA = 1.35
    difflimitYX = microscope.resolution(NA, h.hdr.wave[refwave])/1000.
    difflimit = N.array([difflimitYX*3, difflimitYX, difflimitYX]) / pzyx
    print('diffraction limit (px) is:', difflimit)
    simres = difflimit #/ 1.5#2.

    arr = h.get3DArr(w=refwave).copy()
    if edge:
        arr = arr[:,edge//2:-edge,edge//2:-edge]
    ndim = arr.ndim
    me = arr.mean()
    sd = arr.std()
    thre = me + sd * thre_sigma
    sigma = 1.5

    done = N.zeros(arr.shape, N.bool)

    pzyx *= 1000

    if zyxs is None:
        mst0 = h.hdr.mst[::-1]
        zyxs = []
        #found = []
        sigmas = []
        i = 0
        pmax = 0
        failed = 0
        while i < nbeads:
            Y.refresh()
            amax,z,y,x = U.findMax(arr)
            zyx = N.array((z,y,x), N.float32)
            #found.append(zyx)
            zyx0 = N.where(zyx > simres, zyx - simres, 0).astype(N.int)
            zyx1 = N.where(zyx + simres < shape, zyx + simres + 1, shape).astype(N.int)
            rmslice = [slice(*zyx) for zyx in zip(zyx0, zyx1)]

            if failed > nbeads:
                #raise RuntimeError
                print('no more beads found...')
                break
            elif amax == pmax:
                arr[rmslice] = me
            elif N.any(done[rmslice]):
                arr[rmslice] = me
                done[rmslice] = 1
                print('Nearby region already examined')
                failed += 1
                continue
            elif amax > thre:
                # Gaussian fitting
                try:
                    ret, check = imgFit.fitGaussianND(arr, [z,y,x][-ndim:], sigma, win)
                except IndexError: # too close to the edge
                    arr[rmslice] = me
                    done[rmslice] = 1
                    print('Index Error, too close to the edge', z,y,x)
                    failed += 1
                    continue
                if check == 5:
                    arr[rmslice] = me
                    done[rmslice] = 1
                    print('fit failed', z,y,x)
                    failed += 1
                    continue

                # retreive results
                v = ret[1]
                zyx = ret[2:2+ndim]
                sigma = ret[2+ndim:2+ndim*2]
                if any(sigma) < 1:
                    sigma = N.where(sigma < 1, 1, sigma)

                # check if the result is inside the image
                if N.any(zyx < 0) or N.any(zyx > (shape)):
                    print('fitting results outside the image', zyx, z,y,x, rmslice)
                    arr[rmslice] = me
                    done[rmslice] = 1
                    failed += 1
                    continue # too close to the edge

                # remove the point
                cop = arr.copy()
                imgFilters.mask_gaussianND(arr, zyx, v, sigma)

                # check if the bead is too close to the exisisting ones
                skipped= """
                if len(found):#zyxs):
                    close = imgGeo.closeEnough(zyx, found, difflimit*2)#zyxs, difflimit*2)
                    if N.any(close):
                        if len(zyxs):
                            close = imgGeo.closeEnough(zyx, zyxs, difflimit*2)
                            if N.any(close):
                                idx = close.argmax()
                                already = zyxs.pop(idx)
                                #print 'too close', zyx, already
                        print 'found in the previous list'
                        continue"""

                # remove beads too close to the edge
                if N.any(zyx < 2) or N.any(zyx > (shape-2)):
                    print('too close to the edge', zyx)
                    if N.any(arr[rmslice] > thre):
                        arr[rmslice] = me
                    done[rmslice] = 1
                    failed += 1
                    continue # too close to the edge

                # remove beads with bad shape
                elif N.any(sigma < beads_sigma_max/6.) or N.any(sigma > beads_sigma_max):#0.5) or N.any(sigma > 3):
                    print('sigma too different from expected', sigma, zyx)
                    if N.any(arr[rmslice] > thre):
                        arr[rmslice] = me
                    done[rmslice] = 1
                    sigma = 1.5
                    failed += 1
                    continue

                
                elif N.any(arr[rmslice] > amax / 3.):
                    print('still too bright', arr[rmslice].max(), amax / 3.)
                    arr[rmslice] = me
                    done[rmslice] = 1
                    sigma = 1.5
                    failed += 1
                    continue

                #elif imgGeo.closeEnough(zyx, N.array([12,193-edge/2,48-edge/2]), 10):
                #    raise RuntimeError, 'The point of concern was found'

                old="""
                # remove beads too elliptic
                elif sigma[1] / sigma[2] > 1.5 or sigma[2] / sigma[1] > 1.5:
                    print 'too elliptic', sigma[2] / sigma[1]
                    if N.any(arr[rmslice] > thre):
                        arr[rmslice] = me
                        #if (sigma[2] / sigma[1]) > 20:
                        #raise ValueError
                    sigma = 1.5
                    failed += 1
                    continue

                elif N.any(sigma[-2:] > 3.0):
                    print 'sigma too large', sigma, zyx
                    if N.any(arr[rmslice] > thre):
                        arr[rmslice] = me
                    sigma = 1.5
                    failed += 1
                    continue

                elif sigma[0] < 0.5 or sigma[0] > 3:
                    print 'sigma z too different from expected', sigma, zyx
                    if N.any(arr[rmslice] > thre):
                        arr[rmslice] = me
                    sigma = 1.5
                    failed += 1
                    continue


                #elif imgGeo.closeEnough(zyx, N.array((17,719,810), N.float32), 4):
                #    raise RuntimeError"""


                # add results
                zyxs.append(zyx)
                sigmas.append(sigma)
                i += 1
                pmax = amax
                done[rmslice] = 1
                failed = 0
                #print i
                #yield cop[rmslice], arr[rmslice]

            # maximum is below threshold
            else:
                break
        del arr, done

        if not len(zyxs):
            raise ValueError('No beads found for %s' % fn)

        sigmas = N.array(sigmas)
        sigmaYX = N.mean(sigmas[:,1:], axis=1)
        sigmaZ = sigmas[:,0]
        idxyx = sigmaYX.argmax()
        idxz = sigmaZ.argmax()
        print('sigmaYX', round(sigmaYX.mean(), 3), round(sigmaYX.min(), 3), round(sigmaYX.std(), 3), round(sigmaYX.max(), 3), zyxs[idxyx])
        print('sigmaZ', round(sigmaZ.mean(), 3), round(sigmaZ.min(), 3), round(sigmaZ.std(), 3), round(sigmaZ.max(), 3), zyxs[idxz])


        # remove overlaps
        zyxs2 = []
        zyxs = N.array(zyxs)
        for i, zyx in enumerate(zyxs):
            close = imgGeo.closeEnough(zyx, zyxs, difflimit*4)
            if not N.any(close[:i]) and not N.any(close[i+1:]):
                #idx = close.argmax()
                #already = zyxs.pop(idx)
                zyxs2.append(zyx)
        zyxs = zyxs2
    else:
        zyxs, mst0 = zyxs
        zyxs = N.asarray(zyxs)
    
    waves = list(range(h.nw))
    #waves.remove(refwave)

    difdic = {}
    removes = []

    checks = 0
    zeros = 0
    toofars = 0

    #mst = mst0 - mst1
    #mst[1:] = 0
    mst = mst1 - mst0
    print('mst diff', mst)
    
    for w in waves:
        if w == refwave:
            continue
        arr = h.get3DArr(w=w)[:,edge//2:-edge,edge//2:-edge]
        #me = arr.mean()
        #sd = arr.std()
        #thre = me + sd * thre_sigma

        for zyx in zyxs:
            zyx2 = zyx - mst
            key = tuple(zyx * pzyx)
            if key in removes:
                continue

            #win0 = win
            #while win0 >= 3:
            try:
                ret, check = imgFit.fitGaussianND(arr, zyx2, sigma=sigma, window=win)#0)
                #break
            except (IndexError, ValueError):
                ret = zyx2
                check = 5
                    #win0 -= 2
                    #ret, check = imgFit.fitGaussianND(arr, zyx, sigma=sigma, window=3)

            #dif = (zyx2 - ret[2:5]) * pzyx
            dif = (ret[2:5] - zyx2) * pzyx
            #raise ValueError
            if check == 5 or (w != refwave and  N.any(N.abs(dif) > maxdist)) or (w != refwave and  N.all(dif == 0)) or (w == refwave and N.any(N.abs(dif) > maxrefdist)):#(N.all(dif == 0) or N.any(N.abs(dif) > maxdist))):
                if check == 5:
                    checks += 1
                    #elif N.all(dif == 0):
                    #zeros += 1
                elif w == refwave and N.any(N.abs(dif) > maxrefdist):
                    zeros += 1
                elif N.any(N.abs(dif) > maxdist):
                    toofars += 1
                #if N.any(N.abs(dif) > maxdist):
                #    raise ValueError
                #raise RuntimeError
                removes.append(key)
                if key in difdic:
                    del difdic[key]
                #elif not N.sum(dif) or N.any(dif > 10):
                #raise RuntimeError, 'something is wrong'
            else:
                difdic.setdefault(key, [])
                difdic[key].append(dif)
                sigma = ret[5:8]
                #del arr
                    
    h.close()
    del arr
    del h

    print('check:', checks, 'zeros:', zeros, 'toofars', toofars)

    if not len(difdic):
        raise ValueError('No beads found!!')
    
    # subtracting the center
    newdic = {}
    keys = list(difdic.keys())
    newkeys = N.array(keys)
    zmin = N.min(newkeys[:,0])
    center = (shape * pzyx) / 2.
    #yx0 = (N.max(newkeys[:,1:], axis=0) - N.min(newkeys[:,1:], axis=0)) / 2.
    newkeys[:,0] -= zmin
    newkeys[:,1:] -= center[1:] #yx0
    newkeys = [tuple(key) for key in newkeys]

    items = [difdic[key] for key in keys]
    newdic = dict(list(zip(newkeys, items)))
    difdic = newdic

    # plot
    P.figure(0, figsize=(8,8))
    keys = N.array(list(difdic.keys()))
    P.hold(0)
    P.scatter(keys[:,2], keys[:,1], alpha=0.5)
    P.xlabel('X (nm)')
    P.ylabel('Y (nm)')
    P.savefig(fn+'_fig0.png')

    return difdic, (zyxs,mst1)

def beads_summarize_dics(dics, waves=None):
    """
    waves: a list of wave index to use (excluding refwave)

    return a combined dictionary
    """
    if waves is None:
        keys = list(dics[0].keys())
        waves = range(len(dics[0][keys[0]]))
        
    rdic = {}
    for dic in dics:
        for pos, wpos in dic.items():
            for w in waves:
                rdic.setdefault(pos, []).append(wpos[w])
    return rdic

def beads_plotdic(dic, out=None, overwrite=False, colors = ['b', 'orange'], depth=None):
    """
    depth: nm, None means all, (min, max) or max
    
    return zes, yes, xes, mes, zss, yss, xss, sds, pears
    """
    
    # ['#005900', '#ff7400']
    #'b', 'r', 'y']#(0,255,0), (0,0,255), (255,255,0), (255,255,255)]

    keys = list(dic.keys())

    # measure depth
    zzs = N.array([zyx[0] for zyx in keys])
    thre = N.mean(zzs)
    z0 = zzs[N.where(zzs < thre)]
    z1 = zzs[N.where(zzs > thre)]
    zgap = z1.mean() - z0.mean()

    # depth screen
    if depth:
        try:
            if len(depth) == 2:
                keys = [key for key in keys if key[0] > depth[0] and key[0] < depth[1]]
            else:
                raise ValueError('depth should be (min, max) or just max')
        except TypeError:
            keys = [key for key in keys if key[0] < depth]
            
        print('number of beads', len(keys))
        
    # constants and arrays to store data
    ns = len(keys)            # samples
    nw = len(dic[keys[0]])    # waves
    nd = len(dic[keys[0]][0]) # dimensions
    diffs = N.empty((nw,ns), N.float32)
    diffs2d = N.empty((nw,ns), N.float32)
    dists = N.empty((ns,nd), N.float32)
    error = N.empty((nw,ns,nd), N.float32)
    pears = N.empty((nw,nd), N.float32)

    # dists, diffs, and error
    #for i, kd in enumerate(dic.iteritems()):
    for i, pos in enumerate(keys):
        wzyx = dic[pos]
        #pos, wzyx = kd
        dists[i] = pos# - center
        
        for w, zyx in enumerate(wzyx):
            diffs[w,i] = N.sqrt(N.sum(N.power(zyx, 2)))
            diffs2d[w,i] = N.sqrt(N.sum(N.power(zyx[1:], 2)))
            error[w,i] = zyx

    # plot 1-3, distance vs. deviation
    axes = ['Z', 'Y', 'X']
    for d in range(nd):
        for w in range(nw):
            P.figure(d+1)
            P.hold(bool(w))
            P.scatter(dists[:,d], error[w,:,d], color=colors[w], alpha=0.5)
            P.xlabel('Distance (nm) from the center %s' % axes[d])
            P.ylabel('Deviation (um) from the reference channel in the %s axis' % axes[d])
            if d:
                pears[w,d] = alignfuncs.calcPearson(N.abs(dists[:,d]), N.abs(error[w,:,d]))
            else:
                pears[w,d] = alignfuncs.calcPearson(dists[:,d], error[w,:,d])
            
        if out:
            P.figure(d+1, figsize=(8,8))
            P.savefig(out+'_fig%i.png' % (d+1))

    # plot4 scattered plot XY
    nplot = nd
    nplot += 1
    P.figure(nplot, figsize=(8,8))
    keys = N.array(keys)
    for w in range(nw):
        P.hold(bool(w))
        er = N.mean(N.abs(error[w,:,1:]), axis=-1)
        P.scatter(keys[:,2], keys[:,1], 3*er, color=colors[w], alpha=0.5)
    P.xlabel('X (nm)')
    P.ylabel('Y (nm)')
    if out:
        P.savefig(out+'_fig0.png')

    # plot5 scattered plot Z
    nplot += 1
    P.figure(nplot, figsize=(8,8))
    for w in range(nw):
        P.hold(bool(w))
        #er = N.abs(error[w,:,2])
        #P.scatter(keys[:,0], error[w,:,1], 3*er, color=colors[w], alpha=0.5)
        P.scatter(keys[:,0], N.abs(error[w,:,1]), color=colors[w], alpha=0.5)
    P.xlabel('Depth from the surface of the cover slip (nm)')
    P.ylabel('Deviation (nm) from the reference channel in the Y axis')
    if out:
        P.savefig(out+'_fig0.png')

    # plot6 scattered plot Z
    nplot += 1
    P.figure(nplot, figsize=(8,8))
    for w in range(nw):
        P.hold(bool(w))
        #er = N.abs(error[w,:,2])
        #P.scatter(keys[:,0], error[w,:,1], 3*er, color=colors[w], alpha=0.5)
        P.scatter(keys[:,0], N.abs(error[w,:,2]), color=colors[w], alpha=0.5)
    P.xlabel('Depth from the surface of the cover slip (nm)')
    P.ylabel('Deviation  (nm) from the reference channel in the X axis')
    if out:
        P.savefig(out+'_fig0.png')

    # plot7 scattered plot XY
    nplot += 1
    P.figure(nplot, figsize=(8,8))
    keys = N.array(keys)
    for w in range(nw):
        P.hold(bool(w))
        er = N.abs(error[w,:,0])
        P.scatter(keys[:,2], keys[:,1], 3*er, color=colors[w], alpha=0.5)
    P.xlabel('X (nm)')
    P.ylabel('Y (nm)')
    if out:
        P.savefig(out+'_fig0.png')
        
    # stats
    error = N.abs(error)
    mes = [d.mean() for d in diffs]
    me2d = [d.mean() for d in diffs2d]
    sds = [d.std() for d in diffs]
    sd2d = [d.std() for d in diffs2d]

    zes = [error[w,:,0].mean() for w in range(nw)]
    yes = [error[w,:,1].mean() for w in range(nw)]
    xes = [error[w,:,2].mean() for w in range(nw)]

    zss = [error[w,:,0].std() for w in range(nw)]
    yss = [error[w,:,1].std() for w in range(nw)]
    xss = [error[w,:,2].std() for w in range(nw)]

    # file output
    if out:
        if not overwrite and os.path.isfile(out):
            yn = input('overwrite? %s (y/n)' % os.path.basename(out))
            if yn.startswith('n'):
                return
        import csv
        with open(out, 'w') as h:
            cw = csv.writer(h)

            cw.writerow(['# wavelength', 'n', len(dic), 'zthick', round(zgap, 3)])# + ['']*(nd-1))
            cw.writerow(['#mean', 'z', 'y', 'x', 'zyx', 'yx'])
            for w in range(nw):
                cw.writerow([w]+[round(error[w,:,d].mean(), 1) for d in range(nd)] + [round(mes[w], 3), round(me2d[w], 3)])
                
            cw.writerow(['#std']+[]*(nd+2))
            for w in range(nw):
                cw.writerow([w]+[round(error[w,:,d].std(), 1) for d in range(nd)] + [round(sds[w], 3), round(sd2d[w], 3)])

            cw.writerow(['#pearson']+[]*(nd+2))
            for w in range(nw):
                cw.writerow([w]+list(pears[w]))

            cw.writerow(['#raw data'] + []*(nd+2))
            for w, err in enumerate(error):
                cw.writerow(['#wave%i' % w] + []*(nd+2))
                for i, e in enumerate(err):
                    cw.writerow([i]+list(e)+[diffs[w,i], diffs2d[w,i]])#N.sqrt(N.sum(N.power(e,2)))])
                    
    
    return zes, yes, xes, mes, zss, yss, xss, sds, pears, zgap#, error

def beads_view_mark(vid, zyxs, edge=30, color=(1,0,0), mstdif=[0,0,0]):
    from Priithon.all import Y
    zyxs, mst = zyxs
    zyxs = N.array(zyxs) - mstdif
    ids = [Y.vgMarkIn3D(vid, zyx+(0,edge//2,edge//2), s=4, colAtZ=color, zPlusMinus=0,refreshNow=False) for zyx in zyxs]
    v = Y.viewers[vid]
    v.viewer.Refresh()
    return ids

def beads_pearson(fns, chroms=None, refwave=None):
    from . import alignfuncs as af

    if refwave is None:
        refwave0 = 0
    else:
        refwave0 = refwave
    j = 0
    ps = []
    for i, fn in enumerate(fns):
        if chroms:
            chrom = chroms[i]
            h = imgio.Reader(chrom)#mrcIO.MrcReader(chrom)
            if refwave is not None and h.hdr.n1 != refwave:
                h.close()
                continue
            h.close()

        ps.append([])
        h = imgio.Reader(fn) #mrcIO.MrcReader(fn)
        waves = range(h.hdr.NumWaves)
        a = h.get3DArr(w=refwave0)

        for w in waves:
            if w == refwave0:
                ps[j].append(1)
            else:
                b = h.get3DArr(w=w)
                p = af.calcPearson(a, b)
                ps[j].append(p)

        j += 1
    return ps

def beads_Do(fnALNs, fnLOCALs, maxdist=100, nbeads=200, edge=30):
    dds = [beads_analyzeBeads(fn, maxdist=maxdist, nbeads=nbeads, edge=edge) for fn in fnALNs]
    dics = [d[0] for d in dds]
    zyxs = [d[1] for d in dds]
    dds2 = [beads_analyzeBeads(fn, maxdist=maxdist, nbeads=nbeads, zyxs=zyxs[i], edge=edge) for i, fn in enumerate(fnLOCALs)]
    dics2 = [d[0] for d in dds2]
    
    return dics, dics2#dds, dds2

def beads_zyx4decon(zyx):
    zyx, mst = zyx
    zyx2 = [N.array((yx[0],) + tuple(yx[1:]/2.)) for yx in zyx]
    return zyx2, mst


### 8-well comparison

def beads_well_process(zyxs, prefix='Well%02d', suffix='_?LOCAL', welllist=list(range(1,9)), maxdist=200, edge=60):
    import glob
    fns = [sorted(glob.glob(prefix % i + '*' + suffix+'.dv')) for i in welllist]
    #print fns
    if 0:#len(fns[0]) != len(welllist):
        raise RuntimeError('files not found %s' % (prefix % i + '*' + suffix+'.dv'))
    name_pre = suffix[-5:]+'%02d'
    x = [beads_Do2(fns[i], zyxs[i], maxdist, edge, name_pre % j + '_image%02d.csv') for i, j in enumerate(welllist)]#, fnlist in #enumerate(fns)]

    csvs = [sorted(glob.glob(name_pre %i + '_image0?.csv')) for i in welllist]
    return [csv_summarize(csv) for csv in csvs]
    
def beads_Do2(fnlist, zyxs, maxdist=600, edge=60, name='calib01_image0%i.csv'):
    #dds = [beads_analyzeBeads(fn, maxdist=maxdist, edge=edge, zyxs=zyxs[i]) for i, fn in enumerate(fnlist)]
    dds = [beads_analyzeBeads(fn, maxdist=maxdist, edge=edge, zyxs=zyxs) for i, fn in enumerate(fnlist)]
    dics = [d[0] for d in dds]
    return [beads_plotdic(dic, out=name % (i+1), overwrite=True, colors=['orange']) for i, dic in enumerate(dics)]

def csv_summarize(csvs):
    import csv
    prefix = os.path.commonprefix(csvs)
    out = prefix + '_sum.csv'

    try:
        calib_well = int(os.path.basename(prefix).split('_')[0][-1])
    except (TypeError, ValueError):
        calib_well = os.path.basename(prefix).split('_')[0][-1]
    
    with open(out, 'w') as oh:
        w = csv.writer(oh)

        for i, fn in enumerate(csvs):
            with open(fn) as h:
                r = csv.reader(h)
                title = next(r)
                ntitle, nstr = title[1:3]
                titles = r.next()[1:]
                res = r.next()[1:]
                next(r) # std
                stds = r.next()[1:]

            if i == 0:
                title = ['calib_well', 'target_well', ntitle] + titles + ['std_'+t for t in titles]
                w.writerow(title)
            w.writerow([calib_well, (i + 1), nstr] + res + stds)

    return out

###

def compare_pearson(fns, mergin=2):
    """
    compare pearson correlation of wave0 and wave1 using the same window

    fns: list of filenames
    mergin: remove mergin (pixel) at the edge
    
    return list of pearson correlation
    """
    hs = [imgio.Reader(fn) for fn in fns]#mrcIO.MrcReader(fn) for fn in fns]
    shapes = N.array([(h.nz,)+h.shape for h in hs])
    starts0 = N.array([h.hdr.mst[::-1] for h in hs])
    stops0 = starts0 + shapes

    starts_ori = N.max(starts0, 0)
    stops_ori = N.min(stops0, 0)
    shapes0 = stops_ori - starts_ori

    starts = [starts_ori - start for start in starts0]
    stops = [shapes0 + start for start in starts]
    slcs = []
    for i, start in enumerate(starts):
        slc = []
        for d, s in enumerate(start):
            slc.append(slice(s + mergin//2, stops[i][d] - mergin//2))
        slcs.append(slc)

    if N.sum(hs[0].get3DArr(w=0)[slcs[0]] - hs[1].get3DArr(w=0)[slcs[1]]):
        raise ValueError('probably slicing is wrong with %s and %s' % (fns[0], fns[1]))

    ps = []
    for i, h in enumerate(hs):
        a = h.get3DArr(w=0)[slcs[i]]
        b = h.get3DArr(w=1)[slcs[i]]
        ps.append(alignfuncs.calcPearson(a, b))

    return ps


def chrom_stats(fns, nw=3):
    """
    return deviation in um
    """
    t = 0
    refwave = 0

    results = N.zeros((len(fns),nw-1,aligner.NUM_ENTRY), N.float32)
            
    for i, fn in enumerate(fns):
        data = AlignDataHolder(fn)

        rpos = N.array((0,data.mid), N.float32) * data.pxlsiz[:2][::-1]
        mpos = N.array((65,data.mid,data.mid), N.float32) * data.pxlsiz[::-1]

        for w in range(1, data.nw):
            shift = data.getShift(w=w,t=t,refwave=refwave)
            shift[:3] *= data.pxlsiz[::-1]
            shift[3] = imgGeo.euclideanDist(imgGeo.rotate(rpos, shift[3]), rpos)
            for j in range(3):
                shift[4+j] = abs(imgGeo.zoom(mpos[j], shift[4+j]) - mpos[j])
            
            results[i,w-1] = shift
            
    return results

                

class AlignDataHolder(object):
    def __init__(self, fn):
        arr = Mrc.bindFile(fn)
        self.pxlsiz = arr.Mrc.hdr.d
        self.waves = arr.Mrc.hdr.wave[:arr.Mrc.hdr.NumWaves].copy()
        self.refwave = self.waves[arr.Mrc.hdr.n1]
        self.XYsize = arr.Mrc.hdr.Num[:2]
        self.nt = arr.Mrc.hdr.NumTimes
        self.nw = len(self.waves)
        self.t = 0
        self.dtype = arr.dtype.type
        if 'SIR' in fn:
            self.mid = 512
        else:
            self.mid = 256
            
        if arr.Mrc.hdr.n2 == 1:
            parm = arr
            nentry = aligner.NUM_ENTRY
            self.map_str = 'None'
        else:
            parm = arr.Mrc.extFloats[:arr.Mrc.hdr.NumTimes * arr.Mrc.hdr.NumWaves,:arr.Mrc.hdr.NumFloats]
            nentry = arr.Mrc.hdr.NumFloats
            self.nz = arr.Mrc.hdr.Num[-1] / (arr.Mrc.hdr.NumTimes * arr.Mrc.hdr.NumWaves * 2)
            if self.nz == 1:
                self.map_str = 'Projection'
            else:
                self.map_str = 'Section-wise'
        parm = parm.reshape((arr.Mrc.hdr.NumTimes, arr.Mrc.hdr.NumWaves, nentry))
        self.alignParms = parm.copy() # writable

        del arr, parm

    def getShift(self, w=0, t=0, refwave=None):
        """
        return shift at the specified wavelength and time frame
        """
        if refwave is None:
            waves = list(self.waves)
            refwave = waves.index(self.refwave)

        ret = self.alignParms[t,w].copy()
        ref = self.alignParms[t,refwave]

        ret[:4] -= ref[:4]
        if len(ref) >= 5:
            ret[4:] /= ref[4:len(ret)]
        return ret

    def estimateError(self, dif=N.zeros((aligner.NUM_ENTRY,), N.float32), nz=65):
        """
        return shift_in_nm, vector_sum
        
        >>> d = AlignDataHolder(fn)
        >>> s = d.getShift()
        >>> dif = s - [2,10,-8,0.5,1.01,1.0005,0.9995]
        >>> d.estimateError(dif)
        """
        shift = N.copy(dif)
        shift[4:] += 1
        
        rpos = N.array((0,self.mid), N.float32) * self.pxlsiz[:2][::-1]
        mpos = N.array((nz/4.,self.mid,self.mid), N.float32) * self.pxlsiz[::-1]

        shift[:3] *= self.pxlsiz[::-1]
        shift[3] = imgGeo.euclideanDist(imgGeo.rotate(rpos, shift[3]), rpos) * N.sign(shift[3])
        for j in range(3):
            shift[4+j] = imgGeo.zoom(mpos[j], shift[4+j]) - mpos[j]
            
        return shift, N.sqrt(N.sum(N.power(shift, 2)))#N.sum(N.sqrt(N.power(shift, 2)))

def chrom_stat_write(fns, out=None, nw=3, refwave=1):
    import csv
    common = os.path.commonprefix(fns)
    if not out and common:
        out = common + '.csv'
    elif not out:
        raise ValueError('please supply the output filename')

    with open(out, 'w') as h:
        o = csv.writer(h)

        # header
        o.writerow(['name', 'wave'] + aligner.ZYXRM_ENTRY)

        # now write rows
        for w in range(nw):
            if w == refwave:
                continue
            for fn in fns:
                name = fn.replace(common, '')
                an = AlignDataHolder(fn)
                if len(an.waves) <= w:
                    o.writerow([name, w] + [0]*aligner.NUM_ENTRY)
                    continue
                shift = an.getShift(w, refwave=refwave)
                shift[4:] -= 1
                shift, _ = an.estimateError(shift)
                o.writerow([name, w] + list(shift))

    return out

####################################################################################
#################### Quadrisection phase correlation ##############################


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

    1|0
    ---
    2|3

    """
    if center is None:
        center = N.array(a2d.shape) // 2
    center = [int(c) for c in center]
    r1 = a2d[center[0]:,center[1]:]
    r2 = a2d[center[0]:,:center[1]]
    r3 = a2d[:center[0],:center[1]]
    r4 = a2d[:center[0],center[1]:]
    return r1, r2, r3, r4


def estimate2D(a2d, ref, center=None, cqthre=alignfuncs.CTHRE/10., max_shift_pxl=5):
    """
    return [ty,tx,r,my,mx], offset, check
    """
    if center is None:
        shape = N.array(a2d.shape)
        center = shape // 2

    # separate quadrisection
    a1234 = chopImg(ref, center)
    b1234 = chopImg(a2d, center)
    shape = N.array(a1234[0].shape)
    
    # obtain cm
    a1234p = [xcorr.phaseContrastFilter(N.ascontiguousarray(a)) for a in a1234]
    b1234p = [xcorr.phaseContrastFilter(N.ascontiguousarray(b)) for b in b1234]
    abp = [a + b1234p[i] for i, a in enumerate(a1234p)]
    xcms = [U.nd.center_of_mass(N.max(ab, axis=0)) for ab in abp]
    xcm1 = shape[1] - xcms[1]
    xcm2 = shape[1] - xcms[2]
    xcm = N.mean([xcms[0], xcm1, xcm2, xcms[3]])
    
    ycms = [U.nd.center_of_mass(N.max(ab, axis=1)) for ab in abp]
    ycm2 = shape[0] - xcms[2]
    ycm3 = shape[0] - xcms[3]
    ycm = N.mean([ycms[0], ycms[1], ycm2, ycm3])
    
    cm = N.array((ycm, xcm))
    print(cm)

    # quadrisection cross correlation
    ab = list(zip(a1234p, b1234p))
    try:
        yxcs = [xcorr.Xcorr(a, b, phaseContrast=False, searchRad=max_shift_pxl) for a, b in ab]
    except IndexError:
        return N.array((0,0,0,1,1), N.float32), [0,0], [(i, 0) for i in range(4)]
    except (ValueError, ZeroDivisionError):
        raise AlignError
    yxs = [yx for yx, c in yxcs]
    
    # quality check
    cqvs = [c.max() - c[c.shape[0]//4].std() for yx, c in yxcs]
    del yxcs, ab, c
    
    #cqs = [cv > cqthre for cv in cqvs]

    #ids = [idx for idx, cq in enumerate(cqs) if cq == False]

    checks = [(idx, cq) for idx, cq in enumerate(cqvs) if cq < cqthre]

    # translation
    tyx = getTranslation(yxs)

    # magnification
    myx = getMagnification(yxs, cm*2)

    # rotation
    theta, offset = getRotation(yxs, cm*2)

    return list(tyx) + [theta] + list(myx), offset, checks#, [c for yx, c in yxcs]#ids#, cqvs#, cqthre, [c for yx, c in yxcs]

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

    # the center of the quadratic image should be determined
    center = N.array(center)
    center2 = center/2.
    theta = getTheta(asiny, asinx, center2)
    theta = N.degrees(theta)

    # rotation center but this does not seem to be working
    offx = 0#getOffset(asiny1, asiny2, asinx, theta, center2)
    #print offx
    offset = [0,offx]

    return theta, offset


def getTheta(asiny, asinx, center2=(100,100)):
    cdeg = N.arctan2(*center2)
    ryx = center2 + (asiny, asinx)
    return N.arctan2(*ryx) - cdeg

def getOffset(asiny1, asiny2, asinx, theta, center2):
    """
    trying to obtain rotation center offset arithmetically
    but this always gives the answer 0
    """
    theta1 = getTheta(asiny1, asinx, center2)
    theta2 = getTheta(asiny1, asinx, center2)

    tan0 = N.tan(theta)
    tan1 = N.tan(theta1)
    tan2 = N.tan(theta2)

    cos1 = N.cos(theta1)
    cos2 = N.cos(theta2)

    a1 = center2[1] * cos1
    a2 = center2[1] * cos2

    dx = (a1 * a2 * tan2 - a1 * a2 * tan1) / (a1 * tan1 + a2 * tan2)
    return dx

def iteration(a2d, ref, maxErr=0.01, niter=10, phaseContrast=True, initguess=None, echofunc=None, max_shift_pxl=5, cqthre=alignfuncs.CTHRE/10., if_failed=alignfuncs.IF_FAILED[0]):#'simplex'):
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
    from . import cutoutAlign
    
    shape = N.array(a2d.shape)
    center = shape // 2

    ret = N.zeros((5,), N.float32)
    ret[3:] = 1
    if initguess is None or N.all(initguess[:2] == 0):
        yx, c = xcorr.Xcorr(ref, a2d, phaseContrast=phaseContrast)
        ret[:2] = yx
    else:
        print('in iteration, initial geuss is', initguess)
        ret[:] = initguess[:]

    if if_failed == alignfuncs.IF_FAILED[2]:#force_simplex':
        goodImg = 0#False
        niter = 1
    elif if_failed == alignfuncs.IF_FAILED[1]:
        goodImg = -1
    else:
        goodImg = 1#True
    rough = True
                    
    offset = N.zeros((2,), N.float32)
    for i in range(niter):
        b = alignfuncs.applyShift(a2d, [0]+list(ret), offset)

        # cut out
        # because irregular size of the quadratic images are not favorable,
        # the smallest window will be used
        shiftZYX = cutoutAlign.getShift([0]+list(ret), [0]+list(shape))
        maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
        maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
        slc = [slice(int(maxcutY), int(shape[0]-maxcutY)),
               slice(int(maxcutX), int(shape[1]-maxcutX))]
        b = b[slc]
        c = ref[slc]

        startYX = [maxcutY, maxcutX]

        if goodImg > 0:
            ll, curroff, checks = estimate2D(b, c, center-startYX+offset, max_shift_pxl=max_shift_pxl, cqthre=cqthre)

            if len(checks) <= 1:
                ret[:3] += ll[:3]
                ret[3:] *= ll[3:]

            # the quality of quadratic correlation affects resolution.
            # instead of using low-correlation results, such images are sent to alternative calculation.
            if len(checks):
                regions = [(QUADRATIC_AREA[idx], round(cq, 5)) for idx, cq in checks]
                msg = '%s quadratic regions had too-low correlation, using alternative algorithm' % regions
                if echofunc:
                    echofunc(msg)
                #print msg
                    
                if if_failed == 'terminate':
                    return ret, False
                elif if_failed == 'simplex':
                    goodImg = 0
                else:
                    goodImg = -1#False
                    checks = []
                    if initguess is not None:
                        ret[:] = initguess[:]
                #offset += curroff

        elif goodImg < 0:
            ll = logpolar(b, c, center-startYX+offset, phaseContrast)
            ret[:3] += ll[:3]
            ret[3:] *= ll[3:]
            
        elif goodImg == 0:
            print('doing simplex')
            ll = simplex(b, c, phaseContrast, rough=rough)
            ret[:3] += ll[:3]
            ret[3:] *= ll[3:]
            rough = False
            #if echofunc:
            #echofunc('%i: %s' % (i, ll))#ref))
        print(i, ret)
        errs = alignfuncs.errPxl(ll, center)
        try:
            if len(maxErr) ==2:
                if N.all(errs[:2] < maxErr) and N.all(errs[2] < N.mean(maxErr)) and N.all(errs[3:] < maxErr):
                    break
        except TypeError: # maxErr is scaler
            if N.all(errs < maxErr):
                break


    return ret, True#, offset


############
def intensitySpectrum(fns, out=None):
    from PriCommon import bioformatsIO as io
    import csv
    
    if not out:
        out = os.path.commonprefix(fns) + '_intens.csv'

    waves = set()
    nmes = []
        
    for fn in fns:
        h = io.load(fn)
        mes = [h.get3DArr(w=w).mean() for w in range(h.nw)]
        ma = max(mes)
        nme = [me / ma for me in mes]
        [waves.add(round(w)) for w in h.wave]
        nmes.append(nme)
        h.close()

    waves = sorted(list(waves))

    with open(out, 'w') as h:
        r = csv.writer(h)
        old="""
        r.writerow(['name'] + waves)
        for i, fn in enumerate(fns):
            r.writerow([os.path.basename(fn)] + nmes[i])"""
        r.writerow(['wavelength (nm)'] + [os.path.basename(fn) for fn in fns])
        for w, wave in enumerate(waves):
            r.writerow([wave] + [nme[w] for nme in nmes if len(nme) >= (w+1)])

    return out

def sumSpec(fns, out=None):
    #from PriCommon import bioformatsIO as io, mrcIO
    
    if not out:
        out = os.path.commonprefix(fns) + '_maxAU_waveSum.dv'

    waves = [488,561,640]
        
    for i, fn in enumerate(fns):
        h = imgio.Reader(fn) #io.load(fn)
        if not i:
            hdr = makeHdrFromRdr(h)
            hdr.NumWaves = len(fns)
            hdr.wave[:hdr.NumWaves] = waves[:hdr.NumWaves]
            hdr.Num[-1] /= h.nw
            hdr.Num[-1] *= hdr.NumWaves

            wtr = imgio.Writer(out, hdr=hdr)#mrcIO.MrcWriter(out, hdr)
            #wtr.setDimFromMrcHdr(hdr)

        arr = N.empty((h.nw, h.nz, h.ny, h.nx), N.dtype)
        for w in range(h.nw):
            arr[w] = h.get3DArr(w=w)
        arr = N.average(arr, axis=0)
        wtr.write3DArr(arr.astype(h.dtype), w=i)
        h.close()

    wtr.close()
    return out

def makeHdrFromRdr(rdr):
    """
    rdr: reader object
    return header
    """
    if hasattr(rdr, 'hdr'):
        hdr = rdr.hdr
    else:
        hdr = Mrc.makeHdrArray()
        Mrc.init_simple(hdr, Mrc.dtype2MrcMode(rdr.dtype), rdr.shape)
        hdr.ImgSequence = rdr.imgSequence
        hdr.NumTimes = rdr.nt
        #hdr.NumWaves = rdr.nw
        hdr.Num[-1] = rdr.nt * rdr.nw * rdr.nz
        #if len(rdr.wave):
        #    if [1 for wave in rdr.wave[:rdr.nw] if isinstance(wave, basestring)]:
        #        hdr.wave[:rdr.nw] = 0
        #    else:
        #        hdr.wave[:rdr.nw] = rdr.wave[:rdr.nw]
        hdr.d = rdr.pxlsiz[::-1]
        if 'Instrument' in rdr.metadata:
            hdr.LensNum = eval(rdr.metadata['Instrument']['Objective']['ID'].split(':')[1])

    return hdr

def convertImg2Mrc(fns):
    #from PriCommon import bioformatsIO as io, mrcIO
    outs = []
    for fn in fns:
        base, ext = os.path.splitext(fn)
        out = base + '.dv'
        h = imgio.Reader(fn) #io.load(fn)

        hdr = imgio.mrcIO.makeHdrFromRdr(h)
        hdr.LensNum = 10612
        hdr.wave[2] = 625
        wtr = imgio.Writer(out, hdr=hdr)#mrcIO.MrcWriter(out, hdr)

        for t in range(h.nt):
            for w in range(h.nw):
                arr = h.get3DArr(w=w, t=t)
                wtr.write3DArr(arr, w=w, t=t)
        h.close()
        wtr.close()
        outs.append(out)

    return outs

## 8 well ###
WELL01 = {1: list(range(2, 9))}
NEIGHBORS={1: [2, 3], 2: [1, 4], 3: [1, 4, 5], 4: [2, 3, 6], 5: [3, 6, 7], 6: [4, 5, 8], 7: [5, 8], 8: [6, 7]}
NOCONTACT={1: [5, 6, 7, 8], 2: [5, 6, 7, 8], 3: [7, 8], 4: [7, 8], 5: [1, 2], 6: [1, 2], 7: [1, 2, 3, 4, 5, 6], 8: [1, 2, 3, 4]}

def well_neighbors(fns, outbase='', refwave=0, npxls=(64,1024,1024)):
    from . import chromformat
    if not outbase:
        outbase = os.path.commonprefix(fns)
    
    center = N.divide(npxls, 2)
    
    # obtain data
    rdrs = [chromformat.ChromagnonReader(fn) for fn in fns]
    [r.setRefWave(refwave) for r in rdrs]
    # assuming only two wavelengths
    t = 0
    w = int(not refwave)
    data = N.array([r.alignParms[t,w].copy() for r in rdrs])

    pxlsizs = [r.pxlsiz * 1000 for r in rdrs] # in nm
    [r.close() for r in rdrs]

    outs = []
    # total
    outs.append(_well_neighbors(data, pxlsizs, center, WELL01, outbase+'_total.csv', evalfunc_total))
    
    # neighbor
    outs.append(_well_neighbors(data, pxlsizs, center, NEIGHBORS, outbase+'_neighbor.csv', evalfunc_neigh))

    # no contact
    outs.append(_well_neighbors(data, pxlsizs, center, NOCONTACT, outbase+'_nocontact.csv', evalfunc_neigh))

    return outs


def _well_neighbors(data, pxlsizs, center, wellset, outfn, evalfunc):
    import csv
    with open(outfn, 'w') as h:
        wtr = csv.writer(h)
        wtr.writerow(('well', 'neighbor', 'tz', 'ty', 'tx', 'r', 'mz', 'my', 'mx', 'SUM'))
        
        for well, neis in wellset.items():
            if len(data) == 7 and well == 7:
                continue
            elif len(data) == 7 and well == 8:
                well = 7
            wid = well - 1

            pxlsiz = pxlsizs[wid]

            for nwell in neis:
                nid = nwell - 1
                if len(data) == 7 and nwell == 7:
                    continue
                elif len(data) == 7 and nwell == 8:
                    nid -= 1

                if not evalfunc(wid, nid):
                    continue
                
                dev = data[nid] - data[wid]
                dev[-3:] += 1
                
                # zyx
                dev[:3] *= pxlsiz

                # rotation
                rpos = imgGeo.rotate(center[1:], dev[3])
                dev[3] = imgGeo.euclideanDist(rpos, center[1:]) * N.average(pxlsiz[-2:])

                # magnification
                mpos = center * dev[-3:]
                dev[-3:] = N.abs(mpos - center) * pxlsiz

                # sum
                ss = N.power(dev, 2)
                ss = N.sum(ss, axis=-1)
                ss = N.sqrt(ss)
                wtr.writerow([well, nwell] + list(dev) + [ss])
    return outfn

def evalfunc_total(wid, nid):
    return True

def evalfunc_neigh(wid, nid):
    if nid >= wid:
        return True


### ------- local alignemnt evaluation

def makeWarp(fn):
    from Priithon.all import F
    h = aligner.Chromagnon(fn)
    warp = N.zeros((h.nt, h.nw, 2, h.ny, h.nx), N.float32)
    warp[0,1,0] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=0.5, orig=(h.ny/2, h.nx/2))
    warp[0,1,0] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=0.5, orig=(h.ny/5, h.nx/5))
    warp[0,1,0] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=0.5, orig=(h.ny/5, 4*h.nx/5))
    #warp[0,1,0] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=-0.5, orig=(4*h.ny/5, 4*h.nx/5))
    warp[0,1,0] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=-0.5, orig=(4*h.ny/5, h.nx/5))

    warp[0,1,1] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=0.5, orig=(h.ny/2, h.nx/2))
    warp[0,1,1] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=0.5, orig=(h.ny/4, h.nx/4))
    warp[0,1,1] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=0.5, orig=(3*h.ny/4, h.nx/4))
    #warp[0,1,1] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=-0.5, orig=(3*h.ny/4, 3*h.nx/4))
    warp[0,1,1] += F.gaussianArr((h.ny, h.nx), sigma=30, peakVal=-0.5, orig=(h.ny/4, 3*h.nx/4))

    #h.alignParms[0,1] = [0, -3., -2., 0.5, 1., 0.999, 0.998]
    h.mapyx = warp

    h.saveParm()

    out = fn+'_WARP.dv'
    h.setRegionCutOut()
    h.saveAlignedImage(out)

    return out
    
def compareWarp(fn, out=None, div_step=20, div_max=200, use_varianceMap=True):
    import csv
    from . import chromformat
    from PriCommon import imgFilters
    # output file
    if not out:
        out = fn + '_summary.csv'

    with open(out, 'w') as h:
        wtr = csv.writer(h)
        title = ['name', 'noise type', 'noise value', 'window size (pxl)', 'dx (nm)', 'dy (nm)', 'dmx (nm)', 'dmy (nm)', 'dr (nm)', 'total (nm)', 'nregions', 'me (nm)', 'ma (nm)', 'sd (nm)', 'pearson']
        wtr.writerow(title)

        # constants
        warpst = '_WARP.dv'
        suffix = '.chromagnon.tif'

        noise_steps = [''] + ['%04d' % noise for noise in range(div_step, div_max+div_step, div_step)]

        init = False

        # reference
        ansfn = fn + suffix

        #varianceMap = """
        if use_varianceMap:
            #npxl= 30
            ar, an = prepareImg(fn, chrom=ansfn, aligned=True)
            arr, ref = ar
            variance = alignfuncs.getVar(arr, ref)
            threshold = variance * 0.1 #threfact=0.1

        # 
        noise0 = fn + '_WARP.dv' + suffix
        wins = [30 * 2**i for i in range(3)]

        for npxls in wins:
            if use_varianceMap:
                yx, regions, cs = alignfuncs.xcorNonLinear(arr, ref, npxls=npxls, threshold=threshold)
                #region = regions[1] > threshold
                factor = an.img.nx / regions[1].shape[-1]
                region = imgFilters.zoomFourier(regions[1], factor, use_abs=True)
                from Priithon.all import Mrc
                Mrc.save((region > (threshold * 2.5)).astype(N.uint16), 'region%s_win%i.mrc' % (fn[-1], npxls), ifExists='overwrite')
                continue
                ind = N.nonzero(region > threshold)
                ans = chromformat.ChromagnonReader(ansfn, an.img, an)
                #ansarr = (region * ans.readMap3D(t=0, w=1) * -1)[0]

            else:#all_region = """
                ind = None
                ans = chromformat.ChromagnonReader(ansfn)
            ansarr = (ans.readMap3D(t=0, w=1) * -1)[0]#"""

            truth = ans.alignParms[0,1]
            truth[:4] *= -1
            truth[4:] = 1/truth[4:]
        
            for noise in noise_steps:
                if not noise: # noise 0
                    nfn = fn + warpst
                    chm = align2D(nfn, npxls)
                    names = [fn[-1], '', 0, npxls]
                    
                    writeWarpSingle(ansarr, chm, wtr, truth, names=names, ind=ind)
                else:
                    for noiseModel in ['Gaussian', 'Poisson']:
                        nfn = fn + warpst + noiseModel + noise
                        chm = align2D(nfn, npxls)
                        names = [fn[-1], noiseModel, noise, npxls]

                        writeWarpSingle(ansarr, chm, wtr, truth, names=names, ind=ind)
    h.close()
    return out

                    
def writeWarpSingle(ansarr, chm, wtr, truth, names, ind=None):
    # global
    imgSize = N.array((0,chm.img.nx/2), N.float32)
    pxlsiz = chm.pxlsiz[-2:]
    diff = N.abs(truth - chm.alignParms[0,1])
    dy,dx = diff[1:2] * (pxlsiz * 1000)
    dr = (imgGeo.euclideanDist(imgGeo.rotate(imgSize, N.radians(diff[3])), imgSize))*(N.mean(pxlsiz)*1000)
    dmy = diff[-2] * imgSize[1] * pxlsiz[-2] * 1000
    dmx = diff[-1] * imgSize[1] * pxlsiz[-1] * 1000

    total = N.sqrt(dy**2 + dx**2 + dr**2 + dmy**2 + dmx**2)

    # local
    arr = chm.mapyx[0,1]#readMap3D(t=0, w=1)
    ansarr = alignfuncs.resizeLocal2D(ansarr, arr.shape[-2:])
    #print('shape', arr.shape, ansarr.shape)
    dif = N.abs(ansarr - arr)
    dif[0] *= pxlsiz[0] * 1000
    dif[1] *= pxlsiz[1] * 1000
    if ind is not None:
        #print('before', dif.shape, dif.mean())
        dif = dif[:,ind[0],ind[1]]
        #print('size', dif.shape, len(ind[0]))
        #print(dif.shape, dif.mean())
        #raise
    #return arr, ansarr
    
    me = dif.mean()
    ma = dif.max()
    sd = dif.std()
    pc = calcPearsonSimple(ansarr, arr)
    
    wtr.writerow(names + [dx,dy,dmx,dmy,dr,total,len(ind[0]),me,ma,sd, pc])
    
def align2D(fn, npxls, t=0):
    
    def _echo(msg, skip_notify=False):
        pass
    
    an = aligner.Chromagnon(fn)
    an.setMaxError(0.0000001)

    an.findBestChannel()
    an.setEchofunc(_echo)

    an.setRefImg()

    for w in range(an.img.nw):
        if (w == an.refwave):
            continue

        if an.img.nz > 1:
            img = an.img.get3DArr(w=w, t=t)

            zs = N.round_(N.array(an.refzs)).astype(N.int)

            if zs.max() >= an.img.nz:
                zsbool = (zs < an.img.nz)
                zsinds = N.nonzero(zsbool)[0]
                zs = zs[zsinds]

            imgyx = alignfuncs.prep2D(img, zs=zs)
            del img

        else:
            imgyx = an.img.getArr(w=w, t=t, z=0)

        initguess = N.zeros((5,), N.float32)
        initguess[3:] = 1

        old="""
        parm, check = alignfuncs.iteration(imgyx, an.refyx, maxErr=an.maxErrYX, niter=an.niter, phaseContrast=an.phaseContrast, initguess=initguess, echofunc=an.echofunc, max_shift_pxl=an.max_shift_pxl)

        ty,tx,r,my,mx = parm

        an.alignParms[0,w,1] = ty
        an.alignParms[0,w,2] = tx
        an.alignParms[0,w,3] = r
        an.alignParms[0,w,5] = my
        an.alignParms[0,w,6] = mx"""
        
        #self.setRegionCutOut()
        
        #yx, c = xcorr.Xcorr(, img, phaseContrast=self.phaseContrast, searchRad=searchRad)

        an.findNonLinear2D(npxls=npxls)

        #an.saveParm()

    return an

def calcPearsonSimple(a0, a1):
    a0 = a0.ravel()
    a1 = a1.ravel()

    i0 = N.nonzero(a0)[0]

    b0 = a0[i0]
    b1 = a1[i0]

    a0div = b0 - N.average(b0)
    a1div = b1 - N.average(b1)

    r0 = N.sum(a0div * a1div)
    r1 = (N.sum(a0div**2) * N.sum(a1div**2)) ** 0.5
    #print('r0, r1', r0, r1)
    if r1:
        return r0 / r1
    else:
        return 0

def repeatCompWarp(fns, n=6, div_step=20, div_max=200):
    from . import test_compareReg as reg
    fnwps = [fn + '_WARP.dv' for fn in fns]
    for i in range(n):
        reg.makeFiles(fnwps, std=10, div_step=div_step, div_max=div_max)
        for fn in fns:
            out = fn + '_summary_%i.csv' % (i + 1)
            print(compareWarp(fn, out=out, div_step=div_step, div_max=div_max))
            

def plotCompWarp(tif, axis=0, minus=False, pxlsizYX=0.08, vmin=-50, vmax=50, colorbar=False):
    if isinstance(tif, str):
        h = imgio.Reader(tif)
        a = h.get3DArr(w=1)[...,::-1,:]
    else:
        a = tif[1]
    if minus:
        a *= -1
    a *= pxlsizYX * 1000
    print('max', N.max(a))
    print('min', N.min(a))
    print('mean', N.mean(N.abs(a)))

    fig = P.figure(1)
    P.hold(0)
    im = P.imshow(a[axis], vmin=vmin, vmax=vmax)
    P.hold(1)
    cont = P.contour(a[axis], colors=['white'])
    cont.clabel(fmt='%1.1f', fontsize=12)
    if colorbar:
        fig.colorbar(im)

def imshow(fn, z=23, mi=6, ma=200):

    
    P.hold(0)
    h = imgio.Reader(fn)
    b = N.zeros((h.ny, h.nx, 3), N.float32)

    # channel 1
    w = 0
    a = h.getArr(z=z, w=w)[...,::-1,:]
    a = normalizeP(a, mi, ma)
    
    # cyan
    b[...,1] += a / 2.
    b[...,2] += a / 2.

    # channel 2
    w = 1
    a = h.getArr(z=z, w=w)[...,::-1,:]
    a = normalizeP(a, mi, ma)
    
    # magenta
    b[...,0] += a / 2.
    b[...,2] += a / 2.

    return P.imshow(b)
    
def normalizeP(a, mi=6, ma=200):
    a = a.astype(N.float32)
    mi = N.min(a)
    aa = N.where(a < mi, 0, a - mi)
    aa = N.where(aa > ma-mi, ma-mi, aa)

    return aa / ma
