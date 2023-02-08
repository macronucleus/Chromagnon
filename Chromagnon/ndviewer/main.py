#!/usr/bin/env priithon

import os, sys
import six
    
import wx, wx.lib.scrolledpanel as scrolled
import wx.lib.agw.aui as aui # from wxpython4.0, wx.aui does not work well, use this instead

try:
    from ..common import guiFuncs as G ,microscopy
    from .. import imgio
    from ..Priithon import histogram#, useful as U
    from ..Priithon.all import Y, U, F
    from ..PriCommon import imgResample
except (ValueError, ImportError):
    from common import guiFuncs as G ,microscopy
    import imgio
    from Priithon import histogram#, useful as U
    from Priithon.all import Y, U, F
    from PriCommon import imgResample

from . import viewer2
from . import glfunc as GL
import OpenGL

import numpy as N
from scipy import ndimage as nd

GLUTINITED = False
FRAMESIZE = (1200,768)
#if __name__ != '__main__':
#    _display = wx.GetClientDisplayRect()[-2:]
#    FRAMESIZE = (min(FRAMESIZE[0], _display[0]), min(FRAMESIZE[1], _display[1]))

_rgbList = [
    (1,0,0),
    (0,1,0),
    (0,0,1),
    (1,1,0),
    (0,1,1),
    (1,0,1),
    (1,1,1),
    ]

_rgbList_names = ['red','green','blue', 'yellow', 'cyan', 'magenta', 'grey']
_rgbList_menuIDs = [wx.NewId() for i in range(len(_rgbList))]

viewers = []

def initglut():
    global GLUTINITED
    #if sys.platform.startswith(('linux')):
    #    GL.USEGLUT=False
    #    return
    if not GLUTINITED and sys.platform.startswith(('linux', 'win')):
        from OpenGL import GLUT
        try:
            GLUT.glutInit([])  ## in order to call Y.glutText()
        except OpenGL.error.NullFunctionError:
            #pass
            raise RuntimeError('FreeGlut is not installed on your computer')
            #print('FreeGlut is not installed on your computer')
        GLUTINITED = True

class ImagePanel(wx.Panel):
    viewCut   = False
    def __init__(self, parent, imFile=None, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, useCropbox=viewer2.CROPBOX):
        wx.Panel.__init__(self, parent, id, pos, size, name='')

        # to make consistent with the older viewers
        self.parent = self
        self.useCropbox = useCropbox
        
        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self._perspectives = []
        #self.loaded = False
        
        ## self.doc contains all the information on the displayed image
        if isinstance(imFile, six.string_types) or hasattr(imFile, 'shape'):#str):
            self.doc = imgio.Reader(imFile)
        else:
            self.doc = imFile

        #self.zsec  = [self.doc.nz//2]
        #self.zlast = [0]
        
        if self.doc: # can be ChromagnonEditor
            self.doc.zlast = 0
            self.addImageXY()

        #self.zshape= self.doc.shape[:-2]

            
    def __del__(self):
        self._mgr.UnInit()
        self.doOnClose()

    def doOnClose(self):
        pass
            
    def addImageXY(self):
        ## draw viewer
        ## each dimension is assgined a number: 0 -- z; 1 -- y; 2 -- x
        ## each view has two dimensions (x-y view: (1,2); see below viewer2.GLViewer() calls) and
        ## an axis normal to it (x-y view: 0)

        self.viewers = [] # XY, XZ, ZY
        self.viewers.append(viewer2.GLViewer(self, dims=(1,2),
                                             style=wx.BORDER_SUNKEN,
                                             size=wx.Size(self.doc.nx, self.doc.ny),
                                             useCropbox=self.useCropbox
                                             ))

        self._mgr.AddPane(self.viewers[0], aui.AuiPaneInfo().Floatable(False).Name('XY').Caption("XY").BestSize((self.doc.nx, self.doc.ny)).CenterPane().Position(0))

        self.viewers[-1].setMyDoc(self.doc, self)
        self.viewers[-1].setAspectRatio(self.doc.pxlsiz[-2]/self.doc.pxlsiz[-1])

        imgs2view = self.takeSlice((0,))[0]
        
        for i, img in enumerate(imgs2view):
            self.viewers[-1].addImg(img, None)

            if hasattr(self.doc, 'alignParms'):
                alignParm = self.doc.alignParms[self.doc.t,i]
                self.viewers[-1].updateAlignParm(-1, alignParm)

        # sliders
        if 1:#self.doc.nz > 1 or self.doc.nt > 1:
            self.addZslider()
            ysize = int(self.doc.nz > 1) * 60 + int(self.doc.nt > 1) * 40
            ysize = max(self.doc.nz, ysize)
            self._mgr.AddPane(self.sliderPanel, aui.AuiPaneInfo().Name('Image').Caption("Image").Right().Position(1).BestSize((200,ysize)).MinSize((200,ysize)))
                        
        # histogram
        self.recalcHist_todo_Set = set()

        self.initHists() # histogram/aligner panel
        self.setupHistArrL()
        self.recalcHistL(False)
        self.autoFitHistL()

        self._mgr.AddPane(self.histsPanel, aui.AuiPaneInfo().Name('Histogram').Caption("HistoPanel").MaximizeButton(True).Right().Position(0).BestSize((200, self.doc.ny)).MinSize((200,50+70*2)).MaxSize((250,self.doc.ny)))#MinSize((200,50+70*self.doc.nw)).MaxSize((250,self.doc.ny)))

        wx.CallAfter(self._mgr.Update)
        self.histsPanel.Layout()
        
    def updateGLGraphics(self, viewToUpdate = -1, RefreshNow=True):
        '''
        update cropbox and the slicing lines in all viewers;
        set new image to viewer indicated by viewToUpdate:
            -1 -- no updating viewer image
            0,1,2 -- update viewToUpdate
            3 -- update all viewers
        '''
        # viewers
        if hasattr(viewToUpdate, '__iter__') or viewToUpdate >= 0:
            if viewToUpdate  == 3:
                views2update = list(range(3))
            elif type(viewToUpdate) == int:
                views2update = [viewToUpdate]
            else:
                views2update = viewToUpdate

            views2update = [i for i in views2update if i < len(self.viewers)]
                
            imgs2view = self.takeSlice(views2update)
            for i in views2update:
                v = self.viewers[i]
                for j, img in enumerate(imgs2view[i]):
                    if v.dims != (1,0):
                        v.setImage(j, img, 0)
                    else:
                        v.setImage(j, img.transpose(1,0), 0)

        # draw lines
        for v in self.viewers:
            v.viewGpx = []
            if v.useCropbox:
                lowerBound = self.doc.roi_start.take(v.dims) #cropbox_l.take(v.dims) + ld
                upperBound = self.doc.roi_size.take(v.dims) + lowerBound #cropbox_u.take(v.dims) + ld
                v.viewGpx.append(GL.graphix_cropbox(lowerBound, upperBound))

        pps = self._mgr.GetAllPanes()

        if not any([pp.name == 'ZY' for pp in pps]) or not self.orthogonal_toggle.GetValue():
            for v in self.viewers:
                if v.viewGpx:
                    v.updateGlList([ g.GLfunc for g in v.viewGpx ], RefreshNow)
                else:
                    v.updateGlList(None, RefreshNow)
                v.useHair = False
                #v.dragSide = 0
        else:
            #wx.Yield()
                #if self.orthogonal_toggle.GetValue():
            for v in self.viewers:
                v.viewGpx.append(GL.graphix_slicelines(v))
                v.updateGlList([ g.GLfunc for g in v.viewGpx ], RefreshNow)
                #g = GL.graphix_slicelines(v)
                #v.updateGlList([ g.GLfunc ], RefreshNow)
                v.useHair = True
                #else:
                #for v in self.viewers:
                #v.updateGlList(None, RefreshNow)
                #v.useHair = False
                #v.dragSide = 0
        #self.doc.setIndices()

    old="""
    def IsCut(self):
        return self.viewCut"""

    def updateCropboxEdit(self):
        pass

    def addZslider(self):
        self.sliderPanel = wx.Panel(self, -1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.sliderPanel.SetSizer(sizer)

        # image info
        # \n
        box = G.newSpaceV(sizer)

        bb, box = G.newStaticBox(self.sliderPanel, box, title='Image info', size=(150,-1))#wx.DefaultSize)

        if sys.platform.startswith(('win', 'linux')):
            fsize = 9
        else:
            fsize = 11
        font = wx.Font(fsize, wx.SWISS, wx.NORMAL, wx.NORMAL)
        
        # pixel size
        pxsiz = tuple(self.doc.pxlsiz[::-1])
        dimstr = ('X', 'Y', 'Z')
        line = 'Pixel size (nm):\n'
        pxstr = '  '
        for i, d in enumerate(pxsiz):
            if d:
                pxstr += '%s %i: ' % (dimstr[i], int(d*1000))
        if pxstr:
            line += pxstr[:-2]
        else:
            line = ''
        if line:
            label = G.makeTxt(self.sliderPanel, box, line, flag=wx.EXPAND)
            label.SetFont(font)
            label.SetLabel(line)
            #label.Wrap(self.GetSize().width)
        # data type
        pxtype = imgio.bioformatsIO.pixeltype_to_bioformats(self.doc.dtype)
        line = 'Data type: %s ' % pxtype
        label = G.makeTxt(self.sliderPanel, box, line)
        label.SetFont(font)

        #bb.Layout()
        #box.Layout()
        
        # z slider
        if self.doc.nz > 1:
            topSizer = G.newSpaceV(sizer)

            #label, self.zSliderBox = G.makeTxtBox(self.sliderPanel, topSizer, 'Z', defValue=str(self.doc.z), tip='enter z idx', style=wx.TE_PROCESS_ENTER)
            label, self.zSliderBox = G.makeTxtBox(self.sliderPanel, topSizer, 'Z', defValue=self.doc.z, tip='enter z idx', style=wx.TE_PROCESS_ENTER)

            self.zSliderBox.Bind(wx.EVT_TEXT_ENTER, self.OnZSliderBox)

            G.makeTxt(self.sliderPanel, topSizer, r'/'+str(self.doc.nz-1))

            self.zSlider = wx.Slider(self.sliderPanel, wx.ID_ANY, self.doc.z, 0, 
                                     self.doc.nz-1,
                                     size=wx.Size(150,-1),
                                     style = wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)#|wx.SL_LABELS | wx.SL_AUTOTICKS)

            topSizer.Add(self.zSlider, 6, wx.ALL|wx.ALIGN_LEFT, 2)
            #wx.EVT_SLIDER(self, self.zSlider.GetId(), self.OnZSlider)
            self.Bind(wx.EVT_SLIDER, self.OnZSlider, id=self.zSlider.GetId())
            #wx.EVT_KEY_DOWN(self, self.zSlider.GetId(), self.OnKeyZSlider)
            #self.zSlider.Bind(wx.EVT_KEY_DOWN, self.OnKeyZSlider)
            if self.doc.nt == 1:
                self.sliderPanel.Bind(wx.EVT_KEY_DOWN, self.OnKeyZSlider)
            self.zSlider.Bind(wx.EVT_KEY_DOWN, self.OnKeyZSlider)
            #self.Bind(wx.EVT_CHAR, self.OnKeyZSlider)

            #/n
            box = G.newSpaceV(sizer)
            
            autofocusButton = G.makeButton(self.sliderPanel, box, self.OnAutoFocus, title='Auto focus', tip='')
            
            #/n
            box = G.newSpaceV(sizer)

            self.orthogonal_toggle = G.makeToggleButton(self.sliderPanel, box, self.onOrthogonal, title='Orthogonal view')

            #/n
            box = G.newSpaceV(sizer)
            self.saveScrButton = G.makeButton(self.sliderPanel, box, self.onSaveScr, title='Save screen')

            self.choice_viewers = ['XY', 'XZ', 'ZY']
            label, self.viewerch = G.makeListChoice(self.sliderPanel, box, 'viewer ', self.choice_viewers, defValue=[self.choice_viewers[0]])
            self.viewerch.Enable(0)
        
        # t slider
        if self.doc.nt > 1:  ## need a time slider
            box = G.newSpaceV(sizer)

            label, self.tSliderBox = G.makeTxtBox(self.sliderPanel, box, 'T', defValue=str(self.doc.t), tip='enter time idx', style=wx.TE_PROCESS_ENTER)
            
            self.tSliderBox.Bind(wx.EVT_TEXT_ENTER, self.OnTSliderBox)

            G.makeTxt(self.sliderPanel, box, r'/'+str(self.doc.nt-1))

            self.tSlider = wx.Slider(self.sliderPanel, wx.ID_ANY, 0, 0,
                                     self.doc.nt-1,
                                     size=wx.Size(150,-1),
                                     style = wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)#|wx.SL_LABELS | wx.SL_AUTOTICKS)
            box.Add(self.tSlider, 6, wx.ALL|wx.ALIGN_LEFT, 2)
            #wx.EVT_SLIDER(self, self.tSlider.GetId(), self.OnTSlider)
            self.Bind(wx.EVT_SLIDER, self.OnTSlider, id=self.tSlider.GetId())

            if self.doc.nz == 1:
                self.sliderPanel.Bind(wx.EVT_KEY_DOWN, self.OnKeyTSlider)
            self.tSlider.Bind(wx.EVT_KEY_DOWN, self.OnKeyTSlider)

        if self.doc.nz > 1 or self.doc.nt > 1:
            box = G.newSpaceV(sizer)
            self.loadImgButton = G.makeButton(self.sliderPanel, box, self.loadImage2Memory, title='Load whole data into memory', tip='If the Z/T slider or changing scaling is too slow, try this funtion.')


    def OnAutoFocus(self, evt=None):
        """
        please read Chromagnon.alignfuncs.findBestRefZs() for detail of the logic
        """
        if self.doc.nt > 1:
            t = int(self.tSliderBox.GetValue())
        else:
            t = 0
        ws = [w for w, hist in enumerate(self.hist_toggleButton) if hist.GetValue()]

        ms = N.zeros((len(ws),self.doc.nz), N.float32)

        # FFTW does not work with another program using it
        # here is the workaround for Chromagnon
        try:
            batch = self.GetParent().GetParent().GetParent()
            if hasattr(batch, 'th') and batch.th.isAlive():
                for wi, w in enumerate(ws):
                    arr = self.doc.get3DArr(t=t, w=w)
                    for z in range(self.doc.nz):
                        ms[wi,z] = N.prod(U.mmms(arr[z])[-2:]) # mean * std
                v,_,w,z = U.findMax(ms)
                self.zSliderBox.SetValue(str(z))
                self.OnZSliderBox()
                self.OnAutoScale()
                        
                G.openMsg(parent=self.parent, msg='A clumsy focusing method was used since another program was using FFTW.\nPlease wait for the better method until the other program is done.', title="Please wait")
                return
        except AttributeError: # no parent?
            pass

        # Frequency-based caluculation starts
        #try:
        #    from ..Priithon.all import F
        #except (ValueError, ImportError):
        #    from Priithon.all import F
        
        ring = F.ringArr(self.doc.shape[-2:], radius1=self.doc.shape[-1]//10, radius2=self.doc.shape[-2]//4, orig=(0,0), wrap=1)


        for wi, w in enumerate(ws):
            arr = self.doc.get3DArr(t=t, w=w)
            arr = arr / arr.mean()
            for z in range(self.doc.nz):
                af = F.rfft(N.ascontiguousarray(arr[z]))
                ar = af * ring[:,:af.shape[-1]]
                ms[wi,z] = N.sum(N.abs(ar))
        v,_,w,z = U.findMax(ms)

        self.zSliderBox.SetValue(str(z))
        self.OnZSliderBox()
        self.OnAutoScale()

    def loadImage2Memory(self, evt=False):
        # since bioformats is too slow, orthogonal view needs to read array data into memory
        # On my second thought, 2k x 2k image also takes long to read, it is better to load into memory always.
        if (self.doc.nz > 1 or self.doc.nt > 1) and self.loadImgButton.IsEnabled() and issubclass(type(self.doc), imgio.generalIO.GeneralReader):
            zlast = self.doc.zlast
            z = self.doc.z
            pxlsiz = self.doc.pxlsiz
            roi_start = self.doc.roi_start
            roi_size = self.doc.roi_size
            
            self.doc = imgio.arrayIO.ArrayReader(self.doc)
            self.doc.zlast = zlast
            self.doc.z = z
            self.doc.pxlsiz = pxlsiz
            self.doc.roi_start = roi_start
            self.doc.roi_size = roi_size
            #self.loaded = True
            self.viewers[-1].setMyDoc(self.doc, self)
            #print('loadImage2Memory called')
            self.loadImgButton.Enable(0)
            
    def onOrthogonal(self, evt=None):
        """
        transform to the orthogonal viewer
        """
        if self.orthogonal_toggle.GetValue() and len(self.viewers) == 1:
            self.loadImage2Memory()
            self._mgr.GetPane('Image').Left().Position(1)
            self.OnAddX()
            self.OnAddY()
            self.OnAddLastViewer()
            self.viewerch.Enable(1)
        elif self.orthogonal_toggle.GetValue():
            self._mgr.GetPane('Image').Left().Position(1)
            self._mgr.GetPane('XZ').Show()
            self._mgr.GetPane('ZY').Show()
            self._mgr.Update()
            self.viewerch.Enable(1)
        else:
            self._mgr.GetPane('Image').Right().Position(1)
            self._mgr.GetPane('ZY').Hide()
            self._mgr.GetPane('XZ').Hide()
            self._mgr.Update()
            self.updateGLGraphics(0, True)
            self.viewerch.Enable(0)

    def OnAddY(self, evt=None):
        """
        add ZY viewer
        """
        pps = self._mgr.GetAllPanes()
        if not any([pp.name == 'ZY' for pp in pps]):
            self.viewers.append(viewer2.GLViewer(self, dims=(1,0),
                                                 style=wx.BORDER_SUNKEN,
                                                 size=wx.Size(self.doc.nz, self.doc.ny),
                                                 useCropbox=self.useCropbox
                                                 ))
            self._mgr.AddPane(self.viewers[-1], aui.AuiPaneInfo().Floatable(False).Name('ZY').Caption("ZY").Left().Position(0).BestSize((self.doc.nz, self.doc.ny)))#.Dockable(False).Top())
            self.viewers[-1].setMyDoc(self.doc, self)
            self.viewers[-1].scale *= self.doc.pxlsiz[-3]/self.doc.pxlsiz[-2] # mag compensate
            self.viewers[-1].setAspectRatio(self.doc.pxlsiz[-2]/self.doc.pxlsiz[-3])
        else:
            self._mgr.GetPane('ZY').Show()

    def OnAddX(self, evt=None):
        """
        add XZ viewer
        """
        pps = self._mgr.GetAllPanes()
        if not any([pp.name == 'XZ' for pp in pps]):
            self.viewers.append(viewer2.GLViewer(self, dims=(0,2),
                                                 style=wx.BORDER_SUNKEN,
                                                 size=wx.Size(self.doc.nx, self.doc.nz),
                                                 useCropbox=self.useCropbox
                                                 ))
            self._mgr.AddPane(self.viewers[-1], aui.AuiPaneInfo().Floatable(False).Name('XZ').Caption("XZ").BestSize((self.doc.nz, self.doc.ny)).CenterPane().Position(1))
            self.viewers[-1].setMyDoc(self.doc, self)
            self.viewers[-1].setAspectRatio(self.doc.pxlsiz[-3]/self.doc.pxlsiz[-1])
        else:
            self._mgr.GetPane('XZ').Show()

    def OnAddLastViewer(self, evt=None):
        """
        add images to the viewer and update the window manager
        """
        self.viewers[-1].setMyDoc(self.doc, self)

        # get arrays of flipped, transformed, projected for each dims
        dims_set = set( range(3))
        imgs2view = self.takeSlice(dims_set)
        
        # display image
        for v in self.viewers[1:]:
            axisNormal = dims_set.difference(set(v.dims)).pop() # this does not work..
            im2view = imgs2view[axisNormal]
            for i, img in enumerate(im2view):
                if v.dims != (1,0):  ## x-y or x-z view

                    v.addImg(img, None)
                else:   ## y-z view
                    if img.shape[0] == 1:
                        v.addImg(img.transpose(), None)
                    else:
                        v.addImg(img.transpose(1,0), None)

                if hasattr(self.doc, 'alignParms'):
                    alignParm = self.doc.alignParms[self.doc.t,i]
                    v.updateAlignParm(-1, alignParm)

            if self.doc.nw > 1:
                for i in range(self.doc.nw):
                    #wave = self.doc.wave[i]
                    #self.setColor(i, wave, False)
                    r,g,b = self.viewers[0].imgList[i][6:9]
                    v.setColor(i, r,g,b, RefreshNow=False)

        for i in range(self.doc.nw):
            l, r = self.viewers[0].imgList[i][4:6]
            if l is None or r is None:
                self.hist[i].autoFit()
            else:
                self.hist[i].setBraces(l, r)

        self._mgr.Update()

    def onSaveScr(self, evt=None):
        #from Priithon.all import Y
        #from PIL import Image

        fn = Y.FN(save=1)#, verbose=0)
        #Image.init()
        if not fn:
            return
        elif os.path.splitext(fn)[-1][1:] not in imgio.imgIO.WRITABLE_FORMATS:#Image.EXTENSION:
            G.openMsg(parent=self.parent, msg='Please supply file extension.\nThe file was not saved %s' % os.path.splitext(fn)[-1][1:], title="File format unknown")
            return
            
        # choose viewers
        if self.orthogonal_toggle.GetValue():
            vstr = self.viewerch.GetStringSelection()
            vid = self.choice_viewers.index(vstr)
        else:
            vid = 0
        v = self.viewers[vid]
        #refresh
        self.hist[0].setBraces(self.hist[0].leftBrace, self.hist[0].rightBrace)
        # save
        Y.vSaveRGBviewport(v, fn, flipY=False)

        
    def initHists(self):
        ''' Initialize the histogram/aligner panel, and a bunch of empty lists;
        define HistogramCanvas class;s doOnBrace() and doOnMouse() behaviors
        '''
        self.histsPanel = scrolled.ScrolledPanel(self, -1)#wx.Panel(self, -1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.histsPanel.SetSizer(sizer)

        cookiecutterSizer = wx.BoxSizer(wx.HORIZONTAL)
        # This sizer contains both the cookie cutter toggle button and the cropbox editor
        sizer.Add(cookiecutterSizer, 0, wx.ALL|wx.EXPAND, 2)

        autoscaleButton = G.makeButton(self.histsPanel, cookiecutterSizer, self.OnAutoScale, title='Auto scale', tip='')


        self.hist = [None] * self.doc.nw
        self.hist_arr = [None] * self.doc.nw
        self.hist_min  = [None]*self.doc.nw
        self.hist_max  = [None]*self.doc.nw
        self.hist_toggleButton  = [None]*self.doc.nw
        self.hist_show = [None]*self.doc.nw
        self.mmms      = [None]*self.doc.nw
        self.intensity_label = [None] * self.doc.nw
        self.hist_label = [None] * self.doc.nw
        
        self.hist_singleChannelMode = None
        self.hist_toggleID2col    = {}

        for i in range(self.doc.nw):
            wave = self.doc.wave[i]#mrcIO.getWaveFromHdr(self.doc.hdr, i)
            self.hist_show[i] = True

            box = G.newSpaceV(sizer)
            
            self.hist_toggleButton[i] = G.makeToggleButton(self.histsPanel, box, self.OnHistToggleButton, title=str(wave), size=(40,-1))
            self.hist_toggleButton[i].Bind(wx.EVT_RIGHT_DOWN, 
                                           lambda ev: self.OnHistToggleButton(ev, i=i, mode="r"))
            self.hist_toggleButton[i].SetValue( self.hist_show[i] )

            self.intensity_label[i] = G.makeTxt(self.histsPanel, box, ' '*32)

            box = G.newSpaceV(sizer)
            
            self.hist[i] = histogram.HistogramCanvas(self.histsPanel, size=(200,30))#size)

            box.Add(self.hist[i])

            for ii,colName in enumerate(_rgbList_names):
                self.hist[i].menu.Insert(ii, _rgbList_menuIDs[ii], colName)
                self.hist[i].Bind(wx.EVT_MENU, self.OnHistColorChange, id=_rgbList_menuIDs[ii])

            self.hist[i].menu.InsertSeparator(ii+1)
            self.hist[i].menu.Remove(histogram.Menu_Log)
            self.hist[i].menu.Remove(histogram.Menu_FitYToSeen)


            self.hist_toggleID2col[ self.hist_toggleButton[i].GetId() ] = i
            
            #/n
            box = G.newSpaceV(sizer)
            self.hist_label[i] = G.makeTxt(self.histsPanel, box, ' '*45)
            
            def fff(s, ii=i):
                l, r = s.leftBrace, s.rightBrace
                for v in self.viewers:
                    ## TODO: different scaling for x-z and y-z viewer??
                    v.changeHistScale(ii, l, r)

            self.hist[i].doOnBrace.append(fff)

            def ggg(xEff, ev, ii=i):
                l,r =  self.hist[ii].leftBrace,  self.hist[ii].rightBrace
                if self.doc.dtype in (N.uint8, N.int16, N.uint16, N.int32):
                    self.hist_label[ii].SetLabel("I: %6.0f  l/r: %6.0f %6.0f"  %(xEff,l,r))
                else:
                    self.hist_label[ii].SetLabel("I: %7.1f  l/r: %7.1f %7.1f"  %(xEff,l,r))

            self.hist[i].doOnMouse.append(ggg)

        if self.doc.nw > 1:
            for i in range(self.doc.nw):
                wave = self.doc.wave[i]
                self.setColor(i, wave, False)

        #/n/n
        box = G.newSpaceV(sizer)
        G.makeTxt(self.histsPanel, box, ' ') # dummy
        box = G.newSpaceV(sizer)
        self.xy_label = G.makeTxt(self.histsPanel, box, ' '*64)

        box = G.newSpaceV(sizer)
        self.roi_label0 = G.makeTxt(self.histsPanel, box, ' '*64)
        box = G.newSpaceV(sizer)
        self.roi_label1 = G.makeTxt(self.histsPanel, box, ' '*64)

        self.histsPanel.SetAutoLayout(1)
        self.histsPanel.SetupScrolling()
                
    def OnAutoScale(self, evt=None):
        """
        called when the autoscale button is hit
        """
        for w in range(self.doc.nw):
            self.recalcHist(w, None)
        self.autoFitHistL()

    def OnHistColorChange(self, ev=None):
        '''
        handle the popup color selection menu in the histogram canvas
        '''
        evobj = ev.GetEventObject()  ## the window associated with this event
        if evobj in self.hist:    ## What's this for?? --lin
            i = self.hist.index( evobj )

            global iii # HACK FIXME
            try:
                iii
            except:
                iii=-1
            iii= (iii+1) % len(_rgbList)
            rgb = _rgbDefaultColor(iii)

        # selected col on menu
        else:
            menus = [h.menu for h in self.hist]
            i = menus.index( evobj )
            Id = ev.GetId()
            r, g, b = _rgbList[ _rgbList_menuIDs.index(Id) ]

        self._setColor(i, r, g, b, RefreshNow=1)
        
    def setColor(self, i, wavelength, RefreshNow=True):
        r, g, b = microscopy.LUT(wavelength)
        self._setColor(i, r, g, b, RefreshNow)

    def _setColor(self, i, r, g, b, RefreshNow=True):
        for v in self.viewers:
            v.setColor(i, r, g, b, RefreshNow)

        self.hist[i].m_histGlRGB=(r, g, b)

        self.intensity_label[i].SetForegroundColour(wx.Colour(r, g, b))
        self.hist_label[i].SetForegroundColour((r, g, b))
        
        if RefreshNow:
            self.hist[i].Refresh(0)

    def setupHistArrL(self):
        for i in range( self.doc.nw ):
            self.setupHistArr(i)
            
    def setupHistArr(self,i):
        self.hist_arr[i] = None
        dtype = self.doc.dtype

        ## what about floating point, or int32?
        if dtype == N.uint8:
            self.hist_min[i], self.hist_max[i] = 0, 1<<8
        elif dtype == N.uint16:
            self.hist_min[i], self.hist_max[i] = 0, 1<<16
        elif dtype == N.int16:
            self.hist_min[i], self.hist_max[i] = 1-(1<<15), (1<<15)
             
        if dtype in (N.uint8, N.int16, N.uint16):
            self.hist_arr[i] = N.zeros(shape= self.hist_max[i] - self.hist_min[i], dtype=N.int32)

    def recalcHistL(self, postponeToIdle):
        for i in range( self.doc.nw ):
            self.recalcHist(i, postponeToIdle)

    def recalcHist(self, i, postponeToIdle):
        '''
        recalculate histogram for wave i
        '''
        if postponeToIdle:
            self.recalcHist_todo_Set.add(i)
            return

        img = self.viewers[0].imgList[i][2].ravel()  ## HACK
        for viewer in self.viewers[1:]:
            img = N.concatenate((img, viewer.imgList[i][2].ravel()))

        mmms = U.mmms( img )

        self.mmms[i] = mmms

        if self.hist_arr[i] is not None:
            U.histogram(img, amin=self.hist_min[i], amax=self.hist_max[i], histArr=self.hist_arr[i])
            self.hist[i].setHist(self.hist_arr[i], self.hist_min[i], self.hist_max[i])
        else:
            resolution = 10000
    
            a_h = U.histogram(img, resolution, mmms[0], mmms[1])

            self.hist[i].setHist(a_h, mmms[0], mmms[1])

    def autoFitHistL(self):
        for i in range( self.doc.nw ):
            self.hist[i].autoFit(amin=self.mmms[i][0], amax=self.mmms[i][1])

    def OnHistToggleButton(self, ev=None, i=0, mode=None):
        if ev is not None:
            i = self.hist_toggleID2col[ ev.GetId() ]
            self.hist_show[i] = self.hist_toggleButton[i].GetValue() # 1-self.hist_show[i]

        # 'r': go "singleCHannelMode" -- show only channel i using grey scale, hide others
        if mode == 'r':
            if self.hist_singleChannelMode == i: # switch back to normal
                for ii in range(self.doc.nw):
                    wave = self.doc.wave[ii]#mrcIO.getWaveFromHdr(self.doc.hdr, ii)
                    label = str(wave)
                    self.hist_toggleButton[ii].SetLabel(label)
                    r, g, b = self.hist[ii].m_histGlRGB
                    [v.setColor(ii, r, g, b, RefreshNow=ii==self.doc.nw-1) for v in self.viewers]
                    [v.setVisibility(ii, self.hist_show[ii], RefreshNow=ii==self.doc.nw-1) for v in self.viewers]
                self.hist_singleChannelMode = None
            else:                                # active grey mode for color i only
                for ii in range(self.doc.nw):
                    if ii == i:
                        wave = self.doc.wave[ii]#mrcIO.getWaveFromHdr(self.doc.hdr, ii)
                        label = str(wave)
                        self.hist_toggleButton[ii].SetLabel(label)
                        visible = self.hist_show[ii]
                        [v.setColor(ii, 1,1,1, RefreshNow=ii==self.doc.nw-1) for v in self.viewers]
                    else:
                        self.hist_toggleButton[ii].SetLabel('--')
                        visible = False

                    [v.setVisibility(ii, visible, RefreshNow=ii==self.doc.nw-1) for v in self.viewers]
                self.hist_singleChannelMode = i
        # other mode: show all color channels (when hist_show[i] is true)
        else:
            if self.hist_singleChannelMode is not None: # switch back to normal
                for ii in range(self.doc.nw):
                    wave = self.doc.wave[ii]#mrcIO.getWaveFromHdr(self.doc.hdr, ii)
                    label = str(wave)
                    self.hist_toggleButton[ii].SetLabel(label)#'%d'%ii)
                    r, g, b = self.hist[ii].m_histGlRGB
                    if  self.hist_show[ii]:
                        visible = True
                    else:
                        visible = False   ## disable this wavelength; don't even show black
                    [v.setColor(ii, r, g, b, RefreshNow=ii==self.doc.nw-1) for v in self.viewers]
                    [v.setVisibility(ii, visible, RefreshNow=ii==self.doc.nw-1) for v in self.viewers]
            else:
                if self.hist_show[i]:
                    visible = True
                else:
                    visible = False   ## disable this wavelength; don't even show black
                [v.setVisibility(i, visible) for v in self.viewers]

        #self.doc._wIdx = [w for w, bl in enumerate(self.hist_show) if bl]


        
    def OnZSliderBox(self, event=None):
        z = int(self.zSliderBox.GetValue())
        if z >= self.doc.nz:
            z = self.doc.nz - 1
        elif z < 0:
            z = 0
            #while z < 0:
            #z = self.doc.nz + z
        self.set_zSlice(z)
        self.zSlider.SetValue(z)
     
    def OnZSlider(self, event):
        z = event.GetInt()
        self.set_zSlice(z)
        self.zSliderBox.SetValue(str(z))

    def OnKeyZSlider(self, evnt):
        keycode = evnt.GetKeyCode()
        if keycode == wx.WXK_RIGHT:
            self.doc.z += 1
            if self.doc.z >= self.doc.nz:
                self.doc.z = self.doc.nz - 1
        elif keycode == wx.WXK_LEFT:
            self.doc.z -= 1
            if self.doc.z < 0:
                self.doc.z = 0

        self.zSliderBox.SetValue(str(self.doc.z))
        self.set_zSlice(self.doc.z)
        self.zSlider.SetValue(self.doc.z)

        evnt.Skip()

    def OnKeyTSlider(self, evnt):
        keycode = evnt.GetKeyCode()
        if keycode == wx.WXK_RIGHT:
            self.doc.t += 1
            if self.doc.t >= self.doc.nt:
                self.doc.t = self.doc.nt - 1
        elif keycode == wx.WXK_LEFT:
            self.doc.t -= 1
            if self.doc.t < 0:
                self.doc.t = 0
        self.tSliderBox.SetValue(str(self.doc.t))
        self.set_tSlice(self.doc.t)
        self.tSlider.SetValue(self.doc.t)

        evnt.Skip()
        
    def set_zSlice(self, z):
        self.doc.z = int(z)
        if self.doc.z >= self.doc.nz:
            self.doc.z = self.doc.nz
        elif self.doc.z < 0:
            self.doc.z = 0


        ## insert
       # zsecTuple = tuple(self.zsec)

        #section-wise gfx:  name=tuple(zsec)
        try:
            self.viewers[0].newGLListEnableByName((self.doc.zlast,), on=False, 
                                              skipBlacklisted=True, refreshNow=False)
        except KeyError:
            pass
        try:
            self.viewers[0].newGLListEnableByName((self.doc.z,), on=True, 
                                              skipBlacklisted=True, refreshNow=False)
        except KeyError:
            pass
        self.doc.zlast = z
        ##### end

            
        self.updateGLGraphics(list(range(len(self.viewers))))
        self.recalcHistL(False)
        for i in range( self.doc.nw ):
            self.hist[i].Refresh(0)



    def OnTSliderBox(self, event):
        t = int(self.tSliderBox.GetValue())
        if t >= self.doc.nt:
            t = self.doc.nt - 1
        while t < 0:
            t = self.doc.nt + t
        self.set_tSlice(t)
        self.tSlider.SetValue(t)
     
    def OnTSlider(self, event):
        t = event.GetInt()
        self.set_tSlice(t)
        self.tSliderBox.SetValue(str(t))

    def set_tSlice(self, t):
        self.doc.t = int(t)
        self.updateGLGraphics(list(range(len(self.viewers))))
        self.recalcHistL(False)
        for i in range( self.doc.nw ):
            self.hist[i].Refresh(0)

    def takeSlice(self, axisSet=(0,1,2)):
        '''
        return the slice of the data array (of all wavelengths) defined by time ti and
        the axis this slice is normal to: 0 -- z; 1 -- y; 2 -- x.
        self.alignParams[i]: (tz, ty, tx, rot, mag)
        '''
        #t = self.doc.t
        nc = self.doc.nz / 2.
            
        retSlice = {}

        sliceIdx = [self.doc.z, self.doc.y, self.doc.x]

        # print 'takeSlice'
        for w in range(self.doc.nw):
            if hasattr(self.doc, 'alignParms'):
                tz, ty, tx, rot, magz, magy, magx = self.doc.alignParms[self.doc.t,w][:7]
            else:
                tz, ty, tx, rot, magz, magy, magx = 0, 0, 0, 0, 1, 1, 1

            for axisSliceNormalTo in axisSet: # axis 0,1,2
                shape = [self.doc.nz, self.doc.ny, self.doc.nx]
                shape.pop(axisSliceNormalTo) # projection shape
                retSlice.setdefault(axisSliceNormalTo, []).append(N.zeros(shape, self.doc.dtype)) # canvas
                if hasattr(self.doc, 'alignParms'):
                    tc = self.doc.alignParms[self.doc.t,w, axisSliceNormalTo]
                else:
                    tc = 0

                ## if it's a x-y slice, or if there's no rotation, then use the simple slicing method
                # x-y view uses openGL to rotate and magnify
                if axisSliceNormalTo == 0:
                    whichSlice = sliceIdx[axisSliceNormalTo] - tc#\
                                 #self.doc.alignParms[self.doc.t,w, axisSliceNormalTo]
                    whichSlice = round((whichSlice - nc) / float(magz) + nc)
                    if 0 > whichSlice:
                        whichSlice = 0
                    elif whichSlice >= self.doc.nz:
                        whichSlice = self.doc.nz-1
                    try:
                        retSlice[axisSliceNormalTo][w][:] = self.doc.get3DArr(w=w, zs=[whichSlice], t=self.doc.t)[0]#img.getArr(w=w, z=whichSlice, t=self.doc.t)#self.doc.get3DArr(w=w, zs=[whichSlice], t=self.doc.t)[0]
                    except ValueError:
                        #print retSlice.shape, shape, self.doc.img.getArr(w=w, z=whichSlice, t=self.doc.t).shape
                        raise

                # no rotation and magnification
                elif not rot and N.all([magz==1, magy==1, magx==1]):
                    arr = self.doc.get3DArr(w=w, t=self.doc.t)
                    whichSlice = sliceIdx[axisSliceNormalTo] - tc#\
                                 #self.doc.alignParms[self.doc.t,w, axisSliceNormalTo]
                    retSlice[axisSliceNormalTo][w][:] = N.squeeze( arr.take([whichSlice], axisSliceNormalTo) ) ## HACK [:] to keep the shape of retSlice[w]
                ## otherwise, need to use affine matrix and interpolation to calculate the slice
                    del arr
                else: ## x-z or y-z slice && rotation != 0
                    if shape[0] == 1:
                        continue
                    ## First calculate the coordinates in the original frame for every point along slicing line
                    arr = self.doc.get3DArr(w=w, t=self.doc.t)
                    mag = N.array((magy, magx)) # XY mag is interpolated for XZ and ZY views


                    ny = self.doc.ny
                    nx = self.doc.nx
                    ccdCorr = None
                    sliceIdxYX = sliceIdx[1:]
                        
                    yxCenter = [ny/2., nx/2.]
                    #ty = tx = 0

                    invmat = imgResample.transformMatrix(rot, mag)
                    
                    if axisSliceNormalTo == 1: # x-z slice
                        pointsOnSliceLine = N.empty((2, nx))
                        pointsOnSliceLine[0] = sliceIdxYX[0] # y coordinate
                        pointsOnSliceLine[1] = N.arange(nx) # x coordinate
                    else: # y-z
                        pointsOnSliceLine = N.empty((2, ny))
                        pointsOnSliceLine[0] = N.arange(ny) # y coordiante
                        pointsOnSliceLine[1] = sliceIdxYX[1] # x coordinate

                    yx_input = N.dot(invmat,  pointsOnSliceLine - N.array([yxCenter]).transpose()).transpose() \
                               + yxCenter - [ty, tx]
                    ## Now interpolate the pixels in yx_input for each z section
                    yx_input = yx_input.transpose()
                    for z in range(self.doc.nz): # abondon to use tz
                        algined = nd.map_coordinates(arr[z], yx_input, order=1)
                        retSlice[axisSliceNormalTo][w][z] = algined

                    del arr
        return retSlice

    def takeSlice2(self, axisSet=(0,1,2)):
        '''
        return the slice of the data array (of all wavelengths) defined by time ti and
        the axis this slice is normal to: 0 -- z; 1 -- y; 2 -- x.
        self.alignParams[i]: (tz, ty, tx, rot, mag)
        '''
        #t = self.doc.t
        nc = self.doc.nz / 2.
            
        retSlice = {}

        sliceIdx = [self.doc.z, self.doc.y, self.doc.x]

        # print 'takeSlice'
        for w in range(self.doc.nw):
            #tz, ty, tx, rot, magz, magy, magx = self.doc.alignParms[self.doc.t,w]

            for axisSliceNormalTo in axisSet: # axis 0,1,2
                shape = [self.doc.nz, self.doc.ny, self.doc.nx]
                shape.pop(axisSliceNormalTo) # projection shape
                retSlice.setdefault(axisSliceNormalTo, []).append(N.zeros(shape, self.doc.dtype)) # canvas

                ## a x-y slice
                if axisSliceNormalTo == 0:
                    whichSlice = sliceIdx[axisSliceNormalTo] - \
                                 self.doc.alignParms[self.doc.t,w, axisSliceNormalTo]
                    whichSlice = round((whichSlice - nc) + nc)
                    if 0 > whichSlice:
                        whichSlice = 0
                    elif whichSlice >= self.doc.nz:
                        whichSlice = self.doc.nz-1
                    retSlice[axisSliceNormalTo][w][:] = self.doc.get3DArr(w=w, zs=[whichSlice], t=self.doc.t)[0]

                else:
                    arr = self.doc.get3DArr(w=w, t=self.doc.t)
                    whichSlice = sliceIdx[axisSliceNormalTo] - \
                                 self.doc.alignParms[self.doc.t,w, axisSliceNormalTo]
                    retSlice[axisSliceNormalTo][w][:] = N.squeeze( arr.take([whichSlice], axisSliceNormalTo) ) ## HACK [:] to keep the shape of retSlice[w]
                ## otherwise, need to use affine matrix and interpolation to calculate the slice
                    del arr

        return retSlice

    def getROI(self):
        """
        return (z0,y0,x0), (z1,y1,x1)
        """
        start = self.doc.roi_start
        stop = self.doc.roi_start + self.doc.roi_size
        return tuple(start), tuple(stop)
        #return [slice(*ss) for ss in zip(start, stop)]

class MyFrame(wx.Frame):

    def __init__(self, title='ND viewer', parent=None, id=wx.ID_ANY, size=FRAMESIZE):
        global viewers
        #frame = wx.Frame()
        #wx.Panel.__init__(self, frame, -1)
        
        wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE | wx.BORDER_SUNKEN, size=wx.Size(size[0], size[1]))

        
        # constants
        self.dir = ''
        self.parent = parent
        self.title = self.GetTitle()

        # some attributes

        self.auiManager = aui.AuiManager()
        self.auiManager.SetManagedWindow(self)

        # Notebook
        self.auiManager.AddPane(self.CreateNotebook(), aui.AuiPaneInfo().CloseButton(False).CenterPane())
        #aui.EVT_AUINOTEBOOK_PAGE_CHANGED(self, -1, self.OnNotebookPageChange)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnNotebookPageChange, id=-1)

        self.auiManager.Update()

        self.vid = len(viewers)
        viewers.append(self)

        #wx.GetTopLevelParent(parent).Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_CLOSE, self.onclose)

    def __del__(self):
        self.onclose()

    def onclose(self, evt=None):
        global viewers
        viewers[self.vid] = None

        if evt:
            evt.GetEventObject().Destroy()
        
    def CreateNotebook(self):
        
        #self.imEditWindows = aui.AuiNotebook(self, wx.ID_ANY, style=aui.AUI_NB_DEFAULT_STYLE | aui.AUI_NB_WINDOWLIST_BUTTON | aui.AUI_NB_TAB_FIXED_WIDTH)
        self.imEditWindows = ImEditWindow(self, wx.ID_ANY, style=aui.AUI_NB_DEFAULT_STYLE | aui.AUI_NB_WINDOWLIST_BUTTON | aui.AUI_NB_TAB_FIXED_WIDTH)

        self.imEditWindows.SetNormalFont(wx.NORMAL_FONT)
        self.imEditWindows.SetSelectedFont(wx.NORMAL_FONT)  # do not use bold for selected tab
        self.imEditWindows.SetMeasuringFont(wx.NORMAL_FONT)
        return self.imEditWindows

    def OnNotebookPageChange(self, event):
        new_page = event.GetSelection()
        page = self.imEditWindows.GetPage(new_page)
        if page.doc:
            self.SetTitle('   '.join((self.title, page.doc.file)))

    def getImage(self, idx=0):
        return self.imEditWindows.GetPage(idx).doc

class ImEditWindow(aui.AuiNotebook):
    def __init__(self, *args, **kwds):
        aui.AuiNotebook.__init__(self, *args, **kwds)
        self.setMaxPages()

    def setMaxPages(self, defval=30):
        self.maxpages = defval
        

    def addPage(self, *args, **kwds):
        #print self.GetPageCount(), self.maxpages
        if self.GetPageCount() >= self.maxpages:
            #print 'called'
            #page = self.GetPage(0)
            #page.Close()
            self.DeletePage(0)
            
        self.AddPage(*args, **kwds)
            
def main(fns, parent=None, useCropbox=viewer2.CROPBOX):
    """
    fn: a filename
    """
    initglut()
    
    frame = MyFrame(size=FRAMESIZE, parent=parent)
    frame.Show()

    if isinstance(fns, six.string_types) or not hasattr(fns, '__iter__') or hasattr(fns, 'shape'):
        fns = [fns]
    #elif type(fns) == tuple:
    #    fns = fn
    #else:
    #    raise ValueError

    for fn in fns:
        panel = ImagePanel(frame, fn, useCropbox=useCropbox)
        if isinstance(fn, six.string_types):
            name = os.path.basename(fn)
        elif hasattr(fn, 'fn'):
            name = os.path.basename(fn.fn)
        else:
            name = 'array'
            #raise ValueError('file name is not found')
            
        frame.imEditWindows.addPage(panel, name, select=True)
    return frame

if __name__ == '__main__':
    from Priithon import PriApp
    PriApp._maybeExecMain()
