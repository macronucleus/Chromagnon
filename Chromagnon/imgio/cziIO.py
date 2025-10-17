import numpy as N

try:
    from . import generalIO
except ImportError:
    import generalIO

try:
    import czifile
    READABLE_FORMATS = ('czi',)
except ImportError:
    READABLE_FORMATS = ()
    
WRITABLE_FORMATS = ()

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
        self.fp = czifile.CziFile(self.fn)
        self.handle = self.fp._fh
        
        self.readHeader()

    def readHeader(self):
        ### FIXME: multiple axes needs to be handled

        
        self.readMetaData()
        meta = self.metadata
        img = meta['ImageDocument']['Metadata']['Information']['Image']
        nx = img['SizeX']
        ny = img['SizeY']
        nw = img.get('SizeC', 1) * img.get('Size0', 1)
        nz = img.get('SizeZ', 1) * img.get('SizeH', 1) * img.get('SizeR', 1) * img.get('SizeS', 1) * img.get('SizeI', 1) * img.get('SizeB', 1) * img.get('SizeM', 1) * img.get('SizeV', 1)
        # for SIM, it is phase-rot-z order
        if 'T' in self.fp.axes:
            nt = self.fp.shape[self.fp.axes.index('T')]
        else:
            nt = 1

        #axes = self.fp.axes[:-3].replace('C', 'W').replace('B', '').replace('V', '').replace('YX0', '')
        axes = self._findAxes().replace('C', 'W')
        imgSeq = self.findImgSequence(axes)

        channels = img['Dimensions']['Channels']['Channel']
        if type(channels) == dict: # nw=1
            channels = [channels]
        waves = []
        self.exc = []
        for channel in channels:
            waves.append(channel['EmissionWavelength'])
            self.exc.append(channel['ExcitationWavelength'])
            if waves[-1] == self.exc[-1]:
                try:
                    waves[-1] = (meta['ImageDocument']['Metadata']['Experiment']['ExperimentBlocks']['AcquisitionBlock']['MultiTrackSetup']['TrackSetup']['CenterWavelength'])*(10**9)
                    if waves[-1] == 0:
                        waves[-1] = self.exc[-1] * 1.075
                except KeyError:
                    pass

        self.setDim(nx, ny, nz=nz, nt=nt, nw=nw, dtype=self.fp.dtype, wave=waves, imgSequence=imgSeq)

        #pz = img['Dimensions']['Z']['Interval']['Increment']
        scl = meta['ImageDocument']['Metadata']['Scaling']['Items']['Distance']
        pdic = {}
        for s in scl:
            pdic['p%s' % s['Id'].lower()] = s['Value']*(10**6)

        self.setPixelSize(**pdic)

        try:
            obj = self.na = meta['ImageDocument']['Metadata']['Information']['Instrument']['Objectives']['Objective']
            if type(obj) == list: # lightsheet images
                obj = obj[0]
            self.optics_data['na'] = self.na = obj['LensNA']
            
            #self.optics_data['na'] = self.na = meta['ImageDocument']['Metadata']['Information']['Instrument']['Objectives']['Objective']['LensNA']
            self.optics_data['n1'] = self.n1 = img['ObjectiveSettings']['RefractiveIndex']
            
        except (KeyError, TypeError):
            pass
            

    def readMetaData(self):
        self.metadata = self.fp.metadata(False)

    def readSec(self, i):
        xy0 = self.roi_start[1:]
        xy1 = xy0 + self.roi_size[1:]

        sdir = self.fp.filtered_subblock_directory[i]
        subblock = sdir.data_segment()
        a = subblock.data(raw=False, resize=True, order=0)
        return a.ravel().reshape((self.ny, self.nx))[xy0[0]:xy1[0], xy0[1]:xy1[1]]

    def _findAxes(self):
        axes = self.fp.axes[:-3] # remove YX0
        shape = N.array(self.fp.shape[:-2]) # remove YX
        squeeze = shape - 1
        idx = [i for i, a in enumerate(axes) if squeeze[i]]
        axe2 = [axes[i] for i in idx]
        shape2 = [shape[i] for i in idx]
        axe3 = [a for a in axe2] # copy
        
        starts = []
        for sdir in self.fp.filtered_subblock_directory:
            start = [sdir.dimension_entries[i].start for i in idx]
            starts.append(start)

        diff = N.diff(starts, axis=0)
        for i, a in enumerate(axe2):
            for j in range(N.prod(shape2)):
                if j < diff.shape[0] and 1 in diff[j]:
                    id0 = N.argwhere(diff[j]==1)[0][0]
                    axe3[-1-i] = axe2[id0]
                    #diff = N.delete(diff, id0, -1)
                    diff[:,id0] = 0
                    break
        
        return ''.join(axe3)
                
    
# map dimension character to description
DIMENSIONS = {
    '0': 'Sample',  # e.g. RGBA
    'X': 'Width',
    'Y': 'Height',
    'C': 'Channel',
    'Z': 'Slice',  # depth
    'T': 'Time',
    'R': 'Rotation', # e.g. SIM rotation
    'S': 'Scene',  # contiguous regions of interest in a mosaic image
    'I': 'Illumination',  # direction
    'B': 'Block',  # acquisition
    'M': 'Mosaic',  # index of tile for compositing a scene
    'H': 'Phase',  # e.g. Airy detector fibers, SIM phase
    'V': 'View',  # e.g. for SPIM
}
