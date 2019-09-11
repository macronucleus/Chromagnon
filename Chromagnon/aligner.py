from __future__ import print_function
import os, sys, six
import numpy as N
from scipy import ndimage as nd

try:
    from PriCommon import imgGeo, imgFilters, xcorr, fntools
    from Priithon.all import Mrc, U
    import imgio
except ImportError:
    from Chromagnon.PriCommon import imgGeo, imgFilters, xcorr, fntools
    from Chromagnon.Priithon.all import Mrc, U
    from Chromagnon import imgio

if sys.version_info.major == 2:
    import alignfuncs as af, cutoutAlign, chromformat
elif sys.version_info.major >= 3:
    try:
        from . import alignfuncs as af, cutoutAlign, chromformat
    except (ValueError, ImportError):
        from Chromagnon import alignfuncs as af, cutoutAlign, chromformat

if __name__ == '__main__':
    NCPU = os.cpu_count()
else:
    NCPU = 1

MAXITER = 20
MAXERROR = 0.001

# parameter structure
ZYXRM_ENTRY=['tz','ty','tx','r','mz','my','mx']
NUM_ENTRY=len(ZYXRM_ENTRY)

ZMAG_CHOICE = ['Auto', 'Always', 'Never']
ACCUR_CHOICE_DIC = {'fast': 1, 'good': 2, 'best': 10}
#ACCUR_CHOICE = [x[0] for x in sorted(list(ACCUR_CHOICE_DIC.items()), key=lambda x: x[1])]
ACCUR_CHOICE = sorted(list(ACCUR_CHOICE_DIC.values()))
#print('accu', ACCUR_CHOICE)
MAXITER_3D = ACCUR_CHOICE_DIC['fast']#good']

# file extention
IMG_SUFFIX='_ALN'
WRITABLE_FORMATS = [fm for fm in ('tif', 'dv', 'ome.tif') if fm in imgio.WRITABLE_FORMATS]

# chromagnon file format
IDTYPE = 101

class Chromagnon(object):

    def __init__(self, fn):
        """
        usage: 
        ## channel alignment
        ## fn: the reference image
        >>> an = Chromagnon(fn)
        >>> an.findBestChannel()
        >>> an.findAlignParamWave()
        >>> an.setRegionCutOut()
        >>> an.saveAlignedImage()
        >>> out = an.saveParm()

        ## fn2: the target image
        >>> an = Chromagnon(fn2)
        >>> an.loadParm(out)
        >>> an.setRegionCutOut()
        >>> out = an.saveAlignedImage()

        ## time frame alignment
        ## fn: the reference image (time projected for 10 frames for example)
        >>> an = Chromagnon(fn)
        >>> an.findBestTimeFrame()
        >>> an.findAlignParamTime()
        >>> an.setRegionCutOut()
        >>> an.saveAlignedImage()

        """
        self.img = imgio.Reader(fn)

        self.copyAttr()
        self.setMaxError()
        self.setMaxIter()
        self.setMaxIter3D()
        self.setReferenceTime()
        self.setReferenceWave()
        self.setReferenceZIndex()
        self.setReferenceXIndex()
        self.setImageCenter()
        self.setMultipageTiff()
        self.setphaseContrast()
        self.setEchofunc()
        self.setProgressfunc()
        self.setImgSuffix()
        self.setFileFormats()
        self.setParmSuffix()
        self.setIf_failed()
        self.setDefaultOutPutDir()
        self.setMicroscopeMap()
        
        self.alignParms = N.zeros((self.img.nt, self.img.nw, NUM_ENTRY), N.float32)
        self.alignParms[:,:,4:] = 1
        self.cropSlice = [Ellipsis, slice(None), slice(None), slice(None)]

        self.saturation = N.zeros((self.img.nt, self.img.nw, 3))

        self.refyz = None
        self.refyx = None
        
        self.mapyx = None
        self.regions = None
        self.byteorder = '<'
        self.setMaxShift()
        self.setZmagSwitch()

    def close(self):
        if hasattr(self, 'img') and hasattr(self.img, 'close'):
            self.img.close()

            
    def copyAttr(self):
        if hasSameWave(self.img):
            raise 'The image contains multiple channels with the same wavelength. Please use a unique wavelength for each channel'
        self.nt = self.img.nt
        self.nw = self.img.nw
        self.nz = self.img.nz
        self.ny = self.img.ny
        self.nx = self.img.nx
        self.dtype = self.img.dtype
        self.dirname = os.path.dirname(self.img.filename)
        self.file = self.path = os.path.basename(self.img.filename)

        self.t = self.img.t
        self.w = self.img.w
        self.z = self.img.z
        self.y = self.img.y
        self.x = self.img.x
        self.wave = self.img.wave
        self.shape = self.img.shape

        self.pxlsiz = self.img.pxlsiz

        self.get3DArr = self.img.get3DArr # be carefull since after closing file, and reopen with self.img = im.load(), then this does not work anymore

    def setImgSuffix(self, suffix=IMG_SUFFIX):
        self.img_suffix = suffix

    def setFileFormats(self, ext='tif'):
        if not ext.startswith(os.path.extsep):
            ext = os.path.extsep + ext
        self.img_ext = ext

    def setParmSuffix(self, suffix=''):
        self.parm_suffix = suffix
                
    def setMaxError(self, val=MAXERROR):
        """
        if pixel size is set, then val is um
        otherwise, in pixel

        set self.maxErr, self.maxErrYX, self.maxErrZ
        """
        self.maxErr = val

        self.maxErrYX = self.maxErr / N.mean(self.img.pxlsiz[1:])
        self.maxErrZ = self.maxErr / self.img.pxlsiz[0]

    def setMaxIter(self, val=MAXITER):
        """
        set the maximum number of iterations

        set self.niter
        """
        self.niter = val

    def setMaxIter3D(self, val=MAXITER_3D):
        """
        set the maximum number of iterations for 3D cross correlation

        set self.niter_3D
        """
        if isinstance(val, six.string_types):
            val = ACCUR_CHOICE_DIC[val]
        self.niter_3D = val

    def setMaxShift(self, um=af.MAX_SHIFT):
        if um:
            self.max_shift_pxl = um / N.mean(self.img.pxlsiz[1:])#:2])
            if self.max_shift_pxl > min((self.img.nx, self.img.ny)):
                self.max_shift_pxl = min((self.img.nx, self.img.ny))
        else:
            self.max_shift_pxl = None

    def setZmagSwitch(self, value='Always'):#'Auto'):
        self.zmagSwitch = value

    def setEchofunc(self, func=None):
        self.echofunc = func

    def echo(self, msg=''):
        if self.echofunc:
            self.echofunc(msg)
        else:
            print(msg)

    def setProgressfunc(self, func=None):
        self.progressfunc = func

    def progress(self):
        if self.progressfunc:
            next(self.progressfunc)
            
    def setIf_failed(self, if_failed=af.IF_FAILED[0]):
        self.if_failed = if_failed
        
    def setReferenceTime(self, t=0):
        """
        set self.reftlist
        """
        iforgot="""
        if tlist is None:
            self.reftlist = xrange(self.img.nt)
        elif len(tlist) != self.img.nt:
            raise ValueError, 'tlist must have the length of time frames'
        else:
            self.reftlist = tlist"""
        self.reftime = t

    def setReferenceWave(self, wave=None):
        """
        set self.refwave (index)
        """
        self.refwave = wave

    def setReferenceZIndex(self, zs=None):
        """
        set self.refzs
        reset everytime at every time frame
        """
        self.refzs = zs

    def setReferenceXIndex(self, xs=None):
        """
        set self.refxs
        reset everytime at every time frame
        """
        self.refxs = xs

    def setAlignParam(self, param):
        """
        set 
        """
        # expand drift results if necessary
        if (self.img.nt / float(param.shape[0])) > 1:
            param2 = N.empty((self.img.nt, self.img.nw, param.shape[-1]), param.dtype)
            for w in range(self.img.nw):
                for d in range(param.shape[-1]):
                    if param.shape[0] == 1:
                        param2[:,w,d] = param[0,w,d]
                    else:
                        param2[:,w,d] = nd.zoom(param[:,w,d], self.img.nt / float(param.shape[0]))
            param = param2
        
        self.alignParms[:] = param[:self.img.nt]

        self.fixAlignParmWithCurrRefWave()


    def fixAlignParmWithCurrRefWave(self):
        """
        re-organize align parameters and mapping parameters according to the current reference wave
        """
        param = N.empty((self.img.nt, self.img.nw, self.alignParms.shape[-1]), self.alignParms.dtype)

        for t in range(self.img.nt):
            for w in range(self.img.nw):
                param[t,w] = self.getShift(w,t)
        self.alignParms[:] = param

        if self.mapyx is not None:
            mapyx = N.empty_like(self.mapyx)
            for t, tmp in enumerate(self.mapyx):
                for w, wmp in enumerate(tmp):
                    mapyx[t,w] = wmp - self.mapyx[t,self.refwave]
            self.mapyx = mapyx

    def setImageCenter(self, yx=None):
        """
        use this function to chage image center

        set self.dyx
        """
        if yx is None:
            self.dyx = (0,0)
        else:
            center = N.array((self.img.ny,self.img.nx), N.float32) // 2
        
            self.dyx = yx - center


    def setphaseContrast(self, phaseContrast=True):
        self.phaseContrast = phaseContrast

    def setDefaultOutPutDir(self, outdir=None):
        if outdir and not os.path.isdir(outdir):
            os.path.makedirs(outdir)
        self.outdir = outdir

    def setMicroscopeMap(self, fn=None):
        if fn:
            rdr = chromformat.ChromagnonReader(fn, self.img, self, setmap2holder=False)
            self.microscopemap = rdr.readMapAll()
        else:
            self.microscopemap = None
        
    def getSaturation(self, w=0, t=0, only_neighbor=True):
        """
        return number of saturated pixels
        """
        if not self.saturation[t,w,0]:
            arr = self.img.get3DArr(w=w, t=t)
            self.saturation[t,w,1:] = af.measureSaturation(arr)
            self.saturation[t,w,0] = 1
        if only_neighbor:
            return self.saturation[t,w,-1]
        else:
            return self.saturation[t,w,1:]
        
            
        
    ### find alignment parameters of multicolor images ####
        
    def findBestChannel(self, t=0):
        """
        the reference wavelength is determined from the wavelength and intensity
        
        set self.refwave (in index)
        """
        if self.refwave is not None:
            self.refwave = self.img.getWaveIdx(self.refwave)
        else:
            # if time laplse
            if self.img.nt > 1:
                # how large the object is...
                arrs = [self.img.get3DArr(w=w, t=t).ravel() for w in range(self.img.nw)]
                modes = [imgFilters.mode(a[::50]) for a in arrs]
                fpxls = [N.where(a > modes[i])[0].size/float(a.size) for i, a in enumerate(arrs)]
                # bleach half time
                halfs = []
                if self.nt > 3:
                    for w in range(self.nw):
                        mes = [self.img.get3DArr(w=w, t=t).mean() for t in range(self.nt)]
                        parm, check = U.fitDecay(mes)
                        halfs.append(parm[-1] / float(self.nt))

                    channels = N.add(fpxls, halfs)
                    refwave = N.argmax(channels)
                else:
                    refwave = 0
                print('The channel to align is %i' % refwave)

            # if wavelengths are only 2, then use the channel 0
            elif self.img.nw <= 2:
                refwave = 0

            # take into account for the PSF distortion due to chromatic aberration
            elif self.img.nw > 2:
                pwrs = N.array([self.img.get3DArr(w=w, t=t).mean() for w in range(self.img.nw)])
                # the middle channel should have the intermediate PSF shape
                waves = [self.img.getWaveFromIdx(w) for w in range(self.img.nw)]
                waves.sort()
                candidates = [self.img.getWaveIdx(wave) for wave in waves[1:-1]]

                # remove channels with lots of saturation
                candidates = [w for w in candidates if not self.getSaturation(w=w,t=t)]

                # find out channels with enough signal
                thr = N.mean(pwrs) / 1.25
                bol = N.where(pwrs[candidates] > thr, 1, 0)
                if N.any(bol):
                    ids = N.nonzero(bol)[0]
                    if len(ids) == 1:
                        idx = ids[0]
                    else:
                        candidates = N.array(candidates)[ids]
                        idx = N.argmax(pwrs[candidates])

                    refwave = candidates[idx]
                else:
                    refwave = N.argmax(pwrs)
            self.refwave = refwave

        self.fixAlignParmWithCurrRefWave()

        self.progress()

    
    def setRefImg(self, refyz=None, refyx=None, removeEdge=True):
        """
        set self.refyz and self.refyx
        """
        if refyz is None or refyx is None:
            if self.img.nz > 1:
                ref = self.img.get3DArr(w=self.refwave, t=self.reftime)
                ref = af.fixSaturation(ref, self.getSaturation(w=self.refwave, t=self.reftime))
                
                if refyx is None:
                    if self.refzs is None:
                        self.refzs = af.findBestRefZs(ref)
                        #print('using slices', self.refzs)
                        if self.echofunc:
                            self.echofunc('using slices %s' % self.refzs, skip_notify=True)

                    self.zs = N.array(self.refzs)
                    refyx = af.prep2D(ref, zs=self.refzs, removeEdge=removeEdge)

                if refyz is None:
                    if self.refxs is None:
                        self.refxs = af.findBestRefZs(ref.T, sigma=-0.5)
                    self.xs = N.array(self.refxs)
                    #if self.img.nz <=5:
                    #    removeEdge = False
                    refyz = af.prep2D(ref.T, zs=self.refxs, removeEdge=removeEdge)
                del ref
            elif refyx is None:
                refyx = self.img.getArr(w=self.refwave, t=self.reftime, z=0)
                refyx = af.fixSaturation(refyx, self.getSaturation(w=self.refwave, t=self.reftime))

        self.refyz = refyz
        self.refyx = refyx
        
    def findAlignParamWave(self, t=0, doWave=True, init_t=None):
        """
        do findBestChannel() before calling this function

        init_t: time frame for the initial guess, None uses the same as t

        return nw*[tz,ty,tx,r,mz,my,mx]
        """
        if self.refyz is None or self.refyx is None:
            self.setRefImg()

        if init_t is None:
            init_t = t

        ret = self.alignParms[init_t].copy()
        
        if N.any(ret[:,:-3]):
            doXcorr = False
        else:
            doXcorr = True

        for w in range(self.img.nw):
            if (doWave and w == self.refwave) or (not doWave and w != self.refwave):
                continue

            # vertical alignment
            if self.img.nz > 1:
                img = self.img.get3DArr(w=w, t=t)
                img = af.fixSaturation(img, self.getSaturation(w=w, t=t))
                
                # get initial guess if no initial guess was given
                if doXcorr:
                    self.echo('making an initial guess for channel %i' % w)
                    ref = self.img.get3DArr(w=self.refwave, t=t)
                    prefyx = N.max(ref, 0)
                    pimgyx = N.max(img, 0)
                    if self.max_shift_pxl:
                        searchRad = self.max_shift_pxl * 2
                        if searchRad > min((self.img.nx, self.img.ny)):
                            searchRad = min((self.img.nx, self.img.ny))
                    else:
                        searchRad = None
                    yx, c = xcorr.Xcorr(prefyx, pimgyx, phaseContrast=self.phaseContrast, searchRad=searchRad)
                    ret[w,1:3] = yx
                    #print(yx)
                    del ref, c
                # create 2D projection image
                self.echo('calculating shifts for time %i channel %i' % (t, w))
                xs = N.round_(self.refxs-ret[w,2]).astype(N.int)
                if xs.max() >= self.img.nx:
                    xsbool = (xs < self.img.nx)
                    xsinds = N.nonzero(xsbool)[0]
                    xs = xs[xsinds]

                imgyz = af.prep2D(img.T, zs=xs)

                # add X corr for Z 20190826
                if doXcorr:
                    if self.max_shift_pxl:
                        searchRad = [searchRad, searchRad * (self.img.pxlsiz[0]/self.img.pxlsiz[1])]
                        if searchRad[1] > self.img.nz:
                            searchRad[1] = self.img.nz
                    yz, c = xcorr.Xcorr(self.refyz, imgyz, phaseContrast=self.phaseContrast, searchRad=searchRad)
                    ret[w,0] = yz[1]
                    #print(yz, ret[w])
                    
                # try quadratic cross correlation
                zdif = max(self.refzs) - min(self.refzs)
                zzoom = 1.

                if self.zmagSwitch != ZMAG_CHOICE[2] and not ((zdif <= 7 or self.img.nz <= 10) and self.zmagSwitch == ZMAG_CHOICE[0]): # not "never" and go for zmag
                    initguess = N.zeros((5,), N.float32)
                    initguess[:2] = ret[w,:2][::-1]
                    initguess[3:] = ret[w,4:6][::-1]

                    if zdif > 3 and self.img.nz > 10 and self.zmagSwitch == ZMAG_CHOICE[1]: # always
                        if_failed = 'simplex'
                    else:
                        if_failed = af.IF_FAILED[-1] # 'terminate' -> xcorr

                    if (zdif <= 7 or self.img.nz <= 10) and self.zmagSwitch == ZMAG_CHOICE[1]: # always but number of z sections is not enough
                        zzoom = imgyz.shape[0] / imgyz.shape[1]
                        self.echo('Z axis zoom factor=%.2f' % zzoom)
                        imgyz = nd.zoom(imgyz, (1, zzoom))
                        refyz = nd.zoom(self.refyz, (1, zzoom))
                        maxErrZ = self.maxErrZ * zzoom
                    else:
                        refyz = self.refyz
                        maxErrZ = self.maxErrZ
                        
                    #return imgyz, refyz
                    val, check = af.iteration(imgyz, refyz, maxErr=(self.maxErrYX, maxErrZ), niter=self.niter, phaseContrast=self.phaseContrast, initguess=initguess, echofunc=self.echofunc, max_shift_pxl=self.max_shift_pxl, if_failed=if_failed)

                    #if check:# is not None:
                    ty2,tz,_,_,mz = val#check
                    ret[w,0] = tz / zzoom
                    ret[w,4] = mz
                    if not check: # chage to normal cross correlation
                        initguess = ret[w,:2][::-1]
                        yz = af.iterationXcor(imgyz, refyz, maxErr=(self.maxErrYX,maxErrZ), niter=self.niter, phaseContrast=self.phaseContrast, initguess=initguess, echofunc=self.echofunc)
                        ret[w,0] = yz[1]
                # since number of section is not enough, do normal cross correlation
                else:
                    initguess = ret[w,:2][::-1]
                    yz = af.iterationXcor(imgyz, self.refyz, maxErr=(self.maxErrYX,self.maxErrZ), niter=self.niter, phaseContrast=self.phaseContrast, initguess=initguess, echofunc=self.echofunc)
                    ret[w,0] = yz[1]


                zs = N.round_(self.refzs-ret[w,0]).astype(N.int)
                if zs.max() >= self.img.nz:
                    zsbool = (zs < self.img.nz)
                    zsinds = N.nonzero(zsbool)[0]
                    zs = zs[zsinds]

                imgyx = af.prep2D(img, zs=zs)
                del img
            else:
                imgyx = self.img.getArr(w=w, t=t, z=0)

            initguess = N.zeros((5,), N.float32)
            initguess[:3] = ret[w,1:4] # ty,tx,r
            initguess[3:] = ret[w,5:7] # my, mx
            try:
                val, check = af.iteration(imgyx, self.refyx, maxErr=self.maxErrYX, niter=self.niter, phaseContrast=self.phaseContrast, initguess=initguess, echofunc=self.echofunc, max_shift_pxl=self.max_shift_pxl, if_failed=self.if_failed)
            except ZeroDivisionError:
                if self.phaseContrast:
                    val, check = af.iteration(imgyx, self.refyx, maxErr=self.maxErrYX, niter=self.niter, phaseContrast=False, initguess=initguess, echofunc=self.echofunc, max_shift_pxl=self.max_shift_pxl, if_failed=self.if_failed)
                else: # XY alignment failed
                    raise
            ty,tx,r,my,mx = val
            ret[w,1:4] = ty,tx,r
            ret[w,5:7] = my,mx

            if self.img.nz > 1:
                self.echo('time: %i, wave: %i, tx:%.3f, ty:%.3f, tz:%.3f, r:%.3f, mx:%.3f, my:%.3f, mz:%.3f' % (t,w,tx,ty,ret[w,0],r,mx,my,ret[w,4]))
            else:
                self.echo('time: %i, wave: %i, tx:%.3f, ty:%.3f, r:%.3f, mx:%.3f, my:%.3f' % (t,w,tx,ty,r,mx,my))

            self.progress()

        self.alignParms[t] = ret


        # final 3D cross correlation
        if self.max_shift_pxl:
            searchRad = self.max_shift_pxl * 2
            if searchRad > min((self.img.nx, self.img.ny)):
                searchRad = min((self.img.nx, self.img.ny))
        else:
            searchRad = None

        self.setRegionCutOut()
        ref = self.get3DArrayAligned(w=self.refwave, t=t)
        ref = af.fixSaturation(ref, self.getSaturation(w=w, t=t))
        
        for w in range(self.img.nw):
            if (doWave and w == self.refwave) or (not doWave and w != self.refwave):
                continue

            for i in range(self.niter_3D):
                self.echo('3D phase correlation for time %i channel %i iter %i' % (t, w, i))
                img = self.get3DArrayAligned(w=w, t=t)
                img = af.fixSaturation(img, self.getSaturation(w=w, t=t))

                try:
                    zyx, c = xcorr.Xcorr(ref, img, phaseContrast=self.phaseContrast, searchRad=searchRad)
                except ValueError:
                    raise ValueError('Not enough correlation was found, please check your reference image.')
                del c, img
                if len(zyx) == 2:
                    zyx = N.array([0] + list(zyx))
                self.alignParms[t,w,:3] += zyx
                print('the result of the last correlation', zyx)

                if abs(zyx[0]) < self.maxErrZ and N.all(N.abs(zyx[1:]) < self.maxErrYX):
                    break

                self.progress()
            for j in range((self.niter_3D-1) - i):
                self.progress()
        del ref
        self.echo('Finding affine parameters done!')

    ##-- non linear ----
    def findNonLinear2D(self, t=0, npxls=af.MIN_PXLS_YX, phaseContrast=True):
        """
        calculate local cross correlation of projection images

        set self.mapyx and self.regions
        """
        #if self.refyz is None or self.refyx is None:
        self.setRefImg(removeEdge=False)

        # preparing the initial mapyx
        # mapyx is not inherited to avoid too much distortion

        # from v0.81 mapyx is inherited from instumental
        if self.microscopemap is not None:
            self.mapyx = self.microscopemap#.readMapAll()
        else:
            self.mapyx = N.zeros((self.img.nt, self.img.nw, 2, self.img.ny, self.img.nx), N.float32)

        if N.all((N.array(self.mapyx.shape[-2:]) - self.img.shape[-2:]) >= 0):
            slcs = imgGeo.centerSlice(self.mapyx.shape[-2:], win=self.img.shape[-2:], center=None)
            self.mapyx = self.mapyx[slcs] # Ellipsis already added
        else:
            self.mapyx = imgFilters.paddingValue(self.mapyx, shape=self.img.shape[-2:], value=0)

        self.last_win_sizes = N.zeros((self.nt, self.nw), N.uint16)
        # calculation
        for w in range(self.img.nw):
            if w == self.refwave:
                self.mapyx[t,w] = 0
                continue

            self.echo('Projection local alignment -- W: %i' % w)
            if self.img.nz > 1:
                img = self.img.get3DArr(w=w, t=t)
                #img = af.fixSaturation(img, self.getSaturation(w=w, t=t))

                zs = N.round_(self.refzs-self.alignParms[t,w,0]).astype(N.int)
                if zs.max() >= self.img.nz:
                    zsbool = (zs < self.img.nz)
                    zsinds = N.nonzero(zsbool)[0]
                    zs = zs[zsinds]

                imgyx = af.prep2D(img, zs=zs, removeEdge=False)
                del img
            else:
                imgyx = N.squeeze(self.img.get3DArr(w=w, t=t))
                #imgyx = af.fixSaturation(imgyx, self.getSaturation(w=w, t=t))

            affine = self.alignParms[t,w]

            imgyx = imgyx.astype(N.float32)
            self.refyx = self.refyx.astype(N.float32)

            yxs, regions, arr2, win = af.iterWindowNonLinear(imgyx, self.refyx, npxls, affine=affine, initGuess=self.mapyx[t,w], phaseContrast=self.phaseContrast, maxErr=self.maxErrYX, echofunc=self.echofunc)

            self.mapyx[t,w] = yxs
            if self.regions is None or self.regions.shape[-2:] != regions.shape:
                self.regions = N.zeros((self.img.nt, self.img.nw)+regions.shape, N.uint16)
            self.regions[t,w] = regions

            self.last_win_sizes[t,w] = win
            
            self.progress()

            if 0: # 3D cross correlation after the local alignment does not seem to help improving final correction accuracy.
                if self.max_shift_pxl:
                    searchRad = self.max_shift_pxl * 2
                    if searchRad > min((self.img.nx, self.img.ny)):
                        searchRad = min((self.img.nx, self.img.ny))
                else:
                    searchRad = None
                ref = self.get3DArrayRemapped(w=self.refwave, t=t)
                ref = af.fixSaturation(ref, self.getSaturation(w=self.refwave, t=t))
                img = self.get3DArrayRemapped(w=w, t=t)
                img = af.fixSaturation(img, self.getSaturation(w=w, t=t))
                zyx, c = xcorr.Xcorr(ref, img, phaseContrast=self.phaseContrast, searchRad=searchRad)
                if len(zyx) == 2:
                    zyx = N.array([0] + list(zyx))
                self.alignParms[t,w,:3] += zyx
                print('the result of the last correlation', zyx)

        self.echo('Projection local alignment done')

    def findNonLinear3D(self, t=0, npxls=32, phaseContrast=True):
        """
        calculate local cross correlation of 3D images section-wise

        set self.mapyx and self.regions
        """
        if self.mapyx is not None and self.mapyx.ndim == 5:
            fixGuess = True
            projmap = self.mapyx[t]
        else:
            fixGuess = False
            
        self.mapyx = N.zeros((self.img.nt, self.img.nw, self.img.nz, 2, self.img.ny, self.img.nx), N.float32)

        ref3D = self.img.get3DArr(w=self.refwave, t=t)
        refvar = ref3D.var()
        del ref3D

        for w in range(self.img.nw):
            if w == self.refwave:
                continue

            tzs = N.round_(N.arange(self.img.nz, dtype=N.float32)-self.alignParms[t,w,0]).astype(N.int)
            arr3D = self.get3DArr(w=w, t=0)
            var = (refvar + arr3D.var()) / 2.
            threshold = var * 0.1

            arr3D = af.trans3D_affineVertical(arr3D, self.alignParms[t,w])

            for z in range(self.img.nz):
                if tzs[z] > 0 and tzs[z] < self.img.nz:
                    ref = self.img.getArr(t=t,w=self.refwave,z=z)
                    arr = arr3D[z]

                    if fixGuess:
                        initGuess = projmap[w]
                    else:
                        if z:
                            initGuess = self.mapyx[t,w,z-1]
                        else:
                            initGuess = None
                    print('Section-wise local alignment -- W: %i, Z: %i' % (w, z))
                    yxs, regions,arr2 = af.iterWindowNonLinear(arr, ref, initGuess=initGuess, affine=self.alignParms[t,w], threshold=threshold, phaseContrast=self.phaseContrast, maxErr=self.maxErrYX, echofunc=self.echofunc)
                    self.mapyx[t,w,z] = yxs
                    if self.regions is None or self.regions.shape[-2:] != regions.shape or self.regions.ndim == 4:
                        self.regions = N.zeros((self.img.nt, self.img.nw, self.img.nz)+regions.shape, N.uint16)
                    self.regions[t,w,z] = regions

        return arr2

    def findNonLinear3D2(self, t=0, npxl=32, phaseContrast=True):
        """
        calculate local cross correlation of 3D images section-wise

        set self.mapyx and self.regions
        """
        if self.mapyx is not None and self.mapyx.ndim == 5:
            fixGuess = True
            projmap = self.mapyx[t]
        else:
            fixGuess = False
            
        self.mapyx = N.zeros((self.img.nt, self.img.nw, self.img.nz, 2, self.img.ny, self.img.nx), N.float32)

        ref3D = self.img.get3DArr(w=self.refwave, t=t)
        refvar = ref3D.var()
        del ref3D
        
        for w in range(self.img.nw):
            if w == self.refwave:
                continue

            tzs = N.round_(N.arange(self.img.nz, dtype=N.float32)-self.alignParms[t,w,0]).astype(N.int)
            arr3D = self.get3DArr(w=w, t=0)
            var = (refvar + arr3D.var()) / 2.
            threshold = var * 0.1
            
            affine = self.alignParms[t,w]
            
            arr3D = af.trans3D_affineVertical(arr3D, self.alignParms[t,w])


            if fixGuess:
                initGuess = projmap[w]
                arr_ref_guess = [(arr3D[z], self.img.getArr(w=self.refwave, t=t, z=z), initGuess) for z in range(8) if tzs[z] > 0 and tzs[z] < self.img.nz]
            else:
                initGuess = N.zeros(self.mapyx.shape[-4:])
                initGuess[1:] = self.mapyx[t,w,:-1]

                arr_ref_guess = [(arr3D[z], self.img.getArr(w=self.refwave, t=t, z=z), initGuess[z]) for z in range(list(range(8))) if tzs[z] > 0 and tzs[z] < self.img.nz]
            del arr3D
            
            # prepare for multiprocessing
            if NCPU == 1:
                yxs_regions = [af.findNonLinearSection(arg, npxl, affine, threshold, phaseContrast, self.maxErrYX) for arg in arr_ref_guess]
            else:
                yxs_regions = ppro.pmap(af.findNonLinearSection, arr_ref_guess, NCPU, npxl, affine, threshold, phaseContrast, self.maxErrYX)
            for z, yr in enumerate(yxs_regions):
                yxs, regions = yr
                self.mapyx[t,w,z] = yxs
                if self.regions is None or self.regions.shape[-2:] != regions.shape or self.regions.ndim == 4:
                    self.regions = N.zeros((self.img.nt, self.img.nw, self.img.nz)+regions.shape, N.uint16)
                self.regions[t,w,z] = regions

                if z > 5:
                    break

    def _findNonLinearSection(self, arr_ref_guess, affine, threshold):
        arr, ref, guess = arr_ref_guess
        return af.iterNonLinear(arr, ref, affine=affine, initGuess=guess, threshold=threshold, phaseContrast=self.phaseContrast, maxErr=self.maxErrYX)
        
        
    ### find alignment parameters of timelapse images ####
    def findBestTimeFrame(self, w=0):
        """
        set self.reftime
        """
        
        pwrs = N.array([self.img.get3DArr(w=w, t=t).mean() for t in range(self.img.nt)])

        reftime = N.argmax(pwrs)

        self.reftime = reftime

    def findAlignParamTime(self, doWave=False, doMag=False):
        """
        do findBestChannel() before calling this function

        initguess: nw*[tz,ty,tx,r,mz,my,mx]

        return nw*[tz,ty,tx,r,mz,my,mx]
        """
        niter = self.niter
        self.niter = 3
        for t in range(self.img.nt):
            if t == self.reftime:
                continue

            if t == 0:
                init_t = 0
            else:
                init_t = t - 1
                                    
            self.findAlignParamWave(t=t, doWave=doWave, init_t=init_t)
            if not doMag:
                self.alignParms[t,self.refwave,4:] = 1
                
            if not doWave and self.img.nw > 1:
                for w in range(self.img.nw):
                    self.alignParms[t,w] = self.alignParms[t,self.refwave]

        self.niter = 3

    ### save and load align parameters

    def saveParm(self, fn=None):
        """
        save a chromagnon file
        (as a csv or ome.tif file format)

        return output file name
        """
        if not fn:
            fn = chromformat.makeChromagnonFileName(self.img.filename + self.parm_suffix, self.mapyx is not None or self.microscopemap is not None)
            if self.outdir:
                fn = os.path.join(self.outdir, os.path.basename(fn))
        self.cwriter = chromformat.ChromagnonWriter(fn, self.img, self)
        self.cwriter.writeAlignParamAll()
        self.cwriter.close()

        return fn

    def loadParm(self, fn):
        """
        load a chromagnon file
        """
        print('loading', fn)
        self.creader = chromformat.ChromagnonReader(fn, self.img, self)
        self.creader.close()

        if not self.creader.text:
            self.fixAlignParmWithCurrRefWave()

        
    ### applying alignment parameters ####

    def getShift(self, w=0, t=0, refwave=None, reftime=0):
        """
        return shift at the specified wavelength and time frame
        """
        if refwave is None:
            refwave = self.refwave

        ret = self.alignParms[t,w].copy()
        ref = self.alignParms[reftime,refwave]

        ret[:4] -= ref[:4]
        if len(ref) >= 5:
            ret[4:] /= ref[4:len(ret)]
        if self.img.nz ==1:
            ret[0] = 0
            ret[-3] = 1
        return ret
        
    def setRegionCutOut(self, cutout=True):
        """
        return slc, shiftZYX
        """
        ZYX = N.array((self.img.nz, self.img.ny, self.img.nx))
        
        if cutout:
            shiftZYX = N.zeros((self.img.nt, self.img.nw, 6), N.float32)
            shiftZYX[:,:,1::2] = ZYX

            for t in range(self.img.nt):
                for w in range(self.img.nw):
                    if w != self.refwave:
                        shift = self.getShift(w=w, t=t)
                        shiftZYX[t,w] = cutoutAlign.getShift(shift, ZYX)

            mm = shiftZYX[:,:,::2].max(0).max(0)
            MM = shiftZYX[:,:,1::2].min(0).min(0)

            shiftZYX = N.array((mm[0], MM[0], mm[1], MM[1], mm[2], MM[2]))

            # rearrange as a slice
            shiftZYX = shiftZYX.astype(N.int)
            slc = [Ellipsis, 
                   slice(shiftZYX[0], shiftZYX[1]),
                   slice(shiftZYX[2], shiftZYX[3]),
                   slice(shiftZYX[4], shiftZYX[5])]
            if self.img.nz == 1:
                slc[1] = slice(0, 1)
        else:
            slc = [Ellipsis,
                       slice(0, ZYX[0]),
                       slice(0, ZYX[1]),
                       slice(0, ZYX[2])]

        self.cropSlice = tuple(slc) # future warning 20190604

    def get3DArrayAligned(self, w=0, t=0):
        """
        use self.setRegionCutOut() prior to calling this function if the img is to be cutout
        
        dyx: shift from the center of rotation & magnification

        return interpolated array
        """
        arr = self.img.get3DArr(w=w, t=t)

        arr = af.applyShift(arr, self.alignParms[t,w])

        arr = arr[self.cropSlice]
        
        return arr

    def get3DArrayRemapped(self, w=0, t=0):
        """
        use self.setRegionCutOut() prior to calling this function if the img is to be cutout
        
        dyx: shift from the center of rotation & magnification

        return interpolated array
        """
        if (self.mapyx is None and self.microscopemap is None):
            raise RuntimeError('This method must be called after calling "findNonLinear2D"')
        
        arr = self.img.get3DArr(w=w, t=t)

        if self.mapyx is not None:
            arr = af.remapWithAffine(arr, self.mapyx[t,w], self.alignParms[t,w])
        else:
            arr = af.remapWithAffine(arr, self.microscopemap[t,w], self.alignParms[t,w])
        arr = arr[self.cropSlice]
        
        return arr

    def get2DArray(self, w=0, t=0, yz=False, alignParms=None):#, doXcorr=True):
        """
        alginParms: overwrite self.alignParms, this should not have t dimension

        """
        if self.refyz is None or self.refyx is None:
            self.setRefImg()

        if w == self.refwave:
            if yz:
                return self._zoomimg(self.refyz)
            
            else:
                return self.refyx
        
        if alignParms is None:
            alignParms = self.alignParms[t]
            
        if self.img.nz > 1:
            img = self.img.get3DArr(w=w, t=t)
            img = af.fixSaturation(img, self.getSaturation(w=w, t=t))

            if yz:
                if not alignParms[w,2]:
                    self.echo('making an initial guess for channel %i' % w)
                    ref = self.img.get3DArr(w=self.refwave, t=t)
                    prefyx = N.max(ref, 0)
                    pimgyx = N.max(img, 0)
                    if self.max_shift_pxl:
                        searchRad = self.max_shift_pxl * 2
                        if searchRad > min((self.img.nx, self.img.ny)):
                            searchRad = min((self.img.nx, self.img.ny))
                    else:
                        searchRad = None
                    yx, c = xcorr.Xcorr(prefyx, pimgyx, phaseContrast=self.phaseContrast, searchRad=searchRad)
                    #ret[w,1:3] = yx
                    del ref, c
                    print(yx)
                    zs = N.round_(self.refxs-yx[-1]).astype(N.int)#ret[w,2]).astype(N.int)
                else:
                    zs = N.round_(self.refxs-alignParms[w,2]).astype(N.int)
                nz = self.img.nx
                removeEdge=True
                img = img.T
            else:
                zs = N.round_(self.refzs-alignParms[w,0]).astype(N.int)
                nz = self.img.nz
                removeEdge=False
                
            if zs.max() >= nz:
                zsbool = (zs < nz)
                zsinds = N.nonzero(zsbool)[0]
                zs = zs[zsinds]

            imgyx = af.prep2D(img, zs=zs, removeEdge=removeEdge)
            del img

            imgyx = self._zoomimg(imgyx)
            
        else:
            imgyx = N.squeeze(self.img.get3DArr(w=w, t=t))
        return imgyx

    def _zoomimg(self, imgyz):
        zzoom = self.refyz.shape[0] / self.refyz.shape[1]
        self.echo('Z axis zoom factor=%.2f' % zzoom)
        return nd.zoom(imgyz, (1, zzoom))

    ### saving image into a file ###


    def setMultipageTiff(self, multi=True):
        """
        set self.multipagetif
        use before saving tiff files
        """
        self.multipagetif = multi

    def prepSaveFile(self, fn):
        """
        return file hander class (either ImageWriter or MrcWriter)

        use self.setRegionCutOut() prior to calling this function if the img is to be cutout
        """
        # prepare writer
        try:
            des = imgio.Writer(fn, self.img)
        except OSError:
            # even though old readers/writers are closed, very often they are still alive.
            # In fact, some other program may be opening the file.
            # this is a temporary workaround for windows where open files cannot be overwritten
            fn = fntools.nextFN(fn)
            des = imgio.Writer(fn, self.img)

        nx = self.cropSlice[-1].stop - self.cropSlice[-1].start
        ny = self.cropSlice[-2].stop - self.cropSlice[-2].start
        nz = self.cropSlice[-3].stop - self.cropSlice[-3].start

        des.setDim(nx, ny, nz)
        if type(des) == imgio.mrcIO.MrcWriter:
            des.hdr.mst[:] = [s.start for s in self.cropSlice[::-1][:-1]]
            des.doOnSetDim()
        return des
        

    def min_is_zero(self):
        """
        return True if minimum of all sections is 0
        """
        if self.dtype == N.float32:
            for t in range(self.img.nt):
                for w in range(self.img.nw):
                    arr = self.img.get3DArr(w=w, t=t)
                    if arr.min() != 0:
                        return
            return True

    def saveAlignedImage(self, fn=None):
        """
        save aligned image into a file

        return output file name
        """
        if not fn:
            base, ext = os.path.splitext(self.img.filename)
            print(ext.replace(os.path.extsep, ''))
            if ext.replace(os.path.extsep, '') in imgio.READABLE_FORMATS:
                fn = base + self.img_suffix + self.img_ext
            else:
                fn = self.img.filename + self.img_suffix + self.img_ext
            if self.outdir:
                fn = os.path.join(self.outdir, os.path.basename(fn))

        if fn == self.img.filename:
            raise ValueError('Please use a suffix to avoid overwriting the original file.')
        
        min0 = self.min_is_zero()
                
        des = self.prepSaveFile(fn)

        for t in range(self.img.nt):
            for w in range(self.img.nw):
                
                if w == self.refwave and self.nt == 1:
                    self.echo('Copying reference image, t: %i, w: %i' % (t, w))
                    arr = self.img.get3DArr(w=w, t=t)
                    arr = arr[self.cropSlice]
                elif (self.mapyx is None and self.microscopemap is None):
                    self.echo('Applying affine transformation to the target image, t: %i, w: %i' % (t, w))
                    arr = self.get3DArrayAligned(w=w, t=t)
                else:
                    self.echo('Remapping local alignment, t: %i, w: %i' % (t, w))
                    arr = self.get3DArrayRemapped(w=w, t=t)

                if min0:
                    arr = N.where(arr > 0, arr, 0)
                    
                des.write3DArr(arr, w=w, t=t)
                self.progress()
        des.close()

        return fn


    def saveNonlinearImage(self, out=None, gridStep=10):
        """
        save the result of non-linear transformation into the filename "out"
        gridStep: spacing of grid (number of pixels)

        return out
        """
        if self.mapyx is None:
            return
        
        if not out:
            out = os.path.extsep.join((self.img.filename, 'local', 'tif'))
            if self.outdir:
                out = os.path.join(self.outdir, os.path.basename(out))

        try:
            return af.makeNonliearImg(self, out, gridStep)#chromformat.makeNonliearImg(self, out, gridStep)
        except OSError:
            out = fntools.nextFN(out)
            print(out)
            return af.makeNonliearImg(self, out, gridStep)#chromformat.makeNonliearImg(self, out, gridStep)
    
        
def hasSameWave(img):
    waves = [wave for wave in img.wave if wave]
    if len(waves) > len(set(waves)):
        return True
    
def dummyEcho(msg, skip_notify=None):
    print(msg)
