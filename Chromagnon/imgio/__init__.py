from __future__ import print_function
import os, glob, sys
if sys.version_info.major == 3:
    from importlib import reload
import six
import numpy as N

if sys.version_info.major == 2:
    import generalIO, mrcIO, imgSeqIO, multitifIO, bioformatsIO
elif sys.version_info.major >= 3:
    try:
        from . import generalIO, mrcIO, imgSeqIO, multitifIO, bioformatsIO
    except ImportError:
        from imgio import generalIO, mrcIO, imgSeqIO, multitifIO, bioformatsIO
        
from .bioformatsIO import uninit_javabridge

READABLE_FORMATS = []
WRITABLE_FORMATS = []
_names = ['seq', 'tif', 'mrc', 'bio']
for module in [generalIO, imgSeqIO, multitifIO, mrcIO, bioformatsIO]:
    reload(module)
    READABLE_FORMATS += module.READABLE_FORMATS
    WRITABLE_FORMATS += module.WRITABLE_FORMATS
READABLE_FORMATS = tuple(sorted(list(set(READABLE_FORMATS))))
WRITABLE_FORMATS = tuple(sorted(list(set(WRITABLE_FORMATS))))

JDK_MSG = 'Reading your image format "%s" requires Java Development Kit (JDK).'
    
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
                   'bio': bioformatsIO.READABLE_FORMATS}
        klasses = {'seq': imgSeqIO.ImgSeqReader,
                   'tif': multitifIO.MultiTiffReader,
                   'mrc': mrcIO.MrcReader,
                   'bio': bioformatsIO.BioformatsReader}
    else: # write
        formats = {'seq': imgSeqIO.WRITABLE_FORMATS,
                   'tif': multitifIO.WRITABLE_FORMATS,
                   'mrc': mrcIO.WRITABLE_FORMATS,
                   'bio': bioformatsIO.WRITABLE_FORMATS}
        klasses = {'seq': imgSeqIO.ImgSeqWriter,
                   'tif': multitifIO.MultiTiffWriter,
                   'mrc': mrcIO.MrcWriter,
                   'bio': bioformatsIO.BioformatsWriter}

    ext = os.path.splitext(fn)[1].replace(os.path.extsep, '')

    ## --- JDK check----
    if ext in bioformatsIO.bioformats.READABLE_FORMATS and ext not in formats['bio'] and ext not in formats['seq']:
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
    h = Reader(fn)
    a = N.squeeze(h.asarray())
    h.close()
    return a

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
    for fn in fns:
        h = Reader(fn)
        if along == 't':
            nsecs += h.nt
        #h.close()

    o = Writer(out, h)
    o.setDim(nt=nsecs)

    t2 = 0
    for fn in fns:
        h = Reader(fn)
        for t in range(h.nt):
            for w in range(h.nw):
                a = h.get3DArr(t=t, w=w)
                o.write3DArr(a, t=t2+t, w=w)
        t2 += h.nt
        h.close()
    o.close()

    return out
