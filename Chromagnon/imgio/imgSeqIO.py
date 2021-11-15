
import os, re
import six
import numpy as N
try:
    from . import generalIO, imgIO
except ImportError:
    import generalIO, imgIO

WRITABLE_FORMATS = imgIO.WRITABLE_FORMATS
READABLE_FORMATS = imgIO.READABLE_FORMATS


class ImgSeqReader(generalIO.GeneralReader):
    def __init__(self, fns, mode='r'):
        """
        The fns must be a sequence of simgle image files.
        RGB images are not accepted.
        """
        if isinstance(fns, six.string_types) and os.path.isdir(fns):
            fns = [os.path.join(fns, fn) for fn in os.listdir(fns)]
        elif type(fns) not in [list, set, tuple]:
            raise ValueError('fns must be a directry, or list, set or tuple of filenames')

        self.fns = fns
        generalIO.GeneralReader.__init__(self, fns[0])

    def closed(self):
        return hasattr(self, 'fp')
        
    def openFile(self):
        #self.fns = self.filename
        self.fns.sort()
        self.file = os.path.commonprefix([os.path.basename(fn) for fn in self.fns])
        self.filename = os.path.dirname(self.fns[0])#commonprefix(self.fns)

        self.i = 0

        if 'r' in self.mode:
            self.readHeader()

    def readHeader(self):
        self.fp = imgIO.getHandle(self.fn)
        dtype,nc, ny,nx, isSwapped = imgIO._getImgMode(self.fp)

        nztw, imgSeq = self.determineDimFromName()
        nw = nztw[2] or 1
        self.nc = nc
        wrange = range(nw)
        waves = generalIO.makeWaves(nw)

        self.isSwapped = isSwapped
        self.setPixelSize(pz=0.1, py=0.1, px=0.1) 
        self.setDim(nx, ny, nztw[0] or 1, nztw[1] or 1, nw, dtype, waves, imgSeq)#, isSwapped=isSwapped)

    def determineDimFromName(self):
        fns = [os.path.basename(fn) for fn in self.fns]
        nztw = []
        name = []
        for ds in ['[zZ]', '[tT]', '[wcWC]']:
            pat = re.compile('_%s[0-9]+' % ds)
            ndim = pat.findall(fns[0])
            if ndim:
                nn = len(set([pat.findall(fn)[-1][2:] for fn in fns]))
                nztw.append(nn)
                dn = ndim[-1][1:2].lower()
                if dn == 'c':
                    dn = 'w'
                name.append(dn)
            else:
                nztw.append(None)

        # 0=ZTW, 1=WZT, 2=ZWT, 3=TZW
        # determine imgseq
        if len(name) == 1:
            imgseq = 0
        elif len(name) == 2:
            patstr = '_%s[0-9]+_%s[0-9]+'
            table = {0: [('[wcWC]','[tT]'), ('[wcWC]', '[zZ]'), ('[tT]', '[zZ]')],
                     1: [('[tT]', '[wcWC]'), ('[zZ]', '[wcWC]')],
                     3: [('[zZ]', '[tT]')]}
            for _imgseq, stlist in table.items():
                for st in stlist:
                    pat = re.compile(patstr % tuple(st))
                    if pat.search(self.fns[0]):
                        imgseq = _imgseq
                        break
        elif len(name) == 3:
            patstr = '_%s[0-9]+_%s[0-9]+_%s[0-9]+'
            pats = [seq for seq in [('[zZ]', '[tT]', '[wcWC]'), ('[wcWC]', '[zZ]', '[tT]'), ('[zZ]', '[wcWC]', '[tT]')]]
            for imgseq, st in enumerate(pats):
                pat = re.compile(patstr % tuple(st))
                if pat.search(self.fns[0]):
                    break

        elif len(name) == 0: # micromanager format
            bases = [os.path.splitext(fn)[0] for fn in fns]
            twzs = [fn.split('_')[1:] for fn in bases]
            if len(twzs[0]) != 3:
               raise ValueError('The labeling format of the series not understood') 
            nt = max([int(twz[0]) for twz in twzs]) + 1
            nw = len(set([twz[1] for twz in twzs]))
            nz = max([int(twz[2]) for twz in twzs]) + 1
            nztw = [nz, nt, nw]

            imgseq = 2

        # reorder the fn list
        name2 = []
        if imgseq == 0:
            dname = 'wtz'
        elif imgseq == 1:
            dname = 'tzw'
        elif imgseq == 2:
            dname = 'twz'
        elif dname == 3:
            dname = 'tzw'
        name = [s for s in dname if s in name]

        num = []
        for fn in self.fns:
            ndims = []
            for n in name:
                pat = re.compile('_%s[0-9]+' % n)
                nd = int(pat.findall(fn)[-1][2:])
                ndims.append(nd)
            num.append((ndims, fn))
        num.sort()
        self.fns = [fn for ndims, fn in num]
        

        return nztw, imgseq


    # getting array

    def readSec(self, i=0):
        a = imgIO.load(self.fns[i])
        self.i = i
        return a
    old='''
    def readSec_old(self, i=0):
        if backend == 'PIL':
            if self.fp.filename != self.fns[i]:
                self.fp = Image.open(self.fns[i])

            self.fp.seek(0)

            a = N.fromstring(self.fp.tobytes(), self.dtype)
            a.shape = (self.ny, self.nx)

            if self.isSwapped:
                a.byteswap(True)
        elif backend == 'wx':
            if self.i != i:
                self.fp = wx.Image(self.fns[i])
            buf = self.fp.GetBuffer()
            a = N.frombuffer(buf, dtype=self.dtype, count=-1, offset=0)
            a.shape = (self.ny, self.nx,self.nc)
            a = a[...,0][::-1]

        self.i = i
        return a'''

#------ Below, not yet done -----#

class ImgSeqWriter(generalIO.GeneralWriter):
    def __init__(self, basefn, mode='w'):
        """
        multipage: need to use setHdr() or setDim()
        rgbOrder: rgb, rgba etc... 
        """
        generalIO.GeneralWriter.__init__(self, basefn, mode)
        
        base, self.format = os.path.splitext(basefn)

        if self.format.replace(os.path.extsep, '').lower() not in READABLE_FORMATS:#Image.EXTENSION:
            raise ValueError('Please supply file extension')

        self.rgbOrder = 'rgb'
        self._rescaleTo8bit = False
        self.saveOptions = {}

    def openFile(self):
        self.fp = None
        
    # funcs for output
    def rescaleTo8bit(self, arr=None):
        """
        arr: your whole array
        if multipage: you have to execute this function before writing arr
        if arr is None, then rescale section-wise
        """
        if hasattr(self, 'nw') and self.nw != len(self.rgbOrder):
            if arr is not None and self.nw in arr.shape:
                shape = list(arr.shape)
                self.setColorAxis(shape.index(self.nw))
            else:
                print('WARNING: number of wavelength %i does not match with rgbOrder %s, use setColorAxis() to set color axis' % (self.nw, self.rgbOrder))

        if arr is None:
            self._rescaleTo8bit = True
        else:
            ma, mi = float(arr.max()), float(arr.min())
            self._rescaleTo8bit = (mi, ma-mi)

        # refresh suffix
        if hasattr(self, 'dtype') and not hasattr(self, 'outsuf'):
            self._setSuffix()

        self.dtype = N.uint8

    def setSaveOptions(self, **options):
        """
        jpg: quality, optimized, progressive etc...
        """
        self.saveOptions.update(options)

        
    # functions for series
    def setDim(self, nx, ny, nz, nt, nw, dtype, wave=[], imgSequence=0):
        self.wave = wave
        self.nw = nw
        self.nt = nt
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.imgSequence = imgSequence
        self.dtype = dtype

        #if self.multipage:
        #    self._setSecSize()
        #else:
        self._setSuffix()

    def setDimFromMrcHdr(self, hdr):
        from Priithon.all import Mrc
        self.wave = hdr.wave
        self.nw = hdr.NumWaves
        self.nt = hdr.NumTimes
        self.nx = hdr.Num[0]
        self.ny = hdr.Num[1]
        self.nz = hdr.Num[2] // (self.nt * self.nw)
        self.imgSequence = hdr.ImgSequence
        self.dtype = Mrc.MrcMode2dtype(hdr.PixelType)

        #if self.multipage:
        #    self._setSecSize()
        #else:
        self._setSuffix()

    # funcs for single imgs
    def _setSuffix(self):
        suffix = ''
        imgseq = generalIO.IMGSEQ[self.imgSequence].lower()
        if (self._rescaleTo8bit or self.dtype == N.uint8) and self.rgbOrder:
            imgseq = imgseq.replace('w', '')
            
        for d in generalIO.IMGSEQ[self.imgSequence].lower():
            ns = self.__getattribute__('n%s' % d) - 1
            if ns:
                digit = int(N.log10(ns*10))
                prefix = '_%s' % d
                suffix +=  prefix + '%0' + str(digit) + 'd'
        self.outsuf = fntools.appendToBasename(self.fn, suffix)
        self.wtz_name = [wtz[0] for wtz in suffix.split('_')[1:]]

    def _getOutFn(self, t=0, w=0, z=0):
        dic = {'w': w, 't': t, 'z': z}
        return self.outsuf % tuple([dic[name] for name in self.wtz_name])

    # writing
    def writeSec(self, arr, i=0, singleOutFn=None):
        if not singleOutFn:
            singleOutFn = self.outfn
        
        # astype changes byteorder as well
        arr = arr.astype(self.dtype)
        if has(self._rescaleTo8bit, '__iter__'):
            arr = (arr-self._rescaleTo8bit[0])*255./self._rescaleTo8bit[1]
            rescaleTo8bit = False
        else:
            rescaleTo8bit = self._rescaleTo8bit
        
        return imgIO.save(arr, singleOutFn, rescaleTo8bit, self.rgbOrder.lower())

    def writeArrSingle(self, arr):
        self.writeSec(arr)

    def writeArr(self, arr, t=0, w=0, z=0):
        arr = self.flipY(arr)
        # fill rgb
        if self.rgbOrder and self._rescaleTo8bit:
            nemptycol = len(self.rgbOrder) - self.nw
            if nemptycol <= 4 and nemptycol > 0:
                fill = N.zeros((nemptycol, self.ny, self.nx), arr.dtype.type)
                arr = N.concatenate((arr.reshape((1,self.ny,self.nx)), fill))
            else:
                self.rgbOrder = None

        # write out
        outfn = self._getOutFn(t=t, w=w, z=z)
        self.writeSec(arr, singleOutFn=outfn)


    def write3DArr(self, arr, t=0, w=0):
        # RGB color axis correction -> 1
        if arr.ndim == 4 and self.rgbOrder and (self._rescaleTo8bit or self.dtype == N.uint8):
            shapezw = list(arr.shape[:-2])
            if self.nw not in shapezw:
                raise ValueError('number of wavelength %i was not found in the given array shape %s' % (self.nw, self.shape))
            # color axis
            waxis = shapezw.index(self.nw)
            if waxis == 0:
                arr = arr.transpose((1,0,2,3))


        for z, a in enumerate(arr):
            self.writeArr(a, t=t, w=w, z=z)

