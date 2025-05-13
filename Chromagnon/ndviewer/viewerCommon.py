"""
provides the bitmap OpenGL panel for Priithon's ND 2d-section-viewer 

common base class for single-color and multi-color version
"""

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>, Lin Shao"
__license__ = "BSD license - see LICENSE file"

import six
import wx
from wx import glcanvas as wxgl
from OpenGL.GL import *

import numpy as N

bugXiGraphics = 0

Menu_Zoom2x      = wx.NewId()
Menu_ZoomCenter  = wx.NewId()
Menu_Zoom_5x     = wx.NewId()
Menu_ZoomReset   = wx.NewId()
Menu_ZoomOut     = wx.NewId()
Menu_ZoomIn      = wx.NewId()
#Menu_Color       = wx.NewId()
Menu_Reload       = wx.NewId()
#Menu_chgOrig     = wx.NewId()
Menu_Save = wx.NewId()
Menu_SaveScrShot = wx.NewId()
#Menu_SaveClipboard = wx.NewId()
#Menu_Assign = wx.NewId()
Menu_noGfx = wx.NewId()
Menu_aspectRatio = wx.NewId()
#Menu_rotate = wx.NewId()
#Menu_grid        = wx.NewId()    ## shortcut 'g' for toggling grid display
Menu_ColMap = [wx.NewId() for i in range(8)]


class GLViewerCommon(wxgl.GLCanvas):
    def __init__(self, parent, size=wx.DefaultSize, style=0, originLeftBottom=None):
        wxgl.GLCanvas.__init__(self, parent, -1, style=style, size=size)

        self.error = None
        self.doViewportChange = True
    
        self.x00 = 0 #-.5
        self.y00 = 0 #-.5
        self.x0=None # call center() in OnPaint -- self.x00
        self.y0=None # call center() in OnPaint -- self.y00
        self.scale=1.
        self.aspectRatio = 1.
        self.rot=0.
        self.zoomChanged = True # trigger a first placing of image
        self.sizeChanged = True
        self.keepCentered = True
        

        self.pixelGrid_state = 0 # 0-off, 1-everyPixel, 2- every 10 pixels

        self.GLinit   = False
        self.context = wxgl.GLContext(self) # 20141124 cocoa

        self.moreGlLists = []
        self.moreGlLists_enabled = []
        self.moreMaster_enabled = 1
        self.moreGlLists_dict = {} # map 'name' to list of idx in moreGlLists
        # a given idx can be part of multiple 'name' entries
        # a given name entry can contain a given idx only once
        self.moreGlLists_nameBlacklist = set()
        self.moreGlLists_NamedIdx = {} # map str to int or None -- this is helpful for reusing Idx for "changing" gllists
                                         # if name (type str) wasn't used before, it defaults to None (20080722)

        self.moreGlListReuseIdx=None

        self.wheelFactor = 2 ** (1/3.) #1.189207115002721 # >>> 2 ** (1./4)  # 2
        self.mouse_last_x, self.mouse_last_y = 0,0 # in case mouseIsDown happens without preceeding mouseDown

        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        parent.Bind(wx.EVT_MOVE, self.OnMove)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnWheel)
        #wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        #wx.EVT_MOVE(parent, self.OnMove)
        #wx.EVT_SIZE(self, self.OnSize) # CHECK # CHECK
        #wx.EVT_MOUSEWHEEL(self, self.OnWheel)


    def bindMenuEventsForShortcuts(self):
        self.Bind(wx.EVT_MENU, self.OnCenter, id=Menu_ZoomCenter)
        self.Bind(wx.EVT_MENU, self.OnZoomOut, id=Menu_ZoomOut)
        self.Bind(wx.EVT_MENU, self.OnZoomIn, id=Menu_ZoomIn)
        #wx.EVT_MENU(self, Menu_ZoomCenter, self.OnCenter)
        #wx.EVT_MENU(self, Menu_ZoomOut, self.OnZoomOut)
        #wx.EVT_MENU(self, Menu_ZoomIn, self.OnZoomIn)

        
        dontneed="""
        self.Bind(wx.EVT_MENU, self.On51, id=1051) # left key
        self.Bind(wx.EVT_MENU, self.On52, id=1052) # right key
        self.Bind(wx.EVT_MENU, self.On53, id=1053) # up key
        self.Bind(wx.EVT_MENU, self.On54, id=1054) # down key
        #wx.EVT_MENU(self, 1051, self.On51)  # left key
        #wx.EVT_MENU(self, 1052, self.On52)  # right key
        #wx.EVT_MENU(self, 1053, self.On53)  # up key
        #wx.EVT_MENU(self, 1054, self.On54)  # down key"""
        

        #wx.EVT_MENU(self, Menu_grid, self.setPixelGrid)  # for wxAcceleratorTable
        
    def initAccels(self):
        self.accelTableList = [

            (wx.ACCEL_NORMAL, ord('0'), Menu_ZoomReset),
            (wx.ACCEL_NORMAL, ord('9'), Menu_ZoomCenter),
            (wx.ACCEL_NORMAL, ord('d'), Menu_Zoom2x),
            (wx.ACCEL_NORMAL, ord('h'), Menu_Zoom_5x),
            #(wx.ACCEL_NORMAL, ord('c'), Menu_Color),
            (wx.ACCEL_NORMAL, ord('r'), Menu_Reload),
            #(wx.ACCEL_NORMAL, ord('o'), Menu_chgOrig),
            #(wx.ACCEL_NORMAL, ord('g'), Menu_grid),
            (wx.ACCEL_NORMAL, ord('b'), Menu_noGfx),

            #(wx.ACCEL_CTRL, ord('c'), Menu_SaveClipboard),

            (wx.ACCEL_NORMAL, wx.WXK_HOME, Menu_ZoomCenter),
            (wx.ACCEL_NORMAL, wx.WXK_PAGEDOWN, Menu_ZoomOut),
            (wx.ACCEL_NORMAL, wx.WXK_PAGEUP,Menu_ZoomIn),
            #(wx.ACCEL_NORMAL, wx.WXK_NEXT, Menu_ZoomOut),  
            #(wx.ACCEL_NORMAL, wx.WXK_PRIOR,Menu_ZoomIn),   

           # (wx.ACCEL_CTRL, wx.WXK_LEFT, 1051),
           # (wx.ACCEL_CTRL, wx.WXK_RIGHT,1052),
           # (wx.ACCEL_CTRL, wx.WXK_UP,   1053),
           # (wx.ACCEL_CTRL, wx.WXK_DOWN, 1054),

           # (wx.ACCEL_CTRL, wx.MOD_CMD | 'c', 1051),


            (wx.ACCEL_ALT, ord('0'), Menu_ZoomReset),
            (wx.ACCEL_ALT, ord('9'), Menu_ZoomCenter),
            (wx.ACCEL_ALT, ord('d'), Menu_Zoom2x),
            (wx.ACCEL_ALT, ord('h'), Menu_Zoom_5x),
            #(wx.ACCEL_ALT, ord('c'), Menu_Color),
            (wx.ACCEL_ALT, ord('r'), Menu_Reload),
            #(wx.ACCEL_ALT, ord('o'), Menu_chgOrig),
            #(wx.ACCEL_ALT, ord('g'), Menu_grid),
            (wx.ACCEL_ALT, ord('b'), Menu_noGfx),

            (wx.ACCEL_ALT, wx.WXK_HOME, Menu_ZoomCenter),
            (wx.ACCEL_ALT, wx.WXK_PAGEDOWN, Menu_ZoomOut),
            (wx.ACCEL_ALT, wx.WXK_PAGEUP, Menu_ZoomIn)
           # (wx.ACCEL_ALT, wx.WXK_NEXT, Menu_ZoomOut),
           # (wx.ACCEL_ALT, wx.WXK_PRIOR, Menu_ZoomIn)

            ]
        ## WXK_NEXT is page-down key
        ## WXK_PRIOR is  page-up key

        self.accelTableList_default = list(self.accelTableList) # backup for later resetting
        _at = wx.AcceleratorTable(self.accelTableList)
        self.SetAcceleratorTable(_at)
        
    ## may not need this
    def setAccels(self, appendList=[], reset=False):
        '''
        if reset: revert to original default accels
        '''
        if reset:
            self.accelTableList = list(self.accelTableList_default)
            
        self.accelTableList += appendList

        _at = wx.AcceleratorTable(self.accelTableList)
        self.SetAcceleratorTable(_at)


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
        self.moreGlListReuseIdx = idx
        self.SetCurrent(self.context)
        if isinstance(idx, six.string_types):
            idx = self.moreGlLists_NamedIdx.get(idx) # Never raises an exception if k is not in the map, instead it returns x. x is optional; when x is not provided and k is not in the map, None is returned. 
            if idx is None:
                self.curGLLIST = glGenLists( 1 )
            else:
                try:
                    self.curGLLIST = self.moreGlLists[idx]
                except IndexError: ## vgRemoveAll might have been called
                    self.curGLLIST = glGenLists( 1 )
                    del self.moreGlLists_NamedIdx[self.moreGlListReuseIdx] # will get reset in newGLListDone()
                else:
                    if self.curGLLIST is None:   # glList was deleted Y.vgRemove
                        self.curGLLIST = glGenLists( 1 )

        elif idx is None or self.moreGlLists[idx] is None:
            self.curGLLIST = glGenLists( 1 )
        else:
            self.curGLLIST = self.moreGlLists[idx]

        self.curGLLISTname  = name
        glNewList( self.curGLLIST, GL_COMPILE )
        
    def newGLListAbort(self):
        glEndList()
        glDeleteLists(self.curGLLIST, 1)
        if isinstance(self.moreGlListReuseIdx, six.string_types):
            try:
                del self.moreGlLists_NamedIdx[self.moreGlListReuseIdx] # CHECK
            except KeyError:
                pass # was not in dict yet
        self.moreGlListReuseIdx = None
        
    def newGLListDone(self, enable=True, refreshNow=True):
        glEndList()
        if isinstance(self.moreGlListReuseIdx, six.string_types):
            idx = self.moreGlLists_NamedIdx.get(self.moreGlListReuseIdx)
        else:
            idx = self.moreGlListReuseIdx

        if idx is not None:
            self.moreGlLists[idx] = self.curGLLIST # left side might have been None
            self.moreGlLists_enabled[idx] = enable
        else:
            idx = len(self.moreGlLists)
            self.moreGlLists.append( self.curGLLIST )
            self.moreGlLists_enabled.append( enable )
        
        self.newGLListNameAdd(idx, self.curGLLISTname)

        # remember named idx for future re-use
        if isinstance(self.moreGlListReuseIdx, six.string_types):
            self.moreGlLists_NamedIdx[self.moreGlListReuseIdx] = idx
        self.moreGlListReuseIdx = None

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
                    l = self.moreGlLists_dict[aName]
                    try:
                        l.index(idx)  # don't do anything if aName is already in
                    except ValueError:
                        l.append(idx)
                except KeyError:
                    self.moreGlLists_dict[aName] = [idx]


    def newGLListRemove(self, idx, refreshNow=True):
        """
        instead of 'del' just set entry to None
        this is to prevent, shifting of all higher idx
        20090107: but do 'del' for last entry - no trailing Nones

        self.moreGlLists_dict is cleaned properly
        """
        #20070712 changed! not 'del' - instead set entry to None
        #20070712    ---- because decreasing all idx2 for idx2>idx is complex !!!
        #untrue note;  --- old:
        #untrue note; be careful: this WOULD change all indices (idx) of GLLists
        #untrue note; following idx
        #untrue note!!: if you can not accept that: you should call
        #untrue note!!:   newGLListEnable(idx, on=0)

#       if self.moreGlLists_texture[idx] is not None:
#           glDeleteTextures( self.moreGlLists_texture[idx] )
#           del self.moreGlLists_img[idx]

        if isinstance(idx, six.string_types):
            idx=self.moreGlLists_NamedIdx[idx]
        elif idx<0:
            idx += len(self.moreGlLists)

        if self.moreGlLists[idx]: # could be None - # Note: Zero is not a valid display-list index.
            glDeleteLists(self.moreGlLists[idx], 1)
        #20070712 del self.moreGlLists[idx]
        #20070712 del self.moreGlLists_enabled[idx]
        if idx == len(self.moreGlLists)-1: # 20090107
            del self.moreGlLists[idx]
            del self.moreGlLists_enabled[idx]
        else:
            self.moreGlLists[idx] = None
            self.moreGlLists_enabled[idx] = None
        self.moreGlLists_nameBlacklist.discard(idx)

        #remove idx from 'name' dict entry
        #   remove respective dict-name if it gets empty
        _postposeDelList = [] # to prevent this error:dictionary changed size during iteration
        for name,idxList in self.moreGlLists_dict.items():
            try:
                idxList.remove(idx)
                if not len(idxList):
                    _postposeDelList.append(name)
            except ValueError:
                pass
        for name in _postposeDelList:
            del self.moreGlLists_dict[name]

        if refreshNow:
            self.Refresh(0)

    def newGLListEnable(self, idx, on=True, refreshNow=True):
        """
        ignore moreGlList items that are None !
        """
        if isinstance(idx, six.string_types):
            idx=self.moreGlLists_NamedIdx[idx]
        if self.moreGlLists_enabled[idx] is not None:
            self.moreGlLists_enabled[idx] = on
        if refreshNow:
            self.Refresh(0)
            
    ## may not need
    def newGLListEnableByName(self, name, on=True, skipBlacklisted=False, refreshNow=True):
        '''
        ignore moreGlList items that are None !
        '''
        for idx in self.moreGlLists_dict[name]:
            if self.moreGlLists_enabled[idx] is not None and\
                    (not skipBlacklisted or idx not in self.moreGlLists_nameBlacklist):
                self.moreGlLists_enabled[idx] = on
        if refreshNow:
            self.Refresh(0)

    ## may not need
    def newGLListRemoveByName(self, name, refreshNow=True):
        for idx in self.moreGlLists_dict[name]:
            if self.moreGlLists[idx]:
                glDeleteLists(self.moreGlLists[idx], 1)
            # refer to comment in newGLListRemove() !!!
            self.moreGlLists[idx]  = None
            self.moreGlLists_enabled[idx]  = None
        del self.moreGlLists_dict[name]

        # clean up other name entries in dict
        for name,idxList in list(self.moreGlLists_dict.items()):
            for i in range(len(idxList)-1,-1,-1):
                if self.moreGlLists[idxList[i]] is None:
                    del idxList[i]
            if not len(idxList):
                del self.moreGlLists_dict[name]

        #20090505: remove trailing None's
        for idx in range(len(self.m_moreGlLists)-1, -1, -1):
            if self.moreGlLists[idx] is None:
                del self.moreGlLists[idx]
                del self.moreGlLists_enabled[idx]
            else:
                break

        if refreshNow:
            self.Refresh(0)

    ## may not need
#     def newGLListRemoveAll(self, refreshNow=True):
#         '''
#         this really removes all GLList stuff
#         idx values will restart at 0
#         here nothing gets "only" set to None
#         '''
#         for li in self.moreGlLists:
#             if li:  # Note: Zero is not a valid display-list index.
#                 glDeleteLists(li, 1)
#         self.moreGlLists = []
#         self.moreGlLists_enabled = []
#         #self.moreMaster_enabled = 1
#         self.moreGlLists_dict = {}

#         if refreshNow:
#             self.Refresh(0)
        
    def newGLListRemoveAll(self, refreshNow=True):
        """
        this really removes all GLList stuff
        idx values will restart at 0
        here nothing gets "only" set to None
        """
        for li in self.moreGlLists:
            if li:  # Note: Zero is not a valid display-list index.
                glDeleteLists(li, 1)
        self.moreGlLists = []
        self.moreGlLists_enabled = []
        #self.moreMaster_enabled = 1
        self.moreGlLists_dict.clear()
        self.moreGlLists_nameBlacklist.clear()
        self.moreGlLists_NamedIdx.clear()

        if refreshNow:
            self.Refresh(0)

    def OnNoGfx(self, evt):
        #fails on windows:
        if wx.Platform == '__WXMSW__': ### HACK check LINUX GTK WIN MSW
            menuid  = self.menu.FindItem("hide all gfx")
            self.menu.FindItemById(menuid).Check( not evt.IsChecked() )
            self.moreMaster_enabled ^= 1
        else:
            self.moreMaster_enabled = not evt.IsChecked()

        self.Refresh(0)


    ## may not need
#     def OnChgNoGfx(self):
#         self.moreMaster_enabled ^= 1
#         menuid  = self.menu.FindItem("hide all gfx")
#         self.menu.FindItemById(menuid).Check(self.moreMaster_enabled)
#         self.Refresh(0)

    def setAspectRatio(self, y_over_x, refreshNow=1):
        '''
        strech images in y direction
        use negative value to mirror
        '''
        
        self.aspectRatio=y_over_x
        
        self.zoomChanged=True
        if refreshNow:
            self.Refresh()

    ## may not need
#     def setRotation(self, angle=90, refreshNow=1):
#         '''rotate everything by angle in degrees
#         '''
        
#         self.rot = angle
        
#         self.zoomChanged=1
#         if refreshNow:
#             self.Refresh()

    def center(self, refreshNow=True):
        self.keepCentered = True

        ws = N.array([self.w, self.h])
        nx = self.pic_nx
        if self.originLeftBottom == 8:
            nx = (self.pic_nx-1) * 2
        ps = N.array([nx, self.pic_ny])
        s  = (self.scale, self.scale*self.aspectRatio)
        self.x0, self.y0 = (ws-ps*s) // 2

        self.zoomChanged = True
        if refreshNow:
            self.Refresh(0)
        
    def zoom(self, zoomfactor, absolute=True, refreshNow=True):
        '''set new zoom factor to zoomfactor
        if absolute is False
           adjust current zoom factor to
              "current"*zoomfactor
        image center stays center 
        '''
        if absolute:
            fac = zoomfactor / self.scale
        else:
            fac = zoomfactor
        self.scale *= fac
        #self.center()
        w2 = self.w/2
        h2 = self.h/2
        self.x0 = w2 - (w2-self.x0)*fac
        self.y0 = h2 - (h2-self.y0)*fac
        self.zoomChanged = True
        if refreshNow:
            self.Refresh(0)

    def doReset(self, ev=None, refreshNow=True):
        self.keepCentered = False

        #self.x0=self.x00
        #self.y0=self.y00
        #self.center(False)
        self.scale=1.
        self.rot=0.
        #self.aspectRatio = 1.
        self.zoomChanged = True
        if refreshNow:
            self.Refresh(0)


    def OnCenter(self, event):
        self.center()
    def OnZoomOut(self, event):
        fac = 1./1.189207115002721
        self.zoom(fac, absolute=False)        
    def OnZoomIn(self, event):
        fac = 1.189207115002721
        self.zoom(fac, absolute=False)

    dontneed="""
    def On51(self, event):
        n= self.pic_nx / 4
        if self.originLeftBottom == 8:
            n= (n-1) * 2
        self.doShift(- self.scale*n , 0)
    def On52(self, event):
        n= self.pic_nx / 4
        if self.originLeftBottom == 8:
            n= (n-1) * 2
        self.doShift(+ self.scale*n , 0)
    def On53(self, event):
        n= self.pic_ny / 4
        self.doShift(0,  + self.scale*n)
    def On54(self, event):
        n= self.pic_ny / 4
        self.doShift(0,  - self.scale*n)

    def doShift(self, dx,dy):
        self.keepCentered = False

        self.x0 += dx
        self.y0 += dy
        
        self.zoomChanged = True
        self.Refresh(0)"""




    def OnEraseBackground(self, ev):
        pass # do nothing to prevent flicker !!

    def OnMove(self, event):
        self.doOnFrameChange()
        event.Skip()

    def OnSize(self, event):

        self.w, self.h = self.GetClientSize() #Tuple()
        if self.w <=0 or self.h <=0:
            # no raise here?
            #print "GLViewer.OnSize self.w <=0 or self.h <=0", self.w, self.h
            return
        self.doViewportChange = True

        if self.keepCentered and self.x0 is not None:
            self.center()
        event.Skip()

    def OnWheel(self, evt):
        rot = evt.GetWheelRotation() / evt.GetWheelDelta()  ### 120.

        zoomSpeed = .25
        fac = self.wheelFactor ** (rot*zoomSpeed) # 1.189207115002721 # >>> 2 ** (1./4)
        self.scale *= fac
        w2 = self.w/2
        h2 = self.h/2
        self.x0 = w2 - (w2-self.x0)*fac
        self.y0 = h2 - (h2-self.y0)*fac
        #print self.x0, self.y0
        self.zoomChanged = True
        self.Refresh(0)
        evt.Skip() #?

    def doLDClick(self, x,y):
        pass


    ## don't need
    def OnSaveClipboard(self, event=None):
         import usefulX2 as Y
         Y.vCopyToClipboard(self, clip=1)
         Y.shellMessage("### screenshot saved to clipboard'\n")

    ## don't need
    def OnSaveScreenShort(self, event=None):
        '''always flipY'''
        try:
            from ..Priithon.all import U, FN
        except (ValueError, ImportError):
            from Priithon.all import U, FN
        fn = FN(1)#, verbose=0)
        if not fn:
            return

        flipY=1
        if flipY:
            U.saveImg(self.readGLviewport(copy=1)[:, ::-1], fn)
        else:
            U.saveImg(self.readGLviewport(copy=1), fn)
        
#        from usefulX2 import shellMessage
#         shellMessage("### screenshot saved to '%s'\n"%fn)

    ## don't need
#     def OnAssign(self, event=None):
#         import usefulX2 as Y
#         ss = "<2d section shown>"

#         for i in range(len(Y.viewers)):
#             try:
#                 v = Y.viewers[i]
#                 if v.viewer is self:
#                     ss = "Y.vd(%d)[%s]"%(i, ','.join(map(str,v.zsec)))
#                     break
#             except:
#                 pass

#         Y.assignNdArrToVarname(self.imgArr, ss)

    ## don't need
#     def OnSave(self, event=None):
#         from Priithon.all import Mrc, U, FN
#         fn = FN(1, verbose=0)
#         if not fn:
#             return
#         if fn[-4:] in [ ".mrc",  ".dat" ]:
#             Mrc.save(self.imgArr, fn)
#         elif fn[-5:] in [ ".fits" ]:
#             U.saveFits(self.imgArr, fn)
#         else:
#             U.saveImg8(self.imgArr, fn)

#         from usefulX2 import shellMessage
#         shellMessage("### section saved to '%s'\n"%fn)

    def OnRotate(self, evt):
        import usefulX2 as Y
        Y.vRotate(self)
    def OnAspectRatio(self, evt):
        ds = "nx/ny"
        if self.originLeftBottom == 8:
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
                'a' : self.aspectRatio,
                }
        try:
            y_over_x = float( eval(a,__main__.__dict__, loc) )
        except:
            import sys
            e = sys.exc_info()
            wx.MessageBox("Error when evaluating %s: %s - %s" %\
                          (a, str(e[0]), str(e[1]) ),
                          "syntax(?) error",
                          style=wx.ICON_ERROR)
        else:
            self.setAspectRatio(y_over_x)

    ## handle 'zoom 2x' and 'zoom 0.5x' menu items
    def OnMenu(self, event):
        id = event.GetId()
        
        if id == Menu_Zoom2x:
            fac = 2.
            self.scale *= fac
            w2 = self.w/2
            h2 = self.h/2
            self.x0 = w2 - (w2-self.x0)*fac
            self.y0 = h2 - (h2-self.y0)*fac
            #self.center()#
            self.zoomChanged = True
        elif id == Menu_Zoom_5x:
            fac = .5
            self.scale *= fac
            w2 = self.w/2
            h2 = self.h/2
            self.x0 = w2 - (w2-self.x0)*fac
            self.y0 = h2 - (h2-self.y0)*fac
            #self.center()#
            self.zoomChanged = True

        self.Refresh(0)



    ## don't need
    def readGLviewport(self, clip=False, flipY=True, copy=True):
        '''returns array with r,g,b values from "what-you-see"
            shape(3, height, width)
            type=UInt8

            if clip: clip out the "green background"
            if copy == 0 returns non-contiguous array!!!

        '''
        import sys, platform
        
        self.zoomChanged = True
        self.Refresh(0)
        wx.YieldIfNeeded()
        
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

        ver = wx.version()
        major, minor = ver.split('.')[:2]
        if int(major) >= 4 and int(minor) >= 1:
            cs = self.GetContentScaleFactor()
        else:
            cs = 1

        size = self.GetClientSize()
        width = int(size.width * cs + .5)
        height = int(size.height * cs + .5)

        b = glReadPixels(0, 0, width, height, 
                       GL_RGB,GL_UNSIGNED_BYTE)

        bb=N.ndarray(buffer=b, shape=(height,width,3),
                   dtype=N.uint8)

        cc = N.transpose(bb, (2,0,1))

        if clip:
            x0,y0, s,a = int(self.x0*cs+.5), int(self.y0*cs+.5),self.scale,self.aspectRatio
            if hasattr(self, "imgArr"):
                ny,nx = self.imgArr.shape
            else:
                ny,nx = self.imgList[0][2].shape
            nx,ny = int(nx*cs*s +.5), int(ny*cs*s*a + .5)
            x1,y1 = x0+ nx, y0+ny

            x0 = N.clip(x0, 0, int(self.w*cs+.5))
            x1 = N.clip(x1, 0, int(self.w*cs+.5))
            y0 = N.clip(y0, 0, int(self.h*cs+.5))
            y1 = N.clip(y1, 0, int(self.h*cs+.5))
            nx,ny = x1-x0, y1-y0
            cc=cc[:,y0:y1,x0:x1]
        #else:
        #    y0,x0 = 0,0
        #    ny,nx = y1,x1 = self.h, self.w

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

