"""
the container of
(2d) viewer, histogram and "z"-slider

common base class for single-color and multi-color version
"""

__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import wx
import numpy as N
import fftfuncs as F  # for mockNDarray
import weakref
import PriConfig

##thrd   import  threading
##thrd   ccc=0
##thrd   workerInterval = 1000 # 500 #msec
##thrd   # Define notification event for thread completion
##thrd   EVT_RESULT_ID = wx.NewId()

Menu_AutoHistSec0 = 3310
Menu_AutoHistSec1 = 3311
Menu_AutoHistSec2 = 3312

Menu_WheelWhatMenu = 2013
Menu_ScrollIncrementMenu = 1013 ## scrollIncrL
scrollIncrL= [ 1,2,3,5,6,10,20,30,50,60,100,200,"..." ]

Menu_LeftClickMenu = 1070
Menu_SaveND   = wx.NewId()
Menu_AssignND = wx.NewId()



class spvCommon:
    def __init__(self):
        self.doOnSecChanged = [] # (zTuple, self)
        self.showFloatCoordsWhenZoomingIn = PriConfig.viewerShowFloatCoordsWhenZoomingIn
        self.keyShortcutTable = {}

        
    def doScroll(self, axis, dir):
        """ dir is -1 OR +1
        """
        if self.zndim < 1:
            return
        force1Incr = False
        if axis >= self.zndim:
            axis = self.zndim-1
            force1Incr = True
            
        zz = self.zsec[axis]
        if axis != 0 or force1Incr:
            zz += dir
            if dir < 0:
                if zz <0:
                    zz = self.zshape[axis]-1
            else:
                if zz >=self.zshape[axis]:
                    zz = 0
        else: # scroll by self.scrollIncr
            zz += self.scrollIncr * dir
            if dir < 0:
                if zz <0:
                    ni = self.zshape[axis] // self.scrollIncr
                    niTInc = ni * self.scrollIncr
                    zz += niTInc + self.scrollIncr
                    if zz >= self.zshape[axis]:
                        zz -= self.scrollIncr
            else:
                if zz >=self.zshape[axis]:
                    zz = zz % self.scrollIncr #20051115:  0
                
        self.setSlider(zz, axis)

    def OnWheelWhat(self, ev):
        what = ev.GetId() - (Menu_WheelWhatMenu+1)
        if what < self.zndim:
            def OnWheel(evt):
                rot = evt.GetWheelRotation()      / 120. #HACK
                self.doScroll(axis=what, dir=rot)
            self.viewer.OnWheel = OnWheel
        else:
            self.viewer.OnWheel = self.vOnWheel_zoom
        wx.EVT_MOUSEWHEEL(self.viewer, self.viewer.OnWheel)

    def OnScrollIncr(self, ev):
        i = ev.GetId() - (Menu_ScrollIncrementMenu+1)
        self.scrollIncr = scrollIncrL[i]
        if type(self.scrollIncr) is type("ss") and self.scrollIncr[-3:] == '...':
            i= wx.GetNumberFromUser("scroll step increment:", 'step', "scroll step increment:", 10, 1, 1000)
            self.scrollIncr = i

    def OnMenuAutoHistSec(self, ev):
        self.autoHistEachSect = ev.GetId() - Menu_AutoHistSec0

    def OnMenuAssignND(self, ev=None):
        import usefulX as Y
        Y.assignNdArrToVarname(self.data, "Y.vd(%s)"%(self.id,))

    def OnZZSlider(self, event):
        i = event.GetId()-1001
        zz = event.GetInt()
        self.zsec[i] = zz
        if zz != self.zlast[i]:
            #self.doOnZchange( zz )
            zsecTuple = tuple(self.zsec)

            #section-wise gfx:  name=tuple(zsec)
            try:
                self.viewer.newGLListEnableByName(tuple(self.zlast), on=False, 
                                                  skipBlacklisted=True, refreshNow=False)
            except KeyError:
                pass
            try:
                self.viewer.newGLListEnableByName(zsecTuple, on=True, 
                                                  skipBlacklisted=True, refreshNow=False)
            except KeyError:
                pass

            self.helpNewData(doAutoscale=False, setupHistArr=True)#False)
            
            for f in self.doOnSecChanged:
                try:
                    f( zsecTuple, self )
                except:
                    if PriConfig.raiseEventHandlerExceptions:
                        raise
                    else:
                        import traceback, sys
                        print >>sys.stderr, " *** error in doOnSecChanged **"
                        traceback.print_exc()
                        print >>sys.stderr, " *** error in doOnSecChanged **"

            self.zlast[i] = zz
                
            
            
    def setSlider(self, z, zaxis=0):
        """zaxis specifies "which" zaxis should move to new value z
        """
        self.zsec[zaxis] = z
        self.zzslider[zaxis].SetValue(self.zsec[zaxis])
        e = wx.CommandEvent(wx.wxEVT_COMMAND_SLIDER_UPDATED, 1001+zaxis)
        e.SetInt( self.zsec[zaxis] )
        wx.PostEvent(self.zzslider[zaxis], e)
        #self.OnSlider(e)

        # #         e = wx.CommandEvent(wx.wxEVT_COMMAND_SLIDER_UPDATED, self.zzslider[zaxis].GetId())
        # #         e.SetInt(z)
        # #         #CHECK -- was commented out -- 2007-MDC put back in (win)
        # #         self.OnSlider(e)
        # #         #wx.PostEvent(self.zzslider[zaxis], e)
        # #         self.zzslider[zaxis].SetValue(z)



    def OnMenuSaveND(self, ev=None):
        if self.data.dtype.type in (N.complex64, N.complex128):
            dat = self.dataCplx
            datX = abs(self.data) #CHECK 
        else:
            dat = datX = self.data

        from Priithon.all import Mrc, U, FN, Y
        fn = FN(1,0)
        if not fn:
            return
        if fn[-4:] in [ ".mrc",  ".dat" ]:
            Mrc.save(dat, fn)
        elif fn[-5:] in [ ".fits" ]:
            U.saveFits(dat, fn)
        else:
            # save as sequence of image files
            # if fn does contain something like '%0d' auto-insert '_%0NNd'
            #      with NN to just fit the needed number of digits
            datX = datX.view()
            datX.shape = (-1,)+datX.shape[-2:]
            U.saveImg8_seq(datX, fn)
        Y.shellMessage("### Y.vd(%d) saved to '%s'\n"%(self.id, fn))




    def normalizeKeyShortcutTable(self):
        for k in self.keyShortcutTable.keys():
            if isinstance(k[1], basestring):
                if k[1].islower():
                    new_k = (k[0], ord(k[1])-ord('a')+ord('A'))
                else: #if k[1].isupper():
                    new_k = (k[0], ord(k[1]))
                #else:   #note: there are keys like '0', '9'
                #    raise ValueError, "invalid shortcut key (%s)"%(k[1],)
                self.keyShortcutTable[new_k] = self.keyShortcutTable[k]
                del self.keyShortcutTable[k]

    def installKeyCommands(self, frame):
        from usefulX import iterChildrenTree
        for p in iterChildrenTree(frame):
            p.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

    def OnKeyDown(self, evt):
        #modifiers = ""
        #for mod, ch in [(evt.ControlDown(), 'C'),
        #                (evt.AltDown(),     'A'),
        #                (evt.ShiftDown(),   'S'),
        #                (evt.MetaDown(),    'M')]:
        #    if mod:
        #        modifiers += ch
        #    else:
        #        modifiers += '-'
        #
        #print modifiers, evt.GetModifiers(), evt.GetKeyCode(), evt.GetRawKeyCode(), evt.GetUnicodeKey(), evt.GetX(), evt.GetY()
        
        f = self.keyShortcutTable.get((evt.GetModifiers(), evt.GetKeyCode()))
        if f is not None:
            f()
        else:
            evt.Skip() # this this maybe be always called ! CHECK

    
    def setDefaultKeyShortcuts(self):
        self.keyShortcutTable[ 0, wx.WXK_NUMPAD_MULTIPLY] = self.OnAutoHistScale
        self.keyShortcutTable[ 0, 'h'] = self.OnAutoHistScale
        self.keyShortcutTable[ 0, 'l' ] = self.OnHistLog
        self.keyShortcutTable[ 0, 'f' ] = self.OnViewFFT  # CHECK view2
        self.keyShortcutTable[ wx.MOD_SHIFT, 'f' ] = self.OnViewFFTInv # CHECK view2
        self.keyShortcutTable[ 0, 'a' ] = self.OnViewCplxAsAbs # CHECK view2
        self.keyShortcutTable[ 0, 'p' ] = self.OnViewCplxAsPhase # CHECK view2
        self.keyShortcutTable[ 0, 'x' ] = self.OnViewFlipXZ
        self.keyShortcutTable[ 0, 'y' ] = self.OnViewFlipYZ
        self.keyShortcutTable[ 0, 'v' ] = self.OnViewMaxProj


        #self.keyShortcutTable[ 0, 'm' ] = self.OnViewVTK
        #self.keyShortcutTable[ 0, wx.WXK_F1 ] = self.OnShowPopupTransient

        # z-slider
        self.keyShortcutTable[ 0, wx.WXK_LEFT ] = lambda :self.doScroll(axis=0, dir=-1)
        self.keyShortcutTable[ 0, wx.WXK_RIGHT ]= lambda :self.doScroll(axis=0, dir=+1)
        self.keyShortcutTable[ 0, wx.WXK_UP ]   = lambda :self.doScroll(axis=1, dir=+1)
        self.keyShortcutTable[ 0, wx.WXK_DOWN ] = lambda :self.doScroll(axis=1, dir=-1)


        self.keyShortcutTable[ 0, 'c' ] = self.viewer.OnColor
        self.keyShortcutTable[ 0, 'o' ] = self.viewer.OnChgOrig
        self.keyShortcutTable[ 0, 'g' ] = self.viewer.setPixelGrid
        self.keyShortcutTable[ 0, 'b' ] = self.viewer.OnChgNoGfx

        # panning
        self.keyShortcutTable[ wx.MOD_CMD, wx.WXK_LEFT ] = self.viewer.quaterShiftOffsetLeft
        self.keyShortcutTable[ wx.MOD_CMD, wx.WXK_RIGHT ]= self.viewer.quaterShiftOffsetRight
        self.keyShortcutTable[ wx.MOD_CMD, wx.WXK_UP ]   = self.viewer.quaterShiftOffsetUp
        self.keyShortcutTable[ wx.MOD_CMD, wx.WXK_DOWN ] = self.viewer.quaterShiftOffsetDown
        self.keyShortcutTable[ wx.MOD_CMD|wx.MOD_SHIFT, wx.WXK_LEFT ] = lambda :self.viewer.doShift(-1,0)
        self.keyShortcutTable[ wx.MOD_CMD|wx.MOD_SHIFT, wx.WXK_RIGHT ]= lambda :self.viewer.doShift(+1,0)
        self.keyShortcutTable[ wx.MOD_CMD|wx.MOD_SHIFT, wx.WXK_UP ]   = lambda :self.viewer.doShift(0,+1)
        self.keyShortcutTable[ wx.MOD_CMD|wx.MOD_SHIFT, wx.WXK_DOWN ] = lambda :self.viewer.doShift(0,-1)

        # zooming
        self.keyShortcutTable[ 0, '0' ] = self.viewer.doReset
        self.keyShortcutTable[ 0, '9' ] = self.viewer.OnCenter
        self.keyShortcutTable[ 0, wx.WXK_HOME ] = self.viewer.OnCenter
        self.keyShortcutTable[ 0, wx.WXK_NEXT ] = self.viewer.OnZoomOut
        self.keyShortcutTable[ 0, wx.WXK_PRIOR] = self.viewer.OnZoomIn
        # self.keyShortcutTable[ 0, 'd' ] = lambda :self.viewer.zoom(2., absolute=False)
        # self.keyShortcutTable[ 0, 'h' ] = lambda :self.viewer.zoom(.5, absolute=False)
        self.keyShortcutTable[ 0, 'z' ] = lambda :self.viewer.zoom(2., absolute=False)
        self.keyShortcutTable[ 0, 'm' ] = lambda :self.viewer.zoom(.5, absolute=False)


        self.keyShortcutTable[ 0, 'r' ] = self.viewer.OnReload

        self.normalizeKeyShortcutTable()

