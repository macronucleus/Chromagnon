
import os, csv, sys
import numpy as N
from scipy import ndimage as nd

try:
    from Chromagnon.PriCommon import imgGeo
    from Chromagnon import imgio
except ImportError:
    from PriCommon import imgGeo
    import imgio


IDTYPE = '101'
PARM_EXT=('chromagnon.csv', 'chromagnon.tif', 'chromagnon.tiff','chromagnon.ome.tif', 'chromagnon.ome.tiff', 'chromagnon')
DIMSTRS = ('tz', 'ty', 'tx', 'rz', 'mz', 'my', 'mx')

#for ext in PARM_EXT[1:]:
#    if ext not in bioformatsIO.OMETIFF:
#        bioformatsIO.OMETIFF = tuple(list(bioformatsIO.OMETIFF) + [ext])


def is_binary(fn):
    """
    return if fn is chromagnon.ome.tif
    """
    if fn.endswith(PARM_EXT[1:3]):
        return True
    elif os.path.isfile(fn):
        # http://stackoverflow.com/questions/898669/how-can-i-detect-if-a-file-is-binary-non-text-in-python
        textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
        is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
        return is_binary_string(open(fn, 'rb').read(1024))

def is_chromagnon(fn, check_img_to_open=False):
    """
    return True if fn is a chromagnon file
    """
    check = False
    if fn.endswith(PARM_EXT):
        check = True
    elif os.path.isfile(fn):
        is_image = is_binary(fn)
        if not is_image:
            with open(fn) as rdr:
                #if rdr.next().startswith('nt') and rdr.next().startswith('nw'):
                if next(rdr).startswith('nt') and next(rdr).startswith('nw'):
                    check = True
            
        elif is_image and check_img_to_open:
            rdr = imgio.Reader(fn)#bioformatsIO.BioformatsReader(fn)
            if hasattr(rdr, 'ome'):
                if rdr.metadata['idtype'] == IDTYPE:#ome.get_structured_annotation('idtype') == IDTYPE:
                    check = True
            rdr.close()

    return check

def makeChromagnonFileName(base, binary):
    if binary:
        return os.path.extsep.join((base, PARM_EXT[1]))
    else:
        return os.path.extsep.join((base, PARM_EXT[0]))

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
        self.rdr = rdr
        self.holder = holder
        self.fp = None
        self._closed = False

        self.num_entry = self.holder.alignParms.shape[-1]
        self.refwave = self.holder.refwave#)#list(self.rdr.wave).index(self.holder.refwave)

        # text formats
        if self.holder.mapyx is None:
            if sys.version_info.major == 3:
                self.fp = open(outfn, 'w', newline='')
            else:
                self.fp = open(outfn, 'w')
            self.writer = csv.writer(self.fp)

        else:
            self.writer = imgio.Writer(outfn, self.rdr)

            if holder.mapyx.ndim == 6:
                self.writer.setDim(nz=self.writer.nz*2)#self.writer.nz *= 2
            else:
                self.writer.setDim(nz=2) #self.writer.nz = 2
            #self.writer.imgSequence = 2
            self.writer.dtype = N.float32
                
        self.writeHdr()
        #self.writeAlignParamAll()
        
        #self.close()

    def close(self):
        if not self._closed:
            if self.holder.mapyx is None:
                self.fp.close()
            else:
                self.writer.close()

            self._closed = True

    def writeHdr(self):
        if self.holder.mapyx is None:
            self.writer.writerow(('nt', self.rdr.nt))
            self.writer.writerow(('nw', self.rdr.nw))
            self.writer.writerow(('pxlsize_z_y_x',) + tuple(self.rdr.pxlsiz))
            self.writer.writerow(('refwave', self.refwave))
            self.writer.writerow(('t', 'wavelength',) + DIMSTRS)
        else:
            if self.writer.file.endswith('ome.tif'):
                self.writer.ome.add_structured_annotation('refwave', str(self.refwave))
                self.writer.ome.add_structured_annotation('num_entry', str(self.num_entry))
                self.writer.ome.add_structured_annotation('idtype', IDTYPE)
            else:
                d = {'refwave': str(self.refwave),
                     'num_entry': str(self.num_entry),
                     'idtype': IDTYPE}
            
                self.writer.metadata.update(d)#ex_metadata.update(d)

    def writeAlignParmSingle(self, t=0, w=0):
        parm = self.holder.alignParms[t,w]

        if self.holder.mapyx is None:
            self.writer.writerow([t, self.rdr.wave[w]]+list(parm))
        else:
            for i, key in enumerate(DIMSTRS):
                if self.writer.file.endswith('ome.tif'):
                    self.writer.ome.add_structured_annotation('t%03d_w%i_' %(t,w) + key, str(parm[i]))
                else:
                    self.writer.metadata['t%03d_w%i_' %(t,w) + key] = str(parm[i])#ex_metadata['t%03d_w%i_' %(t,w) + key] = str(parm[i])

    def writeAlignParamAll(self):
        for t in range(self.rdr.nt):
            for w in range(self.rdr.nw):
                self.writeAlignParmSingle(t=t,w=w)

        if self.holder.mapyx is not None:
            self.writeMapAll()
            
    def writeMapAll(self):
        for t in range(self.rdr.nt):
            for w in range(self.rdr.nw):
                for z in range(self.writer.nz):
                    if self.holder.mapyx.ndim == 6:
                        d = z % 2
                        z0 = z // 2
                        arr = self.holder.mapyx[t,w,z0,d]
                    else:
                        arr = self.holder.mapyx[t,w,z]
                    self.writer.writeArr(arr, t=t, w=w, z=z)


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
            self.reader = imgio.Reader(fn)
            self.nz = self.reader.nz // 2
            self.ny = self.reader.ny
            self.nx = self.reader.nx
            self.text = False

        self.readParms()
            
        if rdr and holder:
            self.loadParm()

    def close(self):
        if self.text:
            self.fp.close()
        else:
            self.reader.close()

    def readParms(self):
        if self.text:
            self.nz = 1
            self.nt = int(next(self.reader)[1])#self.reader.next()[1])
            self.nw = int(next(self.reader)[1])#self.reader.next()[1])
            self.pxlsiz = N.array([self.eval(p) for p in next(self.reader)[1:]])#self.reader.next()[1:]])
            self.imgSequence = 2
            refwave = self.eval(next(self.reader)[1])#self.reader.next()[1])
            self.num_entry = len(next(self.reader)[2:])#self.reader.next()[2:])
            self.wave = []
            #self.pos0 = self.tell()
            
            self.alignParms = N.empty((self.nt, self.nw, self.num_entry), N.float32)
            for t in range(self.nt):
                for w in range(self.nw):
                    row = next(self.reader)
                    if t == 0:
                        self.wave.append(int(round(self.eval(row[1]))))
                    self.alignParms[t,w] = [self.eval(v) for v in row[2:]]
            self.refwave = int(round(self.wave[refwave]))

        else:
            self.nt = self.reader.nt
            self.nw = self.reader.nw
            self.wave = [int(round(w)) for w in self.reader.wave]
            self.pxlsiz = self.reader.pxlsiz
            self.roi_size = self.reader.roi_size
            #self.roi_size[0] //= 2 # dim
            self.dtype = self.reader.dtype
            self.imgSequence = self.reader.imgSequence
            self.pxlsiz = self.reader.pxlsiz
            self.metadata = self.reader.metadata
            self.ex_metadata = self.reader.ex_metadata
            #refwave = self.eval(str(self.reader.ome.get_structured_annotation('refwave')))
            refwave = self.reader.metadata['refwave']
            #self.num_entry = self.eval(str(self.reader.ome.get_structured_annotation('num_entry')))
            self.num_entry = self.reader.metadata['num_entry']

            #temp = """
            self.alignParms = N.empty((self.reader.nt, self.reader.nw, self.num_entry), N.float32)
            for t in range(self.reader.nt):
                for w in range(self.reader.nw):
                    for i, key in enumerate(DIMSTRS):
                        self.alignParms[t,w,i] = self.eval(str(self.reader.metadata['t%03d_w%i_' %(t,w) + key]))#ome.get_structured_annotation('t%03d_w%i_' %(t,w) + key)))
            self.refwave = int(round(self.reader.wave[refwave]))
            self.refwave_idx = refwave#"""

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
            message = 'The original reference wavelength %i of the initial guess was not found in the target %s' % (self.refwave, self.holder.fn)
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
        nzyx = N.array((self.nz, self.reader.ny, self.reader.nx), N.int)#float32)
        #nzyx[-2:] *= self.dratio[-2:]
        return nzyx#N.round_(nzyx).astype(N.int)
            
    def readMap3D(self, t=0, w=0):
        nzyx = self.finalDim()
        #print 't,w,nzyx,', t, w, nzyx, self.dratio, self.dratio.dtype
        arr = N.zeros((nzyx[0], 2, nzyx[1], nzyx[2]), self.reader.dtype)

        old="""
        for z in xrange(self.nz):
            warr = self.reader.get3DArr(t=t, w=w)
            warr = warr.reshape((self.nz, 2, self.reader.ny, self.reader.nx))
            for s in xrange(2):
                zc = z * 2 + s
                if self.rdr and any(self.dratio[1:] != 1):
                    arr[z,s] = nd.zoom(warr[z,s], self.dratio[-2:]) * self.dratio[1+s]#(s%2)]
                else:
                    arr[z,s] = warr[:,s]"""
        warr = self.reader.get3DArr(t=t, w=w)
        warr = warr.reshape((self.nz, 2, self.reader.ny, self.reader.nx))
        for s in range(2):
            if self.rdr and any(self.dratio[1:] != 1):
                for z in range(self.nz):
                    arr[z,s] = warr[z,s] / self.dratio[1+s]#nd.zoom(warr[z,s], self.dratio[-2:]) * self.dratio[1+s]#(s%2)]
            else:
                arr[:,s] = warr[:,s]
        
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
            
        for t in range(self.nt):
            if t < tmin:
                for wt, wp in enumerate(self.pids):
                    w = self.tids[wt]
                    a = self.readMap3D(t=t, w=wp)
                    if nzyx[0] > 1:
                        arr[t,w] = a
                    else:
                        arr[t,w] = a[0]

        for w in [w for w, wave in enumerate(self.twaves) if wave not in self.pwaves]:
            arr[:tmin,w] = arr[:tmin,self.refwave_idx]
                    
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
            raise ValueError('no such wave exists %s' % wave)

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
            raise ValueError('no such wavelength index exists %s' % w)

    def setRefWave(self, refwave):
        """
        changes self.refwave and reset alignParms
        """
        self.refwave = self.getWaveFromIdx(refwave)
        idx = self.getWaveIdx(refwave)

        self.alignParms[...,:4] -= self.alignParms[:,idx,:4]
        self.alignParms[...,4:] /= self.alignParms[:,idx,4:]

def summarizeAlignmentData(fns, outfn='', refwave=0, calc_rotmag=True, npxls=(64,512,512)):
    """
    summarize chromagnon results into a single csv file.
    """
    if not outfn:
        outfn = os.path.commonprefix(fns) + '.csv'

    center = N.divide(npxls, 2)

    with open(outfn, 'w') as h:
        wtr = csv.writer(h)
        if calc_rotmag:
            wtr.writerow(('file', 'time', 'wave', 'tz', 'ty', 'tx', 'r', 'mz', 'my', 'mx', 'SUM'))
        else:
            wtr.writerow(('file', 'time', 'wave', 'tx', 'ty', 'tz', 'mx', 'my', 'mz', 'r'))
        for fn in fns:
            r = ChromagnonReader(fn)
            r.setRefWave(refwave)
            pxlsiz = r.pxlsiz
            if calc_rotmag:
                pxlsiz *= 1000 # in nm
            for t in range(r.nt):
                for w, wave in enumerate(r.wave):
                    if wave != r.refwave:
                        dev = r.alignParms[t,w].copy()
                        dev[:3] *= pxlsiz

                        if calc_rotmag:
                            # rotation
                            rpos = imgGeo.rotate(center[1:], dev[3])
                            #print dev[3], rpos, pxlsiz, imgGeo.euclideanDist(rpos, center[1:])
                            dev[3] = imgGeo.euclideanDist(rpos, center[1:]) * N.average(pxlsiz[-2:])

                            # magnification
                            mpos = center * dev[-3:]
                            dev[-3:] = N.abs(mpos - center) * pxlsiz

                            # sum
                            ss = N.power(dev, 2)
                            ss = N.sum(ss, axis=-1)
                            ss = N.sqrt(ss)
                            wtr.writerow([r.file, t, wave] + list(dev) + [ss])
                        else:
                            dev2 = dev.copy()
                            dev[:3] = N.round_(dev2[:3][::-1], 3)
                            dev[3:6] = N.round_(dev2[4:7][::-1], 4)
                            dev[6] = N.round_(dev2[3], 4)
                            wtr.writerow([r.file, t, wave] + list(dev))

                    #else:
                    #    wtr.writerow([r.file, t, wave] + [0,0,0,0,0,0,0])
    return outfn

moved2alignfunc20180806='''
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
        
    for t in range(holder.nt):
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

    writer = imgio.Writer(out)#bioformatsIO.BioformatsWriter(out)

    if hasattr(holder, 'img'):
        writer.setFromReader(holder.img)
    elif hasattr(holder, 'creader'):
        writer.setFromReader(holder.creader)
    if holder.mapyx.ndim == 5:
        writer.nz = 1
    writer.dtype = N.float32

    for t in range(holder.nt):
        for w in range(holder.nw):
            a = arr[t,w]
            if a.ndim == 2:
                a = a.reshape((1,a.shape[0], a.shape[1]))
            a = af.remapWithAffine(a, holder.mapyx[t,w], affine)

            writer.write3DArr(a, t=t, w=w)
    del arr

    return out

def makeNonliearImg_tmp(holder, out, gridStep=10):
    """
    save the result of non-linear transformation into the filename "out"
    gridStep: spacing of grid (number of pixels)

    return out
    """
    ext = ('.ome.tif', '.ome.tiff')
    if not out.endswith(ext):
        out = out + ext[0]

    if holder.mapyx.ndim == 6:
        nz = holder.mapyx.shape[2]
        arr = N.zeros(holder.mapyx.shape[:3]+holder.mapyx.shape[-2:], N.float32)
    else:
        nz = 1
        arr = N.zeros(holder.mapyx.shape[:2]+holder.mapyx.shape[-2:], N.float32)

    yr = range(gridStep, holder.mapyx.shape[-2]-gridStep, gridStep)
    xr = range(gridStep, holder.mapyx.shape[-1]-gridStep, gridStep)
        
    for t in range(holder.nt):
        if hasattr(holder, 'img'):
            a = holder.img.get3DArr(w=holder.refwave, t=t)
            if holder.mapyx.ndim == 5:
                a = N.max(a, 0)
            arr[t,holder.refwave] = a
            me = a.max()
        else:
            me = 1.

        for w in range(holder.nw):
            if w == holder.refwave:
                continue

            for z in range(nz):
                for y in yr:
                    for x in xr:
                        pos0 = N.array((y,x))
                        pos1 = self.mapyx[:,y,x]
                        
            
        if holder.mapyx.ndim == 6:
            arr[t,:,:,::gridStep,:] = me
            arr[t,:,:,:,::gridStep] = me
        else:
            arr[t,:,::gridStep,:] = me
            arr[t,:,:,::gridStep] = me
        
    affine = N.zeros((7,), N.float64)
    affine[-3:] = 1

    writer = imgio.Writer(out)#bioformatsIO.BioformatsWriter(out)

    if hasattr(holder, 'img'):
        writer.setFromReader(holder.img)
    elif hasattr(holder, 'creader'):
        writer.setFromReader(holder.creader)
    if holder.mapyx.ndim == 5:
        writer.nz = 1
    writer.dtype = N.float32

    for t in range(holder.nt):
        for w in range(holder.nw):
            a = arr[t,w]
            if a.ndim == 2:
                a = a.reshape((1,a.shape[0], a.shape[1]))
            a = af.remapWithAffine(a, holder.mapyx[t,w], affine)

            writer.write3DArr(a, t=t, w=w)
    del arr

    return out
'''

class dummyHolder(object):
    def __init__(self):
        self.mapyx = None
        self.alignParms = None
        self.refwave = 0
        
def averageChromagnon(fns, out=None):
    """
    temporally function to average chromagnon parameter file
    """
    n = len(fns)
    if n == 1:
        return fns[0]
    elif n == 0:
        raise ValueError('fns has to have at least one file name')
        
    binars = [is_binary(fn) for fn in fns]
    for bn in binars[1:]:
        if bn != binars[0]:
            raise ValueError('Formats (csv, tif) of the chromagnon files are mixed')
    binar = binars[0]
    if not out:
        out = makeChromagnonFileName(os.path.commonprefix(fns) + '_ave', binar)

    rrs = [ChromagnonReader(fn) for fn in fns]
    r = rrs[0]
    refwave = r.refwave
    [r.setRefWave(refwave) for r in rrs]
    ave = N.average([r.alignParms for r in rrs], axis=0)
    
    holder = dummyHolder()
    holder.alignParms = ave
    #holder.refwave = refwave
    holder.refwave = r.wave.index(r.refwave)
    
    if binar:
        for r in rrs[1:]:
            if r.nw != rrs[0].nw or r.nt != rrs[0].nt or r.nz != rrs[0].nz or r.ny != rrs[0].ny or r.nx != rrs[0].nx:
                raise ValueError('Different dimensions found for chromagon.tif files')
        if r.nz > 1:
            arr = N.empty((n, r.nt, r.nw, r.nz, 2, r.ny, r.nx), N.float32)
        else:
            arr = N.empty((n, r.nt, r.nw, 2, r.ny, r.nx), N.float32)
        for i, r in enumerate(rrs):
            for t in range(r.nt):
                for w in range(r.nt):
                    arr[i, t, w] = r.readMap3D(t=t, w=w)
        arr = N.average(arr, axis=0)
        holder.mapyx = arr

    wtr = ChromagnonWriter(out, r, holder)
    wtr.writeAlignParamAll()
    wtr.close()

    return out
    

def flipChromagnonParms(fn, outfn=None, refwave=0):
    """
    temporally function to inverse chromagnon parameter
    write out a new chromagnon file
    """
    if not outfn:
        base, ext = os.path.splitext(fn)
        outfn = base + '_flip' + ext

    r = ChromagnonReader(fn)
    r.setRefWave(refwave)
    parm = N.empty_like(r.alignParms)
    for t in range(r.nt):
        for w in range(r.nw):
            if w != refwave:
                parm[t,w,:4] = r.alignParms[t,w,:4] * -1
                parm[t,w,4:] = 1. / r.alignParms[t,w,4:]
            else:
                parm[t,w,:4] = 0
                parm[t,w,4:] = 1.

    holder = dummyHolder()
    holder.alignParms = parm
    holder.refwave = refwave
    holder.refwve = r.wave.index(r.refwave)

    ChromagnonWriter(outfn, r, holder)

    return outfn
            
