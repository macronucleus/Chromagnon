try:
    from . import generalIO
except ImportError:
    import generalIO
import czifile

def _eval(txt):
    try:
        return eval(txt)
    except (NameError, TypeError, SyntaxError):
        return txt

class CZIReader(generalIO.GeneralReader):
    def __init__(self, fn):
        """
        fn: file name
        """
        generalIO.GeneralReader.__init__(self, fn)

    def openFile(self):
        """
        open a file for reading
        """
        self.fp = czifile.CziFile(self.fn)
        self.handle = self.fp._fh
        
        self.readHeader()

    def readHeader(self):
        self.readMetaData()

        nt = self.fp.shape[self.fp.axes.index('T')]

        waves = [self.metadata['Channel%iEmissionWavelength' % w] for w in range(self.metadata['SizeC'])]
        for i, imgsq in enumerate(generalIO.IMGSEQ):
            if imgsq.replace('W', 'C') in self.fp.axes:
                imgSeq = i
                break

        self.setDim(self.metadata['SizeX'], self.metadata['SizeY'], self.metadata['SizeZ'], nt, self.metadata['SizeC'], self.fp.dtype, waves, imgSeq)

    def readMetaData(self):
        tree = self.fp.metadata.getroottree()
        root = tree.getroot()
        self.readTree(root)


    def readTree(self, tree):
        if tree.tag == 'Channels':
            self.readChannels(tree)
        else:
            children = tree.getchildren()
            if children:
                for child in children:
                    self.readTree(child)
            else:
                #if tree.tag.endswith('Wavelength'):
                #    raise
                self.metadata[tree.tag] = _eval(tree.text)

    def readChannels(self, tree):
        channels = tree.getchildren()
        for w, channel in enumerate(channels):
            for cha_info in channel:
                self.metadata[('Channel%i' % w) + cha_info.tag] = _eval(cha_info.text)
