from __future__ import division

try:
    from . import generalIO
except ImportError:
    import generalIO


import numpy as N

try:
    import nd2
    # should be > 0.10.1, 0.5.3 did not work (no read_frame)
    from nd2._util import AXIS
    WRITABLE_FORMATS = ()
    READABLE_FORMATS = ('nd2',)
except ImportError:
    WRITABLE_FORMATS = READABLE_FORMATS = ()


class Reader(generalIO.Reader):
    def __init__(self, fn):
        """
        fn: file name
        """
        generalIO.Reader.__init__(self, fn)

    def openFile(self):
        """
        open a file for reading
        """
        self.fp = nd2.ND2File(self.fn)
        self.handle = self.fp._rdr # actual file handler is inside of it
        
        self.readHeader()

    def readHeader(self):
        self.dataOffset = 0
        self._secExtraByteSize = 0
        
        nx = self.fp.sizes.get(AXIS.X, 1)
        ny = self.fp.sizes.get(AXIS.Y, 1)
        nt = self.fp.sizes.get(AXIS.TIME, 1)
        if self.fp.is_rgb:
            nw = self.fp.sizes.get(AXIS.RGB, 1)
        else:
            nw = self.fp.sizes.get(AXIS.CHANNEL, 1)
        nz = self.fp.sizes.get(AXIS.Z, 1)
        
        dtype = self.fp.dtype
        wave = [cc.channel.emissionLambdaNm for cc in self.fp.metadata.channels]
        imgseqstr = ''.join(self.fp.sizes.keys()) # ordered
        if 'C' in imgseqstr[-3:]:
            self.axes = imgseqstr[-3:]
        imgseqstr = imgseqstr.replace('C', 'W')
        imgseqstr = imgseqstr.replace('X', '')
        imgseqstr = imgseqstr.replace('Y', '')
        imgseq = self.findImgSequence(imgseqstr)

        
        
        self.setDim(nx, ny, nz, nt, nw, dtype, wave, imgseq)

        vv = self.fp.voxel_size()
        
        self.pxlsiz = (vv.z, vv.y, vv.x) # um

        self.metadata['nd2metadata'] = (self.fp.metadata)

        # excitation wavelength
        self.exc = [cc.channel.excitationLambdaNm for cc in self.fp.metadata.channels]

        # objective lens
        try:
            self.optics_data['na'] = [cc.microscope.objectiveNumericalAperture for cc in self.fp.metadata.channels]
            self.optics_data['n1'] = [cc.microscope.immersionRefractiveIndex for cc in self.fp.metadata.channels]
            self.optics_data['mag'] = [cc.microscope.objectiveMagnification for cc in self.fp.metadata.channels]
        except KeyError:
            pass

        try:
            self.na = self.optics_data['na'][0]
            self.n1 = self.optics_data['n1'][0]
            self.mag = self.optics_data['mag'][0]
        except IndexError:
            pass


    def readSec(self, i=None):
        if hasattr(self.fp, 'read_frame'):
            arr = self.fp.read_frame(i)
        else:
            arr = self.fp._get_frame(i)
            
        if arr.ndim == 3 and self.axes[0] in ('S', 'C', 'W'):# == 'SYX'
            arr = arr[self.axes_w]
        elif arr.ndim == 3 and self.axes[-1] in ('S', 'C', 'W'):# == 'SYX'
            arr = arr[...,self.axes_w]
        return arr[...,::-1]
