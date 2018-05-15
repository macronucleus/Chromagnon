"""PyShell is a python shell application."""
#seb: PriShell

# The next two lines, and the other code below that makes use of
# ``__main__`` and ``original``, serve the purpose of cleaning up the
# main namespace to look as much as possible like the regular Python
# shell environment.
import __main__
original = list(__main__.__dict__.keys())

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"
#seb __author__ = "Patrick K. O'Brien <pobrien@orbtech.com>"
#seb __cvsid__ = "$Id: PyShell.py,v 1.7 2004/03/15 13:42:37 PKO Exp $"
#seb __revision__ = "$Revision: 1.7 $"[11:-2]

import wx


"""
The main() function needs to handle being imported, such as with the
pyshell script that wxPython installs:

    #!/usr/bin/env python

    from wx.py.PyShell import main
    main()
"""

def main():
    """The main function for the PyShell program."""
    import wx

    #20071212: local class, just so that we don't have a "App" in __main__
    class App(wx.App):
        """PyShell standalone application."""

        def OnInit(self):
            import wx,sys
            from Priithon.py import shell
            wx.InitAllImageHandlers()
            self.frame = shell.ShellFrame(
                title="priithon on %s" % wx.GetHostName(),
                introText=' !!! Welcome to Priithon !!! \n'+
                '(Python %s on %s)' % (sys.version.replace('\n',' '), sys.platform),
                introStatus='Priithon: %s' % sys.argv)
            self.frame.SetSize((750, 525))
            self.frame.Show()
            self.SetTopWindow(self.frame)
            self.frame.shell.SetFocus()
            return True


    import __main__
    md = __main__.__dict__
    #seb keepers = original
    #seb keepers.append('App')
    #print keepers
    #['__builtins__', '__name__', '__file__', '__doc__', '__main__', 'App']
    #seb note: wee don't need to keep any of these 

    # Cleanup the main namespace, leaving the App class.
    for key in list(md.keys()):
        if key not in [
            #20071212 'App',
            '__author__',
            '__builtins__',
            #'__doc__',
            #'__file__',
            '__license__',
            #'__main__',
            '__name__',
            #'main',
            #'original',
            'shell',  # this is used in py/shell.py::shellMessage
            #'wx'
            ]:
            #['App', '__author__', '__builtins__', '__doc__', '__file__', '__license__', '__main__', '__name__', 'main', 'original', 'shell', 'wx']
            del md[key]


    # Mimic the contents of the standard Python shell's sys.path.
    #   python prepends '' if called as 'python'
    #   but    prepends '<path>' if called as 'python <path>/PriShell.py'
    #          in this case we replace sys.path[0] with ''
    import sys
    if sys.path[0]:
        sys.path[0] = ''

    # Create an application instance. (after adjusting sys.path!)
    sys.app = None # dummy to force Priithon.Y getting loaded
    app = App(0)
    #20070914 del md['App']
    # Add the application object to the sys module's namespace.
    # This allows a shell user to do:
    # >>> import sys
    # >>> sys.app.whatever
    sys.app = app

    #seb: load Priithon modules
    #exec "from Priithon.all import *" in __main__.__dict__
    #U._fixDisplayHook()
    try:
        # non-GUI part
        from Priithon import startupPriithon
    except:
        import traceback
        wx.MessageBox(traceback.format_exc(), 
                      "Exception while Priithon Startup", 
                      wx.ICON_ERROR)
    try:
        # GUI part
        __main__.Y._setAutosavePath()
        __main__.Y._fixGuiExceptHook()
    except:
        import traceback
        wx.MessageBox(traceback.format_exc(), 
                      "Exception while Priithon Startup", 
                      wx.ICON_ERROR)
    #import startupPriithon

    # macs tends to have this OpenGL float-texture bug
    # (all images (with pixelvals large compared to 1 appear black)
    # this does not catch the case when Priithon runs
    # remotely on Linux but uses a OSX X-display
    # 
    try:
        if '__WXMAC__' in wx.PlatformInfo:
            from Priithon import usefulX
            usefulX._bugXiGraphics()
    except:
        import traceback
        wx.MessageBox(traceback.format_exc(), 
                      "Exception while Priithon Startup", 
                      wx.ICON_ERROR)
    try:
        from Priithon import usefulX
        usefulX._glutInit(argv=sys.argv)
    except:
        import traceback
        wx.MessageBox(traceback.format_exc(), 
                      "Exception while Priithon Startup", 
                      wx.ICON_ERROR)

    del sys

    # Start the wxPython event loop.
    #del wx
    app.MainLoop()

if __name__ == '__main__':
    main()
