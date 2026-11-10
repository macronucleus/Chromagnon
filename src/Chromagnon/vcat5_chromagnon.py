#!/usr/bin/env python

### vcat5_chromagnon.py ##############################################################
#
# This is a script to run Chromagnon as a plugin called from VCAT5
#
# VCAT5 and tifffile.py uses a different tag grammer (for 'SampleFormat').
# As a result, it was necessary to edit tifffile.py to disable writing the 'SampleFormat' tag
##################################################################################

# no GUI is required!!!
# no bioformats

#  prepare for __main__
if __name__ == '__main__':
    ## windows support for py2exe
    import multiprocessing
    multiprocessing.freeze_support()

    import warnings
    warnings.simplefilter('ignore')#filterwarnings('ignore')

# ------------- import modules
import sys, os, tempfile, shutil
import six
import numpy as N

from Priithon import imgio

## for packaging, here the relative import was impossible to run this script as __main__
try:
    if sys.version_info.major == 2:
        import aligner, cutoutAlign, alignfuncs as af, chromformat, version, threads
    elif sys.version_info.major >= 3:
        from .Chromagnon import aligner, cutoutAlign, alignfuncs as af, chromformat, version, threads
except ImportError: # run as __main__
    from Chromagnon import aligner, cutoutAlign, alignfuncs as af, chromformat, version, threads

#----------- Global constants
#C.CONFPATH = 'Chromagnon.conf'

LOCAL_CHOICE = ['None', 'Projection']


## command line behavior

if __name__ == '__main__':
    import argparse, glob

    description = r"""
       Chromagnon is an adaptive channel alignment program for fluorescnece microscope images.
       """
    usage = '%(prog)s target outfile -R reference [options]'

    p = argparse.ArgumentParser(description=description, usage=usage)
    p.add_argument('--version', '-v', action='version', version='%s' % version.version)

    p.add_argument('targets', nargs=2)
    p.add_argument('--reference', '-R')
    p.add_argument('--local', '-l', type=int, default=0)
    p.add_argument('--crop_margins', '-c', type=int, default=1)


    # extra parameters

    options = p.parse_args(sys.argv[1:])

    ref = options.reference
    fn, out = options.targets
    outdir = tempfile.gettempdir()
    suffix = aligner.IMG_SUFFIX
    ext = aligner.WRITABLE_FORMATS[0]

    with imgio.Reader(ref) as h:
        ref2 = imgio.multitifIO.removeEmptyChannel(h)
    
    if fn:
        with imgio.Reader(fn) as h:
            nts = [h.nt]
            fn2 = imgio.multitifIO.removeEmptyChannel(h)
            h.close()
    else:
        nts = []

    print(fn2, ref2)

    if options.local:
        options.local = LOCAL_CHOICE[1]

    parms = [options.crop_margins,
            outdir, #options.output_directory,
            options.local,
            None, #options.reference_wavelength,
            aligner.MAXITER_3D, #options.n3diter,
            '', #options.parm_suffix,
            suffix, #options.img_suffix,
            nts,
            ext, #options.img_format,
            int(af.MIN_PXLS_YXS[1]), # localMinWindow
            af.MAX_SHIFT, #options.maxShift,
            '', #options.microscope_calib]
             True,True] # dorot4time, doZ

    th = threads.ThreadWithExc(None, LOCAL_CHOICE, [ref2], [fn2], parms)
    th.start()
    th.join()

    outfn = os.path.splitext(os.path.basename(fn2))[0] + suffix + os.path.extsep + ext
    outfn = os.path.join(outdir, outfn)

    with imgio.Reader(outfn) as h:
        imgio.multitifIO.saveAs3DRGB(h, out)
    #shutil.move(outfn, out)

    if ref != ref2:
        os.remove(ref2)
    if fn != fn2 and os.path.isfile(fn2):
        os.remove(fn2)
    os.remove(outfn)
    
    print('done')

