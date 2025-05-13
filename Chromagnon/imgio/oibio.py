try:
    from . import generalIO
except ImportError:
    import generalIO


try:
    import tifffile
    from . import multitifIO
    import oiffile as oib # BSD-3-Clause
    # https://github.com/cgohlke/oiffile
    WRITABLE_FORMATS = ()
    READABLE_FORMATS = ('oif', 'oib') # oir is not supported yet
except ImportError:
    WRITABLE_FORMATS = READABLE_FORMATS = ()


class Reader(generalIO.Reader):
    def __init__(self, fn):
        """
        fn: file name
        """
        generalIO.Reader.__init__(self, fn)

    def openFile(self, series_id=0):
        """
        open a file for reading
        """
        self.fp = oib.OifFile(self.fn)
        series = self.fp.series[series_id]
        self.handle = self.fp.open_file(series)
        #self.tiff = tifffile.TiffFile(self.handle, name=series)
        self.handle._name = series
        self.tiff = multitifIO.Reader(self.handle)#, name=series)
        self.tiff.fp.filehandle._name = series
        
        self.readHeader()

    def readHeader(self):
        ### FIXME: multiple axes needs to be handled

        
        self.readMetaData()
        meta = self.metadata
        img = meta['ImageDocument']['Metadata']['Information']['Image']
        nx = img['SizeX']
        ny = img['SizeY']
        nw = img.get('SizeC', 1)
        nz = img.get('SizeZ', 1)
        if 'T' in self.fp.axes:
            nt = self.fp.shape[self.fp.axes.index('T')]
        else:
            nt = 1

        axes = self.fp.axes[:-3].replace('C', 'W').replace('B', '').replace('V', '').replace('YX0', '')
        imgSeq = self.findImgSequence(axes)

        channels = img['Dimensions']['Channels']['Channel']
        waves = []
        self.exc = []
        for channel in channels:
            waves.append(channel['EmissionWavelength'])
            self.exc.append(channel['ExcitationWavelength'])

        self.setDim(nx, ny, nz=nz, nt=nt, nw=nw, dtype=self.fp.dtype, wave=waves, imgSequence=imgSeq)

        #pz = img['Dimensions']['Z']['Interval']['Increment']
        scl = meta['ImageDocument']['Metadata']['Scaling']['Items']['Distance']
        pdic = {}
        for s in scl:
            pdic['p%s' % s['Id'].lower()] = s['Value']*(10**6)

        self.setPixelSize(**pdic)

    def readMetaData(self):
        self.metadata = self.fp.metadata(False)

    def seekSec(self, i=0):
        self.tiff.seekSec(i)

    def readSec(self, i=0):
        return self.tiff.readSec(i)
