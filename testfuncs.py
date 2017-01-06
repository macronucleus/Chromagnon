from __future__ import with_statement
import numpy as N
from Priithon.all import P, U, Mrc

from PriCommon import xcorr, imgGeo
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
        waves = range(an.img.nw)
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

    a1234 = alignfuncs.chopImg(an.refyz)
    b1234 = alignfuncs.chopImg(imgyz)

    ab = zip(a1234, b1234)

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
        waves = range(an.img.nw)
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

    ab = zip(a1234, b1234)

    yxcs = [xcorr.Xcorr(a, b, phaseContrast=phaseContrast) for a, b in ab]
    yxs = [yx for yx, c in yxcs]
    cqs = [c.max() - c[c.shape[0]//4].std() for yx, c in yxcs]
    
    return ab, cqs, [c for yx, c in yxcs], yxs, an
        
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
        waves = range(an.img.nw)
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


def testNonlinear(arr, ref, npxls=32, phaseContrast=True, centerDot=True):
    try:
        if len(npxls) != len(arr.shape):
            raise ValueError, 'length of the list of npxls must be the same as len(shape)'
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

def beads_analyzeBeads(fn, thre_sigma=1., refwave=2, nbeads=60, win=5, maxdist=600, maxrefdist=5):#0.6, maxrefdist=0.005):
    """
    maxdist: nm
    maxrefdist: nm

    return dic
    """
    from PriCommon import mrcIO, imgFilters, imgFit, imgGeo, microscope
    from Priithon.all import Y
    h = mrcIO.MrcReader(fn)
    if refwave >= h.nw:
        raise ValueError, 'reference wave does not exists'
    shape = h.hdr.Num[::-1].copy()
    shape[0] /= (h.hdr.NumTimes * h.hdr.NumWaves)
    pzyx = h.hdr.d[::-1]

    NA = 1.35
    difflimitYX = microscope.resolution(NA, h.hdr.wave[refwave])/1000.
    difflimit = N.array([difflimitYX*2, difflimitYX, difflimitYX]) / pzyx
    print 'diffraction limit (px) is:', difflimit
    simres = difflimit / 1.5#2.

    arr = h.get3DArr(w=refwave).copy()
    ndim = arr.ndim
    me = arr.mean()
    sd = arr.std()
    thre = me + sd * thre_sigma
    sigma = 1.5

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
        zyx1 = N.where(zyx + simres < shape, zyx + simres, shape).astype(N.int)
        rmslice = [slice(*zyx) for zyx in zip(zyx0, zyx1)]

        if failed > 10:
            raise RuntimeError
            break
        elif amax == pmax:
            arr[rmslice] = me
        elif amax > thre:
            # Gaussian fitting
            try:
                ret, check = imgFit.fitGaussianND(arr, [z,y,x][-ndim:], sigma, win)
            except IndexError: # too close to the edge
                arr[rmslice] = me
                print 'Index Error, too close to the edge', z,y,x
                failed += 1
                continue
            if check == 5:
                arr[rmslice] = me
                print 'fit failed', z,y,x
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
                print 'fitting results outside the image', zyx, z,y,x, rmslice
                arr[rmslice] = me
                failed += 1
                continue # too close to the edge

            # remove the point
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
                print 'too close to the edge', zyx
                if N.any(arr[rmslice] > thre):
                    arr[rmslice] = me
                failed += 1
                continue # too close to the edge

            # remove beads with bad shape
            elif N.any(sigma < 0.5) or N.any(sigma > 3):
                print 'sigma too different from expected', sigma, zyx
                if N.any(arr[rmslice] > thre):
                    arr[rmslice] = me
                sigma = 1.5
                failed += 1
                continue

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
            failed = 0
            #print i
            
        # maximum is below threshold
        else:
            break
    del arr

    sigmas = N.array(sigmas)
    sigmaYX = N.mean(sigmas[:,1:], axis=1)
    sigmaZ = sigmas[:,0]
    idxyx = sigmaYX.argmax()
    idxz = sigmaZ.argmax()
    print 'sigmaYX', round(sigmaYX.mean(), 3), round(sigmaYX.min(), 3), round(sigmaYX.std(), 3), round(sigmaYX.max(), 3), zyxs[idxyx]
    print 'sigmaZ', round(sigmaZ.mean(), 3), round(sigmaZ.min(), 3), round(sigmaZ.std(), 3), round(sigmaZ.max(), 3), zyxs[idxz]

    
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
    
    waves = range(h.nw)
    #waves.remove(refwave)

    difdic = {}
    removes = []

    checks = 0
    zeros = 0
    toofars = 0

    pzyx *= 1000
    
    for w in waves:
        if w == refwave:
            continue
        arr = h.get3DArr(w=w)
        #me = arr.mean()
        #sd = arr.std()
        #thre = me + sd * thre_sigma

        for zyx in zyxs:
            key = tuple(zyx * pzyx)
            if key in removes:
                continue

            #win0 = win
            #while win0 >= 3:
            try:
                ret, check = imgFit.fitGaussianND(arr, zyx, sigma=sigma, window=win)#0)
                #break
            except (IndexError, ValueError):
                ret = zyx
                check = 5
                    #win0 -= 2
                    #ret, check = imgFit.fitGaussianND(arr, zyx, sigma=sigma, window=3)

            dif = (zyx - ret[2:5]) * pzyx
            if check == 5 or (w != refwave and  N.any(N.abs(dif) > maxdist)) or (w == refwave and N.any(N.abs(dif) > maxrefdist)):#(N.all(dif == 0) or N.any(N.abs(dif) > maxdist))):
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
                if difdic.has_key(key):
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

    print 'check:', checks, 'zeros:', zeros, 'toofars', toofars

    # subtracting the center
    newdic = {}
    keys = difdic.keys()
    newkeys = N.array(keys)
    zmin = N.min(newkeys[:,0])
    center = (shape * pzyx) / 2.
    #yx0 = (N.max(newkeys[:,1:], axis=0) - N.min(newkeys[:,1:], axis=0)) / 2.
    newkeys[:,0] -= zmin
    newkeys[:,1:] -= center[1:] #yx0
    newkeys = [tuple(key) for key in newkeys]

    items = [difdic[key] for key in keys]
    newdic = dict(zip(newkeys, items))
    difdic = newdic

    # plot
    P.figure(0, figsize=(8,8))
    keys = N.array(difdic.keys())
    P.hold(0)
    P.scatter(keys[:,2], keys[:,1], alpha=0.5)
    P.xlabel('X (nm)')
    P.ylabel('Y (nm)')
    P.savefig(fn+'_fig0.png')

    return difdic#, shape


def beads_plotdic(dic, out=None, overwrite=False, colors = ['g', 'm'], depth=None):
    """
    depth: nm, None means all, (min, max) or max
    
    return zes, yes, xes, mes, zss, yss, xss, sds, pears
    """
    
    # ['#005900', '#ff7400']
    #'b', 'r', 'y']#(0,255,0), (0,0,255), (255,255,0), (255,255,255)]

    keys = dic.keys()

    # depth screen
    if depth:
        try:
            if len(depth) == 2:
                keys = [key for key in keys if key[0] > depth[0] and key[0] < depth[1]]
            else:
                raise ValueError, 'depth should be (min, max) or just max'
        except TypeError:
            keys = [key for key in keys if key[0] < depth]
            
        print 'number of beads', len(keys)
        
    # constants and arrays to store data
    ns = len(keys)            # samples
    nw = len(dic[keys[0]])    # waves
    nd = len(dic[keys[0]][0]) # dimensions
    diffs = N.empty((nw,ns), N.float32)
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
    sds = [d.std() for d in diffs]

    zes = [error[w,:,0].mean() for w in xrange(nw)]
    yes = [error[w,:,1].mean() for w in xrange(nw)]
    xes = [error[w,:,2].mean() for w in xrange(nw)]

    zss = [error[w,:,0].std() for w in xrange(nw)]
    yss = [error[w,:,1].std() for w in xrange(nw)]
    xss = [error[w,:,2].std() for w in xrange(nw)]

    # file output
    if out:
        if not overwrite and os.path.isfile(out):
            yn = raw_input('overwrite? %s (y/n)' % os.path.basename(out))
            if yn.startswith('n'):
                return
        import csv
        with open(out, 'w') as h:
            cw = csv.writer(h)

            cw.writerow(['# wavelength', 'n', len(dic)] + ['']*(nd-1))
            cw.writerow(['#mean', 'z', 'y', 'x', 'zyx'])
            for w in xrange(nw):
                cw.writerow([w]+[round(error[w,:,d].mean(), 1) for d in xrange(nd)] + [round(mes[w], 3)])
                
            cw.writerow(['#std']+[]*(nd+1))
            for w in xrange(nw):
                cw.writerow([w]+[round(error[w,:,d].std(), 1) for d in xrange(nd)] + [round(sds[w], 3)])

            cw.writerow(['#pearson']+[]*(nd+1))
            for w in xrange(nw):
                cw.writerow([w]+list(pears[w]))

            cw.writerow(['#row data'] + []*(nd+1))
            for w, err in enumerate(error):
                cw.writerow(['#wave%i' % w] + []*(nd+1))
                for i, e in enumerate(err):
                    cw.writerow([i]+list(e))
                    
    
    return zes, yes, xes, mes, zss, yss, xss, sds, pears#, error

def beads_pearson(fns, chroms=None, refwave=None):
    from PriCommon import mrcIO
    import alignfuncs as af

    if refwave is None:
        refwave0 = 0
    else:
        refwave0 = refwave
    j = 0
    ps = []
    for i, fn in enumerate(fns):
        if chroms:
            chrom = chroms[i]
            h = mrcIO.MrcReader(chrom)
            if refwave is not None and h.hdr.n1 != refwave:
                h.close()
                continue
            h.close()

        ps.append([])
        h = mrcIO.MrcReader(fn)
        waves = xrange(h.hdr.NumWaves)
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

        for w in xrange(1, data.nw):
            shift = data.getShift(w=w,t=t,refwave=refwave)
            shift[:3] *= data.pxlsiz[::-1]
            shift[3] = imgGeo.euclideanDist(imgGeo.rotate(rpos, shift[3]), rpos)
            for j in xrange(3):
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
        for j in xrange(3):
            shift[4+j] = imgGeo.zoom(mpos[j], shift[4+j]) - mpos[j]
            
        return shift, N.sqrt(N.sum(N.power(shift, 2)))#N.sum(N.sqrt(N.power(shift, 2)))

def chrom_stat_write(fns, out=None, nw=3, refwave=1):
    import csv
    common = os.path.commonprefix(fns)
    if not out and common:
        out = common + '.csv'
    elif not out:
        raise ValueError, 'please supply the output filename'

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
