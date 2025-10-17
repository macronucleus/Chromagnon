"""provides the bitmap OpenGL panel for Priithon's ND 2d-section-viewer (multi-color version)"""
from __future__ import print_function
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

from .viewerCommon import *


dataTypeMaxValue_table = {
    N.uint16: (1<<16) -1,
    N.int16:  (1<<15) -1, ## check
    N.uint8:  (1<<8) -1, ## check
    N.bool_:  (1<<8) -1, ## check
    N.float32: 1
    }
class GLViewer(GLViewerCommon):
    def __init__(self, parent, size=wx.DefaultSize, originLeftBottom=None):#, depth=32):
        GLViewerCommon.__init__(self, parent, size, originLeftBottom)#, depth=depth)
        
        ###self.m_imgChanged = True
        self.m_imgsGlListChanged = False
#       self.m_histScaleChanged = True
#       if originLeftBottom is None:
#           if imgArr.shape[1] == imgArr.shape[0]/2 + 1:
#               self.m_originLeftBottom = 8  # output from real_fft2d --- data nx is half-sized
#           else:
#               self.m_originLeftBottom = 1
#       else:
#           self.m_originLeftBottom = originLeftBottom
        self.m_originLeftBottom = 1

#       self.m_imgArr = None
    #       self.pic_nx = 0
    #       self.pic_ny = 0
        #20070823-colmap2 ?? self.colMap = None
        #20070823-colmap2 ?? self.colMap_menuIdx = 0

        #HACK to make center() at startup happy
        self.pic_nx = 0  # size as used in current texture
        self.pic_ny = 0

        self.m_gllist = None
    #       self.m_texture_list = None

        self.m_imgList = [] # each elem.:
        # 0       1        2       3            4     5   6 7 8   9, 10,11, 12
        #[gllist, enabled, imgArr, textureID, smin, smax, r,g,b,  tx,ty,rot,mag]

        self.m_loadImgsToGfxCard = []
        self.m_gllist_Changed = False # call defGlList() from OnPaint

        #//note:"ToolTip just annoys"  SetToolTip(wx.String::Format("cam %d", camId))
        if not wx.Platform == '__WXMSW__': #20070525-black_on_black on Windows
            self.SetCursor(wx.CROSS_CURSOR)

        #20171225-PY2to3 deprecation warning use meth: EvtHandler.Bind -> self.Bind()
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        #wx.EVT_PAINT(self, self.OnPaint)
        
        #EVT_MIDDLE_DOWN(self, self.OnMiddleDown)
        self.MakePopupMenu()
        ###          wx.Yield() # setImage has gl-calls - so lets make the window first...
        ###          self.setImage(imgArr)

        
    def MakePopupMenu(self):
        """Make a menu that can be popped up later"""
        self.m_menu = wx.Menu()

        self.m_menu_save = wx.Menu()
        self.m_menu_save.Append(Menu_Save,    "save 2d sec into file")
        self.m_menu_save.Append(Menu_SaveScrShot, "save 2d screen shot 'as seen'")
        self.m_menu_save.Append(Menu_SaveClipboard, "save 2d screen shot 'as seen' into clipboard")
        self.m_menu_save.Append(Menu_Assign,  "assign 2d sec to a var name")

        # m_pMenuPopup->Append(Menu_Color, "&Change color")
        self.m_menu.Append(Menu_Zoom2x,    "&zoom 2x\td")
        #self.m_menu.Append(Menu_ZoomCenter,"zoom &Center here")
        self.m_menu.Append(Menu_Zoom_5x,   "z&oom .5x\th")
        self.m_menu.Append(Menu_ZoomReset, "zoom &reset\t0")
        self.m_menu.Append(Menu_ZoomCenter,"zoom &center\t9")
        self.m_menu.Append(Menu_chgOrig, "c&hangeOrig")
        self.m_menu.Append(Menu_Reload, "reload\tr")
        #20070823-colmap2 ?? self.m_menu.Append(Menu_Color, "change ColorMap")

        #20171225-PY2to3 deprecation warning use Append
        if wx.version().startswith('3') and not wx.version().endswith('(phoenix)'):
            self.m_menu.AppendMenu(wx.NewId(), "save", self.m_menu_save)
        else:
            self.m_menu.Append(wx.NewId(), "save", self.m_menu_save)
        ####self.m_menu.Append(Menu_Save, "save2d")
        self.m_menu.Append(Menu_aspectRatio, "change aspect ratio")
        self.m_menu.Append(Menu_rotate, "display rotated...")
        self.m_menu.Append(Menu_noGfx, "hide all gfx\tb", '',wx.ITEM_CHECK)

        #20171225-PY2to3 deprecation warning use meth: EvtHandler.Bind -> self.Bind()
        self.Bind(wx.EVT_MENU, self.OnCenter,          id=Menu_ZoomCenter)
        self.Bind(wx.EVT_MENU, self.OnZoomOut,         id=Menu_ZoomOut)
        self.Bind(wx.EVT_MENU, self.OnZoomIn,          id=Menu_ZoomIn)
        self.Bind(wx.EVT_MENU, self.OnMenu,            id=Menu_Zoom2x)
        self.Bind(wx.EVT_MENU, self.OnMenu,            id=Menu_Zoom_5x)
        self.Bind(wx.EVT_MENU, self.doReset,           id=Menu_ZoomReset)
        self.Bind(wx.EVT_MENU, self.OnReload,          id= Menu_Reload)
        self.Bind(wx.EVT_MENU, self.OnChgOrig,         id=Menu_chgOrig)
        self.Bind(wx.EVT_MENU, self.OnSave,            id=Menu_Save)
        self.Bind(wx.EVT_MENU, self.OnSaveScreenShort, id=Menu_SaveScrShot)
        self.Bind(wx.EVT_MENU, self.OnSaveClipboard,   id=Menu_SaveClipboard)
        self.Bind(wx.EVT_MENU, self.OnAssign,          id=Menu_Assign)
        self.Bind(wx.EVT_MENU, self.OnAspectRatio,     id=Menu_aspectRatio)
        self.Bind(wx.EVT_MENU, self.OnRotate,          id=Menu_rotate)
        self.Bind(wx.EVT_MENU, self.OnNoGfx,           id=Menu_noGfx)
                      
        #wx.EVT_MENU(self, Menu_ZoomCenter, self.OnCenter)
        #wx.EVT_MENU(self, Menu_ZoomOut, self.OnZoomOut)
        #wx.EVT_MENU(self, Menu_ZoomIn, self.OnZoomIn)
        #wx.EVT_MENU(self, Menu_Zoom2x,     self.OnMenu)
        #wx.EVT_MENU(self, Menu_ZoomCenter, self.OnMenu)
        #wx.EVT_MENU(self, Menu_Zoom_5x,    self.OnMenu)
        #wx.EVT_MENU(self, Menu_ZoomReset,  self.doReset) # OnMenu)
        #20070823-colmap2 ?? wx.EVT_MENU(self, Menu_Color,      self.OnColor)
        #wx.EVT_MENU(self, Menu_Reload,      self.OnReload)
        #wx.EVT_MENU(self, Menu_chgOrig,      self.OnChgOrig)
        #wx.EVT_MENU(self, Menu_Save,      self.OnSave)
        #wx.EVT_MENU(self, Menu_SaveScrShot,      self.OnSaveScreenShort)
        #wx.EVT_MENU(self, Menu_SaveClipboard,    self.OnSaveClipboard)
        #wx.EVT_MENU(self, Menu_Assign,      self.OnAssign)
        #wx.EVT_MENU(self, Menu_aspectRatio,      self.OnAspectRatio)
        #wx.EVT_MENU(self, Menu_rotate,      self.OnRotate)
        #wx.EVT_MENU(self, Menu_noGfx,      self.OnNoGfx)

    def InitGL(self):
#        (self.m_w, self.m_h) = self.GetClientSizeTuple()
        
        #        // Enable back face culling of polygons based upon their window coordinates.
        #        //glEnable(GL_CULL_FACE)
        #        // Enable two-dimensional texturing.
    
        #glClearColor(1.0, 1.0, 1.0, 0.0)
        #glClearColor(0.2, 0.3, 0.1, 0.0)
        glClearColor(0.0, 0.0, 0.0, 0.0)
#20050520       glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)

        #print "InitGL 2"
        """ now in if self.m_doViewportChange:
        glMatrixMode (GL_PROJECTION)
        glLoadIdentity ()
        #//glOrtho (-.375, width-.375, height-.375, -.375, 1., -1.)
        glOrtho (-.375, self.m_w-.375, -.375, self.m_h-.375, 1., -1.)
        #    //  The subtraction of .375 accounts for differences in rasterization of points,
        #    //  lines, and filled primitives in order to ensure their vertices map to pixel
        #    //  coordinates. The reversal of the Y coordinates should buy you a mapping to
        #    //  your inverted window coordinate space in which (0,0) is at the upper left
        #    //  corner.
        #  seb : WE DON'T WANT INVERSION THOUGH !!!!
        glMatrixMode (GL_MODELVIEW)
        glLoadIdentity ()
        #  //glViewport (0, 0, winWidth, winHeight)
        glViewport (0, 0, self.m_w, self.m_h)
        """

        self.m_init = True

    def addImgL(self, imgL, smin=0, smax=0, alpha=1., interp=0, refreshNow=1):
        for img in imgL:
            self.addImg(img, smin, smax, alpha, interp, refreshNow=0)
        if refreshNow:
            self.Refresh(0)
    def addImg(self, img, smin=0, smax=10000, alpha=1., interp=0, imgidx=None, refreshNow=1):
        """
        append new inage. Following lists get somthing appended:
        m_imgList
        m_loadImgsToGfxCard

        if imgidx is not None use 'insert(imgidx,...)' with m_imgList instead of append
        
        a new GL-texture is generated and an empty(!) texture with proper dtype is created.
        a new GL-Display-lists  is generated an compiled according to m_originLeftBottom
        """
        pic_ny,pic_nx = img.shape

        if len(self.m_imgList) == 0:  # some workaround code for functions originally written for viewer.py
            self.pic_ny, self.pic_nx = pic_ny,pic_nx

        if smin == smax == 0:
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

        wx.Yield()
        self.SetCurrent(self.context) # 20141127
        textureID = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, textureID)

        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBlendFunc(GL_ONE, GL_ONE) # 20070827
        #20070827 glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        #20070827
        # GL_LUMINANCE
        #     Each element is a single luminance value. The GL converts it to fixed-point 
        #     or floating-point, then assembles it into an RGBA element by replicating 
        #     the luminance value three times for red, green, and blue and 
        #     attaching 1 for alpha.

        # GL_LUMINANCE_ALPHA
        #     Each element is a luminance/alpha pair. The GL converts it to fixed-point 
        #     or floating point, then assembles it into an RGBA element by replicating 
        #     the luminance value three times for red, green, and blue.


        if interp: # FIXME put into gllist
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        else:
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST)

        if img.dtype.type in (N.uint8,N.bool_):
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

        #self.newGLListNow()
        curGLLIST = glGenLists( 1 )
        # 0       1        2       3            4     5   6 7 8
        #[gllist, enabled, imgArr, textureID, smin, smax, r,g,b]
        r,g,b=1,1,1
        imgListItem = [curGLLIST, 1, img, textureID, smin,smax, r,g,b,  0,0,0,1]
        glNewList( curGLLIST, GL_COMPILE )
        # Newsgroups: comp.graphics.api.opengl   Date: 1998/05/05
        # By the way, you don't have to explicitly delete a display list to reuse 
        # its name.  Simply call glNewList() again with the existing list name -- 
        # this will implicitly delete the old contents and replace them with the 
        # new ones; this will happen at glEndList() time. 

        glPushMatrix() # 20080701:  in new coord system, integer pixel coord go through the center of pixel
        glTranslate(-.5,-.5 ,0)

        glBindTexture(GL_TEXTURE_2D, textureID)
        glEnable(GL_TEXTURE_2D)
        ####        glColor4f(1.0, 1.0, 1.0, alpha)
        ##################################glColor3f(1.0, 0.0, 0.0);
        #  // Use a named texture.
        glBegin(GL_QUADS)
        
        ##BUG - HANGS glBindTexture(GL_TEXTURE_2D, self.m_texture_list)
        #          #  //    glNormal3f( 0.0F, 0.0F, 1.0F)
        
        #          #  //seb TODO  correct for pixel center vs pixel edge -> add .5 "somewhere"
        
        if self.m_originLeftBottom == 7 or \
           self.m_originLeftBottom == 8:
            sx = pic_nx
            ox = sx / 2
            sy = pic_ny
            oy = sy / 2
            hx = self.picTexRatio_x / 2. # fft half nyquist
            hy = self.picTexRatio_y / 2. # fft half nyquist
            fx = self.picTexRatio_x      # fft full nyquist
            fy = self.picTexRatio_y      # fft full nyquist
            

            #   quadrands(q): 2 | 1
            #                 --+--
            #                 3 | 4
            #


            d = 1 # display offset (how far left-down from center)
            ex = self.picTexRatio_x / sx
            ey = self.picTexRatio_y / sy

            # output from real_fft2d --- data nx is half-sized
            if self.m_originLeftBottom == 8:
                sx = (pic_nx-1) * 2
                ox = sx / 2
                hx = self.picTexRatio_x
                
                # data: dc left bottom(q 1)     display: dc left-down from center !
                # q 3                           q 1
                
                glTexCoord2f( 0, 0);            glVertex2i  ( ox-d, oy-d)
                glTexCoord2f( hx, 0);           glVertex2i  ( sx, oy-d)
                glTexCoord2f( hx, hy+ey);          glVertex2i  ( sx, sy)
                glTexCoord2f( 0, hy+ey);           glVertex2i  ( ox-d, sy)
                
                # q 2                           q 4
                glTexCoord2f( 0, fy);           glVertex2i  ( ox-d, oy-d)
                glTexCoord2f( 0, hy+ey);           glVertex2i  ( ox-d, 0)
                glTexCoord2f( hx, hy+ey) ;         glVertex2i  ( sx, 0)
                glTexCoord2f( hx, fy);          glVertex2i  ( sx, oy-d)
                
                
                # q 2 (real_fft2d) (4)          q 2
                glTexCoord2f( hx-ex, fy);       glVertex2i  ( 0,    oy)
                glTexCoord2f( hx-ex, hy);          glVertex2i  ( 0,    sy)
                glTexCoord2f( ex,    hy);          glVertex2i  ( ox-d, sy)
                glTexCoord2f( ex,    fy);       glVertex2i  ( ox-d, oy)

                # (real_fft2d) just 1 pixel row: y-dc x-neg
                glTexCoord2f( hx-ex, 0);       glVertex2i  ( 0,    oy)
                glTexCoord2f( hx-ex, ey);          glVertex2i  ( 0,    oy-d)
                glTexCoord2f( ex,    ey);          glVertex2i  ( ox-d, oy-d)
                glTexCoord2f( ex,    0);       glVertex2i  ( ox-d, oy)
                
                
                # q 3 (real_fft2d) (1)          q 3
                glTexCoord2f( ex,  ey );          glVertex2i  ( ox-d, oy-d)
                glTexCoord2f( hx-ex,    ey );          glVertex2i  ( 0 , oy-d)
                glTexCoord2f( hx-ex,    hy) ;         glVertex2i  ( 0 , 0)
                glTexCoord2f( ex, hy);          glVertex2i  ( ox-d, 0)
                
            else: # self.m_originLeftBottom == 7:

                # data: dc left bottom(q 1)     display: dc left-down from center !
                # q 3                           q 1
                glTexCoord2f( 0, 0);            glVertex2i  ( ox-d, oy-d)
                glTexCoord2f( hx+ex, 0);           glVertex2i  ( sx, oy-d)
                glTexCoord2f( hx+ex, hy+ey);          glVertex2i  ( sx, sy)
                glTexCoord2f( 0, hy+ey);           glVertex2i  ( ox-d, sy)
    
                # q 2                           q 4
                glTexCoord2f( 0, fy);           glVertex2i  ( ox-d, oy-d)
                glTexCoord2f( 0, hy+ey);           glVertex2i  ( ox-d, 0)
                glTexCoord2f( hx+ex, hy+ey) ;         glVertex2i  ( sx, 0)
                glTexCoord2f( hx+ex, fy);          glVertex2i  ( sx, oy-d)
    
                # q 4                           q 2
                glTexCoord2f( fx, 0);           glVertex2i  ( ox-d, oy-d)
                glTexCoord2f( fx, hy+ey);          glVertex2i  ( ox-d, sy)
                glTexCoord2f( hx+ex, hy+ey);          glVertex2i  ( 0 , sy)
                glTexCoord2f( hx+ex, 0);           glVertex2i  ( 0 , oy-d)
    
                # q 1                           q 3
                glTexCoord2f( fx, fy);          glVertex2i  ( ox-d, oy-d)
                glTexCoord2f( hx+ex, fy);          glVertex2i  ( 0 , oy-d)
                glTexCoord2f( hx+ex, hy+ey) ;         glVertex2i  ( 0 , 0)
                glTexCoord2f( fx, hy+ey);          glVertex2i  ( ox-d, 0)

        elif self.m_originLeftBottom:
            ###//(0,0) at left top
            
            glTexCoord2f( 0, 0)
            glVertex2i  ( 0, 0)
            
            glTexCoord2f( self.picTexRatio_x, 0)
            glVertex2i  ( pic_nx, 0)
            
            glTexCoord2f( self.picTexRatio_x, self.picTexRatio_y)
            glVertex2i  ( pic_nx, pic_ny)
            
            glTexCoord2f( 0, self.picTexRatio_y)
            glVertex2i  ( 0, pic_ny)
        else:
            ###//(0,0) at left bottom
            glTexCoord2f( 0,             self.picTexRatio_y)
            glVertex2i  ( 0,             0)
            
            glTexCoord2f( self.picTexRatio_x, self.picTexRatio_y)
            glVertex2i  ( pic_nx,         0)
            
            glTexCoord2f( self.picTexRatio_x, 0)
            glVertex2i  ( pic_nx,         pic_ny)
            
            glTexCoord2f( 0,             0)
            glVertex2i  ( 0,             pic_ny)
            
        glEnd()
        glDisable(GL_TEXTURE_2D) #20050520

        glPopMatrix() # 20080701:  in new coord system, integer pixel coord go through the center of pixel

        glEndList()
        #       idx = self.newGLListDone(refreshNow=1, enable=1)
        #       print idx
        #       self.m_moreGlLists_texture[idx] = texture_list
        #       self.m_moreGlLists_img[idx] = img
        if imgidx is None:
            imgidx = len(self.m_imgList)

        self.m_imgList.insert(imgidx, imgListItem)

        self.m_loadImgsToGfxCard.append( imgidx )
        self.m_imgsGlListChanged = True

        if len(self.m_imgList) == 1:
            self.m_zoomChanged = True

        if refreshNow:
            self.Refresh(0)

    def _loadImgIntoGfx(self, imgidx):
        img       = self.m_imgList[imgidx][2]
        textureID = self.m_imgList[imgidx][3]

        if img.dtype.type in (N.float64,
                              N.int32, N.uint32,N.int64, N.uint64):
            img = img.astype(N.float32)

        glBindTexture(GL_TEXTURE_2D, textureID)

        glPixelStorei(GL_UNPACK_ALIGNMENT, img.itemsize)
        glPixelStorei(GL_UNPACK_SWAP_BYTES, not img.dtype.isnative)

        imgString = img.tobytes() #tostring()
      
        pic_ny,pic_nx = img.shape

        if img.dtype.type in (N.uint8,N.bool_):
            glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny, 
                            GL_LUMINANCE,GL_UNSIGNED_BYTE, imgString)
        elif img.dtype.type == N.int16:
            glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny, 
                            GL_LUMINANCE,GL_SHORT,         imgString)
        elif img.dtype.type == N.float32:
            glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny, 
                            GL_LUMINANCE,GL_FLOAT,         imgString)
        elif img.dtype.type == N.uint16:
            glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny, 
                            GL_LUMINANCE,GL_UNSIGNED_SHORT, imgString)
        else:
            self.error = "unsupported data mode"
            raise ValueError(self.error)
        
    def _setHistScale(self, smin, smax, dataTypeMaxValue):
        #dataTypeMaxValue was  self.maxUShort = (1<<16)-1
        srange =     float(smax - smin)
        #  # const double maxUShort = double((unsigned short)-1)
        if srange == 0:
            fBias = 0
            f = 1
        else:
            fBias =  -smin / srange
            f     = dataTypeMaxValue / srange

        glPixelTransferf(GL_RED_SCALE,   f) #; // TODO HACK
        glPixelTransferf(GL_GREEN_SCALE, f)
        glPixelTransferf(GL_BLUE_SCALE,  f)
        
        glPixelTransferf(GL_RED_BIAS,   fBias)
        glPixelTransferf(GL_GREEN_BIAS, fBias)
        glPixelTransferf(GL_BLUE_BIAS,  fBias)

        #self.fBias = fBias  #for debug
        #self.f     = f
        
        #20070823-colmap2 ?? if self.colMap is not None:
        #20070823-colmap2 ??     glPixelTransferi(GL_MAP_COLOR, True);
        #20070823-colmap2 ??     glPixelMapfv(GL_PIXEL_MAP_R_TO_R, self.colMap[0] )
        #20070823-colmap2 ??     glPixelMapfv(GL_PIXEL_MAP_G_TO_G, self.colMap[1] )
        #20070823-colmap2 ??     glPixelMapfv(GL_PIXEL_MAP_B_TO_B, self.colMap[2] )
        #20070823-colmap2 ?? else:
        glPixelTransferi(GL_MAP_COLOR, False);
            # //printf("%8d %9f \n", -min, f)



    def defGlList(self):
        pass
    def updateGlList(self, glCallsFunctions, refreshNow=True):
        if glCallsFunctions is None:
            def x():
                pass
            self.defGlList = x
        else:
            self.defGlList = glCallsFunctions
        self.m_gllist_Changed = True
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

        self.m_gllist_Changed = True
        self.Refresh(False)

    

#   def 
#       glEndList()
        

    def changeHistogramScaling(self): #, smin=0, smax=0, RefreshNow=1):
        self.m_loadImgsToGfxCard += list(range(len(self.m_imgList)))
        self.Refresh(False)
#       if smin != smax:
#           self.m_minHistScale = smin
#           self.m_maxHistScale = smax

#       self.m_histScaleChanged = True

#       self.m_loadImgsToGfxCard += [idx \
#                                    for idx in range(len(self.m_moreGlLists_texture)) \
#                                                      if self.m_moreGlLists_texture[idx] ]
        
# #         ## self.m_imgChanged=True   #  // HACK HACK - i would prefer NOT to reload image into GfxCard
#       if RefreshNow:
#           self.Refresh(False)

    def changeHistScale(self, imgidx, smin,smax, RefreshNow=1):
        if imgidx == -1:
            for imgListItem in self.m_imgList:
                imgListItem[4:6] = [smin,smax]
            self.m_loadImgsToGfxCard += list(range(len(self.m_imgList)))
        else:
            self.m_imgList[imgidx][4:6] = [smin,smax]
            self.m_loadImgsToGfxCard += [imgidx]

        if RefreshNow:
            self.Refresh(False)

    def changeImgOffset(self, imgidx, tx_or_4tuple,ty=None,rot=0,mag=1, RefreshNow=1):
        """if ty is None:
        tx_or_4tuple needs to be valid 4-tuple
              like e.g.(10,10,90,2)
                for shift 10right,10up,rot90deg,mag2x
        """
        if ty is None:
            if len(tx_or_4tuple) != 4:
                raise ValueError("tx_or_4tuple must be a scalar or a tuple of length 4")
            self.m_imgList[imgidx][9:13] = tx_or_4tuple
        else:
            self.m_imgList[imgidx][9:13] = [tx_or_4tuple, ty,rot,mag]
        #self.m_loadImgsToGfxCard += [imgidx]
        self.m_imgsGlListChanged = True

        if RefreshNow:
            self.Refresh(False)

    def setColor(self, imgidx, r_or_RBG,g=None,b=None, RefreshNow=1):
        if g is None:
            r_or_RBG,g,b = r_or_RBG
        self.m_imgList[imgidx][6:9] = [r_or_RBG,g,b]
        self.m_imgsGlListChanged = True
        if RefreshNow:
            self.Refresh(0)
    def getColor(self, imgidx):
        return self.m_imgList[imgidx][6:9]

    def OnPaint(self, event):
        try:
            dc = wx.PaintDC(self)
        except wx._core.wxAssertionError:# 20201122 MacOS Big Sur
            pass
        except:
            # this windows is dead !?
            return

        #self.m_w, self.m_h = self.GetClientSizeTuple()
        try:
            if self.m_w <=0 or self.m_h <=0:
                # THIS IS AFTER wx.PaintDC -- OTHERWISE 100% CPU usage
                return
        except AttributeError:
            return
        if self.error:
            return
        #//seb check PrepareDC(dc)
        #if not self.GetContext():
        #    print "OnPaint GetContext() error"
        #    return
        
        self.SetCurrent(self.context) # 20141127
  
        if not self.m_init:
            self.InitGL()

        #viewer2: viewer.py has this in InitTex ()
        if not self.m_gllist:
            self.m_gllist = glGenLists( 2 )

        if self.m_doViewportChange:
            glViewport(0, 0, self.m_w, self.m_h)
            glMatrixMode (GL_PROJECTION)
            glLoadIdentity ()
            glOrtho (-.375, self.m_w-.375, -.375, self.m_h-.375, 1., -1.)
            #20080828: put the .375 stuff back --- otherwise some images were shown with "bottom line shown somewhat at top of image" glOrtho (0, self.m_w, 0, self.m_h, 1., -1.)
            glMatrixMode (GL_MODELVIEW)
            self.m_doViewportChange = False


        if self.m_gllist_Changed:
            try:
                self.defGlList
                
                glNewList( self.m_gllist+1, GL_COMPILE )
                try:
                    for gll in self.defGlList:
                        gll()
                except TypeError: #'list' object is not callable
                    self.defGlList()                    
                glEndList()
            except:
                import traceback as tb
                tb.print_exc(limit=None, file=None)
                self.error = "error with self.defGlList()"
                print("ERROR:", self.error)
            self.m_gllist_Changed = False

        #       if not self.m_gllist:
        #           return ## CHECK


        # print self.m_histScaleChanged, self.m_imgChanged,  self.m_w,    self.m_minHistScale, self.m_maxHistScale

        if len( self.m_loadImgsToGfxCard ):
            for imgidx in self.m_loadImgsToGfxCard:
                #print imgidx
                img = self.m_imgList[imgidx][2]
                mi,ma = self.m_imgList[imgidx][4:6]

                self._setHistScale(mi,ma,
                       dataTypeMaxValue_table[img.dtype.type])
                    
                self._loadImgIntoGfx(imgidx)
            self.m_loadImgsToGfxCard = []
          
        if self.m_zoomChanged:
            if self.m_x0 is None:
                self.center(refreshNow=False)

            sx,sy = self.m_scale,self.m_scale* self.m_aspectRatio
            offX,offY = sx*self.pic_nx/2., sy*self.pic_ny/2.
            glMatrixMode (GL_MODELVIEW)
            glLoadIdentity ()
            glTranslate(self.m_x0, self.m_y0,0)
            glTranslate(offX,offY,0)
            glRotate(self.m_rot, 0,0,1)
            glTranslate(-offX,-offY,0)
            glScaled(sx,sy,1.)
            
            self.m_zoomChanged = False


        if self.m_imgsGlListChanged:
            glNewList( self.m_gllist, GL_COMPILE )

            for imgListItem in self.m_imgList:
                if imgListItem[1]:
                    tx,ty,rot,mag = imgListItem[9:13]
                    cx,cy = imgListItem[2].shape[-1]/2., imgListItem[2].shape[-2]/2.
                    glPushMatrix()
                    glTranslated(cx,cy, 0)  # cx,cy  to make rot-center = center-image
                    glScaled(mag,mag, 1)
                    glRotated(rot, 0,0,1)#, cx,cy, 0)
                    glTranslated(tx-cx,ty-cy, 0)
                    glColor3fv(imgListItem[6:9])
                    glCallList( imgListItem[0] )
                    glPopMatrix()

            glEndList()
            self.m_imgsGlListChanged = False
        #              //CHECK
        #              // clear color and depth buffers
        #              //seb seb sbe seb seb 
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        
        #glCallList( self.m_gllist )
        #glCallList( self.m_gllist+1 )
        glCallLists( [self.m_gllist, self.m_gllist+1] )
                
        #for l,on in zip(self.m_moreGlLists,self.m_moreGlLists_enabled):
        #    if on:
        #        glCallList( l )
        if self.m_moreMaster_enabled:
            enabledGLlists = [i for (i,on) in zip(self.m_moreGlLists,
                                              self.m_moreGlLists_enabled) if on]
            if len(enabledGLlists):
                glCallLists( enabledGLlists )
        
        glFlush()
        self.SwapBuffers()

    def setImageL(self, imgArrL, refreshNow=True):
        for i in range(len(imgArrL)):
            self.setImage(i, imgArrL[i], 0)
        if refreshNow:
            self.Refresh(0)
        
    def setImage(self, i, imgArr, refreshNow=True):
        #do checks:
        # type mismatch actually OK -CHECK !?
        #         if self.m_imgList[i][2].dtype.type != imgArr.dtype.type:
        #             raise "type mismatch old vs. new"
        if self.m_imgList[i][2].shape != imgArr.shape:
            #raise "shape mismatch old vs. new"
            # in this case we 
            #  1. do "parts of" delImage
            #  2. add img to postion i
            imgListItem = self.m_imgList[i]
            glDeleteTextures( imgListItem[3] )
            glDeleteLists(imgListItem[0], 1)
            rgb = self.m_imgList[i][6:9]   # reuse RGB settings
            del self.m_imgList[i]
            #self.m_imgsGlListChanged=1
            # CHECK better values for   smin=0, smax=0, alpha=1., interp=0 !?
            self.addImg(imgArr, smin=0, smax=0, alpha=1., interp=0, imgidx=i, refreshNow=refreshNow)
            self.m_imgList[i][6:9] = rgb   # reuse RGB settings
        else:
            self.m_imgList[i][2] = imgArr
#           self.m_imgToDo = imgArr
            self.m_loadImgsToGfxCard.append( i )

            if refreshNow:
                self.Refresh(0)

    def delImage(self, i, refreshNow=1):
        imgListItem = self.m_imgList[i]
        glDeleteTextures( imgListItem[3] )
        glDeleteLists(imgListItem[0], 1)
        del self.m_imgList[i]
        self.m_imgsGlListChanged=1
        if refreshNow:
            self.Refresh(0)

    def goFFTmode(self):
        self.setOriginLeftBottom(7)
    def setOriginLeftBottom(self, olb):
        wx.Bell() # FIXME view2
#       self.m_originLeftBottom = olb
#       self.m_imgToDo = self.m_imgArr
#       self.InitTex()
        self.Refresh(0)

    #20080707 def doOnFrameChange(self):
    #20080707     pass

    #20080707 def doOnMouse(self, x,y, xyEffVal):
    #20080707     # print "xy: --> %7.1f %7.1f" % (x,y)
    #20080707     pass
    
    def OnReload(self, event=None):
        ## self.m_imgChanged = True
        self.Refresh(False)

    def OnChgOrig(self, event=None):
        o = self.m_originLeftBottom
        if o == 1:
            self.setOriginLeftBottom(0)
        elif o == 0:
            self.setOriginLeftBottom(7)
        elif o == 7:
            self.setOriginLeftBottom(8)
        elif o == 8:
            self.setOriginLeftBottom(1)
        else:
            print("FixMe: OnChgOrig")
        
    def OnColor(self, event=None):
        wx.Bell()
        
    
def view(arrayL, title=None, size=None, parent=None):
    try:
        if arrayL.ndim == 2:
            # arrayL is not list but img !
            arrayL = [arrayL]
    except:
        pass
        
    for i in range(len(arrayL)):
        array = arrayL[i]
        if len(array.shape) != 2:
            raise ValueError("arrays must be of dimension 2")

        if   array.dtype.type == N.int32:
            print("** viewer: converted Int32 to Int16")
            arrayL[i] = array.astype(N.int16)
        elif array.dtype.type == N.float64:
            print("** viewer: converted Float64 to Float32")
            arrayL[i] = array.astype(N.float32)
        elif array.dtype.type == N.complex128:
            print("** viewer: converted Complex128to Float32 - used abs()")
            arrayL[i] = N.abs(array).astype(N.float32)
        elif array.dtype.type == N.complex64:
            print("** viewer: complex - used abs()")
            arrayL[i] = N.abs(array)
        
    array = arrayL[0]
    # size = (400,400)
    if size is None:
        w,h = (array.shape[1],array.shape[0], )
        if h/2 == (w-1):  ## real_fft2d
            w = (w-1)*2
        if w>600 or h>600:
            size=400
    elif type(size) == int:
        w,h = size

#   if title is None or title =='':
#       if hasattr(array, 'FileName'):
#           title = array.FileName

#       else:
    title=''

    frame = wx.Frame(parent, -1, title)
    canvas = GLViewer(frame, size=(w,h))
    # b = wx.Button(frame, -1, "www")
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(canvas, 1, wx.EXPAND | wx.ALL, 5);
    frame.SetSizer(sizer);
    # sizer.SetSizeHints(frame) 
    #2.4auto  frame.SetAutoLayout(1)
    sizer.Fit(frame)

    wx.CallAfter(canvas.addImgL, arrayL)
    frame.Show(1)
    # frame.Layout() # hack for Linux-GTK
    return canvas
