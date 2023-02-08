#!/usr/bin/env priithon

import os, sys, time, csv
import Chromagnon as ch
import numpy as N

from Priithon.all import F
from PriCommon import imgGeo
from imgio import mrcIO, Mrc


METHODS=['quadrisection', 'logpolar', 'simplex']
#PARM_EXT = 'csv'

NOISE_STATS=['Gaussian', 'Poisson']

def repeat(fns, n=10):
    outs = []
    base = os.path.commonprefix(fns)
    for i in range(n):
        out = base + '_summary_%i.csv' % i
        print(out)
        outs = makeFiles(fns)
        fns2 = fns + outs
        print('iteration %i comparing %i images to make %s' % (i, len(fns2), out))
        out = compare(fns2, out=out)
        outs.append(out)
    return outs

def makeFiles(fns, std=10, div_step=50, div_max=800):#1000):
    """
    makes a series of images added Gaussain and Poisson noise

    std: standard deviation for Gaussian, and mean=std*10 for Poisson
    div_step: the step that the original image is divided while noise is added
    div_max: the maximum value that the original image is divided

    return output filenames
    """
    
    outs = []
    
    for fn in fns:
        a = Mrc.bindFile(fn)

        
        for ns in NOISE_STATS:
            hdr = mrcIO.makeHdr_like(a.Mrc.hdr)
        
            if ns == NOISE_STATS[0]:
                noise = F.noiseArr(a.shape, stddev=std, mean=0)
            else:
                noise = F.poissonArr(a.shape, mean=std*10)
            steps = range(div_step, div_max+div_step, div_step)
            ag = [a/c + noise for c in steps]
            for i, arr in enumerate(ag):
                val = steps[i]
                if hasattr(arr, "Mrc"):
                    del arr.Mrc
                if arr.dtype == N.float64:
                    arr = arr.astype(N.float32)
                    hdr.PixelType = 2

                out = a.Mrc.path + ns + '%04d' % val
                Mrc.save(arr, out, ifExists='overwrite', hdr=hdr)
                outs.append(out)
    return outs

def compare(fns, methods=METHODS, refwave=0, tz={1:0}, t=0, out=None, imgsize=512, truth=[3,2,-0.5,1.001001,1.002004]):
    if not out:
        out = os.path.commonprefix(fns) + '_summary.csv'
    truth = N.array(truth)
    imgSize = N.array((0,imgsize), N.float32)
        
    o = open(out, 'w')
    cwtr = csv.writer(o)

    cwtr.writerow(['name', 'NoiseModel', 'method', 'wave', 'noise', 'ty(um)', 'tx(um)', 'r', 'my', 'mx', 'dty(nm)', 'dtx(nm)', 'dr(nm)', 'dmy(nm)', 'dmx(nm)', 'total(nm)', 'timeTaken(sec)'])
        
    for method in methods:

        met = ch.alignfuncs.IF_FAILED[METHODS.index(method)]
        #outs = []
        #OLD_EXT = ch.chromformat.PARM_EXT
        #ch.chromformat.PARM_EXT = PARM_EXT

        old_stdout = sys.stdout

        for fn in fns:
            logfn = os.path.extsep.join((fn + '_' + method, 'log'))
            sys.stdout = open(logfn, 'w')

            #base = os.path.splitext(fn)[0]
            name = os.path.basename(fn)#base)
            if name[-1].isdigit():
                for i in range(4):
                    if name[-(i+1)].isdigit():
                        noise = int(name[-(i+1):])
                    else:
                        break
            else:
                noise = 0

            if 'Gaussian' in fn:
                noiseModel = 'Gaussian'
            elif 'Poisson' in fn:
                noiseModel = 'Poisson'
            else:
                noiseModel = 'None'

            if 'deconB' in fn:
                wave = 442
            elif 'deconG' in fn:
                wave = 525

            an = ch.aligner.Chromagnon(fn)
            an.setIf_failed(met)
            an.setMaxError(0.0000001)

            #an.setParmSuffix('_' + method)
            if refwave is not None:
                an.setReferenceWave(refwave)
                an.fixAlignParmWithCurrRefWave()
            else:
                an.findBestChannel()
            an.setEchofunc(_echo)

            an.setRefImg()

            for w in range(an.img.nw):
                if (w == an.refwave):
                    continue

                if an.img.nz > 1:
                    img = an.img.get3DArr(w=w, t=t)

                    zs = N.round_(N.array(an.refzs)-tz[w]).astype(N.int)

                    if zs.max() >= an.img.nz:
                        zsbool = (zs < an.img.nz)
                        zsinds = N.nonzero(zsbool)[0]
                        zs = zs[zsinds]

                    imgyx = ch.alignfuncs.prep2D(img, zs=zs)
                    del img

                else:
                    imgyx = an.img.getArr(w=w, t=t, z=0)

                initguess = N.zeros((5,), N.float32)
                #initguess[:3] = ret[w,1:4] # ty,tx,r
                initguess[3:] = 1#ret[w,5:7] # my, mx

                clk0 = time.clock()

                try:
                    ty,tx,r,my,mx = ch.alignfuncs.iteration(imgyx, an.refyx, maxErr=an.maxErrYX, niter=an.niter, phaseContrast=an.phaseContrast, initguess=initguess, echofunc=an.echofunc, max_shift_pxl=an.max_shift_pxl, if_failed=an.if_failed)
                except ZeroDivisionError:
                    if an.phaseContrast:
                        ty,tx,r,my,mx = ch.alignfuncs.iteration(imgyx, an.refyx, maxErr=an.maxErrYX, niter=an.niter, phaseContrast=False, initguess=initguess, echofunc=an.echofunc, max_shift_pxl=an.max_shift_pxl, if_failed=an.if_failed)

                clk1 = time.clock()
                tt = clk1-clk0

                diff = N.abs(truth - (ty,tx,r,my,mx))
                dy,dx = diff[:2] * (an.pxlsiz[1:] * 1000)
                dr = (imgGeo.euclideanDist(imgGeo.rotate(imgSize, N.radians(diff[2])), imgSize))*(N.mean(an.pxlsiz[1:])*1000)
                dmy = diff[3] * imgsize * an.pxlsiz[-2] * 1000
                dmx = diff[4] * imgsize * an.pxlsiz[-1] * 1000
                total = N.sqrt(dy**2 + dx**2 + dr**2 + dmy**2 + dmx**2)

                cwtr.writerow([name, noiseModel, method, wave, noise, ty*an.pxlsiz[1], tx*an.pxlsiz[2], r, my, mx, dy, dx, dr, dmy, dmx, total, tt])

            an.close()
            sys.stdout.close()
            del imgyx
            del an

    #ch.chromformat.PARM_EXT = OLD_EXT
    #sys.stdout = old_stdout
    sys.stdout = sys.__stdout__
    o.close()

    return out#s

compare.__doc__ = """
    method: %s
    refwave: None or channel index

    return output files""" % str(METHODS)


def _echo(msg, skip_notify=False):
    pass

def summarize(csvs, out=None):
    if not out:
        out = os.path.commomprefix(csvs)

    o = open(out, 'w')
    cwtr = csv.writer(o)

    cwtr.writerow(['name', 'method', 'time', 'wave', 'tz', 'ty', 'tx', 'r', 'mz', 'my', 'mx', 'timeTaken'])
    
    for fn in csvs:
        base = os.path.splitext(fn)[0]
        method = base.split('_')[-1]
        name = os.path.basename(base[:-(len(method)+1)])
        
        rd = ch.ChromagnonReader(fn)
        row = rd.alignParms


if __name__ == '__main__':
    print(sys.argv[1:])
    print(repeat(sys.argv[1:]))
