from __future__ import division

try:
    from . import generalIO
except ImportError:
    import generalIO


import numpy as N

WRITABLE_FORMATS = ()
READABLE_FORMATS = ('lif',)
try:
    import readlif.reader as lif # GPL-3.0
    # https://github.com/nimne/readlif
except ImportError:
    READABLE_FORMATS = ()

class Reader(generalIO.Reader):
    def __init__(self, fn):
        """
        fn: file name
        """
        generalIO.Reader.__init__(self, fn)

    def openFile(self, series=0):
        """
        open a file for reading
        """
        self.handle = lif.LifFile(self.fn)

        self.fp = self.handle.get_image(series)
        self.readHeader()

    def readHeader(self):
        self.dataOffset = 0
        self._secExtraByteSize = 0

        nx = self.fp.dims_n[1]
        ny = self.fp.dims_n[2]
        nz = self.fp.dims_n[3]
        nt = self.fp.dims_n[4]
        nw = self.fp.channels

        dtype = N.uint16
        wave = self.fp.dims_n[5]
        imgseq = 0 # (x, y, z, t, m)

        self.setDim(nx, ny, nz, nt, nw, dtype, wave, imgseq)

        px = self.fp.scale_n[1] # px / um
        py = self.fp.scale_n[2]
        pz = self.fp.scale_n[3]
        self.setPixelSize(pz,py,px)

        metadata = {}
        metadata['bit'] = self.fp.bit_depth
        metadata['entire_image_acquisition_time'] = self.fp.scale_n[4] # images/frames (duration for the entire image acquisition

        self.metadata.update(metadata)
        self.metadata['lifmetadata'] = self.fp.info

        # excitation wavelength
        self.exc = self.fp.dims_n[9]


    def readSec(self, i=None):
        t, w, z = self.findDimFromIdx(i)
        return self.fp.get_frame(z=z, t=t, c=w)
