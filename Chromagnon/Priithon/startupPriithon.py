"""
this is the minimal priithon (non GUI) startup file
it imports all standard Priithon modules into __main__
it fixes the display-hook and execs the Priithon RC file
"""

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import __main__
exec "from Priithon.all import *" in __main__.__dict__
exec "import Priithon.PriConfig as _priConfig" in __main__.__dict__

__main__.U._fixDisplayHook()
__main__.U._execPriithonRunCommands()

#20051117-TODO: CHECK if good idea  U.naSetArrayPrintMode(precision=4, suppress_small=0)
