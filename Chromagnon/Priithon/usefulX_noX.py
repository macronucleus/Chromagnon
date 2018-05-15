"""
Priithon Y module: all functions to do with GUI - 
  (!)BUT(!) this is the version that is imported in case 
  there is NO (X) GUI avalable
"""
#old"Priithon Y module: all functions to do with GUI - imports * from usefulX2"

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

##### from google:
#  #  > Btw, I just noticed that importing scipy assumes that wxPython is
#  #  > installed and DISPLAY must be working. When trying to import scipy
#  #  from a
#  #  > different computer without X connection, I get:
#  #  > 
#  #  > >>> import scipy
#  #  > 
#  #  > Gtk-WARNING **: cannot open display:
#  #  > 
#  #  > and python quits. Any idea how to fix this?

# import sys
# if hasattr(sys,'app'): # HACK: we use this as indicator for a graphic enabled environmaent
#     from usefulX2 import *
#     from usefulX2 import _bugXiGraphics #20070126 _bugOSX1036, 
#     # import some (most (not all) single-underscore
#     #from usefulX2 import  _error
#     #from usefulX2 import  _bugXiGraphics
#     #from usefulX2 import  _saveSessionDefaultPrefix
#     from usefulX2 import  _registerEventHandler
#     #from usefulX2 import  _define_vgAddXXX
#     #from usefulX2 import  _rectCode
#     #from usefulX2 import  _listFilesViewer
#     #from usefulX2 import  _listArrayViewer
#     #from usefulX2 import  _plotprofile_avgSize
#     #from usefulX2 import  _error0

# else:
if 1:
    def refresh():
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
    def FN(verbose=0):
        raise RuntimeError("* sorry no GUI *")
    def DIR(verbose=0):
        raise RuntimeError("* sorry no GUI *")


#del sys
