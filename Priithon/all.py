""" use
from Priithon.all import *
to get access to all the modules like na,U,Y,...
"""
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

## __all__ = ["priism", "seb"]
#  #from priism import *
#  from priism.priism   import *
#  from seb.seb         import *
#  from bettina.bettina import *
#  from lin.lin         import *
#  from willy.willy     import *

#  from sys import getrefcount as rc

_broken=""

#20060719 try:
#20060719     import priism  as P
#20060719 except:    _broken +=" P"
try:
    import numpy as N
except:
    _broken +=" N"

#  try:
#      import ArrayIO as A # needs Scientific.IO.TextFile
#  except:    _broken +="  A"

#interesting stuff is in useful anyway...
#  try:
#      from PIL import Image as I # PIL
#  except:    _broken +="  I"

import useful as U
import fftfuncs as F
try:
    import Mrc
except:
    _broken +=" Mrc"


try:
    import sys
    if hasattr(sys,'app'): # HACK: we use this as indicator for a graphic enabled environment
        import usefulX as Y
    else:
        import usefulX_noX as Y

    FN = Y.FN
    DIR = Y.DIR
except:    
    _broken +="  Y"
    raise
finally:
    del sys
try:
    #20090612 import pylab as P
    from matplotlib import pyplot as P
    P.ion()
except:    _broken +="  P"

if _broken != "":
    print " * couldn't load module(s): ", _broken
