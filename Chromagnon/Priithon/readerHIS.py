"""
Hamamatsu Image Sequence file format reader

"""
import numpy as N

mmap_shape = None # default: map entire file; change this to handle BIG files

dtypeHIS = N.dtype([
    ('magic', 'a2'),
    ('ComLen', N.uint16),
    ('iDX', N.uint16),
    ('iDY', N.uint16),
    ('iX', N.uint16),
    ('iY', N.uint16),
    ('pixType', N.uint16),
    ('numImgs', N.uint32),
    ('numChan', N.uint16),
    ('chan', N.uint16),
    ('timeStamp', N.float64),
    ('marker', N.uint32),
    ('miscinfo', '30i1'),
    ])

hisType2numpyDtype = {
    1: N.uint8,
    2: N.uint16,
    3: N.uint32,
    11: ('RGB', (N.uint8,N.uint8,N.uint8)),
    12: ('RGB', (N.uint16,N.uint16,N.uint16)),
}

class ndarray_inHisFile(N.ndarray):
    def __array_finalize__(self,obj):
        self.HIS = getattr(obj, 'HIS', None)

def openHIS(fn, mode='r'):
    """
    open Hamamatsu Image Sequence
    return a mockNDarray
    each section contains a HIS attribute,
        which contains hdr, offsetNext and comment
    """

    m = N.memmap(fn, shape=mmap_shape, mode=mode)
    offset=0
    imgs = []
    while 1: # for i in range(10):
        try:
            img = readSection(m, offset)
        except:#  EOFError:
            break
        imgs.append(img)
        offset = img.HIS.offsetNext

    from Priithon.fftfuncs import mockNDarray
    return mockNDarray(*imgs)


def readSection(m, offsetSect = 0):
    """
    m:          numpy memmap of a file
    offsetSect: offset of first byte of section to be read
    """

    offsetComment = offsetSect + 64
    

    hisHdr = m[offsetSect:offsetComment]
    hisHdr.dtype = dtypeHIS
    try:
        hisHdr = hisHdr[0]
    except IndexError:
        raise EOFError("End of HIS file reached")


    assert hisHdr['magic'] == 'IM'

    commentLength = hisHdr['ComLen']
    offsetImg     = offsetComment + commentLength

    if commentLength:
        hisComment = m[offsetComment:offsetImg]
        hisComment.dtype = '|S%d'%(hisHdr['ComLen'],)
    else:
        hisComment = ('',)
    imgPixDType = hisType2numpyDtype[ hisHdr['pixType'] ]
    imgBytes = int(hisHdr['iDX']) * int(hisHdr['iDY']) * imgPixDType().itemsize
    
    sectEnd = offsetImg + imgBytes

    img = m[offsetImg:sectEnd]
    img.dtype = imgPixDType
    img.shape = hisHdr['iDY'], hisHdr['iDX']


    #import weakref
    #hisHdr     = weakref.proxy( hisHdr )
    #hisComment = weakref.proxy( hishisComment )
    
    img.__class__ = ndarray_inHisFile
    class hisHeaderInfo:
        hdr = hisHdr
        comment = hisComment[0]  # there is "one" comment per sect
        offsetNext = sectEnd

    img.HIS = hisHeaderInfo
    return img

'''
def loadHISsec0(fn, sec=0):
    #import os
    f = open(fn, "rb")
    offsetSect = 0
    iSec = 0
    global sectsOffsets, hisHdr
    sectsOffsets = []
    
    while 1:
        hisHdr = N.fromfile(f, dtype=dtypeHIS, count=1)
        hisHdr = hisHdr[0]

        assert hisHdr['magic'] == 'IM'
        offsetComment = offsetSect + 64
        commentLength = hisHdr['ComLen']
        offsetImg     = offsetComment + commentLength
        imgPixDType = hisType2numpyDtype[ hisHdr['pixType'] ]
        imgBytes = int(hisHdr['iDX']) * int(hisHdr['iDY']) * imgPixDType().itemsize
        #imgShape = hisHdr['iDY'], hisHdr['iDX']

        sectEnd = offsetImg + imgBytes
        offsetSect = sectEnd
        sectsOffsets.append( offsetSect )
        f.seek( offsetSect )
        #f.seek(offsetSect+64+commentLength+imgBytes)  os.SEEK_CUR)
'''

def loadHISsec(fn, sec=0):
    #import os
    f = open(fn, "rb")
    offsetSect = 0
    iSec = 0
    global sectsOffsets, hisHdr, hisComment
    #sectsOffsets = []
    
    for i in range(sec+1):
        f.seek( offsetSect )
        hisHdr = N.fromfile(f, dtype=dtypeHIS, count=1)
        hisHdr = hisHdr[0]

        assert hisHdr['magic'] == 'IM'
        offsetComment = offsetSect + 64
        commentLength = hisHdr['ComLen']
        offsetImg     = offsetComment + commentLength
        imgPixDType = hisType2numpyDtype[ hisHdr['pixType'] ]
        imgBytes = int(hisHdr['iDX']) * int(hisHdr['iDY']) * imgPixDType().itemsize
        
        sectEnd = offsetImg + imgBytes
        offsetSect = sectEnd
        #sectsOffsets.append( offsetSect )
        #f.seek(offsetSect+64+commentLength+imgBytes)  os.SEEK_CUR)

    
    hisComment = f.read(commentLength)
    imgShape = hisHdr['iDY'], hisHdr['iDX']
    img = N.fromfile(f, dtype=imgPixDType, count=N.prod(imgShape))
    img.shape = imgShape = hisHdr['iDY'], hisHdr['iDX']

    #img.__class__ = ndarray_inHisFile
    #img = ndarray_inHisFile(img)
    #class hisHeaderInfo:
    #    hdr = hisHdr
    #    comment = hisComment
    #    offsetNext = sectEnd

    #img.HIS = hisHeaderInfo
    return img

def loadHISsects(fn, secStart=0, secEnd=1, stride=1):
    #import os
    f = open(fn, "rb")
    offsetSect = 0
    iSec = 0
    imgs = []
    #sectsOffsets = []
    
    i=0
    while secEnd is None or i < secEnd:
    #for i in range(secEnd):
        f.seek( offsetSect )
        hisHdr = N.fromfile(f, dtype=dtypeHIS, count=1)
        hisHdr = hisHdr[0]

        assert hisHdr['magic'] == 'IM'
        offsetComment = offsetSect + 64
        commentLength = hisHdr['ComLen']
        offsetImg     = offsetComment + commentLength
        imgPixDType = hisType2numpyDtype[ hisHdr['pixType'] ]
        imgBytes = int(hisHdr['iDX']) * int(hisHdr['iDY']) * imgPixDType().itemsize
        
        sectEnd = offsetImg + imgBytes
        offsetSect = sectEnd
        #sectsOffsets.append( offsetSect )
        #f.seek(offsetSect+64+commentLength+imgBytes)  os.SEEK_CUR)

        if i >= secStart and (((i - secStart)%stride)==0):
            hisComment = f.read(commentLength)
            imgShape = hisHdr['iDY'], hisHdr['iDX']
            img = N.fromfile(f, dtype=imgPixDType, count=N.prod(imgShape))
            img.shape = imgShape = hisHdr['iDY'], hisHdr['iDX']

            #img.__class__ = ndarray_inHisFile
            #img = ndarray_inHisFile(img)
            #class hisHeaderInfo:
            #    hdr = hisHdr
            #    comment = hisComment
            #    offsetNext = sectEnd
            
            imgs.append( img )
        i+=1
    #img.HIS = hisHeaderInfo

    from Priithon.fftfuncs import mockNDarray
    return mockNDarray(*imgs)
