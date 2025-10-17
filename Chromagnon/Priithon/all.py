""" use
from Priithon.all import *
to get access to all the modules like na,U,Y,...
"""
from __future__ import print_function
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

## __all__ = ["priism", "seb"]
#  #from priism import *
#  from priism.priism   import *
#  from seb.seb         import *
#  from bettina.bettina import *
#  from lin.lin         import *
#  from willy.willy     import *

import sys
def main_is_frozen():
   return (getattr(sys, "frozen", False) or # new py2exe + pyinstaller
           hasattr(sys, "importers")) # old py2exe

#  from sys import getrefcount as rc

_broken=""

#20060719 try:
#20060719     import priism  as P
#20060719 except:    _broken +=" P"
try:
    import numpy as N
    import numpy as np
except:
    _broken +=" N"

#  try:
#      import ArrayIO as A # needs Scientific.IO.TextFile
#  except:    _broken +="  A"

#interesting stuff is in useful anyway...
#  try:
#      from PIL import Image as I # PIL
#  except:    _broken +="  I"

from . import useful as U
from . import fftfuncs as F
try:
    #from . import Mrc
    from imgio import Mrc
except:
    _broken +=" Mrc"

if sys.version_info.major == 3:    
    from importlib import reload

try:
    if not hasattr(sys,'app'): # HACK: we use this as indicator for a graphic enabled environment
        #import usefulX as Y
    #else:
        class dummyPriithonClass:
            def addHistory(self, msg=''):
                print(msg)
            def appendText(self, *args, **kwds):
                pass
        import __main__
        if not hasattr(__main__, 'shell'):
            __main__.shell = dummyPriithonClass()
    from . import usefulX as Y#usefulX_noX as Y



    FN = Y.FN
    DIR = Y.DIR
except:    
    _broken +="  Y"
    raise
#finally:
#    if not main_is_frozen():
#        del sys
try:
    import matplotlib
    matplotlib.use('wxagg')
    from matplotlib import pyplot as P
    P.ion()
except:    _broken +="  P"

if _broken != "" and not main_is_frozen():
    print(" * couldn't load module(s): ", _broken)
