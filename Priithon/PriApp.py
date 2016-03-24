"""
an easy way to make standalong applications:
import  and call _maybeExecMain from here
to make your module a
* PriithonApp *

IMPORT THIS FIRST - BEFORE FROM ALL IMPORT * - TO ENSURE A GOOD Y MODULE

1) call _maybeExecMain()
 a) you define a main() function and it gets called when the module is executed
 b) if you are not already inside a wxApp, one gets created for you (including event loop)
"""
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import sys 
if not hasattr(sys, "app"):
    sys.app = None # dummy to force Priithon.Y getting loaded

def _maybeExecMain():
    import sys,wx
    fr = sys._getframe(1)
    #print "__name__", __name__ 
    main = fr.f_globals['main']

    if fr.f_globals['__name__'] == "__main__":
        if wx.GetApp():
            main(*sys.argv)
        else:
            sys.app = wx.App()#PySimpleApp()
            main(*sys.argv)
            sys.app.MainLoop()
