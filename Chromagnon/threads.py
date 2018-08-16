from __future__ import print_function

import os, threading, time, sys
import wx

try:
    from PriCommon import flatConv
    from Priithon import fftmanager
except ImportError:
    from Chromagnon.PriCommon import flatConv
    from Chromagnon.Priithon import fftmanager

if sys.version_info.major == 2:
    import alignfuncs, chromformat, aligner
elif sys.version_info.major >= 3:
    try:
        from . import alignfuncs as af, chromformat, aligner
    except (ValueError, ImportError):
        from Chromagnon import alignfuncs as af, chromformat, aligner

# cross platform
if not getattr(__builtins__, "WindowsError", None):
    class WindowsError(OSError): pass

###--- thread-safe gui -----------
# http://wiki.wxpython.org/LongRunningTasks

EVT_COLOR_ID = wx.NewId()
EVT_DONE_ID = wx.NewId()
EVT_VIEW_ID = wx.NewId()
EVT_ABORT_ID = wx.NewId()
EVT_ERROR_ID = wx.NewId()
EVT_ECHO_ID = wx.NewId()
EVT_INITGUESS_ID = wx.NewId()
EVT_SETFLAT_ID = wx.NewId()
EVT_CLOSE_PAGE_ID = wx.NewId()
EVT_PROGRESS_ID = wx.NewId()

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

class MyError(Exception): pass

class ThreadWithExc(threading.Thread):
    '''A thread class that supports raising exception in the thread from
       another thread.
    '''
    def __init__(self, notify_obj, localChoice, fns, targets, parms):
        threading.Thread.__init__(self)
        self.notify_obj = notify_obj
        self.localChoice = localChoice
        self.fns = fns
        self.targets = targets
        self.parms = parms
        self.img_suffix = aligner.IMG_SUFFIX
        self.logh = open(os.path.join(os.path.dirname(fns[0]), 'Chromagnon.log'), 'a')
        
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
        for tid, tobj in list(threading._active.items()):
            if tobj is self:
                self._thread_id = tid
                return tid

    def run(self):
        """
        This function execute the series of processes

        Since it uses GUI, this function uses several events to control GUI
        They are called by wx.PostEvent()
        """
        OLD_SCIK = fftmanager.SCIK
        OLD_REIK = fftmanager.REIK
        fftmanager.SCIK = False
        fftmanager.REIK = False
        
        fns = self.fns
        targets = self.targets
        parms = self.parms

        # parameters
        cutout = parms[0]
        initGuess = parms[1]
        if initGuess and not os.path.isfile(initGuess):
            raise ValueError('The initial guess is not a valid Chromagnon file')
        local = parms[2]

        maxShift = parms[3]
        #zmag = parms[4]
        self.parm_suffix = parms[5]
        self.img_suffix = parms[6]
        nts = parms[7]
        self.img_ext = parms[8]
        min_pxls_yx = parms[9]
        
        saveAlignParam = True
        alignChannels = True
        alignTimeFrames = True

        outs0 = []
        outs = []
        doneref = []
        donetgt = []
        errs = []

        kwds = {}

        self.progress(0)

        try:
            # calibration
            for index, fn in enumerate(fns):
                #clk0 = time.clock()
                # calculation
                if not chromformat.is_chromagnon(fn):
                    tstf = time.strftime('%Y %b %d %H:%M:%S', time.localtime())
                    self.log('\n**Measuring shifts in %s at %s' % (os.path.basename(fn), tstf))
                    if self.notify_obj:
                        wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['ref', index, wx.RED]))

                    an = aligner.Chromagnon(fn)
                    an = self.getAligner(fn, index, what='ref')
                    #an.setZmagSwitch(zmag)
                    an.setMaxShift(maxShift)

                    pgen = self.progressValues(target=False, an=an, alignChannels=alignChannels, alignTimeFrames=alignTimeFrames, local=local)
                    an.setProgressfunc(pgen)
                    
                    if initGuess:
                        an.loadParm(initGuess)
                        # mapyx should not be inherited...
                        an.mapyx = None
                    
                    if (an.nw > 1 and an.nt == 1):
                        an.findBestChannel()
                        self.echo('Calculating channel alignment...')
                        
                        for t in range(an.nt):
                            try:
                                an.findAlignParamWave(t=t)
                            except af.AlignError: # in xcorr or else
                                self.echo('Calculation failed, skipping')
                                errs.append(index)
                                continue
                            
                            if local in self.localChoice[1:]:
                                an.findNonLinear2D(t=t, npxls=min_pxls_yx)
                                
                            if local in self.localChoice[2:]:
                                arr = an.findNonLinear3D(t=t, npxls=min_pxls_yx)
                                del arr
                            
                        
                    elif an.nt > 1:
                        self.echo('Calculating timelapse alignment...')
                        an.findBestChannel()
                        an.findBestTimeFrame(an.refwave)
                        
                        an.findAlignParamTime(doWave=False)

                    fn = an.saveParm()

                    currlist = None
                    #clk1 = time.clock()
                    #print('Done seconds', (clk1-clk0))

                    an.close()
                
                doneref.append(index)

                if self.notify_obj:
                    wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['ref', index, wx.BLUE]))
  
                if index < len(targets):
                    if self.notify_obj:
                        wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.RED]))
                    
                    target = targets[index]
                    tstf = time.strftime('%Y %b %d %H:%M:%S', time.gmtime())
                    self.log('\n**Applying to %s using %s at %s' % (os.path.basename(target), os.path.basename(fn), tstf))

                    an = self.getAligner(target, index, what='target')
                    
                    pgen = self.progressValues(target=True, an=an)
                    an.setProgressfunc(pgen)
                    self.progress(0)

                    an.loadParm(fn)
                    #if cutout:
                    an.setRegionCutOut(cutout)

                    out = an.saveAlignedImage()
                    donetgt.append(index)

                    an.close()

                    if self.notify_obj:
                        wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.BLUE]))
                    
                    if self.notify_obj:
                        wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [out]))
                        
                elif self.notify_obj:
                    wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [fn]))


            # remaining target files use the last alignment file
            for index, target in enumerate(targets[len(fns):]):
                index += len(fns)
                if self.notify_obj:
                    wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.BLUE]))

                target = targets[index]
                tstf = time.strftime('%Y %b %d %H:%M:%S', time.gmtime())
                if fns:
                    self.log('\n**Applying to %s using %s at %s' % (os.path.basename(target), os.path.basename(fn), tstf))
                else:
                    self.log('\n**Applying to %s at %s' % (os.path.basename(target), tstf))
                
                an = self.getAligner(target, index, what='target')
                pgen = self.progressValues(target=True, an=an)
                an.setProgressfunc(pgen)
                self.progress(0)

                if len(fns):
                    an.loadParm(fn)

                an.setRegionCutOut(cutout)

                out = an.saveAlignedImage()

                donetgt.append(index)

                an.close()

                if self.notify_obj:
                    wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.BLUE]))
                    #wx.PostEvent(self.notify_obj, MyEvent(EVT_PROGRESS_ID, [prange.pop(0)]))
                   # pgen.next()


                #out = aligner.Chromagnon(out)
                if self.notify_obj:
                    print('event view', out)
                    wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [out]))

        except MyError:
            if self.notify_obj:
                wx.PostEvent(self.notify_obj, MyEvent(EVT_ABORT_ID, []))
                wx.PostEvent(self.notify_obj, MyEvent(EVT_PROGRESS_ID, [0]))
            else:
                pass
        except:
            #exc_type, exc_value, exc_traceback = sys.exc_info()
            #formatted = traceback.format_exception(exc_type, exc_value, exc_traceback)
            if self.notify_obj:
                import traceback, sys
                wx.PostEvent(self.notify_obj, MyEvent(EVT_ERROR_ID, sys.exc_info()))#formatted]))
                #wx.PostEvent(self.notify_obj, MyEvent(EVT_PROGRESS_ID, [0]))
                self.progress(0)
            else:
                pass
        else:
            if self.notify_obj:
                wx.PostEvent(self.notify_obj, MyEvent(EVT_DONE_ID, [doneref, donetgt, errs]))
                #wx.PostEvent(self.notify_obj, MyEvent(EVT_PROGRESS_ID, [0]))
                self.progress(0)
            else:
                pass
        finally:
            self.logh.close()
        #bioformatsIO.uninit_javabridge()

        fftmanager.SCIK = OLD_SCIK
        fftmanager.REIK = OLD_REIK

    def getAligner(self, fn, index, what='ref'):
        """
        what: 'ref' or 'tgt'
        """
        try:
            an = aligner.Chromagnon(fn)
            an.setImgSuffix(self.img_suffix)
            an.setFileFormats(self.img_ext)
            an.setParmSuffix(self.parm_suffix)

        except IOError:
            raise IOError('filename %s, index %i, fns %s' % (fn, index, fns))


        an.setEchofunc(self.echo)
        return an

    
    def echo(self, msg, skip_notify=False):
        if self.notify_obj and not skip_notify:
            wx.PostEvent(self.notify_obj, MyEvent(EVT_ECHO_ID, msg))

        self.log(msg, prefix='    ')
        print(msg)

    def log(self, msg, prefix=''):
        self.logh.write('%s%s\n' % (prefix, msg))

    def progressValues(self, target=False, an=None, alignChannels=None, alignTimeFrames=None, local=None):
        import numpy as N
        
        prange = []
        if not target:
            if (alignChannels and an.nw > 1) or (alignChannels and not alignTimeFrames):
                prange += [0.5+0.5*round(an.nz/50)]
                prange += [1] * (an.nw-1) * an.nt
                prange += [round(an.nz/10) or 0.5] * (an.nw-1) * an.nt
                if local in self.localChoice[1:]:
                    prange += [1] * (an.nw-1) * an.nt

                #prange += [round(an.nz/25)] * an.nw * an.nt * ntargets
            elif an.nt > 1:
                prange += [0.5+0.5*round(an.nz/50)]

                prange += [(1+round(an.nz/10))]*(an.nt-1)

                #prange += [round(an.nz/25)] * an.nw * an.nt * ntargets

        else:
            prange += [1] * an.nw * an.nt
            
        pratio = 100 / sum(prange)
        prange = [p*pratio for p in prange]
        prange = list(N.cumsum(prange)) + [100]*100 # [100] for safety...
        #print 'prange', prange
        return self.progressGen(prange)

    def progressGen(self, vals):
        for val in vals:
            yield self.progress(val)

    def progress(self, val):
        if self.notify_obj:
            return wx.PostEvent(self.notify_obj, MyEvent(EVT_PROGRESS_ID, [val]))
        #print 'pval', val
            
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

        BindEvent(self, self.OnInitGuess, EVT_INITGUESS_ID)

        BindEvent(self, self.OnSetFlat, EVT_SETFLAT_ID)

        BindEvent(self, self.OnClosePage, EVT_CLOSE_PAGE_ID)

        BindEvent(self, self.OnProgress, EVT_PROGRESS_ID)


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
        #wx.Yield()

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
        try:
            from Priithon import guiExceptionFrame
        except ImportError:
            from Chromagnon.Priithon import guiExceptionFrame
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
        #print(msg)

    def OnInitGuess(self, evt):
        self.panel._setInitGuess(evt.data[0])

    
    def OnSetFlat(self, evt):
        self.panel._setFlat(evt.data)

    def OnClosePage(self, evt):
        self.panel.aui.imEditWindows.DeletePage(evt.data[0])

    def OnProgress(self, evt):
        self.panel.progress.SetValue(evt.data[0])


class ThreadFlat(ThreadWithExc):
    '''A thread class that supports raising exception in the thread from
       another thread.
    '''
    def __init__(self, notify_obj, localChoice, fns, targets, parms):
        ThreadWithExc.__init__(self, notify_obj, localChoice, fns, targets, parms)
        
        
    def run(self):
        """
        This function execute the series of processes

        Since it uses GUI, this function uses several events to control GUI
        They are called by wx.PostEvent()
        """
        fn = self.fns[0]
        targets = self.targets
        parms = self.parms

        
        saveAlignParam = True
        alignChannels = True
        alignTimeFrames = True

        outs0 = []
        outs = []
        doneref = []#0]
        donetgt = []
        errs = []

        kwds = {}

        try:
            # calibration
            #clk0 = time.clock()
            #an = aligner.Chromagnon(fn)
            #if not hasattr(an.img, 'hdr') or an.img.hdr.type != flatConv.IDTYPE:
            if not flatConv.is_flat(fn):
                #an = aligner.Chromagnon(fn)
                print('The file is not flat file')
                wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['ref', 0, wx.RED]))
                self.echo('Making a calibration file...')

                flatFile = flatConv.makeFlatConv(fn, suffix=parms[0])

                #out = aligner.Chromagnon(flatFile)
                wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [flatFile]))#out]))
                #clk1 = time.clock()
                #an.close()
            else:
                print('The file is a flat file')
                flatFile = fn
                
           # an.close()
            wx.PostEvent(self.notify_obj, MyEvent(EVT_SETFLAT_ID, [flatFile]))
            wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['ref', 0, wx.BLUE]))

            # remaining target files use the last alignment file
            for index, target in enumerate(targets):
                self.echo('Applying flat fielding to %s...' % os.path.basename(target))
                wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.RED]))

                base, ext = os.path.splitext(target)
                out = ''.join((base, parms[1], parms[2]))
                out = flatConv.flatConv(target, flatFile, out=out)#None, suffix=parms[1])

                wx.PostEvent(self.notify_obj, MyEvent(EVT_COLOR_ID, ['tgt', index, wx.BLUE]))

                out = aligner.Chromagnon(out)
                wx.PostEvent(self.notify_obj, MyEvent(EVT_VIEW_ID, [out]))
                donetgt.append(index)

        except MyError:
            wx.PostEvent(self.notify_obj, MyEvent(EVT_ABORT_ID, []))
        except:
            import traceback, sys
            #exc_type, exc_value, exc_traceback = sys.exc_info()
            #formatted = traceback.format_exception(exc_type, exc_value, exc_traceback) 
            wx.PostEvent(self.notify_obj, MyEvent(EVT_ERROR_ID, sys.exc_info()))#formatted]))
        else:
            wx.PostEvent(self.notify_obj, MyEvent(EVT_DONE_ID, [doneref, donetgt, errs]))

# from stopit
def async_raise(target_tid, exception):
    """Raises an asynchronous exception in another thread.
    Read http://docs.python.org/c-api/init.html#PyThreadState_SetAsyncExc
    for further enlightenments.

    :param target_tid: target thread identifier
    :param exception: Exception class to be raised in that thread
    """
    import ctypes
    # Ensuring and releasing GIL are useless since we're not in C
    # gil_state = ctypes.pythonapi.PyGILState_Ensure()
    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid),
                                                     ctypes.py_object(exception))
    # ctypes.pythonapi.PyGILState_Release(gil_state)
    if ret == 0:
        raise ValueError("Invalid thread ID {}".format(target_tid))
    elif ret > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(target_tid), None)
        raise SystemError("PyThreadState_SetAsyncExc failed")
