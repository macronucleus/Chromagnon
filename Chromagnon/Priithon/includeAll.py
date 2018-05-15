"""this is the GUI (PyShell) startup file"""

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

print("   !!!  Welcome to Priithon !!!")
from Priithon.all import *
def _sebsDisplHook(v):
    if not v is None: # != None:
        import __main__ #global _
        #_ = v
        __main__._ = v
        print(U.myStr(v))
        
import sys
sys.displayhook = _sebsDisplHook
#print "debug: Pr/includeAll"
#if sys.argv[1:]:
#    import string
#    print "start->eval:", sys.argv[1:]
#    eval(string.join(sys.argv[1:]))

#20051117-TODO: CHECK if good idea  U.naSetArrayPrintMode(precision=4, suppress_small=0)

import wx
if hasattr(sys,'argv') and wx.GetApp() is not None: # CHECK: in embedded wxPython sys,.argv not defined
    # sys.app not defined yet
    wx.GetApp().GetTopWindow().SetTitle("priithon on %s" % wx.GetHostName())
del wx
del sys
