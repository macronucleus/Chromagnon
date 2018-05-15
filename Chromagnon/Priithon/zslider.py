from __future__ import print_function
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"
import wx
# ID_ZSLIDER = 1000

class ZSlider( wx.Frame):
    def __init__(self, nz, title=""):
        wx.Frame.__init__(self, None, -1, title) # , size=wx.Size(240,250))
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        #20080707 doOnXXXX event handler are now lists of functions
        self.doOnZchange       = [] # (zSec, ev)
        

        zmax = nz-1
        self.lastZ = -1
        self.zslider = wx.Slider(self, 1001, 0, 0, zmax,
                          wx.DefaultPosition, wx.DefaultSize,
                             #wx.SL_VERTICAL
                             wx.SL_HORIZONTAL
                             | wx.SL_AUTOTICKS | wx.SL_LABELS )
        self.zslider.SetTickFreq(5, 1)

        self.sizer.Add(self.zslider, 1, wx.EXPAND)
        #         panel = wx.Panel(self, -1)
        
        #         button = wx.Button(panel, 1003, "Close Me")
        #         button.SetPosition(wx.Point(15, 15))
        #         self.button = button       
        #         EVT_BUTTON(self, 1003, self.OnCloseMe)
        #wx.EVT_SCROLL_THUMBRELEASE(self, self.OnSlider)
        wx.EVT_SLIDER(self, self.zslider.GetId(), self.OnSlider)
        wx.EVT_CLOSE(self, self.OnCloseWindow)
        #         self.name = 'bubba'
        
        #     def OnCloseMe(self, event):
        #         print 'hit'
        #         self.Close(True)
        self.sizer.Fit(self)

        self.SetAutoLayout(True)
        self.SetSizer(self.sizer)

        self.zslider.SetBackgroundColour(wx.LIGHT_GREY)
        self.SetBackgroundColour(wx.LIGHT_GREY)

        self.Show()
     
    def OnCloseWindow(self, event):
        # print 'close'
        self.Destroy()

    def OnSlider(self, event):
        zz = event.GetInt()
        if zz != self.lastZ:
            self.lastZ = zz
            for f in self.doOnZchange:
                try:
                    f( zz, event )
                except:
                    from . import PriConfig
                    if PriConfig.raiseEventHandlerExceptions:
                        raise
                    else:
                        import sys, traceback
                        print(" *** error in doOnZchange **", file=sys.stderr)
                        traceback.print_exc()
                        print(" *** error in doOnZchange **", file=sys.stderr)

    #20080707 def doOnZchange(self, newZ):
    #20080707     print newZ
    #20080707     ###self.v.setImage(self.data[zz])
     
