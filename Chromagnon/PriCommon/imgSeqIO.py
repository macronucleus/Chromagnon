
import os, sys
import numpy as N
from PIL import Image
import generalIO

###---------- sequence of images -----------###

class ImgSeqReader(generalIO.GeneralReader):
    def __init__(self, fns, mode='r'):
        """
        The fns must be a sequence of simgle image files.
        RGB images are not accepted.
        """
        if isinstance(fns, basestring) and os.path.isdir(fns):
            fns = os.listdir(fns)
        elif type(fns) not in [list, set, tuple]:
            raise ValueError, 'fns must be a directry, or list, set or tuple of filenames'

        self.fns = fns
        generalIO.GeneralReader.__init__(self, fns[0])

    def closed(self):
        return hasattr(self, 'fp')
        
    def openFile(self):
        #self.fns = self.filename
        self.fns.sort()
        self.file = os.path.commonprefix([os.path.basename(fn) for fn in self.fns])
        self.filename = os.path.commonprefix(self.fns)

        self.i = 0

        if 'r' in self.mode:
            self.readHeader()

    def readHeader(self):
        self.fp = Image.open(self.fns[0])
        t,nc, ny,nx, isSwapped = _getImgMode(self.fp)

        nztw, imgSeq = self.determineDimFromName()
        wrange = xrange(nztw[2] or 1)
        waves = [RGB for i, RGB in enumerate([515, 625, 450, 700, 350]) if i in wrange]

        self.isSwapped = isSwapped
        self.setDim(nx, ny, nztw[0] or 1, nztw[1] or 1, nztw[2] or 1, t, waves, imgSeq)#, isSwapped=isSwapped)

    def determineDimFromName(self):
        fns = [os.path.basename(fn) for fn in self.fns]
        nztw = []
        name = []
        for ds in ['z', 't', 'w']:
            val = self.__getattribute__(ds)
            if val:
                pat = re.compile('_%s[0-9]+' % ds)
                nn = len(set([pat.findall(fn)[-1][2:] for fn in fns]))
                nztw.append(nn)
                name.append(ds)
            else:
                nztw.append(None)

        # 0=ZTW, 1=WZT, 2=ZWT, 3=TZW
        # determine imgseq
        if len(name) == 1:
            imgseq = 0
        elif len(name) == 2:
            patstr = '_%s[0-9]+_%s[0-9]+'
            table = {0: ['wt', 'wz', 'tz'],#['zt', 'zw', 'tw'],
                     1: ['tw', 'zw'],
                     3: ['zt']}#['wz', 'wt']}
            for imgseq, stlist in table.iteritems():
                for st in stlist:
                    pat = re.compile(patstr % tuple(st))
                    if pat.search(self.fns[0]):
                        break
        elif len(name) == 3:
            patstr = '_%s[0-9]+_%s[0-9]+_%s[0-9]+'
            pats = [seq.lower() for seq in IMGSEQ]#['ztw', 'wzt', 'zwt']
            for imgseq, st in enumerate(pats):
                pat = re.compile(patstr % tuple(st))
                if pat.search(self.fns[0]):
                    break

        return nztw, imgseq


    # getting array

    def readSec(self, i=0):
        if hasattr(self, 'fp') and self.fp.filename != self.fns[i]:
            self.im = Image.open(self.fns[i])
        
        self.im.seek(0)

        a = N.fromstring(self.im.tobytes(), self.dtype)
        a.shape = (self.ny, self.nx)

        if self.isSwapped:
            a.byteswap(True)
            
        return a

def _getImgMode(im):
    """
    This function is from Priithon.Useful.py
    """
    cols = 1
    BigEndian = False
    if im.mode   == "1":
        t = N.uint8
        cols = -1
    elif im.mode == "L" or \
         im.mode == "P": #(8-bit pixels, mapped to any other mode using a colour palette)
        t = N.uint8
    elif im.mode == "I;16":
        t = N.uint16
    elif im.mode == "I":
        t = N.uint32
    elif im.mode == "F":
        t = N.float32
    elif im.mode == "RGB":
        t = N.uint8
        cols = 3
    elif im.mode in ("RGBA", "CMYK", "RGBX"):
        t = N.uint8
        cols = 4
    elif im.mode == "I;16B":  ## big endian
        t = N.uint16
        BigEndian = True
    else:
        raise ValueError, "can only convert single-layer images (mode: %s)" % (im.mode,)

    nx,ny = im.size

    isSwapped = (BigEndian and sys.byteorder=='little' or not BigEndian and sys.byteorder == 'big')
        
    return t,cols, ny,nx, isSwapped


#------ Below, not yet done -----#

class ImgSeqWriter(generalIO.GeneralWriter):
    def __init__(self, basefn, mode='w'):
        """
        multipage: need to use setHdr() or setDim()
        rgbOrder: rgb, rgba etc... (None means separete file for color)
        """
        generalIO.GeneralWriter.__init__(self, basefn, mode)
        
        base, format = os.path.splitext(outfn)
        
        self.format = format.replace(os.path.extsep, '').upper()
        if self.format.lower() not in IMGEXTS:
            raise ValueError, 'Please supply file extension'
        elif self.format.lower() not in ['tif', 'tiff'] and multipage:
            raise ValueError, "Multipage for your format is not supported "
        elif self.format.lower() in ['tif', 'tiff']:
            self.format = 'TIFF'
            
        self.multipage = multipage
        self.rgbOrder = rgbOrder
        self._rescaleTo8bit = False
        #self._colorAxis = 1
        self.saveOptions = {}

        if self.multipage:
            self.initiated = False


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
                print 'WARNING: number of wavelength %i does not match with rgbOrder %s, use setColorAxis() to set color axis' % (self.nw, self.rgbOrder)

        if arr is None:
            self._rescaleTo8bit = True
        else:
            ma, mi = float(arr.max()), float(arr.min())
            self._rescaleTo8bit = (mi, ma-mi)

        # refresh suffix
        if not self.multipage and hasattr(self, 'dtype') and not hasattr(self, 'outsuf'):
            self._setSuffix()
        if self.multipage and hasattr(self, 'dtype'):
            self._setSecSize()

        self.dtype = N.uint8

    #def setColorAxis(self, axis=1):
    #    self._colorAxis = axis

    def setSaveOptions(self, **options):
        """
        jpg: quality, optimized, progressive etc...
        """
        self.saveOptions.update(options)

        
    # functions for series
    def setDim(self, nx, ny, nz, nt, nw, dtype, wave=[], imgSequence=0):
        self.wave = wave
        if not len(self.wave) and not len(wave) and self.nw:
            self.waves = range(400, 700, 300//self.nw)[:self.nw]
            
        self.nw = nw
        self.nt = nt
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.imgSequence = imgSequence
        self.dtype = dtype

        if self.multipage:
            self._setSecSize()
        else:
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

        if self.multipage:
            self._setSecSize()
        else:
            self._setSuffix()

    # funcs for single imgs
    def _setSuffix(self):
        suffix = ''
        imgseq = IMGSEQ[self.imgSequence].lower()
        if (self._rescaleTo8bit or self.dtype == N.uint8) and self.rgbOrder:
            imgseq = imgseq.replace('w', '')
            
        for d in IMGSEQ[self.imgSequence].lower():
            ns = self.__getattribute__('n%s' % d) - 1
            if ns:
                digit = int(N.log10(ns*10))
                prefix = '_%s' % d
                suffix +=  prefix + '%0' + str(digit) + 'd'
        self.outsuf = appendToBasename(self.outfn, suffix)
        self.wtz_name = [wtz[0] for wtz in suffix.split('_')[1:]]

    def _getOutFn(self, t=0, w=0, z=0):
        dic = {'w': w, 't': t, 'z': z}
        return self.outsuf % tuple([dic[name] for name in self.wtz_name])
        
    # funcs for multipage
    def _setSecSize(self):
        """
        this function is supporsed to be executed after setHdr() or setDim()
        """
        npxls = self.ny * self.nx
        self._secByteSize = int(N.nbytes[self.dtype] * npxls)

        if self.dtype == N.uint8 and self.rgbOrder and self.nw > 1:
            self._secByteSize *= len(self.rgbOrder)

    def seekSec(self, i=0, go2IFDpos=False):
        if self.multipage and not self.initiated:
            self._runTest() # to get number of tags in IFD
            self.initiated = True
        
        IFD = ntagbyte + IFD_byte * self.nIFD + nIFDbyte

        extrabyte = int(bool(i)) * dataOffset + i * IFD

        if go2IFDpos:
            if i == 0:
                extrabyte += dataOffset
            extrabyte += ntagbyte + IFD_byte * self.nIFD

        self.fp.seek(extrabyte + i * self._secByteSize )

    def _runTest(self):
        """
        get number of IFD tags as self.nIFD
        """
        shape = (self.ny, self.nx)
        if self.nw > 1 and self._rescaleTo8bit and self.rgbOrder:
            shape = (self.nw,) + shape
        arr = N.zeros(shape, self.dtype)

        ifdOffset = dataOffset

        for i in range(2):
            self.fp.seek(0, 2) # whence=2 goes to the end of the file
            if i:
                ifdOffset = self.fp.tell()

            img = U.array2image(arr, rgbOrder=self.rgbOrder)

            img.save(self.fp, format=self.format, **self.saveOptions)

            if i: # correct "next" entry of previous ifd -- connect !
                self.fp.seek(last_pos)
                ifdLength = i16(self.fp.read(ntagbyte))
                self.fp.seek(ifdLength * IFD_byte, 1) # whence=1 relative move
                self.fp.write(o32( ifdOffset ))

            last_pos = ifdOffset

        self.nIFD = ifdLength # often 8


    # writing
    def writeSec(self, arr, i=0, singleOutFn=None):
        if self._rescaleTo8bit:
            if self._rescaleTo8bit is True:
                self.rescaleTo8bit(arr)
            arr = (arr-self._rescaleTo8bit[0])*255./self._rescaleTo8bit[1]

        # astype changes byteorder as well
        arr = arr.astype(self.dtype)
        
        if self.multipage and not self._rescaleTo8bit:
            if arr.dtype.type == N.uint8:
                mode = "L"
            elif arr.dtype.type == N.float32:
                mode = "F"
            elif arr.dtype.type in ( N.int16, N.uint16 ):
                mode = "I;16"
            else:
                raise ValueError, "unsupported array datatype"
            img = Image.frombytes(mode, (arr.shape[-1], arr.shape[-2]), arr.tostring())
        else:
            img = U.array2image(arr, rgbOrder=self.rgbOrder)
        
        if self.multipage:
            self.seekSec(i)
            if i:
                ifdOffset = self.fp.tell()

            img.save(self.fp, format=self.format, **self.saveOptions)

            if i: 
                self.seekSec(i-1, go2IFDpos=True)
                self.fp.write(o32( ifdOffset ))
        else:
            if not singleOutFn:
                singleOutFn = self.outfn
            img.save(singleOutFn, **self.saveOptions)

    def writeArrSingle(self, arr):
        self.writeSec(arr)

    def writeArr(self, arr, t=0, w=0, z=0):
        # fill rgb
        if self.rgbOrder and self._rescaleTo8bit:
            nemptycol = len(self.rgbOrder) - self.nw
            if nemptycol <= 4 and nemptycol > 0:
                fill = N.zeros((nemptycol, self.ny, self.nx), arr.dtype.type)
                arr = N.concatenate((arr.reshape((1,self.ny,self.nx)), fill))
            else:
                self.rgbOrder = None

        # write out
        if self.multipage:
            if not hasattr(self, 'fp'):
                self.fp = open(self.outfn, 'w+b')

            if (self._rescaleTo8bit or self.dtype == N.uint8) and self.rgbOrder:
                nw = 1
                w = 0
            else:
                nw = self.nw

            if self.imgSequence == 0:
                i = w*self.nt*self.nz + t*self.nz + z
            elif self.imgSequence == 1:
                i = t*self.nz*nw + z*nw + w
            elif self.imgSequence == 2:
                i = t*self.nz*nw + w*self.nz + z
            elif self.imgSequence == 3:
                i = w*self.nz*self.nt + z*self.nt + t

            self.writeSec(arr, i)

        else:
            outfn = self._getOutFn(t=t, w=w, z=z)
            self.writeSec(arr, singleOutFn=outfn)


    def write3DArr(self, arr, t=0, w=0):
        # RGB color axis correction -> 1
        if arr.ndim == 4 and self.rgbOrder and (self._rescaleTo8bit or self.dtype == N.uint8):
            shapezw = list(arr.shape[:-2])
            if self.nw not in shapezw:
                raise ValueError, 'number of wavelength %i was not found in the given array shape %s' % (self.nw, self.shape)
            # color axis
            waxis = shapezw.index(self.nw)
            if waxis == 0:
                arr = arr.transpose((1,0,2,3))


        for z, a in enumerate(arr):
            self.writeArr(a, t=t, w=w, z=z)


