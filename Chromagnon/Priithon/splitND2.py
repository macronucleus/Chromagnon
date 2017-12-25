"""provides the parent frame of Priithon's ND 2d-section-viewer"""

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

from splitNDcommon import *
Menu_histColor = wx.NewId()
Menu_viewInGrayViewer = wx.NewId()
Menu_autoFit_all = wx.NewId()

_rgbList = [
    (1,0,0),
    (0,1,0),
    (0,0,1),
    (1,1,0),
    (0,1,1),
    (1,0,1),
    (1,1,1),
    ]
_rgbList_names = ['red','green','blue', 
                  'yellow', 'cyan', 'magenta', 
                  'grey']
_rgbList_menuIDs = [wx.NewId() for iii in range(len(_rgbList))] 

def _rgbDefaultColor(i):
    return _rgbList[ i % len(_rgbList) ]

def run(img, colorAxis="smart", title=None, size=None, originLeftBottom=None, _scoopLevel=1): # just to not get a return value
    """img can be either an n-D image array (n >= 3)
          or a filename for a Fits or Mrc or jpg/gif/... file
          or a sequence of the above

       colorAxis is the "z"-axis without sliders 
          "smart" automagically defaults to "shortest" "z"-dimension
       """
    import os, usefulX as Y
    #     if type(img) in (tuple, list):
    #         imgList = img
    #         a = Y.load(imgList[0])
    #         aa = N.empty((len(imgList),)+a.shape, a.dtype)
    #         aa[0] = a
    #         for i in range(1, len(imgList)):
    #             aa[i] = Y.load(imgList[i])
    #         run(aa, 0, title, size, originLeftBottom, _scoopLevel=2)
    #         return
    
    if type(img) is list:
        for i in img:
            run(i, colorAxis, title, size, originLeftBottom, _scoopLevel=2)
        return
    if type(img) is tuple:
        import fftfuncs as F
        imgs = tuple(( Y.load(i) if isinstance(i, basestring) else i for i in img ))
        moa = F.mockNDarray(*imgs)
        run(moa, 0, title, size, originLeftBottom, _scoopLevel=2)
        return

    #"filename"
    if isinstance(img, basestring) and os.path.isfile(img):
        fn=img
        p,f = os.path.split(os.path.abspath(fn))
        #print fn, (fn[:6] == "_thmb_"), (fn[-4:] == ".jpg")
        if f[:6] == "_thmb_" and f[-4:] == ".jpg":
            f = os.path.join(p, f[6:-4])
            if os.path.isfile( f ):
                fn = f

        a = Y.load(fn) #20051213
        if a is None:
            return
        #20060824 CHECK  if originLeftBottom is None and \
        #20060824 CHECK     hasattr(a, '_originLeftBottom'):
        #20060824 CHECK      originLeftBottom = a._originLeftBottom
        if title is None:
            import os.path
            title = "<%s>" % os.path.basename(fn)
        return run(a, colorAxis, title, size, originLeftBottom=originLeftBottom, _scoopLevel=2)
    if title is None:
        # python expression: evaluate this string and use it it as title !
        if type(img)==str: # title
            try:
                import sys
                fr = sys._getframe(_scoopLevel)
                locs = fr.f_locals
                globs = fr.f_globals
                a = eval(img, globs, locs)
                img,title = a, img
            except ValueError: # HACK: stack not deep enough
                pass
        #eval("Y.view(%s, '%s', %s)" % (img, img, size), locs) # HACK

        else:     # see if img has a name in the parent dictionary - use that as title
            try:
                import sys
                fr = sys._getframe(_scoopLevel)
                vars = fr.f_globals.copy()
                vars.update( fr.f_locals )
                for v in vars.keys():
                    if vars[v] is img:
                        title = v
                        break
            except ValueError: # stack not deep enough
                pass

            
    spv(img, colorAxis, title, size, originLeftBottom)
    
class spv(spvCommon):
    """ self.hist_arr != None ONLY IF NOT self.img.type() in (na.UInt8, na.Int16, na.UInt16)
        then also   self.hist_max   and   self.hist_min  is set to min,max of number type !!
        and:  self.hist_range = self.hist_max - self.hist_min
        then  call:
        S.histogram(self.img, self.hist_min, self.hist_max, self.hist_arr)
        self.hist.setHist(self.hist_arr, self.hist_min, self.hist_max)

        
        otherwise call   self.recalcHist()
        this _should_ be done from worker thread !?

        """



    def __init__(self, data, colorAxis=-3, title='', size=None,
                 originLeftBottom=None, parent=None, frameParent=None):
        """
        splitter window for multi-color viewerer
        combines a "topBox" - zslider, OnMouse info,
        a viewer window
        and a set histogram windows (one for each color)

        if parent is None: makes a new frame with "smart" title and given size
        """
        spvCommon.__init__(self)
        if not isinstance(data, F.mockNDarray):
            data = N.asanyarray(data) # 20060720 - numpy arrays don't have ndim attribute
        if min(data.shape) < 1:
            raise ValueError, "data shape contains zeros (%s)"% (data.shape,)

        while data.ndim < 3:
            data.shape = (1,) + data.shape
            #raise "multi-color viewer needs 3+D data"

        try:
            _1checkIt = repr(data)   # protect against crash from ""error: copy2bytes: access beyond buffer""
            del _1checkIt
        except:
            raise

        self.dataOrig = data

        if colorAxis=='smart':
            nonXYshape = list(data.shape[:-2])

            # use shortest "z-dimension" as color - use smaller axisIndex if two are of same length
            notShort = 1+ max(nonXYshape) # use this to have   axes of length 1  ignored
            nonXYshape = map(lambda x:  x>1 and x or notShort, nonXYshape) # ignore axes of length 1
            colorAxis = nonXYshape.index( min(nonXYshape) )

        if colorAxis < 0:
            colorAxis += data.ndim
        if colorAxis < data.ndim - 3:
            self.data=data.transpose(*tuple(range(colorAxis) + \
                                      range(colorAxis+1,data.ndim-2)+\
                                      [colorAxis,data.ndim-2,data.ndim-1] ))
        elif colorAxis == data.ndim - 2:
            self.data=data.transpose(*tuple(range(data.ndim-3) + [colorAxis, data.ndim-3, data.ndim-1] ))

        elif colorAxis == data.ndim - 1:
            self.data=data.transpose(*tuple(range(data.ndim-3) + [colorAxis, data.ndim-3, data.ndim-2] ))
        else:
            self.data=data

        # now data[...,colorAxis,yAxis,xAxis] 

        #self.nColors= self.data.shape[colorAxis]
        self.ColorAxisOrig = colorAxis
        self.nColors= self.data.shape[-3]
        if self.nColors > PriConfig.viewer2maxNumColors:
            raise ValueError, "You should not use more than %d colors (%s)"%(PriConfig.viewer2maxNumColors,self.nColors)


        self.zshape= self.data.shape[:-3]
        self.zndim = self.data.ndim-3
        self.zsec  = [0] * self.zndim
        self.zlast = [0]*self.zndim # remember - for checking if update needed

        self.recalcHist_todo_Set = set()
        from usefulX import viewers
        n = len( viewers )
        viewers.append( self )
        self.id = n

        if parent is None:
            parent=self.makeFrame(size, title, frameParent)
            needShow=True
        else:
            needShow=False

        self.splitter = wx.SplitterWindow(parent, -1, style=wx.SP_LIVE_UPDATE|wx.SP_3DSASH)
    
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.upperPanel = wx.Panel(self.splitter, -1)
        self.upperPanel.SetSizer(sizer)
        self.upperPanel.SetAutoLayout(True)

        self.boxAtTop = wx.BoxSizer(wx.HORIZONTAL)

        self.putZSlidersIntoTopBox(self.upperPanel, self.boxAtTop) #20070621 skipAxes = [colorAxis])
        sizer.AddSizer(self.boxAtTop, 0, wx.GROW|wx.ALL, 2)
        
        import viewer2
        v = viewer2.GLViewer(self.upperPanel, originLeftBottom=originLeftBottom)
        self.viewer = v
        self.viewer.my_spv    = weakref.proxy( self ) # CHECK 20070823


        v.m_menu.Append(Menu_autoFit_all, "auto zoom + scale all")
        wx.EVT_MENU(wx.GetTopLevelParent(parent), Menu_autoFit_all,      self.OnAutoFitAll)

        if self.zndim > 0:
            self.addZsubMenu()

        self.fixupViewer()
        #20080818 self.addHistPanel(self.splitter)
        self.histsPanel = wx.Panel(self.splitter, -1)
        self.initHists()

    
        self.viewer.Bind(wx.EVT_IDLE, self.OnIdle)

        #self.hist_min, self.hist_min, self.hist_avg, self.hist_dev

        sizer.Add(v, 1,  wx.GROW|wx.ALL, 2)
        
        #CHECK - this might conflict with other onClose handlers of parent !! 
        wx.EVT_CLOSE(wx.GetTopLevelParent(parent), self.onClose)

        if needShow:
            parent.Show()
            self.installKeyCommands(parent)
            self.keyShortcutTable[ wx.MOD_CMD, ord('W') ] = parent.Close

        self.setDefaultKeyShortcuts()

        self.autoHistEachSect = 0
        self.scrollIncr = 1             
        self.noHistUpdate = 0 # used for debugging speed issues
        
        self.splitter.SetMinimumPaneSize(5)
        self.splitter.SetSashGravity(1.0)
        self.splitter.SplitHorizontally(self.upperPanel, self.histsPanel, -40*self.nColors)

        self.imgL =  self.data[tuple(self.zsec)]        
        v.addImgL(self.imgL) #, smin=0, smax=0, alpha=1., interp=0)
        for i in range( self.nColors ):
            rgb = _rgbDefaultColor(i)
            self.setColor(i, rgb, RefreshNow=(i==self.nColors-1))

        self.setupHistArrL()
        self.recalcHistL(postponeToIdle=False)
        self.autoFitHistL()
        
        from Priithon import fileDropPopup
        self.viewer.SetDropTarget( fileDropPopup.FileDropTarget(self.viewer) )
        
#         if self.downSizeToFitWindow:
#             fac = 1./1.189207115002721 # >>> 2 ** (1./4)
#             #v.m_scale *= .05 # fac
#             s=max(self.data.shape[-2:])
#             while v.m_scale * s > 600:
#                 v.m_scale *= fac
#        v.center()
        


    def onClose(self, ev=None):
        #print "debug: splitND2::onClose() ", ev and ev.GetEventObject()
        try:
            del self.data
            del self.imgL
        except:
            #would block closing:: if PriConfig.raiseEventHandlerExceptions:
            #    raise
            if 1: #else:
                import traceback, sys
                print >>sys.stderr, "  ### ### cought exception for debugging:  #### " 
                traceback.print_exc()
                print >>sys.stderr, "  ### ### cought exception for debugging:  #### " 
            
        from usefulX import viewers
        try:
            viewers[ self.id ] = None
        except:
            #would block closing:: if PriConfig.raiseEventHandlerExceptions:
            #    raise
            if 1: #else:
                import traceback, sys
                print >>sys.stderr, "  ### ### cought exception for debugging:  #### " 
                traceback.print_exc()
                print >>sys.stderr, "  ### ### cought exception for debugging:  #### " 

        if ev:
            ev.GetEventObject().Destroy()
        # import gc
        # wx.CallAfter( gc.collect )

    # FIXME size=(width+20,height+100+40*self.nColors))
    def makeFrame(self, size, title, frameParent=None):
        """
        create frame
        if dataOrig has "Mrc" attribute, append "<filename> to given title
        """
        self.downSizeToFitWindow=False
        ### size = (400,400)
        if size is None:
            height,width = self.data.shape[-2:] #20051128 self.img.shape
            if height//2 == (width-1):  ## real_fft2d
                width = (width-1)*2
            if width>600 or height>600:
                width=height=600
                self.downSizeToFitWindow=True
#22             if self.nz > 1 and width<250: #HACK: minimum width to see z-slider
#22                 width = 250
        elif type(size) == int:
            width,height = size,size
        else:
            width,height = size
            
        if title is None:
            title=''
        if hasattr(self.dataOrig, 'Mrc'):
            if title !='':
                title += " "
            title += "<%s>" % self.dataOrig.Mrc.filename
        
        title2 = "%d) %s" %(self.id, title)
        frame = wx.Frame(frameParent, -1, title2, size=(width+20,height+100+40*self.nColors))
        from usefulX import shellMessage
        shellMessage("# window: %s\n"% title2)
        self.title  = title
        self.title2 = title2
        return frame

    def addZsubMenu(self):
        v = self.viewer
        '''1
            v.m_menu.AppendSeparator()
            v.m_menu.AppendRadioItem(Menu_AutoHistSec0, "autoHist off")
            v.m_menu.AppendRadioItem(Menu_AutoHistSec1, "autoHist viewer")
            v.m_menu.AppendRadioItem(Menu_AutoHistSec2, "autoHist viewer+histAutoZoom")

            wx.EVT_MENU(self.frame, Menu_AutoHistSec0,      self.OnMenuAutoHistSec)
            wx.EVT_MENU(self.frame, Menu_AutoHistSec1,      self.OnMenuAutoHistSec)
            wx.EVT_MENU(self.frame, Menu_AutoHistSec2,      self.OnMenuAutoHistSec) 

            v.m_menu.AppendSeparator()

            self.vOnWheel_zoom = self.viewer.OnWheel
            menuSub0 = wx.Menu()
            menuSub0.Append(Menu_WheelWhatMenu+1+self.zndim, "zoom")
            for i in range(self.zndim):
                menuSub0.Append(Menu_WheelWhatMenu+1+i, "scroll axis %d" % i)
            v.m_menu.AppendMenu(Menu_WheelWhatMenu, "mouse wheel does", menuSub0)
            for i in range(self.zndim+1):
                wx.EVT_MENU(self.frame, Menu_WheelWhatMenu+1+i,self.OnWheelWhat) 

            menuSub1 = wx.Menu()
            for i in range(len(scrollIncrL)):
                menuSub1.Append(Menu_ScrollIncrementMenu+1+i, "%3s" % scrollIncrL[i])
            v.m_menu.AppendMenu(Menu_ScrollIncrementMenu, "scroll increment", menuSub1)
            for i in range(len(scrollIncrL)):
                wx.EVT_MENU(self.frame, Menu_ScrollIncrementMenu+1+i,self.OnScrollIncr) 

        menuSub2 = wx.Menu()
        from Priithon.all import Y
        self.plot_avgBandSize=1
        self.plot_s='-+'
        def OnChProWi(ev):
            i= wx.GetNumberFromUser("each line profile gets averaged over a band of given width",
                                    'width:', "profile averaging width:",
                                    self.plot_avgBandSize, 1, 1000)
            self.plot_avgBandSize=i
            #Y.vLeftClickNone(self.id) # fixme: would be nice if
            #done!?
            from Priithon import usefulX
            usefulX._plotprofile_avgSize = self.plot_avgBandSize
        def OnSelectSubRegion(ev):
            from viewerRubberbandMode import viewerRubberbandMode
            rub = viewerRubberbandMode(id=self.id,
                                       rubberWhat="box",
                                       color=(0, 255, 0),
                                       clearGfxWhenDone=1)
            
            def doThisAlsoOnDone():
                y0,x0 = rub.yx0
                y1,x1 = rub.yx1
                Y.view( self.data[..., y0:y1+1,x0:x1+1],
                        title="%s [...,%d:%d,%d:%d]" % (self.title, y0,y1+1,x0,x1+1) )
            rub.doThisAlsoOnDone = doThisAlsoOnDone
                
        left_list = [('horizontal profile',
                      lambda ev: Y.vLeftClickHorizProfile(self.id, self.plot_avgBandSize, self.plot_s)),
                     ('vertical profile',
                      lambda ev: Y.vLeftClickVertProfile(self.id, self.plot_avgBandSize, self.plot_s)),
                     ('any-line-profile',
                      lambda ev: Y.vLeftClickLineProfile(self.id, abscissa='line', s=self.plot_s)),
                     ('any-line-profile over x',
                      lambda ev: Y.vLeftClickLineProfile(self.id, abscissa='x', s=self.plot_s)),
                     ('any-line-profile over y',
                      lambda ev: Y.vLeftClickLineProfile(self.id, abscissa='y', s=self.plot_s)),
                     ('Z-profile',
                      lambda ev: Y.vLeftClickZProfile(self.id, self.plot_avgBandSize, self.plot_s)),
                     ('line measure',
                      lambda ev: Y.vLeftClickLineMeasure(self.id)),
                     ('triangle measure',
                      lambda ev: Y.vLeftClickTriangleMeasure(self.id)),
                     ('mark-cross',
                      lambda ev: Y.vLeftClickMarks(self.id, callFn=None)),
                     ('<nothing>',
                      lambda ev: Y.vLeftClickNone(self.id)),
                     ('<clear graphics>',
                      lambda ev: Y.vClearGraphics(self.id)),
                     ('<change profile "width"',
                      lambda ev: OnChProWi(ev)),
                     ('select-view xy-sub-region',
                      lambda ev: OnSelectSubRegion(ev)),
                     ]
        for i in range(len(left_list)):
            itemId = Menu_LeftClickMenu+1+i
            menuSub2.Append(itemId, "%s" % left_list[i][0])
            wx.EVT_MENU(self.frame, itemId, left_list[i][1])
        v.m_menu.AppendMenu(Menu_LeftClickMenu, "on left click ...", menuSub2)
        

        v.m_menu_save.Append(Menu_SaveND,    "save nd data stack")
        v.m_menu_save.Append(Menu_AssignND,  "assign nd data stack to var name")
            
        wx.EVT_MENU(self.frame, Menu_SaveND,      self.OnMenuSaveND)
        wx.EVT_MENU(self.frame, Menu_AssignND,      self.OnMenuAssignND)
        
        dt = MyFileDropTarget(self)
        v.SetDropTarget(dt)
        1'''

    def fixupViewer(self):
        """fix OnMouse event , and OnReload() menu
        """
        v = self.viewer
        def splitND2_onMouse(x,y, ev):
            yy,xx = int(round(y)), int(round(x)) # NEW 20080701:  in new coord system, integer pixel coord go through the center of pixel
            def strForPixVal(i,y,x):
                ny,nx = v.m_imgList[i][2].shape
                if 0<=yy<ny and 0<=xx<nx:
                    val = v.m_imgList[i][2][yy,xx]
                    #if val.dtype.type in (N.uint8, N.int16, N.uint16, N.int32):
                    #    return "%d"%(val,)
                    if N.issubdtype(val.dtype, N.integer) or val.dtype == bool:
                        return "%d"%(val,)
                    elif N.abs(val) > .02:
                        return "%7.2f"  %(val,)
                    else:
                        return "%7.2e"  %(val,)
                else:
                    return "---"
            try:
                vs = ' '.join([strForPixVal(i,y,x) for i in range(len(v.m_imgList)) if self.hist_show[i]])
            except IndexError:
                vs = "?"
            #if self.data.dtype.type in (N.uint8, N.int16, N.uint16, N.int32):
            #    vs = "%6d"  %(xyEffVal,)
            #else:
            #    if N.abs(xyEffVal) > .02:
            #        vs = "%7.2f"  %(xyEffVal,)
            #    else:
            #        vs = "%7.2e"  %(xyEffVal,)
            #    #self.label.SetLabel("xy: %3d %3d  val: %7.2f"%(x,y, xyEffVal))#self.img[y,x]))
            '''
            if v.m_scale != 1:
                self.label.SetLabel("%.2fx yx: %3d %3d val: %s"%(v.m_scale, y,x, vs))
                #self.label.SetLabel("%.2fx yx: %3d %3d"%(v.m_scale, y,x))
            else:
                self.label.SetLabel("yx: %3d %3d val: %s"%(y,x,vs))
            '''
            if v.m_scale > 1 and self.showFloatCoordsWhenZoomingIn:
                self.label.SetLabel("(%.1fx yx: %5.1f %5.1f  val: %s"%(v.m_scale, y,x, vs))
            elif v.m_scale != 1:
                self.label.SetLabel("(%.1fx yx: %3d %3d  val: %s"%(v.m_scale, yy,xx, vs))
            else:
                self.label.SetLabel("yx: %3d %3d  val: %s"%(yy,xx, vs))

        v.doOnMouse.append( splitND2_onMouse )

        def fff(event=None):
            self.helpNewData()
            ###self.frame.Refresh()

        v.OnReload = fff
        import viewer2
        wx.EVT_MENU(v, viewer2.Menu_Reload,      fff)
        self.OnReload = fff

    #20080818 def addHistPanel(self, parent):
    #20080818     self.histsPanel = wx.Panel(parent, -1)
    #20080818     self.initHists()

    def initHists(self):
        v = self.viewer
        histsSizer   = wx.BoxSizer(wx.VERTICAL)
        self.histsPanel.SetSizer(histsSizer)
        self.histsPanel.SetAutoLayout(True)

        import histogram
        self.hist      = [None]*self.nColors
        self.hist_arr  = [None]*self.nColors
        self.hist_min  = [None]*self.nColors
        self.hist_max  = [None]*self.nColors
        self.hist_range= [None]*self.nColors
        self.hist_toggleButton  = [None]*self.nColors
        self.hist_show = [None]*self.nColors          # not really hist - but "show wavelength ''at all''"
        self.mmms      = [None]*self.nColors
        v.hist4colmap  = [None]*self.nColors

        self.hist_singleChannelMode = None
        #self.hist_colorMenuID2col = {}
        self.hist_toggleID2col    = {}

        for i in range( self.nColors ):
            self.hist_show[i] = True
            self.hist[i] = histogram.HistogramCanvas(self.histsPanel)
            #20070525-black_on_black self.hist[i].SetCursor(wx.CROSS_CURSOR)
            
            def onDClick(ev, i=i): # force local/non-bound variable i
                self.OnHistColorChange(ev)#i=i)
            self.hist[i].Bind(wx.EVT_LEFT_DCLICK, onDClick)

            histsCheckSizer   = wx.BoxSizer(wx.HORIZONTAL)
            toggleID = wx.NewId()
            label = "%d"% i
            self.hist_toggleButton[i] = wx.ToggleButton(self.histsPanel, toggleID, label, size=(20,-1))
            self.hist_toggleButton[i].SetValue( self.hist_show[i] )
            histsCheckSizer.Add(self.hist_toggleButton[i], 0, wx.GROW|wx.ALL, 4)
            histsCheckSizer.Add(self.hist[i], 1, wx.GROW|wx.ALL, 1)

            histsSizer.Add(histsCheckSizer, 1, wx.GROW|wx.ALL, 0)
            #20070621 histsSizer.Add(self.hist[i], 1, wx.GROW|wx.ALL, 2)

            
            #Menu_Color = wx.NewId()
            for iii,colName in enumerate(_rgbList_names):
                self.hist[i].menu.Insert(iii, _rgbList_menuIDs[iii], colName)
                self.hist[i].Bind(wx.EVT_MENU, self.OnHistColorChange, id=_rgbList_menuIDs[iii])

            self.hist[i].menu.InsertSeparator(iii+1)
            self.hist[i].menu.Insert(iii+2, Menu_viewInGrayViewer, "view() this channel separetely")
            self.hist[i].Bind(wx.EVT_MENU, lambda ev,i=i: self.OnViewInGrayViewer(ev, i=i)  , id=Menu_viewInGrayViewer)
            self.hist[i].menu.InsertSeparator(iii+3)
            


            self.hist_toggleID2col[ toggleID ] = i
            self.hist_toggleButton[i].Bind(wx.EVT_TOGGLEBUTTON, self.OnHistToggleButton)
            self.hist_toggleButton[i].Bind(wx.EVT_RIGHT_DOWN, 
                                           lambda ev: self.OnHistToggleButton(ev, i=i, mode="r"))

            def splitND2_onMouseHist(xEff, ev, ii=i): # ii with a new objectID - nested scope !!
                h = ev.GetEventObject()
                l,r =  h.leftBrace,  h.rightBrace
                img = self.data[ ...,i,:,:] # 20080925: introduced img instead of just using 'self.data' to support (inhomogeneous) mockArrays
                if img.dtype.type in (N.uint8, N.int16, N.uint16, N.int32):
                    self.label.SetLabel("I: %6.0f  l/r: %6.0f %6.0f"  %(xEff,l,r))
                else:
                    self.label.SetLabel("I: %7.2f  l/r: %7.2f %7.2f"%(xEff,l,r))
            self.hist[i].doOnMouse.append( splitND2_onMouseHist )
            v.hist4colmap[i] = self.hist[i]
            # TODO FIXME 20080815 hist colomap does not reset when nColors change with viewInViewer2 print "DEBUG: v.hist4colmap[i] = self.hist[i]"
            def splitND2_onBrace(s, ii=i): # ii with a new objectID - nested scope !!
                l,r = s.leftBrace, s.rightBrace
                try:
                    self.viewer.changeHistScale(ii, l,r)
                except:
                    pass
            self.hist[i].doOnBrace.append( splitND2_onBrace )
            

        
    def putZSlidersIntoTopBox(self, parent, boxSizer, skipAxes=[]):
        [si.GetWindow().Destroy() for si in boxSizer.GetChildren()] # needed with Y.viewInViewer

        if type(skipAxes) is type(1):
            skipAxes = [skipAxes]

        self.zzslider = [None]*self.zndim
        for i in range(self.zndim-1,-1,-1):
            if i in skipAxes:
                continue
            self.zzslider[i] = wx.Slider(parent, 1001+i, self.zsec[i], 0, self.zshape[i]-1,
                               wx.DefaultPosition, wx.DefaultSize,
                               #wx.SL_VERTICAL
                               wx.SL_HORIZONTAL
                               | wx.SL_AUTOTICKS | wx.SL_LABELS )
            if self.zshape[i] > 1:
                self.zzslider[i].SetTickFreq(5, 1)
                ##boxSizer.Add(vslider, 1, wx.EXPAND)
                boxSizer.Insert(0, self.zzslider[i], 1, wx.EXPAND)
                wx.EVT_SLIDER(parent, self.zzslider[i].GetId(), self.OnZZSlider)
            else: # still good to create the slider - just to no have special handling
                # self.zzslider[i].Show(0) # 
                boxSizer.Insert(0, self.zzslider[i], 0, 0)
        if self.zndim == 0:
            label = wx.StaticText(parent, -1, "")
            #label.SetHelpText("This is the help text for the label")
            boxSizer.Add(label, 0, wx.GROW|wx.ALL, 2)

            
        self.label = wx.StaticText(parent, -1, "----move mouse over image----") # HACK find better way to reserve space to have "val: 1234" always visible 
    
        boxSizer.Add(self.label, 0, wx.GROW|wx.ALL, 2)
        boxSizer.Layout()
        parent.Layout()

    def OnAutoHistScale(self, event=77777):
        for i in range( self.nColors ):        
            #CHECK mi,ma = U.mm( self.img[0] )
            self.hist[i].autoFit(amin=self.mmms[i][0], amax=self.mmms[i][1])
    def OnViewFFT(self, event=77777):
        import fftfuncs as F
        if self.data.dtype.type in (N.complex64, N.complex128):
            f = F.fft2d(self.data)
            #f[ ... , 0,0] = 0. # force DC to zero to ease scaling ...
            run(f, title='cFFT2d of %d'%self.id, _scoopLevel=2)
        else:
            f = F.rfft2d(self.data)
            f[ ... , 0,0] = 0. # force DC to zero to ease scaling ...
            run(f, title='rFFT2d of %d'%self.id, _scoopLevel=2)
#   def On88(self, event):
#       import fftfuncs as F
# #         if self.dataIsCplx:
# #             f = F.fft2d(self.dataCplx)
# #             run(f, title='cFFT2d of %d'%self.id, _scoopLevel=2)
# #         else:
#       f = F.irfft2d(self.data)
#       run(f, title='irFFT2d of %d'%self.id, _scoopLevel=2)
    def OnViewFFTInv(self, event=77777):
        import fftfuncs as F
        if self.data.dtype.type in (N.complex64, N.complex128):
            f = F.irfft2d(self.data)
        else:
            wx.Bell()
            return
        #    f = F.irfft2d(self.data)
        run(f, title='irFFT2d of %d'%self.id, _scoopLevel=2)
    def OnViewCplxAsAbs(self, event=77777):
        if not self.data.dtype.type in (N.complex64, N.complex128)\
               or self.viewer.m_viewComplexAsAbsNotPhase:
            wx.Bell()
            return
        self.viewer.m_viewComplexAsAbsNotPhase = True
        ####self.data = N.abs(self.dataCplx)
        self.helpNewData()
                
    def OnViewCplxAsPhase(self, event=77777):
        if not self.data.dtype.type in (N.complex64, N.complex128)\
               or self.viewer.m_viewComplexAsAbsNotPhase == False:
            wx.Bell()
            return
        self.viewer.m_viewComplexAsAbsNotPhase = False
        #import useful as U
        #self.data = U.phase(self.dataCplx)
        self.helpNewData()
    def OnViewFlipXZ(self, event=77777):
        import fftfuncs as F
        if self.data.dtype.type in (N.complex64, N.complex128):
            print "TODO: cplx "
        #20070821 - HACK - WORKAROUND for BusError -- run(F.getXZview(self.data, zaxis=0), title='X-Z of %d'%self.id, _scoopLevel=2)
        run(F.getXZview(self.data, zaxis=0).copy(), title='X-Z of %d'%self.id, _scoopLevel=2)
        from usefulX import vHistSettings
        vHistSettings(self.id,-1)
    def OnViewFlipYZ(self, event=77777):
        import fftfuncs as F
        if self.data.dtype.type in (N.complex64, N.complex128):
            print "TODO: cplx "
        run(F.getYZview(self.data, zaxis=0), title='Y-Z of %d'%self.id, _scoopLevel=2)
        from usefulX import vHistSettings
        vHistSettings(self.id,-1)
    def OnViewMaxProj(self, event=77777):
        import useful as U
        if self.data.dtype.type in (N.complex64, N.complex128):
            print "TODO: cplx "
        run(U.project(self.data), title='proj of %d'%self.id, _scoopLevel=2)
        from usefulX import vHistSettings
        vHistSettings(self.id,-1)
        
    def OnAutoFitAll(self, ev):
        for ii in range(self.nColors):
            self.hist[ii].autoFit()
        

    def OnViewInGrayViewer(self, ev=None, i=0):
        from splitND import run as view
        view(self.data[...,i,:,:], title="view() of col %d in viewer %s" %(i, self.title2))
    def OnHistToggleButton(self, ev=None, i=0, mode=None):
        if ev is not None:
            # print ev.GetId(), ev.GetEventObject()
            i = self.hist_toggleID2col[ ev.GetId() ]
            self.hist_show[i] = self.hist_toggleButton[i].GetValue() # 1-self.hist_show[i]

        # 'r': go "singleCHannelMode" -- show only channel i using grey scale, hide others
        if mode == 'r':
            if self.hist_singleChannelMode == i: # switch back to normal
                for ii in range(self.nColors):
                    self.hist_toggleButton[ii].SetLabel('%d'%ii)
                    self.viewer.setColor(ii, self.hist[ii].m_histGlRGB, RefreshNow=ii==self.nColors-1)
                self.hist_singleChannelMode = None
            else:                                # active grey mode for color i only
                for ii in range(self.nColors):
                    if ii == i:
                        self.hist_toggleButton[ii].SetLabel('%d'%ii)
                        self.viewer.setColor(ii, 1,1,1, RefreshNow=ii==self.nColors-1)
                    else:
                        self.hist_toggleButton[ii].SetLabel('--')
                        self.viewer.setColor(ii, 0,0,0, RefreshNow=ii==self.nColors-1)
                self.hist_singleChannelMode = i
        # other mode: show all color channels (when hist_show[i] is true)
        else:
            if self.hist_singleChannelMode is not None: # switch back to normal
                for ii in range(self.nColors):
                    self.hist_toggleButton[ii].SetLabel('%d'%ii)
                    if  self.hist_show[ii]:
                        rgb = self.hist[ii].m_histGlRGB
                    else:
                        rgb = 0,0,0
                    self.viewer.setColor(ii, rgb, RefreshNow=ii==self.nColors-1)
            else:
                if self.hist_show[i]:
                    self.viewer.setColor(i, self.hist[i].m_histGlRGB, RefreshNow=1)
                else:
                    self.viewer.setColor(i, 0,0,0, RefreshNow=1)
       
        
    def OnHistColorChange(self, ev=None):  # FIXME separe dclick and menu-selection handlers 
        evobj = ev.GetEventObject()
        # double click
        if   evobj in self.hist: 
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
            id = ev.GetId()
            rgb = _rgbList[ _rgbList_menuIDs.index(id) ]

        self.setColor(i, rgb, RefreshNow=1)

    def setColor(self, i, r_or_RBG,g=None,b=None, RefreshNow=1):
        if g is None:
            r_or_RBG,g,b = r_or_RBG
        r = r_or_RBG
        #         try:
        #             if len(RGB) != 3:
        #                 raise "x"
        #         except:
        #             raise "RGB needs to be a sequence of length 3"
        self.hist[i].m_histGlRGB=(r,g,b)
        if RefreshNow:
            self.hist[i].Refresh(0)
        self.viewer.setColor(i, r,g,b, RefreshNow)
        
    def helpNewData(self, doAutoscale=True, setupHistArr=True):
        """doAutoscale gets ORed with self.autoHistEachSect == 2
        """
        self.imgL =  self.data[tuple(self.zsec)]
#         imgArrL = self.imgL
#         for i in range(len(imgArrL)):
#             self.viewer.setImage(i, imgArrL[i])

        self.viewer.setImageL( self.imgL )
        #debug self.viewer.setImage(0, self.imgL[0] )
        
        #print "debug1:", self.mmms
        #CHECK
        for i in range( self.nColors ):
            if setupHistArr:
                self.setupHistArr(i)
            if not self.noHistUpdate: # used for debugging speed issues
                self.recalcHist(i, postponeToIdle=False)
            if doAutoscale or self.autoHistEachSect == 2:
                self.hist[i].autoFit(amin=self.mmms[i][0], amax=self.mmms[i][1])
                #h.setBraces(self.mmms[0], self.mmms[1])
                #h.fitXcontrast()
                #self.viewer.changeHistogramScaling(self.mmms[0],self.mmms[1])
            elif self.autoHistEachSect == 1:
                self.hist[i].setBraces(self.mmms[i][0], self.mmms[i][1])


            #print "debug2:", self.mmms

    def OnHistLog(self, ev=77777):
        for i in range( self.nColors ):
            self.hist[i].OnLog(ev)

    def setupHistArrL(self):
        for i in range( self.nColors ):
            self.setupHistArr(i)
            
    def setupHistArr(self,i):
        self.hist_arr[i] = None
        img = self.data[ tuple(self.zsec) ][i]
        
        if   img.dtype.type == N.uint8:
            self.hist_min[i], self.hist_max[i] = 0, (1<<8)-1
        elif img.dtype.type == N.uint16:
            self.hist_min[i], self.hist_max[i] = 0, (1<<16)-1
        elif img.dtype.type == N.int16:
            self.hist_min[i], self.hist_max[i] = 0-(1<<15), (1<<15)-1
        from Priithon.all import U
        self.hist[i].hist_min,self.hist[i].hist_max = U.mm(img)#self.img)
             
        if   img.dtype.type in (N.uint8, N.int16, N.uint16):
            self.hist_range[i] = self.hist_max[i] - self.hist_min[i] + 1
            self.hist_arr[i] = N.zeros(shape=self.hist_range[i], dtype=N.int32)
            
    def autoFitHistL(self):
        for i in range( self.nColors ):
            self.hist[i].autoFit(amin=self.mmms[i][0], amax=self.mmms[i][1])
       
    def OnIdle(self, event):
        #print "OnIdle", iiiii,  len(self.recalcHist_todo_Set)
        if len(self.recalcHist_todo_Set):
            i = self.recalcHist_todo_Set.pop()
            self.recalcHist(i, postponeToIdle=False)

    def recalcHistL(self, postponeToIdle):
        for i in range( self.nColors ):
            self.recalcHist(i, postponeToIdle)
    def recalcHist(self, i, postponeToIdle):
        if postponeToIdle:
            self.recalcHist_todo_Set.add(i)
            return
        img = self.data[ tuple(self.zsec) ][i]
        import useful as U
        mmms = U.mmms( img )
        self.mmms[i] = mmms
        #time import time
        #time x = time.clock()
        # print mmms

        import useful as U
        if self.hist_arr[i] is not None:
            #glSeb  import time
            #glSeb  x = time.clock()
            #         print U.mmms(self.hist_arr[i]),
            U.histogram(img, amin=self.hist_min[i], amax=self.hist_max[i], histArr=self.hist_arr[i])
            #         print U.mmms(self.hist_arr[i])
            self.hist[i].setHist(self.hist_arr[i], self.hist_min[i], self.hist_max[i])
            #glSeb  print "ms: %.2f"% ((time.clock()-x)*1000.0)
            ## FIXME  setHist needs to NOT alloc xArray every time !!!
        else:
            resolution = 10000
    
            a_h = U.histogram(img, resolution, mmms[0], mmms[1])

            self.hist[i].setHist(a_h, mmms[0], mmms[1])

