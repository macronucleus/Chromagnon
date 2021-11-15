
# at this moment, "series" data sets are not supported...

import os, copy, unicodedata, sys

try:
    from . import generalIO, mrcIO, multitifIO
except ImportError:
    import generalIO, mrcIO, multitifIO

try:
    from ..PriCommon import microscope, fntools, commonfuncs
except (ValueError, ImportError):    
    from PriCommon import microscope, fntools, commonfuncs
    
import numpy as N

URL='http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html'
#newURL='http://jdk.java.net/12/' # 20190829
HAS_JDK = False

try:
    ### -------- BioFormats --------------####
    import bioformats # reading bioformats is necessary to know if JDK is required or not (in __init__)
    
    if 'czi' not in bioformats.READABLE_FORMATS:
        _READABLE_FORMATS = list(bioformats.READABLE_FORMATS)
        _READABLE_FORMATS.append('czi')
        for fmts in mrcIO.READABLE_FORMATS + multitifIO.READABLE_FORMATS:
            if fmts in _READABLE_FORMATS:
                _READABLE_FORMATS.remove(fmts)
        
        _READABLE_FORMATS.sort()
        bioformats.READABLE_FORMATS = tuple(_READABLE_FORMATS)

    ## to use structured_annotations, I needed to change some code in omexml.py
    from .mybioformats import omexml as ome
    pxltypes_dtype = {N.int8: ome.PT_INT8,#'int8',
                    N.int16: ome.PT_INT16,#'int16',
                    N.int32: ome.PT_INT32,#'int32',
                    N.uint8: ome.PT_UINT8,#'uint8',
                    N.uint16: ome.PT_UINT16,#'uint16',
                    N.uint32: ome.PT_UINT32,#'uint32',
                    N.float32: ome.PT_FLOAT,#'float',
                    #N.float32: 'flaot32',
                    N.bool_: ome.PT_BIT,#'bit',
                    N.float64: ome.PT_DOUBLE,#'double',
                    N.complex64: 'complex',
                    N.complex128: 'double complex'
                    }

    # ----- check if JDK is ok ----------------
    import javabridge

    if sys.platform.startswith('linux'):
        jdk_dir = javabridge.locate.find_javahome()
    else:
        jdk_dir = javabridge.locate.find_jdk()
    if not jdk_dir or not os.path.isdir(jdk_dir):
        raise RuntimeError('JDK not found!, please install from %s' % URL)
    else:
        HAS_JDK = True
    
    # ------ now ready to go -----------------------------
    READABLE_FORMATS = bioformats.READABLE_FORMATS
    WRITABLE_FORMATS = ('dv', 'ome.tif')
        

    def _convertUnit(val, fromwhat='mm', towhat=u'\xb5'+'m'):
        factors = {'m': 0, 'mm': -3, u'\xb5'+'m': -6, 'um': -6, 'nm': -9}
        factor = factors[fromwhat] - factors[towhat] or 0
        return float(val) * 10 ** factor

        
    def pixeltype_to_bioformats(dtype):
        if hasattr(dtype, 'type'):
            return pxltypes_dtype[dtype.type]
        else:
            return pxltypes_dtype[dtype]

    def pixeltype_to_dtype(pixeltype):
        keys = list(pxltypes_dtype.keys())
        for key in keys:
            if pxltypes_dtype[key] == pixeltype:
                return key
        raise ValueError('pixeltype %s was not found' % pixeltype)

except:
    if not commonfuncs.main_is_frozen():
        import traceback, warnings
        #traceback.print_exc()
        errs = traceback.format_exc()
        warnings.warn(errs, UserWarning)
        

    READABLE_FORMATS = []
    WRITABLE_FORMATS = []
    # dummy fucs
    def pixeltype_to_bioformats(dtype):
        return N.int8
    def pixeltype_to_dtype(pixeltype):
        return 'int8'

    try:
    # HACK: the types of error may be different between OS versions (eg. Win8 and win10) when JDK is absent. The following should work universally.
    # bioformats.READABLE_FORMATS is required for imgio.__init__
        bioformats
    except NameError:
        try:
            import bioformats
        except ImportError: # bioformats is simply not installed
            class bioformats:
                READABLE_FORMATS = []
                WRITABLE_FORMATS = []
        except: # JDK is not installed
            class bioformats:
                READABLE_FORMATS = ['al3d', 'am', 'amiramesh', 'apl', 'arf', 'avi', 'bmp',
                        'c01', 'cfg', 'cxd', 'czi', 'dat', 'dcm', 'dicom', 'dm3',# 'dv',
                        'eps', 'epsi', 'fits', 'flex', 'fli', 'gel', 'gif', 'grey',
                        'hdr', 'html', 'hx', 'ics', 'ids', 'img', 'ims', 'ipl',
                        'ipm', 'ipw', 'jp2', 'jpeg', 'jpg', 'l2d', 'labels', 'lei',
                        'lif', 'liff', 'lim', 'mdb', 'mnc', 'mng', 'mov', # 'mrc','lsm',  
                        'mrw', 'mtb', 'naf', 'nd', 'nd2', 'nef', 'nhdr',
                        'nrrd', 'obsep', 'oib', 'oif', 'ome', 'pcx', #'ome.tiff'
                        'pgm', 'pic', 'pict', 'png', 'ps', 'psd', 'r3d', 'raw',
                        'scn', 'sdt', 'seq', 'sld', 'stk', 'svs', #'tif', 'tiff',
                        'tnb', 'txt', 'vws', 'xdce', 'xml', 'xv', 'xys', 'zvi']
                WRITABLE_FORMATS = ['avi', 'eps', 'epsi', 'ics', 'ids', 'jp2', 'jpeg', 'jpg',
                        'mov', 'ome', 'ome.tiff', 'png', 'ps', 'tif', 'tiff']

    try:
        javabridge
    except NameError:
        try:
            import javabridge
            if sys.platform.startswith('linux'):
                jdk_dir = javabridge.locate.find_javahome()
            else:
                jdk_dir = javabridge.locate.find_jdk()
            if not jdk_dir or not os.path.isdir(jdk_dir):
                raise RuntimeError('JDK not found!, please install from %s' % URL)
            else:
                HAS_JDK = True
        except (ImportError, RuntimeError, ValueError): # ValueError is a parent of javabridge.jutil.JVMNotFoundError
            pass
        except:
            if sys.platform.startswith('linux'): # if JDK is not found on linux, it throws exception
                pass
            else:
                raise
            
    
# constants
OMETIFF = ('ome.tif', 'ome.tiff')

WAVE_START = 400
#WAVE_END = 700
WAVE_STEP = 100

### -------- Javabridge --------------####
# javabridge.start_vm(class_path=bioformats.JARS)# cannot call at once
# use init_javabridge

## the programmer is responsible to kill java vm
# use uninit_javabridge

def vm_get_env():
    return javabridge.get_env()

def vm_get_vm():
    return javabridge.jutil._javabridge.get_vm()

def vm_is_active():
    vm = vm_get_vm()
    return vm.is_active()

def vm_get_thread():
    return javabridge.jutil.__start_thread

def vm_is_thread_alive():
    thre = vm_get_thread()
    if thre:
        return thre.is_alive()

def attach():
    if vm_is_active() and not vm_get_env():
        javabridge.jutil.attach()

def init_javabridge():#max_heap_size='4G'):
    if not vm_is_active():
        javabridge.start_vm(class_path=bioformats.JARS, run_headless=True)# max_heap_size=max_heap_size)
        suppressMsgs()
        #atexit.register(uninit_javabridge)

    else:
        attach()

def uninit_javabridge():
    try:
        javabridge
        if vm_is_active() and vm_is_thread_alive():
            javabridge.kill_vm()
    except NameError:
        return

def suppressMsgs():
    """
    supress too many messages from javabridge
    """
    # https://github.com/LeeKamentsky/python-javabridge/issues/37
    java_stack = javabridge.make_instance('java/io/ByteArrayOutputStream', "()V")
    java_stack_ps = javabridge.make_instance('java/io/PrintStream', 
                                   "(Ljava/io/OutputStream;)V", java_stack)
    javabridge.static_call('Ljava/lang/System;', "setErr", 
                  '(Ljava/io/PrintStream;)V', java_stack_ps)
    java_out = javabridge.make_instance('java/io/ByteArrayOutputStream', "()V")
    java_out_ps = javabridge.make_instance('java/io/PrintStream', 
                                   "(Ljava/io/OutputStream;)V", java_out)
    javabridge.static_call('Ljava/lang/System;', "setOut", 
              '(Ljava/io/PrintStream;)V', java_out_ps)
    javabridge.run_script('java.lang.System.out.println("This is java system.out!");')
    try:
        javabridge.run_script('this/raises/an/exception;')
    except javabridge.JavaException:
        print(('\n\nJava stdErr: ' + javabridge.to_string(java_stack)))


## ---- Common classes --------------
# cross platform
if not getattr(__builtins__, "WindowsError", None):
    class WindowsError(OSError): pass
        
# list class
class DynamicList(object):
    def __init__(self, iterable=[]):
        self._list = list(iterable)

    def _slice2list(self, slc):
        start = slc.start
        if not start:
            start = 0
        stop = slc.stop
        if not stop:
            stop = len(self._list)
        step = slc.step
        if not step:
            step = 1

        rlist = list(range(start, stop, abs(step)))
        if step < 0:
            rlist.reverse()
        return rlist
        
    def on_set_item(self, idx, value):
        pass

    def on_get_item(self, idx):
        pass

    def on_del_item(self, idx):
        pass

    def __setitem__(self, idx, value):
        self._list[idx] = value
        if type(idx) == slice:
            slist = self._slice2list(idx)
            for i in slist:
                self.on_set_item(i, value[i])
        else:
            self.on_set_item(idx, value)

    def __getitem__(self, idx):
        if type(idx) == slice:
            slist = self._slice2list(idx)
            return [self.on_get_item(i) for i in slist]
        else:
            x = self.on_get_item(idx)
            return x if x else self._list[idx]

    def __delitem__(self, idx):
        self.on_del_item(idx)
        self.list.__delitem__(idx)
        
    def __len__(self):
        return self._list.__len__()

    def __repr__(self):
        return repr(self._list)

    def __str__(self):
        return str(self._list)

    def __add__(self, y):
        for i, val in enumerate(y):
            self.on_set_item(len(self._list) + i, val)
        return self._list + list(y)

    def __contains__(self, y):
        return y in self._list

    def __iter__(self):
        return iter([self.__getitem__(idx) for idx in range(len(self._list))])

    def append(self, val):
        self._list.append(val)
        self.on_set_item(-1, val)

    def count(self):
        return self._list.count()

    def extend(self, y):
        self._list += list(y)
        for i, val in enumerate(y):
            on_set_item(i, val)

    def index(self, value):
        return self._list.index(value)

    def insert(self, idx, value):
        self._list.insert(idx, value)
        for idx, val in enumerate(self._list[idx:]):
            self.on_set_item(idx, value)

    def pop(self, idx=None):
        if idx is None:
            idx = len(self._list)-1
        self.on_del_item(idx)
        return self._list.pop(idx)

    def remove(self, val):
        idx = self.index(val)
        self.__delitem__(idx)

    def reverse(self):
        self._list.reverse()
        [self.on_set_item(i, val) for i, val in enumerate(self._list)]

class AbstractChannels(DynamicList):
    def __init__(self, iterable=[]):
        DynamicList.__init__(self, iterable)
        
    def setup(self, ome=None, node_name='Channel', key='EmissionWavelength'):
        self.ome = ome # OME_XML_Editor()
        self.node_name = node_name
        self.key = key

        self.populate()

    def populate(self):
        if self._list:
            for w, wave in enumerate(self._list):
                self.on_set_item(w, wave)

        else:
            nw = self.ome.pixels.get_SizeC()
            # guessing the excitation wavelength
            if self.node_name == 'Channel' and self.key == 'ExcitationWavelength' and self.ome.get('EmissionWavelength', node_name=self.node_name, idx=0):
                waves = [str(float(self.ome.get('EmissionWavelength', node_name=self.node_name, idx=w)) - 40) for w in range(nw)]
            else:
                # because 0 is not allowed for wavelength in Bioformats or ome.tiff?? WAVE_START and WAVE_STEP mimics visible wavelength.
                waves = generalIO.makeWaves(nw, WAVE_START, WAVE_STEP)
            if self.ome.pixels.get_channel_count() == nw:
                for w in range(nw):
                    unit = self.ome.get(self.key + 'Unit', self.node_name, w)
                    wave = self.ome.get(self.key, self.node_name, w)
                    if unit and wave:
                        wave = _convertUnit(eval(wave), unit, 'nm')
                        waves[w] = wave
            for wave in waves:
                self.append(wave)

    def on_set_item(self, idx, value):
        if idx < 0:
            idx += len(self._list)
        if idx >= self.ome.pixels.get_channel_count():
            self.ome.addChannel()
            self.ome.setChannel(self.key + 'Unit', 'nm')
        self.ome.set(self.node_name, self.key, value, idx)

    def on_get_item(self, idx):
        return eval(self.ome.get(self.key, self.node_name, idx))

    def on_del_item(self, idx):
        self.ome.removeChannel(idx)

class AbstractPixels(AbstractChannels):
    def __init__(self, iterable=[]):
        AbstractChannels.__init__(self, iterable)
        self.dim_str = ['Z', 'Y', 'X']

    def setup(self, ome=None, node_name='Pixels', key='PhysicalSize'):
        self.ome = ome
        self.node_name = node_name
        self.key = key
        if not self._list:
            self.populate()
    
    def populate(self):
        if self._list:
            for i, px in self._list:
                self.on_set_item(i, px)
        else:
            pxlsiz = N.ones((3,), N.float32) * 0.1

            for i, d in enumerate(('Z', 'Y', 'X')):
                psunit = self.ome.get('PhysicalSize%sUnit' % d, self.node_name) # um
                ps = self.ome.get('PhysicalSize%s' % d, self.node_name)
                if psunit and ps:
                    pxlsiz[i] = _convertUnit(float(ps), psunit)
            if N.all(pxlsiz == 1): # micromanager without calibration.
                pxlsiz[:] = 0.1

            for px in pxlsiz:
                self.append(px)

    def on_set_item(self, idx, value):
        """
        idx: 'Z' or 'X'
        """
        idx = self.dim_str[idx]
        key = self.key + idx.upper()
        self.ome.set(self.node_name, key, value)
        self.ome.setChannel(key + 'Unit', 'um')

    def on_get_item(self, idx):
        idx = self.dim_str[idx]
        key = self.key + idx.upper()
        ret = self.ome.get(key, self.node_name)
        if ret:
            return float(ret)
    

class AbstractReader(object):
    def __init__(self):
        self._closed = True
        self.ome = None # OME_XML_Editor()

        self.imgOrders = [ome.DO_XYZTC,
                    ome.DO_XYCZT,
                    ome.DO_XYZCT,
                    ome.DO_XYTZC,
                    ome.DO_XYCTZ,
                    ome.DO_XYTCZ]
        
    def closed(self):
        return self._closed

    @property
    def pixels(self):
        return self.omexml.image(0).Pixels

    @property
    def nz(self):
        return self.__dict__.get('_nz', self.pixels.get_SizeZ())
    @nz.setter
    def nz(self, value):
        self._nz = value
        self.pixels.set_SizeZ(self._nz)
    @nz.deleter
    def nz(self):
        del self._nz

    @property
    def nw(self):
        return self.__dict__.get('_nw', self.pixels.get_SizeC())
    @nw.setter
    def nw(self, value):
        self._nw = value
        self.pixels.set_SizeC(self._nw)
    @nw.deleter
    def nw(self):
        del self._nw

    @property
    def nt(self):
        return self.__dict__.get('_nt', self.pixels.get_SizeT())
    @nt.setter
    def nt(self, value):
        self._nt = value
        self.pixels.set_SizeT(self._nt)
    @nt.deleter
    def nt(self):
        del self._nt

    @property
    def ny(self):
        return self.__dict__.get('_ny', self.pixels.get_SizeY())#1)
    @ny.setter
    def ny(self, value):
        self._ny = value
        self.pixels.set_SizeY(self._ny)
    @ny.deleter
    def ny(self):
        del self._ny

    @property
    def nx(self):
        return self.__dict__.get('_nx', self.pixels.get_SizeX())#1)
    @nx.setter
    def nx(self, value):
        self._nx = value
        self.pixels.set_SizeX(self._nx)
    @nx.deleter
    def nx(self):
        del self._nx

    @property
    def dtype(self):
        return self.__dict__.get('_dtype', pixeltype_to_dtype(self.pixels.get_PixelType()))#N.uint16)
    @dtype.setter
    def dtype(self, value):
        self._dtype = value
        self.pixels.PixelType = pixeltype_to_bioformats(value)
    @dtype.deleter
    def dtype(self):
        del self._dtype

    @property
    def imgSequence(self):
        return self.__dict__.get('_imgSequence', self.imgOrders.index(self.pixels.get_DimensionOrder()))
    @imgSequence.setter
    def imgSequence(self, value):
        self._imgSequence = value
        self.pixels.DimensionOrder = self.imgOrders[self._imgSequence]
    @imgSequence.deleter
    def imgSequence(self):
        del self._imgSequence

    def setUpDynamicList(self, ome):
        # wavelength
        self.wave = AbstractChannels()
        self.wave.setup(ome=ome)
        self.exc = AbstractChannels()
        self.exc.setup(ome=ome, key='ExcitationWavelength')
        

        # pixel size
        self.pxlsiz = AbstractPixels()
        self.pxlsiz.setup(ome=ome)
        
    def setDim(self, nx=None, ny=None, nz=None, nt=None, nw=None, dtype=None, wave=[], imgSequence=None):
        """
        set dimensions of the current file
        """
        if nx:
            self.nx = int(nx)
        self.x = self.nx // 2
        if ny:
            self.ny = int(ny)
        self.y = self.ny // 2
        if nz:
            self.nz = int(nz)
        self.z = self.nz // 2

        if nw:
            self.nw = int(nw)
        if nt:
            self.nt = int(nt)

        if dtype:
            self.dtype = dtype

        if len(wave):
            if len(wave) > 1 and (wave[0] == wave[-1] or 0 in wave): # because 0 is not allowed for wavelength in Bioformats or ome.tiff?? WAVE_START and WAVE_STEP mimics visible wavelength.
                self.wave = AbstractChannels(generalIO.makeWaves(nw, WAVE_START, WAVE_STEP))
            else:
                self.wave = AbstractChannels(wave)
            self.wave.setup(self.ome)
        elif (hasattr(self, 'wave') and not len(self.wave)) and not len(wave) and self.nw:
            self.wave = AbstractChannels(generalIO.makeWaves(nw, WAVE_START, WAVE_STEP))
            self.wave.setup(self.ome)
        elif not (hasattr(self, 'wave')):
            self.wave = AbstractChannels(generalIO.makeWaves(nw, WAVE_START, WAVE_STEP))
            self.wave.setup(self.ome)

        if imgSequence is not None:
            self.imgSequence = imgSequence

        self.organize()
        
#### ============== Reader =========================

        
class BioformatsReader(AbstractReader, generalIO.GeneralReader):
    def __init__(self, fn):
        """
        fn: file name
        """
        self.imgseqs = [seq.replace('W', 'C') for seq in generalIO.IMGSEQ]
        # http://downloads.openmicroscopy.org/bio-formats-cpp/5.1.8/api/classome_1_1xml_1_1model_1_1enums_1_1PixelType.html

        AbstractReader.__init__(self)
        
        generalIO.GeneralReader.__init__(self, fn)
        # -> openFile() -> readHeader() -> organize() -> setSecSize() -> doOnSetDim()
        
    def close(self):
        """
        closes the current file
        """
        if not self._closed and hasattr(self, 'fp') and hasattr(self.fp, 'close'):
            try:
                self.fp.close()
            except AttributeError:
                del self.fp
        elif hasattr(self, 'fp'):
            del self.fp
        self._closed = True

    def closed(self):
        return self._closed
        
    def openFile(self):
        """
        open a file for reading
        """
        init_javabridge()

        self._closed = False

        if 'r' in self.mode:
            self.readHeader()

    def readHeader(self):
        """
        read metadata
        """
        self.dataOffset = 0
        self._secExtraByteSize = 0

        # ========== obtain reader ============
        # getting the right reader for tiff is not always done by bioformats...
        self.is_ometiff = False
                    
        if self.fn.lower().endswith(OMETIFF) or \
          not self.fn.lower().endswith(READABLE_FORMATS):
            self.fp = bioformats.ImageReader(self.fn, perform_init=False)
            self.handle = self.fp
            rdr = self.fp.rdr = self._readOMETiffHeader(self.fn.lower().endswith(OMETIFF))

        else:
            # reading meta data of standard file formats
            self.xml = bioformats.get_omexml_metadata(self.fn)
            self.fp = bioformats.ImageReader(self.fn)
            self.handle = self.fp
            rdr = self.fp.rdr

        # http://stackoverflow.com/questions/2365411/python-convert-unicode-to-ascii-without-errors
        if sys.version_info.major == 2:
            self.xml = self.xml.replace(u'\xb5', u'u') # micro -> "u"
            self.xml = unicodedata.normalize('NFKD', self.xml).encode('ascii', 'ignore')
        else:
            self.xml = self.xml.replace('&#181', '\xb5')#'u') # micro -> "u"
        self.omexml = ome.OMEXML(self.xml)

        # ========== setup attributes ===========
        self.ome = OME_XML_Editor(self.omexml)

        self.setUpDynamicList(self.ome)

        self.setDim()

        # ========== obtain other data ===========
        self.nseries = self.omexml.get_image_count()
        
        # obtain meta data other than Image
        # TODO: This must be done in a more structured way in the future
        if hasattr(self.omexml, 'root_node'):
            for node in self.omexml.root_node.getchildren():
                name = repr(node).split()[1].split('}')[1].replace("'", '')
                if name not in  ('Image', 'StructuredAnnotations'):
                    self.metadata[name] = dict(list(node.items()))
                    for cnode in node.getchildren():
                        cname = repr(cnode).split()[1].split('}')[1].replace("'", '')
                        self.metadata[name][cname] = dict(list(cnode.items()))


    def _readOMETiffHeader(self, omeformat=True):
        """
        get the right ImageReader directry from Java Class Wrapper
        return ImageReader object just in case to do more work
        """
        # https://github.com/CellProfiler/python-bioformats/issues/23
        # also refer to bioformats.formatreader.py and metadatatools.py

        clsOMEXMLService = javabridge.JClassWrapper('loci.formats.services.OMEXMLService')
        serviceFactory = javabridge.JClassWrapper('loci.common.services.ServiceFactory')()
        service = serviceFactory.getInstance(clsOMEXMLService.klass)
        metadata = service.createOMEXMLMetadata()
        level = bioformats.metadatatools.get_metadata_options(bioformats.metadatatools.ALL)

        if omeformat:
            # for OME-Tiff only
            self.is_ometiff = True
            rdr = javabridge.JClassWrapper('loci.formats.in.OMETiffReader')()
            rdr.setOriginalMetadataPopulated(True)
        else:
            # rather in general
            rdr = bioformats.formatreader.make_image_reader_class()()
            rdr.allowOpenToCheckType(True)
        
        rdr.setMetadataStore(metadata)
        rdr.setMetadataOptions(level)
        rdr.setId(self.fn)
        self.xml = service.getOMEXML(metadata)

        return rdr
    

    def getArr(self, t=0, z=0, w=0):
        if self.is_ometiff:
            xywh = None
        else:
            xywh = N.empty((4,), N.int16)
            xywh[:2] = self.roi_start[1:][::-1]
            xywh[2:] = self.roi_size[1:][::-1]
            xywh = tuple(xywh)

        # spectral imaging of Olympus microscope was not read correctly by Bioformats
        # here is the workaround
        if self.file.endswith('oib') and self.imgSequence == 2 and self.nw > 4:
            t, z, w = self.convertFileIdx(t, z, w)
        arr = self.fp.read(c=w, z=z, t=t, series=self.series, rescale=False, XYWH=xywh)[::-1]
        return arr#self.flipY(arr)

    # reading file
    def convertFileIdx(self, t=0, z=0, w=0, targetSeq=1):
        """
        return section_number in the file
        """
        if targetSeq == 0:
            i = w*self.nt*self.nz + t*self.nz + z
        elif targetSeq == 1:
            i = t*self.nz*self.nw + z*self.nw + w
        elif targetSeq == 2:
            i = t*self.nz*self.nw + w*self.nz + z
        elif targetSeq == 3:
            i = w*self.nz*self.nt + z*self.nt + t
        elif targetSeq == 4:
            i = z*self.nt*self.nw + t*self.nw + w
        elif targetSeq == 5:
            i = z*self.nw*self.nt + w*self.nt + t

        if self.imgSequence == 0:
            w = i // (self.nt * self.nz)
            ii = i // (w+1)
            t = ii // self.nz
            z = ii - ((t+1) * self.nz)
        elif self.imgSequence == 1:
            t = i // (self.nz * self.nw)
            ii = i // (t+1)
            z = ii // self.nw
            w = ii - (z * self.nw)
        elif self.imgSequence == 2:
            t = i // (self.nw * self.nz)
            ii = i // (t+1)
            w = ii // self.nz
            z = ii - (w * self.nz)
        elif self.imgSequence == 3:
            w = i // (self.nz * self.nt)
            ii = i // (w+1)
            z = ii // self.nt
            t = ii - ((z+1) * self.nt)
        elif self.imgSequence == 4:
            z = i // (self.nt * self.nw)
            ii = i // (z+1)
            t = ii // self.nw
            w = ii - ((t+1) * self.nw)
        elif self.imgSequence == 5:
            z = i // (self.nw * self.nt)
            ii = i // (w+1)
            w = ii // self.nt
            t = ii - ((w+1) * self.nt)
        return t, z, w

class BioformatsWriter(AbstractReader, generalIO.GeneralWriter):
    def __init__(self, fn):
        """
        fn: file name (must be 'ome.tiff' for OME-TIFF)
        """
        AbstractReader.__init__(self)
        generalIO.GeneralWriter.__init__(self, fn)
        # -> openFile()

    def openFile(self):
        if os.path.isfile(self.fn):
            # overwrite
            removed = False
            i = 0
            while not(removed):
                try:
                    os.remove(self.fn)
                    removed = True
                except OSError:
                    self.fn = fntools.nextFN(self.fn)
                    i += 1
                if i > 10:
                    raise RuntimeError('too many iteration to overwrite the last filename %s' % self.fn)
            old="""
            try:
                os.remove(self.fn)
            except OSError:
                raise RuntimeError, '%s is still open' % self.fn"""
        
        init_javabridge()
        self.fp = None
        self.handle = self.fp
        self._closed = False
        # edit omexml using OME_XML_Editor() or copy from original file
        self.omexml = ome.OMEXML()
        self.ome = OME_XML_Editor(self.omexml)
        self.setUpDynamicList(self.ome)


    def close(self):
        """
        closes the current file
        """
        if hasattr(self, 'fp') and hasattr(self.fp, 'close'):
            script = """
            writer.close();
            """
            if self.fp is not None:
                javabridge.run_script(script,
                                    dict(writer=self.fp))
            self._closed = True
            
            #self.fp.close() # this does not work...
            self.fp = None
        self._closed = True

    def closed(self):
        return self._closed

    def writeArr(self, arr, t=0, w=0, z=0):
        """
        write array
        """
        
        pxltype = self.omexml.image().Pixels.get_PixelType()

        pixel_buffer = bioformats.formatwriter.convert_pixels_to_buffer(arr[::-1], pxltype)
        index = self.findFileIdx(t=t, z=z, w=w)

        arr = self.flipY(arr)
        
        if self.fp is None:
            self.setup(arr)

        self.fp.saveBytes(index, pixel_buffer)
        
    def setFromReader(self, rdr):
        """
        read dimensions, imgSequence, dtype, pixelsize from a reader
        """
        if hasattr(rdr, 'omexml'):
            self.omexml = copy.deepcopy(rdr.omexml) # this does all
            self.ome = OME_XML_Editor(self.omexml)

            self.setUpDynamicList(self.ome)
            self.setDim()
        else:
            self.setPixelSize(*rdr.pxlsiz)
            if hasattr(rdr, 'roi_size'):
                nz, ny, nx = rdr.roi_size
            else:
                nz, ny, nx = rdr.nz, rdr.ny, rdr.nx
            self.setDim(nx, ny, nz, rdr.nt, rdr.nw, rdr.dtype, rdr.wave, rdr.imgSequence)
            #raise RuntimeError
        
        self.metadata = rdr.metadata

        if self.dtype in (N.uint16, N.uint8):
            self.imgSequence = 2 # in some reason, image order does not work for, at least, uint16 and uint8

    def setup(self, arr):
       # ome = bioformats.omexml
        # bioformats/formatwriter.py
        
        if arr.ndim == 3:
            p = self.omexml.image(0).Pixels
            p.SizeC = arr.shape[2]
            p.Channel(0).SamplesPerPixel = pixels.shape[2]
            self.omexml.structured_annotations.add_original_metadata(
                ome.OM_SAMPLES_PER_PIXEL, str(pixels.shape[2]))

        self.xml = self.omexml.to_xml()
        self.xml = self.xml.replace('&#181;', '\xb5')

        clsOMEXMLService = javabridge.JClassWrapper('loci.formats.services.OMEXMLService')
        serviceFactory = javabridge.JClassWrapper('loci.common.services.ServiceFactory')()
        service = serviceFactory.getInstance(clsOMEXMLService.klass)
        #print(self.xml)
        metadata = service.createOMEXMLMetadata(self.xml)

        if self.file.endswith(OMETIFF):
            self.fp = javabridge.JClassWrapper('loci.formats.out.OMETiffWriter')()
        else:
            self.fp = javabridge.JClassWrapper('loci.formats.ImageWriter')()
            
        self.fp.setMetadataRetrieve(metadata)

        self.fp.setId(self.fn)
        #if self.imgSequence in (0, 2, 3, 5):
        #    self.fp.setInterleaved(True)
        #else:
        self.fp.setInterleaved(False)


class OME_XML_Editor(object):
    """
    This is a class to edit or look inside the omexml
    """
    def __init__(self, omexml):
        self.ome = omexml
        self.pixels = self.ome.image().Pixels

    def qn(self, node_name):
        return ome.qn(self.ome.ns['ome'], node_name)
        
    def setRoot(self, key, val):
        self.ome.root_node.set(key, str(val))

    def setImage(self, key, val):
        self.ome.image().node.set(key, str(val))

    def setPixels(self, key, val):
        self.ome.image().Pixels.node.set(key, str(val))

    def setChannel(self, key, val, idx=0):
        self.ome.image().Pixels.Channel(idx).node.set(key, str(val))

    def addChannel(self):
        self.pixels.set_channel_count(self.pixels.get_channel_count() + 1)

    def removeChannel(self, idx=-1):
        channels = self.findnodes('Channel')
        self.pixels.remove(channels[idx])

    def addPlane(self):
        self.pixels.set_plane_count(self.pixels.get_plane_count() + 1)

    def removePlane(self, idx=-1):
        channels = self.findnodes('Plane')
        self.pixels.remove(channels[idx])
        # use px.set_pane_count(0) to remove all
        
    def findnode(self, node_name, idx=0):
        nodes = self.findnodes(node_name)
        if nodes:
            return nodes[idx]
        
    def findnodes(self, node_name):
        """
        """
        root = self.ome.root_node
        nodes = root.findall(self.qn(node_name))
        if not nodes:
            nodes = self._findnode(root, node_name)
        if nodes:
            return nodes
            
    def _findnode(self, node, node_name):
        for element in node:
            candidates = element.findall(self.qn(node_name))
            if candidates:
                return candidates
            else:
                candidates = self._findnode(element, node_name)
                if candidates:
                    return candidates
        
    def set(self, node_name, key, val, idx=0):
        node = self.findnode(node_name, idx)

        if node is not None:
            node.set(key, str(val))
        else:
            raise ValueError('The node name not found')

    def _get(self, node, key):
        for element in node:
            if key in list(element.keys()):
                return element.get(key)
            else:
                val = self._get(element, key)
                if val is not None:
                    return val
                
    def get(self, key, node_name='', idx=0):
        if node_name:
            node = self.findnode(node_name, idx)
            if node is None:
                raise ValueError('no such node found')
            return node.get(key)

        root = self.ome.root_node
        return self._get(root, key)

    def add_subelement(self, parent_name, tag, attrib={}, idx=0):
        """
        return the new element
        """
        if parent_name == 'root':
            parent = self.ome.root_node
        else:
            parent = self.findnode(parent_name, idx)
        return ET.SubElement(parent, self.qn(tag), attrib)
            
    def remove_subelement(self, parent_name, tag, idx):
        parent = self.findnode(parent_name, idx)
        parent.remove

    def add_structured_annotation(self, key, val):
        sa = self.ome.structured_annotations
        return sa.add_original_metadata(key, val)

    def get_structured_annotation(self, key):
        sa = self.ome.structured_annotations
        return sa.get_original_metadata_value(key)
