from __future__ import with_statement
import os, csv
import numpy as N
from scipy import ndimage as nd
from PriCommon import bioformatsIO
from . import alignfuncs as af

IDTYPE = '101'
PARM_EXT='chromagnon'
DIMSTRS = ('tz', 'ty', 'tx', 'rz', 'mz', 'my', 'mx')

if PARM_EXT not in bioformatsIO.OMETIFF:
    bioformatsIO.OMETIFF = tuple(list(bioformatsIO.OMETIFF) + [PARM_EXT])


def is_binary(fn):
    # http://stackoverflow.com/questions/898669/how-can-i-detect-if-a-file-is-binary-non-text-in-python
    textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
    is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
    return is_binary_string(open(fn, 'rb').read(1024))

def is_chromagnon(fn, check_img_to_open=False):
    check = False
    if fn.endswith(PARM_EXT):
        check = True
    else:
        is_image = is_binary(fn)
        if not is_image:
            with open(fn) as rdr:
                if rdr.next().startswith('nt') and rdr.next().startswith('nw'):
                    check = True
            
        elif is_image and check_img_to_open:
            rdr = bioformatsIO.BioformatsReader(fn)
            if hasattr(rdr, 'ome'):
                #ome = bioformatsIO.OME_XML_Editor(rdr.omexml)
                if rdr.ome.get_structured_annotation('idtype') == IDTYPE:
                    check = True
            rdr.close()

    return check
            

class ChromagnonWriter(object):#bioformatsIO.BioformatsWriter):
    def __init__(self, outfn, rdr, holder):
        """
        save a chromagnon file
        (as a Mrc file format)
        
        rdr: imgReader object with dimension information
        holder: a object with refwave, alignParms, mapyx attributes

        write all parms into outfn

        This if broken for mapyx array writer..., use function below instead
        """
        if 0:#not outfn.endswith(PARM_EXT):
            outfn = os.path.extsep.join((outfn, PARM_EXT))
        
        self.rdr = rdr
        self.holder = holder
        self.fp = None
        self._closed = False


        self.num_entry = self.holder.alignParms.shape[-1]

        #self.setFromReader(self.rdr)

        #self.imgSequence = 2
        #self.dtype = N.float32
        
        # text formats
        if self.holder.mapyx is None:
            # replacing calling bioformatsIO.BioformatsWriter.__init__(self, outfn)
            self.filename = self.fn = outfn
            self.dr, self.file = os.path.split(outfn)
            self.pxlsiz = N.ones((3,), N.float32)
            self.doOnSetDim = lambda x=0: x
            
            self.fp = open(outfn, 'w')
            self.writer = csv.writer(self.fp)
            self.setFromReader(self.rdr)

        else:
            #bioformatsIO.BioformatsWriter.__init__(self, outfn)
            #self.ome = bioformatsIO.OME_XML_Editor(self.omexml)
            self.writer = bioformatsIO.BioformatsWriter(outfn)

            self.writer.setFromReader(self.rdr)
            
            if self.holder.mapyx.ndim == 5:
                #self.nz0 = 1
                self.writer.nz = 2#1
            else:
                #self.nz0 = self.nz
                self.writer.nz *= 2

        self.writer.imgSequence = 2
        self.writer.dtype = N.float32
                
        self.writeHdr()
        self.writeAlignParamAll()
        self.writeMapAll()

        self.close()

    def close(self):
        if not self._closed:
            if self.holder.mapyx is None:
                self.fp.close()
            else:
                import javabridge
                script = """
                writer.close();
                """
                if self.fp:
                    javabridge.run_script(script,
                                        dict(writer=self.writer.fp))

                #self.fp.close() # this does not work...
            self.writer.fp = None
            self._closed = True

    def writeHdr(self):
        if self.holder.mapyx is None:
            self.writer.writerow(('nt', self.nt))
            self.writer.writerow(('nw', self.nw))
            self.writer.writerow(('pxlsize_z_y_x',) + tuple(self.pxlsiz))
            self.writer.writerow(('refwave', self.holder.refwave))
            self.writer.writerow(('t', 'wavelength',) + DIMSTRS)
        else:
            px = self.writer.omexml.image().Pixels
            px.set_SizeZ(self.writer.nz)# * 2)
            # pixel size is already written
            #self.ome.setPixels('refwave', str(self.holder.refwave))
            #self.ome.setPixels('num_entry', str(self.num_entry))

            #self.ome.add_structured_annotation('refwave', str(self.holder.refwave))
            #self.ome.add_structured_annotation('num_entry', str(self.num_entry))

    def writeAlignParmSingle(self, t=0, w=0):
        parm = self.holder.alignParms[t,w]#.reshape((1,self.num_entry))
        #print 'chrom writing', w, parm.shape
        if self.holder.mapyx is None:

            self.writer.writerow([t, self.wave[w]]+list(parm))
        else:
            for i, key in enumerate(DIMSTRS):
                #self.ome.setChannel('t%03d_' %t + key, parm[i], idx=w)
                #self.ome.add_structured_annotation('t%03d_w%i_' %(t,w) + key, str(parm[i]))
                pass

    def writeAlignParamAll(self):
        for t in xrange(self.rdr.nt):
            for w in xrange(self.rdr.nw):
                self.writeAlignParmSingle(t=t,w=w)
    
    def writeMap3D(self, arr=None, t=0, w=0):
        """
        write a single 3D array
        """
        if self.holder.mapyx is not None:
            for z in xrange(self.nz0):
                self.writeMap2D(arr, t=t, w=w, z=z)

    def writeMap2D(self, arr=None, t=0, w=0, z=0):
        for d in xrange(2): # 2 is y, x
            zc = z * 2 + d
            if self.holder.mapyx.ndim == 6:
                arr = self.holder.mapyx[t,w,z,d]
            else:
                arr = self.holder.mapyx[t,w,d]
            self.writeArr(arr, t=t, w=w, z=zc)
            #print 'write t,w,z,d', t, w, z, d
            
    def writeMapAll(self):
        for t in xrange(self.rdr.nt):
            for w in xrange(self.rdr.nw):
                for z in xrange(self.writer.nz):
                    if self.holder.mapyx.ndim == 6:
                        d = z % 2
                        z0 = z // 2
                        arr = self.holder.mapyx[t,w,z0,d]
                    else:
                        arr = self.holder.mapyx[t,w,z]
                    self.writer.writeArr(arr, t=t, w=w, z=z)
                        #self.writeMap3D(t=t,w=w)


def ChromagnonWriter(fn, rdr, holder):
    """
    return a writer
    """
    if not fn.endswith(PARM_EXT):
        fn = os.path.extsep.join((fn, PARM_EXT))

    if holder.mapyx is None:
        fp = open(fn, 'w')
        wt = csv.writer(fp)

        wt.writerow(('nt', rdr.nt))
        wt.writerow(('nw', rdr.nw))
        wt.writerow(('pxlsize_z_y_x',) + tuple(rdr.pxlsiz))
        wt.writerow(('refwave', holder.refwave))
        wt.writerow(('t', 'wavelength',) + DIMSTRS)

        for t in xrange(rdr.nt):
            for w in xrange(rdr.nw):
                parm = holder.alignParms[t,w]
                wt.writerow([t, rdr.wave[w]]+list(parm))
        fp.close()

    else:
            
        num_entry = holder.alignParms.shape[-1]

        wt = bioformatsIO.BioformatsWriter(fn)
        wt.setFromReader(rdr)
        if holder.mapyx.ndim == 6:
            wt.nz *= 2
        else:
            wt.nz = 2

        #print len(wt.omexml.structured_annotations.keys())
        from PriCommon.mybioformats import omexml as ome
        wt.ome.add_structured_annotation('refwave', str(holder.refwave))
        wt.ome.add_structured_annotation('num_entry', str(num_entry))
        wt.ome.add_structured_annotation('idtype', IDTYPE)

        #print len(wt.omexml.structured_annotations.keys())

        for t in xrange(rdr.nt):
            for w in xrange(rdr.nw):
                for i, key in enumerate(DIMSTRS):
                    parm = holder.alignParms[t,w]
                    wt.ome.add_structured_annotation('t%03d_w%i_' %(t,w) + key, str(parm[i]))

        for t in xrange(rdr.nt):
            for w in xrange(rdr.nw):
                for z in xrange(wt.nz):
                    if holder.mapyx.ndim == 6:
                        d = z % 2
                        z0 = z // 2
                        arr = holder.mapyx[t,w,z0,d]
                    else:
                        arr = holder.mapyx[t,w,z]
                    wt.writeArr(arr, t=t, w=w, z=z)
        wt.close()
    return wt


def ChromagnonReader(fn, rdr=None, holder=None):
    rdr = rdr
    holder = holder

    dratio = N.ones((3,), N.float32)

    if not is_binary(fn):
        text = True
        
        fp = open(fn)
        reader = csv.reader(fp)

        # read parameters
        nt = int(reader.next()[1])
        nw = int(reader.next()[1])
        pxlsiz = N.array([eval(p) for p in reader.next()[1:]])
        imgSequence = 2
        refwave = eval(reader.next()[1])
        num_entry = len(reader.next()[2:])
        wave = []
        #self.pos0 = self.tell()

        alignParms = N.empty((nt, nw, num_entry), N.float32)
        for t in xrange(nt):
            for w in xrange(nw):
                row = reader.next()
                wave.append(_eval(row[1]))
                alignParms[t,w] = [eval(v) for v in row[2:]]
    else:
        text = False
        
        reader = bioformatsIO.BioformatsReader(fn)
        pxlsiz = reader.pxlsiz
        wave = reader.wave
        nw = reader.nw
        nt = reader.nt
        nz = reader.nz
        nz //= 2
        ny = reader.ny
        nx = reader.nx

        # read parameters
        refwave = eval(reader.ome.get_structured_annotation('refwave'))
        num_entry = eval(reader.ome.get_structured_annotation('num_entry'))

        alignParms = N.empty((reader.nt, reader.nw, reader.num_entry), N.float32)
        for t in xrange(reader.nt):
            for w in xrange(reader.nw):
                for i, key in enumerate(DIMSTRS):
                    alignParms[t,w,i] = eval(reader.ome.get_structured_annotation('t%03d_w%i_' %(t,w) + key))

    # loading parameters to the parent classes
    if rdr and holder:
        # reading the header
        if hasattr(rdr, 'pxlsiz'):
            dratio = N.asarray(pxlsiz, N.float32) / N.asarray(rdr.pxlsiz, N.float32)
        else: # chromeditor
            dratio = N.ones((3,), N.float32)
            rdr.pxlsiz = pxlsiz
            rdr.wave = wave
            rdr.nw = nw
            rdr.nt = nt
            rdr.nz = nz

        # wavelength difference
        pwaves = list(wave[:nw])
        twaves = list(rdr.wave[:rdr.nw])
        tids = [twaves.index(wave) for wave in pwaves if wave in twaves]
        pids = [pwaves.index(wave) for wave in twaves if wave in pwaves]

        somewaves = [w for w, wave in enumerate(pwaves) if wave in twaves]

        if refwave in twaves:
            holder.refwave = twaves.index(refwave)
        elif len(somewaves) >= 1: # the reference wavelength was not found but some found
            holder.refwave = somewaves[0]
            from PriCommon import guiFuncs as G
            message = 'The original reference wavelength %i of the initial guess was not found in the target %s' % (refwave, holder.file)
            G.openMsg(msg=message, title='WARNING')

        else:
            from PriCommon import guiFuncs as G
            message = 'No common wavelength with initial guess was found in %s and %s' % (os.path.basename(file), rdr.file)
            G.openMsg(msg=message, title='WARNING')
            return

        # compensate wavelength difference
        target = N.zeros((nt, rdr.nw, num_entry), N.float32)
        target[:,:,4:] = 1
        target[:,tids] = alignParms[:,pids]
        for w in [w for w, wave in enumerate(twaves) if wave not in pwaves]:
            target[:,w] = alignParms[:,holder.refwave]
        target[:,:,:3] *= dratio
        alignParms = target

        # set holder
        if hasattr(self.holder, 'setAlignParam'):
            holder.setAlignParam(alignParms)
        else:
            holder.alignParms = alignParms

        # obtain mapping array
        if not text:
            nzyx = N.array((nz, reader.ny, reader.nx), N.float32)
            nzyx *= dratio
            nyzx = nzyx.astype(N.int)

            tmin = min(rdr.nt, reader.nt)
            if nzyx[0] > 1:
                arr = N.zeros((rdr.nt, rdr.nw, nzyx[0], 2, nzyx[1], nzyx[2]), reader.dtype)
            else:
                arr = N.zeros((rdr.nt, rdr.nw, 2, nzyx[1], nzyx[2]), reader.dtype)
            
            for t in xrange(tmin):
                for wt, wp in enumerate(pids):
                    w = tids[wt]

                    a = N.zeros((nzyx[0], 2, nzyx[1], nzyx[2]), reader.dtype)
            
                    for z in xrange(nz):
                        warr = reader.get3DArr(t=t, w=w)
                        warr = warr.reshape((nz, 2, reader.ny, reader.nx))
                        for s in xrange(2):
                            zc = z * 2 + s
                            if any(dratio[1:] != 1):
                                a[z,s] = nd.zoom(warr[:,s], dratio) * dratio[1+(s%2)]
                            else:
                                arr[z,s] = warr[:,s]
                    
                    if nzyx[0] > 1:
                        arr[t,w] = a
                    else:
                        arr[t,w] = a[0]

            for w in [w for w, wave in enumerate(twaves) if wave not in pwaves]:
                arr[:tmin,w] = arr[:tmin,refwave]
            
            holder.mapyx = arr
    return reader
        

def _eval(val):
    try:
        return eval(val)
    except NameError:
        return val

            
class ChromagnonReader(object):
    def __init__(self, fn, rdr=None, holder=None):
        
        self.rdr = rdr
        self.holder = holder

        self.dratio = N.ones((3,), N.float32)

        if not is_binary(fn):
            self.filename = self.fn = fn
            self.dr, self.file = os.path.split(fn)
            
            self.fp = open(fn)
            self.reader = csv.reader(self.fp)
            self.text = True
            self._closed = False
        else:
            self.reader = bioformatsIO.BioformatsReader(fn)
            self.ome = bioformatsIO.OME_XML_Editor(self.reader.omexml)
            self.nz = self.reader.nz // 2
            self.text = False

        self.readParms()
            
        if rdr and holder:
            self.loadParm()
        #self.close()

    def close(self):
        if self.text:
            self.fp.close()
        else:
            self.reader.close()

    def readParms(self):
        if self.text:
            self.nz = 1
            self.nt = int(self.reader.next()[1])
            self.nw = int(self.reader.next()[1])
            self.pxlsiz = N.array([eval(p) for p in self.reader.next()[1:]])
            self.imgSequence = 2
            refwave = eval(self.reader.next()[1])
            self.num_entry = len(self.reader.next()[2:])
            self.wave = []
            #self.pos0 = self.tell()
            
            self.alignParms = N.empty((self.nt, self.nw, self.num_entry), N.float32)
            for t in xrange(self.nt):
                for w in xrange(self.nw):
                    row = self.reader.next()
                    if t == 0:
                        self.wave.append(int(round(self.eval(row[1]))))
                    self.alignParms[t,w] = [eval(v) for v in row[2:]]
            self.refwave = int(round(self.wave[refwave]))

        else:
            self.nt = self.reader.nt
            self.nw = self.reader.nw
            self.wave = [int(round(w)) for w in self.reader.wave]
            self.pxlsiz = self.reader.pxlsiz
            self.roi_size = self.reader.roi_size
            self.dtype = self.reader.dtype
            self.imgSequence = self.reader.imgSequence
            self.pxlsiz = self.reader.pxlsiz
            self.metadata = self.reader.metadata
            refwave = eval(self.reader.ome.get_structured_annotation('refwave'))
            self.num_entry = eval(self.reader.ome.get_structured_annotation('num_entry'))

            self.alignParms = N.empty((self.reader.nt, self.reader.nw, self.num_entry), N.float32)
            for t in xrange(self.reader.nt):
                for w in xrange(self.reader.nw):
                    for i, key in enumerate(DIMSTRS):
                        self.alignParms[t,w,i] = eval(self.reader.ome.get_structured_annotation('t%03d_w%i_' %(t,w) + key))
            self.refwave = int(round(self.reader.wave[refwave]))

    def eval(self, val):
        try:
            return eval(val)
        except NameError:
            return val
            
    def loadParm(self):
        """
        load a chromagnon file
        """

        # reading the header
        if hasattr(self.rdr, 'pxlsiz'):
            self.dratio = N.asarray(self.pxlsiz, N.float32) / N.asarray(self.rdr.pxlsiz, N.float32)
        else: # chromeditor
            self.dratio = N.ones((3,), N.float32)
            self.rdr.pxlsiz = self.pxlsiz
            self.rdr.wave = self.wave
            self.rdr.nw = self.nw
            self.rdr.nt = self.nt
            self.rdr.nz = self.nz

        # wavelength difference
        self.pwaves = [int(round(w)) for w in self.wave[:self.nw]]
        self.twaves = [int(round(w)) for w in self.rdr.wave[:self.rdr.nw]]
        self.tids = [self.twaves.index(wave) for wave in self.pwaves if wave in self.twaves]
        self.pids = [self.pwaves.index(wave) for wave in self.twaves if wave in self.pwaves]

        somewaves = [w for w, wave in enumerate(self.pwaves) if wave in self.twaves]

        if self.refwave in self.twaves:
            self.holder.refwave = self.twaves.index(self.refwave)
        elif len(somewaves) >= 1: # the reference wavelength was not found but some found
            self.holder.refwave = somewaves[0]
            from PriCommon import guiFuncs as G
            message = 'The original reference wavelength %i of the initial guess was not found in the target %s' % (self.refwave, self.holder.file)
            G.openMsg(msg=message, title='WARNING')

        else:
            #self.holder.parm = N.zeros((self.rdr.nt, self.rdr.nw, self.num_entry), self.dtype)
            from PriCommon import guiFuncs as G
            message = 'No common wavelength with initial guess was found in %s and %s' % (os.path.basename(self.file), self.rdr.file)
            G.openMsg(msg=message, title='WARNING')
            return

        # obtain affine parms
        self.readParmWave()

        if hasattr(self.holder, 'setAlignParam'):
            self.holder.setAlignParam(self.alignParms)
        else:
            self.holder.alignParms = self.alignParms


        # obtain mapping array
        if not self.text:
            self.holder.mapyx = self.readMapAll()

    def readParmWave(self):
        """
        return parm compensated for wavelength difference
        """
        # compensate wavelength difference
        if self.rdr:
            target = N.zeros((self.nt, self.rdr.nw, self.num_entry), N.float32)
            target[:,:,4:] = 1
            target[:,self.tids] = self.alignParms[:,self.pids]
            for w in [w for w, wave in enumerate(self.twaves) if wave not in self.pwaves]:
                target[:,w] = self.alignParms[:,self.holder.refwave]
            target[:,:,:3] *= self.dratio
            self.alignParms = target
            
    def finalDim(self):
        nzyx = N.array((self.nz, self.reader.ny, self.reader.nx), N.float32)
        nzyx *= self.dratio
        return nzyx.astype(N.int)
            
    def readMap3D(self, t=0, w=0):
        nzyx = self.finalDim()
        #print 't,w,nzyx,', t, w, nzyx, self.dratio, self.dratio.dtype
        arr = N.zeros((nzyx[0], 2, nzyx[1], nzyx[2]), self.reader.dtype)
            
        for z in xrange(self.nz):
            warr = self.reader.get3DArr(t=t, w=w)
            warr = warr.reshape((self.nz, 2, self.reader.ny, self.reader.nx))
            for s in xrange(2):
                zc = z * 2 + s
                if self.rdr and any(self.dratio[1:] != 1):
                    arr[z,s] = nd.zoom(warr[:,s], self.dratio) * self.dratio[1+(s%2)]
                else:
                    arr[z,s] = warr[:,s]
        return arr

    def readMapAll(self):
        nzyx = self.finalDim()
        if self.rdr:
            tmin = min(self.rdr.nt, self.nt)
            if nzyx[0] > 1:
                arr = N.zeros((self.rdr.nt, self.rdr.nw, nzyx[0], 2, nzyx[1], nzyx[2]), self.reader.dtype)
            else:
                arr = N.zeros((self.rdr.nt, self.rdr.nw, 2, nzyx[1], nzyx[2]), self.reader.dtype)
        else:
            tmin = self.nt
            if nzyx[0] > 1:
                arr = N.zeros((self.nt, self.nw, nzyx[0], 2, nzyx[1], nzyx[2]), self.reader.dtype)
            else:
                arr = N.zeros((self.nt, self.nw, 2, nzyx[1], nzyx[2]), self.reader.dtype)
            
        for t in xrange(self.nt):
            if t < tmin:
                for wt, wp in enumerate(self.pids):
                    w = self.tids[wt]
                    a = self.readMap3D(t=t, w=wp)
                    if nzyx[0] > 1:
                        arr[t,w] = a
                    else:
                        arr[t,w] = a[0]
                    
        for w in [w for w, wave in enumerate(self.twaves) if wave not in self.pwaves]:
            arr[:tmin,w] = arr[:tmin,self.refwave]
                    
        return arr

    def getWaveIdx(self, wave):
        """
        return index
        """
        wave = int(wave)
        # work around for eg. 450.000000000001 vs 450
        try:
            check = [i for i, w in enumerate(self.wave[:self.nw]) if abs(w - wave) < 0.000001]
        except TypeError:
            check = []
        #print check
        if wave in self.wave[:self.nw]:
            wave = list(self.wave).index(wave)
            return wave
        elif len(check) == 1:
            return check[0] 
        elif wave < self.nw:
            return wave
        else:
            raise ValueError, 'no such wave exists %s' % wave

    def getWaveFromIdx(self, w):
        """
        return wavelength (nm)
        """
        w = int(w)
        if w in self.wave[:self.nw]:
            return w
        elif w < self.nw: # idx
            return self.wave[w]
        else:
            raise ValueError, 'no such wavelength index exists %s' % w

    def setRefWave(self, refwave):
        """
        changes self.refwave and reset alignParms
        """
        self.refwave = self.getWaveFromIdx(refwave)
        idx = self.getWaveIdx(refwave)

        self.alignParms[...,:4] -= self.alignParms[:,idx,:4]
        self.alignParms[...,4:] /= self.alignParms[:,idx,4:]

def summarizeAlignmentData(fns, outfn='', refwave=1):
    """
    summarize chromagnon results into a single csv file.
    """
    if not outfn:
        outfn = os.path.commonprefix(fns) + '.csv'
    
    with open(outfn, 'w') as h:
        wtr = csv.writer(h)
        wtr.writerow(('file', 'time', 'wave', 'tz', 'ty', 'tx', 'r', 'mz', 'my', 'mx'))
        for fn in fns:
            r = ChromagnonReader(fn)
            r.setRefWave(refwave)
            for t in xrange(r.nt):
                for w, wave in enumerate(r.wave):
                    if wave != r.refwave:
                        alignParms = r.alignParms[t,w].copy()
                        alignParms[:3] *= r.pxlsiz
                        wtr.writerow([r.file, t, wave] + list(alignParms))
    return outfn

def makeNonliearImg(holder, out, gridStep=10):
    """
    save the result of non-linear transformation into the filename "out"
    gridStep: spacing of grid (number of pixels)

    return out
    """
    ext = ('.ome.tif', '.ome.tiff')
    if not out.endswith(ext):
        out = out + ext[0]

    if holder.mapyx.ndim == 6:
        arr = N.zeros(holder.mapyx.shape[:3]+holder.mapyx.shape[-2:], N.float32)
    else:
        arr = N.zeros(holder.mapyx.shape[:2]+holder.mapyx.shape[-2:], N.float32)
        
    for t in xrange(holder.nt):
        if hasattr(holder, 'img'):
            a = holder.img.get3DArr(w=holder.refwave, t=t)
            if holder.mapyx.ndim == 5:
                a = N.max(a, 0)
            arr[t,holder.refwave] = a
            me = a.max()
        else:
            me = 1.
        if holder.mapyx.ndim == 6:
            arr[t,:,:,::gridStep,:] = me
            arr[t,:,:,:,::gridStep] = me
        else:
            arr[t,:,::gridStep,:] = me
            arr[t,:,:,::gridStep] = me
        
    affine = N.zeros((7,), N.float64)
    affine[-3:] = 1

    writer = bioformatsIO.BioformatsWriter(out)

    if hasattr(holder, 'img'):
        writer.setFromReader(holder.img)
    elif hasattr(holder, 'creader'):
        writer.setFromReader(holder.creader)
    if holder.mapyx.ndim == 5:
        writer.nz = 1
    writer.dtype = N.float32

    for t in xrange(holder.nt):
        for w in xrange(holder.nw):
            a = arr[t,w]
            if a.ndim == 2:
                a = a.reshape((1,a.shape[0], a.shape[1]))
            a = af.remapWithAffine(a, holder.mapyx[t,w], affine)

            writer.write3DArr(a, t=t, w=w)
    del arr

    return out
