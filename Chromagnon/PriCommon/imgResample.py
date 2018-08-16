try:
    from ..Priithon.all import U, N
except ValueError:
    from Priithon.all import U, N

from . import ppro26 as ppro
NCPU = ppro.NCPU

import scipy.ndimage.interpolation as ndii

METHODS = {'0nearest': 0,
           '1bilinear': 1,
           '3cubic': 3,
           '6affine': 6,
           'b': 1, # bilinear
           's': 3, # spline
           'a': 6} # affine
# comparison of time to interpolate arr of shape (29,512,512) on stylonichia
# sb: 0.8
# s : 4.7
# ab: 4.0
# a : 7.9

ORDER=3

def trans3D(arr, tzyx=(0,0,0), r=0, mag=1, dzyx=(0,0,0), rzy=0, method='a', ncpu=NCPU):#, **splinekwds):
    order = METHODS.get(method, 3)
    if order == 1:
        func = trans3D_bilinear
    elif order <= 5:
        #kwds = {'order': order, 'prefilter': bool(order)}
        func = trans3D_spline
    elif order == 6:
        func = trans3D_affine
    else:
        raise ValueError('method not recognized')

    return func(arr, tzyx=tzyx, r=r, mag=mag, dzyx=dzyx, rzy=rzy, ncpu=ncpu)


## affine transform

## Using scipy.ndimage's affine_transform() to transform this wavelength; but there's a pitfall:
## the matrix and offset passed to affine_transform() actually defines the transform from output
## to input. Therefore, to do a input->output mapping of r_o= M(r_i+t-c)+c, we have to pass
## Inv(M) and  -Inv(M)c+c-t as the matrix and offset respectively.
## Note: affine_transform() can only do 2D transform.
## Note: rotation matrix rotates theta in clockwise; but here because we do [y, x], not [x, y],
## somehow it turns out right if one thinks of rot as counter-clockwise

def trans3D_affine(arr, tzyx=(0,0,0), r=0, mag=1, dzyx=(0,0,0), rzy=0, ncpu=NCPU, order=ORDER):#**kwds):
    """
    return array 
    """    
    dtype = arr.dtype.type
    arr = arr.astype(N.float32)
    
    ndim = arr.ndim
    if ndim == 2:
        arr = arr.reshape((1,)+arr.shape)
    elif ndim == 3:
        if len(tzyx) < ndim:
            tzyx = (0,)*(ndim-len(tzyx)) + tuple(tzyx)
        if len(dzyx) < ndim:
            dzyx = (0,)*(ndim-len(dzyx)) + tuple(dzyx)

    dzyx = N.asarray(dzyx)

    magz = 1
    try:
        if len(mag) == 3:
            magz = mag[0]
            mag = mag[1:]
    except TypeError:
        pass

    if ndim == 3 and (magz != 1 or tzyx[-3] or rzy):
        #print magz, arr.shape
        # because, mergins introduced after 2D transformation may interfere the result of this vertical transform, vertical axis was processed first, since rzy is 0 usually.
        arrT = arr.T # zyx -> xyz
        magzz = (1,magz)
        canvas = N.zeros_like(arrT)
        tzy = (0,tzyx[-3])
        dzy = (dzyx[-2], dzyx[-3])

        #if ncpu > 1 and mp:
        ret = ppro.pmap(_dothat, arrT, ncpu, tzy, rzy, magzz, dzy, order)
        for x, a in enumerate(ret):
            canvas[x] = a
        #else:
        #    for x, a in enumerate(arrT):
        #        canvas[x] = _dothat(a, tzy, rzy, magzz, dzy, order)

        arr = canvas.T
        #del arrT

    if N.any(tzyx[-2:]) or r or N.any(mag):
        #print ndim, arr.shape
        canvas = N.zeros_like(arr)
        if ndim == 3:# and ncpu > 1 and mp:
            # dividing XY into pieces did not work for rotation and magnification
            # here parallel processing is done section-wise since affine works only for 2D
            ret = ppro.pmap(_dothat, arr, ncpu, tzyx[-2:], r, mag, dzyx[-2:], order)
            for z, a in enumerate(ret):
                canvas[z] = a
        else:
            for z, a in enumerate(arr):
                canvas[z] = _dothat(a, tzyx[-2:], r, mag, dzyx[-2:], order)

        if ndim == 2:
            canvas = canvas[0]

        arr = canvas

    if dtype in (N.int, N.uint8, N.uint16, N.uint32):
        arr = N.where(arr < 0, 0, arr)
        
    return arr.astype(dtype)


def _dothat(arr2D, tyx, r, mag, dyx, order=ORDER):
    invmat = transformMatrix(r, mag)
    offset = getOffset(arr2D.shape, invmat, tyx[-2], tyx[-1], (dyx[-2], dyx[-1]))
    return affine_transform(arr2D, invmat, offset, order)

def transformMatrix(rot=0.0, mag=1.0):
    """
    retrn invmat
    """
    rotRadian = N.pi / 180. * rot
    cosTheta = N.cos(rotRadian)
    sinTheta = N.sin(rotRadian)
    affmatrix = N.array([ [cosTheta, sinTheta], [-sinTheta, cosTheta] ]) * mag
    invmat = N.linalg.inv(affmatrix)

    return invmat

def getOffset(shape, invmat, ty, tx, start=0):
    try:
        if len(start) == len(shape):
            yxCenter = [s/2. + start[i] for i, s in enumerate(shape)]
    except TypeError:
        yxCenter = [s/2. + start for s in shape]
    return -N.dot(invmat, yxCenter) + yxCenter -  [ty, tx]

def affine_transform(arr, invmat, offset=0.0, order=ORDER):
    return U.nd.affine_transform(arr, invmat, offset,
                               output=N.float32, cval=arr.min(), order=order)


# 
def trans3D_bilinear(a, tzyx=(0,0,0), r=0, mag=1, dzyx=(0,0,0), b=None, rzy=0, **kwds):
    """
    magyx: scalar or [y,x] or [y,x, direction in degrees]
    """
    a = a.copy()
    ndim = a.ndim
    if ndim == 2:
        a = a.reshape((1,)+a.shape)
        
    try:
        if len(magyx) == 3:
            mr = magyx[-1]
            magyx = magyx[:2]
        else:
            mr = 0
    except:
        mr = 0

    if b is None:
        b2d = N.empty_like(a[0])

    dzyx = N.asarray(dzyx)
    tzyx = N.asarray(tzyx)
    tzyx[-2:] += dzyx[-2:]

    magaxis = 1 # only this axis works
    magz = 1
    try:
        if len(mag) == 3:
            magz, magy, magx = mag
        elif len(mag) == 2:
            magy, magx = mag
        else:
            magy = magx = mag[0]
    except:
        magy = magx = mag
    mag = magy
    anismag = magx / magy

    for z, a2d in enumerate(a):
        if N.any(dzyx[-2:]) or mr:
            temp = N.ascontiguousarray(b2d)
            target = N.ascontiguousarray(a2d)
            #U.trans2d(target, temp, (-dyx[1], -dyx[0], -mr, 1, 0, 1))
            U.trans2d(target, temp, (-dzyx[-1], -dzyx[-2], -mr, 1, 0, 1))
        else:
            temp = N.ascontiguousarray(a2d)
            target = N.ascontiguousarray(b2d)

        if r or mag != 1 or anismag != 1:
            U.trans2d(temp, target, (0, 0, r, mag, magaxis, anismag))
        else:
            target[:] = temp[:]

        #if rzx: # is this correct?? havn't tried yet
        #    target = U.nd.rotate(target, rzx, axes=(0,2), order=1, prefilter=False)

        if N.any(tzyx[-2:]) or mr:#N.any(dyx) or mr:
            #U.trans2d(target, temp, (dyx[1], dyx[0], mr, 1, 0, 1))
            U.trans2d(target, temp, (tzyx[-1], tzyx[-2], mr, 1, 0, 1))
        else:
            temp[:] = target[:]
        a[z] = temp[:]

    if ndim == 2:
        a = a[0]
    elif ndim == 3 and (magz != 1 or tzyx[-3]):
        at = a.T # zyx -> xyz
        mag = 1#magz
        anismag = magz #magy / magz
        canvas = N.empty_like(at)
        target = b2d.T
        for x, a2d in enumerate(at):
            if dzyx[-3]:
                U.trans2d(a2d, target, (0, -dyzx[-3], 0, 1, 1, 1))
            else:
                target = a2d

            canvas[x] = U.trans2d(target, None, (tzyx[-3], 0, rzy, mag, magaxis, anismag))
        #canvas = canvas.T
        a = canvas.T

    return a

# 
def trans3D_bilinear(a, tzyx=(0,0,0), r=0, mag=1, dzyx=(0,0,0), rzy=0, mr=0, ncpu=1, **kwds):
    """
    magyx: scalar or [y,x] or [y,x, direction in degrees]
    """
    a = a.copy()
    ndim = a.ndim
    if ndim == 2:
        a = a.reshape((1,)+a.shape)


    #b2d = N.empty_like(a[0])

    #dzyx = N.asarray(dzyx)
    #tzyx = N.asarray(tzyx)
    #tzyx[-2:] += dzyx[-2:]

    # mag
    magaxis = 1 # only this axis works
    magz = 1
    try:
        if len(mag) == 3:
            magz, magy, magx = mag
        elif len(mag) == 2:
            magy, magx = mag
        else:
            magy = magx = mag[0]
    except:
        magy = magx = mag

    # vertical axis    
    if ndim == 3 and (magz != 1 or tzyx[-3]):
        #print 'vertical'
        at = a.T # zyx -> xyz
        mag = 1
        anismag = magz
        canvas = N.empty_like(at)
        old="""
        for x, a2d in enumerate(at):
            if dzyx[-3]:
                U.trans2d(a2d, target, (0, -dyzx[-3], 0, 1, 1, 1))
            else:
                target = a2d

            canvas[x] = U.trans2d(target, None, (tzyx[-3], 0, rzy, mag, magaxis, anismag))"""

        if ndim == 3:# and ncpu > 1 and mp:
            ret = ppro.pmap(_doBilinear2D, at, ncpu, (0,tzyx[-3]), rzy, mag, anismag, (0,dzyx[-3]))
            for z, a2d in enumerate(ret):
                canvas[z] = a2d
        else:
            target = N.empty_like(a.T[0])#N.ascontiguousarray(b2d.T)
        
            for z, a2d in enumerate(at):
                canvas[z] = _doBilinear2D(a2d, (0,tzyx[-3]), rzy, mag, anismag, (0,dzyx[-3]), b2d=target)

        a = canvas.T
        #return a

    # Horizontal axis
    mag = magy
    anismag = magx / magy

    oldcode="""
    for z, a2d in enumerate(a):
        if N.any(dzyx[-2:]) or mr:
            temp = N.ascontiguousarray(b2d)
            target = N.ascontiguousarray(a2d)
            U.trans2d(target, temp, (-dzyx[-1], -dzyx[-2], -mr, 1, 0, 1))
        else:
            temp = N.ascontiguousarray(a2d)
            target = N.ascontiguousarray(b2d)

        if r or mag != 1 or anismag != 1:
            U.trans2d(temp, target, (0, 0, r, mag, magaxis, anismag))
        else:
            target[:] = temp[:]

        if N.any(tzyx[-2:]) or mr:
            U.trans2d(target, temp, (tzyx[-1], tzyx[-2], mr, 1, 0, 1))
        else:
            temp[:] = target[:]
        a[z] = temp[:]"""
    
    if ndim == 3 and ncpu > 1 and mp:
        ret = ppro.pmap(_doBilinear2D, a, ncpu, tzyx[-2:], r, mag, anismag, dzyx[-2:], mr)
        for z, a2d in enumerate(ret):
            a[z] = a2d
    else:
        b2d = N.empty_like(a[0])
        for z, a2d in enumerate(a):
            a[z] = _doBilinear2D(a2d, tzyx[-2:], r, mag, anismag, dzyx[-2:], mr, b2d)

    if ndim == 2:
        a = a[0]


    return a

def _doBilinear2D(a2d, tyx=(0,0), r=0, mag=1, anismag=1, dyx=(0,0), mr=0, b2d=None):
    if b2d is None:
        b2d = N.empty_like(a2d)
    else:
        b2d = N.ascontiguousarray(b2d)
    a2d = a2d.copy() # otherwise, the following code will mess up the input

    if N.any(dyx[-2:]) or mr:
        temp = b2d
        target = a2d
        U.trans2d(target, temp, (dyx[-1], dyx[-2], mr, 1, 0, 1))
    else:
        temp = a2d
        target = b2d

    # rot mag first to make consistent with affine
    magaxis = 1 # only this axis works
    if r or mag != 1 or anismag != 1:
        U.trans2d(temp, target, (0, 0, r, mag, magaxis, anismag))
    else:
        target[:] = temp[:]

    # then translate
    tyx2 = N.array(tyx) # copy
    tyx2[-2:] -= dyx[-2:]
    if N.any(tyx2[-2:]) or mr:
        U.trans2d(target, temp, (tyx2[-1], tyx2[-2], -mr, 1, 0, 1))
    else:
        temp[:] = target[:]
    #a[z] = temp[:]
    return temp

def trans3D_spline(a, tzyx=(0,0,0), r=0, mag=1, dzyx=(0,0), rzy=0, mr=0, reshape=False, ncpu=1, **splinekwds):
    """
    mag: scalar_for_yx or [y,x] or [z,y,x]
    mr: rotational direction of yx-zoom in degrees
    ncpu: no usage
    """
    splinekwds['prefilter'] = splinekwds.get('prefilter', True)
    splinekwds['order'] = splinekwds.get('order', 3)
    
    ndim = a.ndim
    shape = N.array(a.shape, N.float32)
    tzyx = N.asarray(tzyx, N.float32)
    
    # rotation axis
    if ndim == 3:
        axes = (1,2)
    else:
        axes = (1,0)

    # magnification
    try:
        if len(mag) == 1: # same as scalar
            mag = [1] * (ndim-2) + list(mag) * 2
        else:
            mag = [1] * (ndim-2) * (3-len(mag)) + list(mag)
    except: # scalar -> convert to yx mag only
        mag = [1] * (ndim-2) + ([mag] * ndim)[:2]
    mag = N.asarray(mag)

    try:
        dzyx = N.array([0] * (ndim-2) * (3-len(dzyx)) + list(dzyx))
    except: # scalar
        pass

    if mr:
        a = U.nd.rotate(a, mr, axes=axes, reshape=reshape, **splinekwds)
        splinekwds['prefilter'] = False
        
    if N.any(dzyx):
        a = U.nd.shift(a, -dzyx, **splinekwds)
        splinekwds['prefilter'] = False

    if r:
        a = U.nd.rotate(a, -r, axes=axes, reshape=reshape, **splinekwds)
        splinekwds['prefilter'] = False

    if N.any(mag != 1):
        a = U.nd.zoom(a, zoom=mag, **splinekwds)
        splinekwds['prefilter'] = False

        if not reshape:
            dif = (shape - N.array(a.shape, N.float32)) / 2.
            mod = N.ceil(N.mod(dif, 1))
            tzyx[-ndim:] -= (mod / 2.)
        
    if rzy and ndim >= 3: # is this correct?? havn't tried yet
        a = U.nd.rotate(a, -rzy, axes=(0,1), reshape=reshape, **splinekwds)

    if N.any(dzyx):
        a = U.nd.shift(a, dzyx, **splinekwds)

    if mr:
        a = U.nd.rotate(a, -mr, axes=axes, reshape=reshape, **splinekwds)

    if reshape:
        a = U.nd.shift(a, tzyx[-ndim:], **splinekwds)
    else:
        tzyx0 = N.where(mag >= 1, tzyx[-ndim:], 0)
        if N.any(tzyx0[-ndim:]):
            a = U.nd.shift(a, tzyx0[-ndim:], **splinekwds)

    if N.any(mag != 1) and not reshape:
        a = keepShape(a, shape, (dif, mod))
        old="""
        canvas = N.zeros(shape, a.dtype.type)

        #dif = (shape - N.array(a.shape, N.float32)) / 2
        #mod = N.ceil(N.mod(dif, 1))
        dif = N.where(dif > 0, N.ceil(dif), N.floor(dif))

        # smaller
        aoff = N.where(dif < 0, 0, dif)
        aslc = [slice(dp, shape[i]-dp+mod[i]) for i, dp in enumerate(aoff)]

        # larger
        coff = N.where(dif > 0, 0, -dif)
        cslc = [slice(dp, a.shape[i]-dp+mod[i]) for i, dp in enumerate(coff)]

        canvas[aslc] = a[cslc]
        a = canvas"""

    if not reshape:
        tzyx0 = N.where(mag < 1, tzyx[-ndim:], 0)
        if N.any(mag != 1):
            tzyx0[-ndim:] -= (mod / 2.)
        if N.any(tzyx0[-ndim:]):
            a = U.nd.shift(a, tzyx0[-ndim:], **splinekwds)
        
    return a

def keepShape(a, shape, difmod=None):
    canvas = N.zeros(shape, a.dtype.type)

    if difmod is None:
        dif = (shape - N.array(a.shape, N.float32)) / 2.
        mod = N.ceil(N.mod(dif, 1))
    else:
        dif, mod = difmod
    dif = N.where(dif > 0, N.ceil(dif), N.floor(dif))

    # smaller
    aoff = N.where(dif < 0, 0, dif)
    aslc = [slice(dp, shape[i]-dp+mod[i]) for i, dp in enumerate(aoff)]

    # larger
    coff = N.where(dif > 0, 0, -dif)
    cslc = [slice(dp, a.shape[i]-dp+mod[i]) for i, dp in enumerate(coff)]

    canvas[aslc] = a[cslc]

    if difmod is None:
        return canvas, mod
    else:
        return canvas

# multiprocessing funcs
def chopYX(shapeYX, ncpu=8):
    """
    return axis, YXmmlist
    """
    n, _1, _2, axis = U.findMax(shapeYX)
    n0 = n // ncpu
    mms = []
    pixel = 0
    for cpu in range(ncpu):
        mms += [[pixel, pixel + n0]]
        pixel += n0
    mms[-1][-1] = n
    return axis, mms

def splitImage(a, ncpu=8, mergin=10):
    axis, regions = chopYX(N.array(a.shape[-2:]), ncpu)
    dzyx = []
    arrs = []
    slc = [slice(None) for d in range(a.ndim)]
    axis = axis + (a.ndim-2)
    for i, region in enumerate(regions):
        if i:
            start = region[0] - mergin
        else:
            start = region[0]
        if i < (len(regions) -1):
            stop = region[1] + mergin
        else:
            stop = region[1]
        slc[axis] = slice(start, stop)
        arrs.append(a[slc])
        dd = [0 for i in range(a.ndim)]
        dd[axis] = -region[0]
        dzyx.append(dd)
    return arrs, axis, dzyx

def stichImage(arrs, axis, mergin=10):
    a = arrs[0]
    slc = [slice(None) for d in range(a.ndim)]
    slc[axis] = slice(a.shape[axis]-mergin)

    brrs = [a[slc]]
    for i, arr in enumerate(arrs[1:]):
        start = mergin
        if i < (len(arrs) -2):
            stop = arr.shape[axis] - mergin
        else:
            stop = None
        slc[axis] = slice(start, stop)
        brrs.append(arr[slc])
    return N.concatenate(brrs, axis=axis)

# ------ non linear functions ------

def remap(img, mapy, mapx, interp=2):
    """
    transform image using coordinate x,y

    Interpolation method:
    0 = CV_INTER_NN nearest-neigbor interpolation
    1 = CV_INTER_LINEAR bilinear interpolation (used by default)
    2 = CV_INTER_CUBIC bicubic interpolation
    3 = CV_INTER_AREA resampling using pixel area relation. It is the preferred method for image decimation that gives moire-free results. In terms of zooming it is similar to the CV_INTER_NN method

    return resulting array
    """
    des = N.zeros_like(img)

    # cv.fromarray: array can be 2D or 3D only
    if cv2.__version__.startswith('2'):
        cimg = cv.fromarray(img)
        cdes = cv.fromarray(des)

        cmapx = cv.fromarray(mapx.astype(N.float32))
        cmapy = cv.fromarray(mapy.astype(N.float32))
        
        cv.Remap(cimg, cdes, cmapx, cmapy, flags=interp+cv.CV_WARP_FILL_OUTLIERS)
    else:
        cimg = img
        #cdes = des
        cmapx = mapx.astype(N.float32)
        cmapy = mapy.astype(N.float32)

        cdes = cv2.remap(cimg, cmapx, cmapy, interp)

    return N.asarray(cdes)

def remap(img, mapy, mapx, order=ORDER):
    """
    transform image using coordinate x,y
    return resulting array
    """
    return ndii.map_coordinates(img, [mapy, mapx], order=order)

def logpolar_cv(img, center=None, mag=1):
    des = N.zeros_like(img)
    if center is None:
        center = N.divide(img.shape, 2)

    # cv.fromarray: array can be 2D or 3D only
    cimg = cv.fromarray(img)
    cdes = cv.fromarray(des)

    cv.LogPolar(cimg, cdes, tuple(center), mag)#, cv.CV_WARP_FILL_OUTLIERS)

    return N.array(cdes)


# http://www.lfd.uci.edu/~gohlke/code/imreg.py.html

# Copyright (c) 2011-2014, Christoph Gohlke
# Copyright (c) 2011-2014, The Regents of the University of California
# Produced at the Laboratory for Fluorescence Dynamics
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of the copyright holders nor the names of any
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

def logpolar(image, center=None, angles=None, radii=None):
    """Return log-polar transformed image and log base."""
    shape = image.shape
    if center is None:
        center = shape[0] / 2, shape[1] / 2
    if angles is None:
        angles = shape[0]
    if radii is None:
        radii = shape[1]
    theta = N.zeros((angles, radii), dtype=N.float64)
    theta.T[:] = -N.linspace(0, N.pi, angles, endpoint=False)
    #d = radii
    d = N.hypot(shape[0]-center[0], shape[1]-center[1])
    log_base = 10.0 ** (N.log10(d) / (radii))
    radius = N.empty_like(theta)
    radius[:] = N.power(log_base, N.arange(radii,
                                                   dtype=N.float64)) - 1.0
    x = radius * N.sin(theta) + center[0]
    y = radius * N.cos(theta) + center[1]
    output = N.zeros_like(x)
    ndii.map_coordinates(image, [x, y], output=output)
    return output, log_base

## polar transform

## from
# http://stackoverflow.com/questions/9924135/fast-cartesian-to-polar-to-cartesian-in-python
import numpy as np

def polar2cart2D(r, theta, center):

    y = r  * np.sin(theta) + center[0]
    x = r  * np.cos(theta) + center[1]
    return y, x# x, y

def img2polar2D(img, center, final_radius=None, initial_radius = None, phase_width = 360, return_idx=False):
    """
    img: array
    center: coordinate y, x
    final_radius: ending radius
    initial_radius: starting radius
    phase_width: npixles / circle
    return_idx: return transformation coordinates (y,x)
    """
    if img.ndim > 2 or len(center) > 2:
        raise ValueError('this function only support 2D, you entered %i-dim array and %i-dim center coordinate' % (img.ndim, len(center)))
    
    if initial_radius is None:
        initial_radius = 0

    if final_radius is None:
        rad0 = N.ceil(N.array(img.shape) - center)
        final_radius = min((int(min(rad0)), int(min(N.ceil(center)))))

    if phase_width is None:
        phase_width = N.sum(img.shape[-2:]) * 2

    theta , R = np.meshgrid(np.linspace(0, 2*np.pi, phase_width), 
                            np.arange(initial_radius, final_radius))

    Ycart, Xcart = polar2cart2D(R, theta, center)

    Ycart = N.where(Ycart >= img.shape[0], img.shape[0]-1, Ycart)
    Xcart = N.where(Xcart >= img.shape[1], img.shape[1]-1, Xcart)
    
    Ycart = Ycart.astype(int)
    Xcart = Xcart.astype(int)


    polar_img = img[Ycart,Xcart]
    polar_img = np.reshape(polar_img,(final_radius-initial_radius,phase_width))

    if return_idx:
        return polar_img, Ycart, Xcart
    else:
        return polar_img

