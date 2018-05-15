"""Priithon's MOSAIC viewer"""
from __future__ import print_function
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import wx

#from wxPython.glcanvas import *
from wx import glcanvas as wxgl
#from wxPython import glcanvas
from OpenGL.GL import *
#08 from OpenGL import GLU

import numpy as N

Menu_Zoom2x      = wx.NewId()
Menu_ZoomCenter  = wx.NewId()
Menu_Zoom_5x     = wx.NewId()
Menu_ZoomReset   = wx.NewId()
Menu_ZoomAll   = wx.NewId()
Menu_Color       = wx.NewId()
Menu_zoomWithMiddle  = wx.NewId()
Menu_noGfx = wx.NewId()

bugXiGraphics = 0

def getTexSize(nx,ny):
    tex_nx = 2
    while tex_nx<nx:
        tex_nx*=2 # // texture must be of size 2^n
    tex_ny = 2
    while tex_ny<ny:
        tex_ny*=2

    return (tex_nx,tex_ny)

class GLViewer(wxgl.GLCanvas):
    def __init__(self, parent, size, keyTargetWin=None):
        wxgl.GLCanvas.__init__(self, parent, -1, size=size)

        self.error = None

        self.m_imgArrL    = []
        self.m_imgPosArr  = []
        self.m_imgSizeArr = []
        self.m_imgRotArr = []
        self.m_imgScaleMM = []
        self.m_nImgs = 0

        self.m_loadImgsToGfxCard = []
        self.m_imgL_changed = True ##  trigger initTex (also  for wmpty imgList !!!) #False

        self.m_doViewportChange = True
        self.m_zoomChanged = True # // trigger a first placing of image
        self.m_sizeChanged = True 
        self.m_originLeftBottom = True
        self.m_positionsChanged = True
        
        self.m_hideTheseImages = [] # 20051208

        #20040308  lb = self.m_imgPosArr[0]
        self.x00 = 0#20040308  - lb[0] +10
        self.y00 = 0#20040308  - lb[1] +10
        #007 print self.x00, self.y00

        self.m_x0=self.x00
        self.m_y0=self.y00
        self.m_scale=1
        self.m_aspectRatio = 1.
        self.m_rot = 0

        self.colMap = None
        self.m_minHistScale = 0
        self.m_maxHistScale = 100

        self.m_init   = False
        self.m_gllist = None
        self.m_texture_list = []
        self.m_moreGlLists = []
        self.m_moreGlLists_enabled = []
        self.m_moreMaster_enabled = True

        self.m_gllist_Changed = False # call defGlList() from OnPaint

        self.m_wheelFactor = 2
        self.m_zoomDragFactor = 1.05

        #//note:"ToolTip just annoys"  SetToolTip(wx.String::Format("cam %d", camId))
        #20041118 self.SetCursor(wx.CROSS_CURSOR)
        #20041202(just use defaultArrow)  self.SetCursor( wx.StockCursor(wx.CURSOR_BULLSEYE) )

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_ERASE_BACKGROUND(self, lambda evt: evt) # Do nothing, to avoid flashing
        #wx.EVT_SIZE(parent, self.OnSize)
        wx.EVT_SIZE(self, self.OnSize)
        #wx.EVT_MOVE(parent, self.OnMove) # CHECK

        #EVT_MIDDLE_DOWN(self, self.OnMiddleDown)
        wx.EVT_MOUSE_EVENTS(self, self.OnMouse)

        wx.EVT_MOUSEWHEEL(self, self.OnWheel)

        self.MakePopupMenu()

        ###          wx.Yield() # setImage has gl-calls - so lets make the window first...
        ###          self.setImage(imgArr)

        if keyTargetWin is not None:
            self.keyTargetWin = keyTargetWin
            #      m_pMenuPopup = new wx.Menu
            wx.EVT_KEY_DOWN(self, self.OnKey)
            #wx.EVT_KEY_UP(self, self.OnKeyUp)
            #wx.EVT_CHAR(self, self.OnKey)


    def MakePopupMenu(self):
        """Make a menu that can be popped up later"""
        self.m_menu = wx.Menu()

        # m_pMenuPopup->Append(Menu_Color, "&Change color")
        self.m_menu.Append(Menu_ZoomAll,"zoom &All")
        self.m_menu.Append(Menu_Zoom2x,    "&zoom 2x")
        self.m_menu.Append(Menu_Zoom_5x,   "z&oom .5x")
        self.m_menu.Append(Menu_ZoomReset, "zoom &reset")
        self.m_menu.Append(Menu_ZoomCenter,"zoom &Center here")
        self.m_menu.Append(Menu_Color, "Color")
        #self.m_menu.AppendCheckItem(Menu_zoomWithMiddle, "middle button zooms")
        self.m_menu.Append(Menu_noGfx, "hide all gfx", '',wx.ITEM_CHECK)
        self.m_menu.Append(Menu_zoomWithMiddle, "middle button zooms", '',wx.ITEM_CHECK)

        #20050729
        f = wx.GetTopLevelParent(self) # popupmenu lives in topLevelFrame because EVT_MENU_HIGHLIGHT
        wx.EVT_MENU(f, Menu_ZoomAll, lambda ev: self.zoomToAll())
        wx.EVT_MENU(f, Menu_Zoom2x,    self.OnMenu)
        wx.EVT_MENU(f, Menu_Zoom_5x,       self.OnMenu)
        wx.EVT_MENU(f, Menu_ZoomCenter, self.OnZoomCenter)
        wx.EVT_MENU(f, Menu_ZoomReset,  self.OnZoomReset)
        wx.EVT_MENU(f, Menu_Color,     self.OnColor)
        wx.EVT_MENU(self, Menu_noGfx,      self.OnNoGfx)
        wx.EVT_MENU(f, Menu_zoomWithMiddle,  self.OnZoomWithMiddle)
        
    def InitGL(self):
        (self.m_w, self.m_h) = self.GetClientSizeTuple()
        
        self.SetCurrent() # 20041026 - needed ?? 

        glClearColor(1.0, 1.0, 1.0, 0.0)
        #glClearColor(0.0, 0.0, 0.0, 0.0)
        #20050520 glEnable(GL_TEXTURE_2D)

        #CHECK glEnable(GL_DEPTH_TEST)

        #20060417 glEnable(GL_BLEND)
        #glBlendFunc (GL_ONE, GL_ONE)
        #glBlendFunc (GL_ONE, GL_ZERO) # default
#20040801-nowIn_updatePositions         glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
#20040801-nowIn_updatePositions         glColor4f(1.0, 1.0, 1.0, 1.0)

        
        self.m_init = True

    def InitTex(self):   

        self.SetCurrent() # 20041026 - needed ?? 

        if not self.m_gllist:
            self.m_gllist = glGenLists( 2 )
        if len(self.m_texture_list) :
            glDeleteTextures(self.m_texture_list)#glDeleteTextures  silently  ignores  zeros

        if self.m_nImgs > 0:
            self.m_texture_list = glGenTextures(  self.m_nImgs )
            #20050304  print "debug:seb4:   type(self.m_texture_list):", type(self.m_texture_list)
            #20050304  import traceback
            #20050304  traceback.print_stack()
            try:
                #20050304  a = self.m_texture_list[0] # for nImgs == 1:  make into sequence
                self.m_texture_list = list( self.m_texture_list )
            except TypeError:
                self.m_texture_list = [ self.m_texture_list ]
        else:
            self.m_texture_list=[]

        for i in range(self.m_nImgs):
            glBindTexture(GL_TEXTURE_2D, self.m_texture_list[i])
        
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR)
            # glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST)
            # glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST)
            #    // GL_CLAMP causes texture coordinates to be clamped to the range [0,1] and is
            #    // useful for preventing wrapping artifacts when mapping a single image onto
            #    // an object.
            #    //  //    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP)
            #    //  //    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP)

            img = self.m_imgArrL[i]

            pic_ny, pic_nx = img.shape
            tex_nx,tex_ny = getTexSize(pic_nx,pic_ny)

            imgType = img.dtype.type
            if bugXiGraphics:
                imgType = N.uint8
            elif img.dtype.type in (N.float64, N.int32, N.uint32):
                imgType = N.float32
            elif img.dtype.type in (N.complex64, N.complex128):
                imgType = N.float32
        
            if   img.dtype.type == N.uint8:
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
            else:
                self.error = "unsupported data mode"
                raise ValueError(self.error)

    def defGlList(self):
        pass
    def updateGlList(self, glCallsFunctions, refreshNow=1):
        self.defGlList = glCallsFunctions
        self.m_gllist_Changed = True
        if refreshNow:
            self.Refresh(False)

    '''
    #2007 01 05  use appendNewImg / insertNewImg
    
    def appendMosaic(self, imgL, posL, sizeL, scaleMinMax=(0,0),
             holdBackUpdate=0):
        self.insertMosaic(imgL, posL, sizeL, len(self.m_imgArrL),
              scaleMinMax, holdBackUpdate)
    def insertMosaic(self, imgL, posL, sizeL, listIdx,
                     scaleMinMax=(0,0), holdBackUpdate=0):
        """
        """
        if type(imgL) != type([]):
            imgL = [imgL]
        if type(posL) != type([]):
            posL = [posL]
        if type(sizeL) != type([]):
            sizeL = [sizeL]
        #if type(scaleMinMaxL) != type([]):
        #    scaleMinMaxL = [scaleMinMaxL]
        scaleMinMaxL = [scaleMinMax] * len(imgL)
        if len(imgL) != len(posL):
            raise ValueError, "unequal number of imgs and positions"
        
        for i in range(len(posL)):
            if type(posL[i]) != N.ndarray:
                posL[i] = N.array(posL[i])
        for i in range(len(sizeL)):
            if type(sizeL[i]) != N.ndarray:
                sizeL[i] = N.array(sizeL[i])
            if sizeL[i].shape in ( (), (1,) ): # 1D sizes
                sizeL[i] = N.resize(sizeL[i], 2)
        if 1 == len(sizeL) < len(imgL):
            sizeL *= len(imgL)
        

        self.m_imgArrL    [listIdx:listIdx]=  imgL
        self.m_imgPosArr  [listIdx:listIdx]=  posL
        self.m_imgSizeArr [listIdx:listIdx]=  sizeL
        self.m_imgRotArr  [listIdx:listIdx]=  [0.0] * len(posL)
        self.m_imgScaleMM [listIdx:listIdx]=  scaleMinMaxL

        self.m_nImgs = len( self.m_imgArrL )

        if not holdBackUpdate:
            self.m_imgL_changed = True
            
            self.Refresh(0)
    '''

    def clearAll(self):
        self.m_imgArrL    =  []
        self.m_imgPosArr  =  []
        self.m_imgSizeArr =  []
        self.m_imgRotArr  =  []
        self.m_imgScaleMM =  []

        self.m_nImgs = len( self.m_imgArrL )

        self.m_imgL_changed = True

        self.SetCurrent()
        if self.m_nImgs>0:
            glDeleteTextures(self.m_texture_list)#glDeleteTextures  silently  ignores  zeros

        self.m_texture_list = []
        self.m_nImg = 0
        self.Refresh(0)


    def clearIdx(self, idx, n=1, refresh=1):
        """
        remove images with index idx
           -1 means last
           clean also the n-1 following images idx+1,idx+2,...
        """
        if idx<0:
            idx += self.m_nImgs
        self.m_imgArrL    =  self.m_imgArrL   [:idx] + self.m_imgArrL   [idx+n:]
        self.m_imgPosArr  =  self.m_imgPosArr [:idx] + self.m_imgPosArr [idx+n:]
        self.m_imgSizeArr =  self.m_imgSizeArr[:idx] + self.m_imgSizeArr[idx+n:]
        self.m_imgRotArr  =  self.m_imgRotArr [:idx] + self.m_imgRotArr [idx+n:]
        self.m_imgScaleMM =  self.m_imgScaleMM[:idx] + self.m_imgScaleMM[idx+n:]

        self.SetCurrent()
        glDeleteTextures(self.m_texture_list[idx])  #glDeleteTextures   silently  ignores  zeros
        self.m_texture_list = self.m_texture_list[:idx] + self.m_texture_list[idx+n:]
        self.m_nImgs = len( self.m_imgArrL )
        self.m_imgL_changed = True
        if refresh:
            self.Refresh(0)


    def readGLviewport(self, copy=1):
        """
        returns array with r,g,b values from "what-you-see"
            shape(3, height, width)
            type=UInt8
            if copy == 0 returns non-contiguous array!!!

        """
        self.SetCurrent()
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

    def save(self, baseFn=None):
        """save Mosaic size/pos/scale info in baseFn.txt
           save all images into baseFn_xx.mrc
        """
        from Priithon.all import Mrc, U

        if baseFn is None:
            from .usefulX import FN
            baseFn = FN(1)
            if not baseFn:
                return
        a = N.concatenate((self.m_imgPosArr,
                          self.m_imgSizeArr,
                          N.array(self.m_imgRotArr,)[:,N.newaxis],
                          self.m_imgScaleMM), 1)

        U.writeArray(a, baseFn + '.txt')
        n = len(self.m_imgSizeArr)
        for i in range( n ):
            # Mrc.save(self.m_imgArrL[i], "%s_%02d.mrc" % (baseFn, i))
            #20070126 m = Mrc.Mrc("%s_%02d.mrc" % (baseFn, i), "w+", self.m_imgArrL[i] )
            #20070126 m.calcMMM()
            #20070126 m.hdr('d')[:] =    tuple(self.m_imgSizeArr[i] / N.array((self.m_imgArrL[i].shape))[::1]) + (1,)
            #20070126 m.hdr('zxy0')[:] = (0,) + tuple(self.m_imgPosArr[i]) 
            #20070126 m.hdr('mmm1')[:] = tuple(self.m_imgScaleMM[i]) + (1,)
            #20070126 m.flush()
            #20070126 m.close()
            d    = tuple(self.m_imgSizeArr[i] / N.array((self.m_imgArrL[i].shape), dtype=N.float32)[::1]) + (1,)
            zxy0 = (0,) + tuple(self.m_imgPosArr[i]) 
            Mrc.save(self.m_imgArrL[i],
                     "%s_%02d.mrc" % (baseFn, i),
                     hdrEval='''hdr.d = d; hdr.zxy0 = zxy0'''
                     )

    def load(self, baseFn=None, n=None, n0=0, sparse=1):
        """load Mosaic size/pos/scale from in baseFn.txt
           load all images into baseFn_xx.mrc

           load only the first n images - n=None means all
           skip the first n0 of these
           if sparse>1 take only every 'sparse' pixel along x & y

           if baseFn end on '.txt' - that suffix gets ignored
        """
        from Priithon.all import Mrc, U

        if baseFn is None:
            from .usefulX import FN
            baseFn = FN()
            if not baseFn:
                return
        if baseFn[-4:] == '.txt':
            baseFn = baseFn[:-4]

        a = U.readArray(baseFn + '.txt')
        if len(a.shape) == 1:
            a.shape = (1,) + a.shape
        nn = len(a)
        if n is not None and n<nn:
            nn=n
        n=nn
        apos = a[:, :2]
        asiz = a[:, 2:4]
        arot = a[:, 4]
        ascl = a[:, 5:7]
        
        #n = len( apos )
        for i in range(n0, n ):
            #20070126 aa = Mrc.bindFile("%s_%02d.mrc" % (baseFn, i)).copy()[0]
            aa = Mrc.load("%s_%02d.mrc" % (baseFn, i))[0]
            #            self.appendMosaic( aa,
            self.appendNewImg( aa[::sparse,::sparse],
                               apos[i], asiz[i], ascl[i],
                               holdBackUpdate=(i+1<n), rot=arot[i] )
        

    def updateOneImg(self, i, autoScale=0, updatePositions=False):
        self.m_positionsChanged = updatePositions
        self.m_loadImgsToGfxCard += [i]
        self.Refresh(0)
        

    def _updatePositions(self):
        glNewList( self.m_gllist, GL_COMPILE )
        glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        glColor4f(1.0, 1.0, 1.0, 1.0)

        glEnable(GL_TEXTURE_2D)#20050520
        for i in range(self.m_nImgs):   
            if i in self.m_hideTheseImages:
                continue
            glBindTexture(GL_TEXTURE_2D, self.m_texture_list[i])
            ##################################glColor3f(1.0, 0.0, 0.0);
            #  // Use a named texture.
            glBegin(GL_QUADS)
            
            ##BUG - HANGS glBindTexture(GL_TEXTURE_2D, self.m_texture_list)
            #          #  //    glNormal3f( 0.0F, 0.0F, 1.0F)
            
            #          #  //seb TODO  correct for pixel center vs pixel edge -> add .5 "somewhere"

            (x,y) = self.m_imgPosArr[i]
            (w,h) = self.m_imgSizeArr[i]

            alpha = N.pi/180 *  self.m_imgRotArr[i] #degree
            c = N.cos(alpha)
            s = N.sin(alpha)
            cw = c*w
            sw = s*w
            ch = c*h
            sh = s*h

            img = self.m_imgArrL[i]
            pic_ny, pic_nx = img.shape
            tex_nx,tex_ny = getTexSize(pic_nx,pic_ny)
            picTexRatio_x = float(pic_nx) / tex_nx
            picTexRatio_y = float(pic_ny) / tex_ny

            if self.m_originLeftBottom:
                ###//(0,0) at left top
                
                glTexCoord2f( 0, 0)
                glVertex2f  ( x,    y)
                
                glTexCoord2f( picTexRatio_x, 0)
                glVertex2f  ( x+ cw, y +sw)
                
                glTexCoord2f( picTexRatio_x, picTexRatio_y)
                glVertex2f  ( x+ cw-sh, y+ sw+ch)
                
                glTexCoord2f( 0, picTexRatio_y)
                glVertex2f  ( x -sh,    y+ ch)
            else:
                raise
            #               ###//(0,0) at left bottom
            #               glTexCoord2f( 0,             picTexRatio_y)
            #               glVertex2d  ( x+ pic_nx+  0,              0)
            
            #               glTexCoord2f( picTexRatio_x, picTexRatio_y)
            #               glVertex2d  ( i*pic_nx+  pic_nx,        0)
            
            #               glTexCoord2f( picTexRatio_x, 0)
            #               glVertex2d  ( i*pic_nx+  pic_nx,        pic_ny)
            
            #               glTexCoord2f( 0,             0)
            #               glVertex2d  ( i*pic_nx+  0,             pic_ny)
                
            #print "InitGL 3"
            glEnd()
            #print "InitGL 4"
        glDisable(GL_TEXTURE_2D) #20050520
        glEndList()


    def appendNewImg(self, img, pos, size, scaleMinMax=(0,0), holdBackUpdate=0, rot=0):
        """
        calls insertNewImg  with idx=-1
        """
        self.insertNewImg(img, pos, size, scaleMinMax, -1, holdBackUpdate, rot)
    '''
    def appendNewImg(self, img, pos, size, scaleMinMax=(0,0), holdBackUpdate=0, rot=0):
        pos = N.asarray(pos)
        size = N.asarray(size)
        if size.shape in ( (), (1,) ): # 1D sizes
            size = N.resize(size, 2)

        self.m_imgArrL    .append( img )
        self.m_imgPosArr  .append( pos )
        self.m_imgSizeArr .append( size )
        self.m_imgRotArr  .append( rot )
        self.m_imgScaleMM .append( scaleMinMax )

        self.m_nImgs += 1 # len( self.m_imgArrL )

        #       if not holdBackUpdate:
        #           self.m_imgL_changed = True
        #           self.Refresh(0)

        self.SetCurrent()

        t = glGenTextures(  1 )
        #print "debug:seb:   type(self.m_texture_list):", type(self.m_texture_list)
        texListIdx =len( self.m_texture_list )
        self.m_texture_list .append( t ) #  += [t]

        glBindTexture(GL_TEXTURE_2D, t)
        
        #        //glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST)
        #      //glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST)
        #    // GL_CLAMP causes texture coordinates to be clamped to the range [0,1] and is
        #    // useful for preventing wrapping artifacts when mapping a single image onto
        #    // an object.
        #    //  //    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP)
        #    //  //    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP)

        ######                img = self.m_imgArrL[i]

        pic_ny, pic_nx = img.shape
        tex_nx,tex_ny = getTexSize(pic_nx,pic_ny)

        if   img.dtype.type == N.uint8:
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
        else:
            self.error = "unsupported data mode"
            raise ValueError, self.error

        if not holdBackUpdate:
            self.m_loadImgsToGfxCard += [texListIdx]
            self.m_positionsChanged = True
            #20050304  print "debug:seb7", self.m_loadImgsToGfxCard,  self.m_imgArrL[texListIdx].max()
            self.Refresh(0)
'''



    def insertNewImg(self, img, pos, size, scaleMinMax=(0,0), idx=-1, holdBackUpdate=0, rot=0):
        """idx defaults to -1 == "append"
        """
        
        if idx<0:
            idx += self.m_nImgs + 1
            
        pos = N.asarray(pos)
        size = N.asarray(size)
        if size.shape in ( (), (1,) ): # 1D sizes
            size = N.resize(size, 2)

        self.m_imgArrL    [idx:idx] = [ img ]
        self.m_imgPosArr  [idx:idx] = [ pos ]
        self.m_imgSizeArr [idx:idx] = [ size ]
        self.m_imgRotArr  [idx:idx] = [ rot ]
        self.m_imgScaleMM [idx:idx] = [ scaleMinMax ]

        self.m_nImgs += 1 # len( self.m_imgArrL )

        #       if not holdBackUpdate:
        #           self.m_imgL_changed = True
        #           self.Refresh(0)

        self.SetCurrent()

        t = glGenTextures(  1 )
        #print "debug:seb:   type(self.m_texture_list):", type(self.m_texture_list)
        ##insert##### texListIdx =len( self.m_texture_list )
        ##insert##### self.m_texture_list .append( t ) #  += [t]
        self.m_texture_list [idx:idx] = [ t ] #  += [t]

        glBindTexture(GL_TEXTURE_2D, t)
        
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR)
        #glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        #glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST)
        #    // GL_CLAMP causes texture coordinates to be clamped to the range [0,1] and is
        #    // useful for preventing wrapping artifacts when mapping a single image onto
        #    // an object.
        #    //  //    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP)
        #    //  //    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP)

        ######                img = self.m_imgArrL[i]

        pic_ny, pic_nx = img.shape
        tex_nx,tex_ny = getTexSize(pic_nx,pic_ny)

        if   img.dtype.type == N.uint8:
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
        else:
            self.error = "unsupported data mode"
            raise ValueError(self.error)

        if not holdBackUpdate:
            self.m_loadImgsToGfxCard += [idx]
            self.m_positionsChanged = True
            #20050304  print "debug:seb7", self.m_loadImgsToGfxCard,  self.m_imgArrL[texListIdx].max()
            self.Refresh(0)


    def OnNoGfx(self, evt):
        #self.m_menu.GetMenuItems()[-1].Check( not event.IsChecked() )     ### HACK check LINUX GTK WIN MSW

        self.m_moreMaster_enabled = not evt.IsChecked()
        self.Refresh(0)     

    def newGLListNow(self) : # , i):
        """
        call this immediately before you call a bunch of gl-calls
           issue newGLListDone() when done
           OR newGLListAbort() when there is problem and
               the glist should get cleared 
        """
        self.SetCurrent()
        self.curGLLIST = glGenLists( 1 )
        glNewList( self.curGLLIST, GL_COMPILE )

    def newGLListAbort(self):
        glEndList()
        glDeleteLists(self.curGLLIST, 1)

    def newGLListDone(self, enable=1, refreshNow=1):
        glEndList()
        i = len(self.m_moreGlLists)
        self.m_moreGlLists.append( self.curGLLIST )
        self.m_moreGlLists_enabled.append( enable )
        if refreshNow:
            self.Refresh(0)
        return i

    def newGLListRemove(self, idx):
        glDeleteLists(self.m_moreGlLists[idx], 1)
        del self.m_moreGlLists[idx]
        del self.m_moreGlLists_enabled[idx]
        self.Refresh(0)

    def newGLListEnable(self, idx, on=1):
        self.m_moreGlLists_enabled[idx] = on
        self.Refresh(0)



    def histScale(self, hmin=None, hmax=None, startIdx=0):
        """
        use hmin, hmax to do autoscale each tile
        None mean img.min(), max() respectively
        """
        #   if lastNimg == None:
        #       i = X.MOnLMXmaps
        #   elif lastNimg < 0:
        #       i = X.MOv.m_nImgs + lastNimg
        #   else:
        #       i = lastNimg        
        #   print "scaling images Idx:", i
        for i in range(startIdx, len(self.m_imgScaleMM) ):
            hmini, hmaxi,  = hmin, hmax
            if hmax is None:
                hmaxi =  self.m_imgArrL[i].max()
            if hmin is None:
                hmini =  self.m_imgArrL[i].min()

            self.m_imgScaleMM[i] = (hmini, hmaxi)

        self.m_imgL_changed = 1
        self.Refresh()
    


    '''
    def zoomToAll(self):
        if self.m_nImgs < 1:
            return
        # FIXME not misses left edge 
        posA=N.array(self.m_imgPosArr)
        sizA=N.array(self.m_imgSizeArr)
        a=N.array([N.minimum.reduce(posA),
                    #N.minimum.reduce(posA-sizA),
                    #N.minimum.reduce(posA+sizA),
                    #N.maximum.reduce(posA-sizA),
                    N.maximum.reduce(posA+sizA),
                    ])

        from Priithon.all import U

        # the rot part is totally broken !!!!
        r = U.deg2rad(self.m_rot)
        a = N.matrixmultiply(a, [(N.cos(r), -N.sin(r)),
                                  (N.sin(r), N.cos(r))])

        a.sort(0)

#         a[-1]= N.matrixmultiply([(N.cos(r), -N.sin(r)),
#                                   (N.sin(r), N.cos(r))], a[-1])
        self.zoomToRect(x0=a[0][1], y0=a[0][1],
                        x1=a[-1][1],y1=a[-1][0])
    '''
    def zoomToAll(self):
        if self.m_nImgs < 1:
            return

        posA=N.array(self.m_imgPosArr)
        sizA=N.array(self.m_imgSizeArr)
        a=N.array([N.minimum.reduce(posA),
                   N.maximum.reduce(posA+sizA),
                   ])
        from Priithon.all import U

        MC = N.array([0.5, 0.5]) # mosaic viewer's center (0.5, 0.5)
        a -= MC
        hypot = N.array((N.hypot(a[0][0], a[0][1]),
                         N.hypot(a[1][0], a[1][1])))
        theta = N.array((N.arctan2(a[0][1], a[0][0]),
                         N.arctan2(a[1][1], a[1][0]))) # radians
        phi = theta + U.deg2rad(self.m_rot)
        mimXY = N.array((hypot[0]*N.cos(phi[0]), hypot[0]*N.sin(phi[0])))
        maxXY = N.array((hypot[1]*N.cos(phi[1]), hypot[1]*N.sin(phi[1])))
        a = N.array((mimXY, maxXY))
        a.sort(0)
        if self.m_aspectRatio == -1:
            a = N.array(([a[0][0],-a[1][1]],[a[1][0],-a[0][1]]))

        self.zoomToRect(x0=a[0][0], y0=a[0][1],
                        x1=a[-1][0],y1=a[-1][1])

    def zoomToRect(self, x0,y0,x1,y1):
        dx = x1-x0
        dy = y1-y0
        sx,sy = self.GetClientSizeTuple()

        scaleX = abs(sx / float(dx))
        scaleY = abs(sy / float(dy))

        scale = min(scaleX, scaleY)

        self.zoomTo(x0,y0, scale)
        
    def zoomTo(self, x,y, scale):
        self.m_x0, self.m_y0 = -x*scale,-y*scale
        self.m_scale = scale
        self.m_zoomChanged = True
        self.Refresh(0)
        
    def setAspectRatio(self, y_over_x=-1, refreshNow=1):
        """
        strech images in y direction
        use negative value to mirror
        """
        
        self.m_aspectRatio=y_over_x
        
        self.m_zoomChanged=1
        if refreshNow:
            self.Refresh()

    def setRotation(self, angle=90, refreshNow=1):
        """rotate everything by angle in degrees
        """
        
        self.m_rot = angle
        
        self.m_zoomChanged=1
        if refreshNow:
            self.Refresh()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)

        if self.error:
            return
        #//seb check PrepareDC(dc)
        if not self.GetContext():
            print("OnPaint GetContext() error")
            return
        
        self.SetCurrent()
  
        if not self.m_init:
            self.InitGL()

        if self.m_doViewportChange:
            glViewport(0, 0, self.m_w, self.m_h)
            glMatrixMode (GL_PROJECTION)
            glLoadIdentity ()
            glOrtho (-.375, self.m_w-.375, -.375, self.m_h-.375, 1., -1.)
            glMatrixMode (GL_MODELVIEW)
            self.m_doViewportChange = False

        if self.m_imgL_changed:
            self.InitTex()
            self.m_positionsChanged = True
            self.m_loadImgsToGfxCard += list(range(self.m_nImgs))
            self.m_imgL_changed = False


        if self.m_positionsChanged:
            self._updatePositions()
            self.m_positionsChanged = False


            
        #20040309 if not self.m_gllist:
        #20040309     return ## CHECK
        if self.m_gllist_Changed:
            try:
                self.defGlList
                
                glNewList( self.m_gllist+1, GL_COMPILE )
                self.defGlList()
                glEndList()
            except:
                import traceback as tb
                tb.print_exc(limit=None, file=None)
                self.error = "error with self.defGlList()"
                print("ERROR:", self.error)
            self.m_gllist_Changed = False

        if len( self.m_loadImgsToGfxCard ):
            for i in self.m_loadImgsToGfxCard:
                glBindTexture(GL_TEXTURE_2D, self.m_texture_list[i])
                #20050304  print "debug98", i, self.m_texture_list[i]

                img = self.m_imgArrL[i]
                pic_ny, pic_nx = img.shape

                mi,ma = self.m_imgScaleMM[i]
                if(mi!=ma): 
                    if bugXiGraphics:
                        self.bugXiGraphicsmi = mi
                        self.bugXiGraphicsma = ma
                        den = (self.bugXiGraphicsma - self.bugXiGraphicsmi)
                        if den == 0:
                            den = 1
                        self.bugXiGraphicsfa = 255./den

                        fBias = 0
                        f = 1

                        data = ((img-self.bugXiGraphicsmi) *self.bugXiGraphicsfa)
                        data = N.clip(data, 0, 255)
                        data = data.astype(N.uint8)
                        imgString = data.tostring()
                        imgType = N.uint8

                    else:
                        if img.dtype.type in (N.float64, N.int32, N.uint32):
                            data = img.astype(N.float32)
                            imgString = data.tostring()
                            imgType = N.float32
                        else:
                            imgString = img.tostring()
                            imgType = img.dtype.type
                            
                        # maxUShort: value that represents "maximum color" - i.e. white
                        if   img.dtype.type == N.uint16:
                            maxUShort = (1<<16) -1
                        elif img.dtype.type == N.int16:
                            maxUShort = (1<<15) -1
                        elif img.dtype.type == N.uint8:
                            maxUShort = (1<<8) -1
                        else:
                            maxUShort = 1


                        mmrange =  float(ma)-float(mi)
                        fBias =  -float(mi) / mmrange
                        f  =  maxUShort / mmrange


                    glPixelTransferf(GL_RED_SCALE,   f) #; // TODO HACK
                    glPixelTransferf(GL_GREEN_SCALE, f)
                    glPixelTransferf(GL_BLUE_SCALE,  f)
                    
                    glPixelTransferf(GL_RED_BIAS,   fBias)
                    glPixelTransferf(GL_GREEN_BIAS, fBias)
                    glPixelTransferf(GL_BLUE_BIAS,  fBias)
                    
                    if self.colMap != None:
                        glPixelTransferi(GL_MAP_COLOR, True);
                        glPixelMapfv(GL_PIXEL_MAP_R_TO_R, self.colMap[0] )
                        glPixelMapfv(GL_PIXEL_MAP_G_TO_G, self.colMap[1] )
                        glPixelMapfv(GL_PIXEL_MAP_B_TO_B, self.colMap[2] )
                    else:
                        glPixelTransferi(GL_MAP_COLOR, False)
                else:
                    print("mmviewer-debug12: min==max: self.m_imgScaleMM[i]", self.m_imgScaleMM[i])
                    
                if bugXiGraphics: #20070126  or (bugOSX1036 and img.dtype.type == N.float32): #20060221
                    itSize = 1
                    #20070625-why need for single byte?? glPixelStorei(GL_UNPACK_SWAP_BYTES, img.dtype.byteorder != '=')
                elif img.dtype.type in (N.float64,
                                        N.int32, N.uint32,
                                        N.complex64, N.complex128):
                    itSize = 4
                    glPixelStorei(GL_UNPACK_SWAP_BYTES, False) # create native float32 copy - see below
                else:
                    itSize = img.itemsize
                    glPixelStorei(GL_UNPACK_SWAP_BYTES, not img.dtype.isnative)

                glPixelStorei(GL_UNPACK_ALIGNMENT, itSize)

                #20050304  print "debug99", type(img), img.shape
                if imgType == N.uint8:
                    glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny, 
                                    GL_LUMINANCE,GL_UNSIGNED_BYTE, imgString)
                elif imgType == N.int16:
                    glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny, 
                                    GL_LUMINANCE,GL_SHORT, imgString)
                elif imgType == N.float32:
                    glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny, 
                                    GL_LUMINANCE,GL_FLOAT, imgString)
                elif imgType == N.uint16:
                    glTexSubImage2D(GL_TEXTURE_2D,0,  0,0,  pic_nx,pic_ny, 
                                    GL_LUMINANCE,GL_UNSIGNED_SHORT, imgString)
                else:
                    self.error = "unsupported data mode"
                    raise ValueError(self.error)

            self.m_loadImgsToGfxCard = []

          
        if self.m_zoomChanged:

            glMatrixMode (GL_MODELVIEW)
            glLoadIdentity ()
            glTranslated(self.m_x0, self.m_y0,0)
            glScaled(self.m_scale,self.m_scale* self.m_aspectRatio,1.)
            glRotate(self.m_rot,0,0,1)
            
            self.m_zoomChanged = False

        #              //CHECK
        #              // clear color and depth buffers
        #              //seb seb sbe seb seb 
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        
        glCallList( self.m_gllist )
        glCallList( self.m_gllist+1 )

        if self.m_moreMaster_enabled:
            for l,on in zip(self.m_moreGlLists,self.m_moreGlLists_enabled):
                if on:
                    glCallList( l )
        
        
        glFlush()
        self.SwapBuffers()

#20040308      def setImage(self, imgArr):
#20040308          self.m_imgToDo = imgArr
#20040308          self.Refresh(0)

    def reInit(self):
        self.m_imgL_changed = True
        
        self.Refresh(0)


    def doOnFrameChange(self):
        pass
#20051107 this was because of incosistant naming in OMX-mosaic
#     def doOnLeftDClick(self, event):
#         x,y = event.GetX(),  self.m_h-event.GetY()
#         x0,y0, s = self.m_x0, self.m_y0,self.m_scale

#         #08 xx,yy = event.m_x, self.m_h-event.m_y
#         #08 wx,wy,wz = GLU.gluUnProject( xx,yy,winz=0)
#         #08 print xx,yy  , ((x-x0)/s, (y-y0)/s)
#         #08 print wx,wy,wz   # same with onSize now connected to self (not parent anymore)
        
#         self.doDClick((x-x0)/s, (y-y0)/s)
#         #08 self.doDClick(wx,wy)

#     def doDClick(self, x,y):
#         print "xy: --> %7.1f %7.1f" % (x,y)
#         pass
    
    def doOnMouse(self, x,y, xyEffVal):  # CHECK thrid arg no sense in mmviewer
        # print "xy: --> %7.1f %7.1f" % (x,y)
        pass

    def OnMove(self, event):
        self.doOnFrameChange()
        
    def OnSize(self, event):
        self.m_doViewportChange = True
        
        #self.m_w, self.m_h = self.GetSizeTuple() # self.GetClientSizeTuple()
        self.m_w, self.m_h = self.GetClientSizeTuple()
        #print "***1 ", self.GetSizeTuple()
        #print "***2 ", self.GetClientSizeTuple()
        if self.m_w <=0 or self.m_h <=0:
            print("view.OnSize self.m_w <=0 or self.m_h <=0", self.m_w, self.m_h)
            return

        self.doOnFrameChange()
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
            #self.doCenter()
            w2 = self.m_w/2.
            h2 = self.m_h/2.
            self.m_x0 = w2 - (w2-self.m_x0)*fac
            self.m_y0 = h2 - (h2-self.m_y0)*fac
            self.m_zoomChanged = True
            self.Refresh(0)
        #else:
        #    slider.SetValue()
        
    def decideZoom_not_drag(self, ev):
        """
        return true if middle mouse does zoom
        return false if middle mouse does drag
        """
        return ev.ShiftDown() or ev.ControlDown()

    def doLDClick(self, x,y):
        # print "doDLClick xy: --> %7.1f %7.1f" % (x,y)
        pass
    def doLDown(self, x,y):
        # print "doLDown xy: --> %7.1f %7.1f" % (x,y)
        pass

        

    def OnMouse(self, ev):
        if ev.Leaving():
            ## leaving trigger  event - bug !!
            return
        self._onMouseEvt = ev  # be careful - only use INSIDE a handler function that gets call from here
        x0,y0, s,a = self.m_x0, self.m_y0,self.m_scale,self.m_aspectRatio
        x,y = ev.m_x, self.m_h-ev.m_y
        xEff,yEff = (x-x0)/float(s) ,  (y-y0)/float(s*a) # float !

        midButt = ev.MiddleDown() or (ev.LeftDown() and ev.AltDown())
        midIsButt = ev.MiddleIsDown() or (ev.LeftIsDown() and ev.AltDown())
        rightButt = ev.RightDown() or (ev.LeftDown() and ev.ControlDown())
 
        if midButt:
            #########wx,wy,wz = GLU.gluUnProject( x,y,winz=0)
            self.mouse_last_x, self.mouse_last_y = x,y
        elif midIsButt: #ev.Dragging()
            #########wx,wy,wz = GLU.gluUnProject( x,y,winz=0)
            if self.decideZoom_not_drag(ev):
                #dx = x-self.mouse_last_x
                dy = y-self.mouse_last_y

                fac = self.m_zoomDragFactor ** (dy)
                self.m_scale *= fac
                w2 = self.m_w/2.
                h2 = self.m_h/2.
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
            self.mousePos_remembered_x, self.mousePos_remembered_y = ev.GetPositionTuple()
            pt = ev.GetPosition()
            #20050729   self.PopupMenu(self.m_menu, pt)
            f = wx.GetTopLevelParent(self)
            pt = f.ScreenToClient(self.ClientToScreen(pt))
            f.PopupMenu(self.m_menu, pt)# popupmenu lives in topLevelFrame because EVT_MENU_HIGHLIGHT
            
        elif ev.LeftDClick():
            #20051107 what was this for !?:self.doOnLeftDClick(ev)
        #elif ev.LeftDClick():
            self.doLDClick(xEff,yEff)

        elif ev.LeftDown():
            self.doLDown(xEff,yEff)

        self.doOnMouse(xEff, yEff, 0) # xyEffVal) # CHECK third arg no sense in mmviewer

    def OnZoomWithMiddle(self, event):

        ##20050922 self.m_menu.GetMenuItems()[-1].Check( not event.IsChecked() )     ### HACK check LINUX GTK WIN MSW

        if event.IsChecked():
            def decideZoom_not_drag(ev):
                return ev.ShiftDown() or ev.ControlDown()
        else:
            def decideZoom_not_drag(ev):
                return not (ev.ShiftDown() or ev.ControlDown())

        self.decideZoom_not_drag = decideZoom_not_drag
    
    def OnColor(self, event):
        if self.colMap != None:
            self.cmnone()
        else:
            self.cmcol()

    def OnMenu(self, event):
        id = event.GetId()
        
        if id == Menu_Zoom2x:
            fac = 2.
            self.m_scale *= fac
            w2 = self.m_w/2.
            h2 = self.m_h/2.
            self.m_x0 = w2 - (w2-self.m_x0)*fac
            self.m_y0 = h2 - (h2-self.m_y0)*fac
            self.m_zoomChanged = True
        elif id == Menu_Zoom_5x:
            fac = .5
            self.m_scale *= fac
            w2 = self.m_w/2.
            h2 = self.m_h/2.
            self.m_x0 = w2 - (w2-self.m_x0)*fac
            self.m_y0 = h2 - (h2-self.m_y0)*fac
            self.m_zoomChanged = True

        self.Refresh(0)

    def OnZoomReset(self, event=None):
        self.m_x0=self.x00
        self.m_y0=self.y00
        self.m_scale=1
        self.m_aspectRatio = 1.
        self.m_rot = 0
        self.m_zoomChanged = True
        self.Refresh(0)

    def OnZoomCenter(self, event=None):
        x = self.mousePos_remembered_x
        y = self.mousePos_remembered_y

        w2 = self.m_w/2.
        h2 = self.m_h/2.
        self.m_x0 += (w2-x)*self.m_scale
        self.m_y0 += (h2-y)*self.m_scale
        self.m_zoomChanged = True
        self.Refresh(0)

    def OnKey(self, event): 
        """Key down event handler. 
        """
        #key = event.KeyCode() 
        #controlDown = event.ControlDown() 
        #altDown = event.AltDown()
        #shiftDown = event.ShiftDown() 
        #print key, shiftDown, controlDown, altDown,event
        wx.PostEvent(self.keyTargetWin, event)
        
        event.Skip() 


    ###############3###############3###############3###############3###############3
    ###############3###############3###############3###############3###############3

    colnames= {
        "white" : (255, 255, 255),
        "red" : (255, 0, 0),
        "yellow" : (255, 255, 128),
        "green" : (0, 255, 0),
        "cyan" : (0, 255, 255),
        "blue" : (0, 0, 255),
        "magenta" : (255, 0, 255),
        "black" : (0, 0, 0),
        "grey" : (128, 128, 128),
        "gray" : (128, 128, 128),
        "orange" : (255, 128, 0),
        "violet" : (128, 0, 255),
        "darkred" : (128, 0, 0),
        "darkgreen" : (0, 128, 0),
        "darkblue" : (0, 0, 128),
        }
    
    grey = ["black", "white"]
    spectrum = ["darkred", "red", "orange", "yellow", "green", "blue",
                "darkblue", "violet"]
    blackbody = ["black", "darkred", "orange", "yellow", "white"]
    redgreen = ["red", "darkred", "black", "darkgreen", "green"]
    greenred = ["green", "darkgreen", "black", "darkred", "red"]
    twocolorarray = ["green", "yellow", "red"]

    spectrum2 = ["darkred", "red", "orange", "255:255:0", "green", "cyan", "blue",
                 "darkblue", "violet"]
    spectrum3 = ["darkred", "red", "orange", "255:255:0", "green", "cyan", "blue",
                 "darkblue", "violet", "white"] # , "200:200:200"
    spectrum4 = ["black", "darkred", "red", "orange", "255:255:0", "green", "cyan", "blue",
                 "darkblue", "violet", "white"] # , "200:200:200"
    

        
        
    def cms(self,colseq=spectrum, reverse=0):

        import re
        col_regex = re.compile(r'(\d+):(\d+):(\d+)')
        def s2c(s):
            mat = col_regex.match(s)
            if mat:
                return N.array( list(map(int, mat.groups())), dtype=N.float32 ) /255.
            else:
                return N.array( self.colnames[s], dtype=N.float32 ) /255.

        if reverse:
            colseq = colseq[:]
            colseq.reverse()
        self.cm_size = 256 ###### non omx
        self.colMap = N.zeros(shape=(3, self.cm_size), dtype=N.float32)
        n = len(colseq)
        #  print n
        c = 0
        acc = s2c( colseq[0] )
        # print acc
        for i in range( 0, n-1 ):
            rgb0 = s2c( colseq[i] )
            rgb1 = s2c( colseq[i+1] )
            delta = rgb1 - rgb0

            # print "===> ", i, colseq[i], colseq[i+1], "  ", rgb0, rgb1, "   d: ", delta

            sub_n_f = self.cm_size / float(n-1.0)
            sub_n   = self.cm_size / float(n-1)
            # print "*****    ", c, "  ", i*sub_n_f, " ", i*sub_n,  " ++++ ", int( i*sub_n_f+.5 )

            if int( i*sub_n_f+.5 ) > c:
                sub_n += 1             # this correct rounding - to get
                #              correct total number of entries
            delta_step = delta / float(sub_n)
            for i in range(sub_n):
                # print c, acc
                self.colMap[:, c] = acc
                
                c+=1
                acc += delta_step
        if(c < self.cm_size):
            #  print c, acc
            self.colMap[:, c] = acc
            #      else:
            #          print "** debug ** c == self.cm_size ..."
    
        ##########3viewerRedraw(cam)
    
    def cmgrey(self, reverse=0):
        self.cms(self.grey, reverse)
        self.m_loadImgsToGfxCard += list(range(self.m_nImgs))
        self.Refresh(0)
    def cmcol(self, reverse=0):
        self.cms(self.spectrum3, reverse)
        self.m_loadImgsToGfxCard += list(range(self.m_nImgs))
        self.Refresh(0)
    def cmnone(self):
        self.colMap = None
        self.m_loadImgsToGfxCard += list(range(self.m_nImgs))
        self.Refresh(0)
    def cmgray(self, gamma=1):
        """set col map to gray"""
        if gamma == 1:
            n = self.cm_size = 512
            self.colMap = N.empty(shape = (3,n), dtype = N.float32)
            self.colMap[:] = N.arange(0,1,1./n)
        else:
            n = self.cm_size = 512
            gamma = float(gamma)
            wmax = 0 + (1 - 0) * ((n - 0) / (1. - 0)) ** gamma
            self.colMap = N.empty(shape = (3,n), dtype = N.float32)
            self.colMap[:] = \
                  (0 + (1 - 0) * ((N.arange(n) - 0) / (1. - 0)) **gamma) / wmax
        self.m_loadImgsToGfxCard += list(range(self.m_nImgs))
        self.Refresh(0)
    
def mview(arrayL=None, imgPosArr=None, imgSizeArr=None,
          size=(600,600), title="2d mosaic viewer", keyTargetWin=None, parent=None,
          zoomToAll=True, histScale=True, sparse=1):
    """
    if arrayL is a string
    this gets interpeted as the basefilename for load()
    sparse is used for load() if arrayL is 'basefilename'
    """
    #     if len(array.shape) != 2:
    #         raise "array must be of dimension 2"

    ### size = (400,400)
    try:
        w,h = size
    except:
        w,h = size,size
    
    ###print 'wwwwwwwwww',w,h
    frame = wx.Frame(parent, -1, title)
    # canvas = wx.Window(frame, -1) #
    canvas = GLViewer(frame, (w,h), keyTargetWin)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(canvas, 1, wx.EXPAND | wx.ALL, 5);
    frame.SetSizer(sizer);
    sizer.Fit(frame)

    if type(arrayL) is type('fn'):
        canvas.load(arrayL, sparse=sparse)
    elif arrayL != None:
        canvas.appendMosaic(arrayL, imgPosArr, imgSizeArr)

    if histScale:
        canvas.histScale()

    frame.Show(1)
    frame.Layout() # hack for Linux-GTK

    if zoomToAll:
        canvas.zoomToAll()
    
    return canvas
