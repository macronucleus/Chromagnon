USEGLUT=True

class graphix:
    def __init__(self, color_tuple, linewidth, hidden = False):

        self.hidden = hidden
        self.color = color_tuple
        self.linewidth = linewidth

    def hide(self):
        self.hidden = True

    def show(self):
        self.hidden = False

    def IsHidden(self):
        return self.hidden


from OpenGL import GL
from OpenGL import GLUT

class graphix_cropbox(graphix):
    '''
    The 3D crop box;s 2D projection on this viewer
    '''
    def __init__(self, lowerbounds, upperbounds, color=(1,1,1), linewidth=1, hidden=False):
        graphix.__init__(self, color, linewidth, hidden)
        self.lowerbounds = lowerbounds
        self.upperbounds = upperbounds

    def GLfunc(self):
        GL.glColor(self.color)
        GL.glLineWidth(self.linewidth)
        GL.glDisable(GL.GL_BLEND)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(self.lowerbounds[1], self.lowerbounds[0])
        GL.glVertex2f(self.lowerbounds[1], self.upperbounds[0])
        GL.glVertex2f(self.upperbounds[1], self.upperbounds[0])
        GL.glVertex2f(self.upperbounds[1], self.lowerbounds[0])
        GL.glEnd()

class graphix_slicelines(graphix):
    '''
    the cross on the viewer indicating where other ortho views slice through
    '''
    def __init__(self, glview, color=(1,1,1), linewidth=1, hidden=False, x0=0, y0=0):
        graphix.__init__(self, color, linewidth, hidden)
        sliceIdx = [glview.mydoc.z, glview.mydoc.y, glview.mydoc.x]
        self.vertline_pos = sliceIdx[glview.dims[1]] + x0
        self.horzline_pos = sliceIdx[glview.dims[0]] + y0
        self.dims = glview.dims
        self.x0 = x0
        self.y0 = y0
#         self.cropbox_rightside = glview.mydoc.cropbox_u[glview.dims[1]]
#         self.cropbox_upperside = glview.mydoc.cropbox_u[glview.dims[0]]
        import numpy as N
        shapes = N.empty((glview.mydoc.nw, 2), N.uint)
        for w, img in enumerate(glview.imgList):
            shapes[w] = img[2].shape[-2:]
        pic_ny, pic_nx = shapes.max(0)
        #print pic_ny, pic_nx, x0, y0

        try:
            self.lowerbounds = [-glview.y0 /glview.scale, -glview.x0 / glview.scale]
            self.upperbounds = [(glview.h-glview.y0) /glview.scale, (glview.w-glview.x0) / glview.scale]
        except:
            self.lowerbounds = [0, 0]
            self.upperbounds = [glview.h /glview.scale, glview.w / glview.scale]

        try:
            self.cropbox_rightside = glview.pic_nx
            self.cropbox_upperside = glview.pic_ny
        except:
            self.cropbox_rightside = 0
            self.cropbox_upperside = 0

    def GLfunc(self):
        GL.glColor(self.color)
        GL.glLineWidth(self.linewidth)
        GL.glDisable(GL.GL_BLEND)
        
        GL.glBegin(GL.GL_LINES)
        GL.glVertex2f(self.vertline_pos+0.5, self.lowerbounds[0])
        GL.glVertex2f(self.vertline_pos+0.5, self.upperbounds[0])
        GL.glVertex2f(self.lowerbounds[1], self.horzline_pos+0.5)
        GL.glVertex2f(self.upperbounds[1], self.horzline_pos+0.5)
        GL.glEnd()

        from Priithon import usefulX as Y
        if self.dims == (1,2):
            coord_strY = str(int(self.vertline_pos + self.y0))
            coord_strX = str(int(self.horzline_pos + self.x0))
        elif self.dims == (1,0):
            coord_strY = str(int(self.vertline_pos))
            coord_strX = str(int(self.horzline_pos - self.y0))
        elif self.dims == (0,2):
            coord_strY = str(int(self.vertline_pos - self.x0))
            coord_strX = str(int(self.horzline_pos))

        if USEGLUT:
            Y.glutText(coord_strY, (float(self.vertline_pos), float(self.cropbox_upperside)), color=(1,0,1), size=0.1, mono=GLUT.GLUT_STROKE_MONO_ROMAN)
            Y.glutText(coord_strX, (float(self.cropbox_rightside), float(self.horzline_pos)), color=(1,0,1), size=0.1, mono=GLUT.GLUT_STROKE_MONO_ROMAN) # float for sizes is required for older? or linux? OpenGL
        

                                 

