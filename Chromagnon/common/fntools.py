import os, time
join = ''.join

def getFilename(ext='', pre='', fext='.mrc', format='%y%m%d_%H%M_%S'):
    """
    <pre> + <current time> + <ext> + <fext>
    """
    if fext and not fext.startswith(os.path.extsep):
        fext = join((os.path.extsep, fext))
    tm = time.localtime()
    tmf = time.strftime(format, tm)
    fn = join((pre, tmf, ext, fext))
    return fn

def shortenStr(word, nChar=30, lead='...'):
    nw = len(word)
    if nw > nChar:
        nl = len(lead)
        pre = (nChar - nl) // 2
        post = nChar - nl - pre
       # print pre, post, nw, nl
        word = join((word[:pre], lead, word[-post:]))
    return word

def getFileNameFrom(path, fext='.mrc'):
    """
    change extension
    """
    sep = '.'
    ff, ext = os.path.splitext(path)
    if not fext.startswith(os.path.extsep):
        fext = join((os.path.extsep, fext))
    return ff + fext

def getFileNameEndsWith(path, end='', fext=''):
    """
    insert 'end' before extension
    fext: if present, extension is also changed to it
    """
    ff, ext = os.path.splitext(path)
    if fext:
        if not fext.startswith(os.path.extsep):
            fext = join((os.path.extsep, fext))
        ext = fext
    return join((ff, end, ext))

def _findLastDigit(name):
    temp = name
    digi = []
    while temp[-1].isdigit():
        digi.append(temp[-1])
        temp = temp[:-1]
    return join(digi[::-1])

def nextFN(path):
    """
    return filename with the next number
    """
    while os.path.exists(path):
        if path.endswith('.ome.tif'):
            fn = path.replace('.ome.tif', '')
            ext = '.ome.tif'
        else:
            fn, ext = os.path.splitext(path)
        digi = _findLastDigit(fn)
        if digi:
            nd = slice(-len(digi))
            digi = int(digi) + 1
        else:
            nd = slice(None)
            digi = 0
        path = join((fn[nd], str(digi), ext))
        
    return path
            
            
def uniquePart(pathList):
    pre = len(os.path.commonprefix(pathList))
    pathListR = [s[pre::-1] for s in pathList]
    pos = len(os.path.commonprefix(pathListR))
    if not pos:
        sl = slice(pre, None, None)
    else:
        sl = slice(pre, -pos)
    return [s[sl] for s in pathList]
    

def newestFileInTheDir(dr='.', whattime='m', suffix=None, excludeHidden=True):
    """
    whattime: modified (m), created (c) or accessed (a)
    """
    what = whattime[0]
    if what in ['m', 'c', 'a']:
        #exec('func = os.path.get%stime' % what)
        func = os.path.__getattribute__('get%stime' % what) # python 3 compatible
    else:
        raise ValueError('whatitme cannot be recognized')
        
    fns = [(func(os.path.join(dr,fn)), fn) for fn in os.listdir(dr)
           if os.path.isfile(os.path.join(dr, fn))]
    if suffix:
        fns = [fn for fn in fns if fn[-1].endswith(suffix)]
    if excludeHidden:
        fns = [fn for fn in fns if not fn[-1].startswith('.')]
    fns.sort()
    if fns:
        return os.path.join(dr, fns[-1][-1])
    
def appendToBasename(fn, suffix=''):
    base, ext = os.path.splitext(fn)
    return base + suffix + ext

def classifyFn(fns, sep='_', idx=0):
    """
    compare base filenames and list out names

    
    """
    caps = [os.path.basename(fn).split(sep)[idx] for fn in fns]

    done = []
    for i, cap in enumerate(caps[:-1]):
        if cap in [d[0] for d in done]:
            continue

        done.append([cap, [i] + [j+i+1 for j, obj in enumerate(caps[i+1:]) if obj == cap]])

    import pprint
    return pprint.pformat(done)
#return done
            
def linuxOrMac(fn):
    import sys
    if sys.platform == 'darwin' and not fn.startswith('/Volumes'):
        fn = '/Volumes' + fn
    elif sys.platform.startswith('linux') and fn.startswith('/Volumes'):
        fn = fn.replace('/Volumes', '')
    return fn
