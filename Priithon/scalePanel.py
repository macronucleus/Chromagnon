"""old: Dec 4, 2003  - unused !?"""

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import wx
# ID_ZSLIDER = 1000

class scalePanel( wx.Frame):
    def __init__(self, viewer, title=""):
        wx.Frame.__init__(self, None, -1, 'scale Panel') # , size=wx.Size(240,250))
        self.viewer = viewer

        self.SetTitle("scale 4: " + self.viewer.GetParent().GetTitle())

        self.min, self.max, self.mean, self.stddev = U.mmms(self.viewer.m_imgArr)
        self.range = self.max - self.min
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        t = wx.StaticText(self, -1, "mmms: %.1f %.1f  %.2f %.3f"%(self.min, self.max, self.mean, self.stddev))
        self.sizer.Add(t, 1, wx.EXPAND)


        self.sizerh1 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.sizerh1, 1, wx.EXPAND)

        self.button = wx.Button(self, 1003, "value")
        self.sizerh1.Add(self.button, 1, wx.EXPAND)
        wx.EVT_BUTTON(self, 1003, self.OnCloseWindow)

        self.t1 = wx.TextCtrl(self, 1004, "%.1f"%self.min)
        self.sizerh1.Add(self.t1, 1, wx.EXPAND)
        wx.EVT_TEXT(self, 1004, self.OnT)

        self.t2 = wx.TextCtrl(self, 1005, "%.1f"%self.max)
        self.sizerh1.Add(self.t2, 1, wx.EXPAND)
        wx.EVT_TEXT(self, 1005, self.OnT)



        self.sizerh2 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.sizerh2, 1, wx.EXPAND)

        self.button2= wx.Button(self, 1003, "percent")
        self.sizerh2.Add(self.button2, 1, wx.EXPAND)
        wx.EVT_BUTTON(self, 1013, self.OnCloseWindow)

        self.p1 = wx.TextCtrl(self, 1014, "0")
        self.sizerh2.Add(self.p1, 1, wx.EXPAND)
        wx.EVT_TEXT(self, 1014, self.OnP)

        self.p2 = wx.TextCtrl(self, 1015, "100")
        self.sizerh2.Add(self.p2, 1, wx.EXPAND)
        wx.EVT_TEXT(self, 1015, self.OnP)



        self.sizerh3 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.sizerh3, 1, wx.EXPAND)

        self.button3= wx.Button(self, 1023, "gamma")
        self.sizerh3.Add(self.button3, 1, wx.EXPAND)
        #wx.EVT_BUTTON(self, 1023, self.OnCloseWindow)

        self.g1 = wx.TextCtrl(self, 1024, "1")
        self.sizerh3.Add(self.g1, 1, wx.EXPAND)
        wx.EVT_TEXT(self, 1024, self.OnG)




        wx.EVT_CLOSE(self, self.OnCloseWindow)
        #         self.name = 'bubba'
        
        #     def OnCloseMe(self, event):
        #         print 'hit'
        #         self.Close(wx.true)
        self.sizer.Fit(self)

        ####self.SetAutoLayout(wx.true)
        self.SetSizer(self.sizer)

        #slider.SetBackgroundColour(wx.LIGHT_GREY)
        #self.SetBackgroundColour(wx.LIGHT_GREY)

        self.Show()
     
    def OnCloseWindow(self, event):
        # print 'close'
        self.Destroy()

    def OnT(self, event):
        try:
            t1 = float( self.t1.GetValue() )
            t2 = float( self.t2.GetValue() )
            self.viewer.changeHistogramScaling(t1,t2)
            # print t1
        except ValueError:
            pass

    def OnP(self, event):
        try:
            p1 = float( self.p1.GetValue() )
            p2 = float( self.p2.GetValue() )

            self.min, self.max, self.mean, self.stddev = U.mmms(self.viewer.m_imgArr)
            self.range = self.max - self.min
            t1  = self.min + self.range * p1 / 100.
            t2 = self.min + self.range * p2 / 100.
            self.viewer.changeHistogramScaling(t1,t2)
        except ValueError:
            pass
        # print t1

    def OnG(self, event):
        try:
            p1 = float( self.p1.GetValue() )
            p2 = float( self.p2.GetValue() )
            
            t1  = self.min + self.range * p1 / 100.
            t2 = self.min + self.range * p2 / 100.
            
            gamma = float( self.g1.GetValue() )

            if gamma < 0:
                self.viewer.cmcol()
            else:
                self.viewer.cmgray(gamma)
        except ValueError:
            pass
