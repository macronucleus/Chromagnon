#!/usr/bin/env priithon

import Chromagnon as ch
import os, csv
from Priithon import imgio
import numpy as N
from scipy.spatial import distance
from Priithon import imgGeo
from Priithon.all import P

MINPXL=60

####========= Functions to make something similar to Fig S4 in Sci Rep 2018 ===========###
# 20180306maptest

def examine_local(fns, out_prefix=None, minpxls=MINPXL, use_suffix_num=True):
    """
    3 wavelengths did not work as expected.
    2 wavelengths worked okay.
    """
    if not out_prefix:
        out_prefix = os.path.commonprefix(fns)
        
    out = out_prefix + 'npxl%i_summ.dv' % minpxls
    out_csv = out_prefix + '_global_summ.csv'
    
    for t, fn in enumerate(fns):
        print('processing t=%i: %s' % (t, fn))
        if use_suffix_num:
            tstr = os.path.splitext(fn)[0].split('_')[-1]
            if tstr.isdigit():
                t = int(tstr)
            elif tstr.startswith('y'):
                y = int(tstr[1:])
                xstr = os.path.splitext(fn)[0].split('_')[-2]
                x = int(xstr[1:])
                tt2 = len(fns)**0.5
                t = int(y * (tt2) + x) # x --> y
            else:
                tstr2 = ''
                for cc in fn[::-1]:
                    if cc.isdigit():
                        tstr2 += cc
                    else:
                        break
                t = int(tstr2[::-1])
                
        an = ch.aligner.Chromagnon(fn)
        an.setEchofunc(ch.aligner.dummyEcho)
        an.findBestChannel()
        try:
            an.findAlignParamWave()
        except ValueError:
            continue

        try:
            cwriter.rdr = an.img
            cwriter.holder = an
        except NameError:
            cwriter = ch.chromformat.ChromagnonWriter(out_csv, an.img, an)
        for w in range(an.nw):
            if w != an.refwave:
                writeAlignParmSingle(cwriter, t=t, w=w)
        
        an.findNonLinear2D(npxls=minpxls)
        #return an
        arr, mas = makeNonLinearImg(an)
        an.close()

        try:
            o
        except NameError:
            waves = list(an.wave) + [int(wave) for wave in N.linspace(700,900,(an.nw-1)*3)]#[400, 500, 450]
            if an.nw == 2:
                hdr = imgio.mrcIO.makeHdrFromDim(nx=arr.shape[-1], ny=arr.shape[-2], nz=1, nt=len(fns), nw=arr.shape[0], dtype=arr.dtype, wave=waves)
                hdr.mmm1=  (0,mas[0], 0)#0,0)
                hdr.mm2= (0,mas[-1])#0)
                hdr.mm3= (0,1)
                hdr.mm4= (0,1)
                hdr.mm5= (0,1)
                o = imgio.Writer(out, hdr=hdr)
            elif an.nw > 2:
                out = os.path.splitext(out)[0] + '.tif'
                o = imgio.Writer(out, an.img)
                o.setDim(nz=1, nt=len(fns), nw=arr.shape[0], dtype=N.float32, wave=waves)

        if arr.shape[-2] >= o.shape[-2]:
            if arr.shape[-1] >= o.shape[-1]:
                arr = arr[...,:o.shape[-2],:o.shape[-1]]
            else:
                zeros = N.zeros((o.nw,)+o.shape, o.dtype)
                zeros[...,:arr.shape[-1]] = arr[...,:o.shape[-2],:]
                arr = zeros
        else:
            if arr.shape[-1] < o.shape[-1]:
                zeros = N.zeros((o.nw,)+o.shape, o.dtype)
                zeros[...,:arr.shape[-2],:arr.shape[-1]] = arr
                arr = zeros
            else:
                zeros = N.zeros((o.nw,)+o.shape, o.dtype)
                zeros[...,:arr.shape[-2],:] = arr[...,o.shape[-1]]
                arr = zeros

        for w, a in enumerate(arr):
            #print('t=', t, 'w=', w, a.shape)
            o.writeArr(N.ascontiguousarray(a.astype(N.float32)), t=t, w=w, z=0)
        # in some reasons, the last time frame was not saved, even though it said they were saved.
        # also, frame 13 was zero...
            
    o.close()
    cwriter.fp.close()

    out1 = calcPearson(out)
        
    return out, out1

def makeNonLinearImg(holder):
    """
    return arr with 5 channels

    channel 0: wave 0 + grid
    channel 1: wave 1 + grid
    channel 2: regions
    channel 3: mapyx y
    channel 4: mapyx x
    """
    mas = []
    mnw = holder.nw -1
    for w in range(holder.nw):
        a = holder.get3DArrayRemapped(w=w)
        if a.ndim == 3:
            a = N.max(a, 0)
        try:
            arr
        except NameError:
            arr = N.zeros((holder.nw+mnw*3,) + a.shape, N.float32)
        arr[w] = a

        mas.append(a.max())

    # yx map
    ws = list(range(holder.nw))
    ws.remove(holder.refwave)
    #print(ws)

    for i, w in enumerate(ws):
        #print(holder.nw + 1 + 3*i, holder.nw + 3 + 3*i, arr.shape)
        arr[holder.nw + 1 + 3*i:holder.nw + 3 + 3*i] = holder.mapyx[0,w][(Ellipsis,)+holder.cropSlice[-2:]]

    # draw img and add region
    for i, w in enumerate(ws):
        win = holder.last_win_sizes[0,w]
        win2 = (win + 2) // 4

        shape = holder.img.shape[-2:]
        shiftZYX = ch.cutoutAlign.getShift(holder.alignParms[0,w], [0]+list(shape))
        maxcutY = max(shiftZYX[2], shape[0]-shiftZYX[3])
        maxcutX = max(shiftZYX[4], shape[1]-shiftZYX[5])
        shape = N.subtract(shape, (maxcutY*2, maxcutX*2))

        taas = [[ch.alignfuncs.chopShapeND(shape, win, shiftOrigin=(yi,xi)) for xi in range(2)] for yi in range(2)]

        for yi, taa in enumerate(taas):
            for xi, yxs in enumerate(taa):
                ys, xs = yxs
                for yj, yslc in enumerate(ys):
                    y0 = yslc.start + win2
                    y1 = yslc.stop - win2 + 1
                    #print(y0, y1)
                    #for w, ma in enumerate(mas):
                    arr[w,y0] = mas[w]
                    arr[w,y1] = mas[w]
                    y = yj*2 + yi
                    for xj, xslc in enumerate(xs):
                        x0 = xslc.start + win2
                        x1 = xslc.stop - win2 +1
                        #for w, ma in enumerate(mas):
                        arr[w,:,x0] = mas[w]
                        arr[w,:,x1] = mas[w]
                        x = xj*2 + xi
                        try:
                            if holder.regions[0,w,y,x]:
                                arr[holder.nw+3*i,y0:y1,x0:x1] += 1
                        except IndexError:
                            #print('IndexError----shape: %s w:%i y:%i x:%i' % (holder.regions.shape, w, y,x))
                            pass

    return arr, mas


def writeAlignParmSingle(cwriter, t=0, w=0):
    parm = cwriter.holder.alignParms[0,w]

    cwriter.writer.writerow([t, cwriter.rdr.wave[w]]+list(parm))


### ----analyzis-----
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
    return r0 / r1
    
def calcPearson(fn, out=None):
    if not out:
        out = os.path.splitext(fn)[0] + '_pearson.csv'

    fill = fillFactor(fn)
        
    with open(out, 'w') as o:
        wtr = csv.writer(o)
        with imgio.Reader(fn) as h:
            tlist = list(range(h.nt))
            nw = (h.nw + 3) // 4
            for w in range(nw,h.nw):
                idx = (w - nw) % 3
                if idx == 0:
                    continue
                dim = {1: 'X', 2: 'Y'}[idx]
                wtr.writerow(['w', dim] + tlist)
                if w == (nw+1):
                    wtr.writerow(['fill', ''] + list(fill))
                for t0 in range(h.nt):
                    ref = h.getArr(w=w, t=t0, z=0)
                    line = [w, t0]
                    for t1 in range(h.nt):
                        if t1 <= t0:
                            line.append('')
                        if t1 > t0:
                            #print(w, t1, t0)
                            img = h.getArr(w=w, t=t1, z=0)
                            p = calcPearsonSimple(ref, img)
                            line.append(p)
                    wtr.writerow(line)
    return out

def calcError(dvfn, globalsum, out=None, reft=0, refdvfn=None, refglobalsum=None, originalShape=(512,512)):
    """
    dvfn: _summ.dv
    globalsum: _summ.csv

    reft: index in reference data set (stored as time frame)

    if you like to use different reference file from dvfn,
    refdvfn: _summ.dv
    refglobalsum: _summ.csv

    return out
    """
    if not out:
        out = os.path.splitext(dvfn)[0] + '_errors.csv'

    fill = fillFactor(dvfn) # CHECK not ready for multiple wavelength

    with open(out, 'w') as o:
        wtr = csv.writer(o)

        title = ['w', 'axis', 't', 'dx (nm)', 'dy (nm)', 'dmx (nm)', 'dmy (nm)', 'dr (nm)', 'total (nm)', 'nregions', 'me (nm)', 'ma (nm)', 'sd (nm)', 'pearson']
        wtr.writerow(title)

       # read global params
        with open(globalsum) as h:
            rdr = csv.reader(h)
            [next(rdr) for i in range(2)]
            pxlsiz = N.array([float(p) for p in next(rdr)[2:4]])
            next(rdr)
            header = next(rdr)
            lines = []
            for line in rdr:
                lines.append([float(v) for v in line[2:]])
            parms = N.array(lines)
            #parms = [line for line in rdr]
        if refglobalsum: # assuming the same pixel size
            with open(refglobalsum) as h:
                rdr = csv.reader(h)
                [next(rdr) for i in range(5+reft)]
                truth = N.array([float(v) for v in next(rdr)[2:]])
        else:
            truth = parms[reft]


        
        # get imgSize from dv
        with imgio.Reader(dvfn) as h:

            
            tlist = list(range(h.nt))
            imgSize = N.array((0,h.nx/2), N.float32)
            #pxlsiz = h.pxlsiz[-2:]
            nw = (h.nw + 3) // 4

            if refdvfn:
                hr = imgio.Reader(refdvfn)
            else:
                hr = h

            # crop slice
            ZYX = N.array((1,)+tuple(originalShape))
            mm1 = ch.cutoutAlign.getShift(parms[0], ZYX)[2:]
            mm2 = ch.cutoutAlign.getShift(truth, ZYX)[2:]
            mmd = mm1 - mm2
            crsl1 = []
            crsl2 = []
            for d in range(2):
                n = {0: h.ny, 1: h.nx}[d]
                v = int(mmd[d])
                if v > 0:
                    crsl1.append(slice(0, n-v))
                    crsl2.append(slice(v, n))
                else:
                    crsl1.append(slice(-v, n))
                    crsl2.append(slice(0, n+v))

            for w in range(nw,h.nw):
                idx = (w - nw) % 3
                if idx == 0:
                    continue
                dim = {1: 'X', 2: 'Y'}[idx]

                # local difference
                ref = hr.getArr(w=w, t=reft, z=0)[crsl2]
                
                for t in range(h.nt):
                    img = h.getArr(w=w, t=t, z=0)[crsl1]
                    dif = N.abs(ref - img)
                    dif[0] *= pxlsiz[0] * 1000
                    dif[1] *= pxlsiz[1] * 1000
                    me = dif.mean()
                    ma = dif.max()
                    sd = dif.std()
                    pc = calcPearsonSimple(ref, img)

                    # global distances
                    # CHECK not ready for multiple wavelengths
                    diff = N.abs(parms[t] - truth)
                    #if t == 1:
                    #    print(diff, pxlsiz)
                    dy,dx = diff[1:3] * (pxlsiz * 1000)
                    dr = (imgGeo.euclideanDist(imgGeo.rotate(imgSize, N.radians(diff[3])), imgSize))*(N.mean(pxlsiz)*1000)
                    dmy = diff[-2] * imgSize[1] * pxlsiz[-2] * 1000
                    dmx = diff[-1] * imgSize[1] * pxlsiz[-1] * 1000

                    total = N.sqrt(dy**2 + dx**2 + dr**2 + dmy**2 + dmx**2)

                    wtr.writerow([w,dim,t,dx,dy,dmx,dmy,dr,total,fill[t],me,ma,sd, pc])
    if refdvfn:
        hr.close()
    
    return out

def plotErrors(fn, what='me (nm)', axis='X', vmin=None, vmax=None):
    with open(fn) as h:
        rdr = csv.reader(h)
        header = next(rdr)

        adx = header.index('axis')
        idx = header.index(what)

        vals = N.array([float(line[idx]) for line in rdr if line[adx] == axis.upper()])
    n = int(len(vals) ** 0.5)
    a = vals.reshape((n,n))
    ma = N.max(a)
    mi = N.min(a)
    print('max', ma)
    print('min', mi)
    if not vmin:
        vmin = mi
    if not vmax:
        vmax = ma
    P.figure()
    P.hold(0)
    P.imshow(a, cmap='rainbow', vmin=vmin, vmax=vmax)
    return P.colorbar()

def plotMap(summdv, axis='x', pxlsiz=0.08, minwin=64):
    with imgio.Reader(summdv) as h:
        w = {'x': 3, 'y': 4}[axis.lower()]
        #idx = {'x': -1, 'y': -2}[axis.lower()]
        a = N.array([h.getArr(w=w, t=t, z=0)[minwin//2:-minwin,minwin//2:-minwin] for t in range(h.nt)])
        aa = N.average(a, axis=0)
        P.figure()
        aa *= pxlsiz * 1000#h.pxlsiz[idx]
        P.imshow(aa, cmap='rainbow', vmin=aa.min(), vmax=aa.max())
        P.colorbar()
        
    
## =============== examine how local alignment is conserved ============
# 20181025YAM296Local
# 1  2  3  4  5  ....  20
# 40 ...           22  21
# 41 ...           59  60

def average_locals(fns, out_prefix=None, minpxls=60, n=20, horizontal=True, start_num=1):
    nt = len(fns)
    ts = [int(os.path.splitext(fn)[0].split('_')[-1]) for fn in fns]

    inds = N.arange(start_num, nt+start_num)
    inds = inds.reshape((-1, n))
    inds[1::2] = inds[1::2][:,::-1]
    if horizontal:
        suffix = 'hori'
    else:
        inds = inds.T
        suffix = 'vert'
    outs = []
    for ta, idx in enumerate(inds):
        ids = [i for i, t in enumerate(ts) if t in idx]
        fns0 = [fns[i] for i in ids]
        if 0:#ta is 2:
            print(fns0)
            return
        #else:
        #    continue

        out = os.path.commonprefix(fns) + '_%saveraged_%i.dv' % (suffix, ta)
        out = ch.alignfuncs.averageImage(fns0, out=out)#suffix='_%saveraged_%i' % (suffix, ta), ext='.dv')
        outs.append(out)

    #if not out_prefix:
    #    out_prefix = os.path.commonprefix(outs) + '_averaged_%s' % suffix
    #dones = examine_local(outs, out_prefix=out_prefix, minpxls=minpxls, use_suffix_num=True)
    #[os.remove(out) for out in outs]

    return outs #dones

def average_square(fns, nline=20, nstep=5, proceed2examine=True, minpxls=60, out_prefix=None, start_num=1):
    if nline % nstep:
        raise ValueError('nstep must be a divisor of nline')
    
    nt = len(fns)
    ts = [int(os.path.splitext(fn)[0].split('_')[-1]) for fn in fns]

    inds = N.arange(start_num, (nt+start_num))
    inds = inds.reshape((-1, nline))
    inds[1::2] = inds[1::2][:,::-1]

    nboxes = nline // nstep
    slcs = []
    for y in range(nboxes):
        for x in range(nboxes):
            slcs.append([slice(y*nstep, (y+1)*nstep), slice(x*nstep, (x+1)*nstep)])#[slice(i*nstep, (i+1)*nstep) for d in range(2)])

    outs = []
    prefix = os.path.commonprefix(fns)
    logfile = prefix + '_boxaverage.log'
    with open(logfile, 'w') as log:
        wtr = csv.writer(log)
        for ta, slc in enumerate(slcs):
            idx = inds[slc].ravel()
            ids = [i for i, t in enumerate(ts) if t in idx]
            fns0 = [fns[i] for i in ids]
            nums = sorted([int(os.path.splitext(fn)[0].split('_')[-1]) for fn in fns0])
            wtr.writerow(nums)

            ty = ta // nboxes
            tx = ta % nboxes

            out = prefix + '_boxaveraged_x%i_y%i.dv' % (tx, ty)
            out = ch.alignfuncs.averageImage(fns0, out=out)#, ext='.dv')

            outs.append(out)

    if proceed2examine:
        if not out_prefix:
            out_prefix = os.path.commonprefix(outs) + '_averaged_%s' % 'box'
        dones = examine_local(outs, out_prefix=out_prefix, minpxls=minpxls, use_suffix_num=True)
        [os.remove(out) for out in outs]
        return dones
    else:
        return outs
        

# ------ distance dependence test from pearson correlation output
def test_distance_pearson_box(fn, out=None, stepsize_um=100, nstep=5, remove_zero=False):
    """
    using box averaging
    """
    if not out:
        base, ext = os.path.splitext(fn)
        suffix = '_dist'
        if remove_zero:
            suffix += 'r0'
        out = base + suffix + ext

    start = 1
    with open(fn) as h:
        rdr = csv.reader(h)
        for d in range(len(('x', 'y'))):
            header = next(rdr)
            #axis = header[0]
            if header[0] == 'w' and d == 0:
                #axis = header[1]
                start += 1
            rowlist = [int(r) for r in header[start:]]#1:]]
            nrow = len(rowlist)
            if d == 0:
                yx = N.zeros((2, nrow, nrow), N.float32)

            for row in rowlist:
                line = next(rdr)
                ll = int(line[start-1])#0])
                if ll != row:
                    raise ValueError('line number and row number has to be consistent')
                vals = [float(v) for v in line[start+1+row:]]#2+row:]]
                yx[d,ll,1+row:] = vals

    #regions = []
    nrow2 = int(nrow**0.5)

    ind = N.indices((nrow2, nrow2), dtype=N.float32)
    ii = ind.T.reshape(nrow, 2)
    dists = N.empty((nrow**2), N.float32)
    vals = N.empty((2, nrow**2), N.float32)
    for r in rowlist:
        x = r % 4
        y = r // 4
        line = yx[:,r].copy()
        line[:,:r] = yx[:,:r,r]

        dist = distance.cdist(ii, [[x,y]])
        #dists += dist.ravel().tolist()
        dists[r*nrow:(r+1)*nrow] = dist.reshape((nrow,))

        #vals += line.ravel().tolist()
        vals[:,r*nrow:(r+1)*nrow] = line.reshape((2,-1))
        #regions.append(line.reshape((2,nrow2, nrow2)))
    #return regions

    if remove_zero:
        ind = N.nonzero(dists)[0]
        dists = dists[ind] #* (stepsize_um * nrow2)
        vals = vals[:,ind]
    dists *= stepsize_um * nrow2 / 1000.

    sheet = N.empty((3,dists.shape[0]), dists.dtype)
    sheet[0] = dists
    sheet[1:] = vals

    with open(out, 'w') as o:
        wtr = csv.writer(o)

        #wtr.writerow(['dist'] + list(dists))
        #wtr.writerow(['X'] + list(vals[0]))
        #wtr.writerow(['Y'] + list(vals[1]))

        wtr.writerow(['dist', 'X', 'Y'])
        [wtr.writerow(s) for s in sheet.T]
        
    #return dists, vals#N.array(dists), N.array(vals)
    return out

## ----- analysis
def arrPearson(fn):#, plot=False, dim=0):
    with open(fn) as h:
        rdr = csv.reader(h)
        header = next(rdr)
        start = 2
        if header[0] == 'w':
            start += 1
        nrow = int(header[-1])+1
        canvas = N.zeros((2, nrow, nrow), N.float32)
        
        start0 = start
        r = 0
        w = 0
        for line in rdr:
            if line[0] in ('w', 'Y'):
                start = start0
                r = 0
                w += 1
                #print(line)#'line')
                continue
            elif line[0] == 'fill':
                continue
            canvas[w, r, (r+1):] = [float(l) for l in line[start:]]
            #print(r, start)
            
            
            start += 1
            r += 1

    #if plot:
    #    from Priithon.all import P
    #    x = N.arange(nrow)
    #    P.pcolor(x, x, canvas[dim], vmin=0, vmax=1.0, cmap='rainbow')
    #    P.colorbar()

    return canvas

def plotPearsonArr(arr, dim=0):
    x = N.arange(arr.shape[-1])#nrow)
    P.pcolor(x, x, arr[dim], vmin=0, vmax=1.0, cmap='rainbow')
    P.colorbar()

def fillFactor(sumdv):
    h = imgio.Reader(sumdv)
    ret = []
    for t in range(h.nt):
        a = h.getArr(w=2, t=t, z=0)
        x = N.nonzero(a.ravel())[0]
        ret.append(x.size / a.size)
    return ret
    
# main
if __name__ == '__main__':
    import argparse, glob

    description = r"""Examine local alignment"""
            
    p = argparse.ArgumentParser(description=description)


    p.add_argument('fns', nargs='*',
                       help='target image files (required)')
    p.add_argument('--out_prefix', '-O', default=None,
                       help='output filename prefix (default=commonprefix + averaged_hori)')
    p.add_argument('--minpxls', '-p', type=int, default=MINPXL,
                       help='number of minimum pixel (default=%i)' % MINPXL)
    #p.add_argument('--horizontal', '-h', action='store_true',
    #                   help='horizontal (default=False))
    p.add_argument('--average', '-a', action='store_true',
                       help='do average (default=False)')
    p.add_argument('--use_suffix_num', '-u', action='store_true',
                       help='use suffix number in the filename as t (default=False)')
    p.add_argument('--start_num', '-n', type=int, default=1,
                       help='starting number (default=%i)' % 1)

    options = p.parse_args()

    average = options.average
    del options.average
    if average:
        del options.use_suffix_num
        out = average_square(**options.__dict__)#proceed2examine=False):#average_locals()
    else:
        del options.start_num
        out = examine_local(**options.__dict__)
    print(out, 'saved')

