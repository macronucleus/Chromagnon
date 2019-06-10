import numpy as N

def RotateXY(xy, r, center=(0.0, 0.0)):
    """
    XY = (x, y)
    r = rotation in degrees (counter-clockwise; same as self.m_rot)

    any rotation introduced in mmviewer
    is cancelled to get the original coordinates if r = -self.m_rot

    returns an array([x,y])
    """
    if not r:
        return xy
    x = xy[0] - center[0]
    y = xy[1] - center[1]
    rd = N.math.radians(r)
    sin = N.sin(rd)
    cos = N.cos(rd)
    xr = x * cos - y * sin
    yr = x * sin + y * cos
    xyr = N.empty((2))
    xyr[0] = xr + center[0]
    xyr[1] = yr + center[1]
    return xyr

def rotate(a, r, center=None):
    """
    a:      2D coordinate(s) yx
    r:      degrees (counter-clockwise)
    center: center of rotation, if None, use (0,0)
    """
    if N.all(r == 0):#not r:
        return a
    a = N.asarray(a)
    if center is None:
        center = 0
    else:
        center = N.asarray(center)
        a = a[:] - center

    rd = N.radians(r)
    sin = N.sin(rd)
    cos = N.cos(rd)
    try:
        m = N.mat(((cos, sin), (-sin, cos)))
        ar = N.inner(a, m) + center
    except ValueError: # more than 2D
        y, x = a
        ar = N.array(((x * sin + y * cos), (x*cos-y*sin))) + center
    if ar.ndim > a.ndim: # windows numpy keeps matrix with larger ndim 
        ar = N.asarray(ar).reshape(a.shape)
    return ar
    
def zoom(a, mag, center=None):
    """
    a:      coordinate(s)
    mag:    magnification
    center: center of zoom, if None, use (0,0)
    """
    a = N.array(a)
    if center is None:
        center = 0
    else:
        center = N.asarray(center)
        a = a[:] - center
    a *= mag
    return a + center

def affine(a, r, mag, tyx=(0,0), center=(0,0)):
    """
    a:   2D coordinate(s) yx
    r:   degrees (counter-clockwise)
    mag: magnification
    tyx: translation
    
    center: center of rotation, if None, use (0,0)
    """
    rotRadian = N.pi / 180. * r
    cosTheta = N.cos(rotRadian)
    sinTheta = N.sin(rotRadian)
    bottom = N.array([sinTheta, cosTheta]) * mag
    affmatrix = N.array([ [cosTheta, -sinTheta],  bottom])
    return N.dot(affmatrix, N.array(a) - center) + tyx

def affine_index(indexarray, r, mag, tyx=(0,0), center=None):
    if center is None:
        center = N.array(indexarray.shape[-2:], N.float) / 2.
    
    rotRadian = N.pi / 180. * r
    cosTheta = N.cos(rotRadian)
    sinTheta = N.sin(rotRadian)

    try:
        if len(mag) != 2:
            raise ValueError('mag should be (y,x) or scaler')
    except TypeError:
        mag = [mag,mag]

    y = indexarray[0]
    x = indexarray[1]
    
    dx =  ((cosTheta * (x - center[1])) + (sinTheta * (y - center[0]))) / mag[1] + tyx[1] + center[1]
    dy =  ((-sinTheta * (x - center[1])) + (cosTheta * (y - center[0]))) / mag[0] + tyx[0] + center[0]

    return N.array((dy,dx))

def FlipXY(XY, XorY='Y', center=(0,0), shift=(0,0)):
    """
    XY = (x, y)
    XorY = 'X', 'Y' or 'XY'
    return flipped xy

    self.m_aspectRatio = -1 is XorY = 'Y'
    """
    if XorY == 'X': X, Y = 0, 1
    elif XorY == 'Y': X, Y = 1, 2
    elif XorY == 'XY': X, Y = 0, 2

    xy = N.array(XY) # creates copy!
    XYf = 2 * N.asarray(center) - xy - N.asarray(shift)
    xy[X:Y] = XYf[X:Y]

    return xy

def closeEnough(pos, pos0, r):
    """
    calculate Eucledian distance

    pos:  coordinate to be examine
    pos0: coordinate to be compared
    r:    diameter (scaller) or linear distance (same len as pos)
    
    return True if pos is within a circle/sphere of center pos0 diameter r
    """
    diff = N.abs(N.subtract(pos0, pos))
    try:
        if len(r) == diff.shape[-1]:
            if len(r) == len(diff[0]):
                return N.array([N.alltrue(d < r) for d in diff])
            else:
                r = N.average(r)
                raise TypeError('go to except')
        else:
            return N.alltrue(diff < r)
    except TypeError:
        dd = N.power(diff, 2)
        dd = N.sum(dd, axis=-1)
        diff = N.sqrt(dd)
        return diff < r

def euclideanDist(pos0, pos1):
    diff = N.abs(N.subtract(pos0, pos1))
    dd = N.power(diff, 2)
    dd = N.sum(dd, axis=-1)
    return N.sqrt(dd)

def angles2D(pos0, poses, degrees=False):
    """
    pos0: the starting corrdinate (y, x)
    poses: the ending coordinates [(y,x), (y,x),...]
    degrees: return angles in degrees otherwise, in radian
    """
    diff = N.subtract(poses, pos0)
    if diff.ndim == 1:
        rads = N.arctan2(*diff)
    else:
        rads = [N.arctan2(*dif) for dif in diff]
    if degrees:
        return N.degrees(rads)
    else:
        return rads
    

def centerSlice(shape, win, center=None):
    '''
    win:    scalar (in pixel or ratio < 1.0) or tuple (in pixel of any dimensions)
    center: if None, use center of shape

    if size is even, then the program selects "lower-left-corner" square
    The problem is when you have 1.99999.., then this does not become 2 but 1
    
    return list of slices
    '''
    shape = N.asarray(shape, N.float32)
    if center is None:
        center = shape / 2.
    ndim = len(shape)
    center = N.asarray(center, N.float32)
    try:
        nw = len(win)
        if nw < ndim:
            win = list(shape[:nw]) + list(win)
        else:
            win = win[-ndim:]
        win = N.asarray(win, N.float32)
    except TypeError:
        if win > 1: # pixel
            win = N.asarray((win,)*ndim, N.float32)
        else: # ratio
            win = shape * win

    win /= 2.
    center += .5000001

    start = center - win
    stop = center + win
    return [Ellipsis] + [slice(int(start[d]),int(stop[d])) for d in range(ndim)]

def LDRU(xy0, xy1):
    """
    returns xy0 (left-down) and xy1 (right-up) from any input of xy0, xy1
    """
    if xy0[0] > xy1[0]:
        oldx0 = xy0[0]
        xy0[0] = xy1[0]
        xy1[0] = oldx0
    if xy0[1] > xy1[1]:
        oldy0 = xy0[1]
        xy0[1] = xy1[1]
        xy1[1] = oldy0
    return xy0, xy1

def evenSquareMM(arr, min=(0,0), max=(1024,1024)):
    """
    arr: ((minX, minY),(maxX, maxY))
    min, max: (x,y)
    requied for lowPassGaussFilter2d
    """
    for i in range(len(arr[0])):
        if (arr[1][i] - arr[0][i]) % 2:
            if arr[0][i] != min[i]:
                arr[0][i] -= 1
            elif arr[1][i] != max[i]:
                arr[1][i] += 1
            elif arr[0][i] <= min[i] and arr[1][i] >= max[i]:
                arr[1][i] -= 1
    return arr

def evenShape(shape, minus=True):
    """
    trim shape to make a even shape
    this is for rfft

    returns array(even_shape)
    """
    shape = N.asarray(shape)
    if minus:
        return N.where(shape % 2, shape - 1, shape)
    else:
        return N.where(shape % 2, shape + 1, shape)        

def nearbyRegion(shape, pos, r=5, closest=True, adjustEdge=True):
    '''
    r: length of square, can be (z,y,x) or scaller (diameter)
    closest: use closest index using subpixel pos info, None is the same as N.floar(pos)
    adjustEdge: change slice so that slice does not include outside, if this is None and pos is too close to the edge, return None

    return slice of square surrounding pos (or None)
    image edge is not included, so resulting shape may not be rxr
    '''
    if not closest:
        pos = N.floor(pos)
    try:
        np = len(pos)
    except TypeError:
        pos = [pos]
        np = 1

    try:
        if len(shape) < np:
            raise ValueError('must be len(shape) >= len(pos)')
    except TypeError:
        if np == 1:
            shape = [shape]
        else:
            raise ValueError('must be len(shape) >= len(pos)')
    try:
        len(r)
        if len(r) < np:
            raise ValueError('must be len(r) >= len(pos)')
        r = N.round_(r)
    except (TypeError, ValueError):
        r = round(r)
        r = [r] * np
    sls = []
    for i, zyx in enumerate(pos[::-1]): # fill from lowest axis
        j = -(i+1)
        zyx = zyx + 0.5000001
        start = int(zyx - r[j] / 2.)# + 0.5000001)
        end = int(zyx + r[j] / 2.)# + 0.5000001)
        #print(start, end, r)
        if start < 0:
            if adjustEdge:
                start = 0
            else:
                return None
        if end > shape[j]:
            if adjustEdge:
                end = shape[j]
            else:
                return None

        sls.append(slice(start, end))
    sls.append(Ellipsis)
    return tuple(sls[::-1])

def edgeFromSlice(slicelist, start=True):
    if start:
        return [sl.start for sl in slicelist if isinstance(sl, slice)]
    else:
        return [sl.stop for sl in slicelist if isinstance(sl, slice)]

def lineIdx3D(pos0, pos1):
    """
    return idx (z,y,x) -- use it as img[idx[0], idx[1], idx[2]]
    """
    #poss = N.array((pos0, pos1))
    #pos0 = poss.min(0)
    #pos1 = poss.max(0)
    dzyx = pos1 - pos0

    l = N.sqrt(N.sum(dzyx**2))
    if l < 1: # no difference
        return N.zeros((dzyx.size,0), N.uint16)

    # yx
    cos = dzyx[-1] / l
    sin = dzyx[-2] / l
    xs = N.arange(pos0[-1], pos1[-1], cos) + 0.5
    ys = N.arange(pos0[-2], pos1[-2], sin) + 0.5
    size = xs.size or ys.size
    if not size and dzyx.size == 3: # no yx difference
        sin = dzyx[-3] / l
        zs = N.arange(pos0[-3], pos1[-3], sin) + 0.5
        zyx = N.zeros((dzyx.size, zs.size), N.uint16) # uint16 !
        zyx[0] = zs
        zyx[-2] = pos0[-2]
        zyx[-1] = pos0[-1]
        return zyx
    # yx has differences
    zyx = N.empty((dzyx.size, size), N.uint16) # uint16 !
    #zyx[-1] = xs
    #zyx[-2] = ys
    if not xs.size:
        zyx[-1] = pos0[-1]
    else:
        zyx[-1] = xs
    if not ys.size:
        zyx[-2] = pos0[-2]
    else:
        zyx[-2] = ys

    # z
    if dzyx.size == 3:
        sin = dzyx[-3] / l
        zs = N.arange(pos0[-3], pos1[-3], sin) + 0.5
        if zs.size:
            zyx[-3] = zs
        else:
            zyx[-3] = pos0[-3]
    return zyx

