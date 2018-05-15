"""
this is the minimal priithon (non GUI) startup file
it imports all standard Priithon modules into __main__
it fixes the display-hook and execs the Priithon RC file
"""
from __future__ import print_function

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import __main__
exec("from Priithon.all import *", __main__.__dict__)
exec("import Priithon.PriConfig as _priConfig", __main__.__dict__)

__main__.U._fixDisplayHook()
__main__.U._execPriithonRunCommands()

#20051117-TODO: CHECK if good idea  U.naSetArrayPrintMode(precision=4, suppress_small=0)

# python2 and 3 compatibility
import sys
if sys.version_info.major == 2:
    __main__.__builtins__.print = print
    _possible="""
    from future_builtins import filter, hex, map, oct, zip
    __main__.__builtins__.filter = filter
    __main__.__builtins__.hex    = hex
    __main__.__builtins__.map    = map
    __main__.__builtins__.oct    = oct
    __main__.__builtins__.zip    = zip"""
