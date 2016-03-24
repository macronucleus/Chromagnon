#!/usr/bin/env priithon

import wx, wx.aui
from Priithon import histogram, useful as U

import viewer2
import glfunc as GL

import numpy as N
from PriCommon import guiFuncs as G ,microscope, imgfileIO, imgResample
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


def initglut():
    global GLUTINITED
    if not GLUTINITED:
        from OpenGL import GLUT
        GLUT.glutInit([])  ## in order to call Y.glutText()
        GLUTINITED = True

class ImagePanel(wx.Panel):
    viewCut   = False
    def __init__(self, parent, imFile=None, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize):
        wx.Panel.__init__(self, parent, id, pos, size, name='')

        # to make consistent with the older viewers
        self.parent = self
        
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self._perspectives = []

        
        ## self.doc contains all the information on the displayed image
        if isinstance(imFile, basestring):
            self.doc = imgfileIO.load(imFile)#aligner.Chromagnon(imFile)
        else:
            self.doc = imFile

        if self.doc:
            self.addImageXY()

    def addImageXY(self):
        ## draw viewer
        ## each dimension is assgined a number: 0 -- z; 1 -- y; 2 -- x
        ## each view has two dimensions (x-y view: (1,2); see below viewer2.GLViewer() calls) and
        ## an axis normal to it (x-y view: 0)

        self.viewers = [] # XY, XZ, ZY
        self.viewers.append(viewer2.GLViewer(self, dims=(1,2),
                                             style=wx.BORDER_SUNKEN,
                                             size=wx.Size(self.doc.nx, self.doc.ny)
                                             ))

        self._mgr.AddPane(self.viewers[0], wx.aui.AuiPaneInfo().Floatable(False).Name('XY').Caption("XY").BestSize((self.doc.nx, self.doc.ny)).CenterPane().Position(0))

        self.viewers[-1].setMyDoc(self.doc, self)

        imgs2view = self.takeSlice((0,))[0]
        
        for i, img in enumerate(imgs2view):
            self.viewers[-1].addImg(img, None)

            if hasattr(self.doc, 'alignParms'):
                alignParm = self.doc.alignParms[self.doc.t,i]
                self.viewers[-1].updateAlignParm(-1, alignParm)

        # sliders
        if self.doc.nz > 1 or self.doc.nt > 1:
            self.addZslider()
            ysize = int(self.doc.nz > 1) * 60 + int(self.doc.nt > 1) * 40
            ysize = max(self.doc.nz, ysize)
            self._mgr.AddPane(self.sliderPanel, wx.aui.AuiPaneInfo().Name('Sliders').Caption("Sliders").Right().Position(1).BestSize((200,ysize)).MinSize((200,ysize)))
                        
        # histogram
        self.recalcHist_todo_Set = set()

        self.initHists() # histogram/aligner panel
        self.setupHistArrL()
        self.recalcHistL(False)
        self.autoFitHistL()

        self._mgr.AddPane(self.histsPanel, wx.aui.AuiPaneInfo().Name('Histogram').Caption("HistoPanel").MaximizeButton(True).Right().Position(0).BestSize((200, self.doc.ny)).MinSize((200,50+70*self.doc.nw)))

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
        if viewToUpdate >= 0:
            if viewToUpdate  == 3:
                views2update = range(3)
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
        pps = self._mgr.GetAllPanes()
        if not any([pp.name == 'ZY' for pp in pps]) or not self.orthogonal_toggle.GetValue():
            for v in self.viewers:
                v.updateGlList(None, RefreshNow)
                v.useHair = False
                v.dragSide = 0
        else:
                #if self.orthogonal_toggle.GetValue():
            for v in self.viewers:
                g = GL.graphix_slicelines(v)
                v.updateGlList([ g.GLfunc ], RefreshNow)
                v.useHair = True
                #else:
                #for v in self.viewers:
                #v.updateGlList(None, RefreshNow)
                #v.useHair = False
                #v.dragSide = 0
        #self.doc.setIndices()


    def IsCut(self):
        return self.viewCut

    def updateCropboxEdit(self):
        pass

    def addZslider(self):
        self.sliderPanel = wx.Panel(self, -1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.sliderPanel.SetSizer(sizer)
        
        # z slider
        if self.doc.nz > 1:
            topSizer = G.newSpaceV(sizer)

            label, self.zSliderBox = G.makeTxtBox(self.sliderPanel, topSizer, 'Z', defValue=str(self.doc.z), tip='enter z idx', style=wx.TE_PROCESS_ENTER)

            self.zSliderBox.Bind(wx.EVT_TEXT_ENTER, self.OnZSliderBox)

            G.makeTxt(self.sliderPanel, topSizer, r'/'+str(self.doc.nz-1))

            self.zSlider = wx.Slider(self.sliderPanel, wx.ID_ANY, self.doc.z, 0, 
                                     self.doc.nz-1,
                                     size=wx.Size(150,-1),
                                     style = wx.SL_HORIZONTAL | wx.SL_AUTOTICKS)#|wx.SL_LABELS | wx.SL_AUTOTICKS)

            topSizer.Add(self.zSlider, 6, wx.ALL|wx.ALIGN_LEFT, 2)
            wx.EVT_SLIDER(self, self.zSlider.GetId(), self.OnZSlider)

            #/n
            box = G.newSpaceV(sizer)

            self.orthogonal_toggle = G.makeToggleButton(self.sliderPanel, box, self.onOrthogonal, title='Orthogonal projections')

        
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
            wx.EVT_SLIDER(self, self.tSlider.GetId(), self.OnTSlider)


    def onOrthogonal(self, evt=None):
        """
        transform to the orthogonal viewer
        """
        if self.orthogonal_toggle.GetValue() and len(self.viewers) == 1:
            self._mgr.GetPane('Sliders').Left().Position(1)
            self.OnAddX()
            self.OnAddY()
            self.OnAddLastViewer()
        elif self.orthogonal_toggle.GetValue():
            self._mgr.GetPane('Sliders').Left().Position(1)
            self._mgr.GetPane('XZ').Show()
            self._mgr.GetPane('ZY').Show()
            self._mgr.Update()
        else:
            self._mgr.GetPane('Sliders').Right().Position(1)
            self._mgr.GetPane('ZY').Hide()
            self._mgr.GetPane('XZ').Hide()
            self._mgr.Update()
            self.updateGLGraphics(0, True)
        
    def OnAddY(self, evt=None):
        """
        add ZY viewer
        """
        pps = self._mgr.GetAllPanes()
        if not any([pp.name == 'ZY' for pp in pps]):
            self.viewers.append(viewer2.GLViewer(self, dims=(1,0),
                                                 style=wx.BORDER_SUNKEN,
                                                 size=wx.Size(self.doc.nz, self.doc.ny)
                                                 ))
            self._mgr.AddPane(self.viewers[-1], wx.aui.AuiPaneInfo().Floatable(False).Name('ZY').Caption("ZY").Left().Position(0).BestSize((self.doc.nz, self.doc.ny)))#.Dockable(False).Top())
            self.viewers[-1].setMyDoc(self.doc, self)
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
                                                 size=wx.Size(self.doc.nx, self.doc.nz)
                                                 ))
            self._mgr.AddPane(self.viewers[-1], wx.aui.AuiPaneInfo().Floatable(False).Name('XZ').Caption("XZ").BestSize((self.doc.nz, self.doc.ny)).CenterPane().Position(1))
            self.viewers[-1].setMyDoc(self.doc, self)
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
                wave = self.doc.hdr.wave[i]
                self.setColor(i, wave, False)

        self.autoFitHistL()
        self._mgr.Update()

        
    def initHists(self):
        ''' Initialize the histogram/aligner panel, and a bunch of empty lists;
        define HistogramCanvas class;s doOnBrace() and doOnMouse() behaviors
        '''
        self.histsPanel = wx.Panel(self, -1)

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
            wave = self.doc.hdr.wave[i]#mrcIO.getWaveFromHdr(self.doc.hdr, i)
            self.hist_show[i] = True

            box = G.newSpaceV(sizer)
            
            self.hist_toggleButton[i] = G.makeToggleButton(self.histsPanel, box, self.OnHistToggleButton, title=str(wave), size=(40,-1))
            self.hist_toggleButton[i].Bind(wx.EVT_RIGHT_DOWN, 
                                           lambda ev: self.OnHistToggleButton(ev, i=i, mode="r"))
            self.hist_toggleButton[i].SetValue( self.hist_show[i] )

            self.intensity_label[i] = G.makeTxt(self.histsPanel, box, ' ')

            box = G.newSpaceV(sizer)
            
            self.hist[i] = histogram.HistogramCanvas(self.histsPanel, size=(200,30))#size)

            box.Add(self.hist[i])

            for ii,colName in enumerate(_rgbList_names):
                self.hist[i].menu.Insert(ii, _rgbList_menuIDs[ii], colName)
                self.hist[i].Bind(wx.EVT_MENU, self.OnHistColorChange, id=_rgbList_menuIDs[ii])

            self.hist[i].menu.InsertSeparator(ii+1)


            self.hist_toggleID2col[ self.hist_toggleButton[i].GetId() ] = i
            
            #/n
            box = G.newSpaceV(sizer)
            self.hist_label[i] = G.makeTxt(self.histsPanel, box, ' ')
            
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
                wave = self.doc.hdr.wave[i]
                self.setColor(i, wave, False)

        #/n/n
        box = G.newSpaceV(sizer)
        G.makeTxt(self.histsPanel, box, ' ') # dummy
        box = G.newSpaceV(sizer)
        self.xy_label = G.makeTxt(self.histsPanel, box, ' ')
                
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
        r, g, b = microscope.LUT(wavelength)
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
                    wave = self.doc.hdr.wave[ii]#mrcIO.getWaveFromHdr(self.doc.hdr, ii)
                    label = str(wave)
                    self.hist_toggleButton[ii].SetLabel(label)
                    r, g, b = self.hist[ii].m_histGlRGB
                    [v.setColor(ii, r, g, b, RefreshNow=ii==self.doc.nw-1) for v in self.viewers]
                    [v.setVisibility(ii, self.hist_show[ii], RefreshNow=ii==self.doc.nw-1) for v in self.viewers]
                self.hist_singleChannelMode = None
            else:                                # active grey mode for color i only
                for ii in range(self.doc.nw):
                    if ii == i:
                        wave = self.doc.hdr.wave[ii]#mrcIO.getWaveFromHdr(self.doc.hdr, ii)
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
                    wave = self.doc.hdr.wave[ii]#mrcIO.getWaveFromHdr(self.doc.hdr, ii)
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


        
    def OnZSliderBox(self, event):
        z = int(self.zSliderBox.GetValue())
        if z >= self.doc.nz:
            z = self.doc.nz - 1
        while z < 0:
            z = self.doc.nz + z
        self.set_zSlice(z)
        self.zSlider.SetValue(z)
     
    def OnZSlider(self, event):
        z = event.GetInt()
        self.set_zSlice(z)
        self.zSliderBox.SetValue(str(z))

    def set_zSlice(self, z):
        self.doc.z = int(z)
        self.updateGLGraphics(range(len(self.viewers)))
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
        self.updateGLGraphics(range(len(self.viewers)))
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

class MyFrame(wx.Frame):

    def __init__(self, title='Chromagnon viewer', parent=None, id=wx.ID_ANY, size=FRAMESIZE):
        wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE | wx.BORDER_SUNKEN, size=wx.Size(size[0], size[1]))

        # constants
        self.dir = ''
        self.parent = parent

        # some attributes
        self.auiManager = wx.aui.AuiManager()
        self.auiManager.SetManagedWindow(self)

        # Notebook
        self.auiManager.AddPane(self.CreateNotebook(), wx.aui.AuiPaneInfo().CloseButton(False).CenterPane())

        self.auiManager.Update()

    def CreateNotebook(self):
        
        self.imEditWindows = wx.aui.AuiNotebook(self, wx.ID_ANY, style=wx.aui.AUI_NB_DEFAULT_STYLE | wx.aui.AUI_NB_WINDOWLIST_BUTTON | wx.aui.AUI_NB_TAB_FIXED_WIDTH)

        self.imEditWindows.SetNormalFont(wx.NORMAL_FONT)
        self.imEditWindows.SetSelectedFont(wx.NORMAL_FONT)  # do not use bold for selected tab
        self.imEditWindows.SetMeasuringFont(wx.NORMAL_FONT)
        return self.imEditWindows

def main(*fn):
    """
    fn: a filename
    """
    frame = MyFrame(size=FRAMESIZE, parent=None)
    frame.Show()

    if isinstance(fn, basestring):
        fns = [fn]
    elif type(fn) == tuple:
        fns = fn
    else:
        raise ValueError

    for fn in fns:
        panel = ImagePanel(frame, fn)
        frame.imEditWindows.AddPage(panel, 'name', select=True)
    return frame

if __name__ is '__main__':
    from Priithon import PriApp
    PriApp._maybeExecMain()
