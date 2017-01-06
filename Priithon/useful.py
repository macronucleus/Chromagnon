"""priithon U modules: lot's of simple 'useful' (shortcut) functions
"""
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

#from __future__ import generators

import numpy as N
try:
    from scipy import ndimage as nd
except ImportError:
    pass

try:
    import Image
except ImportError:
    try:
        from PIL import Image
    except:
        pass
    
#20060722  import numarray as na
######from numarray import nd_image as nd
#20060722  from numarray import linear_algebra as la
#20060722  from numarray import random_array as ra

try:
    import pdb # useful for U.pdb.pm()  # no time to first import: exception would get lost
except ImportError:
    pass

try:
    import Priithon_bin.seb as S
except:
    S = None
from usefulGeo import *

#  >>> dir(A)
#  ['TextFile', '__builtins__', '__doc__', '__file__', '__name__', 'numarray', 'readArray', 'readFloatArray', 'readIntegerArray', 'string', 'writeArray', 'writeDataSets']

from ArrayIO import readArray_conv, readArray, readFloatArray, readIntegerArray, writeArray, writeDataSets

from readerSIF import readSIF as loadSIF # uses memmap

def myStr(a):
    """
    like str()  but calls str() recursively for lists and tuples
    """
    import types, string #, __builtin__
    if type(a) is types.UnicodeType:
        return "u'"+a+"'"
    if type(a) is types.StringType:
        return "'"+a+"'"
    if type(a) is types.TupleType:
        return '(' + string.join(map(myStr,a), ', ') +')'
    if type(a) is types.ListType:
        return '[' + string.join(map(myStr,a), ', ') +']'
    if type(a) is N.dtype and a.isbuiltin:
        return a.name  # 20060720 

    try:
        s = str(a)
    except:
        return repr(a)
    if s =='':
        return repr(a)
    else:
        return s

def _fixDisplayHook():
    """
    change default displayHook: print .3 instead of .299999
    """

    import sys, __main__
    def _sebsDisplHook(v):
        if not v is None: # != None:
            import __main__ #global _
            #_ = v
            __main__._ = v
            print myStr(v)
    sys.displayhook = _sebsDisplHook

def _execPriithonRunCommands():
    """
    http://en.wikipedia.org/wiki/Run_Commands
    Rc stands for the phrase "run commands"
    It is used for any file that contains startup information for a command.
    While not historically precise, rc may also be pronounced as "run control", because an rc file controls how a program runs.

    Similarely to matplotlib (ref. matplotlib_fname()), we look for a "user customization" file,
    ".priithonrc.py" in the following order:
    1. currentworking directory
    2. environment variable PRIITHONRC
    3. HOME/.priithonrc.py
    4. windows only:  TODO FIXME
    """
    rcFN = _getRCfile()
    if rcFN:
        import sys,__main__
        #try:
            #stdout = sys.stdout
            #try:
            #    sys.stdout = __main__.shell
            #except:
            #    pass
        try:
            execfile(rcFN,__main__.__dict__)
        except:
            if PriConfig.raiseEventHandlerExceptions:
                raise
            else:
                import traceback
                traceback.print_exc()
        #finally:
        #    sys.stdout = stdout

def _getRCfile():
    import os
    rcFN = os.path.join( os.getcwd(), '.priithonrc.py')
    if os.path.exists(rcFN):
        return rcFN
    rcFN = os.path.join( os.getcwd(), '_priithonrc.py')
    if os.path.exists(rcFN):
        return rcFN

    try:
        #old path =  os.environ['PRIITHONRC']
        rcFN =  os.environ['PRIITHONRC']
    except KeyError:
        pass
    else:
        #  rcFN = os.path.join( path, '.priithonrc.py')
        #  if os.path.exists(rcFN):
        return rcFN

    path = getHomeDir(defaultToCwd=False)
    if path:
        rcFN = os.path.join( path, '.priithonrc.py')
        if os.path.exists(rcFN):
            return rcFN
        rcFN = os.path.join( path, '_priithonrc.py')
        if os.path.exists(rcFN):
            return rcFN

    return ""
    
def getHomeDir(defaultToCwd=False):
    """
    Try to find user's home directory, otherwise return current directory.
    If defaultToCwd is False, returns "" in case nothing else works
    """
    #original: http://mail.python.org/pipermail/python-list/2005-February/305394.html
    #          Subject: Finding user's home dir
    #          From: Nemesis nemesis at nowhere.invalid 
    #          Date: Wed Feb 2 20:26:00 CET 2005
    #          def getHomeDir():
    #              ''' Try to find user's home directory, otherwise return current directory.'''
    import os
    try:
        path1=os.path.expanduser("~")
    except:
        path1=""
    try:
        path2=os.environ["HOME"]
    except:
        path2=""
    try:
        path3=os.environ["USERPROFILE"]
    except:
        path3=""

    if not os.path.exists(path1):
        if not os.path.exists(path2):
            if not os.path.exists(path3):
                if defaultToCwd:
                    return os.getcwd()
                else: return ""
            else: return path3
        else: return path2
    else: return path1



def _getSourceCodeLine(depth=0):
    """
    return "current" line number of source code  inside py-file 
    """
    import inspect
    return inspect.currentframe(depth).f_back.f_lineno

def _getSourceCodeFilename(numPathTails=None, depth=0):
    """
    return "current" filename of py-file 
    if numPathTails:
        split off all leading folder before the last numPathTails parts,
        and return only those remaining parts;
        e.g. for numPathTails=2: for "/a/b/c/d/e.py" return "d/e.py"
    """
    import inspect
    fn= inspect.currentframe(depth).f_back.f_code.co_filename
    if numPathTails:
        return '/'.join(fn.split('/')[-numPathTails:])
    else:
        return fn

def _getSourceCodeFuncName(depth=0):
    """
    return "current" function name 
    """
    import inspect
    return inspect.currentframe(depth).f_back.f_code.co_name

def _getSourceCodeLocation(numPathTails=None, depth=0):
    """
    return <filename>:<lineNo
    concatenating the results of
    _getSourceCodeFilename  and _getSourceCodeLine
    """
    return "%s:%d"%(_getSourceCodeFilename(numPathTails, depth+1),
                    _getSourceCodeLine(depth+1))

def _raiseRuntimeError(msg, appendSourceCodeLocation=True, numPathTails=None):
    """
    use this only inside an except clause
    """
    #import traceback
    import sys
    exc_info = sys.exc_info()
    exc_info = (RuntimeError, 
                RuntimeError(msg + "\n" + #"Cannot open file as image\n"+
                             _getSourceCodeLocation(numPathTails, depth=1)
                             #"   (%s line:%s)\n"%(currentfile(2),currentline())
                             ),#"prior error: "+''.join(traceback.format_exception_only(exc_info[0], exc_info[1]),)),
                exc_info[2])
    raise exc_info[0], exc_info[1], exc_info[2]
    




def _getGoodifiedArray(arr):
    """
    return "well behaved" version of a numpy array
    1) convert lists or tuple to numpy-array
    2) make copy of numpy arrays if non-contigous or non-native

    (used in conjunction with SWIGed functions)
    """
    try:
        if arr.dtype.isnative:
            arr = N.ascontiguousarray(arr)
        else:
            arr = N.ascontiguousarray(arr, arr.dtype.newbyteorder('='))
    except AttributeError:
            arr = N.ascontiguousarray(arr)

    if arr.dtype == N.bool:  # no SWIGed function for bool, use uint8
        arr = arr.view(N.uint8)

    return arr

def naSetArrayPrintMode(precision=4, suppress_small=1):
    #import sys
    #sys.float_output_suppress_small=suppress_small
    #na.arrayprint.set_precision(precision)
    N.set_printoptions(precision=precision, threshold=None,
                       edgeitems=None, linewidth=None,
                       suppress=suppress_small)

def debug():
    """calls post-mortem-debugger  pdm.pm()
    commands:
        q - quit
        l - list
        p - print 'variable'
        u - up in calling stack
        d - down in calling stack
        h - help
        ...
    """
    pdb.pm()

def DEBUG_HERE():
    """calls debugger  pdm.set_trace()
       go into debugger mode once execution reaches this line
    """
    pdb.set_trace()


def timeIt(execStr, nReps=1):
    """calls exec(execStr)  nReps times
    returns "cpu-time-after"-"cpu-time-before"
    if nReps > 1  the it calls it nReps times
                  and return mmms over all (each separately timed!)
    """
    import sys, time
    global fr,fc, argsn, args
    fr = sys._getframe(1)
    # fc = fr.f_code
    #gs = fr.f_locals   #gs = fr.f_globals
    

    if nReps==1:
        t0 = time.clock()
        exec execStr in fr.f_locals, fr.f_globals
        return time.clock() - t0
    else:
        _ttt = N.empty(shape=nReps, dtype=N.float64)
        for _i in range(nReps):
            t0 = time.clock()
            exec execStr  in fr.f_locals, fr.f_globals
            _ttt[_i] = time.clock() - t0
        return mmms(_ttt)

def reloadAll(verbose=False, repeat=1, hiddenPriithon=True):
    """
    reload all modules known in __main__

    repeat 'repeat' times - in case of dependencies

    if hiddenPriithon is True:
    also reload
       viewer.py
       viewer2.py
       viewerCommon.py
       histogram.py
       splitND.py
       splitND2.py
       splitNDCommon.py
    """
    import __main__, types, __builtin__, sys
    for i in range(1+repeat):
        for m,mm in __main__.__dict__.iteritems():
            if type(mm) == types.ModuleType and not mm in (__builtin__, __main__, sys):
                if verbose:
                    print m,
                reload(mm)
        if hiddenPriithon:
            mods = ['viewerCommon',
                    'viewer',
                    'viewer2',
                    'histogram',
                    'splitNDcommon',
                    'splitND',
                    'splitND2', 
                    'usefulX', 
                    ]
            for m in mods:
                exec "import %s; reload(%s)" %(m,m)

def localsAsOneObject(*args):
    """
    useful for rapid code development / debugging:

    create and return a classObject containing some/all local variables
    taken from the calling function-frame

    if no args given: return all local vars
    """
    import sys
    fr = sys._getframe(1)

    class _someLocalVars:
        pass
    
    retDict = _someLocalVars()
    if len(args) == 0:
        for varname,varvalue in fr.f_locals.iteritems():
            retDict.__dict__[varname] = varvalue
    else:
        for v in args:
            for varname,varvalue in fr.f_locals.iteritems():
                if v is varvalue:
                    retDict.__dict__[varname] = varvalue
                    break

    return retDict
                




import string
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/303342
def strTranslate(s, frm='', to='', delete='', keep=None):
    """
    translate chars in string `s`
    each `c` in `frm` is translated into the respective `c` in `to`
      (`to` can be length 1)
    each `c` in `keep` is kept
     UNLESS(!) it is also in `delete`
    each `c` in `delete` is taken out

    seb: instead of a class we have a function - ref. ASPN/Cookbook/Python/Recipe/303342

    This class handles the three most common cases where I find myself having to stop and think about how to use translate:

    1) Keeping only a given set of characters.
    >>> strTranslate('Chris Perkins : 224-7992', keep=U.string.digits)
    '2247992'

    2) Deleting a given set of characters.
    >>> strTranslate('Chris Perkins : 224-7992', delete=U.string.digits)
    'Chris Perkins : -'

    3) Replacing a set of characters with a single character.
    >>> trans = Translator(string.digits, '%')
    >>> strTranslate('Chris Perkins : 224-7992', (string.digits, '%')
    'Chris Perkins : %%%-%%%%'

    Note that the delete parameter trumps the keep parameter if they overlap:
    >>> strTranslate('abcdef', delete='abcd', keep='cdef')
    'ef'
    This is an arbitrary design choice - makes as much sense as anything, I suppose.
    """
    allchars = string.maketrans('','')
    if len(to) == 1:
        to = to * len(frm)
    trans = string.maketrans(frm, to)
    if keep is not None:
        delete = allchars.translate(allchars, keep.translate(allchars, delete))
    #def callable(s):

    if type(s) is unicode: # HACK workaround for unicode (occurred with TextCrtl unicode-version of wxPython)
        s = str(s)
    return s.translate(trans, delete)
    #return callable

def memNAprofile(dicts=[],
                 addHere=3,
                 verbose=True):
    """
    report on numarray mem usage in given dictinoaries (or modules)
    if addHere is
       1 include locals() dict from where memNAprofile is called
       2 include globals() dict from where memNAprofile is called
       3 both

    if verbose: print stats for each numarray found

    returns tuple( number of numarrays, total MB mem usage, timeString)
    """
    print "TODO: memNAprofile"
    return 
    global arrs # HACK for sebsort
    gs = {}
    if addHere:
        import sys
        fr = sys._getframe(1)
        if addHere & 2:
            gs.update(fr.f_globals)
        if addHere & 1:
            gs.update(fr.f_locals)
    for d in dicts:
        if type(d) is dict:
            gs.update( d )
        else: # assume it is a module
            gs.update( d.__dict__ )
        

    #global gs, k, o,f,fs, arrs, totsize, totnum
    f=''   # RuntimeError: dictionary changed size during iteration
    fs=''
    o=''
    k=''
    arrs = {}
    totsize = 0
    totnum = 0
    kStringMaxLen = 0
    t_naa = N.ndarray
    import string

    nonMemFakeAddr = -1

    for k in gs:
        if len(k) > kStringMaxLen:
            kStringMaxLen = len(k)
        o = gs[k]
        t = type(o)
        if t == t_naa:
            #print k # , t
            f = string.split( repr(o._data) )
            if f[0] == '<memory': # '<memory at 0x50a66008 with size:0x006f5400 held by object 0x092772e8 aliasing object 0x00000000>'
                fs = string.split( f[4],':' )
                size   = eval( fs[1] )
                memAt  = f[2]
                objNum = f[8]
            elif f[0] == '<MemmapSlice': # '<MemmapSlice of length:7290000 readonly>'
                fs = string.split( f[2],':' )
                size   = eval( fs[1] )
                memAt  = nonMemFakeAddr
                nonMemFakeAddr -= 1
                objNum = 0
            else:
                if verbose:
                    print "# DON'T KNOW: ",  k, repr(o._data)
                continue

            #print repr(o._data)
            #print objNum, memAt, size

            try:
                arrs[ memAt ][0] += 1
                arrs[ memAt ][1].append( k )
                arrs[ memAt ][2].append( size )
            except:
                arrs[ memAt ] = [ 1, [k], [size] ]
                totsize += size
                totnum  += 1
                
    def sebsort(m1,m2):
        global arrs
        import __builtin__
        k1 = arrs[ m1 ][1]
        k2 = arrs[ m2 ][1]
        return __builtin__.cmp(k1,  k2)

    if verbose:
        ms = arrs.keys()
        ms.sort( sebsort )
        #print kStringMaxLen
        for memAt in ms:
            ks   = arrs[ memAt ][1]
            size = arrs[ memAt ][2][0]
            o = gs[ ks[0] ]
            if len(ks) == 1:
                ks = ks[0]
            print "%8.2fk %-*s %-14s %-15s %-10s" %(size/1024., kStringMaxLen, ks, o.type(), o.shape, memAt)

    del arrs # HACK for sebsort
    import time
    return totnum, int(totsize/1024./1024. * 1000) / 1000.,  time.asctime()

def dirNA(inclSize=0):
    import sys, time
    global fr,fc, argsn, args
    fr = sys._getframe(1)
    fc = fr.f_code
        
    print "TODO: dirNA"
    return 
    #           modname = fr.f_globals['__name__']
    #    #print "=== Module:", modname, "==="
    
    #           if modname != None:
    #               exec "import " + modname
    #           else:
    #               print "DEBUG: modname is None  -- why !?"

    global gs, k, o,f,fs, arrs, totsize, totnum
    f=''   # RuntimeError: dictionary changed size during iteration
    fs=''
    o=''
    k=''
    arrs = {}
    totsize = 0
    totnum = 0
    #gs = fr.f_globals # .keys()
    gs = fr.f_locals # .keys()
    kStringMaxLen = 0
    t_naa = N.ndarray
    import string


    gsF = []
    for k in gs:
        o = gs[k]
        t = type(o)
        if t == t_naa:
            if inclSize:
                f = string.split( repr(o._data) )
                if f[0] == '<memory':
                    fs = string.split( f[4],':' )
                    size   = eval( fs[1] )
                    memAt  = f[2]
                    objNum = f[8]
                else:
                    fs = string.split( f[2],':' )
                    size   = eval( fs[1] )
                    memAt  = 0
                    objNum = 0
                    gsF += [(k, size)]
            else:
                gsF += k
        gsF.sort()
        print gsF
        '''
    for k in gs:
        if len(k) < kStringMaxLen:
            kStringMaxLen = len(k)
        o = gs[k]
        t = type(o)
        if t == t_naa:
            #print k # , t

            #print repr(o._data)
            #print objNum, memAt, size

            try:
                arrs[ memAt ][0] += 1
                arrs[ memAt ][2].append( size )
            except:
                arrs[ memAt ] = [ 1, k, [size] ]
                totsize += size
                totnum  += 1

    def sebsort(m1,m2):
        global arrs
        import __builtin__
        k1 = arrs[ m1 ][1]
        k2 = arrs[ m2 ][1]
        return __builtin__.cmp(k1,    k2)

    ms = arrs.keys()
    ms.sort( sebsort )
    for memAt in ms:
        k     = arrs[ memAt ][1]
        size = arrs[ memAt ][2][0]
        o = gs[k]
        
        print "%8.2fk %-*s %14s %15s %10s" %(size/1024., kStringMaxLen, k, o.type(), o.shape, memAt)
        '''

def deriv1D(arr, reverse=0):
    """poor mans derivative:
    if reverse:
        returns arr[:-1] - arr[1:]
    else
        returns arr[1:] - arr[:-1]
    """
    arr = N.asarray(arr)
    if reverse:
        return arr[:-1] - arr[1:]
    else:
        return arr[1:] - arr[:-1]

   

def checkGoodArrayF(arr, argnum, shape=None):
    if not arr.flags.carray:
        raise RuntimeError, "*** non contiguous arg %s ** maybe use zeroArrF" % argnum
    if arr.dtype.type != N.float32:
        raise RuntimeError, "*** non Float32 arg %s ** maybe use zeroArrF" % argnum
    if not arr.dtype.isnative:
        raise RuntimeError, "*** non native byteorder: arg %s ** maybe use zeroArrF" % argnum
    if shape is not None and shape != arr.shape:
        raise RuntimeError, "*** arg %d should have shape %s, but has shape %s" \
                   % (argnum, shape, arr.shape)


def arrSharedMemory(shape, dtype, tag="PriithonSharedMemory"):
    """
    Windows only !
    share memory between different processes if same `tag` is used.
    """
    itemsize = N.dtype(dtype).itemsize
    count = N.product(shape)
    size =  count * itemsize
    
    import mmap
    sharedmem = mmap.mmap(0, size, tag)
    a=N.frombuffer(sharedmem, dtype, count)
    a.shape = shape
    return a


def arr(dtype=None, *args):
    """return args tuple as array
    if dtype is None use "default/automatic" dtype
    """
    return N.array(args, dtype=dtype)
def arrF(*args):
    """return args tuple as array dtype=Float32
    """
    return N.array(args, dtype=N.float32)
def arrD(*args):
    """return args tuple as array dtype=Float64
    """
    return N.array(args, dtype=N.float64)
def arrI(*args):
    """return args tuple as array dtype=Int32
    """
    return N.array(args, dtype=N.int32)
def arrU(*args):
    """return args tuple as array dtype=UInt16
    """
    return N.array(args, dtype=N.uint16)
def arrS(*args):
    """return args tuple as array dtype=Int16
    """
    return N.array(args, dtype=N.int16)
def arrC(*args):
    """return args tuple as array dtype=Complex64 (single prec)
    """
    return N.array(args, dtype=N.complex64)
def arrCC(*args):
    """return args tuple as array dtype=Complex128 (double prec)
    """
    return N.array(args, dtype=N.complex128)

def asFloat32(a):
    """returns N.asarray(a, N.Float32)"""
    return N.asarray(a, N.float32)

def norm(arr, axis=-1):
    """return array with ndim arr.ndim-1
        return N.sqrt(N.sum(arr**2, axis)

U.norm([3,4])
5.0
U.timeIt("U.norm([3,4])", 100000)
(0.0, 0.02, 0.000384, 0.00192211966329)
U.timeIt("U.norm([3])", 100000)
(0.0, 0.02, 0.0003597, 0.00186269050301)
a = na.asarray([3,4])
U.timeIt("U.norm(a)", 100000)
(0.0, 0.01, 0.0001728, 0.00130312706978)
a = na.asarray([3])
U.timeIt("U.norm(a)", 100000)
(0.0, 0.01, 0.0001689, 0.00128859333771)
U.timeIt("na.abs(a)", 100000)
(0.0, 0.02, 0.0001107, 0.00104725618165)
U.timeIt("abs(a)", 100000)
(0.0, 0.01, 0.0001092, 0.00103926674151)
    """
    arr = N.asarray(arr)
    return N.sqrt(N.sum(arr**2, axis))

def clip(arr,min,max):
    """
    clips arr *inplace*
    returns arr
    """
    #arr = _getGoodifiedArray(arr)
    #S.clip( arr, min, max )
    arr = N.clip(arr, min, max)
    return arr

def findMax(arr):
    """returns value and position of maximum in arr
    assumes 3D array, so returned is a 4-tuple: [val,z,y,x]
    for 2D or 1D z,y would be respectively 0
    """
    #arr = _getGoodifiedArray(arr)
    #return S.findMax( arr )
    a1d = arr.ravel()
    idx = N.argmax(a1d)
    ids = N.unravel_index(idx, arr.shape)
    ids = (3-len(ids)) * (0,) + ids
    val = a1d[idx]
    return (val,) + ids

def findMin(arr):
    """returns value and position of minimum in arr
    assumes 3D array, so returned is a 4-tuple: [val,z,y,x]
    for 2D or 1D z,y would be respectively 0
    """
    #arr = _getGoodifiedArray(arr)
    #return S.findMin( arr )
    a1d = arr.ravel()
    idx = N.argmin(a1d)
    ids = N.unravel_index(idx, arr.shape)
    ids = (3-len(ids)) * (0,) + ids
    val = a1d[idx]
    return (val,) + ids

def min(arr):
    arr = N.asarray(arr)
    return arr.min()

def max(arr):
    arr = N.asarray(arr)
    return arr.max()

def median(arr):
    #arr = _getGoodifiedArray(arr)
    #return S.median( arr )
    return N.median(arr)

#def median2(arr):
#    """returns both median and "median deviation" (tuple)
#    (broken on windows !!! returns always -999, see 'seb1.cpp')
#    """
#    arr = _getGoodifiedArray(arr)
#    return S.median2( arr )


def mean(arr):
    #arr = _getGoodifiedArray(arr)
    #return S.mean( arr )  # CHECK if should use ns.mean
    return N.mean(arr)

def stddev(arr):
    arr = N.asarray(arr)
    return N.std(arr.flat)

_FWHM_over_gaussStddev = 2. * N.sqrt(2.*N.log(2.)) 

def FWHM(arr):
    """returns Full-Width-Half-Max for gaussian distributions"""
    return _FWHM_over_gaussStddev * stddev(arr)

def FWHM_s(gaussStddev):
    """returns Full-Width-Half-Max for gaussian distributions
    gaussStddev is the stddev of arr"""
    return _FWHM_over_gaussStddev * gaussStddev

_pi_over_180 = N.pi/180
def deg2rad(angle):
    """return angle(given in degree) converted to randians"""
    return angle * _pi_over_180
def rad2deg(angle):
    """return angle(given in randians) converted to degree"""
    return angle / _pi_over_180


def mm(arr):
    """
    returns min,max of arr
    """

    arr = N.asarray(arr)
    return (N.minimum.reduce(arr.flat), N.maximum.reduce(arr.flat))

def mmm(arr):
    """
    returns min,max,mean of arr
    """
    #arr = _getGoodifiedArray(arr)
    #TODO: make nice for memmap
    #m = S.mean(arr)
    m = N.mean(arr)
    return (N.minimum.reduce(arr.flat), N.maximum.reduce(arr.flat), m)

def mmms(arr):
    """
    returns min,max,mean,stddev of arr
    """
    #arr = _getGoodifiedArray(arr)
    #TODO: make nice for memmap
    #mi,ma,me,st = S.mmms( arr )
    mi = N.minimum.reduce(arr.flat)
    ma = N.maximum.reduce(arr.flat)
    me = arr.mean()
    st = arr.std()
    return (mi,ma,me,st)

def mean2d(arr, outtype=N.float32):
    """
    returns an array of shape arr.shape[:-2] and dtype outtype
    """
    b = N.empty(shape=arr.shape[:-2], dtype=outtype)
    bb = b.view()
    bb.shape = (-1,)
    aarr = arr.view()
    aarr.shape = (-1,) + arr.shape[-2:]

    for i in range( bb.shape[0] ):
        #bb[i] = S.mean( aarr[i] )
        bb[i] = aarr[i].mean()

    return b

def max2d(arr, outtype=None):
    """returns an array of shape arr.shape[:-2] and dtype outtype
    if outtype=None it uses arr.dtype
    """
    if outtype is None:
        outtype = arr.dtype

    b = N.empty(shape=arr.shape[:-2], dtype=outtype)
    bb = b.view()
    bb.shape = (-1,)
    aarr = arr.view()
    aarr.shape = (-1,) + arr.shape[-2:]

    for i in range( bb.shape[0] ):
        bb[i] = aarr[i].max()

    return b
def min2d(arr, outtype=None):
    """returns an array of shape arr.shape[:-2] and dtype outtype
    if outtype=None it uses arr.dtype
    """
    if outtype is None:
        outtype = arr.dtype

    b = N.empty(shape=arr.shape[:-2], dtype=outtype)
    bb = b.view()
    bb.shape = (-1,)
    aarr = arr.view()
    aarr.shape = (-1,) + arr.shape[-2:]

    for i in range( bb.shape[0] ):
        bb[i] = aarr[i].min()

    return b

def mmm2d(arr, outtype=None):
    """min-max-mean: returns an array of shape (3,)+arr.shape[:-2] and dtype outtype
    if outtype=None it uses arr.dtype
    """
    if outtype is None:
        outtype = arr.dtype

    b = N.empty(shape=(3,)+arr.shape[:-2], dtype=outtype)
    bb = b.view()
    bb.shape = (3, -1)
    aarr = arr.view()
    aarr.shape = (-1,) + arr.shape[-2:]

    for i in range( bb.shape[1] ):
        arr = _getGoodifiedArray(aarr[i])

        bb[:, i] = mmm( aar )

    return b

def mmms2d(arr, outtype=N.float32):
    """min-max-mean-stddev: returns an array of shape (4,)+arr.shape[:-2] and dtype outtype
    if outtype=None it uses arr.dtype
    """
    if outtype is None:
        outtype = arr.dtype

    b = N.empty(shape=(4,)+arr.shape[:-2], dtype=outtype)
    bb = b.view()
    bb.shape = (4, -1)
    aarr = arr.view()
    aarr.shape = (-1,) + arr.shape[-2:]

    for i in range( bb.shape[1] ):
        arr = _getGoodifiedArray(aarr[i])
        bb[:, i] = mmms( arr )

    return b

def mm2d(arr, outtype=None):
    """min-max: returns an array of shape (2,)+arr.shape[:-2] and dtype outtype
    if outtype=None it uses arr.dtype
    """
    if outtype is None:
        outtype = arr.dtype

    b = N.empty(shape=(2,)+arr.shape[:-2], dtype=outtype)
    bb = b.view()
    bb.shape = (2, -1)
    aarr = arr.view()
    aarr.shape = (-1,) + arr.shape[-2:]

    for i in range( bb.shape[1] ):
        bb[0, i] = aarr[i].min()
        bb[1, i] = aarr[i].max()

    return b
def median2d(arr, outtype=None):
    """median per 2d section

    returns an array of shape arr.shape[:-2] and dtype outtype
    if outtype=None it uses arr.dtype
    """
    if outtype is None:
        outtype = arr.dtype

    b = N.empty(shape=arr.shape[:-2], dtype=outtype)
    bb = b.view()
    bb.shape = (-1,)
    aarr = arr.view()
    aarr.shape = (-1,) + arr.shape[-2:]

    for i in range( bb.shape[0] ):
        arr = _getGoodifiedArray(aarr[i])
        bb[i] = median( arr )

    return b
def median22d(arr, outtype=None):
    """median2 per 2d section [median is (median,meddev)]

    returns an array of shape (2,)+arr.shape[:-2] and dtype outtype
    if outtype=None it uses arr.dtype
    """
    if outtype is None:
        outtype = arr.dtype

    b = N.empty(shape=(2,)+arr.shape[:-2], dtype=outtype)
    bb = b.view()
    bb.shape = (2, -1)
    aarr = arr.view()
    aarr.shape = (-1,) + arr.shape[-2:]

    for i in range( bb.shape[1] ):
        arr = _getGoodifiedArray(aarr[i])
        bb[:, i] = S.median2( arr )

    return b

def topPercentile2d(arr, percentile=1, outtype=None):
    """find Intens. for highest percentile  per section


    returns an array of shape (2,)+arr.shape[:-2] and dtype outtype
    if outtype=None it uses arr.dtype

    slow!! ****** might only work for UInt16 arr *********
    """
    if outtype is None:
        outtype = arr.dtype

    b = N.empty(shape=arr.shape[:-2], dtype=outtype)
    bb = b.view()
    bb.shape = (-1,)
    aarr = arr.view()
    aarr.shape = (-1,) + arr.shape[-2:]

    hist = N.empty( shape=(1<<16), dtype=N.int32 )
    nPix = N.prod( aarr[0].shape )
    for i in range( bb.shape[0] ):
        arr = _getGoodifiedArray(aarr[i])

        (mi,ma,mean,stddev) = S.histogram2(arr, 0, (1<<16), hist)
        tp = S.toppercentile(hist, nPix, int(ma), percentile)
        bb[i] = tp

    return b


def fitLine(yy,xx=None):
    """returns (a,b, yDeltaSumPerVal) for least-sqare-fit of axx(i) + b = yy(i)
    yDeltaSumPerVal= sum[(axx+ b - yy)**2] **.5 / numPoints

    if xx is None it defaults to 0,1,2,3,4,...
    """
    if xx is None:
       xx= N.arange( len(yy) )
    
    xm = N.mean(xx)
    ym = N.mean(yy)
    xym = N.mean(xx*yy)
    xxm= N.mean(xx*xx)
    a = (xm * ym - xym) / (xm*xm - xxm)
    b = ym-a*xm

    deltaSumPerVal = N.sum( (a*xx+b - yy) ** 2 ) **.5   / xx.shape[0]
    
    return (a, b, deltaSumPerVal)

'''
def fitAnyND(f, parmTuple0, arr, max_iterations=None):
    """
    arr is an nd-array
    todo: optional "delta-Y"-array
    
    f is your 'model' function that takes two arguments:
    a tuple of parameters and x
    
    The function returns a list containing the optimal parameter values
    and the chi-squared value describing the quality of the fit.
    """

    from Scientific.Functions.LeastSquares import leastSquaresFit

    coords = N.transpose(N.indices(arr.shape), range(1,arr.ndim+1)+[0]).copy() # 'x' (tuples)
    coords.shape=(-1,arr.ndim)

    data = [(p, arr[tuple(p)]) for p in coords]

    return leastSquaresFit(f,parmTuple0,data, max_iterations)

def _gaussian2D_5_N(parms, coor_tuple):
    """parms: peakValue, sigmay,x,centery,x"""
    import Numeric as Num
    amp = parms[0]
    sig_y = parms[1]
    sig_x = parms[2]
    y0 = parms[3]
    x0 = parms[4]
    y = coor_tuple[-2]
    x = coor_tuple[-1]
    dy = (y-y0)/sig_y
    dx = (x-x0)/sig_x

    return amp*Num.exp(-0.5*( dy*dy + dx*dx) )
def _gaussian3D_7_N(parms, coor_tuple):
    """parms: peakValue, sigmaz,y,x,centerz,y,x"""
    import Numeric as Num
    amp = parms[0]
    sig_z = parms[1]
    sig_y = parms[2]
    sig_x = parms[3]
    z0 = parms[4]
    y0 = parms[5]
    x0 = parms[6]
    z = coor_tuple[-3]
    y = coor_tuple[-2]
    x = coor_tuple[-1]
    dz = (z-z0)/sig_z
    dy = (y-y0)/sig_y
    dx = (x-x0)/sig_x

    return amp*Num.exp(-0.5*( dz*dz + dy*dy + dx*dx) )
    

def fitGaussian2D(parmTuple0, arr, max_iterations=None):
    """parms: peakValue, sigmay,x,centery,x"""
    if arr.ndim != 2:
        raise ValueError, "arr must be of ndim 2"
    if len(parmTuple0) != 5:
        raise ValueError, "parmTuple0 must be a 5-tuple: peakValue, sigmay,x,centery,x"
    return fitAnyND(_gaussian2D_5_N, parmTuple0, arr, max_iterations)    
def fitGaussian3D(parmTuple0, arr, max_iterations=None):
    """parms: peakValue, sigmaz,y,x,centerz,y,x"""
    if arr.ndim != 3:
        raise ValueError, "arr must be of ndim 3"
    if len(parmTuple0) != 7:
        raise ValueError, "parmTuple0 must be a 7-tuple: peakValue, sigmaz,y,x,centerz,y,x"
    return fitAnyND(_gaussian3D_7_N, parmTuple0, arr, max_iterations)    


'''



def yGaussian(parms=(10,100), t=0):
    """
    t can be a scalar or a vector
    returns y value(s) of a 1D-gaussian model

    parms can be tuple of length 2,3 or 4, with
    2: tuple is [sigma, peakVal]
    3: tuple is [x0, sigma, peakVal]
    4: tuple is [y0, x0, sigma, peakVal]

    x0 is center of gaussian (default 0)
    y0 is baseline offset gaussian (default 0)
    sigma is sigma (stddev) of gaussian
    peakval is  "center height" above baseline
    """
    import fftfuncs as F

    if len(parms) == 4:
        y0,x0 = parms[:2]
    elif len(parms) == 3:
        y0,x0 = 0.0, parms[0]
    else:
        y0,x0 = 0.0, 0.0
    sigma, peakVal = parms[-2:]

    return y0+F.gaussian(t-x0, dim=1, sigma=sigma, peakVal=peakVal)

def yDecay(parms=(1000,10000,10), t=0):
    """
    t can be a scalar or a vector
    returns y value(s) of a decay model
    parms:
        tuple of 1 or 3 or 5 or .. values
        first baseline = asymtote =y for t-> inf
        then pairs:
          first:  intercept of an exponential decay
          second: half-time of an exponential decay

        for more than 3 parameters: sum multiple such decay terms
    """
    if len(parms) % 2==0:
        raise ValueError, "number of parms must be odd: one offset and 2 more for each exponential"
    try:
        r = N.array(len(t)*(parms[0],))
    except: # t has no len
        r = parms[0]

    halfTimeScaler = N.log(2.)
    n = int( (len(parms)-1) / 2 )
    for i in range(n):
        r = r + parms[1+2*i] * N.exp(-t *halfTimeScaler/ parms[2+2*i])
#       r = r + parms[1+2*i] * N.exp(-t *halfTimeScaler/ float(parms[2+2*i]))
    return r
def yPoly(parms=(1,1,0), t=0):
    """
    t can be a scalar or a vector
    returns y value(s) of a polygon model
    parms:
      baseline, first-order coeff, 2nd, ...
    """
    r = 0.0
    tPow = 1.
    for i in range(len(parms)):
        if i:
            tPow *= t
        r = r + parms[i]*tPow # N.power(t, i)
    return r

def yLine(abTuple=(1,1), t=0):
    """
    t can be a scalar or a vector
    returns y value(s) of a line model
    parms:
      abTuple: a,b  - as in y= ax + b
    """
    a,b = abTuple
    return b+a*t





def fitAny(f, parmTuple0, data, fixed_mask=None, **leastsq_kwargs):
    """
    data should be list of (x,y)  tuples
    TODO: or (x,y,deltaY)
    (instead of 'list' you can of course have an array w/
    shape=(n,2) or shape=(n,3), n beeing the number of data points

    if data.ndim == 1 or data.shape = (n,1) it fits assuming x=0,1,2,3,...n-1

    f is your 'model' function that takes two arguments:
       a tuple of parameters and x
    
    The function returns a list containing the optimal parameter values
    and the chi-squared value describing the quality of the fit. (CHECK if this is true)

    fixed_mask: if not None: 
       this sequence of bool values determinces if the respective parameter
       shall be fixed or free to be adjusted

    leastsq_kwargs: optional arguments feed to scipy.optimize.leastsq:
       useful might be e.g.: 
        * maxfev -- The maximum number of calls to the function. If zero,
           then 100*(N+1) is the maximum where N is the number
           of elements in x0.
        * full_output -- non-zero to return all optional outputs.
        * warning -- True to print a warning message when the call is
             unsuccessful; False to suppress the warning message.
        for more see scipy.optimize.leastsq
    """
    from scipy.optimize import leastsq

    data = N.asarray(data, dtype=N.float64)

    if len(data.shape) == 1:
        data = N.transpose(N.array([N.arange(len(data)), data]))
    elif data.shape[1] == 1:
        data = N.transpose(N.array([N.arange(len(data)), data][0]))

    x,y = data.T
    
    if fixed_mask is not None:
        # just in case fixed_mask is too long for parmTuple
        fixed_mask = fixed_mask[:len(parmTuple0)]

    if fixed_mask is None or not any(fixed_mask):
        def func(p):
            return f(p, x)-y

        x0 = parmTuple0
        return leastsq(func, x0, **leastsq_kwargs)
    elif all(fixed_mask):
        # all parameters are fixed -- we don't need to fit anything here.
        return parmTuple0, 999
    else:
        def func(p):
            par_iHere=0
            pp=[None]*len(parmTuple0)
            for par_i,par_fixed in enumerate(fixed_mask):
                if par_fixed:
                    pp[par_i] = parmTuple0[par_i]
                else:
                    pp[par_i] = p[par_iHere]
                    par_iHere+=1
            return f(pp, x)-y
    
        x0=[]
        for par_i,par_fixed in enumerate(fixed_mask):
            if not par_fixed:
                x0.append(parmTuple0[par_i])
        x0=tuple(x0)

        p, r = leastsq(func, x0, **leastsq_kwargs)
        try:
            p[0]
        except IndexError:
            p=(p,)         # put single value (scalar) back into a tuple ...

        par_iHere=0
        pp=N.empty(len(parmTuple0), float)
        for par_i,par_fixed in enumerate(fixed_mask):
            if par_fixed:
                pp[par_i] = parmTuple0[par_i]
            else:
                pp[par_i] = p[par_iHere]
                par_iHere+=1
        return pp,r  # pp is N.array, like what  leastsq seems to return
            
    #return leastsq(func, x0)#, args=(), Dfun=None,
                   #full_output=0, col_deriv=0,
                   #ftol=1.49012e-08, xtol=1.49012e-08, gtol=0.0, maxfev=0, epsfcn=0.0, factor=100, diag=None)
    
def fitDecay(data, p=(1000,10000,10), fixed_mask=None, **leastsq_kwargs):
    """
    see yDecay.
    p: initial guess
    data: vector of data points to be fit

    if fixed_mask is not None: 
       this sequence of bool values determinces if the respective parameter
       shall be fixed or free to be adjusted
    """
    return fitAny(yDecay, p, data, fixed_mask=fixed_mask, **leastsq_kwargs)

def fitGaussian(data, p=(0,10,100), fixed_mask=None, **leastsq_kwargs):
    """
    see yGaussian.
    p: initial guess
    data: vector of data points to be fit

    if fixed_mask is not None: 
       this sequence of bool values determinces if the respective parameter
       shall be fixed or free to be adjusted
    """
    return fitAny(yGaussian, p, data, fixed_mask=fixed_mask, **leastsq_kwargs)
#     from scipy.optimize import leastsq
    
#     n = len(y)
#     x = N.arange(n)
    
#     def func(p):
#         return yDecay(p, x)-y
    
#     x0 = p
#     return leastsq(func, x0)#, args=(), Dfun=None,
#                    #full_output=0, col_deriv=0,
#                    #ftol=1.49012e-08, xtol=1.49012e-08, gtol=0.0, maxfev=0, epsfcn=0.0, factor=100, diag=None)


def fitPoly(data, p=(1,1,1), fixed_mask=None, **leastsq_kwargs):
    """
    see yPoly

    data should be list of y or (x,y)- or (x,y,deltaY)-tuples
    (instead of 'list' you can of course have an array w/
    shape=(n,2) or shape=(n,3), n beeing the number of data points

    uses polynomial 'model' ( U.yPoly )
    
    The function returns a list containing the optimal parameter values
    and the chi-squared value describing the quality of the fit.

    if fixed_mask is not None: 
       this sequence of bool values determinces if the respective parameter
       shall be fixed or free to be adjusted
    """

    return fitAny(yPoly, p, data, fixed_mask=fixed_mask, **leastsq_kwargs)

























def nd__center_of_mass(input, labels = None, index = None):
    """Calculate the center of mass of of the array.

    The index parameter is a single label number or a sequence of
    label numbers of the objects to be measured. If index is None, all
    values are used where labels is larger than zero.

    Seb: this is from scipy.ndimage, but returns ndarray and
    fixes return value type & shape
    for the cases  len(index) == 1 and len(index) == 0
    """
    ll = hasattr(index, "__len__")
    if ll and len(index) == 0:
        r = N.array([])
        r.shape=0,input.ndim
        return r
    r = N.array( nd.center_of_mass(input, labels, index) )
    if ll and len(index) == 1:
        r.shape = (1, -1)
    return r
#         r = [ r ]
#     return N.array( r )
def nd__maximum_position(input, labels = None, index = None):
    """Find the position of the maximum of the values of the array.

    The index parameter is a single label number or a sequence of
    label numbers of the objects to be measured. If index is None, all
    values are used where labels is larger than zero.

    Seb: this is from scipy.ndimage, but returns ndarray and
    fixes return value type & shape
    for the cases  len(index) == 1 and len(index) == 0
    """
    ll = hasattr(index, "__len__")
    if ll and len(index) == 0:
        r = N.array([])
        r.shape=0,input.ndim
        return r
    r = N.array( nd.maximum_position(input, labels, index) )
    if ll and len(index) == 1:
        r.shape = (1, -1)
    return r
#         r = [ r ]
#     return N.array( r )
def nd__minimum_position(input, labels = None, index = None):
    """Find the position of the minimum of the values of the array.

    The index parameter is a single label number or a sequence of
    label numbers of the objects to be measured. If index is None, all
    values are used where labels is larger than zero.

    Seb: this is from scipy.ndimage, but returns ndarray and
    fixes return value type & shape
    for the cases  len(index) == 1 and len(index) == 0
    """
    ll = hasattr(index, "__len__")
    if ll and len(index) == 0:
        r = N.array([])
        r.shape=0,input.ndim
        return r
    r = N.array( nd.minimum_position(input, labels, index) )
    if ll and len(index) == 1:
        r.shape = (1, -1)
    return r
#         r = [ r ]
#     return N.array( r )
def nd__sum(input, labels=None, index=None):
    """Calculate the sum of the values of the array.

    :Parameters:
        labels : array of integers, same shape as input
            Assign labels to the values of the array.

        index : scalar or array
            A single label number or a sequence of label numbers of
            the objects to be measured. If index is None, all
            values are used where 'labels' is larger than zero.

    Examples
    --------

    >>> input =  [0,1,2,3]
    >>> labels = [1,1,2,2]
    >>> sum(input, labels, index=[1,2])
    [1.0, 5.0]

    Seb: this is from scipy.ndimage, but returns ndarray and
    fixes return value type & shape
    for the cases  len(index) == 1 and len(index) == 0
    """
    ll = hasattr(index, "__len__")
    if ll and len(index) == 0:
        r = N.array([])
        r.shape=0,input.ndim
        return r
    r = N.array( nd.sum(input, labels, index) )
    if ll and len(index) == 1:
        r.shape = (-1)
    return r
#         r = [ r ]
#     return N.array( r )





def noiseSigma(arr, backgroundMean=None):
    """ask Erik"""
    from numarray import nd_image as nd
    if backgroundMean is None:
        m = arr.mean() #20040707 nd.mean(arr)
        #       s = nd.standard_deviation(arr)
        #       nd.standard_deviation(d, d<m+s)
    else:
        m=backgroundMean
    mm = nd.mean(arr, labels=arr<m, index=None) - m

    #ask Erik:
    return N.sqrt( (mm**2) * N.pi * .5 )

def signal2noise(arr):
    from numarray import nd_image as nd
    ma = nd.maximum(arr)

    m = nd.mean(arr)
    #       s = nd.standard_deviation(arr)
    #       nd.standard_deviation(d, d<m+s)
    mm = nd.mean(arr, labels=arr<m, index=None) - m

    sigma = N.sqrt( (mm**2) * N.pi * .5 )
    #from Priithon import seb as S
    #print "debug:", S.median(arr)
    #from numarray import image
    #global med
    #med = arr
    #while not type(med) == type(1) or med.ndim > 0:
    #     med = image.median(med)
    #med = image.median(N.ravel(arr))
    #print "debug:", med
    print "debug - mean: %s      max: %s  meanLeft: %d     sigma: %s" %( m, ma, mm, sigma)
    return (ma-m) / sigma


def interpolate1d(x0, y, x=None):
    """
    assume a function f(x) = y
    defined by value-pairs in y,x
    evaluate this at x=x0

    note: x0 does not need to be one of the given values in x

    if x is None: use N.arange(len(y))

    more repeated evaluations 
    this is slow - because it remakes the spline fit every time
    """
    import scipy.interpolate
    if x is None:
        x = N.arange(len(y))
    else:
        ii = N.argsort(x)
        x = x[ii]
        y = y[ii]

    rep = scipy.interpolate.splrep(x, y, 
                                   w=None, xb=None, xe=None, 
                                   k=3, task=0, s=0.001, t=None, 
                                   full_output=0, per=0, quiet=1)

    return scipy.interpolate.splev(x0,rep)
        





def histogram(a, nBins=None, amin=None,amax=None, histArr=None, norm=False, cumsum=False, returnTuple=False, exclude_amax=False):
    """
    creates/returns  array with nBins int32 entries
       fills it with histogram of 'a'
    if amin and/or amax is None it calculates the min/max of a and uses that
    if nBins is None:
        nBins = int(amax-amin+1)
        if narr is of float dtype  Bins < 100:
            nBins = 100
    if histArr is given it is used to fill in the histogram values
        then nBins must be None and histArr of dtype N.int32

    if norm:
       divide bins (=histArr) by sum of bins and convert to float64
    if cumsum:
       calculate cumulative histogram (apply N.cumsum)
       if norm: normalize so that rightmost bin will be 1
    if returnTuple:
        return (histArr, nBins, amin, amax)
    if exclude_amax:
        last bin starts at amax
    else:  last bin ends at amax, values equal amax are NOT counted
    """
    a = N.asarray(a)
    
    if amin is None and amax is None:
        amin = a.min()  
        amax = a.max()
    elif amin is None:
        amin = a.min()
    elif amax is None:
        amax = a.max()

    if histArr is not None:
        if nBins is not None:
            raise ValueError("only one of histArr and nBins can be given")
        if histArr.dtype != N.int32:
            raise ValueError("histArr must of dtype N.int32")
        if not histArr.flags.carray or  not histArr.dtype.isnative:
            raise ValueError("histArr must be a 'native c(ordered)-array'")
        nBins = len(histArr)
    else:
        if nBins is None:
            nBins = int(amax-amin+1)
            if N.issubdtype(float, a.dtype) and nBins < 100:
                nBins = 100

        histArr = N.empty( shape=(nBins,), dtype=N.int32 )

        #a = _getGoodifiedArray(a)

    # NOTE: S.histogram *ignores* all values outside range (it does not count amax !!)
    #       it only count amin<= val < amax

    if exclude_amax:
        amaxTweaked = amax
    else:
        amaxTweaked = amin+nBins*(amax-amin)/(nBins-1.)
    # CHECK numpy - why type(a.min())=numpy.float32 not SWIG compatible to float!
    #S.histogram(a, float(amin),float(amaxTweaked), histArr)
    histArr, xs = N.histogram(a, nBins, range=(float(amin), float(amaxTweaked)))

    if norm:
        histArrNormed = N.empty( shape=(nBins,), dtype=N.float64 )
        histArrNormed[:] = histArr
        # if cumsum:
        #     binWidth = (float(amaxTweaked)-float(amin))/nBins
        #    normFac = binWidth / histArr.sum()
        #else:
        #    normFac = 1./ histArr.sum()
        #histArrNormed *= normFac
        histArrNormed /= histArrNormed.sum()
        histArr = histArrNormed

    if cumsum:
        histArr.cumsum(out=histArr)


    if returnTuple:
        return (histArr, nBins, amin, amax)
    else:
        return histArr

def histogramXY(a, nBins=None, amin=None,amax=None, histArr=None, norm=False, cumsum=False, exclude_amax=False):
    """
    returns flipped version of histogramYX
    use this e.g. in
     Y.plotxy( U.histogramXY( a ) )
    """ 
    b,x = histogramYX(a, nBins, amin,amax, histArr, norm, cumsum, exclude_amax)
    return x,b

# 20161214 py2exe did not allow this...
#histogramXY.__doc__ += '\n' + histogram.__doc__
def histogramYX(a, nBins=None, amin=None,amax=None, histArr=None, norm=False, cumsum=False, exclude_amax=False):
    """
    returns same as U.histogram
    but also a "range array" amin,...amax with nBins entries
    """

    b,nBins,amin,amax = histogram(a,nBins,amin,amax, histArr, norm=norm, cumsum=cumsum, returnTuple=True, exclude_amax=exclude_amax)
    if norm:
        x,step = N.linspace(amin,amax, nBins, endpoint=not exclude_amax, retstep=True)
        if not cumsum:
            b /= float(step)

    else:
        x = N.linspace(amin,amax, nBins, endpoint=not exclude_amax)

    return b, x
#histogramYX.__doc__ += '\n' + histogram.__doc__

def generalhistogram(a, weightImg, nBins=None, amin=None,amax=None):
    """
    creates/returns ("histogram") array with nBins entries of same dtype as weightImg
    while for a standard histogram one adds up 1s in bins for
          each time you encouter a certain value in a
    generalhistogram  adds the pixel value found in weightImg 
          each time it encouters a certain value in a (for that pixel)
    
    if amin and/or amax is None it calculates the min/max of a and uses that
    if nBins is None:
        nBins = int(amax-amin+1)
        if a is of float dtype   and nBins < 100:
             nBins = 100
    """
    if amin is None and amax is None:
        amin = a.min()
        amax = a.max()
    elif amin is None:
        amin = a.min()
    elif amax is None:
        amax = a.max()

    if nBins is None:
        nBins = int(amax-amin+1)
        if N.issubdtype(float, a.dtype) and nBins < 100:
            nBins = 100
    b = N.empty( shape=(nBins,), dtype=weightImg.dtype )

    a = _getGoodifiedArray(a)
    weightImg = _getGoodifiedArray(weightImg)

    # NOTE: S.histogram *ignores* all values outside range (it does not count amax !!)
    #       it only count amin<= val < amax
    
    amaxTweaked = amin+nBins*(amax-amin)/(nBins-1.)
    # CHECK numpy - why type(a.min())=numpy.float32 not SWIG compatible to float!
    S.generalhist(a, weightImg, float(amin),float(amaxTweaked), b)

    return b
    

def topPercentile(img, percentile=1):
    """find Intens. for highest percentile

        slow!! ****** might only work for uint16 arr *********
    """
    a = N.empty( shape=(1<<16), dtype=N.int32 ) # bins
    (mi,ma,mean,stddev) = S.histogram2(img, 0, (1<<16), a)
    nPix = N.prod( img.shape )


    a = _getGoodifiedArray(a)

    tp = S.toppercentile(a, nPix, int(ma), percentile)
    return tp

'''
def ffta(img):
    if len(img.shape) != 2:
        raise "2d only"


    import numarray as na
    from numarray import fft

    #f = fft.fft2d(img)
    #fr = na. abs( fft.real_fft2d(img).astype(na.Float32) ) 
    #if img.type

    fa = fft.fft2d(img).astype(na.Complex32) # fixme single float fft ?
    fa = na.abs(fa) # we want Float     - copy...
    na.log10(fa,fa)
    fa[0,0] = 1
    return fa

def fftc(img):
    if len(img.shape) != 2:
        raise "2d only"


    import numarray as na
    from numarray import fft

    #f = fft.fft2d(img)
    #fr = na. abs( fft.real_fft2d(img).astype(na.Float32) ) 
    #if img.type

    fa = fft.fft2d(img).astype(na.Complex32) # fixme single float fft ?
    #na.abs(fa, fa)
    #na.log10(fa,fa)
    fa[0,0] = 0
    return fa
def fftcinv(img):
    if len(img.shape) != 2:
        raise "2d only"


    import numarray as na
    from numarray import fft

    #f = fft.fft2d(img)
    #fr = na. abs( fft.real_fft2d(img).astype(na.Float32) ) 
    #if img.type

    fa = fft.inverse_fft2d(img).astype(na.Complex32) # fixme single float fft ?
    #na.abs(fa, fa)
    #na.log10(fa,fa)
    fa[0,0] = 0
    return fa
'''
def l2norm(a):
    """
    return the euclidian length of vector a
    return N.sqrt(a**2).sum())
    """
    a = N.asarray(a)
    return N.sqrt(a**2).sum()

def l1norm(a):
    """
    return the "abs"-norm of vector a
    return N.sum(abs(a))
    """
    a = N.asarray(a)
    return N.sum(abs(a))

def rms(a):
    """
    returns root mean square (aka. the quadratic mean):
        (a**2).mean()**.5
    http://en.wikipedia.org/wiki/Root_mean_square
    """
    a = N.asanyarray(a)  # CHECK asanyarray or asarray
    return (a**2).mean()**.5


def phase(a):
    """
    returns N.arctan2(a.imag, a.real)
    """
    return N.arctan2(a.imag, a.real)

def polar2cplx(aAbs,aPhase):
    """
    returns new complex array 'a' with
    a.real = aAbs * N.cos(aPhase)
    a.imag = aAbs * N.sin(aPhase)
    """
    if aAbs.dtype.type == N.float32:
        dtype = N.complex64
    else:   # HACK FIXME
        dtype = N.complex128

    a = N.empty(shape=aAbs.shape, dtype=dtype)
    a.real[:] = aAbs * N.cos(aPhase)
    a.imag[:] = aAbs * N.sin(aPhase)
    return a



def rot90(a, n):
    """return a.copy() rotated
    n == 1 --> counter-clockwise
    n == 2 --> 180 degrees
    n == 3 --> clockwise
    n ==-1 --> clockwise
    """
    if n == 2:
        b = a.copy()
        return b[::-1,::-1]
    else:
        b = N.transpose( a )
        if n == 1:
            return b[::-1]
        elif n==3 or n==-1:
            return b[:,::-1]
    raise ValueError, "cannot rotated with n == %s"%n
    

def project(a, axis=0):
    """
    returns maximum projection along given [old: 'first'(e.g. z)] axis
    """
    if axis < 0:
        axis += a.ndim
    return N.maximum.reduce(a, axis)


def insert(arr, i, entry, axis=0):
    """returns new array with new element inserted at index i along axis
    if arr.ndim>1 and if entry is scalar it gets filled in (ref. broadcasting)

    note: (original) arr does not get affected
    """
    if i > arr.shape[axis]:
        raise IndexError, "index i larger than arr size"
    shape = list(arr.shape)
    shape[axis] += 1
    a= N.empty(dtype=arr.dtype, shape=shape)
    aa=N.transpose(a, [axis]+range(axis)+range(axis+1,a.ndim))
    aarr=N.transpose(arr, [axis]+range(axis)+range(axis+1,arr.ndim))
    aa[:i] = aarr[:i]
    aa[i+1:] = aarr[i:]
    aa[i] = entry
    return a


#######################################################################
######### stuff that works with float32 array (was: ... that uses Bettina's FORTRAN)
#######################################################################

def trans2d(inArr, outArr, (tx,ty,rot,mag,gmag2_axis,gmag2)):
    """
    first translates by tx,ty
    THEN rotate and mag and aniso-mag
        (rotation relative to img-center !
         positive angle moves object counter-clockwise)

    if outArr is None ret
    NOTE: tx,ty go positive for right/up
    (bettinas Fortran goes left/down !!!) 
"""
    # , (tx=0,ty=0,rot=0,mag=1,gmag2_axis=0,gmag2=1)):
    ret = 0
    if outArr is None:
        outArr = N.empty(shape=inArr.shape, dtype=N.float32)
        ret = 1
    #checkGoodArrayF(outArr, 1, inArr.shape)

    #inArr = _getGoodifiedArray(inArr)

    #S.trans2d(inArr,outArr,(-tx,-ty,  rot,mag, gmag2_axis,gmag2) )
    temp = nd.shift(inArr, (tx, ty), order=0, prefilter=None)
    temp = nd.rotate(inArr, -rot, order=0, prefilter=None)
    if gmag2 != 1.0:
        if gmag2_axis == 0:
            mag = (gmag2, mag)
        else:
            mag = (mag, gmag2)
    outArr = nd.zoom(inArr, mag, order=0, prefilter=None)

    if ret:
        return outArr

def trans2d(inArr, outArr, (tx,ty,rot,mag,gmag2_axis,gmag2)):
    """
    first translates by tx,ty
    THEN rotate and mag and aniso-mag
        (rotation relative to img-center !
         positive angle moves object counter-clockwise)

    if outArr is None ret
    NOTE: tx,ty go positive for right/up
    (Bettina's Fortran goes left/down !!!) 
"""
    # , (tx=0,ty=0,rot=0,mag=1,gmag2_axis=0,gmag2=1)):
    ret = 0
    if outArr is None:
        outArr = N.empty(shape=inArr.shape, dtype=N.float32)
        ret = 1

    if 0:#S:
        checkGoodArrayF(outArr, 1, inArr.shape)

        inArr = _getGoodifiedArray(inArr)

        S.trans2d(inArr,outArr,(-tx,-ty,  rot,mag, gmag2_axis,gmag2) )

    else:
        # use spline method
        # be careful! nd.zoom only magnify pixelwise...
        if tx or ty:
            nd.shift(inArr, (tx, ty), outArr, order=1, prefilter=None)
            inArr = outArr.copy()
        if rot:
            nd.rotate(inArr, -rot, output=outArr, reshape=False, order=1, prefilter=None)
            inArr = outArr.copy()
        if mag != 1.0 or gmag2 != 1.0:
            if gmag2 != 1.0:
                if gmag2_axis == 0:
                    mag = (gmag2*mag, mag)
                else:
                    mag = (mag, gmag2*mag)
            outArr = nd.zoom(inArr, mag, order=1, prefilter=None)
            outArr = keepShape(outArr, inArr.shape)
        
    
    if ret:
        return outArr

def keepShape(a, shape):#, difmod=None):
    canvas = N.zeros(shape, a.dtype.type)

    #if difmod is None:
    dif = (shape - N.array(a.shape, N.float32)) / 2.
    mod = N.ceil(N.mod(dif, 1))
    #else:
    #    dif, mod = difmod
    #dif = N.where(dif > 0, N.ceil(dif), N.floor(dif))

    # smaller
    aoff = N.where(dif < 0, 0, dif)
    aslc = [slice(dp, shape[i]-dp+mod[i]) for i, dp in enumerate(aoff)]

    # larger
    coff = N.where(dif > 0, 0, -dif)
    cslc = [slice(dp, a.shape[i]-dp+mod[i]) for i, dp in enumerate(coff)]

    canvas[aslc] = a[cslc]

    #if difmod is None:
    #    return canvas, mod
    #else:
    return canvas

def translate2d(a,b,tx,ty):
    """ shift a in to b

    use bi-linear interpolation

    if b is None
      output array b is allocated and returned

    NOTE: tx,ty go positive for right/up
    (bettina's Fortran goes left/down !!!) 
    """
    rot,gmag,axis,gmag2 = 0, 1,0,1
    return trans2d(a,b,(tx,ty,  rot,gmag,axis,gmag2) )

def transmat2d(a,b,tx,ty, m11,m12,m21,m22, tx2=0,ty2=0):
    """
    transform a(input) into b(output) :
    first translates by tx,ty
    THEN apply rotate/skew
        (rotation relative to img-center !
         positive angle moves object counter-clockwise)

    (m11 m12)  is the 2d transformation matrix
    (m21 m22) 

    use bi-linear interpolation

    NOTE: tx,ty go positive for right/up
    (bettinas Fortran goes left/down !!!)

    tx2,ty2 is for an extra translating ?? before OR after ?>??
    """
    checkGoodArrayF(b, 1, a.shape)

    ny,nx = a.shape
    #20050502  # now we have a '-' here !!!!
    xc = (nx - 1.)*.5 + -tx  # ! Center of image.
    yc = (ny - 1.)*.5 + -ty

    a = _getGoodifiedArray(a)

    S.binterp2d(a,b, (m11,m12,m21,m22), xc,yc,  tx2,ty2)



def rot3d(a,b, angle, rot_axis=0):
    """ angle: in degree,
        rot_axis: axis to rotate the object about"""

    checkGoodArrayF(b, 1, a.shape)
    a = _getGoodifiedArray(a)
    
    cdr = N.arctan(1)/ 45.
    c = N.cos(angle*cdr)
    s = N.sin(angle*cdr)

    tx=ty=tz=0

    if a.ndim == 2:
        a = a.view()
        b = b.view()        
        b.shape = a.shape = (1,) + a.shape

    xoff=0.5*(a.shape[2]-1)
    yoff=0.5*(a.shape[1]-1)
    zoff=0.5*(a.shape[0]-1)
    xc=xoff+tx                                    # Shift by -xt, -yt,-zt.
    yc=yoff+ty
    zc=zoff+tz 

    if rot_axis==0:
        S.rot3d(a,b,
                ( c,-s, 0,
                  s, c, 0,
                  0, 0, 1),
                1, xoff,yoff,zoff,xc,yc,zc)
    elif rot_axis==1:
        S.rot3d(a,b,
                ( c, 0, s,
                  0, 1, 0,
                 -s, 0, c),
                1, xoff,yoff,zoff,xc,yc,zc)
    elif rot_axis==2:
        S.rot3d(a,b,
                ( 1, 0, 0,
                  0, c,-s,
                  0, s, c),
                1, xoff,yoff,zoff,xc,yc,zc)
    else:
        print "*** bad rot_axis ***"
        

#######################################################################
######### stuff that used PIL
#######################################################################

def _getImgMode(im):
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
        raise ValueError, "can only convert single-layer images (mode: %s)" % (im.mode,)

    nx,ny = im.size
    import sys
    isSwapped = (BigEndian and sys.byteorder=='little' or not BigEndian and sys.byteorder == 'big')
        
    return t,cols, ny,nx, isSwapped


def image2array(im, i0=0, iDelta=1, squeezeGreyRGB=True):
    """
    Convert image to numpy array

    if i0 is None:
           just read next section (no im.seek !) and 
           convert and return 2d array 
    if squeezeGreyRGB:
       test if an RGB (RGBA) image really just grey - 
         then return only one channel (others are identical)
    """
    
    #import Image

    if i0 is not None:
        #HACK for multipage images
        nn = 0
        for i in xrange(i0, 100000, iDelta):
            try:
                im.seek(i)
                nn+=1
            except EOFError:
                break
        #def getLayerlayerToArray

        im.seek(i0) # CHECK: PIL docs say, only forward seeks are supported - (but seems to work anyway 200808)
    t,cols,ny,nx,isSwapped = _getImgMode(im)

    if i0 is None or nn == 1:
        #global a
        a = N.fromstring(im.tobytes(), t)#tostring(), t)
        if cols == -1:
            raise NotImplementedError, "TODO: bit array: image size: %s  but array shape: %s" % (im.size, a.shape)
            # s = im.size[0]
            # return a
           
        elif cols>1:
            s = ( ny, nx, cols)
            #print "# multi color image [PIL mode: '%s']: orig shape=%s" % (im.mode,s), \
            #" --> return transposed! "
            a.shape = s
            a=a.transpose((2,0,1))
            #special treatment of "grey scale" images saved as RGB or RGBA
            if squeezeGreyRGB:
                if cols==3:
                    if (a[0] == a[1]).all() and \
                       (a[0] == a[2]).all():
                        a=a[0]
                elif cols==4:
                    if (a[0] == a[1]).all() and \
                       (a[0] == a[2]).all() and \
                       (a[0] == a[3]).all() or (a[3] == 0).all():  # CHECK
                        a=a[0]
            a=a.copy() # just copy() to get contiguous   
        else:
           a.shape = ( ny, nx )
    else:
        if cols == -1:
            raise NotImplementedError, "TODO a: bit array: image size: %s" % (im.size,)
        if cols > 1:
            a = N.empty(shape=(nn, cols, ny, nx), dtype=t)
            for i in range(nn):
                im.seek(i0+iDelta*i)
                x = N.fromstring(im.tobytes(), t)#tostring(), t)
                x.shape = (ny, nx, cols)
                a[i] = x.transpose((2,0,1))
        else:
            a = N.empty(shape=(nn, ny, nx), dtype=t)
            for i in range(nn):
                im.seek(i0+iDelta*i)
                x = N.fromstring(im.tobytes(), t)#tostring(), t)
                x.shape = (ny, nx)
                a[i] = x
        

    if isSwapped:
        a.byteswap(True)
        
    return a


def array2image(a, rgbOrder="rgba"):
    """Convert numpy array to image
       a must be of ndim 2 and dtype UInt8,Float32 or UInt16
       if a.ndim ==3:
          a.dtype must be uint8
          the first axis is interpreted as RGB color axis -- for fewer "sections" in a, remaining are assumed to be zero
          rgbOrder: order in which axes are mapped to RGB(A) channels
    """
    #import Image

    # translate string to "inverse map" aAxis->rgbaIndex
    # e.g. "br" -> [1, 2, 0, 3]
    rgbOrder = rgbOrder.lower()
    rgbOrder = [rgbOrder.find(col) for col in "rgba"]
    fillAx=max(rgbOrder)+1
    for i,ax in enumerate(rgbOrder):
        if ax<0:
            rgbOrder[i] = fillAx
            fillAx+=1

    if a.ndim == 3:
        if   a.shape[0] == 1:
            assert a.dtype==N.uint8
            a22 = N.transpose(a,(1,2,0)) # .copy()
            import fftfuncs as F
            a22 = N.append(a22,F.zeroArr(a22.dtype,a22.shape[:2]+(2,)), -1)
            a22 = a22[:,:,rgbOrder[:3]]
            ii = Image.frombytes("RGB", (a.shape[-1],a.shape[-2]), a22.tostring())
            return ii
        elif   a.shape[0] == 2:
            assert a.dtype==N.uint8
            a22 = N.transpose(a,(1,2,0)) # .copy()
            import fftfuncs as F
            a22 = N.append(a22,F.zeroArr(a22.dtype,a22.shape[:2]+(1,)), -1)
            a22 = a22[:,:,rgbOrder[:3]]
            ii = Image.frombytes("RGB", (a.shape[-1],a.shape[-2]), a22.tostring())
            return ii
        elif a.shape[0] == 3:
            assert a.dtype==N.uint8
            a22 = N.transpose(a,(1,2,0)) # .copy()
            a22 = a22[:,:,rgbOrder[:3]]
            ii = Image.frombytes("RGB", (a.shape[-1],a.shape[-2]), a22.tostring())
            return ii
        elif a.shape[0] == 4:
            assert a.dtype==N.uint8
            a22 = N.transpose(a,(1,2,0)) # .copy()
            a22 = a22[:,:,rgbOrder[:4]]
            ii = Image.frombytes("RGBA", (a.shape[-1],a.shape[-2]), a22.tostring())
            return ii
        else:
            raise ValueError, "only 2d greyscale or 3d (RGB[A]) supported"
    # else:  (see return above)
    if a.ndim != 2: 
        raise ValueError, "only 2d greyscale or 3d (RGB[A]) supported"

    if a.dtype.type == N.uint8:
        mode = "L"
    elif a.dtype.type == N.float32:
        mode = "F"
    elif a.dtype.type in ( N.int16, N.uint16 ):
        mode = "I;16"
    else:
        raise ValueError, "unsupported array datatype"
    return Image.frombytes(mode, (a.shape[1], a.shape[0]), a.tostring())
    #20040929 todo: try this:   return Image.frombuffer(mode, (a.shape[1], a.shape[0]), a._data)


def load(fn):
    """open any image file:
          '.fits'  - FITS files
          '.sif'   - Andor SIF files
          '.his'   - Hamamatsu HIS files
          '.lsm'   - Zeiss LSM images are read like TIFF; skipping every other slice (thumbnail)
          any image file: jpg/bmp/png/... (all PIL formats)
               #20060824 CHECK  in this case the returned arr gets attr: arr._originLeftBottom=0
          'Mrc' (use Mrc.bindFile)
          TODO: "_thmb_<fn.jpg>" files are taken to mean <fn.jpg>
       returns image array
               None on error

       if imgFN is None  call Y.FN()  for you
    """
    if fn[-5:].lower() == ".fits":
        #import useful as U
        a = loadFits( fn )
    elif fn[-4:].lower() == ".sif":
        #import useful as U
        a = loadSIF( fn )
    elif fn[-4:].lower() == ".his":
        #import useful as U
        a = loadHIS( fn )
    else:
        try:
            iDelta = 1
            if fn[-4:].lower() == ".lsm":
                iDelta=2 # LSM-Zeiss every 2nd img is a thumbnail
            #import useful as U
            a = loadImg(fn, iDelta=iDelta)
            #20060824 CHECK  a._originLeftBottom=0
        except (IOError, SystemError, ImportError): # ImportError for Image
            import Mrc
            a = Mrc.bindFile(fn)

    return a
    

def loadImg(fn, i0=0, iDelta=1, squeezeGreyRGB=True):
    """Loads image file (tiff,jpg,...) and return it as array

    if squeezeGreyRGB:
       test if an RGB (RGBA) image really just grey - 
         then return only one channel (others are identical)

    !!be careful about up-down orientation !!
    """

    #global im
    #import Image
    im = Image.open(fn)
    return image2array(im, i0, iDelta, squeezeGreyRGB)

def loadImg_iterSec(fn, i0=0, iDelta=1, squeezeGreyRGB=True):
    """
    iterator:
    Loads image file (tiff,jpg,...) and 
    iterate section-wise yielding a 2d array
    """
    #import Image
    im = Image.open(fn)
    for i in xrange(i0, 100000, iDelta):
        try:
            im.seek(i)

            yield image2array(im, None, iDelta, squeezeGreyRGB)
        except EOFError:
            return

def loadImg_seq(fns, channels=None, verbose=0): #### #, i0=0, iDelta=1, squeezeGreyRGB=True):
    """
    Open multiple TIFF-files into a 3-(or 4-)D numpy stack.

    fns is a list of filenames or a glob-expression
    channels:
      specify 0 for R
              1 for G
              2 for B
              list of above for mnore than one
              None for all
      returned shape is (nz, nChannels,ny,nx) if a list/tuple was given
      returned shape is (nz, ny,nx) if a scalar was given
      if channels is None: one of the above is choosen depending on nChannels==1
    """
    import glob, Image
    if type(fns) is not type([]):
        fns = glob.glob( fns )
        fns.sort()

    n = len(fns)
    #print n
    #print fns

    fn = fns[0]
    im = Image.open(fn)
    dtype,cols, ny,nx,isSwapped = _getImgMode(im)
    del im

    if cols > 1:
        if hasattr(channels, "__len__"):
            # ensure list-type so that it can be used for fancy indixing
            channels = list(channels)
            shape = (n,len(channels),ny,nx)
        else:
            if channels is None:
                channels = range(cols)
            else:
                channels = [channels]
            if len(channels) == 1:
                shape = (n,ny,nx)
            else:
                shape = (n,len(channels),ny,nx)


        if channels is None:
            channels = range(cols)
        elif not hasattr(channels, "__len__"):
            channels = [channels]
        else:
            channels = list(channels)

    else:
        if channels is not None:
            raise ValueError, "`channels` can not be specified for one color images"
        shape = (n,ny,nx)
        
    a = N.zeros(dtype=dtype, shape=shape)
        

    for i,fn in enumerate(fns):
        if verbose:
            print i,
            from Priithon.all import Y
            Y.refresh()

        im = Image.open(fn)
        ##be more robust: 
        aa = loadImg(fn, squeezeGreyRGB=False)
        #         dtype2,cols2, ny2,nx2 = U._getImgMode(im)
        #         aa = image2array(im)
        if cols > 1:
            #             if cols2 == 1:
            #                 # what now: we just put data into channels[0] - set others to 0
            #                 aa = aa[channels]
            #             else:
            aa = aa[channels]
        a[i] = aa

    if verbose:
        print 
        Y.refresh()

    if isSwapped:
        a.byteswap(True)

    return a


def saveImg(arr, fn, forceMultipage=False, rgbOrder="rgba"):
    """
    Saves data array as image file (format from    extension !! .tif,.jpg,...)
    tries to use number format of 'arr'
    also supports multipage TIFF:
        3D arrays: grey (if more than 4 z-secs or forceMultipage==True)
        4D arrays: color (second dim must be of len 2..4 (RG[B[A]]))

    for multi-color images:
         rgbOrder: order in which axes are mapped to RGB(A) channels
      
    !!be careful about up-down orientation !!
    """

    arr = N.asarray(arr)
    if (arr.ndim == 3 and (len(arr)>4 or forceMultipage)) or \
            arr.ndim == 4:
        return saveTiffMultipage(arr, fn, rescaleTo8bit=False, rgbOrder=rgbOrder)

    im = array2image(arr, rgbOrder)
    im.save(fn)

def _saveSeq_getFixedFN(fn, n):
    """
    check that fn contains a '%02d'-like part'
    autofix if necessary (add enough digits to fit n filenames)
    """
    try:
        __s = fn % 1 # test if fn contains '%d'
    except TypeError:
        import os
        fnf = os.path.splitext(fn)
        fns = '_%0' + '%d'%(int(N.log10(n-1))+1) +'d'
        fn = fnf[0] + fns + fnf[1]
    return fn

def saveImg_seq(arr, fn, rgbOrder="rgba"):
    """
    Saves 3D data array as 8-bit gray image file sequence (format from  extension !! .tif,.jpg,...)
    filename should contain a "template" like %02d - use '%%' otherwise inplace of single '%'
    template gets replaced with 00,01,02,03,...

    for multi-color images:
         rgbOrder: order in which axes are mapped to RGB(A) channels
      
    !!be careful about up-down orientation !!
    """
    arr = N.asarray(arr)
    #if arr.ndim != 3:
    #    raise "can only save 3d arrays"
    if not (arr.ndim == 3 or (arr.ndim == 4 and arr.shape[1] in (1,2,3,4))):
        raise ValueError, "can only save 3d arrays or 4d with second dim of len 1..4 (RG[B[A]])"

    fn = _saveSeq_getFixedFN(fn, len(arr))

    for i in range(arr.shape[0]):
        saveImg(arr[i], fn % i, rgbOrder=rgbOrder)

def saveImg8(arr, fn, forceMultipage=False, rgbOrder="rgba"):
    """
    Saves data array as 8-bit gray image file (format from  extension !! .tif,.jpg,...)
    be careful about up-down orientation !!
    if arr.dtype is not N.uint8  arr gets rescaled to 0..255
    also supports multipage TIFF:
        arr gets rescaled to 0..255 to match min..max of entire stack
        3D arrays: grey (if more than 4 z-secs or forceMultipage==True)
        4D arrays: color (second dim must be of len 2..4 (RG[B[A]]))

    for multi-color images:
         rgbOrder: order in which axes are mapped to RGB(A) channels
      
    !!be careful about up-down orientation !!
    """

    arr = N.asarray(arr)
    if (arr.ndim == 3 and (len(arr)>4 or forceMultipage)) or \
            arr.ndim == 4:
        return saveTiffMultipage(arr, fn, rescaleTo8bit=True, rgbOrder=rgbOrder)

    if not (arr.ndim == 2 or (arr.ndim == 3 and arr.shape[0] in (1,2,3,4))):
        raise ValueError, "can only save 2d greyscale or 3d (RGB[A]) arrays"
    
    if arr.dtype.type != N.uint8:
        mi,ma = float(arr.min()), float(arr.max())
        ra = ma-mi
        arr = ((arr-mi)*255./ra).astype(N.uint8)

    #import Image
    im8 = array2image(arr, rgbOrder)
    #20050711 im8= im.convert("L")
    im8.save(fn)

def saveImg8_seq(arr, fn, rgbOrder="rgba"):
    """
    Saves 3D data array as 8-bit gray image file sequence (format from  extension !! .tif,.jpg,...)
    filename must contain a "template" like %02d - use '%%' otherwise inplace of single '%'
    template gets replaced with 00,01,02,03,...

    arr gets rescaled to 0..255 to match min..max of entire stack

    for multi-color images:
         rgbOrder: order in which axes are mapped to RGB(A) channels
      
    !!be careful about up-down orientation !!
    """
    arr = N.asarray(arr)
    if arr.ndim != 3:
        raise ValueError, "can only save 3d arrays"

    fn = _saveSeq_getFixedFN(fn, len(arr))

    mi,ma = float(arr.min()), float(arr.max())
    ra = ma-mi
    for i in range(arr.shape[0]):
        a=(arr[i]-mi)*255./ra
        saveImg(a.astype(N.uint8), fn % i, rgbOrder=rgbOrder)

def loadFits(fn, slot=0):
    """
    Loads FITC file and return it as array
    """
    import pyfits
    ff = pyfits.open(fn)
    return ff[ slot ].data

def loadHIS(fn, secStart=0, secEnd=None, stride=1, mode='r'):
    """
    load Hamamatsu Image Sequence file format

    if secStart=0, and secEnd=None, and strid=1:
       use memmap to map entire file and 
       return mockNDarray of (memmaped) sections
    otherwise OR if mode is None: 
       load given range of sections into memory 
       (using N.fromfile) and
       return mockNDarray of (in memory) sections

    if secEnd is None: load section until end of file
    mode: only used for case 1; 'r' open file readonly, 'r+' read-and-write
    ref.: readerHIS.py
    """
    #from readerHIS import openHIS as loadHIS 
    if secStart==0 and secEnd is None and stride==1 and mode is not None:
        from readerHIS import openHIS # uses memmap
        return openHIS(fn, mode)
    else:
        from readerHIS import loadHISsects # uses fromfile
        return loadHISsects(fn, secStart, secEnd, stride)

def saveFits(arr, fn, overwrite=True):
    import pyfits

    if overwrite:
        import os
        if os.path.exists(fn):
            os.remove(fn)

    fits_file = pyfits.HDUList()
    datahdu = pyfits.PrimaryHDU()
    shapehdu = pyfits.ImageHDU()
    datahdu.data = arr
    shapehdu.data = N.array(arr.shape)
    fits_file.append(datahdu)
    fits_file.append(shapehdu)
    fits_file.writeto(fn)


def saveTiffMultipage(arr, fn, rescaleTo8bit=False):
    """
    using tifffile
    """
    import tifffile

    if rescaleTo8bit:
        mi,ma = float(arr.min()), float(arr.max())
        ra = ma-mi
        arr=(arr-mi)*255./ra
        arr = arr.astype(N.uint8)
    
    tifffile.imsave(fn, arr)

    
def saveTiffMultipageOld(arr, fn, rescaleTo8bit=False, rgbOrder="rgba", **params):
    """
    extension to PIL save TIFF
    if rescaleTo8bit: scale sections (using global(!) min & max intesity) to 0..255
        (ratios between colors are unchanged)

    **params is directly forwarded to PIL save function
    """
    import sys
    if sys.byteorder == 'little':
        def i16(c, o=0):
            return ord(c[o]) + (ord(c[o+1])<<8)
        def o32(i):
            return chr(i&255) + chr(i>>8&255) + chr(i>>16&255) + chr(i>>24&255)
    else:
        def i16(c, o=0):
            return ord(c[o+1]) + (ord(c[o])<<8)
        def o32(i):
            return chr(i>>24&255) + chr(i>>16&255) + chr(i>>8&255) + chr(i&255)
    
    #from PIL import _binary
    if arr.ndim == 4:
        if arr.shape[1] not in (1,2,3,4):
            raise ValueError, "can save 4d arrays (color) only with second dim of len 1..4 (RG[B[A]])"
    elif arr.ndim != 3:
        raise ValueError, "can only save 3d (grey) or 4d (color) arrays"

    fp = open(fn, 'w+b')

    ifd_offsets=[]

    if rescaleTo8bit:
        mi,ma = float(arr.min()), float(arr.max())
        ra = ma-mi

    params["_debug_multipage"] = True
    for z in range(arr.shape[0]):
        if rescaleTo8bit:
            a=(arr[z]-mi)*255./ra
            ii = array2image(a.astype(N.uint8), rgbOrder=rgbOrder)
        else:
            ii = array2image(arr[z], rgbOrder=rgbOrder)

        fp.seek(0,2) # go to end of file
        if z==0:
            # ref. PIL  TiffImagePlugin
            # PIL always starts the first IFD at offset 8
            ifdOffset = 8
        else:
            ifdOffset = fp.tell()

        ii.save(fp, format="TIFF", **params)
        
        if z>0: # correct "next" entry of previous ifd -- connect !
            ifdo = ifd_offsets[-1]
            fp.seek(ifdo)
            #ifdLength = ii._debug_multipage.load_signed_short(fp.read(2))#i16(fp.read(2))
            ifdLength = i16(fp.read(2))
            #ifdLength = ifdLength[0]
            fp.seek(ifdLength*12,1) # go to "next" field near end of ifd
            #fp.write(ii._debug_multipage.write_float(ifdOffset))#o32( ifdOffset ))
            
            fp.write(o32( ifdOffset ))
            
        ifd_offsets.append(ifdOffset)
    fp.close()#"""


def saveTiffMultipageOld(arr, fn, rescaleTo8bit=False, rgbOrder="rgba", **params):
    """
    extension to PIL save TIFF
    if rescaleTo8bit: scale sections (using global(!) min & max intesity) to 0..255
        (ratios between colors are unchanged)

    **params is directly forwarded to PIL save function
    """
    import struct
    #from PIL import _binary
    if arr.ndim == 4:
        if arr.shape[1] not in (1,2,3,4):
            raise ValueError, "can save 4d arrays (color) only with second dim of len 1..4 (RG[B[A]])"
    elif arr.ndim != 3:
        raise ValueError, "can only save 3d (grey) or 4d (color) arrays"

    fp = open(fn, 'w+b')


    ifh = fp.read(8)
    if ifh[:2] == b'MM': # bid-endian
        endian = ">"
    elif ifh[:2] == b'II': # little-endian
        endian = '<'
    else:
        endian = '<'

    #fp.seek(0)
    #fp.write(struct.pack(endian+"HL", 42, 8))
        
    
    ifd_offsets=[]

    if rescaleTo8bit:
        mi,ma = float(arr.min()), float(arr.max())
        ra = ma-mi

    params["_debug_multipage"] = True
    for z in range(arr.shape[0]):
        if rescaleTo8bit:
            a=(arr[z]-mi)*255./ra
            ii = array2image(a.astype(N.uint8), rgbOrder=rgbOrder)
        else:
            ii = array2image(arr[z], rgbOrder=rgbOrder)

        fp.seek(0,2) # go to end of file
        if z==0:
            # ref. PIL  TiffImagePlugin
            # PIL always starts the first IFD at offset 8
            ifdOffset = 8
        else:
            ifdOffset = fp.tell()

        ii.save(fp, format="TIFF", **params)
        
        if z>0: # correct "next" entry of previous ifd -- connect !
            ifdo = ifd_offsets[-1]
            fp.seek(ifdo)
            #ifdLength = ii._debug_multipage.load_signed_short(fp.read(2))#i16(fp.read(2))
            try:
                ifdLength = struct.unpack(endian+"H", fp.read(2))[0]
                fp.seek(ifdLength*12,1) # go to "next" field near end of ifd
            except:
                pass
            
            fp.write(struct.pack(endian+'I', ifdOffset))#o32( ifdOffset ))
            
        ifd_offsets.append(ifdOffset)
    fp.close()#"""

    
def saveTiffMultipageFromSeq(arrseq, fn, rescaleSeqTo8bit=False, rgbOrder="rgba", **params):
    """
    arrseq can be an iterator that yield 2D(grey) or 3D(color) image

    extension to PIL save TIFF

    if rescaleSeqTo8bit: scale each section (separately!) to 0..255
        (ratios between colors are unchanged)
    **params is directly forwarded to PIL save function
    """
#     if arr.ndim == 4:
#         if arr.shape[1] not in (1,2,3,4):
#             raise ValueError, "can save 4d arrays (color) only with second dim of len 1..4 (RG[B[A]])"
#     elif arr.ndim != 3:
#         raise ValueError, "can only save 3d (grey) or 4d (color) arrays"

    fp = open(fn, 'w+b')

    ifd_offsets=[]

#     if rescaleTo8bit:
#         mi,ma = float(arr.min()), float(arr.max())
#         ra = ma-mi

    params["_debug_multipage"] = True
    for z,a in enumerate(arrseq):
        if rescaleSeqTo8bit:
            mi,ma = float(a.min()), float(a.max())
            ra = ma-mi
            a=(a-mi)*255./ra
            ii = array2image(a.astype(N.uint8), rgbOrder=rgbOrder)
        else:
            ii = array2image(a, rgbOrder=rgbOrder)

        fp.seek(0,2) # go to end of file
        if z==0:
            # ref. PIL  TiffImagePlugin
            # PIL always starts the first IFD at offset 8
            ifdOffset = 8
        else:
            ifdOffset = fp.tell()

        ii.save(fp, format="TIFF", **params)
        
        if z>0: # correct "next" entry of previous ifd -- connect !
            ifdo = ifd_offsets[-1]
            fp.seek(ifdo)
            ifdLength = ii._debug_multipage.i16(fp.read(2))
            fp.seek(ifdLength*12,1) # go to "next" field near end of ifd
            fp.write(ii._debug_multipage.o32( ifdOffset ))

        ifd_offsets.append(ifdOffset)
    fp.close()

def loadImageFromURL(url):
    """
    download url of an image file
    into local cache and 
    return numpy array 
    """
    import urllib
    fp = urllib.urlretrieve(url, filename=None, reporthook=None, data=None)
    #     >>> fp[0]
    #     'c:\docume~1\haase\locals~1\temp\tmpgpcmwo.jpg'
    #     >>> fp[1]
    #     Date: Sat, 29 Sep 2007 21:03:15 GMT
    #     Server: Apache/1.3.27 (Unix)  (Red-Hat/Linux)
    #     P3P: CP="NOI DSP COR NID ADM DEV TAI PSA PUBo STP PHY"
    #     Last-Modified: Mon, 18 Oct 1999 17:32:10 GMT
    #     ETag: "4b75a-7aca-380b599a"
    #     Accept-Ranges: bytes
    #     Content-Length: 31434
    #     Connection: close
    #     Content-Type: image/jpeg 
    #     >>> fp[2]
    #     IndexError: tuple index out of range
    arr = loadImg(fp[0])
    return arr


###############################################################
###############################################################

def calc_threshold_basic(a, histYX=None, dt=.5, nMax=100, retImg = False):
    """
    calculate a threshold value
    using the "Basic Global Thresholding" method
    described in Ch. 10.3.2 in "Digital Image Processing"

    returns threshold T (1 for a>T; not >=T)

    stop iteration when T doesn't change more than dt
    or after nMax iterations

    histYX, is the histogram of a -- a tuple(binCount, binPixelValue)

    if retImg:
        returns thresholded image as uint8 
    """

    if histYX is None:
        h,x = histogramYX(a)
    else:
        h,x = histYX

    m1,m2 = x[0],x[-1]
    T = .5*(m1+m2)
    for i in xrange(nMax):
        ix1=N.where(x<=T)[0]
        ix2=N.where(x> T)[0]
        m1 = (h[ix1]*x[ix1]).sum() / float(h[ix1].sum())
        m2 = (h[ix2]*x[ix2]).sum() / float(h[ix2].sum())

        Tnew = .5*(m1+m2)

        if abs(T-Tnew) < dt:
            break
        T=Tnew

    if retImg:
        qq = N.ones(a.shape, dtype=N.uint8)#N.select([a>x2,a>x1], [N.ones(a.shape, dtype=N.uint8)])
        qq[a<=Tnew] = 0
        return qq
    else:
        return Tnew


def calc_threshold_otsu(a, histYX=None, retEM=False, retImg=False):
    """
    calculate a threshold value
    using "Otsu's Method"
    described in Ch. 10.3.3 in "Digital Image Processing"

    returns threshold T (1 for a>T; not >=T)

    histYX, is the histogram of `a` -- a tuple(binCount, binPixelValue)

    if retImg:
        returns thresholded image as uint8 
    elif retEM: 
        returns (T, eta), where eta is the "segmentation measure" 
                           (which might be Matlab's "effectiveness metric")

    TODO FIXME: this assumes a unique maximum for s2_B; 
                 otherwise an average of the corresponding T values *should* be returned
    """
    import fftfuncs as F

    if histYX is None:
        h,x = histogramYX(a)
    else:
        h,x = histYX

    p = F.zeroArrD(len(h))
    p[:] = h
    p/=float(h.sum())

    P = p.cumsum()       [:-1]# exclude last value; cumsum will be approx. 1 - causing division by zero
    m = (x*p).cumsum() 
    m_G = m[-1]
    s2_B = (m_G*P - m[:-1])**2. / (P*(1-P))

    k = N.argmax(s2_B)
    T = x[ k ]

    if retImg:
        x1 = x[ k ]
        qq = N.ones(a.shape, dtype=N.uint8)#N.select([a>x2,a>x1], [N.ones(a.shape, dtype=N.uint8)])
        qq[a<=T] = 0
        return qq
    if retEM:
        s2_G = ((x-m_G)**2.*p).sum()
        #separability measure:
        eta  =  s2_B/s2_G

        return T,eta[k]
    else:
        return T


def calc_threshold_otsu2(a, histYX=None, retEM=False, retImg=False):
    """
    calculate multiple (i.e. 2; nT = 2 !!) threshold values
    using "Otsu's Method"
    described in Ch. 10.3.6 in "Digital Image Processing"
    Also ref.: "A Fast Algorithm for Multilevel Thrsholding", Liao, Chen, Chung, 2001

    ################## old:returns array of nT(=2) thresholds (T1,T2)
    returns tuple of T1, T2   (1 for a>T; not >=T)

    histYX, is the histogram of a -- a tuple(binCount, binPixelValue)

    if retImg:
        returns thresholded image as uint8 
    elif retEM: 
        returns ((T1,T2), eta), where eta is the "segmentation measure" 
                                 (which might be Matlab's "effectiveness metric")

    TODO FIXME: this assumes a unique maximum for s2_B; 
                 otherwise an average of the corresponding T values *should* be returned
    """
    import fftfuncs as F
    nT=2 # max-search is too slow for nT>= 3

    if histYX is None:
        h,x = histogramYX(a)
    else:
        h,x = histYX

    nk = len(h) # number of bins

    p = F.zeroArrD(len(h))
    p[:] = h
    p/= float(h.sum())

    P = p.cumsum()       
    m = (x*p).cumsum() 
    m_G = m[-1]
    #m_G = (h*x).sum()/h.sum()  # global mean

    
    otsu2Img = F.zeroArrF(nk, nk)

    M = nT + 1 # number of classes
    for Tk1 in range(1,nk-2): # leave room for 2 values, i.e  another threshold, at the top
        omeg_1 = P[Tk1]
        mu_1   = m[Tk1] / omeg_1
        for Tk2 in range(Tk1+1, nk-1):
            omeg_2 = P[Tk2] - omeg_1
            omeg_3 = 1. -  P[Tk2]

            mu_2   = (m[Tk2] - m[Tk1]) / omeg_2
            mu_3   = (m[-1]-m[Tk2]) / omeg_3

            otsu2Img[Tk1,Tk2] = \
                 omeg_1*mu_1*mu_1 +\
                 omeg_2*mu_2*mu_2 +\
                 omeg_3*mu_3*mu_3
            
    #return otsu2Img
    s2_B__prime, _, Tk1, Tk2 = findMax(otsu2Img)

    if retImg:
        x1,x2 = x[Tk1], x[Tk2]
        qq = N.select([a>x2,a>x1], [2,N.ones(a.shape, dtype=N.uint8)])
        return qq
    if retEM:
        omeg_1 = P[Tk1]
        mu_1   = m[Tk1] / omeg_1
        omeg_2 = P[Tk2] - omeg_1
        omeg_3 = 1. -  P[Tk2]
        mu_2   = (m[Tk2] - m[Tk1]) / omeg_2
        mu_3   = (m[-1]-m[Tk2]) / omeg_3

        mu_T = (omeg_1*mu_1 + omeg_2*mu_2 + omeg_3*mu_3)
        s2_B = s2_B__prime - mu_T * mu_T

        s2_G = ((x-m_G)**2*p).sum()
        eta = s2_B / s2_G
        return (x[Tk1], x[Tk2]), eta
    else:
        return (x[Tk1], x[Tk2])

    '''
    K = nT + 1 # number of classes
    #T=N.arange(0,K+1, dtype=N.float64)
    #T[0]  = x[0] -1 # lower bound is fixed to min-1
    #T[K]  = x[-1]+1 # upper bound is fixed to max+1
    Tk=N.arange(0,K+1, dtype=N.int) # theshold in units of "bin number"
    Tk[0]  = -1 # lower bound is fixed to min-1
    Tk[K]  = nk # upper bound is fixed to max+1
    


    P  = F.zeroArrD(K)
    m  = F.zeroArrD(K)

    otsu2Img = F.zeroArrF(len(h), len(h))
    for Tk1 in range(1,nk-2): # leave room for 2 values, i.e  another threshold, at the top
        for Tk2 in range(Tk1+1, nk-1):
            # . x[N.where((x>T1) & (x<x[-1]))]:
            Tk[1] = Tk1
            Tk[2] = Tk2
    
 #             N.where((x>T[i]) & (x<=T[i+1]))
            ix =  [  N.arange(Tk[i]+1, Tk[i+1])            for i in range(K) ]


            for i in range(K):
                P [i] =  p[ix[i]].sum()
                m [i] =  (p[ix[i]]*x[ix[i]]).sum() / P[i]

            s2_B = (P[i]*(m[i]-m_G)**2).sum()

            otsu2Img[Tk1,Tk2] = s2_B

    #s2_G = ((x-m_G)**2*p).sum()
    #separability measure:
    #eta  =  s2_B/s2_G
    #eta[T]

    return otsu2Img
    '''
    
    

def calc_threshold_otsu3(a, histYX=None, retEM=False, retImg=False):
    """
    calculate 3 threshold values using "Otsu's Method"
    described in Ch. 10.3.6 in "Digital Image Processing"
    Also ref.: "A Fast Algorithm for Multilevel Thrsholding", Liao, Chen, Chung, 2001

    returns tuple of T1, T2, T3 (1 for a>T; not >=T)

    histYX, is the histogram of a -- a tuple(binCount, binPixelValue)

    if retImg:
        returns thresholded image as uint8 
    elif retEM: 
        returns ((T1,T2,T3), eta), where eta is the "segmentation measure" 
                           (which might be Matlab's "effectiveness metric")

    TODO FIXME: this assumes a unique maximum for s2_B; 
                 otherwise an average of the corresponding T values *should* be returned
    """
    import fftfuncs as F
    nT=3

    if histYX is None:
        h,x = histogramYX(a)
    else:
        h,x = histYX

    nk = len(h) # number of bins

    p = F.zeroArrD(len(h))
    p[:] = h
    p/= float(h.sum())

    P = p.cumsum()       
    m = (x*p).cumsum() 
    m_G = m[-1]
    #m_G = (h*x).sum()/h.sum()  # global mean

    
    otsu2Img = F.zeroArrF(nk, nk, nk)
    
    M = nT + 1 # number of classes
    for Tk1 in range(1,nk-nT-1): # leave room for nT values, i.e  another threshold, at the top
        omeg_1 = P[Tk1]
        mu_1   = m[Tk1] / omeg_1
        for Tk2 in range(Tk1+1, nk-3):
            omeg_2 = P[Tk2] - omeg_1
            mu_2   = (m[Tk2] - m[Tk1]) / omeg_2

            for Tk3 in range(Tk2+1, nk-2):
                omeg_3 = P[Tk3] - P[Tk2]
                mu_3   = (m[Tk3] - m[Tk2]) / omeg_3

                omeg_4 = 1. -  P[Tk3]
                mu_4   = (m[-1]-m[Tk3]) / omeg_4

                otsu2Img[Tk1,Tk2,Tk3] = \
                     omeg_1*mu_1*mu_1 +\
                     omeg_2*mu_2*mu_2 +\
                     omeg_3*mu_3*mu_3 +\
                     omeg_4*mu_4*mu_4
            
    #return otsu2Img
    s2_B__prime, Tk1, Tk2, Tk3 = findMax(otsu2Img)
    x1,x2,x3 = x[Tk1], x[Tk2], x[Tk3]

    if retImg:
        qq = N.select([a>x3,a>x2,a>x1], [3,2,N.ones(a.shape, dtype=N.uint8)])
        return qq
    if retEM:
        omeg_1 = P[Tk1]
        mu_1   = m[Tk1] / omeg_1

        omeg_2 = P[Tk2] - omeg_1
        mu_2   = (m[Tk2] - m[Tk1]) / omeg_2

        omeg_3 = P[Tk3] - P[Tk2]
        mu_3   = (m[Tk3] - m[Tk2]) / omeg_3

        omeg_4 = 1. -  P[Tk3]
        mu_4   = (m[-1]-m[Tk3]) / omeg_4

        mu_T = (omeg_1*mu_1 + omeg_2*mu_2 + omeg_3*mu_3 + omeg_4*mu_4)
        s2_B = s2_B__prime - mu_T * mu_T

        s2_G = ((x-m_G)**2*p).sum()
        eta = s2_B / s2_G
        return (x1,x2,x3), eta
    else:
        return (x1,x2,x3)


###############################################################
###############################################################

#adapted from numpy's numeric.py

def _getconv(dtype):
    typ = dtype.type
    if issubclass(typ, N.bool_):
        return lambda x: bool(int(x))
    if issubclass(typ, N.integer):
        return int
    elif issubclass(typ, N.floating):
        return float
    elif issubclass(typ, complex):
        return complex
    else:
        return str

def _string_like(obj):
    try: obj + ''
    except (TypeError, ValueError): return False
    return True

def saveTxt(arrND, fname, fmt='%8.3f', delimiter=' ', intro='',  transpose=False):
    """
    write 2D arrays as rows(-2 axis) of columns (last axis)
    for each additional dimension, prepend a column for the axis index 
      (total of arrNDndim-2 additional columns)
    1D arrays are written as one value per line

    list of arrays are converted into mockNDarrays

    fname can be one of an open file, a filename or a filename ending on ".gz"

    start by writing intro into the file
      if intro does not end with "\\n", auto-append a newline

    delimiter is used to separate the fields, eg delimiter ',' for
    comma-separated values

    if transpose: transpose last 2 dimensions of arrND before saving
    """

    if _string_like(fname):
        if fname.endswith('.gz'):
            import gzip
            fh = gzip.open(fname,'wb')
        else:
            fh = file(fname,'w')
    elif hasattr(fname, 'readline'):
        fh = fname
    else:
        raise ValueError('fname must be a string or file handle')

    if len(intro)>0:
        fh.write(intro)
        if intro[-1] != '\n':
            fh.write('\n')

    if not hasattr(arrND, "ndim"):
        from fftfuncs import mockNDarray
        arrND = mockNDarray(*arrND)


    if arrND.ndim == 1:
        arrND = arrND.view()
        arrND.shape = len(arrND), 1

    if transpose:
        nd = arrND.ndim
        arrND = arrND.transpose( range(nd-2)+[nd-1, nd-2] )

    if arrND.ndim > 2:
        for i in N.ndindex(arrND.shape[:-2] ):
            for row in arrND[i]:
                fh.write( delimiter.join(map(str,i))+delimiter +
                          delimiter.join([fmt%val for val in row]) + '\n')
    else:
        for row in arrND:
            fh.write( delimiter.join([fmt%val for val in row]) + '\n')
        
def loadTxt(fname, ndim=3, dtype=None, delimiter=None, skipNlines=0, 
            comments='#', converters=None, usecols=None):
    """
    load a text file into a ndimensional array (mockNDarray)

    fname can be an open file or a filename or a filename ending on ".gz" or ".bz2"
    if dtype is not None, force data to be dtype

    delimiter is a string-like character used to seperate values in the
    file. If delimiter is unspecified or none, any whitespace string is
    a separator.

    lines or trailing line parts starting with a character in comments are ignored

    converters, if not None, is a dictionary mapping column number to
    a function that will convert that column to a float.  Eg, if
    column 0 is a date string: converters={0:datestr2num}
    
    usecols, if not None, is a sequence of integer column indexes to
    extract where 0 is the first column, eg usecols=(1,4,5) to extract
    just the 2nd, 5th and 6th columns

    after applying converters (at first) and usecols (after that),
    the first ndim-2 columns are interpreted as the nd-index
    """
    if _string_like(fname):
        if fname.endswith('.gz'):
            import gzip
            fh = gzip.open(fname)
        # zip is an archive - should we just read the first file !?
        #elif fname.endswith('.zip'):
        #    import zip
        #    fh = zip.ZipFile(fname)
        elif fname.endswith('.bz2'):
            import bz2
            fh = bz2.BZ2File(fname)
        else:
            fh = file(fname)
    elif hasattr(fname, 'readline'):
        fh = fname
    else:
        raise ValueError('fname must be a string or file handle')

    from numpy.core import multiarray
    dtype = multiarray.dtype(dtype)
    defconv = _getconv(dtype)
    converterseq = None    
    if converters is None:
        converters = {}
        if dtype.names is not None:
            converterseq = [_getconv(dtype.fields[name][0]) \
                            for name in dtype.names]
            
    
    ndim2 = ndim-2

    # read file line by line into a dictionary of lists of rows
    iiMax = [0] * ndim2
    Xii = {}
    for i,line in enumerate(fh):
        if i<skipNlines: continue
        line = line[:line.find(comments)].strip()
        if not len(line): continue
        vals = line.split(delimiter)

        if converterseq is None:
           converterseq = [converters.get(j,defconv) \
                           for j in xrange(len(vals))]
        if usecols is not None:
            row = [converterseq[j](vals[j]) for j in usecols]
        else:
            row = [converterseq[j](val) for j,val in enumerate(vals)]
        if dtype.names is not None:
            row = tuple(row)

        ii = tuple(map(int, row[:ndim2])) # nd-index
        # line part AFTER nd-indices
        row = row[ndim2:]


        try:
            X = Xii[ ii ]
        except KeyError:
            X = Xii[ ii ] = []

        from __builtin__ import max
        iiMax = [max(j,k) for j,k in zip(iiMax,ii)]
        X.append(row)

    # convert list of rows into (real) ndarrays; for each >2 dimensional index separately

    for ii,X in Xii.iteritems():
        Xii[ii] = X = N.array(X, dtype)
        r,c = X.shape
        if r==1 or c==1:
            X.shape = max([r,c]),


    if ndim2 == 0:
        return Xii[()]

    shape2 = tuple([im+1 for im in iiMax])

    # convert dictionary of >2 dimensional indeces into nested lists of (real) arrays
    nestedListsOfArrays = [None] * (shape2[-1])
    for len_i in shape2[::-1][1:]: # same as [-2::-1]
        nestedListsOfArrays= [nestedListsOfArrays[:] for  j in range(len_i)]

    #print nestedListsOfArrays

    #  # replace the Nones by the arrays
    for ii,X in Xii.iteritems():
        nLAi = nestedListsOfArrays
        for iii in ii[:-1]:
            nLAi = nLAi[iii]
        nLAi[ii[-1]] = X

    #print nestedListsOfArrays
    #return nestedListsOfArrays

    # turn list of lists into mockNDarrays (of mockNDarrays ... of real arrays)

    #print ndim2, shape2
    from fftfuncs import mockNDarray
    if ndim2 == 1:
        nLAi = mockNDarray(*nestedListsOfArrays)
    else: # 20090305: CHECK if this "else" section could now be handled (like the ndim2==1 case) by extended mockNDarray handling of nested lists
        for order in range(ndim2,1 -1,-1):
            for ii in N.ndindex( shape2[:order] ):
                #print order, ii
                nLAi = nestedListsOfArrays
                for iii in ii[:-1]:
                    nLAi = nLAi[iii]
                nLAi[ii[-1]] = mockNDarray(*nLAi[ii[-1]])
        nLAi = mockNDarray(*nLAi)
    return nLAi

def text2array(txt, transpose=False, comment='#', sep=None, convFcn = None, convertDecimalKomma=False):
    """
    Return an array containing the data contained as text in txt. This
    function works for arbitrary data types (every array element can be
    given by an arbitrary Python expression), but at the price of being
    slow. 
   
    if convFcn is not None:
        convFcn is called for each "cell" value - a string !.
        useful here: "N.float32"  # WRONG !! THIS DOES NOT WORK FIXME !
    else:
        "eval" is called for each cell

    if sep is None, any white space is seen as field separator
    ignore all lines that start with any character contained in comment

    if convertDecimalKomma:
       convert e.g. "10,2" to "10.2"
    """
 
    if convertDecimalKomma:
        from useful import strTranslate
        if convFcn is not None:
            def fn(numTxt):
                return convFcn( strTranslate(numTxt, ',', '.') )
        else:
            def fn(numTxt):
                return eval(strTranslate(numTxt, ',', '.'))
    else:
        if convFcn is not None:
            def fn(x):
                return convFcn(x)
        else:
            def fn(x):
                return eval(x)


    data = []
    for line in txt.splitlines():
        if not line[0] in comment:
            data.append(map(fn, line.split(sep)))
    a = N.array(data)
    if a.shape[0] == 1 or a.ndim>1 and a.shape[1] == 1:
        a = N.ravel(a)

    if transpose:
        a = a.T
    return a



def uu_encodestring(text, compress=True):
    """
    from http://effbot.org/librarybook/uu.htm
    seb added bz2 compression
    """
    import StringIO, uu, bz2
    fin = StringIO.StringIO(bz2.compress(text))
    fout = StringIO.StringIO()
    uu.encode(fin, fout)
    return fout.getvalue()

def uu_decodestring(text, decompress=True):
    """
    from http://effbot.org/librarybook/uu.htm
    seb added bz2 compression
    """
    import StringIO, uu, bz2
    fin = StringIO.StringIO(text)
    fout = StringIO.StringIO()
    uu.decode(fin, fout)
    return bz2.decompress(fout.getvalue())


def grep(pattern, *files):# , retList=False):
    """
    emulate grep-functionality

    #if retList:
        return tuple list of (file, lineNo, lineText)-tuple
    #else:
    #    print familiar output to stdout

    posted by Fredrik Lundh, October 25th, 2005
    http://bytes.com/forum/thread169012.html
    """
    #if retList:
    ret=[]
    search = re.compile(pattern).search
    for file in files:
        for index, line in enumerate(open(file)):
            if search(line):
                #if retList:
                ret.append( (file, str(index+1), line[:-1]) )
                #else:
                #    print ":".join((file, str(index+1), line[:-1]))
    #if retList:
            fns = '_%0' + '%d'%(int(N.log10(n))+1) +'d'
    return ret


def pathPrependToFilename(path, prefix):
    """
    given filename path containing multiple parent folders
    change only the last "file name" part by prepending `prefix`;
    keep all parent folder names unchanced
    """
    import os
    f = os.path.split(path)
    return os.path.join( *(f[:-1] + (prefix+f[-1],)) )

def path_mkdir(newdir):
    """
    works the way a good mkdir should :)
    - already exists, silently complete
    - regular file in the way, raise an exception
    - parent directory(ies) does not exist, make them as well

    Recipe 82465: a friendly mkdir() 
    http://code.activestate.com/recipes/82465/
    """
    import os
    if os.path.isdir(newdir):
        return
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            path_mkdir(head)
        #print "_mkdir %s" % repr(newdir)
        if tail:
            os.mkdir(newdir)

def sgn(a):
    return N.sign(a)

def binaryRepr(x, count=8):
    """
    Integer to "binary string" ("101011")
    returns string of length count containing '0's and '1'
    building up the "binary representation" of x
    Count is number of bits
    
    Note: the inverse operation is done by int(xxx, 2)
    """
    return "".join(map(lambda i:str((x>>i)&1), range(count-1, -1, -1)))
    
def fib(max=100, startWith0=True):
    """uses generator to iterate over sequence of Fibonacci numbers
    """
    a, b = 0, 1
    if startWith0:
        yield a
    while 1:
        if b > max:
            return
        yield b
        a, b = b, a+b
def fib2(n):
    """
    direct calc (non-recursive) return n_th Fibonacci number (as float!)
    n=0 --> 0
    n=1 --> 1
    n=2 --> 1
    ...
    n should be <= 604 ;-( (as float)
    n should be <= 46  ;-( (if you want to convert to int)
    #http://en.wikipedia.org/wiki/Fibonacci_sequence
    #
    http://www.research.att.com/cgi-bin/access.cgi/as/njas/sequences/eisA.cgi?Anum=A000045
    """
    
    return ((1+N.sqrt(5))**n-(1-N.sqrt(5))**n)/(2**n*N.sqrt(5))

def primes(max=100):
    ps=[2]
    i = 3
    yield 2
    while i<=max:
        isPrime = 1
        for p in ps:
            if i % p == 0:
                isPrime=0
                break
        if isPrime:
            ps.append(i)
            yield i
        i+=1

def primeFactors(a, max=None, includeRemainder=False):
    """return list of a's prime factors
    if max is not None:
       largest prime in list will be max
        (as often as it would be in the complete list)
       in this case: if includeRemainder is True:
                     append remainder so that N.product(<list>) == a
    """
    f = []
    for p in primes(a):
        if max is not None and p>max:
            if includeRemainder and a>1:
                f.append(a)
            return f
        while a%p==0:
            f.append(p)
            a/=p
            if a == 1:
                return f
    return f

def factorial(n, _memo={0:1,1:1}):
    try: return _memo[n]
    except KeyError:
        result = _memo[n] = n * factorial(n-1)
        return result
fac = factorial

def gamma(x, _memo={.5:N.pi**.5,  1.:1.}):
    """
    return gamma function
    defined for integer and half-integer values

    you can use scipy.special.gamma() for the general case
    """
    try: return _memo[x]
    except KeyError:
        if x>0 and (x == int(x) or 2.*x % 2 == 1.):
            xx=x-1
            return (xx)*gamma(xx)
        else:
            raise ValueError, "we have gamma(x) only defined for x =.5, 1, 1.5,..."
    
def iterIndices(shape):
    if type(shape) == int:
        shape = (shape,)    
    if len(shape) == 1:
        for i in range(shape[0]):
            yield (i,)
    else:
        for i in range(shape[0]):
            for ii in iterIndices(shape[1:]):
                yield (i,) + ii

def smooth1d(x,window_len=10,window='hanning'):
    """smooth the data using a window with requested size.
    
    This method is based on the convolution of a scaled window with the signal.
    The signal is prepared by introducing reflected copies of the signal 
    (with the window size) in both ends so that transient parts are minimized
    in the begining and end part of the output signal.
    
    input:
        x: the input signal 
        window_len: the dimension of the smoothing window
        window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
            flat window will produce a moving average smoothing.

    output:
        the smoothed signal
        
    (ref.: copy paste from http://www.scipy.org/Cookbook/SignalSmooth)
    example:

    t=linspace(-2,2,0.1)
    x=sin(t)+randn(len(t))*0.1
    y=smooth(x)
    
    see also: 
    
    numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
    scipy.signal.lfilter
 
    TODO: the window parameter could be the window itself if an array instead of a string   
    """

    x = N.asarray(x)

    if x.ndim != 1:
        raise ValueError, "smooth only accepts 1 dimension arrays."

    if x.size < window_len:
        raise ValueError, "Input vector needs to be bigger than window size."


    if window_len<3:
        return x


    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"


    s=N.r_[2*x[0]-x[window_len:1:-1],x,2*x[-1]-x[-1:-window_len:-1]]
    #print(len(s))
    if window == 'flat': #moving average
        w=ones(window_len,'d')
    else:
        w=eval('N.'+window+'(window_len)')

    y=N.convolve(w/float(w.sum()),s,mode='same')
    return y[window_len-1:-window_len+1]
