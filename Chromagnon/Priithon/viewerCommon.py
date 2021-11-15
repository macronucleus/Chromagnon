"""
provides the bitmap OpenGL panel for Priithon's ND 2d-section-viewer 

common base class for single-color and multi-color version
"""
from __future__ import print_function
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"


### NOTES 2008-July-04:
###
### rename m_init to m_glInited
### fix wheel for 2d images
### 
### revive idea that an image (texture) is handled within a m_moreGlLists (for multi-color viewer)
###
### indices in  m_moreGlLists[idx] are always growing - remove just sets m_moreGlLists[idx] to None



import six
import wx
from wx import glcanvas as wxgl
#from wxPython import glcanvas
from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as N
import traceback, sys
from . import PriConfig

bugXiGraphics = 0

Menu_Zoom2x      = wx.NewId()
Menu_ZoomCenter  = wx.NewId()
Menu_Zoom_5x     = wx.NewId()
Menu_ZoomReset   = wx.NewId()
Menu_ZoomOut     = wx.NewId()
Menu_ZoomIn      = wx.NewId()
Menu_Color       = wx.NewId()
Menu_Reload       = wx.NewId()
Menu_chgOrig     = wx.NewId()
Menu_Save = wx.NewId()
Menu_SaveScrShot = wx.NewId()
Menu_SaveClipboard = wx.NewId()
Menu_Assign = wx.NewId()
Menu_noGfx = wx.NewId()
Menu_aspectRatio = wx.NewId()
Menu_rotate = wx.NewId()
Menu_grid        = wx.NewId()
Menu_ColMap = [wx.NewId() for i in range(8)]


class GLViewerCommon(wxgl.GLCanvas):
    def __init__(self, parent, size=wx.DefaultSize, originLeftBottom=None):#, depth=32):
        wxgl.GLCanvas.__init__(self, parent, -1, size=size, style=wx.WANTS_CHARS)#, attribList=[wxgl.WX_GL_DOUBLEBUFFER, wxgl.WX_GL_RGBA, wxgl.WX_GL_DEPTH_SIZE, depth])
        # wxWANTS_CHARS to get arrow keys on Windows

        self.error = None
        self.m_doViewportChange = True
    
        # NEW 20080701:  in new coord system, integer pixel coord go through the center of pixel
        self.x00 = -.5 # 0
        self.y00 = -.5 # 0
        self.m_x0=None #20070921 - call center() in OnPaint -- self.x00
        self.m_y0=None #20070921 - call center() in OnPaint -- self.y00
        self.m_scale=1
        self.m_aspectRatio = 1.
        self.m_rot=0.
        self.m_zoomChanged = True # // trigger a first placing of image
        self.m_sizeChanged = True
        self.keepCentered = True

        #20080722 self.m_pixelGrid_Idx = None
        self.m_pixelGrid_state = 0 # 0-off, 1-everyPixel, 2- every 10 pixels

        self.m_init   = False
        self.context = wxgl.GLContext(self) # 20141124 cocoa

        self.m_moreGlLists = []
        self.m_moreGlLists_enabled = []
        self.m_moreMaster_enabled = True
        self.m_moreGlLists_dict = {} # map 'name' to list of idx in m_moreGlLists
        # a given idx can be part of multiple 'name' entries
        # a given name entry can contain a given idx only once
        # a name that is a tuple, has a special meaning: if name == zSecTuple - 
        #               auto en-/dis-able gfxs in splitNDcommon::OnZZSlider (ref. zlast)
        #               UNLESS gfx idx is in self.m_moreGlLists_nameBlacklist
        self.m_moreGlLists_nameBlacklist = set()
        self.m_moreGlLists_NamedIdx = {} # map str to int or None -- this is helpful for reusing Idx for "changing" gllists
                                         # if name (type str) wasn't used before, it defaults to None (20080722)

        self.m_moreGlListReuseIdx=None
        self.m_wheelFactor = 2 ** (1/3.) #1.189207115002721 # >>> 2 ** (1./4)  # 2
        self.mouse_last_x, self.mouse_last_y = 0,0 # in case mouseIsDown happens without preceeding mouseDown

        #20080707 doOnXXXX event handler are now lists of functions
        #                x,y are (corrected, float value) pixel position
        #                ev is the wx onMouseEvent obj -- use ev.GetEventObject() to get to the viewer object
        #20080707-unused self.doOnFrameChange = [] # no args
        self.doOnMouse       = [] # (x,y, ev)
        self.doOnLDClick     = [] # (x,y, ev)
        self.doOnLDown       = [] # (x,y, ev)
        

        #wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)

        #20171225-PY2to3 deprecation warning use meth: EvtHandler.Bind -> self.Bind()
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        #wx.EVT_SIZE(self, self.OnSize)
        #evtHandler.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse)
        #wx.EVT_MOUSEWHEEL(self, self.OnWheel)
        #wx.EVT_MOUSE_EVENTS(self, self.OnMouse)
        self.Bind(wx.EVT_SIZE, self.OnSize)


    def setPixelGrid(self, ev=None):
        if   self.m_pixelGrid_state == 0:  # old state == 0 == 'off'             -> new state=1
            self.m_pixelGrid_state = 1
            self.drawPixelGrid(1, 1)
        elif self.m_pixelGrid_state == 1:  # old state == 1 == 'every pixel'     -> new state=2
            self.m_pixelGrid_state = 2
            self.drawPixelGrid(10, 10)
        elif self.m_pixelGrid_state == 2:  # old state == 2 == 'every 10 pixels'  -> new state=0
            self.m_pixelGrid_state = 0

            #self.newGLListRemove( self.m_pixelGrid_Idx )
            self.newGLListEnable( 'm_pixelGrid_Idx', False )

    def drawPixelGrid(self, spacingY, spacingX, color=(1,0,0), width=1):
        self.newGLListNow(idx='m_pixelGrid_Idx')
        glLineWidth(width)
        glColor3f(*color)
        glTranslate(-.5,-.5 ,0)  # 20080701:  in new coord system, integer pixel coord go through the center of pixel

        glBegin(GL_LINES)
        ny = self.pic_ny
        nx = self.pic_nx
        if self.m_originLeftBottom == 8:
            nx = (nx-1)*2
        for y in range(0,ny+1, spacingY):
            glVertex2d(0, y)
            glVertex2d(nx, y)
        for x in range(0,nx+1, spacingX):
            glVertex2d(x, 0)
            glVertex2d(x, ny)
        glEnd()

        glTranslate(.5,.5 ,0)  # 20080701:  in new coord system, integer pixel coord go through the center of pixel            
        self.newGLListDone(enable=True, refreshNow=True)
        





    def newGLListNow(self, name=None, idx=None) : # , i):
        """
        call this immediately before you call a bunch of gl-calls
        issue newGLListDone() when done
        OR newGLListAbort() when there is problem and
            the glist should get cleared

        create new or append to dict entry 'name' when done
            if name is a list (! not tuple !) EACH list-items is used
            a tuple is interpreted as "z-sect-tuple" and means that this gllist 
                gets automacically en-/dis-abled with z-slider entering/leaving that section
                (see on splitNDcommon::OnZZSlider)
        if idx is not None:  reuse and overwrite existing gllist
        if idx is of type str: on first use, same as None; but on subsequent uses, reuse and overwrite 
        """
        self.m_moreGlListReuseIdx = idx
        self.SetCurrent(self.context)
        if isinstance(idx, six.string_types):
            idx = self.m_moreGlLists_NamedIdx.get(idx) # Never raises an exception if k is not in the map, instead it returns x. x is optional; when x is not provided and k is not in the map, None is returned. 
            if idx is None:
                self.curGLLIST = glGenLists( 1 )
            else:
                try:
                    self.curGLLIST = self.m_moreGlLists[idx]
                except IndexError: ## vgRemoveAll might have been called
                    self.curGLLIST = glGenLists( 1 )
                    del self.m_moreGlLists_NamedIdx[self.m_moreGlListReuseIdx] # will get reset in newGLListDone()
                else:
                    if self.curGLLIST is None:   # glList was deleted Y.vgRemove
                        self.curGLLIST = glGenLists( 1 )

        elif idx is None or self.m_moreGlLists[idx] is None:
            self.curGLLIST = glGenLists( 1 )
        else:
            self.curGLLIST = self.m_moreGlLists[idx]

        self.curGLLISTname  = name
        glNewList( self.curGLLIST, GL_COMPILE )

    def newGLListAbort(self):
        glEndList()
        glDeleteLists(self.curGLLIST, 1)
        if isinstance(self.m_moreGlListReuseIdx, six.string_types):
            try:
                del self.m_moreGlLists_NamedIdx[self.m_moreGlListReuseIdx] # CHECK
            except KeyError:
                pass # was not in dict yet
        self.m_moreGlListReuseIdx = None

    def newGLListDone(self, enable=True, refreshNow=True):
        glEndList()
        if isinstance(self.m_moreGlListReuseIdx, six.string_types):
            idx = self.m_moreGlLists_NamedIdx.get(self.m_moreGlListReuseIdx)
        else:
            idx = self.m_moreGlListReuseIdx

        if idx is not None:
            self.m_moreGlLists[idx] = self.curGLLIST # left side might have been None
            self.m_moreGlLists_enabled[idx] = enable
        else:
            idx = len(self.m_moreGlLists)
            self.m_moreGlLists.append( self.curGLLIST )
            self.m_moreGlLists_enabled.append( enable )
        
        self.newGLListNameAdd(idx, self.curGLLISTname)

        # remember named idx for future re-use
        if isinstance(self.m_moreGlListReuseIdx, six.string_types):
            self.m_moreGlLists_NamedIdx[self.m_moreGlListReuseIdx] = idx
        self.m_moreGlListReuseIdx = None

        if refreshNow:
            self.Refresh(0)
        return idx

    def newGLListNameAdd(self, idx, name):
        if type(name) != list:
            name = [ name ]

        # make sure cur idx is in each name-list; create new name-list or append to existing, as needed 
        for aName in name:
            if aName is not None:
                try:
                    l = self.m_moreGlLists_dict[aName]
                    try:
                        l.index(idx)  # don't do anything if aName is already in
                    except ValueError:
                        l.append(idx)
                except KeyError:
                    self.m_moreGlLists_dict[aName] = [idx]
    def newGLListNameRemove(self, idx, name):
        if type(name) != list:
            name = [ name ]

        # remove idx from list given by each name
        for aName in name:
            if aName is not None:
                try:
                    l = self.m_moreGlLists_dict[aName]
                    try:
                        l.remove( idx )
                    except ValueError:
                        # don't do anything if idx was not part of aName
                        pass
                except KeyError:
                    pass

    def newGLListRemove(self, idx, refreshNow=True):
        """
        instead of 'del' just set entry to None
        this is to prevent, shifting of all higher idx
        20090107: but do 'del' for last entry - no trailing Nones

        self.m_moreGlLists_dict is cleaned properly
        """
        #20070712 changed! not 'del' - instead set entry to None
        #20070712    ---- because decreasing all idx2 for idx2>idx is complex !!!
        #untrue note;  --- old:
        #untrue note; be careful: this WOULD change all indices (idx) of GLLists
        #untrue note; following idx
        #untrue note!!: if you can not accept that: you should call
        #untrue note!!:   newGLListEnable(idx, on=0)

#       if self.m_moreGlLists_texture[idx] is not None:
#           glDeleteTextures( self.m_moreGlLists_texture[idx] )
#           del self.m_moreGlLists_img[idx]

        if isinstance(idx, six.string_types):
            idx=self.m_moreGlLists_NamedIdx[idx]
        elif idx<0:
            idx += len(self.m_moreGlLists)

        if self.m_moreGlLists[idx]: # could be None - # Note: Zero is not a valid display-list index.
            glDeleteLists(self.m_moreGlLists[idx], 1)
        #20070712 del self.m_moreGlLists[idx]
        #20070712 del self.m_moreGlLists_enabled[idx]
        if idx == len(self.m_moreGlLists)-1: # 20090107
            del self.m_moreGlLists[idx]
            del self.m_moreGlLists_enabled[idx]
        else:
            self.m_moreGlLists[idx] = None
            self.m_moreGlLists_enabled[idx] = None
        self.m_moreGlLists_nameBlacklist.discard(idx)

        #remove idx from 'name' dict entry
        #   remove respective dict-name if it gets empty
        _postposeDelList = [] # to prevent this error:dictionary changed size during iteration
        for name,idxList in self.m_moreGlLists_dict.items():
            try:
                idxList.remove(idx)
                if not len(idxList):
                    _postposeDelList.append(name)
            except ValueError:
                pass
        for name in _postposeDelList:
            del self.m_moreGlLists_dict[name]

        if refreshNow:
            self.Refresh(0)

    def newGLListEnable(self, idx, on=True, refreshNow=True):
        """
        ignore moreGlList items that are None !
        """
        if isinstance(idx, six.string_types):
            idx=self.m_moreGlLists_NamedIdx[idx]
        if self.m_moreGlLists_enabled[idx] is not None:
            self.m_moreGlLists_enabled[idx] = on
        if refreshNow:
            self.Refresh(0)

    def newGLListEnableByName(self, name, on=True, skipBlacklisted=False, refreshNow=True):
        """
        "turn on/off" all gfx whose idx is in name-dict
        if skipBlacklisted: IGNORE idx if contained in moreGlLists_nameBlacklist
        ignore moreGlList items that are None !
        """
        for idx in self.m_moreGlLists_dict[name]:
            if self.m_moreGlLists_enabled[idx] is not None and\
                    (not skipBlacklisted or idx not in self.m_moreGlLists_nameBlacklist):
                self.m_moreGlLists_enabled[idx] = on
        if refreshNow:
            self.Refresh(0)

    def newGLListRemoveByName(self, name, refreshNow=True):
        for idx in self.m_moreGlLists_dict[name]:
            if self.m_moreGlLists[idx]:
                glDeleteLists(self.m_moreGlLists[idx], 1)
            # refer to comment in newGLListRemove() !!!
            self.m_moreGlLists[idx]  = None
            self.m_moreGlLists_enabled[idx]  = None
        del self.m_moreGlLists_dict[name]

        # clean up other name entries in dict
        for name,idxList in list(self.m_moreGlLists_dict.items()):
            for i in range(len(idxList)-1,-1,-1):
                if self.m_moreGlLists[idxList[i]] is None:
                    del idxList[i]
            if not len(idxList):
                del self.m_moreGlLists_dict[name]


        #20090505: remove trailing None's
        for idx in range(len(self.m_moreGlLists)-1, -1, -1):
            if self.m_moreGlLists[idx] is None:
                del self.m_moreGlLists[idx]
                del self.m_moreGlLists_enabled[idx]
            else:
                break

        if refreshNow:
            self.Refresh(0)

    def newGLListRemoveAll(self, refreshNow=True):
        """
        this really removes all GLList stuff
        idx values will restart at 0
        here nothing gets "only" set to None
        """
        for li in self.m_moreGlLists:
            if li:  # Note: Zero is not a valid display-list index.
                glDeleteLists(li, 1)
        self.m_moreGlLists = []
        self.m_moreGlLists_enabled = []
        #self.m_moreMaster_enabled = 1
        self.m_moreGlLists_dict.clear()
        self.m_moreGlLists_nameBlacklist.clear()
        self.m_moreGlLists_NamedIdx.clear()

        if refreshNow:
            self.Refresh(0)
        




    def OnNoGfx(self, evt):
        #fails on windows:
        if wx.Platform == '__WXMSW__': ### HACK check LINUX GTK WIN MSW
            menuid  = self.m_menu.FindItem("hide all gfx")
            self.m_menu.FindItemById(menuid).Check( not evt.IsChecked() )
            self.m_moreMaster_enabled ^= 1
        else:
            self.m_moreMaster_enabled = not evt.IsChecked()

        self.Refresh(0)

    def OnChgNoGfx(self):
        self.m_moreMaster_enabled ^= 1
        menuid  = self.m_menu.FindItem("hide all gfx")
        self.m_menu.FindItemById(menuid).Check(self.m_moreMaster_enabled)
        self.Refresh(0)

    def setAspectRatio(self, y_over_x, refreshNow=1):
        """
        strech images in y direction
        use negative value to mirror
        """
        
        self.m_aspectRatio=y_over_x
        
        self.m_zoomChanged=True
        if refreshNow:
            self.Refresh()

    def setRotation(self, angle=90, refreshNow=1):
        """rotate everything by angle in degrees
        """
        
        self.m_rot = angle
        
        self.m_zoomChanged=1
        if refreshNow:
            self.Refresh()

    def center(self, refreshNow=True):
        self.keepCentered = True

        ws = N.array([self.m_w, self.m_h])
        nx = self.pic_nx
        if self.m_originLeftBottom == 8:
            nx = (self.pic_nx-1) * 2
        ps = N.array([nx, self.pic_ny])
        s  = self.m_scale
        self.m_x0, self.m_y0 = (ws-ps*s) // 2
        self.m_zoomChanged = True
        if refreshNow:
            self.Refresh(0)
        
    def zoom(self, zoomfactor=None, cyx=None, absolute=True, refreshNow=True):
        """
        set new zoom factor to zoomfactor
        if absolute is False
           adjust current zoom factor to
              "current"*zoomfactor
        if zoomfactor is None:
            zoomfactor stays unchanged

        if cyx is None:
            image center stays center
        otherwise, image will get "re-centered" to cyx beeing the new center
        """
        if zoomfactor is not None:
            if absolute:
                fac = zoomfactor / self.m_scale
            else:
                fac = zoomfactor
            self.m_scale *= fac
        #self.center()

        w2 = self.m_w/2
        h2 = self.m_h/2
        if cyx is None:
            self.m_x0 = w2 - (w2-self.m_x0)*fac
            self.m_y0 = h2 - (h2-self.m_y0)*fac
        else:
            cy,cx = cyx
            self.m_x0 = w2 - cx*self.m_scale
            self.m_y0 = h2 - cy*(self.m_scale*self.m_aspectRatio)
            
        self.m_zoomChanged = True
        if refreshNow:
            self.Refresh(0)

    def doReset(self, ev=None, refreshNow=True):
        self.keepCentered = False

        self.m_x0=self.x00
        self.m_y0=self.y00
        self.m_scale=1.
        self.m_rot=0.
        self.m_aspectRatio = 1.
        self.m_zoomChanged = True
        if refreshNow:
            self.Refresh(0)



    def OnCenter(self, event=None): # was:On30
        self.center()
    def OnZoomOut(self, event=77777): # was:On31
        fac = 1./1.189207115002721 # >>> 2 ** (1./4)
        self.zoom(fac, absolute=False)        
    def OnZoomIn(self, event=77777): # was:On32
        fac = 1.189207115002721 # >>> 2 ** (1./4)
        self.zoom(fac, absolute=False)

#      def On41(self, event):
#          self.doShift(- self.m_scale , 0)
#      def On42(self, event):
#          self.doShift(+ self.m_scale , 0)
#      def On43(self, event):
#          self.doShift(0,  + self.m_scale)
#      def On44(self, event):
#          self.doShift(0,  - self.m_scale)

    def quaterShiftOffsetLeft(self):
        n= self.pic_nx / 4
        if self.m_originLeftBottom == 8:
            n= (n-1) * 2
        self.doShift(- self.m_scale*n , 0)
    def quaterShiftOffsetRight(self):
        n= self.pic_nx / 4
        if self.m_originLeftBottom == 8:
            n= (n-1) * 2
        self.doShift(+ self.m_scale*n , 0)
    def quaterShiftOffsetUp(self):
        n= self.pic_ny / 4
        self.doShift(0,  + self.m_scale*n)
    def quaterShiftOffsetDown(self):
        n= self.pic_ny / 4
        self.doShift(0,  - self.m_scale*n)

    def doShift(self, dx,dy):
        self.keepCentered = False

        self.m_x0 += dx
        self.m_y0 += dy
        
        self.m_zoomChanged = True
        self.Refresh(0)

    def OnMouse(self, ev):
        self._onMouseEvt = ev  # be careful - only use INSIDE a handler function that gets call from here
        if self.m_x0 is None:
            return # before first OnPaint call

        self.SetCurrent(self.context)        
        #x,y = ev.m_x,  self.m_h-ev.m_y
        x, y = ev.GetPosition() # 20141127
        y = self.m_h - y
        xEff_float, yEff_float= gluUnProject(x,y,0)[:2]

        # 20080701:  in new coord system, integer pixel coord go through the center of pixel

        #20080707-alwaysCall_DoOnMouse xyEffInside = False
        nx = self.pic_nx
        ny = self.pic_ny
        #20080707 xyEffVal = 0

        import sys
        if sys.platform != 'win32' and ev.Entering():
            self.SetFocus()

        if self.m_originLeftBottom == 0:
            yEff_float = ny-1 - yEff_float
        #elif self.m_originLeftBottom == 1:
        #  pass

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
                self.ReleaseMouse()
        else:
            if midButt or ev.LeftDown():
                self.CaptureMouse()

        #20070713 if ev.Leaving():
        #20070713     ## leaving trigger  event - bug !!
        #20070713     return

        if midButt:
            self.mouse_last_x, self.mouse_last_y = x,y
        elif midIsButt: #ev.Dragging()
            self.keepCentered = False
            if ev.ShiftDown() or ev.ControlDown():
                #dx = x-self.mouse_last_x
                dy = y-self.mouse_last_y

                fac = 1.05 ** (dy)
                self.m_scale *= fac
                w2 = self.m_w/2
                h2 = self.m_h/2
                self.m_x0 = w2 - (w2-self.m_x0)*fac
                self.m_y0 = h2 - (h2-self.m_y0)*fac
                self.m_zoomChanged = True

            else:
                self.m_x0 += (x-self.mouse_last_x) #/ self.sx
                self.m_y0 += (y-self.mouse_last_y) #/ self.sy
            self.m_zoomChanged = 1
            self.mouse_last_x, self.mouse_last_y = x,y
            self.Refresh(0)

        elif rightButt:
            #20060726 self.mousePos_remembered_x, self.mousePos_remembered_y = ev.GetPositionTuple()
            pt = ev.GetPosition()
            self.PopupMenu(self.m_menu, pt)
        elif ev.LeftDown():
            for f in self.doOnLDown:
                try:
                    f(xEff_float,yEff_float, ev)
                except:
                    if PriConfig.raiseEventHandlerExceptions:
                        raise
                    else:
                        print(" *** error in doOnLDown **", file=sys.stderr)
                        traceback.print_exc()
                        print(" *** error in doOnLDown **", file=sys.stderr)
                    
        elif ev.LeftDClick():
            for f in self.doOnLDClick:
                try:
                    f(xEff_float,yEff_float, ev)
                except:
                    if PriConfig.raiseEventHandlerExceptions:
                        raise
                    else:
                            print(" *** error in doOnLDClick **", file=sys.stderr)
                            traceback.print_exc()
                            print(" *** error in doOnLDClick **", file=sys.stderr)
                    
            #print ":", x,y, "   ", x0,y0, s, "   ", xyEffInside, " : ", xEff, yEff
            
            #if xyEffInside:
            #    self.doDClick(xEff, yEff)
            #self.doOnLeftDClick(ev)

        #20080707-alwaysCall_DoOnMouse if xyEffInside:
        for f in self.doOnMouse:
            try:
                f(xEff_float, yEff_float, ev)
            except:
                if PriConfig.raiseEventHandlerExceptions:
                    raise
                else:
                    print(" *** error in doOnMouse **", file=sys.stderr)
                    traceback.print_exc()
                    print(" *** error in doOnMouse **", file=sys.stderr)
        ev.Skip() # other things like EVT_MOUSEWHEEL are lost




    def OnEraseBackground(self, ev):
        pass # do nothing to prevent flicker !!

    #20080707-unused def OnMove(self, event):
    #20080707-unused     self.doOnFrameChange()
    #20080707-unused     event.Skip()

    def OnSize(self, event):
        self.m_w, self.m_h = self.GetSize() #Tuple() # self.GetClientSizeTuple()
        if self.m_w <=0 or self.m_h <=0:
            #print "GLViewer.OnSize self.m_w <=0 or self.m_h <=0", self.m_w, self.m_h
            return
        self.m_doViewportChange = True

        '''#20080806
        #if hasattr(self, 'm_w'):
        try:
            ow,oh = self.m_w, self.m_h
            moveCenter=1
        except:
            moveCenter=0
            pass
        if moveCenter:
            dw,dh = self.m_w-ow, self.m_h-oh
            if dw != 0 or dh != 0:
                self.m_x0 += dw//2
                self.m_y0 += dh//2
                self.m_zoomChanged = 1
                self.Refresh(0)

        #FIXME print "viewer -> OnSize -> center"
        #  self.center()
        #20080707-unused self.doOnFrameChange()
        '''
        if self.keepCentered and self.m_x0 is not None:
            self.center()
        event.Skip()

    def OnWheel(self, evt):
        #delta = evt.GetWheelDelta()
        rot = evt.GetWheelRotation()      / 120. #HACK
        #linesPer = evt.GetLinesPerAction()
        #print "wheel:", delta, rot, linesPer
        if 1:#nz ==1:
            zoomSpeed = 1. # .25
            fac = self.m_wheelFactor ** (rot*zoomSpeed) # 1.189207115002721 # >>> 2 ** (1./4)
            self.m_scale *= fac
            #self.center()
            w2 = self.m_w/2
            h2 = self.m_h/2
            self.m_x0 = w2 - (w2-self.m_x0)*fac
            self.m_y0 = h2 - (h2-self.m_y0)*fac
            self.m_zoomChanged = True
            self.Refresh(0)
        #else:
        #    slider.SetValue()
        evt.Skip() #?

    #20080707 def doLDClick(self, x,y):
    #20080707     # print "doDLClick xy: --> %7.1f %7.1f" % (x,y)
    #20080707     pass
    #20080707 def doLDown(self, x,y):
    #20080707     # print "doLDown xy: --> %7.1f %7.1f" % (x,y)
    #20080707     pass

        
    def OnSaveClipboard(self, event=None):
        from . import usefulX as Y
        Y.vCopyToClipboard(self, clip=1)
        Y.shellMessage("### screenshot saved to clipboard'\n")

    def OnSaveScreenShort(self, event=None):
        """always flipY"""
        from Priithon.all import U, FN, Y
        fn = FN(1)#, verbose=0)
        if not fn:
            return

        flipY=1
        if flipY:
            U.saveImg(self.readGLviewport(copy=1)[:, ::-1], fn)
        else:
            U.saveImg(self.readGLviewport(copy=1), fn)
        
        Y.shellMessage("### screenshot saved to '%s'\n"%fn)

    def OnAssign(self, event=None):
        from . import usefulX as Y
        ss = "<2d section shown>"

        for i in range(len(Y.viewers)):
            try:
                v = Y.viewers[i]
                if v.viewer is self:
                    ss = "Y.vd(%d)[%s]"%(i, ','.join(map(str,v.zsec)))
                    break
            except:
                pass

        if hasattr(self, 'm_imgArr'):
            arr = self.m_imgArr
        elif hasattr(self, 'm_imgList'):
            arr = N.array([img[2] for img in self.m_imgList])
        Y.assignNdArrToVarname(arr, ss) #self.m_imgArr, ss)

    def OnSave(self, event=None):
        from Priithon.all import Mrc, U, Y
        fn = Y.FN(1)#, verbose=0)
        if not fn:
            return
        if fn[-4:] in [ ".mrc",  ".dat" ]:
            Mrc.save(self.m_imgArr, fn)
        elif fn[-5:] in [ ".fits" ]:
            U.saveFits(self.m_imgArr, fn)
        else:
            U.saveImg8(self.m_imgArr, fn)

        Y.shellMessage("### section saved to '%s'\n"%fn)

    def OnRotate(self, evt):
        from . import usefulX as Y
        Y.vRotate(self)
    def OnAspectRatio(self, evt):
        ds = "nx/ny"
        if self.m_originLeftBottom == 8:
            ds = "(2*nx+1)/ny"
        a = wx.GetTextFromUser('''\
set image aspect ratio (y/x factor for display)
  (any python-expression is OK)
     nx,ny = width,height
     a     = current aspect ratio                             
                               ''',
                               "set image aspect ratio",
                               ds)
        if a=='':
            return
        import __main__
        loc = { 'nx': float(self.pic_nx),
                'ny': float(self.pic_ny),
                'a' : self.m_aspectRatio,
                }
        try:
            y_over_x = float( eval(a,__main__.__dict__, loc) )
        except:
            raise # this was from the time before we had guiExceptions, I guess...
            #             import sys
            #             e = sys.exc_info()
            #             wx.MessageBox("Error when evaluating %s: %s - %s" %\
                #                           (a, str(e[0]), str(e[1]) ),
            #                           "syntax(?) error",
            #                           style=wx.ICON_ERROR)
        else:
            self.setAspectRatio(y_over_x)

    def OnMenu(self, event):
        id = event.GetId()
        
        #          if id == Menu_ZoomCenter:
        #              x = self.mousePos_remembered_x
        #              y = self.mousePos_remembered_y
        
        #              w2 = self.m_w/2
        #              h2 = self.m_h/2
        #              self.m_x0 += (w2-x)*self.m_scale
        #              self.m_y0 += (h2-y)*self.m_scale
        #              self.m_zoomChanged = True

        if id == Menu_Zoom2x:
            fac = 2.
            self.m_scale *= fac
            w2 = self.m_w/2.
            h2 = self.m_h/2.
            self.m_x0 = w2 - (w2-self.m_x0)*fac
            self.m_y0 = h2 - (h2-self.m_y0)*fac
            #self.center()#
            self.m_zoomChanged = True
        elif id == Menu_Zoom_5x:
            fac = .5
            self.m_scale *= fac
            w2 = self.m_w/2.
            h2 = self.m_h/2.
            self.m_x0 = w2 - (w2-self.m_x0)*fac
            self.m_y0 = h2 - (h2-self.m_y0)*fac
            #self.center()#
            self.m_zoomChanged = True

        self.Refresh(0)


           

    def readGLviewport(self, clip=False, flipY=True, copy=True):
        """returns array with r,g,b values from "what-you-see"
            shape(3, height, width)
            type=UInt8

            if clip: clip out the "green background"
            if copy == 0 returns non-contiguous array!!!

        """
        self.m_zoomChanged = True
        self.Refresh(0)
        
        self.SetCurrent(self.context)
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        
        get_cm = glGetInteger(GL_MAP_COLOR)
        get_rs = glGetDoublev(GL_RED_SCALE)
        get_gs = glGetDoublev(GL_GREEN_SCALE)
        get_bs = glGetDoublev(GL_BLUE_SCALE)
            
        get_rb = glGetDoublev(GL_RED_BIAS)
        get_gb = glGetDoublev(GL_GREEN_BIAS)
        get_bb = glGetDoublev(GL_BLUE_BIAS)

        glPixelTransferi(GL_MAP_COLOR, False)

        glPixelTransferf(GL_RED_SCALE,   1)
        glPixelTransferf(GL_GREEN_SCALE, 1)
        glPixelTransferf(GL_BLUE_SCALE,  1)
            
        glPixelTransferf(GL_RED_BIAS,   0)
        glPixelTransferf(GL_GREEN_BIAS, 0)
        glPixelTransferf(GL_BLUE_BIAS,  0)

        b=glReadPixels(0,0, self.m_w, self.m_h,
                       GL_RGB,GL_UNSIGNED_BYTE)
        
        bb=N.ndarray(buffer=b, shape=(self.m_h,self.m_w,3),
                   dtype=N.uint8) #, aligned=1)

        cc = N.transpose(bb, (2,0,1))

        if clip:
            x0,y0, s,a = int(self.m_x0), int(self.m_y0),self.m_scale,self.m_aspectRatio
            if hasattr(self, "m_imgArr"):
                ny,nx = self.m_imgArr.shape
            else:
                ny,nx = self.m_imgList[0][2].shape
            nx,ny = int(nx*s +.5), int(ny*s*a + .5)
            x1,y1 = x0+ nx, y0+ny

            x0 = N.clip(x0, 0, self.m_w)
            x1 = N.clip(x1, 0, self.m_w)
            y0 = N.clip(y0, 0, self.m_h)
            y1 = N.clip(y1, 0, self.m_h)
            nx,ny = x1-x0, y1-y0
            cc=cc[:,y0:y1,x0:x1]
        #else:
        #    y0,x0 = 0,0
        #    ny,nx = y1,x1 = self.m_h, self.m_w

        if flipY:
            cc = cc[:,::-1] # flip y
            
        if copy:
            cc = cc.copy()

        glPixelTransferi(GL_MAP_COLOR, get_cm)

        glPixelTransferf(GL_RED_SCALE,   get_rs)
        glPixelTransferf(GL_GREEN_SCALE, get_gs)
        glPixelTransferf(GL_BLUE_SCALE,  get_bs)
            
        glPixelTransferf(GL_RED_BIAS,   get_rb)
        glPixelTransferf(GL_GREEN_BIAS, get_gb)
        glPixelTransferf(GL_BLUE_BIAS,  get_bb)

        glPixelStorei(GL_PACK_ALIGNMENT, 4) # reset default
        return cc
