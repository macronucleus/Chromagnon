__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import Priithon_bin.CCG_d as _CCG_d
import Priithon_bin.CCG_s as _CCG_s
import numpy as _N


"""
ccg ChangeLog
* starting out with ccg essentially from GPL Eden version
   (2/24/95)
   Author:  Erik M. Johansson, translation of Dennis Goodman;s
            FORTRAN constrained least squares conjugate gradient
            codes            
* python binding for original AIDA ccg
  * global memory-pointers xn,gn,go,d inited with by init_global_array_pointers
  * CostFunction takes arguments: xo, grad
  * later removed 'grad' argument
  * xmin,xmax changed to scalar (all dimensions see same xmin,xmax)
  * 20050707: ivec was 'int' now changed to 'unsigned char'
              fixed some bugs in countem function - only used for debug-printing

* 20060425 changed to more generic priithon version
  * all global pointers removed
      required to add some extra args to some internal functions
      we only use those 4 arrays as module-global variables
        to reuse beween ccg calls
        and (maybe) simplify debugging (?)
  * xmin,xmax is an array again
      BUT if size of xmin is 1 (given by nMinMax) use "scalar iterpretation"
          from above (all dimensions see same xmin,xmax)
  * CostFunction not a hard-coded python module/function pair anymore
      BUT given as Python(-function) object as argument to getsol
  * CostFunction takes two arguments (again)
      xx,gg: eliminates need to access any "global" arrays
             (BUT xx,gg still are effectively pointers to same arrays (xn and gn=grad))
             (no copying!)
  * debug and debug2 as arguments to control debug printing (debug2 enables prints in clsrch)
  * 20060510: added dfdxpc as argument (was "uninitialized"/never-used global)
                 meaning: Stop getsol if df/dx is reduced to 'dfdxpc' of its initial value
                 (needed to read Eden code to understand this)
  * 20060510: changed returned itn and ifn to be 0-based,
               i.e. one "successful" loop run returns now 1 (before: 2)
  * fixed bugs about not itn and/or Nclsrch not being intied to 0 on early exit
  * 20060510: fixed bug of missing memcpy on NORMAL_STOP and DX_TOO_SMALL (?????? 20060519 not here) exit
              result x was in xn (forgot to copy into xo)

  * python function renamed from _gs and doCCG to _getsolMultiType and getsol
  * order of return tuple changed: 20060517
     old:  itn,ifn, istop, fn, df0, Nclsrch
     new:  istop, itn,ifn, Nclsrch, fn, df0

     (fixed SWIG interface unclarity: we use Nclsrch only as output
                    - not cumulative between getsol calls !!)
"""


def _getsolMultiType(a, *args):
    if a.dtype == _N.float32:
        return  _CCG_s.getsol(a, *args)
    elif a.dtype == _N.float64:
        return  _CCG_d.getsol(a, *args)
    else:
        raise TypeError, "dtype must be either float32 or float64"

bufSize=-1

def getsol(xo, xmin, xmax, _ivec, CG_iter, fmin, df0, CCG_tolerance,
          costGradFunc, dfdxpc=0, debug=0, debug2=0):
    """
    xo   vector of variables.  Set to initial estimate.
           On return, it holds the location of the minimum      
    xmin     lower bound ("scalar"? see N.B.) on the variables          
    xmax     upper bound ("scalar"? see N.B.) on the variables          
    ivec     array of integers (20050707: now type Bytes) providing information about the
        variables.  See ccg.h                   
             if scalar is provided - ivec gets expanded into ivec global array
    iter     maximum number of iterations allowed in getsol 
    fmin     smallest possible value for function being minimized   
    df0  initial value for df for this call to getsol.  
                   On return, same for next call to getsol      
    tol  relative tolerance for function            

    costGradFunc  a callback function - see below
    dfdxpc    Stop getsol if df/dx is reduced to 'dfdxpc' of its initial value

 returns:
    itn  the number of iterations in getsol         
    ifn  the number of times funct was evaluated        
    istop    the reason for stopping.  See ccg.h            
    fn   the value of funct at the minimum          

     on entry and return:

    Nclsrch     cumulative # calls to clsrch()      

    costGradFunc::
    ***************
    csol ;       current solution array  (=xn)
    grad ;       gradient array (returned, i.e. changed inplace)
    ressq ;      (returned) residue         
    iqflag ;     (returned) flag re success 

    note: doCCG caches buffers for subsequent calls
    """
    global bufSize, buf1, buf2, buf3, buf4
    global xn,grad,go,d
    global ivec
    
    shape = xo.shape
    dtype = xo.dtype
    nBytes = xo.nbytes
    
    if bufSize < nBytes:
        bufSize = nBytes
        buf1 = _N.empty_like(xo)
        buf2 = _N.empty_like(xo)
        buf3 = _N.empty_like(xo)
        buf4 = _N.empty_like(xo)

    # xn, grad, go, d
    xn   = _N.ndarray(buffer=buf1, shape=shape, dtype=dtype)
    grad = _N.ndarray(buffer=buf2, shape=shape, dtype=dtype)
    go   = _N.ndarray(buffer=buf3, shape=shape, dtype=dtype)
    d    = _N.ndarray(buffer=buf4, shape=shape, dtype=dtype)
    
    #_init_global_array_pointers(xn, grad, go, d)

    xmin = _N.array(xmin, dtype, ndmin=1)
    xmax = _N.array(xmax, dtype, ndmin=1)
    if xmin.size == 1:
        if xmax.size != 1:
            raise ValueError, "xmin is a single value, but xmax is not"
    else:
        if xmin.size != xo.size:
            raise ValueError, "xmin must be either single value or same size as xo"
        elif xmax.size != xo.size:
            raise ValueError, "xmax must same size as xmin"

    #no!! ivec gets changed in-place !!  ivec = na.asarray(ivec, na.UInt8)
    if type(_ivec) is int:
        ivec = _N.empty(shape=shape, dtype=_N.uint8)
        ivec[:] = _ivec
    else:
        ivec = _ivec
    return _getsolMultiType(xo, xmin, xmax, ivec,
                            CG_iter, fmin, df0, CCG_tolerance,
                            xn,grad,go,d,
                            costGradFunc,
                            dfdxpc, debug, debug2)



def makeCostGradFunction(cgf, *args, **kwargs):
    """
    use this if your costGradFunction wants
    additional arguments and/or keyword-arguments
    (constant thought optimization)

    example:
    def myCGF(x, gg, zzz=0, set=1):
        ...
        gg[:] = ... zzz...
        return set*x, 0

    ccg.getsol( ... costGradFunc=ccg.makeCostGradFunction(myCGF, set=4) ...)
    
    """
    def wrapCostFunction(x,gg):
        return cgf(x,gg, *args, **kwargs)

    return wrapCostFunction

def makeCostGradFunction2(cf, gf, *args, **kwargs):
    """
    use this if your have separate functions for
    cost and gradient calculation
    also
    additional arguments and/or keyword-arguments
    (constant thought optimization)
    can be specified.

    example:
    def myCost(x, zzz=0, set=1):
        ...
        return set*x, 0

    def myGrad(x, gg, zzz=0, set=1):
        ...
        gg[:] = ... zzz...

    ccg.getsol( ... costGradFunc=ccg.makeCostGradFunction2(myCost, myGrad, set=4) ...)
    
    """
    def wrapCostFunction(x,gg):
        gf(x, gg, *args, **kwargs)
        return cf(x, *args, **kwargs)

    return wrapCostFunction
