from __future__ import print_function
import os, glob, sys
if sys.version_info.major == 3:
    from importlib import reload
import six
import numpy as N

if sys.version_info.major == 2:
    import generalIO, mrcIO, imgIO, imgSeqIO, multitifIO, bioformatsIO, arrayIO, nd2io
elif sys.version_info.major >= 3:
    try:
        from . import generalIO, mrcIO, imgIO, imgSeqIO, multitifIO, bioformatsIO, arrayIO, nd2io
    except ImportError:
        from imgio import generalIO, mrcIO, imgIO, imgSeqIO, multitifIO, bioformatsIO, arrayIO, nd2io

uninit_javabridge = bioformatsIO.uninit_javabridge

READABLE_FORMATS = []
WRITABLE_FORMATS = []
_names = ['seq', 'tif', 'mrc', 'bio']
for module in [generalIO, imgIO, imgSeqIO, multitifIO, mrcIO, bioformatsIO, arrayIO, nd2io]:
    reload(module)
    READABLE_FORMATS += module.READABLE_FORMATS
    WRITABLE_FORMATS += module.WRITABLE_FORMATS
READABLE_FORMATS = tuple(sorted(list(set(READABLE_FORMATS))))
WRITABLE_FORMATS = tuple(sorted(list(set(WRITABLE_FORMATS))))

JDK_MSG = 'Reading/Writing your image format "%s" is not supported.'
if not bioformatsIO.HAS_JDK:
    JDK_MSG += ' Installing Java Development Kit (JDK) may help.'
    
def Reader(fn, *args, **kwds):
    """
    return a reader class instance
    args and kwds are passed to the reader class
    """
    return _switch(fn, read=True, *args, **kwds)

def Writer(fn, rdr=None, *args, **kwds):
    """
    return a writer class instance
    args and kwds are passed to the writer class
    """
    wtr = _switch(fn, read=False, *args, **kwds)
    if rdr:
        wtr.setFromReader(rdr)
    return wtr


def _switch(fn, read=True, *args, **kwds):
    if read:
        formats = {'seq': imgSeqIO.READABLE_FORMATS,
                   'tif': multitifIO.READABLE_FORMATS,
                   'mrc': mrcIO.READABLE_FORMATS,
                   'bio': bioformatsIO.READABLE_FORMATS,
                    'nd2': nd2io.READABLE_FORMATS}
        klasses = {'seq': imgSeqIO.ImgSeqReader,
                   'tif': multitifIO.MultiTiffReader,
                   'mrc': mrcIO.MrcReader,
                   'bio': bioformatsIO.BioformatsReader,
                   'arr': arrayIO.ArrayReader,
                    'nd2': nd2io.ND2Reader}
    else: # write
        formats = {'seq': imgSeqIO.WRITABLE_FORMATS,
                   'tif': multitifIO.WRITABLE_FORMATS,
                   'mrc': mrcIO.WRITABLE_FORMATS,
                   'bio': bioformatsIO.WRITABLE_FORMATS}
        klasses = {'seq': imgSeqIO.ImgSeqWriter,
                   'tif': multitifIO.MultiTiffWriter,
                   'mrc': mrcIO.MrcWriter,
                   'bio': bioformatsIO.BioformatsWriter}

    if isinstance(fn, six.string_types):
        ext = os.path.splitext(fn)[1].replace(os.path.extsep, '')
    elif hasattr(fn, 'shape'): # array
        return klasses['arr'](fn, *args, **kwds)
    else:
        raise ValueError('The input type %s is not understood' % type(fn))
        

    ## --- JDK check----
    _allfmt = formats['tif'] + formats['mrc'] + formats['seq'] + formats['bio']
    if ext not in _allfmt and ext in bioformatsIO.bioformats.READABLE_FORMATS:# and ext not in formats['bio'] and ext not in formats['seq']:
        raise ValueError(JDK_MSG % ext)
    #-------------
    
    if (not isinstance(fn, six.string_types) and hasattr(fn, '__iter__')) or (read and not os.path.isfile(fn)):
        if not isinstance(fn, six.string_types) and hasattr(fn, '__iter__'): # list of file
            fns = fn
        elif os.path.isdir(fn): # directory
            fns = [os.path.join(fn, f) for f in os.listdir(fn)]
        else: # common prefix
            fns = glob.glob(fn + '*')
            if not fns:
                raise ValueError('The input file name %s was not understood' % fn)

        fns = [ff for ff in fns if os.path.splitext(ff)[1].replace(os.path.extsep, '') in formats['seq']]
        if os.path.commonprefix(fns):
            return klasses['seq'](fns, *args, **kwds)
        else:
            raise ValueError('The directory does not seem to contain image series')

    # ome.tif is written by BioformatsWriter
    elif fn.endswith('ome.tif') and not read:
        tifversion = tifffile.__version__.split('.')
        if (int(tifversion[0]) == 2020 and int(tifversion[1]) >= 11) or int(tifversion[0]) > 2020:
            return klasses['tif'](fn, style='ome', *args, **kwds)
        else:
            return klasses['bio'](fn, *args, **kwds)
    
    # specific formats
    elif ext in formats['tif']:
        try:
            return klasses['tif'](fn, *args, **kwds)
        except generalIO.ImageIOError:
            print('Reading tif file failed, forwarding to bioformats')
            if 'nd2' in bioformatsIO.bioformats.READABLE_FORMATS and 'nd2' not in formats['bio'] and ext not in formats['seq']:
                raise ValueError(JDK_MSG % 'tif')
            try:
                return klasses['bio'](fn, *args, **kwds)
            except:
                raise ValueError('The input file %s was not readable' % fn)
    elif ext in nd2io.READABLE_FORMATS:
        return klasses['nd2'](fn, *args, **kwds)
    elif read and ext in imgIO.READABLE_FORMATS:
        return imgIO.load(fn)
    elif ext in formats['mrc']:
        return klasses['mrc'](fn, *args, **kwds)
    elif ext in formats['bio']:
        return klasses['bio'](fn, *args, **kwds)
    elif ext in formats['seq']:
        return klasses['seq'](fn, *args, **kwds) # meant to be a single slice
    else: # for myself, making any image files
        try:
            return klasses['mrc'](fn, *args, **kwds)
        except:
            raise ValueError('The input file name %s was not understood' % fn)

def load(fn):
    """
    return numpy array
    """
    if fn.endswith('.npy'):
        return N.load(fn)
    h = Reader(fn)
    if type(h) == N.ndarray:
        a = h
    else:
        a = h.arr_with_header() #N.squeeze(h.asarray())
        h.close()
    return a

def save(arr, outfn, dimorder='twzyx', wave=[], pzyx=[.1,.1,.1], metadata={}):
    """
    arr: numpy array
    outfn: output file name with extension (usually '.dv' or '.tif')
    
    return outputfilename
    """
    import re

    # check if the array is writable into the target file
    base, ext = os.path.splitext(outfn)
    if ext.replace('.', '') not in WRITABLE_FORMATS:
        raise ValueError('%s is not writable, please choose from %s' % (ext, WRITABLE_FORMATS))

    if arr.ndim > 3 and ext not in ('.dv', '.mrc', '.tif'):
        raise ValueError('%i dimension array is not compatible with %s format' % (arr.dim, ext))
    
    if N.iscomplexobj(arr) and ext not in ('.dv', '.mrc'):
        raise ValueError('The array is complex type, please use ".dv" format')

    # dtype check
    match = re.match(r"([a-z]+)([0-9]+)", arr.dtype.name, re.I)
    if match:
        dtypename, dtypenum = match.groups()
        dtypenum = int(dtypenum)
    else:
        dtypename = arr.dtype.name
        dtypenum = 1000
    
    if 'int' in dtypename and dtypenum > 16:
        if dtypename.startswith('u'):
            arr = arr.astype(N.uint16) # can be converted to 8 bit in the writer
        else:
            arr = arr.astype(N.int16)
    elif dtypename == 'float' and dtypenum > 32:
        arr = arr.astype(N.float32)
    elif dtypenum == 'complex' and dtypenum > 64:
        arr = arr.astype(N.complex64)

    # more than 5 dimension is saved in a tifffle
    if arr.ndim > 5:
        if ext != '.tif':
            raise ValueError('dimension of %i can only be saved in tif format' % arr.ndim)
        multitifIO.tifffile.imsave(outfn, arr, metadata={'wave': wave}.update(metadata))
        return outfn

    # save in conventional microscopy formats
    # dimension data
    kwd = {}
    for i, s in enumerate(arr.shape[::-1]):
        kwd['n'+dimorder[::-1][i]] = s
    for nd in ['nt', 'nw', 'nz', 'ny']:
        if nd not in kwd:
            kwd[nd] = 1
    arr = arr.reshape((1,) * (5-arr.ndim) + arr.shape)
        
    with Writer(outfn) as o:
        # header
        kwd['imgSequence'] = o.findImgSequence(dimorder[:-2])
        kwd['dtype'] = arr.dtype
        kwd['wave'] = wave
        
        o.setDim(**kwd)
        o.setPixelSize(*pzyx)
        if hasattr(o, 'metadata'):
            o.metadata.update(metadata)

        dstr = generalIO.IMGSEQ[kwd['imgSequence']]

        # start saving
        ind = [0,0,0]
        for t in range(kwd['nt']):
            ind[dstr.index('T')] = t
            for w in range(kwd['nw']):
                ind[dstr.index('W')] = w
                for z in range(kwd['nz']):
                    ind[dstr.index('Z')] = z
                    a = arr[tuple(ind)]
                    o.writeArr(a, t=t, w=w, z=z)
        
    return outfn
    
    
    

def copy(fn, out='test.dv'):
    """
    return Reader of the output file
    """
    h = Reader(fn)
    o = Writer(out, h)
    for t in range(h.nt):
        for w in range(h.nw):
            a = h.get3DArr(t=t, w=w)
            o.write3DArr(a, t=t, w=w)
    h.close()
    o.close()

    return Reader(out)


def merge(fns, out=None, along='t'):
    if not out:
        out = os.path.commonprefix(fns) + '_merge.dv'
    nsecs = 0
    waves = []
    for fn in fns:
        h = Reader(fn)
        if along == 't':
            nsecs += h.nt
        elif along == 'w':
            nsecs += h.nw
            waves += list(h.wave)
        elif along == 'z':
            nsecs += h.nz
        #h.close()
        
    o = Writer(out, h)
    if along == 't':
        o.setDim(nt=nsecs)
    elif along == 'w':
        o.setDim(nw=nsecs,wave=waves)
    elif along == 'z':
        o.setDim(nz=nsecs)

    d2 = 0
    for fn in fns:
        h = Reader(fn)
        for t in range(h.nt):
            for w in range(h.nw):
                a = h.get3DArr(t=t, w=w)
                if along == 't':
                    o.write3DArr(a, t=d2+t, w=w)
                elif along == 'w':
                    o.write3DArr(a, t=t, w=w+d2)
                elif along == 'z':
                    for z in range(h.nz):
                        o.write3DArr(a, t=t, w=w, z=z+d2)
        if along == 't':
            d2 += h.nt
        elif along == 'w':
            d2 += h.nw
        elif along == 'z':
            d2 += h.nz
        h.close()
    o.close()

    return out

def formatTWZYX(twzyxs, h, start=True):
    ret = []
    for dim, v in twzyxs:
        n = h.__getattribute__('n%s' % dim)
        if v is None and start:
            ret.append((dim, 0))
        if v is None and not start:
            ret.append((dim, n))
        elif v < 0:
            v = n + v
            ret.append((dim, v))
        elif v > n:
            raise ValueError('number of %s is only %i but you specified %i' % (dim.upper(), n, v))
        else:
            ret.append((dim, v))
    return ret

def copyRegion(fn, out=None, twzyx0=(0,0,0,0,0), twzyx1=(None,None,None,None,None), ifExists='overwrite'):
    """
    twzyx0: starting index (minus values accepcted)
    twzyx1: ending index (minus values accepcted)

    return output filename
    """
    dimstr = 'twzyx'
    twzyx0s = list(zip(dimstr, twzyx0))
    twzyx1s = list(zip(dimstr, twzyx1))
    with Reader(fn) as h:
        if not out:
            what0 = ''.join([s.lower() + str(v) for s,v in twzyx0s if v])
            what1 = ''.join([s.upper() + str(v) for s,v in twzyx1s if v is not None])
            whats = '_'.join((what0, what1))
            base, ext = os.path.splitext(fn)
            if ext not in WRITABLE_FORMATS:
                ext = '.dv'
            out = base + whats + ext
            if os.path.isfile(out) and ifExists != 'overwrite':
                raise ValueError('The output file name %s exists, please specify another output file name.' % os.path.basename(out))
            
        twzyx0s = formatTWZYX(twzyx0s, h, start=True)
        twzyx1s = formatTWZYX(twzyx1s, h, start=False)
        ts = range(twzyx0s[0][1], twzyx1s[0][1])
        ws = range(twzyx0s[1][1], twzyx1s[1][1])
        zs = range(twzyx0s[2][1], twzyx1s[2][1])
        ys = slice(twzyx0s[3][1], twzyx1s[3][1])
        xs = slice(twzyx0s[4][1], twzyx1s[4][1])

        if (ys.stop - ys.start) <= 0 or (xs.stop - xs.start) <= 0 or not (len(zs)) or not (len(ts)) or not (len(ws)):
            raise ValueError('The target dimension cannot be less than or equal to 0')

        if type(h) == mrcIO.MrcReader:
            hdr = mrcIO.makeHdrFromRdr(h)
            hdr.NumTimes = len(ts)
            hdr.NumWaves = len(ws)
            hdr.Num[2] = len(zs) * hdr.NumTimes * hdr.NumWaves
            hdr.Num[1] = ys.stop - ys.start
            hdr.Num[0] = xs.stop - xs.start
            waves = hdr.wave[ws]
            #print(ws, waves, hdr.wave)
            hdr.wave[:len(waves)] = waves
            o = Writer(out, hdr=hdr)
        else:
            o = Writer(out, h)
            o.setDim(nx=xs.stop - xs.start, ny=ys.stop - ys.start, nz=len(zs), nt=len(ts), nw=len(ws))
        
        for t0, t1 in enumerate(ts):
            for w0, w1 in enumerate(ws):
                for z0, z1 in enumerate(zs):
                    a = h.getArr(t=t1, w=w1, z=z1)[ys,xs]
                    o.writeArr(a, t=t0, w=w0, z=z0)
        o.close()

    return out

def swapZtoT(fn, out=None):
    if not out:
        base, ext = os.path.splitext(fn)
        out = base + '_swapZtoT' + ext

    with Reader(fn) as h:
        with Writer(out, h) as o:
            o.setDim(nz=h.nt, nt=h.nz)

            for w in range(h.nw):
                for t in range(h.nt):
                    for z in range(h.nz):
                        a = h.getArr(w=w, t=t, z=z)
                        o.writeArr(a, t=z, z=t)
    return out
        
