from __future__ import with_statement
import numpy as N
from Priithon.all import P, U, Mrc

from PriCommon import xcorr, imgGeo
import aligner, alignfuncs

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
    return arr, ref, an
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
    elif z is None:
        arr3D = an.get3DArr(w=w)
        zs = N.round_(an.refzs-an.alignParms[0,w,0]).astype(N.int)
        arr = alignfuncs.prep2D(arr3D, zs=zs)
    else:
        z0 = int(round(z - an.alignParms[0,w,0]))
        arr = an.img.getArr(w=w, z=z0)
        
    an.setRegionCutOut()
    arr = arr[an.cropSlice[-2:]]#[Ellipsis]+an._yxSlice]
    ref = ref[an.cropSlice[-2:]]#[Ellipsis]+an._yxSlice]
    an.close()

    return N.array((arr, ref)), an


def testNonlinear(arr, ref, npxls=32, phaseContrast=True):
    try:
        if len(npxls) != len(arr.shape):
            raise ValueError, 'length of the list of npxls must be the same as len(shape)'
    except TypeError:
        npxls = [npxls for d in range(len(arr.shape))]
        
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

def beads_analyzeBeads(fn, thre_sigma=1., refwave=2, nbeads=30, win=5, maxdist=0.6):
    from PriCommon import mrcIO, imgFilters, imgFit, imgGeo, microscope
    h = mrcIO.MrcReader(fn)
    shape = list(h.hdr.Num[::-1])
    shape[0] /= (h.hdr.NumTimes * h.hdr.NumWaves)
    pzyx = h.hdr.d[::-1]

    NA = 1.35
    difflimitYX = microscope.resolution(NA, h.hdr.wave[refwave])/1000.
    difflimit = N.array([difflimitYX*2, difflimitYX, difflimitYX]) / pzyx

    arr = h.get3DArr(w=refwave).copy()
    me = arr.mean()
    sd = arr.std()
    thre = me + sd * thre_sigma
    sigma = 0.5
        
    zyxs = []
    i = 0
    while i < nbeads:
    #for i in range(nbeads):#100):
        if arr.max() > thre:
            v, zyx, sigma = imgFilters.findMaxWithGFit(arr, sigma=sigma, win=win)
            if len(zyxs) and imgGeo.closeEnough(zyx, zyxs, difflimit*2):
                print 'too close', zyx
                imgFilters.mask_gaussianND(arr, zyx, v, sigma)
                continue
            zyxs.append(zyx)
            imgFilters.mask_gaussianND(arr, zyx, v, sigma)
            i += 1
        else:
            break
    del arr
    
    waves = range(h.nw)
    #waves.remove(refwave)

    difdic = {}
    removes = []

    checks = 0
    zeros = 0
    toofars = 0
    
    for w in waves:
        arr = h.get3DArr(w=w)
        me = arr.mean()
        sd = arr.std()
        thre = me + sd * thre_sigma

        for zyx in zyxs:
            key = tuple(zyx)
            if key in removes:
                continue

            win0 = win
            while win0 >= 3:
                try:
                    ret, check = imgFit.fitGaussianND(arr, zyx, sigma=sigma, window=win0)
                    break
                except IndexError:
                    win0 -= 2
                    #ret, check = imgFit.fitGaussianND(arr, zyx, sigma=sigma, window=3)

            dif = (zyx - ret[2:5]) * pzyx
            if check == 5 or (w != refwave and (N.all(dif == 0) or N.any(N.abs(dif) > maxdist))):
                if check == 5:
                    checks += 1
                elif N.all(dif == 0):
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

    P.figure(0)
    keys = N.array(difdic.keys())
    P.hold(0)
    P.scatter(keys[:,2], keys[:,1], alpha=0.5)
    P.xlabel('X (pixel)')
    P.ylabel('Y (pixel)')
    P.savefig(fn+'_fig0.png')

    return difdic, shape


def beads_plotdic(dic, shape, out=None, overwrite=False):
    colors = ['g', 'b', 'r', 'y']#(0,255,0), (0,0,255), (255,255,0), (255,255,255)]
    center = N.divide(shape, 2)
    keys = dic.keys()

    ns = len(keys)            # samples
    nw = len(dic[keys[0]])    # waves
    nd = len(dic[keys[0]][0]) # dimensions
    diffs = N.empty((nw,ns), N.float32)
    dists = N.empty((ns,nd), N.float32)
    error = N.empty((nw,ns,nd), N.float32)
    pears = N.empty((nw,nd), N.float32)
    
    for i, kd in enumerate(dic.iteritems()):
        pos, wzyx = kd
        dists[i] = pos - center
        
        for w, zyx in enumerate(wzyx):
            diffs[w,i] = N.sqrt(N.sum(N.power(zyx, 2)))
            #for axis in range(nd):
            error[w,i] = zyx

    

    axes = ['Z', 'Y', 'X']
    for d in range(nd):
        for w in range(nw):
            P.figure(d+1)
            P.hold(bool(w))
            P.scatter(dists[:,d], error[w,:,d], color=colors[w], alpha=0.5)
            P.xlabel('Distance (pixel) from the center %s' % axes[d])
            P.ylabel('Distance (um) from the red channel')
            pears[w,d] = alignfuncs.calcPearson(N.abs(dists[:,d]), error[w,:,d])
            
        if out:
            P.figure(d+1)
            P.savefig(out+'_fig%i.png' % (d+1))

    mes = [d.mean() for d in diffs]
    sds = [d.std() for d in diffs]

    zes = [error[w,:,0].mean() for w in xrange(nw)]
    yes = [error[w,:,1].mean() for w in xrange(nw)]
    xes = [error[w,:,2].mean() for w in xrange(nw)]

    zss = [error[w,:,0].std() for w in xrange(nw)]
    yss = [error[w,:,1].std() for w in xrange(nw)]
    xss = [error[w,:,2].std() for w in xrange(nw)]

    if out:
        if not overwrite and os.path.isfile(out):
            yn = raw_input('overwrite? %s (y/n)' % os.path.basename(out))
            if yn.startswith('n'):
                return
        import csv
        ncolumns = nw + 1
        with open(out, 'w') as h:
            cw = csv.writer(h)

            cw.writerow(['# mean', len(dic)] + ['']*(nd-1))
            cw.writerow(['# z', 'y', 'x', 'zyx'])
            for w in xrange(nw):
                cw.writerow([round(error[w,:,d].mean(), 4) for d in xrange(nd)] + [round(mes[w], 4)])
                
            cw.writerow(['#std']+[]*nd)
            for w in xrange(nw):
                cw.writerow([round(error[w,:,d].std(), 4) for d in xrange(nd)] + [round(mes[w], 4)])

            cw.writerow(['#pearson']+[]*nd)
            for w in xrange(nw):
                cw.writerow(pears[w])
    
    return zes, yes, xes, mes, zss, yss, xss, sds, pears

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
    t = 0
    refwave = 0

    results = N.zeros((len(fns),nw-1,aligner.NUM_ENTRY), N.float32)
            
    for i, fn in enumerate(fns):
        data = AlignDataHolder(fn)

        rpos = N.array((0,256), N.float32) * data.pxlsiz[:2][::-1]
        mpos = N.array((65,256,256), N.float32) * data.pxlsiz[::-1]

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
            refwave = self.refwave

        ret = self.alignParms[t,w].copy()
        ref = self.alignParms[t,refwave]

        ret[:4] -= ref[:4]
        if len(ref) >= 5:
            ret[4:] /= ref[4:len(ret)]
        return ret
