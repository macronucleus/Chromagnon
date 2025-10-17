"""provides the histogram scaling OpenGL-based panel for Priithon's ND 2d-section-viewer"""
from __future__ import print_function
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

#20051107 from wxPython   import wx
import wx
from wx import glcanvas
from OpenGL import GL
# from OpenGL import GLU   ## CHECK langur has not GLUT - debian glutg3
#seb     from OpenGL.GLUT import *
try:
    import Priithon_bin.glSeb as glSeb
except:
    pass

## import Numeric as Num
#from numarray import numeric as Num
#import numarray as na
import numpy as N
import traceback, sys#, socket
from . import PriConfig

###########################################from numarray import numeric as na
#----------------------------------------------------------------------

#  #timings
#  # Numeric
#  ms: 0.00
#  setHist00  ms: 0.00
#  setHist01  ms: 110.00
#  setHist1  ms: 380.00
#  setHist2  ms: 380.00
#  setHist3 ms: 380.00
#  setHist3b ms: 380.00
#  setHist4 ms: 380.00
#  setHist5 ms: 510.00

#  #numarray
#  setHist00  ms: 0.00
#  newshape: (65536, 2)
#  setHist01  ms: 0.00
#  setHist1  ms: 10.00
#  setHist2  ms: 20.00
#  setHist3 ms: 20.00
#  setHist3b ms: 20.00
#  setHist4 ms: 16630.00
#  setHist5 ms: 16630.00
#  ms: 10.00
#  setHist00  ms: 0.00
#  setHist01  ms: 0.00
#  setHist1  ms: 0.00
#  setHist2  ms: 0.00
#  setHist3 ms: 0.00
#  setHist3b ms: 0.00
#  setHist4 ms: 16790.00
#  setHist5 ms: 16800.00


#before going to numpy: (laptop windows)
# >>> Y.view(a)
# setHist00     ms: 0.01
# newshape: (10000, 2)
# setHist01     ms: 1.25
# setHist1 ms: 6.39
# setHist2 ms: 7.11
# setHist3 ms: 7.51
# setHist3b ms: 8.25
# setHist4 ms: 8.63
# setHist5 ms: 9.09
# >>> 
#with numpy:
# >>> Y.view(a)
# setHist00     ms: 0.01
# newshape: (10000, 2)
# setHist01     ms: 2.29
# setHist1 ms: 3.15
# setHist2 ms: 4.22
# setHist3 ms: 4.80
# setHist3b ms: 6.40
# setHist4 ms: 7.00
# setHist5 ms: 8.09

### without sebgl. module
# >>> Y.view(a)
# setHist00     ms: 0.01
# newshape: (10000, 2)
# setHist01     ms: 2.93
# setHist1 ms: 4.24
# setHist2 ms: 5.31
# setHist3 ms: 6.34
# setHist3b ms: 7.91
# setHist4 ms: 80.02
# setHist5 ms: 81.40


Menu_Reset = wx.NewId()
Menu_ZoomToBraces   = wx.NewId()
Menu_AutoFit   = wx.NewId()
Menu_Log   =  wx.NewId()
Menu_FitYToSeen   =  wx.NewId()
Menu_EnterScale   =  wx.NewId()
#20051117 Menu_Gamma   = 1004

Call_Yield_Before_SetCurrent = False

HistLogModeZeroOffset = .0001

class MyCanvasBase(glcanvas.GLCanvas):
    def __init__(self, parent, size=wx.DefaultSize):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size, style=wx.WANTS_CHARS)
        # wxWANTS_CHARS to get arrow keys on Windows

        #self.parent = parent
        self.init = False
        self.context = glcanvas.GLContext(self) # 20141124 cocoa
        self.m_w, self.m_h = 0,0
        
        self.zoomChanged = 1
        self.m_doViewportChange = 1
        self.m_sx, self.m_sy = 1,1
        self.m_tx, self.m_ty = 0,0
        
        # initial mouse position
        #seb self.lastx = self.x = 30
        #seb self.lasty = self.y = 30

        #20171225-PY2to3 deprecation warning use meth: EvtHandler.Bind -> self.Bind()
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        
        #wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        #wx.EVT_SIZE(self, self.OnSize)
        #wx.EVT_PAINT(self, self.OnPaint)
        #          EVT_LEFT_DOWN(self, self.OnMouseDown)  # needs fixing...
        #          EVT_LEFT_UP(self, self.OnMouseUp)
        #          EVT_MOTION(self, self.OnMouseMotion)
        
        # xPlotArrayCache
        #20080701 self.ca_xMin = 0
        #20080701 self.ca_xMax = 0
        #20080701 self.ca_n = 0
        

    def OnEraseBackground(self, event):
        pass # Do nothing, to avoid flashing on MSW.

    def OnSize(self, event):
        self.m_w, self.m_h = self.GetClientSize()#Tuple()
        if self.m_w <=0 or self.m_h <=0:
            #print "debug: HistogramCanvas.OnSize: self.m_w <=0 or self.m_h <=0", self.m_w, self.m_h
            return
        # do not change viewport if size negative
        self.m_doViewportChange = 1
        event.Skip()
        
    def OnPaint(self, event):
        try: # 20201122 MacOS BigSur
            dc = wx.PaintDC(self)
        except wx._core.wxAssertionError:
            pass
        except:
            return 
        if self.m_w <=0 or self.m_h <=0:
            #THIS IS AFTER wx.PaintDC -- OTHERWISE 100% CPU usage
            return 
        self.SetCurrent(self.context) # 20141124 Cocoa
        if not self.init:
            self.InitGL()
            self.init = 1

        if self.m_doViewportChange:
            #print "debug: m_doViewportChange", self.m_w, self.m_h
            GL.glViewport(0, 0, self.m_w, self.m_h)
            GL.glMatrixMode (GL.GL_PROJECTION)
            GL.glLoadIdentity ()
            GL.glOrtho (-.375, self.m_w-.375, -.375, self.m_h-.375, 1., -1.)
            GL.glMatrixMode (GL.GL_MODELVIEW)
            self.m_doViewportChange = False
            ####GL.glOrtho(  0, self.m_w, 0, self.m_h, -1,1);


        if self.zoomChanged:
            #print "debug: zoomChanged", self.m_sx,self.m_sy
            GL.glMatrixMode (GL.GL_MODELVIEW);
            GL.glLoadIdentity ();     
            GL.glTranslated(self.m_tx,self.m_ty,0);
            GL.glScaled(self.m_sx,self.m_sy,1.);          
            self.zoomChanged = 0

        self.OnDraw()

#      def OnMouseDown(self, evt):
#          self.CaptureMouse()

#      def OnMouseUp(self, evt):
#          self.ReleaseMouse()

#      def OnMouseMotion(self, evt):
#          if evt.Dragging() and evt.LeftIsDown():
#              self.x, self.y = self.lastx, self.lasty
#              self.x, self.y = evt.GetPosition()
#              self.Refresh(False)




class HistogramCanvas(MyCanvasBase):
    def __init__(self, parent, size=wx.DefaultSize):
        MyCanvasBase.__init__(self, parent, size=size)

        
        self.m_log = True # 20070724 - default log-scale
        self.fitYtoSeen = True # 20080731

        self.mouse_last_x, self.mouse_last_y = 0,0 # in case mouseIsDown happens without preceeding mouseDown
        self.dragCenter = False # in case mouseIsDown happens without preceeding mouseDown
        self.dragLeft   = True # in case mouseIsDown happens without preceeding mouseDown
        self.keepZoomedToBraces = True # 20080806

        #20171225-PY2to3 deprecation warning use meth: EvtHandler.Bind -> self.Bind()
        self.Bind(wx.EVT_MOUSE_EVENTS,  self.OnMouse)
        self.Bind(wx.EVT_MOUSEWHEEL,    self.OnWheel)
        
        #wx.EVT_MOUSE_EVENTS(self, self.OnMouse)
        #wx.EVT_MOUSEWHEEL(self, self.OnWheel)
        #wx.EVT_CLOSE(self, self.OnClose)
        self.MakePopupMenu()
        self.m_histPlotArray = None
        self.leftBrace = 0.
        self.rightBrace= 100.
        self.bandTobeGenerated = True
        self.m_imgChanged = 1
        self.m_histScaleChanged = 1
        self.colMap = None
        self.m_texture_list = None
        self.m_histGlRGB=(1.0, 1.0, 1.0)

        #20080707 doOnXXXX event handler are now lists of functions
        self.doOnBrace = [] # (self) # use self.leftBrace, self.rightBrace to get current brace positions
        self.doOnMouse = [] # (xEff, ev)

    def OnSize(self, event):
        MyCanvasBase.OnSize(self, event)
        self.fitY() # CHECK - efficiency could cache hm=na.maximum.reduce( self.m_histPlotArray[:,1])
        if self.keepZoomedToBraces:
            self.zoomToBraces()



    def InitGL(self):
        (self.m_w, self.m_h) = self.GetClientSize()#Tuple()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(  0, self.m_w, 0, self.m_h, -1,1)
        GL.glMatrixMode(GL.GL_MODELVIEW);

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        
        GL.glClearColor(1.0, 1.0, 1.0, 0.0)

        GL.glEnable(GL.GL_TEXTURE_1D)


    def OnDraw(self):
        # clear color and depth buffers
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT);


        #print "debug:", "ondraw", self.bandTobeGenerated, self.m_histScaleChanged,self.m_imgChanged

        if self.bandTobeGenerated:
            self.tex_nx = 256
            self.tex_ny = 1
            # self.m_gllist = glGenLists( 1 )
            if self.m_texture_list:
                GL.glDeleteTextures(self.m_texture_list)#glDeleteTextures  silently  ignores  zeros
                
            self.m_texture_list = GL.glGenTextures(1)

            GL.glBindTexture(GL.GL_TEXTURE_1D, self.m_texture_list)
            
            GL.glTexParameteri(GL.GL_TEXTURE_1D,GL.GL_TEXTURE_MIN_FILTER,GL.GL_NEAREST)
            #GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_1D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_NEAREST)
            #GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_MAG_FILTER,GL.GL_LINEAR)
            #    // GL_CLAMP causes texture coordinates to be clamped to the range [0,1] and is
            #    // useful for preventing wrapping artifacts when mapping a single image onto
            #    // an object.
            #GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_WRAP_S,GL.GL_CLAMP)
            #GL.glTexParameteri(GL.GL_TEXTURE_2D,GL.GL_TEXTURE_WRAP_T,GL.GL_CLAMP)
            GL.glTexParameteri(GL.GL_TEXTURE_1D,GL.GL_TEXTURE_WRAP_S,GL.GL_REPEAT)
            
            GL.glTexImage1D(GL.GL_TEXTURE_1D,0,  GL.GL_RGB, self.tex_nx, 0, 
                            GL.GL_LUMINANCE,GL.GL_UNSIGNED_BYTE, None)
        
            self.bandTobeGenerated = False

        if self.m_histScaleChanged:
            if self.colMap is not None:
                GL.glPixelTransferi(GL.GL_MAP_COLOR, True)
                # this part may be different depending on GL versions
                # here is __version__ = 3.0.2 on mac 10.7 py2.6
                mapsize = len(self.colMap[0])
                GL.glPixelMapfv(GL.GL_PIXEL_MAP_R_TO_R, mapsize, self.colMap[0] )
                GL.glPixelMapfv(GL.GL_PIXEL_MAP_G_TO_G, mapsize, self.colMap[1] )
                GL.glPixelMapfv(GL.GL_PIXEL_MAP_B_TO_B, mapsize, self.colMap[2] )
                original="""
                GL.glPixelMapfv(GL.GL_PIXEL_MAP_R_TO_R, self.colMap[0] )
                GL.glPixelMapfv(GL.GL_PIXEL_MAP_G_TO_G, self.colMap[1] )
                GL.glPixelMapfv(GL.GL_PIXEL_MAP_B_TO_B, self.colMap[2] )"""
            else:
                GL.glPixelTransferi(GL.GL_MAP_COLOR, False);

            self.m_histScaleChanged = False

        HEIGHT = self.m_h/ float(self.m_sy)
        try:

            if self.m_imgChanged:
                self.m_imgArr = N.arange(self.tex_nx).astype(N.uint8)
                #self.m_imgArr[:] = 128
                GL.glBindTexture(GL.GL_TEXTURE_1D, self.m_texture_list)
      
                if self.m_imgArr.dtype.type == N.uint8:
                    GL.glTexSubImage1D(GL.GL_TEXTURE_1D,0,  0, self.tex_nx, 
                                       GL.GL_LUMINANCE,GL.GL_UNSIGNED_BYTE, self.m_imgArr.tobytes()) #tostring())

                self.m_imgChanged = False

            GL.glColor3fv(self.m_histGlRGB);
            #20051205 GL.glColor3f(1.0, 1.0, 1.0);
            GL.glBindTexture(GL.GL_TEXTURE_1D, self.m_texture_list)
            GL.glBegin(GL.GL_QUADS)
            GL.glTexCoord2f( 0, 0);          GL.glVertex2f  ( self.leftBrace, HEIGHT*.1)
            GL.glTexCoord2f( 0, 1);          GL.glVertex2f  ( self.leftBrace, HEIGHT*.9)
            GL.glTexCoord2f( 1, 1);          GL.glVertex2f  ( self.rightBrace, HEIGHT*.9)
            GL.glTexCoord2f( 1, 0);          GL.glVertex2f  ( self.rightBrace, HEIGHT*.1)
            GL.glEnd()
        except:
            print('DEBUG: histogram.py: oops - set self.bandTobeGenerated')
            print('DEBUG: self.m_texture_list', self.m_texture_list)
            self.bandTobeGenerated  = True

        GL.glDisable(GL.GL_TEXTURE_1D);

        GL.glColor3f(0.0, 0.0, 1.0);
        if self.m_histPlotArray is not None:
            GL.glDrawArrays(GL.GL_LINE_STRIP, 0, self.m_histPlotArray.shape[0])
            #crashed here if my glSeb extension is compiler on a NVIDIA based OpenGL debian
            #haase@colobus:~: file  /usr/lib/libGL.so
            #/usr/lib/libGL.so: broken symbolic link to `libGL.so.1.2'

            #glSeb.glDrawArrays(GL.GL_LINE_STRIP, 0, self.m_histPlotArray.shape[0])

        braceW = 15        / float(self.m_sx)
        braceY1 = HEIGHT*.95
        #braceY0 = self.m_h*.05 /self.m_sy
        braceY0 = 0
        GL.glColor3f(1.0, 0.0, 0.0);
        
        #print self.leftBrace, self.m_h, self.m_sx
        x = self.leftBrace
        GL.glBegin(GL.GL_LINE_STRIP);
        GL.glVertex2d(x+braceW, braceY0);
        GL.glVertex2d(x,        braceY0);
        GL.glVertex2d(x,        braceY1);
        GL.glVertex2d(x+braceW, braceY1);
        GL.glEnd();
        
        x = self.rightBrace
        GL.glBegin(GL.GL_LINE_STRIP);
        GL.glVertex2d(x-braceW, braceY0);
        GL.glVertex2d(x,        braceY0);
        GL.glVertex2d(x,        braceY1);
        GL.glVertex2d(x-braceW, braceY1);
        GL.glEnd();
        
        GL.glEnable( GL.GL_TEXTURE_1D);
        
        self.SwapBuffers()

    def OnWheel(self, evt):
        # print "DEBUG: OnWheel"
        #delta = evt.GetWheelDelta()
        rot = evt.GetWheelRotation()      / 120. #HACK
        #linesPer = evt.GetLinesPerAction()
        #print "wheel:", delta, rot, linesPer
        zoomSpeed = 1. # .25
        
        #sfac = 1.05 ** (rot*zoomSpeed)
        sfac = 1.5 ** (rot*zoomSpeed)
        self.m_tx *= sfac
        #x = evt.m_x
        x = evt.GetPosition()[0]
        self.m_tx += x* (1.-sfac)
        self.m_sx *= sfac

        #20080731 self.zoomChanged = 1
        #20080731 #self.mouse_last_x, self.mouse_last_y = x,y
        #20080731 self.Refresh(0)
        self.fitY() #20080731 

    def OnMouse(self, ev):
        #x,y = ev.m_x, self.m_h-ev.m_y
        x, y = ev.GetPosition()
        y = self.m_h - y
        xEff = (x - self.m_tx) / float(self.m_sx)
        
        #  global evt
        #          evt = ev
        #          print dir(ev)
        
        midButt = ev.MiddleDown() or (ev.LeftDown() and ev.AltDown())
        midIsButt = ev.MiddleIsDown() or (ev.LeftIsDown() and ev.AltDown())
        rightButt = ev.RightDown() or (ev.LeftDown() and ev.ControlDown())

        # TODO CHECK 
        # Any application which captures the mouse in the beginning of some
        # operation must handle wxMouseCaptureLostEvent and cancel this
        # operation when it receives the event.
        # The event handler must not recapture mouse. 
        if self.HasCapture():
            if not (midIsButt or ev.LeftIsDown()):
                #print "#debug hist: capture release"
                self.ReleaseMouse()
        else:
            if midButt or ev.LeftDown():
                #print "#debug hist: capture mouse"
                self.CaptureMouse()

                
        #20070713 if ev.Leaving():
        #20070713     #if(self.dragging):
        #20070713     #    print "TODO"
        #20070713     ## leaving trigger  event - bug !!
        #20070713     return

        if rightButt:
            pt = ev.GetPosition()
            self.PopupMenu(self.menu, pt)

        elif midButt:
            self.mouse_last_x, self.mouse_last_y = x,y
        elif midIsButt: #ev.Dragging()
            dx = x-self.mouse_last_x
            dy = y-self.mouse_last_y
            sfac = 1.05 ** dy ##(round(dy/10.)*10)
            self.m_tx += dx
            self.m_tx *= sfac
            self.m_tx += x* (1.-sfac)
            self.m_sx *= sfac

            self.mouse_last_x, self.mouse_last_y = x,y
            self.keepZoomedToBraces = False
            #20080731 self.zoomChanged = 1
            #20080731 self.Refresh(0)
            self.fitY() #20080731


        elif ev.LeftDown():
            self.mouse_last_x, self.mouse_last_y = x,y

            braceSpace4= abs(self.rightBrace-self.leftBrace) /4.
#           if braceSpace4 < 8./ float(self.m_sx):
#               braceSpace4 = 8./ float(self.m_sx)
            braceCenter= (self.rightBrace+self.leftBrace) / 2.
            self.dragCenter = (abs(xEff-braceCenter) < braceSpace4) 
            self.dragLeft = (abs(xEff-self.leftBrace) < abs(xEff-self.rightBrace))
        elif ev.LeftIsDown(): #ev.Dragging()
            d =(x-self.mouse_last_x) / float(self.m_sx)
            if self.dragCenter:
                self.leftBrace  += d
                self.rightBrace += d
                #CHECK  if self.leftBrace>= self.rightBrace:
                #CHECK      self.leftBrace = self.rightBrace -1
            elif self.dragLeft:
                self.leftBrace += d
                #CHECK  if self.leftBrace>= self.rightBrace:
                #CHECK      self.leftBrace = self.rightBrace -1
            else:
                self.rightBrace += d
                #CHECK  if self.rightBrace <= self.leftBrace:
                #CHECK     self.rightBrace = self.leftBrace +1

            self.mouse_last_x, self.mouse_last_y = x,y
            self.keepZoomedToBraces = False

            for f in self.doOnBrace:
                try:
                    f(self)
                except:
                    if PriConfig.raiseEventHandlerExceptions:
                        raise
                    else:
                        print(" *** error in doOnBrace **", file=sys.stderr)
                        traceback.print_exc()
                        print(" *** error in doOnBrace **", file=sys.stderr)
                    
            self.Refresh(0)


        """#20080731 unused -- OnWheel is called instead (mac)
        #print ev.GetEventType()
        elif ev.GetEventType() == wx.EVT_MOUSEWHEEL:
            print "DEBUG: wx.EVT_MOUSEWHEEL"
            d = ev.GetWheelRotation() / 120.0
            sfac = 1.2 ** d
            deltax = self.m_w * self.m_sx * .1 * d;
            print "wx.EVT_MOUSEWHEEL", d,sfac,deltax,self.m_w
            self.m_tx += .5 * self.m_sx * self.m_w * (1.-sfac)
            self.m_sx *= sfac
            self.zoomChanged = 1
            self.Refresh(0)
        """
        if ev.LeftDClick():
            print("x,y: %d %d    xEff: %.3f" %(x,y, xEff))
        for f in self.doOnMouse:
            try:
                f(xEff, ev) # , 0) #bin)
            except:
                if PriConfig.raiseEventHandlerExceptions:
                    raise
                else:
                    print(" *** error in doOnMouse **", file=sys.stderr)
                    traceback.print_exc()
                    print(" *** error in doOnMouse **", file=sys.stderr)

    #20080707 def doOnMouse(self, xEff, bin):
    #20080707    pass

    def MakePopupMenu(self):
        """Make a menu that can be popped up later"""
        menu = wx.Menu()
        menu.Append(Menu_Reset, "zoom to full range")
        menu.Append(Menu_ZoomToBraces, "zoom to braces")
        menu.Append(Menu_AutoFit, "auto zoom + scale")
        #20051117 menu.Append(Menu_Gamma, "gamma...")

        menu.Append(Menu_Log, "log")
        menu.Append(Menu_FitYToSeen, "auto fit y axis to shown values")
        menu.Append(Menu_EnterScale, "scale to ...")

        #20171225-PY2to3 deprecation warning use meth: EvtHandler.Bind -> self.Bind()
        self.Bind(wx.EVT_MENU, self.OnReset, id=Menu_Reset)
        self.Bind(wx.EVT_MENU, self.zoomToBraces, id=Menu_ZoomToBraces)
        self.Bind(wx.EVT_MENU, self.autoFit,      id=Menu_AutoFit)
        self.Bind(wx.EVT_MENU, self.OnLog,        id=Menu_Log)
        self.Bind(wx.EVT_MENU, self.OnFitYToSeen, id=Menu_FitYToSeen)
        self.Bind(wx.EVT_MENU, self.OnEnterScale, id=Menu_EnterScale)
        
        #wx.EVT_MENU(self, Menu_Reset, self.OnReset)
        #wx.EVT_MENU(self, Menu_ZoomToBraces, self.zoomToBraces)
        #wx.EVT_MENU(self, Menu_AutoFit, self.autoFit)
        #wx.EVT_MENU(self, Menu_Log, self.OnLog)
        #wx.EVT_MENU(self, Menu_FitYToSeen, self.OnFitYToSeen)
        #wx.EVT_MENU(self, Menu_EnterScale, self.OnEnterScale)
        #20051117  wx.EVT_MENU(self, Menu_Gamma, self.OnMenuGamma)
        self.menu = menu

    def OnReset(self,ev):
        ma, mi = self.m_histPlotArray[-1,0], self.m_histPlotArray[0,0]
        if ma == mi: #CHECK
            ma += 1

        self.m_sx = self.m_w / float(ma-mi)
        self.m_tx = -mi * self.m_sx
        
        self.m_sy = 1
        self.m_ty = 0
        self.fitY()
        #  #  #          self.zoomChanged = 1
        #  #  #          self.Refresh(0)
        #      def OnFit(self,ev):
        #          self.fitXcontrast()

    def OnEnterScale(self,ev):
        s = wx.GetTextFromUser('''enter min max values \n
     and (optinally) a gamma value\n
     if no gamma given, gamma stays as before''',
                               "min max [gamma]",
                               '%s %s' %( self.leftBrace, self.rightBrace))
        if s=='':
            return
        f = s.split()
        if len(f)>2:
            gamma = float(f[2])
        else:
            gamma = None
        self.setBraces(float(f[0]), float(f[1])) #20060823 , gamma)
        if gamma and hasattr(self, "my_viewer"):
            self.my_viewer.gamma = gamma
            self.my_viewer.setGamma()
            self.my_viewer.changeHistogramScaling()
            self.my_viewer.updateHistColMap()
            
    def OnLog(self,ev=77777):
        if self.m_log:
            self.goLinear()
        else:
            self.goLog()            

    def OnFitYToSeen(self,ev):
        self.fitYtoSeen = not self.fitYtoSeen
        self.fitY()
        
    #def OnClose(self, ev):
    #    print "OnCLose() - done."

    def setHist(self, yArray, xMin, xMax):
        import time
        #x = time.clock()

        n = yArray.shape[0]
        #glSeb      print "setHist00     ms: %.2f"% ((time.clock()-x)*1000.0)
        if n < 2:
            raise ValueError("cannot have Histogram with less than 2 bins")
        if xMin == xMax:
            #WARN:? print " ** setHist: xMin == xMax ==",xMin, "!! set xMax+=1"
            xMax+=1

        if self.m_histPlotArray is None or \
               self.m_histPlotArray.shape[0] != n:
            self.m_histPlotArray = N.zeros((n,2), N.float32)
            #glSeb          print "newshape:", (n,2)
        #glSeb      print "setHist01     ms: %.2f"% ((time.clock()-x)*1000.0)
        if self.m_log:
            self.m_histPlotArray[:,1] = N.log(yArray+HistLogModeZeroOffset)
        else:
            self.m_histPlotArray[:,1] = yArray

        #glSeb      print "setHist1 ms: %.2f"% ((time.clock()-x)*1000.0)

        #20070605  FIXME TODO - comparison of floats !?
        if self.m_histPlotArray.shape[0] != n or \
              self.m_histPlotArray[0,   0] != xMin or \
              self.m_histPlotArray[-1,  0] != xMax:
           self.m_histPlotArray[:,0] = N.linspace(xMin,xMax, n)
        #glSeb      print "setHist2 ms: %.2f"% ((time.clock()-x)*1000.0)

        if 0:#not self.GetContext():
            testing="""
            print " ** setHist: no self.GetContext():"
            return"""

        #glSeb      print "setHist3 ms: %.2f"% ((time.clock()-x)*1000.0)
        #self.SetCurrent()
        #glSeb      print "setHist3b ms: %.2f"% ((time.clock()-x)*1000.0)
        #
        #glSeb.glVertexPointer(self.m_histPlotArray) # AM 20130203

        if Call_Yield_Before_SetCurrent:
            wx.Yield() # 20191029 this was very harmfull. Y.view does not work on most systems. But this was required for Dileptus particles_in_cells. Set Call_Yield_Before_SetCurrent before calling Y.view.

       	self.SetCurrent(self.context) # 20141124 Cocoa
        if sys.platform != 'linux':
            GL.glVertexPointerf(self.m_histPlotArray) # 20201224
        
        #glSeb       print "setHist4 ms: %.2f"% ((time.clock()-x)*1000.0)

        self.fitY()
        #glSeb      print "setHist5 ms: %.2f"% ((time.clock()-x)*1000.0)
        
    def goLog(self):
        self.m_log = True
        self.m_histPlotArray[:,1] = N.log(self.m_histPlotArray[:,1]+HistLogModeZeroOffset)
        self.SetCurrent(self.context) # 20141124
        #glSeb.glVertexPointer(self.m_histPlotArray) # AM 20130203
        GL.glVertexPointerf(self.m_histPlotArray)
        self.fitY()
        #self.Refresh(0)
        
    def goLinear(self):
        self.m_log = False
        self.m_histPlotArray[:,1] = N.exp(self.m_histPlotArray[:,1])-HistLogModeZeroOffset
        self.SetCurrent(self.context) # 20141124 cocoa
        #glSeb.glVertexPointer(self.m_histPlotArray) # AM 20130203
        GL.glVertexPointerf(self.m_histPlotArray)
        self.fitY()
        # self.Refresh(0)

    #20080707 def doOnBrace(self, left, right):
    #20080707    pass
    def fitY(self):
        if self.m_histPlotArray is None:
            return

        ys = self.m_histPlotArray[:,1]
        if self.fitYtoSeen:
            xs = self.m_histPlotArray[:,0]
            mi = -self.m_tx / float(self.m_sx)
            ma = mi + self.m_w / float(self.m_sx)
            shownIdxs = N.where((xs>=mi) & (xs<=ma))[0]
            if len(shownIdxs) == 0:
                return
            hm = ys[shownIdxs].max()
        else:
            hm = ys.max()

        if hm == 0:
            #nothing to fit -- done --raise "histogram 'empty'"
            return 
        if self.m_h == 0:
            #nothing to fit -- done --raise "window zero size"
            return
        self.m_sy = float(self.m_h) / hm *.95
        self.zoomChanged = 1
        self.Refresh(0)

    def zoomToBraces(self, ev=None): #fitXcontrast(self, ev=None):
        # self.m_ty =
        #print "#DEBUG: self.m_w", self.m_w
        self.keepZoomedToBraces=True # 20080806

        den = abs(float(self.rightBrace-self.leftBrace))
        if den == 0 or self.m_w <= 0:
            self.m_sx = 1
        else:
            self.m_sx = self.m_w / float(den)
        self.m_tx = - self.leftBrace * self.m_sx
        # self.m_sy =
        self.zoomChanged = 1
        self.Refresh(0)

    def autoFit(self, ev=None, amin=None, amax=None, autoscale=True):
        # self.setBraces(   )
        
        whereHelper = None
        if amin is None:
            #20080730 amin = float( self.m_histPlotArray[0,0] ) # pyOpenGL cannot handle numpy.float32
            if self.m_log:
                whereHelper = N.where(self.m_histPlotArray[:,1]>-1)[0]
            else:
                whereHelper = N.where(self.m_histPlotArray[:,1]>0)[0]

            if whereHelper is not None and len(whereHelper):
                amin = self.m_histPlotArray[ whereHelper[0],  0]
            elif hasattr(self, 'hist_min'): # setupHistArr in splitND
                amin = self.hist_min
                amax = self.hist_max
                #print self.hist_min
            else:
                amin = float( self.m_histPlotArray[0,0] ) # pyOpenGL cannot handle numpy.float32
                #amin = self.m_histPlotArray[ whereHelper[0],  0]"""
        if amax is None:
            #20080730 amax = float( self.m_histPlotArray[-1,0] ) # pyOpenGL cannot handle numpy.float32
            if whereHelper is None:
                if self.m_log:
                    whereHelper = N.where(self.m_histPlotArray[:,1]>-1)[0]
                else:
                    whereHelper = N.where(self.m_histPlotArray[:,1]>0)[0]

            if whereHelper is not None and len(whereHelper):
                amax = self.m_histPlotArray[ whereHelper[-1],  0]
            else:
                amax = float( self.m_histPlotArray[-1,0] ) # pyOpenGL cannot handle numpy.float32
        self.leftBrace =  float(amin)  # fix numpy types like uint16 coming from a.min()
        self.rightBrace=  float(amax)
        #self.Refresh(0)
        if autoscale:
            self.zoomToBraces()
        else:
            self.Refresh(0)
        for f in self.doOnBrace:
            try:
                f(self)
            except:
                if PriConfig.raiseEventHandlerExceptions:
                    raise
                else:
                    print(" *** error in doOnBrace **", file=sys.stderr)
                    traceback.print_exc()
                    print(" *** error in doOnBrace **", file=sys.stderr)


    def setBraces(self, l,r): #20060823 , gamma=None):
        self.leftBrace = float(l)
        self.rightBrace= float(r)
        for f in self.doOnBrace:
            try:
                f(self)
            except:
                if PriConfig.raiseEventHandlerExceptions:
                    raise
                else:
                    print(" *** error in doOnBrace **", file=sys.stderr)
                    traceback.print_exc()
                    print(" *** error in doOnBrace **", file=sys.stderr)

        #20080707 self.doOnBrace(self.leftBrace, self.rightBrace) #20060823, gamma)
        self.Refresh(0)

    #20051117
    '''
    def OnMenuGamma(self, ev):
        self.gammawin = GammaPopup(self)

        # Show the popup right below or above the button
        # depending on available screen space...
        #btn = evt.GetEventObject()
        #pos = btn.ClientToScreen( (0,0) )
        #sz =  btn.GetSize()
        #win.Position(pos, (0, sz.height))
        #self.gammawin.Position(self.frame.GetPosition(), (0,0) )
        
        self.gammawin.Show()
    '''
        
def hist(histArray, hMin, hMax, title=""):
    #      global hframe
    #      global hcanvas
    frame = wx.Frame(None, -1, title)
    canvas = HistogramCanvas(frame, size=(400,100))

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(canvas, 1, wx.EXPAND | wx.ALL, 5);
    frame.SetSizer(sizer);
    sizer.SetSizeHints(frame);
    frame.SetAutoLayout(1)
    sizer.Fit(frame)

    frame.Show(1)
    wx.Yield() ## other raise "window zero size" in fitY(self)
    canvas.setHist(histArray, hMin, hMax)

    return canvas


'''
class GammaPopup(wx.Frame):
    def __init__(self, histParent):
        wx.Frame.__init__(self, histParent, -1,"") # , size=wx.Size(240,250))

        self.SetTitle("gamma of v:%s"%\
                      wx.GetTopLevelParent(histParent).GetTitle())
        self.gamma = 1

        topframeChildn=wx.GetTopLevelParent(histParent).GetChildren() #[splitter]
        #[<Priithon.splitND.MySplitter; proxy of C++ wxSplitterWindow instance at _50cb6a08_p_wxSplitterWindow>]
        splitter = topframeChildn[0]
        #>>> _[0].GetChildren()
        #[<wx._windows.Panel; proxy of C++ wxPanel instance at _68a3a008_p_wxPanel>, <Priithon.histogram.HistogramCanvas; proxy of C++ wxGLCanvas instance at _88569e08_p_wxGLCanvas>]
        viewerpanel = splitter.GetChildren()[0]
        viewerpanelChildn=viewerpanel.GetChildren()
        #>>> _[0].GetChildren()
        #[<wx._controls.StaticText; proxy of C++ wxStaticText instance at _f0447708_p_wxStaticText>, <wx._controls.StaticText; proxy of C++ wxStaticText instance at _c8537608_p_wxStaticText>, <Priithon.viewer.GLViewer; proxy of C++ wxGLCanvas instance at _b812a408_p_wxGLCanvas>]
        viewer= viewerpanelChildn[2]
        self.v = viewer
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(wx.StaticText(self, -1, "gamma:"))#, 0, wx.EXPAND)
        self.txtctrl = wx.TextCtrl(self, -1, "%.2f"%self.gamma, size=(40,-1))
        self.sizer.Add(self.txtctrl, 0)#, wx.EXPAND)
        self.slider = wx.Slider(self, -1, self.gamma*100, 0, 1000, size=(200,-1))
        self.sizer.Add(self.slider, 1)#, wx.EXPAND)
        #self.sizer.Add(wx.StaticText(self, -1, "%"))#, 0, wx.EXPAND)

        #Layout sizers
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        self.sizer.Fit(self)

        wx.EVT_SLIDER(self, self.slider.GetId(), self.OnSlider)
        wx.EVT_TEXT(self, self.txtctrl.GetId(), self.OnText)        
        #wx.EVT_KEY_DOWN(self, self.OnKeyDown)

    def ProcessLeftDown(self, evt):
        #print "ProcessLeftDown"
        #self.Dismiss()
        return False

    #def OnDismiss(self):
    #   print "OnDismiss"

    def OnKeyDown(self, evt):
        print "OnKeyDown"
        #self.Dismiss()


    def OnSlider(self, ev):
        self.gamma = self.slider.GetValue() / 100.
        self.txtctrl.SetValue("%.2f"%self.gamma)
        self.updateGamma()

    def OnText(self,ev):
        try:
            g = float(ev.GetString())
        except:
            return
        if g<0:
            return
        
        self.gamma = g
        self.slider.SetValue(100*g)
        self.updateGamma()

    def updateGamma(self):
        self.v.cmgray(self.gamma)
        

'''
