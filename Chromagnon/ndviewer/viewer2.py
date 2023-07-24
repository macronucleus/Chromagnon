"""provides the bitmap OpenGL panel for Priithon's ND 2d-section-viewer (multi-color version)"""
import weakref, sys
from .viewerCommon import *
try:
    from ..PriCommon import imgGeo #PriCommon import imgGeo
except (ValueError, ImportError): # interactive mode
    from PriCommon import imgGeo
    

dataTypeMaxValue_table = {
    N.uint16: (1<<16) -1,
    N.int16:  (1<<15) -1,
    N.uint8:  (1<<8) -1, 
    N.bool_:  (1<<8) -1,
    N.float32: 1
    }
BACKGROUND=(0.2,0.2,0.2,0) # color
CROPBOX = False


class GLViewer(GLViewerCommon):
    def __init__(self, parent, dims=(1,2), size=wx.DefaultSize, style=0, originLeftBottom=None, useCropbox=CROPBOX):
        '''
        dims tells which 2 of the three dimensions this viewer is showing; 0--z, 1--y, 2--x
        '''
        GLViewerCommon.__init__(self, parent, size, style, originLeftBottom)
        self.imgsGlListChanged = False
        self.originLeftBottom = 1
        self.gllist = None

        self.vclose = False
        self.hclose = False
        self.myViewManager = weakref.proxy(parent.parent)
        
        self.imgList = [] # each elem.:
        # 0       1        2       3            4     5   6 7 8   9, 10,11, 12,13,14
        #[gllist, enabled, imgArr, textureID, smin, smax, r,g,b,  tx,ty,rot,magX,magY,magZ]

        self.pic_nys, self.pic_nxs = [], []
        self.loadImgsToGfxCard = []
        self.gllist_Changed = False # call defGlList() from OnPaint

        if not wx.Platform == '__WXMSW__': #20070525-black_on_black on Windows
            self.SetCursor(wx.CROSS_CURSOR)
        self.defaultCursor = self.GetCursor()

        self.dims = dims

        self.cropboxDragging = False
        self.dragSide = 0
        self.useHair = True
        self.useCropbox = useCropbox #CROPBOX
        self.viewGpx = [] # an container for cropbox drawing

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse)
        #wx.EVT_PAINT(self, self.OnPaint)
        #wx.EVT_MOUSE_EVENTS(self, self.OnMouse)

        self.MakePopupMenu()
        self.bindMenuEventsForShortcuts()   ## viewerCommon.py
        self.initAccels()
    
        _at = [
            (wx.ACCEL_NORMAL, wx.WXK_LEFT, 2051),
            (wx.ACCEL_NORMAL, wx.WXK_RIGHT,2052),
            (wx.ACCEL_NORMAL, wx.WXK_UP,   2053),
            (wx.ACCEL_NORMAL, wx.WXK_DOWN, 2054),
            ]
        self.setAccels(_at)  ## append _at to existing accelerator table
        ## and associate these keys with handlers
        self.Bind(wx.EVT_MENU, self.OnArrowKeys, id=2051)
        self.Bind(wx.EVT_MENU, self.OnArrowKeys, id=2052)
        self.Bind(wx.EVT_MENU, self.OnArrowKeys, id=2053)
        self.Bind(wx.EVT_MENU, self.OnArrowKeys, id=2054)

        #wx.EVT_MENU(self, 2051, self.OnArrowKeys)
        #wx.EVT_MENU(self, 2052, self.OnArrowKeys)
        #wx.EVT_MENU(self, 2053, self.OnArrowKeys)
        #wx.EVT_MENU(self, 2054, self.OnArrowKeys)

    def setMyDoc(self, doc, parent):
        self.mydoc = weakref.proxy(doc)
        #self.myViewManager = weakref.proxy(parent)
        #self.setLeftDown()

    def setLeftDown(self, ld=None):
        """
        ld: None uses self.mydoc info, otherwise supply [z,y,x]
        """
        if ld is None:
            leftDown = N.zeros((3,), int)
            debug="""
            if hasattr(self, 'pic_ny'):
                if self.dims in  ((1,2), (1,0)): # XY, ZY
                    leftDown[1] = self.pic_ny
                elif self.dims == (0,2): # XZ
                    leftDown[0] = self.pic_ny"""
            #leftDown[-2:] = self.mydoc._offset.min(0)
            self.ld = leftDown[list(self.dims)]
        else:
            self.ld = ld

    def MakePopupMenu(self):
        """Make a menu that can be popped up later"""
        self.menu = wx.Menu()

        ## self.menu_save = wx.Menu()
        ## self.menu_save.Append(Menu_Save,    "save 2d sec into file")
        ## self.menu_save.Append(Menu_SaveScrShot, "save 2d screen shot 'as seen'")
        ##self.menu_save.Append(Menu_SaveClipboard, "save 2d screen shot 'as seen' into clipboard")
        ## self.menu_save.Append(Menu_Assign,  "assign 2d sec to a var name")

        # m_pMenuPopup->Append(Menu_Color, "&Change color")
        self.menu.Append(Menu_Zoom2x,    "&zoom 2x")
        self.menu.Append(Menu_Zoom_5x,   "z&oom .5x")
        self.menu.Append(Menu_ZoomReset, "zoom &reset")
        self.menu.Append(Menu_ZoomCenter,"zoom &center")
        #self.menu.Append(Menu_chgOrig, "c&hange Origin")
        self.menu.Append(Menu_Reload, "reload") # 
        self.menu.Append(Menu_SaveScrShot, 'save')#, self.menu_save) #wx.NewId(), "save", self.menu_save)
        self.menu.Append(Menu_aspectRatio, "change aspect ratio")
        self.menu.Append(Menu_noGfx, "hide all gfx\tb", '',wx.ITEM_CHECK)

        self.Bind(wx.EVT_MENU, self.OnMenu, id=Menu_Zoom2x)
        self.Bind(wx.EVT_MENU, self.OnMenu, id=Menu_Zoom_5x)
        self.Bind(wx.EVT_MENU, self.doReset, id=Menu_ZoomReset)
        self.Bind(wx.EVT_MENU, self.OnReload, id=Menu_Reload)
        self.Bind(wx.EVT_MENU, self.OnSaveScreenShort, id=Menu_SaveScrShot)
        self.Bind(wx.EVT_MENU, self.OnAspectRatio, id=Menu_aspectRatio)
        self.Bind(wx.EVT_MENU, self.OnNoGfx, id=Menu_noGfx)
                                                                
        #wx.EVT_MENU(self, Menu_Zoom2x,     self.OnMenu)
        #wx.EVT_MENU(self, Menu_Zoom_5x,    self.OnMenu)
        #wx.EVT_MENU(self, Menu_ZoomReset,  self.doReset)
        #wx.EVT_MENU(self, Menu_Reload,      self.OnReload)
        #wx.EVT_MENU(self, Menu_chgOrig,      self.OnChgOrig)
        ## wx.EVT_MENU(self, Menu_Save,      self.OnSave)
        #wx.EVT_MENU(self, Menu_SaveScrShot,      self.OnSaveScreenShort)
        ##wx.EVT_MENU(self, Menu_SaveClipboard,    self.OnSaveClipboard)
        ## wx.EVT_MENU(self, Menu_Assign,      self.OnAssign)
        #wx.EVT_MENU(self, Menu_aspectRatio,      self.OnAspectRatio)
        #wx.EVT_MENU(self, Menu_noGfx,      self.OnNoGfx)

    def InitGL(self):
        glClearColor(*BACKGROUND)#0.1, 0.1, 0.1, 0.0)   ## background color

        self.GLinit = True

    def addImgL(self, imgL, smin=0, smax=0, alpha=1., interp=0, refreshNow=1):
        '''
        append images from a list of them
        '''
        for img in imgL:
            self.addImg(img, smin, smax, alpha, interp, refreshNow=0)
        if refreshNow:
            self.Refresh(0)

    def addImg(self, img, smin=0, smax=10000, alpha=1., interp=0, imgidx=None, alignParm=None, refreshNow=1):
        '''
        append new image. Following lists get somthing appended:
        self.imgList
        self.loadImgsToGfxCard

        if imgidx is not None use 'insert(imgidx,...)' with self.imgList instead of append
        
        a new GL-texture is generated and an empty(!) texture with proper dtype is created.
        a new GL-Display-lists  is generated and compiled according to self.originLeftBottom
        '''
        pic_ny, pic_nx = img.shape

        # different shapes in multi wave images
        #self.pic_nys.append(pic_ny)
        #self.pic_nxs.append(pic_nx)
        if self.dims == (1,2): # XY
            self.pic_nys = [self.mydoc.ny]*self.mydoc.nw
            self.pic_nxs = [self.mydoc.nx]*self.mydoc.nw
        elif self.dims == (0,2): # XZ
            self.pic_nys = [self.mydoc.nz]*self.mydoc.nw
            self.pic_nxs = [self.mydoc.nx]*self.mydoc.nw
        elif self.dims == (1,0): # ZY
            self.pic_nys = [self.mydoc.ny]*self.mydoc.nw
            self.pic_nxs = [self.mydoc.nz]*self.mydoc.nw

        self.pic_ny, self.pic_nx = max(self.pic_nys), max(self.pic_nxs)

        if smin == smax == 0:
            try:
                from ..Priithon.all import U
            except (ValueError, ImportError):
                from Priithon.all import U
            smin, smax = U.mm(img)

        tex_nx = 2
        while tex_nx<pic_nx:
            tex_nx*=2 # // texture must be of size 2^n
        tex_ny = 2
        while tex_ny<pic_ny:
            tex_ny*=2

        self.picTexRatio_x = float(pic_nx) / tex_nx
        self.picTexRatio_y = float(pic_ny) / tex_ny

        if sys.platform.startswith('linux'):# and wx.version().startswith('3'): # wxversion removed 20210107
            wx.Yield() # added 20180312
        self.SetCurrent(self.context) ## makes the implicit rendering context of this canvas current with this canvas
        textureID = glGenTextures(1)  ## create one name for a texture object
        glBindTexture(GL_TEXTURE_2D, textureID)

        ## Define this new texture object based on img's geometry
        if interp:
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        else:
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST)

        if img.dtype.type in (N.uint8, N.bool_):
            glTexImage2D(GL_TEXTURE_2D,0,  GL_RGB, tex_nx,tex_ny, 0, 
                         GL_LUMINANCE,GL_UNSIGNED_BYTE, None)
        elif img.dtype.type == N.int16:
            glTexImage2D(GL_TEXTURE_2D,0,  GL_RGB, tex_nx,tex_ny, 0, 
                         GL_LUMINANCE,GL_SHORT, None)
        elif img.dtype.type == N.float32:
            glTexImage2D(GL_TEXTURE_2D,0,  GL_RGB, tex_nx,tex_ny, 0, 
                         GL_LUMINANCE,GL_FLOAT, None)
        elif img.dtype.type == N.uint16:
            glTexImage2D(GL_TEXTURE_2D,0,  GL_RGB, tex_nx,tex_ny, 0, 
                         GL_LUMINANCE,GL_UNSIGNED_SHORT, None)
        elif img.dtype.type in (N.float64,
                                N.int32, N.uint32, N.int64, N.uint64,):
                                #N.complex64, N.complex128):
            glTexImage2D(GL_TEXTURE_2D,0,  GL_RGB, tex_nx,tex_ny, 0, 
                         GL_LUMINANCE,GL_FLOAT, None)
        else:
            self.error = "unsupported data mode"
            raise ValueError(self.error)

        curGLLIST = glGenLists( 1 )  ## request one display-list index

        # 0       1        2       3            4     5   6 7 8  9   10  11   12   13  14
        #[gllist, enabled, imgArr, textureID, smin, smax, r,g,b, tx, ty, rot, magX, magY, magZ]
        r,g,b=1,1,1  ## default grey (if no self.setColor() is called)
        imgListItem = [curGLLIST, 1, img, textureID, smin,smax, r,g,b,  0,0,0,1,1,1]

        glNewList(curGLLIST, GL_COMPILE) # Display list is created; Commands are merely compiled

        # Newsgroups: comp.graphics.api.opengl   Date: 1998/05/05
        # By the way, you don't have to explicitly delete a display list to reuse 
        # its name.  Simply call glNewList() again with the existing list name -- 
        # this will implicitly delete the old contents and replace them with the 
        # new ones; this will happen at glEndList() time. 


        glBindTexture(GL_TEXTURE_2D, textureID)   # CHECK: Is this redundant?
        glEnable(GL_TEXTURE_2D)

        glEnable(GL_BLEND)   ## enable blending of colors (Chapter 6 of the Red Book)
        glBlendFunc(GL_ONE, GL_ONE)

        glBegin(GL_QUADS)

        ### draw black background under the image
        ###//(0,0) at left bottom
        glTexCoord2f( 0, 0)
        glVertex2i  ( 0, 0)
            
        glTexCoord2f( self.picTexRatio_x, 0)
        glVertex2i  ( pic_nx, 0)
            
        glTexCoord2f( self.picTexRatio_x, self.picTexRatio_y)
        glVertex2i  ( pic_nx, pic_ny)
            
        glTexCoord2f( 0, self.picTexRatio_y)
        glVertex2i  ( 0, pic_ny)

        glEnd()
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)

        glEndList()   ## display list stops here

        if imgidx is None:
            imgidx = len(self.imgList)

        self.imgList.insert(imgidx, imgListItem)
        ## imgListItem contains the newly created display list, indexed by imgidx

        self.loadImgsToGfxCard.append( imgidx )
        self.imgsGlListChanged = True

        self.setLeftDown()
        
        if refreshNow:
            self.Refresh(0)

    def updateAlignParm(self, imgidx=-1, alignParm=None):
        if alignParm is not None:
            if self.dims == (1,2):
                self.imgList[imgidx][1] = 1
                self.imgList[imgidx][10] = alignParm[self.dims[0]] # y
                self.imgList[imgidx][9] = alignParm[self.dims[1]] # x
                self.imgList[imgidx][11] = alignParm[3] # r
                self.imgList[imgidx][12:] = alignParm[4:][::-1] # mx,my,mz
            elif self.dims == (0,2): # XZ
                self.imgList[imgidx][10] = alignParm[self.dims[0]] # z
                self.imgList[imgidx][12:] = alignParm[4:][::-1] # mx,my,mz
                
            elif self.dims == (1,0): # ZY
                self.imgList[imgidx][9] = alignParm[self.dims[1]] # z
                self.imgList[imgidx][12:] = alignParm[4:][::-1] # mx,my,mz

            self.imgsGlListChanged = True

    ## Bind a textureID to a 2D texture
    def _loadImgIntoGfx(self, imgidx):
        img       = self.imgList[imgidx][2]
        textureID = self.imgList[imgidx][3]

        glBindTexture(GL_TEXTURE_2D, textureID)

        glPixelStorei(GL_UNPACK_ALIGNMENT, img.itemsize)
        glPixelStorei(GL_UNPACK_SWAP_BYTES, not img.dtype.isnative)

        imgString = img.tostring()
      
        pic_ny,pic_nx = img.shape

        if img.dtype.type in (N.uint8,N.bool_):
            glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny,
                            GL_LUMINANCE,GL_UNSIGNED_BYTE, imgString)
        elif img.dtype.type == N.int16:
            glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny,
                            GL_LUMINANCE,GL_SHORT,         imgString)
        elif img.dtype.type == N.float32:
            try:
                glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny,
                                GL_LUMINANCE,GL_FLOAT,         imgString)
            except GLerror as e:
                print(textureID, self.dims, img.shape)
                print(e)
                
        elif img.dtype.type == N.uint16:
            glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny,
                            GL_LUMINANCE,GL_UNSIGNED_SHORT, imgString)
        else:
            self.error = "unsupported data mode"
            raise ValueError(self.error)
        
    def _setHistScale(self, smin, smax, dataTypeMaxValue):

        srange = float(smax - smin)
        #  # const double maxUShort = double((unsigned short)-1)
        if srange == 0:
            fBias = 0
            f = 1
        else:
            fBias =  -smin / srange
            f     = dataTypeMaxValue / srange

        glPixelTransferf(GL_RED_SCALE,   f)
        glPixelTransferf(GL_GREEN_SCALE, f)
        glPixelTransferf(GL_BLUE_SCALE,  f)
        
        glPixelTransferf(GL_RED_BIAS,   fBias)
        glPixelTransferf(GL_GREEN_BIAS, fBias)
        glPixelTransferf(GL_BLUE_BIAS,  fBias)

        glPixelTransferf(GL_MAP_COLOR, False)


    ## these 3 calls are for graphic objects, like lines, circles, crosses, etc.
    def defGlList(self):
        pass
    def updateGlList(self, glCallsFunctions, refreshNow=True):
        if glCallsFunctions is None:
            def x():
                pass
            self.defGlList = x
        else:
            self.defGlList = glCallsFunctions
        self.gllist_Changed = True
        if refreshNow:
            self.Refresh(False)

    def addGlList(self, glCallsFunctions):
        if glCallsFunctions is None:
            def x():
                pass
            glCallsFunctions = x
        try:
            self.defGlList.append( glCallsFunctions )
        except:
            self.defGlList = [ self.defGlList, glCallsFunctions ]

        self.gllist_Changed = True
        self.Refresh(False)

    


    def changeHistogramScaling(self):
        self.loadImgsToGfxCard += list(range(len(self.imgList)))
        self.Refresh(False)

    def changeHistScale(self, imgidx, smin,smax, RefreshNow=1):
        if imgidx == -1:
            for imgListItem in self.imgList:
                imgListItem[4:6] = [smin,smax]
            self.loadImgsToGfxCard += list(range(len(self.imgList)))
        else:
            self.imgList[imgidx][4:6] = [smin,smax]
            self.loadImgsToGfxCard += [imgidx]

        if RefreshNow:
            self.Refresh(False)

    def changeImgOffset(self, imgidx, tx_or_4tuple,ty=None,rot=0,magX=1, magY=1, magZ=1, RefreshNow=1):
        '''if ty is None:
        tx_or_4tuple needs to be valid 4-tuple
              like e.g.(10,10,90,2)
                for shift 10right,10up,rot90deg,mag2x
        '''
        if ty is None:
            self.imgList[imgidx][9:15] = tx_or_4tuple
        else:
            self.imgList[imgidx][9:15] = [tx_or_4tuple, ty,rot,magX,magY, magZ]

        
        self.imgsGlListChanged = True  ## otherwise won't redraw

        if RefreshNow:
            self.Refresh(False)

    def setColor(self, imgidx, r_or_RBG,g=None,b=None, RefreshNow=1):
        if g is None:
            r_or_RBG,g,b = r_or_RBG
        self.imgList[imgidx][6:9] = [r_or_RBG,g,b]
        self.imgsGlListChanged = True
        if RefreshNow:
            self.Refresh(0)

    def setVisibility(self, imgidx, visible_or_not, RefreshNow = 1):
        self.imgList[imgidx][1] = visible_or_not
        self.imgsGlListChanged = True
        if RefreshNow:
            self.Refresh(0)
        
    def OnPaint(self, event):

        try:
            dc = wx.PaintDC(self)
        except wx._core.wxAssertionError:# 20201122 MacOS Big Sur
            pass
        except:
            return

        try:
            if self.w <=0 or self.h <=0:
                # THIS IS AFTER wx.PaintDC -- OTHERWISE 100% CPU usage
                return
        except AttributeError:
            self.w, self.h = self.GetClientSize() #Tuple()   ## hack for MSW: the 1st OnPaint call happens before OnSize()

        if self.error:
            return

        old="""
        if wx.VERSION >= (2,9):
            if self.GetParent().IsShown():
                if hasattr(self, 'context') and (self.context is not None):
                    self.SetCurrent(self.context)
                    print 'found context'
                else:
                    self.SetCurrent()
        else:
                    
            if not self.GetContext(): #Obtains the context that is associated with this canvas
                print "OnPaint GetContext() error"
                return"""
        
        self.SetCurrent(self.context)
  
        if not self.GLinit:
            self.InitGL()

        #viewer2: viewer.py has this in InitTex ()
        if not self.gllist:
            self.gllist = glGenLists( 2 )  # generate a contiguous set of empty display lists
            ## self.gllist, self.gllist + 1 are created

        if self.doViewportChange:  ## OnSize()
            glViewport(0, 0, self.w, self.h)
            glMatrixMode (GL_PROJECTION)
            glLoadIdentity ()
            #glOrtho (-.375, self.w-.375, -.375, self.h-.375, 1., -1.) # why -.375?
            glOrtho (0, self.w, 0, self.h, 1., -1.)
            glMatrixMode (GL_MODELVIEW)
            self.doViewportChange = False


        if self.gllist_Changed:   ## new graphic objects
            try:
                self.defGlList
                
                glNewList( self.gllist+1, GL_COMPILE )
                try:
                    for gll in self.defGlList:
                        gll()
                except TypeError: #'list' object is not callable
                    #raise
                    self.defGlList()                    
                glEndList()
            except:
                import traceback as tb
                tb.print_exc(limit=None, file=None)
                self.error = "error with self.defGlList()"
                print("ERROR:", self.error, self.defGlList)
            self.gllist_Changed = False


        if len( self.loadImgsToGfxCard ):  # images to load
            for imgidx in self.loadImgsToGfxCard:
                img = self.imgList[imgidx][2]
                mi,ma = self.imgList[imgidx][4:6]
                #print mi, type(mi)
                if mi == None: # don't know how this happens
                    # seems to happen at the start
                    #print 'warning: mi==None'
                    mi = 0
                self._setHistScale(mi,ma,
                       dataTypeMaxValue_table[img.dtype.type])

                self._loadImgIntoGfx(imgidx) ## textureID and texture are bound
            self.loadImgsToGfxCard = []

        if self.zoomChanged  and len(self.imgList)>0:   # Lin  self.pic_nx undefined exception
            if self.x0 is None:  ## only happens at 1st OnPaint() call
                self.center(refreshNow=False)

            sx,sy = self.scale,self.scale* self.aspectRatio
            #offX,offY = sx*self.pic_nx/2., sy*self.pic_ny/2.

            glMatrixMode (GL_MODELVIEW)
            glLoadIdentity ()
            glTranslate(self.x0, self.y0,0)
            #glTranslate(offX,offY,0)
            glRotate(self.rot, 0,0,1)
            glScaled(sx,sy,1.)
           # glTranslate(-offX,-offY,0)

            self.myViewManager.updateGLGraphics()

            self.zoomChanged = False

        ## cut preview
        old="""
        if self.myViewManager.IsCut():
            ly = self.mydoc.cropbox_l[self.dims[0]]
            uy = self.mydoc.cropbox_u[self.dims[0]]
            lx = self.mydoc.cropbox_l[self.dims[1]]
            ux = self.mydoc.cropbox_u[self.dims[1]]
            sx, sy = self.scale, self.scale* self.aspectRatio

            ## -0.05 in eqn0 and eqn2 is to make sure the binding box appears correctly in zoomed view
            eqn0 = [0.0, 1.0, 0.0, -(ly-0.05)]
            eqn1 = [0.0, -1.0, 0.0, (uy)]
            eqn2 = [1.0, 0.0, 0.0, -(lx-0.05)]
            eqn3 = [-1.0, 0.0, 0.0, (ux)]
            glClipPlane(GL_CLIP_PLANE0, eqn0)
            glEnable(GL_CLIP_PLANE0)
            glClipPlane(GL_CLIP_PLANE1, eqn1)
            glEnable(GL_CLIP_PLANE1)
            glClipPlane(GL_CLIP_PLANE2, eqn2)
            glEnable(GL_CLIP_PLANE2)
            glClipPlane(GL_CLIP_PLANE3, eqn3)
            glEnable(GL_CLIP_PLANE3)
        else:"""
        glDisable(GL_CLIP_PLANE0)
        glDisable(GL_CLIP_PLANE1)
        glDisable(GL_CLIP_PLANE2)
        glDisable(GL_CLIP_PLANE3)
            

        if self.imgsGlListChanged:
            glNewList( self.gllist, GL_COMPILE )

            ## first, for each image in the list at its particular position,
            ## draw a black rectangle so that the colors can blend
            glColor3i(0, 0, 0)
            for w, imgListItem in enumerate(self.imgList): # black background
                if imgListItem[1]:
                    tx,ty,rot,magX,magY,magZ = imgListItem[9:15]
                    magXYZ = N.array((magX, magY, magZ), N.float64)


                    if rot or N.any(magXYZ != 1):
                        cxy = self.ld[::-1].astype(N.float64) + N.array((self.pic_nx, self.pic_ny), N.float64)/2.
                        mx, my = (cxy - cxy * magXYZ[:2])/magXYZ[:2]
                        if self.dims == (0,2): # x-z
                            cz = self.ld[0] + self.mydoc.nz / 2.
                            mz = (cz - cz * magZ) / magZ
                            #mx -= 2
                        elif self.dims == (1,0): # z-y
                            cz = self.ld[1] + self.mydoc.nz / 2.
                            mz = (cz - cz * magZ) / magZ
                        else:
                            mz = 0
                        rxy = imgGeo.RotateXY(cxy, rot)
                        fxy = cxy - rxy
                        fx,fy = imgGeo.RotateXY(fxy, -rot)
                    else:
                        mz=mx=my=fx=fy=0

                    if self.dims != (1,2):
                        mx = my = 0
                        magX = magY = 1

                    glPushMatrix()

                    # some versions of GL requires double instead of numpy.float32
                    rot = float(rot)
                    magX = float(magX)
                    magY = float(magY)
                    magZ = float(magZ)
                    mx = float(mx)
                    my = float(my)
                    mz = float(mz)
                    
                    if self.dims == (1,2):   ## mag both dimesions in x-y view
                        glScaled(magX,magY, 1)
                        glTranslated(mx,my, 0)
                    elif self.dims == (0,2): ## mag only horizontal dimesion in x-z view
                        glScaled(magX, magZ, 1)
                        glTranslated(mx,mz, 0)
                    elif self.dims == (1,0): ## mag only vertical dimesion in z-y view
                        glScaled(magZ, magY, 1)
                        glTranslated(mz,my, 0)
                    glRotated(rot, 0,0,1)
                    glTranslated(tx+fx,ty+fy, 0)
                    glBegin(GL_QUADS)
                    glVertex2i(0, 0)
                    glVertex2i(self.pic_nxs[w], 0)
                    glVertex2i(self.pic_nxs[w], self.pic_nys[w])
                    glVertex2i(0, self.pic_nys[w])
                    glEnd()
                    glPopMatrix()


            for imgListItem in self.imgList: # image part
                if imgListItem[1]:
                    tx,ty,rot,magX,magY,magZ = imgListItem[9:15]
                    magXYZ = N.array((magX, magY, magZ))
                        
                    if rot or N.any(magXYZ != 1):
                        cxy = self.ld[::-1] + N.array((self.pic_nx, self.pic_ny))/2.
                        mx, my = (cxy - cxy * magXYZ[:2])/magXYZ[:2]
                        if self.dims == (0,2):
                            cz = self.ld[0] + self.mydoc.nz / 2.
                            mz = (cz - cz * magZ) / magZ
                            #mx -= 2
                        elif self.dims == (1,0):
                            cz = self.ld[1] + self.mydoc.nz / 2.
                            mz = (cz - cz * magZ) / magZ
                        else:
                            mz = 0
                        rxy = imgGeo.RotateXY(cxy, rot)
                        fxy = cxy - rxy
                        fx,fy = imgGeo.RotateXY(fxy, -rot)
                    else:
                        mz=mx=my=fx=fy=0
                    
                    if 0:#self.dims != (1,2):
                        mx = my = 0
                        magX = magY = 1
                    glPushMatrix()

                    # some versions of GL requires double instead of numpy.float32
                    rot = float(rot)
                    magX = float(magX)
                    magY = float(magY)
                    magZ = float(magZ)
                    mx = float(mx)
                    my = float(my)
                    mz = float(mz)
                    if self.dims == (1,2):   ## mag both dimesions in x-y view
                        glScaled(magX,magY, 1)
                        glTranslated(mx,my, 0)
                    elif self.dims == (0,2):   ## mag only horizontal dimesion in x-z view
                        #print(self.dims,magX,magZ)
                        glScaled(magX, magZ, 1)
                        glTranslated(mx,mz, 0)
                        #pass
                    elif self.dims == (1,0):  ## mag only vertical dimesion in z-y view
                        glScaled(magZ, magY, 1)
                        glTranslated(mz,my, 0)

                    glRotated(rot, 0,0,1)
                    glTranslated(tx+fx,ty+fy, 0)

                    glColor3fv(imgListItem[6:9])

                    ## display list for this particular 2D image created in addImg()
                    glCallList( imgListItem[0] )
                    glPopMatrix()

            glEndList()
            self.imgsGlListChanged = False

        #  clear color and depth buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glCallLists( [self.gllist, self.gllist+1] )
                
        if self.moreMaster_enabled:
            enabledGLlists = [i for (i,on) in zip(self.moreGlLists,
                                              self.moreGlLists_enabled) if on]
            if len(enabledGLlists):
                glCallLists( enabledGLlists )
        
        glFlush()
        self.SwapBuffers() ### <- memory leak on ubuntu18.04LTS?? use GetDC??

    def setImageL(self, imgArrL, refreshNow=1):
        for i in range(len(imgArrL)):
            self.setImage(i, imgArrL[i], 0)
        if refreshNow:
            self.Refresh(0)
        
    def setImage(self, i, imgArr, refreshNow=1):
        if self.imgList[i][2].shape != imgArr.shape:
            # in this case we 
            #  1. do "parts of" delImage
            #  2. add img to postion i
            imgListItem = self.imgList[i]
            glDeleteTextures( imgListItem[3] )
            glDeleteLists(imgListItem[0], 1)
            rgb = self.imgList[i][6:9]   # reuse RGB settings
            del self.imgList[i]
            #self.pic_nys.pop(i)
            #self.pic_nxs.pop(i)
            self.addImg(imgArr, smin=0, smax=0, alpha=1., interp=0, imgidx=i, refreshNow=refreshNow)
            self.imgList[i][6:9] = rgb   # reuse RGB settings
            #self.setLeftDown()
        else:
            self.imgList[i][2] = imgArr
            self.loadImgsToGfxCard.append( i )

            if refreshNow:
                self.Refresh(0)

    def delImage(self, i, refreshNow=1):
        imgListItem = self.imgList[i]
        glDeleteTextures( imgListItem[3] )
        glDeleteLists(imgListItem[0], 1)
        del self.imgList[i]
        self.imgsGlListChanged=1
        if refreshNow:
            self.Refresh(0)

    def delAllImages(self, refreshnow=1):
        for imgItem in self.imgList:
            glDeleteTextures( imgItem[3] )
            glDeleteLists(imgItem[0], 1)
            del imgItem[2]
        self.imgList = []
        self.imgsGlListChanged=1
        if refreshnow:
            self.Refresh(0)
            

    def doOnFrameChange(self):
        '''
        Called by self.OnSize() and self.OnMove()
        '''
        pass

    def doOnMouse(self, xeff, yeff, xyEffVal):
        if hasattr(self.mydoc, 'roi_start'):
            mydoc = self.mydoc
        else:
            mydoc = self.mydoc.img
        ly = mydoc.roi_start[self.dims[0]] #cropbox_l[self.dims[0]]
        uy = mydoc.roi_size[self.dims[0]] + ly #cropbox_u[self.dims[0]]
        lx = mydoc.roi_start[self.dims[1]] #cropbox_l[self.dims[1]]
        ux = mydoc.roi_size[self.dims[1]] + lx #cropbox_u[self.dims[1]]
        
        sliceIdx = [self.mydoc.z, self.mydoc.y, self.mydoc.x]
        horizontal_line = sliceIdx[self.dims[0]]
        vertical_line   = sliceIdx[self.dims[1]]

        shapes = N.empty((self.mydoc.nw, 2), N.uint)
        for w, img in enumerate(self.imgList):
            shapes[w] = img[2].shape[-2:]
        pic_ny, pic_nx = shapes.max(0)

        x = xeff
        y = yeff
        
        if not (self.dragSide and self.cropboxDragging) and (self.useHair or self.useCropbox): ## once drag starts, don't change the drag side

            # dragSide                               
            #                    uy                  10
            # 2|       3         |4                  |
            #-----------------------                 |
            #  |                 |                   |
            #  |                 |                   |
            #  |                 |                   |
            # 1|       11        |5      ------------|--------------- 9
            #  |                 |                   |
            #  |                 |                   |
            #  |                 |                   |
            #-----------------------                 |
            # 8|       7         |6                  |
            #  lx                ux
            #  ly
            #      or 0

            
            self.vclose = False
            self.hclose = False
            if wx.version().startswith('3'):
                Cursor = wx.StockCursor
            else:
                Cursor = wx.Cursor
            if abs(x-lx) <=4 and abs(y-uy) <=4 and self.useCropbox:
                self.SetCursor(Cursor(wx.CURSOR_SIZENWSE))
                self.dragSide = 2
            elif abs(x-ux) <=4 and abs(y-ly) <=4 and self.useCropbox:
                self.SetCursor(Cursor(wx.CURSOR_SIZENWSE))
                self.dragSide = 6
            elif abs(x-lx) <=4 and abs(y-ly) <=4 and self.useCropbox:
                self.SetCursor(Cursor(wx.CURSOR_SIZENESW))
                self.dragSide = 8
            elif abs(x-ux) <=4 and abs(y-uy) <=4 and self.useCropbox:
                self.SetCursor(Cursor(wx.CURSOR_SIZENESW))
                self.dragSide = 4
            elif lx < x < ux and ( abs(y-ly) <=2 or abs(y-uy) <=2) and self.useCropbox:
                self.SetCursor(Cursor(wx.CURSOR_SIZENS))
                if abs(y - ly) < abs(y - uy):
                    self.dragSide = 7
                else:
                    self.dragSide = 3
            elif ly < y < uy and ( abs(x-lx) <=2 or abs(x-ux) <=2 ) and self.useCropbox:
                self.SetCursor(Cursor(wx.CURSOR_SIZEWE))
                if abs(x - lx) <=2 < abs(x - ux):
                    self.dragSide = 1
                else:
                    self.dragSide = 5
            elif 0:#x > (lx + 2) and x < (ux - 2) and y > (ly + 2) and y < (uy - 2) and self.useCropbox:
                self.SetCursor(self.defaultCursor)
                self.dragSide = 11
                    
            elif abs(y - horizontal_line) <=1 and self.useHair:
                self.SetCursor(Cursor(wx.CURSOR_SIZENS))
                self.dragSide = 9
                self.hclose = True
                self.vclose = False
            elif abs(x - vertical_line) <=1 and self.useHair:
                self.SetCursor(Cursor(wx.CURSOR_SIZEWE))
                self.dragSide = 10
                self.vclose = True
                self.hclose = False
            elif not self.cropboxDragging:
                self.dragSide = 0
                self.SetCursor(self.defaultCursor)
                self.vclose = False
                self.hclose = False
            ## else:
            ##     self.vclose = False
            ##     self.hclose = False
            #print self.dragSide, self.cropboxDragging, self.useHair, self.useCropbox, not (self.dragSide and self.cropboxDragging), (self.useHair or self.useCropbox), abs(x-lx) <=2,  abs(y-uy) <=2


        viewer2update = -1 ## only when dragging sectioning lines is a viewer# (0,1,2) needed
        if self._onMouseEvt.LeftIsDown():
            if self.cropboxDragging:
                prev_y0 = mydoc.roi_start[self.dims[0]]
                prev_x0 = mydoc.roi_start[self.dims[1]]
                
                if self.dragSide == 1:
                    mydoc.roi_start[self.dims[1]] = x if 0 <= x < ux else ( 0 if x <0 else ux-1 )
                    mydoc.roi_size[self.dims[1]] -= (x - prev_x0) if 0 <= x < ux else 0
                elif self.dragSide == 5:
                    mydoc.roi_size[self.dims[1]] = x - lx if lx < x < pic_nx else ( pic_nx - lx if x >=pic_nx else lx+1)
                elif self.dragSide == 3:
                    mydoc.roi_size[self.dims[0]] = y - ly if ly < y < pic_ny else (pic_ny - ly if y >= pic_ny else ly+1) 
                elif self.dragSide == 7:
                    mydoc.roi_start[self.dims[0]] = y if 0 <= y < uy else (0 if y <0 else uy -1)
                    mydoc.roi_size[self.dims[0]] -= (y - prev_y0) if 0 <= y < uy else 0
                elif self.dragSide == 2:
                    mydoc.roi_start[self.dims[1]] = x if 0 <= x < ux else ( 0 if x <0 else ux-1 )
                    mydoc.roi_size[self.dims[1]] -= (x - prev_x0) if 0 <= x < ux else 0
                    mydoc.roi_size[self.dims[0]] = y -ly if ly < y < pic_ny else (pic_ny - ly if y >= pic_ny else ly+1)
                elif self.dragSide == 4:
                    mydoc.roi_size[self.dims[1]] = x - lx if lx < x < pic_nx else ( pic_nx - lx if x >=pic_nx else lx+1)
                    mydoc.roi_size[self.dims[0]] = y - ly if ly < y < pic_ny else (pic_ny - ly if y >= pic_ny else ly+1) 
                elif self.dragSide == 6:
                    mydoc.roi_size[self.dims[1]] = x -lx if lx < x < pic_nx else ( pic_nx - lx if x >=pic_nx else lx+1)
                    mydoc.roi_start[self.dims[0]] = y if 0 <= y < uy else (0 if y <0 else uy -1)
                    mydoc.roi_size[self.dims[0]] -= (y - prev_y0) if 0 <= y < uy else 0
                elif self.dragSide == 8:
                    mydoc.roi_start[self.dims[1]] = x if 0 <= x < ux else (0 if x <0 else ux -1)
                    mydoc.roi_size[self.dims[1]] -= (x - prev_x0) if 0 <= x < ux else 0
                    mydoc.roi_start[self.dims[0]] = y if 0 <= y < uy else (0 if y <0 else uy -1)
                    mydoc.roi_size[self.dims[0]] -= (y - prev_y0) if 0 <= y < uy else 0

                elif self.dragSide == 11:
                    mydoc.roi_start[self.dims[1]] = x if 0 <= x < ux else (0 if x <0 else ux -1)
                    if (x + mydoc.roi_size[self.dims[1]]) > pic_nx:
                        mydoc.roi_size[self.dims[1]] = pic_nx - x
                    mydoc.roi_start[self.dims[0]] = y if 0 <= y < uy else (0 if y <0 else uy -1)
                    if (y + mydoc.roi_size[self.dims[0]]) > pic_ny:
                        mydoc.roi_size[self.dims[0]] = pic_ny - y
                    
                elif self.dragSide == 9:  ## horizontal sectioning line
                    v = y if 0<=y<pic_ny else (0 if y < pic_ny//2 else pic_ny-1)
                    viewer2update = self.dims[0]
                    if self.dims[0] == 0:
                        self.mydoc.z = v
                        if 0 <= v < pic_ny:
                            parent = self.GetParent()
                            parent.zSliderBox.SetValue(str(int(v)))
                            parent.zSlider.SetValue(int(v))
                            #parent.OnZSliderBox()
                    elif self.dims[0] == 1:
                        self.mydoc.y = v
                    elif self.dims[0] == 2:
                        self.mydoc.x = v
                elif self.dragSide == 10:  ## vertical sectioning line
                    viewer2update = self.dims[1]
                    v = x if 0<=x<pic_nx else (0 if x < pic_nx//2 else pic_nx-1)

                    if self.dims[1] == 0:
                        self.mydoc.z = v
                        if 0<= v < pic_nx:
                            parent = self.GetParent()
                            parent.zSliderBox.SetValue(str(int(v)))
                            parent.zSlider.SetValue(int(v))
                            #parent.OnZSliderBox()
                    elif self.dims[1] == 1:
                        self.mydoc.y = v
                    elif self.dims[1] == 2:
                        self.mydoc.x = v
                self.myViewManager.updateGLGraphics(viewer2update)
                #print self.mydoc.z, self.mydoc.y, self.mydoc.x, mydoc.roi_start, mydoc.roi_size, y, x, self.y0, self.x0
                #print self.dragSide, self.cropboxDragging, self.useHair, self.useCropbox, not (self.dragSide and self.cropboxDragging), (self.useHair or self.useCropbox), abs(x-lx) <=2,  abs(y-uy) <=2

        for wi in range(self.mydoc.nw):
            if hasattr(self.mydoc, 'alignParms'):
                tz, ty, tx, rot, magz, magy, magx = self.mydoc.alignParms[self.mydoc.t,wi][:7]
            else:
                tz, ty, tx, rot, magz, magy, magx = 0, 0, 0, 0, 1, 1, 1
            magYX = N.array((magy, magx))
            if self.dims == (1,2) and (abs(ty) >0 or abs(tx) >0 or abs(rot)>0 or N.any(abs(magYX-1)>0)):
                rotRadian = -N.pi / 180. * rot   ## rotation in OpenGL is counter-clockwise for positive angle
                cosTheta = N.cos(rotRadian)
                sinTheta = N.sin(rotRadian)
                affmatrix = N.array([ [cosTheta, sinTheta], [-sinTheta, cosTheta] ]) * magYX
                invmat = N.linalg.inv(affmatrix)
                xyCenter = [self.mydoc.nx/2., self.mydoc.ny/2.]
                xy_input = N.dot(invmat, N.array([x, y]) - xyCenter) + xyCenter - [tx, ty]
                
            elif self.dims == (0,2) and (abs(tz) >0 or abs(tx) >0):
                xy_input = N.array([x, y]) - [tx, tz]
            elif self.dims == (1,0) and (abs(ty) >0 or abs(tx) >0):
                xy_input = N.array([x, y]) - [tz, ty]
            else:
                xy_input = [x, y]
            xi, yi = xy_input

            pic_ny, pic_nx = self.imgList[wi][2].shape[-2:]
            if 0 <= xi < pic_nx and 0 <= yi < pic_ny:
                if self.dims == (1,2):
                    xy_t = "Cursor XY: "
                elif self.dims == (0,2):
                    xy_t = "Cursor XZ: "
                elif self.dims == (1,0):
                    xy_t = "Cursor ZY: "
                t ="Value: %.2f" % self.imgList[wi][2][int(yi), int(xi)]
                xy_t += "(%d, %d)" %  (xi, yi)
            else:
                t = "Outside of image"
                xy_t = "Outside of image"
            parent = self.GetParent()
            parent.intensity_label[wi].SetLabel(t)
        parent.xy_label.SetLabel(xy_t)

        roi0 = 'ROI start (x,y,z):  %i %i %i' % tuple(self.mydoc.roi_start[::-1])
        roi1 = 'ROI size  (x,y,z):  %i %i %i' % tuple(self.mydoc.roi_size[::-1])
        parent.roi_label0.SetLabel(roi0)
        parent.roi_label1.SetLabel(roi1)

    
    def doLDown(self, xeff, yeff):
        if self.dragSide:  ## drag only starts after cursor has changed, i.e., dragSide >0
            self.cropboxDragging = True

    def doLUp(self):
        self.cropboxDragging = False
        #self.dragSide = 0

    def OnMouse(self, ev):
        if ev.Entering():
            self.SetFocus()
        self._onMouseEvt = ev  # be careful - only use INSIDE a handler function that gets call from here
        if self.x0 is None:
            return # before first OnPaint call

        x = ev.GetX()
        y = self.h-ev.GetY()

        x0, y0, scale, aspR = self.x0, self.y0, self.scale, self.aspectRatio
        xEff, yEff = int( (x-x0)/scale ) - self.ld[1], int( (y-y0)/(scale*aspR) ) - self.ld[0]

        xyEffInside = False

        midButt = ev.MiddleDown() or (ev.LeftDown() and ev.AltDown())
        midIsButt = ev.MiddleIsDown() or (ev.LeftIsDown() and ev.AltDown())
        rightButt = ev.RightDown() or (ev.LeftDown() and ev.ControlDown())
        
        if ev.Leaving():
            ## leaving trigger  event - bug !!
            parent = self.GetParent()
            [l.SetLabel('') for l in parent.intensity_label]

            return
        
        if midButt or (ev.LeftDown() and not self.dragSide):
            self.mouse_last_x, self.mouse_last_y = x,y
        elif midIsButt or (ev.LeftIsDown() and not self.dragSide):
            self.keepCentered = False
            if ev.ShiftDown() or ev.ControlDown():
                #dx = x-self.mouse_last_x
                dy = y-self.mouse_last_y

                fac = 1.05 ** (dy)
                self.scale *= fac
                w2 = self.w/2.
                h2 = self.h/2.
                self.x0 = w2 - (w2-self.x0)*fac
                self.y0 = h2 - (h2-self.y0)*fac
                self.zoomChanged = True

            else:
                self.x0 += (x-self.mouse_last_x) #/ self.sx
                self.y0 += (y-self.mouse_last_y) #/ self.sy

            self.zoomChanged = 1
            self.mouse_last_x, self.mouse_last_y = x,y
            self.Refresh(0)

        elif rightButt:
            pt = ev.GetPosition()
            self.PopupMenu(self.menu, pt)
        elif ev.LeftDown():
            ## HACK: why float?? xEff,yEff = (x-x0)/scale ,  (y-y0)/scale # float !
            self.doLDown(xEff,yEff)
        elif ev.LeftUp():
            self.doLUp()
        elif ev.LeftDClick():
            xEff,yEff = (x-x0)/scale ,  (y-y0)/scale # float !          
            self.doLDClick(xEff,yEff)
            print(xEff, yEff, x, y)

        #if xyEffInside:
        self.doOnMouse(xEff, yEff, None)
        ev.Skip() # other things like EVT_MOUSEWHEEL are lost

    def OnReload(self, event=None):
        self.Refresh(False)

    def OnArrowKeys(self, event):
        old="""
        sliceIdx = [self.mydoc.z, self.mydoc.y, self.mydoc.x]
        horizontal_line = sliceIdx[self.dims[0]]
        vertical_line   = sliceIdx[self.dims[1]]
        
        x = self.xEff
        y = self.yEff
        if abs(y - horizontal_line) <=1:
            hclose = True
        else:
            hclose = False

        if abs(x - vertical_line) <=1:
            vclose = True
        else:
            vclose = False"""
        
        
        evtId = event.GetId()
        if  evtId == 2051 and self.vclose: ## left arrow
            print('left', self.dims)
            if self.dims[1] == 0 and self.mydoc.z > 0:
                self.mydoc.z -= 1
            elif self.dims[1] == 1 and self.mydoc.y > 0:
                self.mydoc.y -= 1
            elif self.dims[1] == 2 and self.mydoc.x > 0:
                self.mydoc.x -= 1
            #if self.mydoc.sliceIdx[self.dims[1]] >0:
            #    self.mydoc.sliceIdx[self.dims[1]] -= 1
        elif evtId == 2052 and self.vclose:   ## right arrow
            print('right', self.dims, self.mydoc.x, self.pic_nx-1)
            if self.dims[1] == 0 and self.mydoc.z < (self.pic_nx-1):
                self.mydoc.z += 1
            elif self.dims[1] == 1 and self.mydoc.y < (self.pic_nx-1):
                self.mydoc.y += 1
            elif self.dims[1] == 2 and self.mydoc.x < (self.pic_nx-1):
                self.mydoc.x += 1
            #if self.mydoc.sliceIdx[self.dims[1]] < self.pic_nx-1:
            #    self.mydoc.sliceIdx[self.dims[1]] += 1
        elif evtId == 2053 and self.hclose:   ## up arrow
            print('up', self.dims, self.mydoc.x, self.pic_nx-1)
            if self.dims[0] == 0 and self.mydoc.z < (self.pic_ny-1):
                self.mydoc.z += 1
            elif self.dims[0] == 1 and self.mydoc.y < (self.pic_ny-1):
                self.mydoc.y += 1
            elif self.dims[0] == 2 and self.mydoc.x < (self.pic_ny-1):
                self.mydoc.x += 1
            #if self.mydoc.sliceIdx[self.dims[0]] < self.pic_ny-1:
            #    self.mydoc.sliceIdx[self.dims[0]] += 1
        elif evtId == 2054 and self.hclose:   ## down arrow
            print('down', self.dims)
            if self.dims[0] == 0 and self.mydoc.z > 0:
                self.mydoc.z -= 1
            elif self.dims[0] == 1 and self.mydoc.y > 0:
                self.mydoc.y -= 1
            elif self.dims[0] == 2 and self.mydoc.x > 0:
                self.mydoc.x -= 1
            #if self.mydoc.sliceIdx[self.dims[0]] >0:
            #    self.mydoc.sliceIdx[self.dims[0]] -= 1
            
        self.myViewManager.updateGLGraphics(self.dims[1] if evtId == 2051 or evtId == 2052 else self.dims[0])
        #self.dragSize = 0   ## to prevent the next mouse click from changing slicing lines abruptly
        event.Skip()

