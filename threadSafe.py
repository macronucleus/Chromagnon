
import os, threading, exceptions, time, sys
import wx
import aligner, alignfuncs
from PriCommon import imgfileIO


###--- thread-safe gui -----------
# http://wiki.wxpython.org/LongRunningTasks

EVT_COLOR_ID = wx.NewId()
EVT_DONE_ID = wx.NewId()
EVT_VIEW_ID = wx.NewId()
EVT_ABORT_ID = wx.NewId()
EVT_ERROR_ID = wx.NewId()
EVT_ECHO_ID = wx.NewId()

# Dine events
def BindEvent(win, func, evt_id):
    win.Connect(-1, -1, evt_id, func)

class MyEvent(wx.PyEvent):
    def __init__(self, evt_id, data):
        wx.PyEvent.__init__(self)
        self.SetEventType(evt_id)
        self.data = data


###---- funcs to cancel execution ---------
# http://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread-in-python

class MyError(exceptions.Exception): pass

class ThreadWithExc(threading.Thread):
    '''A thread class that supports raising exception in the thread from
       another thread.
    '''
    def __init__(self, notify_obj, localChoice, fns, targets, parms, extrainfo={}):
        threading.Thread.__init__(self)
        self.notify_obj = notify_obj
        self.localChoice = localChoice
        self.fns = fns
        self.targets = targets
        self.parms = parms
        self.extrainfo = extrainfo
        
    def _get_my_tid(self):
        """determines this (self's) thread id

        CAREFUL : this function is executed in the context of the caller
        thread, to get the identity of the thread represented by this
        instance.
        """
        if not self.isAlive():
            raise threading.ThreadError("the thread is not active")

        # do we have it cached?
        if hasattr(self, "_thread_id"):
            return self._thread_id

        # no, look for it in the _active dict
        for tid, tobj in threading._active.items():
            if tobj is self:
                self._thread_id = tid
                return tid

    def echo(self, msg):
        wx.PostEvent(self.notify_obj, MyEvent(EVT_ECHO_ID, msg))
            
    def run(self):
        """
        This function execute the series of processes

        Since it uses GUI, this function uses several events to control GUI
        They are called by wx.PostEvent()
        """
        fns = self.fns
        targets = self.targets
        parms = self.parms

        # parameters
        cutout = parms[0]
        initGuess = parms[1]
        if initGuess and not os.path.isfile(initGuess):
            raise ValueError, 'The initial guess is not a valid Chromagnon file'
        local = parms[2]
        #cthre = parms[3]
        forceZmag = parms[3]
        maxShift = parms[4]
        nts = parms[5]
        
        saveAlignParam = True
        alignChannels = True
        alignTimeFrames = True

        outs0 = []
        outs = []
        doneref = []
        donetgt = []
        errs = []

        kwds = {}

        try:
            # calibration
            for index, fn in enumerate(fns):
                clk0 = time.clock()
                an = aligner.Chromagnon(fn)
                # calculation
                if an.img.hdr.type != aligner.IDTYPE:
                    
                    wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['ref', index, wx.RED]))

                    an = self.getAligner(fn, index, what='ref')
                    an.setForceZmag(forceZmag)
                    an.setMaxShift(maxShift)
                    
                    if initGuess:
                        an.loadParm(initGuess)
                        # mapyx should not be inherited...
                        an.mapyx = None
                    
                    if (alignChannels and nts[index] <= 1) or (alignChannels and not alignTimeFrames):
                        an.findBestChannel()
                        self.echo('Calculating...')
                        try:
                            an.findAlignParamWave()
                        except alignfuncs.AlignError: # in xcorr or else
                            self.echo('Calculation failed, skipping')
                            errs.append(index)
                            continue
                        if local in self.localChoice[1:]:
                            #an.setCCthreshold(cthre)
                            arr = an.findNonLinear2D()
                            del arr
                        if local in self.localChoice[2:]:
                            arr = an.findNonLinear3D()
                            del arr
                        
                    elif alignTimeFrames:
                        an.findBestTimeFrame()
                        an.findAlignParamTime(doWave=False)

                    fn = an.saveParm()
                    initGuess = fn
                        #fn = initGuess = an.saveParm()
                        #self.initGuess.SetValue(initGuess)
                        #self.initGuess.SetForegroundColour(wx.BLUE)
                    
                    currlist = None
                    clk1 = time.clock()
                    print 'Done seconds', (clk1-clk0)
                    
                    if local in self.localChoice[1:]:# and not wx.__version__.startswith('2.8'):
                        an.loadParm(fn)
                        nonlinear = imgfileIO.load(an.saveNonlinearImage())
                        wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [nonlinear]))
                        #wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [fn]))
                        #else:
                        #wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [fns[index], fn]))

                an.close()
                
                doneref.append(index)

                wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['ref', index, wx.BLUE]))
  
                if index < len(targets):
                    wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.RED]))
                    
                    target = targets[index]
                    an = self.getAligner(target, index, what='target')
                    an.loadParm(fn)

                    if cutout:
                        an.setRegionCutOut()

                    out = an.saveAlignedImage()
                    donetgt.append(index)

                    an.close()

                    wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.BLUE]))
                    
                    out = aligner.Chromagnon(out)
                    if type(out.img) == imgfileIO.MultiTiffReader:
                        einfo = self.extrainfo['target'][target]
                        out.setExtrainfo(einfo)
                        out.restoreDimFromExtra()
                        out.img.imgSequence = 2
                    wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [out]))


            # remaining target files use the last alignment file
            for index, target in enumerate(targets[len(fns):]):
                index += len(fns)
                wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.BLUE]))

                target = targets[index]
                an = self.getAligner(target, index, what='target')

                if len(fns):
                    an.loadParm(fn)

                if cutout:
                    an.setRegionCutOut()

                out = an.saveAlignedImage()
                donetgt.append(index)

                an.close()

                wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.BLUE]))


                out = aligner.Chromagnon(out)
                if type(out.img) == imgfileIO.MultiTiffReader:
                    einfo = self.extrainfo['target'][target]
                    out.setExtrainfo(einfo)
                    out.restoreDimFromExtra()
                    out.img.imgSequence = 2
                wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [out]))

        except MyError:
            wx.PostEvent(self.notify_obj, MyEvent(EVT_ABORT_ID, []))
        except:
            import traceback, sys
            #exc_type, exc_value, exc_traceback = sys.exc_info()
            #formatted = traceback.format_exception(exc_type, exc_value, exc_traceback) 
            wx.PostEvent(self.notify_obj, MyEvent(EVT_ERROR_ID, sys.exc_info()))#formatted]))
        else:
            wx.PostEvent(self.notify_obj, MyEvent(EVT_DONE_ID, [doneref, donetgt, errs]))

    def getAligner(self, fn, index, what='ref'):
        """
        what: 'ref' or 'tgt'
        """
        try:
            an = aligner.Chromagnon(fn)
        except IOError:
            raise IOError, 'filename %s, index %i, fns %s' % (fn, index, fns)

        if type(an.img) == imgfileIO.MultiTiffReader:
            einfo = self.extrainfo[what][fn]

            an.setExtrainfo(einfo)
            an.restoreDimFromExtra()


        an.setEchofunc(self.echo)
        return an

            
class GUImanager(wx.EvtHandler):
    def __init__(self, panel, name=None):
        """
        This class handles events
        """
        wx.EvtHandler.__init__(self)
        self.panel = panel
        self.name = name
        self.stopWithErr = False
        
        BindEvent(self, self.OnColor, EVT_COLOR_ID)

        BindEvent(self, self.OnView, EVT_VIEW_ID)

        BindEvent(self, self.OnDone, EVT_DONE_ID)

        BindEvent(self, self.OnCancel, EVT_ABORT_ID)
        
        BindEvent(self, self.OnError, EVT_ERROR_ID)

        BindEvent(self, self.OnEcho, EVT_ECHO_ID)

        self.OnStart()
        
    def OnStart(self):
        self.panel.goButton.SetLabel('Cancel')
        self.panel.buttonsEnable(0)
        #self.panel.label.SetLabel('processing, please wait ...')
        #self.panel.label.SetForegroundColour('red')
        self.echo('preparing, please wait ...')

    def OnColor(self, evt):
        if evt.data[0] == 'ref':
            listbox = self.panel.listRef
        else:
            listbox = self.panel.listTgt
        index = evt.data[1]
        color = evt.data[2]

        item = listbox.GetItem(index)
        item.SetTextColour(color)
        listbox.SetItem(item)
            
        self.currlist = self.panel.listRef
        self.item     = item


    def OnView(self, evt):
        #if len(evt.data) == 2:
        #    fn, chrom = evt.data
        #else:
        fn = evt.data[0]
            #    chrom = None

        if sys.platform == 'linux2': # or wx.__version__.startswith('2.8')??
            self.panel.view(fn)#, calib=chrom)
        else:
            wx.CallAfter(self.panel.view,fn)#, calib=chrom)
        wx.Yield()

    def OnDone(self, evt=None):

        if not self.stopWithErr:
            doneref, donetgt, err = evt.data
            doneref.sort(reverse=True)
            donetgt.sort(reverse=True)
            [self.panel.listRef.clearRaw(i) for i in doneref]
            [self.panel.listTgt.clearRaw(i) for i in donetgt]
                #self.panel.listRef.clearAll()
                #self.panel.listTgt.clearAll()
            
            #self.panel.label.SetLabel('Done!!')
            #self.panel.label.SetForegroundColour('black')
            if err:
                self.echo('Done with %i errs' % len(err), 'blue')
            else:
                self.echo('Done!!', 'blue')

            self.panel.goButton.Enable(0)
            #self.panel.viewButton.Enable(0)

        self.panel.goButton.SetValue(0)
        self.panel.goButton.SetLabel('Run all')
        self.panel.buttonsEnable(1)
        self.panel.OnItemSelected()

    def OnCancel(self, evt):
        if self.currlist:
            self.item.SetTextColour(wx.BLACK)
            self.currlist.SetItem(self.item)

            #self.panel.label.SetLabel('Cancelled')
            #self.panel.label.SetForegroundColour('black')
        self.echo('Cancelled', 'blue')

        self.stopWithErr = True

        self.OnDone()
        
    def OnError(self, evt):
        from Priithon import guiExceptionFrame
        self.panel.label.SetLabel('')
        self.panel.label.SetForegroundColour('black')
        self.stopWithErr = True
        f = guiExceptionFrame.MyFrame(*evt.data)
        self.OnDone()
        #raise evt.data[0], evt.data[1]

    def OnEcho(self, evt):
        self.echo(evt.data)
        
    def echo(self, msg, color='red'):
        self.panel.label.SetLabel(msg)
        self.panel.label.SetForegroundColour(color)
