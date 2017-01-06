#!/usr/bin/env priithon
__version__ = 0.1

from Priithon.all import Mrc, N
from PriCommon import mrcIO, imgGeo, imgManager
import os


EXT_CUTOUT='cut'

def _cutoutForAlign2(fn, py, outFn=''):
    """
    if not outFn, default with 'cut' extention
    resulting array is imgSequence=0 (t,w,z,y,x)
    return outFn
    """
    h = imgManager.ImageManager(fn)
    slc, shiftZYX, ZYX = makeSlice(h, py)

    # input
    arr = N.empty((h.nt, h.nw, h.nz, h.ny, h.nx), h.dtype)
    for t in range(h.nt):
        for w in range(h.nw):
            arr[t,w] = h.get3DArr(w=w, t=t)

    canvas = N.squeeze(arr[slc].astype(arr.dtype.type))
    newNum = (canvas.shape[-1], canvas.shape[-2], N.prod(canvas.shape[:-3]))
    if not outFn:
        outFn = '_'.join((h.filePath, EXT_CUTOUT))#arr.Mrc.path, EXT_CUTOUT))
    hdr = Mrc.makeHdrArray()
    Mrc.initHdrArrayFrom(hdr, h.hdr)#arr.Mrc.hdr)
    hdr.ImgSequence=2
    hdr.Num[:] = newNum
    mstart = [sl.start for sl in slc[::-1][:3] if isinstance(sl, slice)]
    hdr.mst[:len(mstart)] += mstart
    
    Mrc.save(canvas, outFn, ifExists='overwrite', hdr=hdr)
    return outFn

def _cutoutForAlignPriism(fn, py, outFn=''):
    """
    if not outFn, default with 'cut' extention
    resulting array is imgSequence=0 (t,w,z,y,x)
    return outFn
    """
    if not outFn:
        outFn = '_'.join((fn, EXT_CUTOUT))

    h = imgManager.ImageManager(fn)
    slc, shiftZYX, ZYX = makeSlice(h, py)
    return pc.CopyRegion(fn, outFn, zyxslc=slc)

if os.environ.has_key('IVE_BASE'):
    from PriCommon import priismCommands as pc
    cutoutForAlign = _cutoutForAlignPriism
else:
    cutoutForAlign = _cutoutForAlign2




def getShift(shift, ZYX, erosionZYX=0):
    """
    shift: zyxrmm
    return [zmin,zmax,ymin,ymax,xmin,xmax]
    """
    # erosion
    try:
        if len(erosionZYX) == 3:
            erosionZ = erosionZYX[0]
            erosionYX = erosionZYX[1:]
        elif len(erosionZYX) == 2:
            erosionZ = 0
            erosionYX = erosionZYX
        elif len(erosionZYX) == 1:
            erosionZ = 0
            erosionYX = erosionZYX[0]
    except TypeError: # scalar
        erosionZ = erosionZYX
        erosionYX = erosionZYX

    # magnification
    magZYX = N.ones((3,), N.float32)
    magZYX[3-len(shift[4:]):] = shift[4:]
    if len(shift[4:]) == 1:
        magZYX[1] = shift[4]
        
    # rotation
    r = shift[3]

    # target shape
    ZYX = N.asarray(ZYX, N.float32)
    ZYXm = ZYX * magZYX
    
    # Z
    z = N.where(shift[0] < 0, N.floor(shift[0]), N.ceil(shift[0]))
    ztop = ZYXm[0] + z
    nz = N.ceil(N.where(ztop > ZYX[0], ZYX[0], ztop))
    z += erosionZ
    nz -= erosionZ
    if z < 0:
        z = 0
    if nz < 0:
        nz = z+1
    zyx0 = N.ceil((ZYX - ZYXm) / 2.)
    #print zyx0
    #if zyx0[0] > 0:
    #    z -= zyx0[0]
    #    nz += zyx0[0]

    zs = N.array([z, nz])

    # YX
    #try:
    #    if len(erosionYX) != 2:
    #        raise ValueError, 'erosion is only applied to lateral dimension'
    #except TypeError:
    #    erosionYX = (erosionYX, erosionYX)

    yxShift = N.where(shift[1:3] < 0, N.floor(shift[1:3]), N.ceil(shift[1:3]))
    
    # rotate the magnified center
    xyzm = N.ceil(ZYXm[::-1]) / 2.
    xyr = imgGeo.RotateXY(xyzm[:-1], r)
    xyr -= xyzm[:-1]
    yx = xyr[::-1]
    leftYX = N.ceil(N.abs(yx))
    rightYX = -N.ceil(N.abs(yx))

    # then translate
    leftYXShift = (leftYX + yxShift) + zyx0[1:]
    
    leftYXShift = N.where(leftYXShift < 0, 0, leftYXShift)

    rightYXShift = (rightYX + yxShift) - zyx0[1:]
    YXmax = N.where(ZYXm[1:] > ZYX[1:], ZYXm[1:], ZYX[1:])
    rightYXShift = N.where(rightYXShift > 0, YXmax, rightYXShift + YXmax)  # deal with - idx

    rightYXShift = N.where(rightYXShift > ZYX[1:], ZYX[1:], rightYXShift)

    leftYXShift += erosionYX
    rightYXShift -= erosionYX

    # (z0,z1,y0,y1,x0,x1)
    tempZYX = N.array((zs[0], zs[1],
                       int(N.ceil(leftYXShift[0])), int(rightYXShift[0]),
                       int(N.ceil(leftYXShift[1])), int(rightYXShift[1])))
    return tempZYX

def showInViewer(vid, slc):
    from Priithon.all import Y
    Y.vgAddRect(vid, ((slc[2],slc[4]),(slc[3],slc[5])))



########################################################

if __name__ == '__main__':
    import optparse, glob

    usage = r""" %prog imgFile py [-O outputfile]"""

    p = optparse.OptionParser(usage=usage,
                              version='%prog' + ' %.2f' % __version__)

    p.add_option('--outFn', '-O', default=None, help='out put file name')

    options, args = p.parse_args()

    fns = []
    for fn in args:
        fns += glob.glob(os.path.expandvars(os.path.expanduser(fn)))
    fns = [fn for fn in fns if os.path.isfile(fn)]

    out = cutoutForAlign(*fns, **options.__dict__)

    print 'saved %s' % out
