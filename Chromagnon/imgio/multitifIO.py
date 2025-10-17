from __future__ import division
import sys
try:
    from . import generalIO
except ImportError:
    import generalIO
import six


import struct, copy, inspect
    
import numpy as N

try:
    import tifffile # 2020.11.26 - 2021.7.2
    from tifffile import tifffile as tifff
    ## MEMO: "ImageJ does  not support non-contiguous data" means shape does not match
    WRITABLE_FORMATS = ('tif', 'tiff')
    tifversion = tifffile.__version__.split('.')
    if int(tifversion[0]) > 2021 or (int(tifversion[0]) >= 2021 and int(tifversion[1]) >= 11):
        WRITABLE_FORMATS += ('ome.tif', 'ome.tiff')
        READABLE_FORMATS = WRITABLE_FORMATS + ('lsm',)
    else:
        READABLE_FORMATS = WRITABLE_FORMATS + ('ome.tif', 'ome.tiff', 'lsm')
except ImportError:
    WRITABLE_FORMATS = READABLE_FORMATS = ()
    

IMAGEJ_METADATA_TYPES = ['Info', 'Labels', 'Ranges', 'LUTs', 'Plot', 'ROI', 'Overlays']

PXUNIT_FACTORS = {'m': 0, 'mm': -3, u'\xb5'+'m': -6, 'nm': -9, 'micron': -6, 'um': -6}


def _convertUnit(val, fromwhat='mm', towhat=u'\xb5'+'m'):
    factors = PXUNIT_FACTORS
    factor = factors[fromwhat] - factors[towhat] or 0
    return float(val) * 10 ** factor

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
        self.fp = tifffile.TiffFile(self.fn)
        self.handle = self.fp.filehandle
        
        self.readHeader()

    def readHeader(self):
        self.readMetaData()

        s = self.fp.series[0]
        shape = s.shape

        if self.fp.is_imagej and not self.fp.is_micromanager and 'channels' in self.metadata:
            imgSeq = 1
            nw = nt = nz = 1

            if 'channels' in self.metadata:
                nw = self.metadata['channels']
            if 'slices' in self.metadata:
                nz = self.metadata['slices']
            if 'frames' in self.metadata:
                nt = self.metadata['frames']
            #print('imagej')
        
        elif 0:#self.fp.is_micromanager:
            nw = self.metadata['Channels']
            nz = self.metadata['Slices']
            nt = self.metadata['Frames']
            axes = s.axes.replace('C', 'W')
            imgSeq = self.findImgSequence(axes[:-2])
            #print('micromanager', nw, nz, nt)
            #axes = 'TZCYXS'
        else:
           # print('other')
            axes = s.axes.replace('S', 'W')    # sample (rgb)
            axes = axes.replace('C', 'W')      # color, emission wavelength
            axes = axes.replace('E', 'W')      # excitation wavelength
            if 'Z' not in axes:
                axes = axes.replace('I', 'Z')  # general sequence, plane, page, IFD
            elif 'W' not in axes:
                axes = axes.replace('I', 'W')
            elif 'T' not in axes:
                axes = axes.replace('I', 'T')
            if 'Z' not in axes:
                axes = axes.replace('Q', 'Z') # other
            elif 'W' not in axes:
                axes = axes.replace('Q', 'W')
            elif 'T' not in axes:
                axes = axes.replace('Q', 'T')
            imgSeq = self.findImgSequence(axes.replace('YX', ''))#[:-2])


            nz = nt = nw = 1
            if 'Z' in axes:
                zaxis = axes.index('Z')
                nz = shape[zaxis]

            if 'T' in axes:
                taxis = axes.index('T')
                nt = shape[taxis]

            if 'W' in axes:
                waxis = axes.index('W')
                nw = shape[waxis]
        waves = generalIO.makeWaves(nw)

        
        p = self.fp.pages[0]

        if int(tifffile.__version__.split('.')[0]) == 0:
            self.dataOffset = p.offsets_bytecounts[0][0]
            if len(self.fp.pages) > 1:
                page1_offset     = self.fp.pages[1].offsets_bytecounts[0][0]
                page0_offset     = self.fp.pages[0].offsets_bytecounts[0][0]
                page0_byte_count = self.fp.pages[0].offsets_bytecounts[1][0]
        else: # recent versions of tifffile 20210618
            self.dataOffset = p.dataoffsets[0]
            if len(self.fp.pages) > 1:
                page1_offset     = self.fp.pages[1].dataoffsets[0]
                page0_offset     = self.fp.pages[0].dataoffsets[0]
                page0_byte_count = self.fp.pages[0].databytecounts[0]

        if len(self.fp.pages) > 1:
            self._secExtraByteSize = page1_offset - page0_offset - page0_byte_count
        else:
            self._secExtraByteSize = 0

        dtype = s.dtype or p.dtype
        if not issubclass(type(dtype), N.dtype): # 20210618
            raise generalIO.ImageIOError('data type not found')
            
        waves = self.readChannelInfo(nw, waves)

        self.setDim(p.imagewidth, p.imagelength, nz, nt, nw, dtype, waves, imgSeq)
        #self.setPixelSize(p.samplesperpixel)
        
        self.axes = p.axes # axis of one section
        self.compress = p.compression

        # since imageJ stores all image metadata in the first page
        #if self.fp.is_imagej or self.readSec(0).ndim > 2:
        #    self.arr = self.fp.pages[0].asarray()

    def readMetaData(self):
        """
        read pixel size and extra info
        """
        self.ex_metadata = {}
        p = self.fp.pages[0]

        if self.fp.is_micromanager: # also is_ome and is_imagej
            self.metadata = meta = self.fp.micromanager_metadata['Summary']
            px = abs(meta.get('PixelSize_um', 0.1))
            if not px:
                px = 0.1
            asp = meta.get('PixelAspect', 1)
            py = px * asp # is this correct?
            pz = abs(meta.get('z-step_um', 0.3))
            if not pz:
                pz = 0.3
            self.setPixelSize(pz, py, px)
        
        elif self.fp.is_ome:
            tifversion = tifffile.__version__.split('.')
            if int(tifversion[0]) >= 2020:
                self.metadata = xml2dict(self.fp.ome_metadata)
            else:
                self.metadata = self.fp.ome_metadata
            if 'OME' in self.metadata:
                self.metadata = meta = self.metadata['OME']
            else:
                self.metadata = meta = self.metadata
            # pixel size
            px = meta['Image']['Pixels']
            pxlsiz = [0.1, 0.1, 0.1]
            for d, dim in enumerate(('Z', 'Y', 'X')):
                if px['PhysicalSize%sUnit' % dim] in PXUNIT_FACTORS: # unit can be "pixel"
                    pxlsiz[d] = _convertUnit(px['PhysicalSize%s' % dim], px['PhysicalSize%sUnit' % dim])
            self.setPixelSize(*pxlsiz)

            if meta.get('StructuredAnnotations'):
                sas = meta['StructuredAnnotations']['XMLAnnotation']
                if type(sas) == list:
                    for sa in sas: # list
                        kv = sa['Value']['OriginalMetadata']
                        self.metadata[kv['Key']] = kv['Value']
                elif type(sas) == dict:
                    kv = sas['Value']['OriginalMetadata']
                    self.metadata[kv['Key']] = kv['Value']
                
        elif self.fp.is_imagej:
            self.metadata = meta = self.fp.imagej_metadata
            if 'spacing' in meta:
                pz = meta['spacing']
                xr = p.tags['XResolution']
                px = xr.value[1]/xr.value[0]
                yr = p.tags['YResolution']
                py = yr.value[1]/yr.value[0]
                unit = meta['unit']
                pz = _convertUnit(pz, unit)
                self.setPixelSize(pz, py, px)
            else:
                self.setPixelSize(0.3, 0.1, 0.1)

            #if 'Info' in meta:
            #    for m in meta['Info'].split('\n')[13:]:
            #        mm = m.split(' = ')
            #        if len(mm) == 2:
            #            key, val = mm
            #            self.ex_metadata[key] = val
            temp_meta = copy.deepcopy(meta)
            for key, value in meta.items():
                if key in IMAGEJ_METADATA_TYPES:
                    self.ex_metadata[key] = value
                    if key in temp_meta:
                        del temp_meta[key]
            self.metadata = temp_meta

        elif self.fp.is_lsm:
            self.metadata = meta = self.fp.lsm_metadata
            pz = _convertUnit(meta['VoxelSizeZ'], 'm', 'micron')
            py = _convertUnit(meta['VoxelSizeY'], 'm', 'micron')
            px = _convertUnit(meta['VoxelSizeX'], 'm', 'micron')
            self.setPixelSize(pz, py, px)

        else:
            
            self.setPixelSize(0.3, 0.1, 0.1)


    def readChannelInfo(self, nw, waves):
        if self.fp.is_micromanager:
            # my code uses wavelength a lot, and therefore, string name is not accepted...
            #waves = self.metadata['ChNames']
            self.nw = nw
            self.wave = self.makeWaves()#N.arange(400, 700, 300//nw)[:nw]
        
        elif self.fp.is_ome:
            px = self.metadata['Image']['Pixels']
            for w in range(nw):
                channels = px['Channel']
                if type(channels) == list:
                    channel = channels[w]
                else:
                    channel = channels
                unit = channel.get('EmissionWavelengthUnit', 'nm')
                wave = channel.get('EmissionWavelength')
                if wave is not None:
                    waves[w] = _convertUnit(wave, unit, 'nm')
        elif self.fp.is_imagej and 'Info' in self.metadata:
            for m in self.metadata['Info'].split('\n')[13:]:
                    mm = m.split(' = ')
                    if len(mm) == 2:
                        key, val = mm
                        # reading wavelength of tif from DV format ...
                        if key.startswith('Wavelength') and key.endswith('nm)'):
                            channel = int(key.split(' ')[1]) - 1
                            if channel < nw:
                                waves[channel] = eval(val)
        elif self.fp.is_lsm:
            channel = self.metadata['ChannelColors']['Colors']
            color_code = N.array((650, 515, 450, 0), N.float32)
            #waves = []
            for w in range(nw):
                color = N.array(channel[w])
                if N.sum(color):
                    waves[w] = int(N.sum(color_code * color / N.sum(color)))
                else:
                    waves[w] = generalIO.WAVE_START - 50
        
        elif 'waves' in self.metadata:
            if isinstance(self.metadata['waves'], six.string_types):#type(self.metadata['waves']) in (int, float):
                waves = [eval(w) for w in self.metadata['waves'].split(',')]
            else:
                waves = [self.metadata['waves']]
            #else:
            #    waves = [eval(w) for w in self.metadata['waves'].split(',')]
        return waves

                                
    def seekSec(self, i=0):
        p = self.fp.pages[i]
        #byte_counts, offsets = p._byte_counts_offsets
        tifversion = tifffile.__version__.split('.')
        if int(tifversion[0]) == 0:
            offsets, byte_counts = p.offsets_bytecounts#_byte_counts_offsets
        else:
            offsets = p.dataoffsets

        self.handle.seek(offsets[0])
        
    def readSec(self, i=None):
        """
        return the section at the number i in the file
        if i is None: return current position (not fast though)
        """
        if i is None:
            i = self.tellSec() + 1 # handle go back to the beggining of the page after reading...

        #if 0:#self.fp.is_imagej or hasattr(self, 'arr'):
        #    return self.arr[int(i)]
        #else:
        if len(self.fp.pages) >= self.nsec:
            arr = self.fp.pages[int(i)].asarray()
            if arr.ndim == 3 and self.axes[0] in ('S', 'C', 'W'):# == 'SYX'
                arr = arr[self.axes_w]
            elif arr.ndim == 3 and self.axes[-1] in ('S', 'C', 'W'):# == 'SYX'
                arr = arr[...,self.axes_w]
        else: # only series 0 is used
            series = self.fp.series[0]
            byteorder = self.fp.byteorder + series.dtype.char
            ndata = tifffile.product(series.shape[-2:])
            dtype = N.dtype(byteorder)
            self.handle.seek(series.offset + (ndata * dtype.itemsize * i))

            parameters = inspect.signature(self.handle.read_array)
            if 'native' in parameters.parameters.keys():
                img = self.handle.read_array(byteorder, count=ndata, out=None, native=True)
            else:
                img = self.handle.read_array(byteorder, count=ndata, out=None)
            arr = img.reshape(self.shape)
        return arr


class Writer(generalIO.Writer):
    def __init__(self, fn, mode=None, style='imagej', software='multitifIO.py', metadata={}):
        """
        mode is 'wb' whatever the value is...
        style: 'imagej', 'ome', ..., ('RGB' does not work yet)
        """
        self.style = style #imagej = imagej
        self.software = software
        #self.ex_metadata = extra_metadata
        #self.extratags = ()
        self.init = False

        generalIO.Writer.__init__(self, fn, mode)
        self.metadata.update(metadata) #{}

        if self.style == 'RGB':
            self.axes += 'S'
            #self.setDim(dtype=N.uint8, imgSequence=1)


    def openFile(self):
        """
        open a file for reading
        """
        imagej = self.style == 'imagej'
        ome = self.style == 'ome'
        tifversion = tifffile.__version__.split('.')
        if int(tifversion[0]) == 0 and int(tifversion[1]) <= 14:
            self.fp = tifffile.TiffWriter(self.fn, software=self.software, imagej=imagej)#, ome=ome)#, bigtiff=not(imagej))
        elif (int(tifversion[0]) == 0 and int(tifversion[1]) == 15) or (int(tifversion[0]) == 2019 and int(tifversion[1])==7):
            self.fp = tifffile.TiffWriter(self.fn, imagej=imagej)
        else:
            self.fp = tifffile.TiffWriter(self.fn, imagej=imagej, ome=ome)#, bigtiff=not(imagej))

        self.handle = self.fp._fh
        self.dataOffset = None #self.handle.tell()

    def close(self):
        """
        closes the current file
        """
        tifversion = tifffile.__version__.split('.')
        if (int(tifversion[0]) == 2020 and int(tifversion[1]) >= 11) or int(tifversion[0]) > 2020:
            # it is necessary to overwrite description after seuqnentially add image sections
            if hasattr(self, 'nt') and hasattr(self, 'fp') and self.fp._storedshape:
                shape = (self.nt,self.nz,self.nw,self.ny,self.nx)
                if self.style == 'imagej':
                   # if 'Channels' in self.metadata:
                   #     self.metadata['channels'] = self.metadata.pop('Channels')
                    colormapped = self.fp._colormap is not None
                    isrgb = self.fp._storedshape[-1] in (3, 4)
                    #des = tifffile.tifffile.imagej_description(shape=shape, rgb=isrgb, colormaped=colormapped, **self.metadata)
                    des = tifffile.tifffile.imagej_description(shape, rgb=isrgb, colormaped=colormapped, **self.metadata)
                    #print('writing metaata', self.metadata)
                elif self.style == 'ome':
                    #self.metadata['DimensionOrder'] = 'XY'
                    if 'Channels' in self.metadata:
                        self.metadata['Channel'] = self.metadata.pop('Channels')
                    if self.fp._subifdslevel < 0:
                        datashape = self.makeShape(squeeze=(False))#True)
                        storedshape = (N.prod(shape[:3]), 1, 1, self.ny, self.nx, 1)
                        #axes = self.metadata['Pixels']['DimensionOrder'][::-1]
                        #axes = self.metadata['Pixels']['axes']
                       # axes = self.metadata['axes']
                       # print(self.metadata, datashape, axes)

                        if hasattr(self.fp._ome, 'addimage'): # older versions
                            self.fp._ome.addimage(
                                self.dtype,
                                datashape,
                                storedshape,
                              #  axes=axes,
                                **self.metadata
                                )
                        else:
                            self.fp._omexml.addimage(
                                self.dtype,
                                datashape,
                                storedshape,
                              #  axes=axes,
                                **self.metadata
                                )

                        # when this error is raised:
                        # OmeXmlError('metadata DimensionOrder does not match {axes!r}')
                        # then edit tifffile.py
                        # ax for ax in omedimorder if dimsizes[dimorder.index(ax)] >= 1
                        # change '>' to '>='
                        
                    if hasattr(self.fp._ome, 'addimage'): # older versions
                        des = self.fp._ome.tostring(declaration=True).encode()
                    else:
                        des = self.fp._omexml.tostring(declaration=True).encode()

                self.fp.overwrite_description(des)
        
        if hasattr(self, 'fp') and hasattr(self.fp, 'close'):
            self.fp.close()
        elif hasattr(self, 'fp'):
            del self.fp

    def doOnSetDim(self):
        # ImageJ's dimension order is always TZCYXS
        # since tifffile only accepts ascii, micron characters often used in ImageJ should be removed...20210216
        self.metadata = walk(self.metadata, replace)
        
        if self.style == 'imagej': 
            self.imgSequence = 1
            self.metadata.update(self._makeMetadata())
            datasize = self._secByteSize * self.nt * self.nw
            if datasize >= (2**32):
                raise ValueError('ImageJ format does not allow file size more than 4GB but your data has %.1f GB.' % (datasize/(10**9)))
        elif self.style == 'ome':
            self.metadata.update(self.makeOMEMetadata())
        else:
            self.metadata = self._makeMetadata() # remove the inherited metadata

        unit = 10**6
        self.res = [(int(p), unit) for p in 1/self.pxlsiz[-2:] * unit]

                    
        
    def writeRGBArr(self, arr, waxis=0, t=0, z=0):
        """
        waxis: axis of channel in 3D array
        """
        if self.axes[-1] in ('S', 'C', 'W') and waxis not in (3, -1):
            barr = N.empty((self.ny, self.nx, self.nw), dtype=arr.dtype)
            for w in range(self.nw):
                barr[...,w] = arr[w] # not sure how to do this?? usually waxis should be 0 (an index can only have as single ellipsis)
            arr = barr
        elif self.axes[0] in ('S', 'C', 'W') and waxis not in (0):
            barr = N.empty((self.nw, self.ny, self.nx), dtype=arr.dtype)
            for w in range(self.nw):
                barr[w] = arr[...,w]
            arr = barr

        self.writeArr(N.ascontiguousarray(arr), t=t, z=z)

        
    def writeSec(self, arr, i=None):
        tifversion = tifffile.__version__.split('.')
        
        if len(self.axes) == 3 and arr.ndim != 3:
            raise ValueError('array has to be 3 dimensions of "YXS"')

        if self.style == 'RGB':
            photometric = 'RGB'
        else:
            photometric = None
        
        if not self.init:
            self.doOnSetDim()

            if int(tifversion[0]) >= 2020:
                self._secByteSize = (self.ny*self.nx) * arr.itemsize
            else:
                test = N.zeros((self.ny, self.nx), self.dtype)
                self.dataOffset, self._secByteSize = self.fp.save(test, resolution=self.res, metadata=self.metadata, returnoffset=True)#, extratags=self.extratags)
                self.handle.seek(self.handle.tell() - self._secByteSize)

            self.init = True
        
        elif i is not None:
            self.seekSec(i)

        #print('in writesec walking', self.metadata)
        self.metadata = walk(self.metadata, replace)

        if int(tifversion[0]) >= 2020:
            offset, sec = self.fp.write(arr, resolution=self.res, metadata=self.metadata, returnoffset=True, software=self.software, photometric=photometric, contiguous=True)
        elif int(tifversion[0]) == 0 and int(tifversion[1]) <= 14:
            offset, sec = self.fp.save(arr, resolution=self.res, metadata=self.metadata, returnoffset=True, photometric=photometric)
        elif hasattr(self.fp, 'save'):#int(tifversion[0]) >= 2020:
            offset, sec = self.fp.save(arr, resolution=self.res, metadata=self.metadata, returnoffset=True, software=self.software, photometric=photometric, contiguous=True)
        else:
            offset, sec = self.fp.write(arr, resolution=self.res, metadata=self.metadata, returnoffset=True, software=self.software, photometric=photometric)

        if int(tifversion[0]) >= 2020 and not self.dataOffset:
            self.dataOffset = offset
 
    def _makeMetadata(self):
        """
        "Info" field does not work...
        Somebody tell me why
        """
        tifversion = tifffile.__version__.split('.')

        if int(tifversion[0]) >= 2020:
                    metadata = {
                        'images': self.nsec,
                        'channels': self.nw,
                        'slices': self.nz,
                        'frames': self.nt,
                        'hyperstack': True,
                        'loop': False,
                        #'mode': 'grayscale',
                        #'spacing': self.pxlsiz[0],
                        'unit': 'micron',
                        'waves': ','.join([str(wave) for wave in self.wave[:self.nw]])
            }
        else:
            metadata = {
                        'images': self.nsec,
                        'channels': self.nw,
                        'slices': self.nz,
                        'hyperstack': (self.ndim > 3 and (len(self.axes)==2 or self.nw == 1)) or (self.ndim > 4 and (len(self.axes)==3 and self.nw > 1)),
                        'unit': 'micron',
                        'loop': False,
                        'frames': self.nt,
                        # my field goes to "description"
                        'waves': ','.join([str(wave) for wave in self.wave[:self.nw]])
                        }
        if self.style == 'imagej':
            if int(tifversion[0]) == 0:
                metadata['ImageJ'] = '1.51h'
            metadata['mode'] = 'grayscale'
            metadata['spacing'] = self.pxlsiz[0]
        elif self.style == 'RGB':
            metadata['images'] = self.nz * self.nt




        if self.style == 'imagej':
            if 'Ranges' in self.ex_metadata:
                nw_range = len(self.ex_metadata['Ranges']) // 2
                if nw_range != self.nw:
                    del self.ex_metadata['Ranges']
            # 20210618 -> 20220805
           # if hasattr(self.fp, '_byteorder'):
           #     self.extratags = imagej_metadata_tags(self.ex_metadata, self.fp._byteorder)
           # else:
           #     self.extratags = imagej_metadata_tags(self.ex_metadata, self.fp.tiff.byteorder)

            
        return metadata

    def makeOMEMetadata(self):
        if self.nt == 1 and self.nw==1:
            self.imgSequence = 0
        elif self.nt == 1 and self.nz == 1:
            self.imgSequence = 1
        elif self.nw == 1 and self.nz == 1:
            self.imgSequence = 3
        elif self.nt == 1:
            if self.imgSequence == 0:
                self.imgSequence = 2
            elif self.imgSequence == 4:
                self.imgSequence = 1
        elif self.nw == 1:
            if self.imgSequence == 2:
                self.imgSequence = 0
            elif self.imgSeuqnce == 5:
                self.imgSeuqnce = 3
        elif self.nz == 1:
            if self.imgSequence == 1:
                self.imgSequence = 4
            elif self.imgSequence == 3:
                self.imgSequence = 5

        axes = self.makeDimensionStr(squeeze=False).replace('W', 'C')
        dimension = self.makeDimensionStr(squeeze=False).replace('W', 'C')[::-1]
        
        metadata = {
            #'Pixels': {
                    'axes': axes,
                    'Interleaved': False,
                    'Type': pixeltype_to_ome(self.dtype),
                    'DimensionOrder': dimension,
                    'SizeX': self.nx,
                    'SizeY': self.ny,
                    'SizeZ': self.nz,
                    'SizeC': self.nw,
                    'SizeT': self.nt,
                    'PhysicalSizeX': float(self.pxlsiz[-1]),
                    'PhysicalSizeY': float(self.pxlsiz[-2]),
                    'PhysicalSizeZ': float(self.pxlsiz[-3]),
                    'PhysicalSizeXUnit': u'\xb5'+'m',
                    'PhysicalSizeYUnit': u'\xb5'+'m',
                    'PhysicalSizeZUnit': u'\xb5'+'m',
                }#}
        channels = [{} for w in range(len(self.wave))]
        for w, wave in enumerate(self.wave):
            channels[w]['EmissionWavelength'] = wave
            channels[w]['EmissionWavelengthUnit'] = 'nm'
        #metadata['Pixels']['Channel']  = channels
        metadata['Channels'] = channels
                
        return metadata
    
pxltypes_dtype = {N.int8: 'int8',
                    N.int16: 'int16',
                    N.int32: 'int32',
                    N.uint8: 'uint8',
                    N.uint16: 'uint16',
                    N.uint32: 'uint32',
                    N.float32: 'float',
                    N.bool_: 'bit',
                    N.float64: 'double',
                    N.complex64: 'complex',
                    N.complex128: 'double complex'
                    }
#imgOrders = ['XYZTC',
#             'XYCZT',
#             'XYZCT',
#             'XYTZC',
 #            'XYCTZ',
 #            'XYTCZ']

def pixeltype_to_ome(dtype):
    if hasattr(dtype, 'type'):
        return pxltypes_dtype[dtype.type]
    else:
        return pxltypes_dtype[dtype]

def ome_to_dtype(pixeltype):
    keys = list(pxltypes_dtype.keys())
    for key in keys:
        if pxltypes_dtype[key] == pixeltype:
            return key
    raise ValueError('pixeltype %s was not found' % pixeltype)

#def imgSeq_to_ome(imgSequence):
#    return imgOrders[imgSequence]

def saveAs3DRGB(h, out=None, t=0, vcat5=True):
    if not out:
        import os
        out = os.path.splitext(h.fn)[0] + '_RGB_t%i.tif' % t

    nw = 3
    arr = N.empty((h.nz, h.ny, h.nx, nw), h.dtype)
    
    for w in range(min(h.nw, nw)):
        arr[...,w] = h.get3DArr(t=t, w=w)
    if h.nw < nw:
        arr[...,h.nw:] = 0

    with tifffile.TiffWriter(out) as tif:
        tif.vcat5 = vcat5
        tif.save(arr)

    #tifffile.imsave(out, data=arr)# )
    # Below tags can be added but not necessary...
    #, photometric='RGB', planarconfig='CONTIG', metadata={'images': h.nz, 'slices': h.nz, 'axes': 'ZYXS'})

    return out

def removeEmptyChannel(h, out=None):
    """
    return output filename, but if no channel was removed, the original filename is returned.
    """
    rmv = []
    for w in range(h.nw):
        a = h.get3DArr(w=w)
        if a.min() == 0 and a.max() == 0:
            rmv.append(w)

    if rmv:
        if not out:
            import os
            out = os.path.splitext(h.fn)[0] + 'rmv.tif'
        o = MultiTiffWriter(out)
        o.setFromReader(h)
        o.setDim(nw=h.nw-len(rmv))

        for t in range(h.nt):
            for wo, wi in enumerate(range(h.nw)):
                if wi not in rmv:
                    a = h.get3DArr(w=wi, t=t)
                    o.write3DArr(a, w=wo, t=t)
        return out
    else:
        return h.fn
        
    
def xml2dict(xml, sanitize=True, prefix=None):
    """Return XML as dict.

    >>> xml2dict('<?xml version="1.0" ?><root attr="name"><key>1</key></root>')
    {'root': {'key': 1, 'attr': 'name'}}

    """
    from collections import defaultdict  # delayed import
    from xml.etree import cElementTree as etree  # delayed import

    at = tx = ''
    if prefix:
        at, tx = prefix

    def etree2dict(t):
        # adapted from https://stackoverflow.com/a/10077069/453463
        key = t.tag
        if sanitize:
            key = key.rsplit('}', 1)[-1]
        d = {key: {} if t.attrib else None}
        children = list(t)
        if children:
            dd = defaultdict(list)
            for dc in map(etree2dict, children):
                for k, v in dc.items():
                    dd[k].append(astype(v))
            d = {key: {k: astype(v[0]) if len(v) == 1 else astype(v)
                       for k, v in dd.items()}}
        if t.attrib:
            d[key].update((at + k, astype(v)) for k, v in t.attrib.items())
        if t.text:
            text = t.text.strip()
            if children or t.attrib:
                if text:
                    d[key][tx + 'value'] = astype(text)
            else:
                d[key] = astype(text)
        return d

    return etree2dict(etree.fromstring(xml))

if READABLE_FORMATS:
    tifff.xml2dict = xml2dict


def astype(value):
    if isinstance(value, six.string_types) and (value[0].isdigit() or value[-1].isdigit()):
        if value.isdigit():
            return int(value)
        else:
            try:
                return float(value)
            except:
                try:
                    return tifff.asbool(value)
                except:
                    return value
    else:
        try:
            return tifff.asbool(value)
        except:
            return value

def testit(fn, outfn='testImageJ.tif'):
    r = Reader(fn)
                
    ww = Writer(outfn, imagej=True)
    ww.setFromReader(r)
    for t in range(r.nt):
        for w in range(r.nw):
            for z in range(r.nz):
                arr = r.getArr(t=t, w=w, z=z)
                ww.writeArr(arr, t=t, w=w, z=z)
    ww.close()
    rr = Reader(outfn)
    return rr.asarray()


# https://stackoverflow.com/questions/50258287/how-to-specify-colormap-when-saving-tiff-stack?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa

def imagej_metadata_tags(metadata, byteorder):
    """Return IJMetadata and IJMetadataByteCounts tags from metadata dict.

    The tags can be passed to the TiffWriter.save function as extratags.

    """
    header = [{'>': b'IJIJ', '<': b'JIJI'}[byteorder]]
    bytecounts = [0]
    body = []

    def writestring(data, byteorder):
        return data.encode('utf-16' + {'>': 'be', '<': 'le'}[byteorder])

    def writedoubles(data, byteorder):
        return struct.pack(byteorder+('d' * len(data)), *data)

    def writebytes(data, byteorder):
        return data.tobytes()

    metadata_types = (
        ('Info', b'info', 1, writestring),
        ('Labels', b'labl', None, writestring),
        ('Ranges', b'rang', 1, writedoubles),
        ('LUTs', b'luts', None, writebytes),
        ('Plot', b'plot', 1, writebytes),
        ('ROI', b'roi ', 1, writebytes),
        ('Overlays', b'over', None, writebytes))

    for key, mtype, count, func in metadata_types:
        if key not in metadata:
            continue
        if byteorder == '<':
            mtype = mtype[::-1]
        values = metadata[key]
        if count is None:
            count = len(values)
        else:
            values = [values]
        header.append(mtype + struct.pack(byteorder+'I', count))
        for value in values:
            data = func(value, byteorder)
            body.append(data)
            bytecounts.append(len(data))

    body = b''.join(body)
    header = b''.join(header)
    data = header + body
    bytecounts[0] = len(header)
    bytecounts = struct.pack(byteorder+('I' * len(bytecounts)), *bytecounts)
    return ((50839, 'B', len(data), data, True),
            (50838, 'I', len(bytecounts)//4, bytecounts, True))

def walk(node, func):
    """
    walk through a dictionary or list and do something by func
    return an updated dictionary or list
    """
    if isinstance(node, dict):
        node2 = {}
        for key, item in node.items():
            if isinstance(item, (list, dict)):
                item = walk(item, func)
            if isinstance(key, six.string_types):# and u'\xb5' in key:
                key = func(key)
            if isinstance(item, six.string_types):# and u'\xb5' in item:
                item = func(item)
            node2[key] = item
    elif isinstance(node, list):
        node2 = []
        for item in node:
            if isinstance(item, (list, dict)):
                item = walk(item, func)
            elif isinstance(item, six.string_types):# and u'\xb5' in item:
                item = func(item)
                #print(key, item)
            node2.append(item)
        
    return node2
    #self.metadata = walk(self.metadata)

def replace(st):
    """
    replace micron character to u
    and remove other possible inpurity for ascii
    """
    import unicodedata
    st = st.replace(u'\xb5', u'u')
    st = unicodedata.normalize('NFKD', st)
    st = st.encode('ascii', 'ignore').decode()
    #print('in replace', st)
    return st
