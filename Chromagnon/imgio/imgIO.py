import sys
import numpy as N
backend = None
try:
    #raise ImportError
    from PIL import Image
    backend = 'PIL'
    WRITABLE_FORMATS = ('bmp', 'eps', 'gif', 'icns', 'ico', 'im', 'jpg', 'jpeg', 'jpeg2000', 'msp', 'pcx', 'png', 'ppm', 'sgi', 'spider', 'tif', 'webp', 'xbm')
    READABLE_FORMATS = WRITABLE_FORMATS + ('cur', 'dcx', 'dds', 'fli', 'flc', 'fpx', 'ftex', 'gbr', 'gd', 'imt', 'iptc', 'naa', 'mcidas', 'mic', 'mpo', 'pcd', 'pixar', 'psd', 'tga', 'wal', 'xpm')
    WRITABLE_FORMATS += ('palm', 'pdf', 'xv')
except ImportError:
    try:
        import wx
        backend = 'wx'
        wcs = wx.Image.GetImageExtWildcard()
        wcs = wcs.split('|')[0][1:-1]
        wcs = wcs.split(';')
        READABLE_FORMATS = WRITABLE_FORMATS = tuple([s.replace('*.', '') for s in wcs])
        # 16-bit tif cannot be read by wxpython
        try:
            from . import multitifIO
        except ImportError:
            import multitifIO
    except ImportError:
        READABLE_FORMATS = WRITABLE_FORMATS = ()

###---------- sequence of images -----------###
def getHandle(fn):
    if backend == 'PIL':
        fp = Image.open(fn)
    elif backend == 'wx' and not fn.endswith(('tiff', 'tif')):
        fp = wx.Image(fn)
    elif backend == 'wx' and fn.endswith(('tiff', 'tif')):
        fp = multitifIO.MultiTiffReader(fn)
    return fp
    
def load(fn):
    """
    return array from common image formats
    """
    fp = getHandle(fn)
    if backend == 'PIL':
        t,cols,ny,nx,isSwapped = _getImgMode(fp)
        fp.seek(0)

        a = N.fromstring(fp.tobytes(), dtype=t)
        if cols > 1:
            a.shape = (ny, nx, cols)
            a = a.transpose((2,0,1))
        else:
            a.shape = (ny, nx)
        if isSwapped:
            a.byteswap(True)
            
    elif backend == 'wx' and not fn.endswith(('tiff', 'tif')):
        t,cols,ny,nx,isSwapped = _getImgMode(fp)
        buf = fp.GetDataBuffer()
        a = N.frombuffer(buf, dtype=t).copy() # copy is required for some reason
        a.shape = (ny, nx,cols)
        a = a.transpose((2,0,1))
        
    elif backend == 'wx' and fn.endswith(('tiff', 'tif')):
        a = N.squeeze(fp.asarray())
        
    a = a[...,::-1,:]
    return a


colnames= {
    "w" : (255, 255, 255),
    "r" : (255, 0, 0),
    "y" : (255, 255, 0),
    "g" : (0, 255, 0),
    "c" : (0, 255, 255),
    "b" : (0, 0, 255),
    "m" : (255, 0, 255),
    "o" : (255, 128, 0),
    "v" : (128, 0, 255),
    }

def pretreatArr4Img2D(arr, rgbOrder='cmy', min_scales=[None,None,None], max_scales=[None,None,None]):
    """
    arr.shape == (nw, ny, nx)
    rgbOrder: gray scale is 'w', other colors are r, y, g, c, b, m, o, v
    """
    rgb = 'rgb'
    brr = N.zeros((len(rgb),) + arr.shape[-2:], dtype=N.float32)#uint8)
    if arr.ndim == 2:
        arr = arr.reshape((1,)+arr.shape)
    for i, a in enumerate(arr):
        a = a.astype(N.float32)
        mi = min_scales[i]
        if mi is None:
            mi = float(a.min())
        ma = max_scales[i]
        if ma is None:
            ma = float(a.max())
        ad = (a-mi)*255./(ma-mi)
        #if ad.max() > 255:
        #    raise ValueError
        #ad = N.clip(ad, 0, 255)
        
        for j, c in enumerate(colnames[rgbOrder[i]]):
            brr[j] += (ad * (c/255.)).astype(N.float32)
    brr = N.clip(brr, 0, 255).astype(N.uint8)
        
    return brr

def save(arr, outfn, rescaleTo8bit=True, rgbOrder='rgba'):
    """
    Saves data array as image file (format from extension .tif,.jpg,...)

    for multi-color images:
         rgbOrder: order in which axes are mapped to RGB(A) channels
    """
    if rescaleTo8bit:
        ma, mi = float(arr.max()), float(arr.min())
        arr = (arr-mi)*255./(ma-mi)
        arr = arr.astype(N.uint8)

    # common operation from Priithon.useful.array2image
    rgbOrder = rgbOrder.lower()
    rgbOrder = [rgbOrder.find(col) for col in "rgba"]

    #arr = arr[...,::-1,:]
    
    if arr.ndim == 3:
        nc, ny, nx = arr.shape
        if nc < nx:
            arr = N.transpose(arr, (1,2,0))
        else:
            nc0 = nx
            nx = nc
            nc = nc0
            del nc0
        n = 3 - nc
        if n > 0:
            zero = N.zeros(arr.shape[:2]+(n,), arr.dtype)
            arr = N.append(arr, zero, -1)
        nc = arr.shape[-1]
        arr = arr[...,rgbOrder[:nc]]
    elif arr.ndim == 2:
        nc = 1
        ny, nx = arr.shape

    # -----

    if backend == 'PIL':
        arr = arr[::-1]
        if arr.ndim == 2:
            #ny, nx = arr.shape
            if arr.dtype.type == N.uint8:
                mode = "L"
            elif arr.dtype.type == N.float32:
                mode = "F"
            elif arr.dtype.type in ( N.int16, N.uint16 ):
                mode = "I;16"
            else:
                raise ValueError("unsupported array datatype")
            img = Image.frombytes(mode, (nx,ny), arr.tostring())
        else:
            img = Image.frombytes("RGBA"[:nc], (nx,ny), arr.tostring())
        img.save(outfn)
    elif backend == 'wx' and not outfn.endswith(('tif', 'tiff')):
        arr = arr[::-1]
        if arr.ndim == 2:
            arr = N.stack((arr,arr,arr), axis=-1)
        arr = arr.astype(N.uint8)
        img = wx.ImageFromBuffer(arr.shape[-2],arr.shape[-3], N.ascontiguousarray(arr))
        img.SaveFile(outfn)
    elif backend == 'wx' and outfn.endswith(('tif', 'tiff')):
        fp = multitifIO.MultiTiffWriter(outfn)
        fp.setDim(nx=nx, ny=ny, nz=1, nt=1, nw=nc, dtype=arr.dtype)
        waves = fp.makeWaves()
        fp.setDim(wave=waves)
        if nc == 1:
            fp.writeSec(arr)
        else:
            for w in range(nc):
                fp.writeArr(N.ascontiguousarray(arr[...,w]), w=w)
        fp.close()
    return outfn

# -----
def _getImgMode(im):
    """
    This function is from Priithon.Useful.py
    """
    if backend == 'PIL':
        cols = 1
        BigEndian = False
        if im.mode   == "1":
            t = N.uint8
            cols = -1
        elif im.mode == "L" or \
             im.mode == "P": #(8-bit pixels, mapped to any other mode using a colour palette)
            t = N.uint8
        elif im.mode == "I;16":
            t = N.uint16
        elif im.mode == "I":
            t = N.uint32
        elif im.mode == "F":
            t = N.float32
        elif im.mode == "RGB":
            t = N.uint8
            cols = 3
        elif im.mode in ("RGBA", "CMYK", "RGBX"):
            t = N.uint8
            cols = 4
        elif im.mode == "I;16B":  ## big endian
            t = N.uint16
            BigEndian = True
        else:
            raise ValueError("can only convert single-layer images (mode: %s)" % (im.mode,))

        nx,ny = im.size

        isSwapped = (BigEndian and sys.byteorder=='little' or not BigEndian and sys.byteorder == 'big')

        return t,cols, ny,nx, isSwapped
    elif backend == 'wx':
        if type(im) == multitifIO.MultiTiffReader:
            return im.dtype, 1, im.ny, im.nx, None
        else:
            nx = im.GetWidth()
            ny = im.GetHeight()
            col = 3
            dtype = N.uint8
            isSwapped = False
            return dtype, col, ny, nx, isSwapped
    
