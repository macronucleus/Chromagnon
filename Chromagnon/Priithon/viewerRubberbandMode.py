__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import numpy as N

log2 = N.log(2)

class viewerRubberbandMode:
    def __init__(self, id=-1, rubberWhat='box', color=(0,1,0), 
                 gfxWhenDone='hide', roiName='1'):
        """
        id can be a viewerID
               or a viewer.GLViewer object
        rubberWhat should be one of:
             'box'
             'line'
             'circle'
             'ellipse'

        gfxWhenDone should be one of: 'hide', 'remove', None
        """
        from Priithon.all import Y
        if type(id) is int:
            self.splitND = Y.viewers[id]
            self.viewer = Y.viewers[id].viewer
        else:
            self.splitND = None # CHECK Y.viewers[id]
            self.viewer = id

        self.id = id
        self.rubberWhat = rubberWhat
        self.color = color
        self.gfxWhenDone = gfxWhenDone
        self.roiName = roiName
        self.gfxIdx = None

        #20070721 self.oldOnMouse= self.viewer.doOnMouse
        #20070721 self.viewer.doLDown =self.onLeft1
        Y._registerEventHandler(self.viewer.doOnLDown, newFcn=self.onLeft1, newFcnName='vLeftClickDoes', oldFcnName=None)

    def __call__(self, *args):
        """no args: return 2d indices (2-tuple of 2d-index-arrays)
           1 arg:  return "selected region" of 2+-D data
        """
        if len(args) == 0:
            return self.ind()
        else:
            data = args[0]
            takeAxes = range(data.ndim-2, data.ndim)
            dataSubReg = data.take(self.ind(), takeAxes)
            dataSubReg.transpose(range(2,data.ndim)+range(2))
            return dataSubReg

    def ind(self): # , compress=False):
        # global nx,ny, i0,i1
        y0,x0 = self.yx0
        y1,x1 = self.yx1
        if x1< x0:
            x0,x1 = x1,x0
        if y1< y0:
            y0,y1 = y1,y0

        nx = 1+x1-x0
        ny = 1+y1-y0

        i0 = N.arange(y0,y1+1)
        i0 = i0.repeat(nx)
        i0.shape = (ny,nx)
        i1 = N.arange(x0,x1+1)[N.newaxis,:]
        i1 = i1.repeat(ny)
        return (i0,i1)
    
    def getSlice(self):
        y0,x0 = self.yx0
        y1,x1 = self.yx1
        return (Ellipsis,slice(y0,y1+1),slice(x0,x1+1))
    slice = property(getSlice, doc="bounding box as slice-tuple")
    def getBoundingBox(self):
        """return edge coordinates yx0,yx1 as 2 numpy arrays
        """
        return N.array(self.yx0), N.array(self.yx1)

    boundYX01 = property(getBoundingBox, doc="2 yx edge-coords as numpy arrays")

    def getSize(self):
        """return height, width as numpy arrays
        """
        y0,x0 = self.yx0
        y1,x1 = self.yx1
        return N.array((y1-y0+1,x1-x0+1))

    size = property(getSize, doc="height,width as numpy arrays")


    def getData(self, id=None):
        """
        return data inside ROI
        if id is None: select data in this ROI's viewer 
        if id is an integer: used that viewer with given id  instead
        else interpret id as a data array where to select the ROI from
        """
        if id is None:
            id = self.id
        if type(id) is int:
            from Priithon.all import Y
            data = Y.viewers[id].data
        else: 
            data = id

        return data[self.slice]
        
    data = property(getData, doc="cut-out data selected by this ROI")

    def getMask(self):
        """
        return bool array of (2D) shape
        1 inside ROI, 0 outside
        """
        id=None

        if id is None:
            id = self.id
        if type(id) is int:
            from Priithon.all import Y
            data = Y.viewers[id].data
        else: 
            data = id


        #ny,nx = data.shape[-2:]
        if self.rubberWhat == 'box':
            m = N.zeros(data.shape[-2:], dtype=N.bool)
            m[self.slice] = 1
        elif self.rubberWhat == 'line':
            m = N.zeros(data.shape[-2:], dtype=N.bool)
            from all import F
            F.drawLine(m, self.yx0, self.yx1, 1)
        elif self.rubberWhat == 'circle':
            y0,x0 = self.yx0
            y1,x1 = self.yx1
            dx = x1-x0
            dy = y1-y0
            x = x0 + .5*dx
            y = y0 + .5*dy
            rx = float(x1-x)
            ry = float(y1-y)
            m = N.fromfunction(lambda yy,xx: 
                               ((y-yy)/ry)**2 + ((x-xx)/rx)**2 < 1., data.shape[-2:]).\
                               astype(N.bool) # use astype instead dtype= -- because the second returns all 0
        return m
    mask = property(getMask, doc="2D boolean mask")

    def onLeft1(self, xEff, yEff, ev):
        self.yx0 = (int(yEff), int(xEff))
        #20070721 self.viewer.doLDown =self.onLeft2
        #20070721 self.viewer.doOnMouse = self.onMove
        from Priithon.all import Y
        Y._registerEventHandler(self.viewer.doOnLDown, newFcn=self.onLeft2, newFcnName='vLeftClickDoes')
        Y._registerEventHandler(self.viewer.doOnMouse, newFcn=self.onMove, newFcnName='vLeftClickDoes', oldFcnName=None)
        self.doThisAlsoOnStart()
        
    def onLeft2(self, xEff, yEff, ev):
        from Priithon.all import Y
        #self.yx1 = (yEff, xEff)
        def ppp(*args):
            pass
        self.viewer.doLDown = ppp

        if   self.gfxWhenDone == 'remove':
            self.gfxRemove()
        elif   self.gfxWhenDone == 'hide':
            self.gfxHide()


        #20070721 self.viewer.doOnMouse = self.oldOnMouse
        Y._registerEventHandler(self.viewer.doOnLDown, oldFcnName='vLeftClickDoes')
        Y._registerEventHandler(self.viewer.doOnMouse, oldFcnName='vLeftClickDoes')

        #sort indices
        y0,x0 = self.yx0
        y1,x1 = self.yx1
        if y1< y0:
            y0,y1 = y1,y0
        if x1< x0:
            x0,x1 = x1,x0
        self.yx0 = y0,x0 
        self.yx1 = y1,x1
        
        self.doThisAlsoOnDone()
        
    def onMove(self, xEff, yEff, ev):
        #self.oldOnMouse(xEff, yEff, xyEffVal) # show label info
        
        self.yx1 = y1,x1 = int(round(yEff)), int(round(xEff))
        y0,x0 = self.yx0
        dy = y1-y0
        dx = x1-x0

        from Priithon.all import U

        # even size
        if ev.AltDown():
            dy2 = int(dy / 2) * 2
            dx2 = int(dx / 2) * 2

            y1 = y0 + dy2
            x1 = x0 + dx2
            self.yx1 = (y1,x1)
            dy = y1-y0
            dx = x1-x0
            
        #power of two
        if ev.ShiftDown() and ev.ControlDown():
            ddy = N.log(abs(dy)) / log2
            dy2 = 2 ** int(ddy+.5)
            ddx = N.log(abs(dx)) / log2
            dx2 = 2 ** int(ddx+.5)

            y1 = y0 + dy2 *   U.sgn(dy)
            x1 = x0 + dx2 *   U.sgn(dx)
            self.yx1 = (y1,x1)
            dy = y1-y0
            dx = x1-x0

        #square 
        elif ev.ShiftDown() or ev.ControlDown():
            if abs(dx) < abs(dy):
                x1 = x0 + abs(dy) *   U.sgn(dx)
                self.yx1 = (y1,x1)
            elif abs(dy) < abs(dx):
                y1 = y0 + abs(dx) *   U.sgn(dy)
                self.yx1 = (y1,x1)
            dx = x1-x0
            dy = y1-y0
            
        if self.splitND is not None:
            self.splitND.label.SetLabel("h,w: %3d %3d" % (abs(dy),abs(dx)))


        self.gfxUpdate()

        #self.viewer.updateGlList( self.my_defGlList )
        self.doThisAlsoOnMove()


    def gfxUpdate(self):
        from Priithon.all import Y
        if self.rubberWhat == 'box':
            self.gfxIdx = \
                Y.vgAddRect(self.id, [self.yx0 ,self.yx1], enclose=True, color=self.color, 
                            width=1, name="ROI-%s"%(self.roiName,), idx=self.gfxIdx, 
                            enable=True, refreshNow=True)
        elif self.rubberWhat == 'line':
            self.gfxIdx = \
                Y.vgAddLines(self.id, [self.yx0 ,self.yx1], color=self.color, 
                            width=1, name="ROI-%s"%(self.roiName,), idx=self.gfxIdx, 
                            enable=True, refreshNow=True)

        elif self.rubberWhat == 'circle':
            y0,x0 = self.yx0
            y1,x1 = self.yx1
            dx = x1-x0
            dy = y1-y0
            x = x0 + .5*dx
            y = y0 + .5*dy
            rx = abs(x1-x)
            ry = abs(y1-y)
            self.gfxIdx = \
                Y.vgAddEllipses(self.id, [(y,x,ry,rx)], color=self.color, 
                            width=1, name="ROI-%s"%(self.roiName,), idx=self.gfxIdx, 
                            enable=True, refreshNow=True)


    def gfxShow(self):
        self.viewer.newGLListEnable(self.gfxIdx, on=True, refreshNow=True)
    def gfxHide(self):
        self.viewer.newGLListEnable(self.gfxIdx, on=False, refreshNow=True)
    def gfxEnable(self, on=True):
        self.viewer.newGLListEnable(self.gfxIdx, on=on, refreshNow=True)
    def gfxRemove(self):
        self.viewer.newGLListRemove(self.gfxIdx, refreshNow=True)
            
            
#     def my_defGlList(self):
#         from Priithon.all import Y

#         self.oldDefGlList()

#         x0,y0 = self.xy0
#         x1,y1 = self.xy1
             
#         if self.rubberWhat == 'box':
#             Y.glBox(x0, y0, x1, y1, color=self.color)
#         elif self.rubberWhat == 'line':
#             Y.glLine(x0, y0, x1, y1, color=self.color)
#         elif self.rubberWhat == 'circle':
#             dx = x1-x0
#             dy = y1-y0
#             r = (dx**2+dy**2)**.5
#             Y.glCircle(x0,y0,r=r, nEdges=60, color=self.color)
#         elif self.rubberWhat == 'ellipse':
#             dx = x1-x0
#             dy = y1-y0
#             Y.glEllipse(x0,y0,rx=dx,ry=dy, nEdges=60,
#                         color=self.color)


    def doThisAlsoOnMove(self):
        pass
    def doThisAlsoOnDone(self):
        pass
    def doThisAlsoOnStart(self):
        pass

