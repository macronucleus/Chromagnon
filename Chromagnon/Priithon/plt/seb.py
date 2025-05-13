#seb     big = limits.double_max / 10
#seb    small = limits.double_min / 10
##import numarray as Numeric #HACK
##import numarray as na
import numpy as N

toFloat32 = lambda x: N.asarray(x).astype(N.float32)
toFloat64 = lambda x: N.asarray(x).astype(N.float64)

class limits:
    # not quite right...
    double_min = -1.797683134862318e308
    double_max = 1.797683134862318e308
    double_precision = 15
    double_resolution = 10.0**(-double_precision)

    float_min = -3.402823e38
    float_max = 3.402823e38
    float_precision = 6
    float_resolution = 10.0**(-float_precision)
    def epsilon(typecode):
        if typecode == N.float32: cast = toFloat32
        elif typecode == N.float64: cast = toFloat64
        one = cast(1.0)
        x = cast(1.0)
        while N.all(one+x > one):
            x = x * cast(.5)
        x = x * cast(2.0)
        return x

    def tiny(typecode):
        if typecode == N.float32: cast = toFloat32
        if typecode == N.float64: cast = toFloat64
        zero = cast(0.0)
        d1 = cast(1.0)
        d2 = cast(1.0)
        while N.all(d1 > zero):
            d2 = d1
            d1 = d1 * cast(.5)
        return d2

    float_epsilon = epsilon(N.float32)
    float_tiny = tiny(N.float32)
    # hard coded - taken from Norbert's Fortran code.
    #      INTEGER, PARAMETER :: kind_DBLE = KIND(0D0)           ! 8 (HP-UX)
    #      INTEGER, PARAMETER :: prec_DBLE = PRECISION(0D0)      ! 15
    #      INTEGER, PARAMETER :: range_DBLE = RANGE(0D0)         ! 307
    #      REAL(kind_DBLE), PARAMETER :: eps_DBLE = EPSILON(0D0) ! 2.22e-16
    #      REAL(kind_DBLE), PARAMETER :: tiny_DBLE = TINY(0D0)   ! 2.23e-308
    #      REAL(kind_DBLE), PARAMETER :: huge_DBLE = HUGE(0D0)   ! 1.80e+308
    double_epsilon = epsilon(N.float64)
    double_tiny = tiny(N.float64)

    


def big_for(a):
    '''returns a number that is considred big for the type of a'''
    if a.dtype is N.float32:
        return limits.float_max / 10
    elif a.dtype is N.float64:
        return limits.double_max / 10
    else:
        return limits.float_max / 10 # FIXME
def small_for(a):
    '''returns a number that is considred small for the type of a'''
    if a.dtype is N.float32:
        return limits.float_min / 10
    elif a.dtype is N.float64:
        return limits.double_min / 10
    else:
        return limits.float_min / 10 # FIXME
    

#added by seb: in case y.dtype is e.g. uint8, there might be more than 255 x values ...
#20070731 - CHECK

def dtypeBigEnough(a):
    """
    return dtype of a but at least N.int16
    """
    d = a.dtype
    if d in (bool, N.uint8, N.int8):
        return N.int16
    else:
        return d
