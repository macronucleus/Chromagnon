#!/usr/bin/env priithon
from __future__ import print_function
import os
import six
import numpy as N
try:
    import imgio
except ImportError:
    from .. import imgio

# GUI
try:
    import wx
    import time
    from common import guiFuncs as G
    _wx = True
except ImportError:
    _wx = False

__version__ = 0.2

# Constants
#EXT='flat.ome.tif'
SUF = '_FLAT'
EXT = 'flat.tif'
IDTYPE = '101'

# functions
def is_flat(fn, check_img_to_open=True):
    check = False
    if fn.endswith(EXT):
        check = True
    elif check_img_to_open:
        rdr = imgio.Reader(fn)
        if hasattr(rdr, 'ome') and \
            rdr.ome.get_structured_annotation('idtype') == IDTYPE:
                check = True
        elif hasattr(rdr, 'metadata') and \
            rdr.metadata.get('idtype') == int(IDTYPE):
                check = True
        rdr.close()

    return check

def makeFlatConv(fn, out=None, suffix=''):
    """
    save a calibration file
    
    return output file name
    """
    if not out:
        out = os.path.splitext(fn)[0] + suffix + os.path.extsep + EXT
    elif not out.endswith(EXT):
        out = os.path.extsep.join(os.path.splitext(out)[0], EXT)

    h = imgio.Reader(fn)
    ntz = h.nz * h.nt
    
    o = imgio.Writer(out)
    o.setFromReader(h)
    o.setDim(nt=1, nz=1, dtype=N.float32)
    if out.endswith('.ome.tif'):
        o.ome.add_structured_annotation('idtype', IDTYPE)
    elif out.endswith('.tif'):
        o.metadata['idtype'] = IDTYPE
    
    for w in range(h.nw):
        canvas = N.zeros((h.nt, h.nz, h.ny, h.nx), N.float32)
        for t in range(h.nt):
            for z in range(h.nz):
                canvas[t,z] = h.getArr(w=w, t=t, z=z)
        arr = canvas.reshape((ntz, h.ny, h.nx)).mean(axis=0)
        arr = arr.mean() / arr
        o.writeArr(arr.astype(N.float32), w=w, z=0)
    o.close()
    h.close()

    return out

def flatConv(fn, flatFile, out=None, suffix=SUF):
    """
    save a normalized image

    return output filename
    """
    if not out:
        base, ext = os.path.splitext(fn)
        out = base + suffix + ext

    h = imgio.Reader(fn)

    f = imgio.Reader(flatFile)

    if h.shape != f.shape:
        from Priithon.all import F
    
    o = imgio.Writer(out)
    o.setFromReader(h)
    if out.endswith('ome.tif'):
        o.imgSequence = 0

    for w in range(h.nw):
        tgt_wave = h.getWaveFromIdx(w)

        if tgt_wave in f.wave:
            rw = h.getWaveIdx(tgt_wave)
            fs = f.getArr(w=rw, z=0)
            if h.shape != f.shape:
                fs = F.getPadded(fs, h.shape)
            
            for t in range(h.nt):
                for z in range(h.nz):
                    a = h.getArr(w=w, t=t, z=z)
                    b = a * fs
                    o.writeArr(b.astype(h.dtype), w=w, t=t, z=z)
        else:
            for t in range(h.nt):
                for z in range(h.nz):
                    a = h.getArr(w=w, t=t, z=z)
                    o.writeArr(a.astype(h.dtype), w=w, t=t, z=z)
    o.close()
    h.close()
    f.close()

    return out
                


## GUI
# Execute this function to start
def main(sysarg=None):

    fr = makeFrame(title="Flatfield")
    fr.Show()

    return fr

def makeFrame(title=''):
    frame = wx.Frame(None, title=title, size=(710,300))
    frame.panel = BatchPanel(frame)
    return frame

# GUI
if _wx:
    class BatchPanel(wx.Panel):
        def __init__(self, frame):
            """
            This panel is the main panel to do batch alignment
            """
            wx.Panel.__init__(self, frame)

            self.prevImgFns = []
            self.aui = None

            # draw / arrange
            sizer = wx.BoxSizer(wx.VERTICAL)
            self.SetSizer(sizer)

            # \n
            box = G.newSpaceV(sizer)

            label, self.fileNameTxt = G.makeTxtBox(self, box, 'Image files', defValue='', tip='image files to be flatfield', sizeX=400, sizeY=80, style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER)

            G.makeButton(self, box, self.OnChooseFile, title='Choose files', tip='', enable=True)


            # \n
            box = G.newSpaceV(sizer)

            label, self.calibNameTxt = G.makeTxtBox(self, box, 'Calibration files', defValue='', tip='calibration file', sizeX=300, sizeY=-1)

            G.makeButton(self, box, self.OnChooseCalib, title='Choose files', tip='', enable=True)
            G.makeButton(self, box, self.OnClearCalib, title='Clear', tip='', enable=True)


            # \n
            box = G.newSpaceV(sizer)

            self.goButton = G.makeButton(self, box, self.OnGo, title='Go', tip='', enable=False)

            self.label = G.makeTxt(self, box, ' ')

            ## new box
            sb, group1Box = G.newStaticBox(self, sizer, title='making a new calibration')

            # \n
            box = G.newSpaceV(group1Box)

            self.newCalibCb = G.makeCheck(self, box, "Make a new calibration --- separate images of different colors will be merged into a single file", tip='', defChecked=False)
            self.Bind(wx.EVT_CHECKBOX, self.checkGo, self.newCalibCb)


        def OnChooseFile(self, ev=None):
            dlg = G.FileSelectorDialog(self)#wx.FileDialog(self, 'Choose image files', style=wx.FD_MULTIPLE)
            if dlg.ShowModal() == wx.ID_OK:
                self.fns = dlg.GetPaths()
                fns = "\n".join(self.fns)
                self.fileNameTxt.SetValue(fns)

                self.checkGo()

        def OnChooseCalib(self, ev=None):
            dlg = G.FileSelectorDialog(self, wildcard='*')#wx.FileDialog(self, 'Choose a calibration file')#, wildcard=os.path.extsep.join(('*','py')))
            if dlg.ShowModal() == wx.ID_OK:
                flt = dlg.GetPath()
                self.calibNameTxt.SetValue(flt)
                self.checkGo()

        def OnClearCalib(self, evt=None):
            self.calibNameTxt.SetValue('')
            self.checkGo()

        def checkGo(self, evt=None):
            if (self.fileNameTxt.GetValue() and self.calibNameTxt.GetValue()) or \
                    (self.fileNameTxt.GetValue() and self.newCalibCb.GetValue()):
                self.goButton.Enable(1)
            else:
                self.goButton.Enable(0)

        def OnGo(self, ev=None):

            fns = self.fileNameTxt.GetValue().split('\n')
            if not fns:
                return

            self.label.SetLabel('processing, please wait ...')
            self.label.SetForegroundColour('red')
            wx.Yield()

            flt = self.calibNameTxt.GetValue()

            outs = []

            # calibration
            if fns and self.newCalibCb.GetValue():
                #outs = [makeFlatConv(fn) for fn in fns]
                for fn in fns:
                    out = makeFlatConv(fn)
                    self.view(out)
                    outs.append(out)

                self.calibNameTxt.SetValue(outs[-1])

            # making aligned images
            else:
                #outs = [flatConv(fn, flatFile=flt) for fn in fns]

                for fn in fns:
                    out = flatConv(fn, flatFile=flt)
                    self.view(out)
                    outs.append(out)

            bases = [os.path.basename(out) for out in outs]
            self.label.SetLabel('%s Done!! at %s' % (bases, time.strftime('%H:%M')))
            self.label.SetForegroundColour('black')
            self.fileNameTxt.SetValue('')

            self.goButton.Enable(0)
            self.newCalibCb.SetValue(0)


        def view(self, target):
            """
            view with viewer
            """
            import ndviewer
            import sys
            # prepare viewer
            if not self.aui:
                self.aui = ndviewer.main.MyFrame(parent=self)
                self.aui.Show()

            # draw
            if isinstance(target, six.string_types):
                newpanel = ndviewer.main.ImagePanel(self.aui, target)
                #newpanel = chromeditor.ChromagnonEditor(self.aui, target)

            if isinstance(target, six.string_types):
                name = os.path.basename(target)
            else:
                name = target.file
            if sys.platform in ('linux2', 'win32'):
                wx.CallAfter(self.aui.imEditWindows.AddPage, newpanel, name, select=True)
            else:
                self.aui.imEditWindows.AddPage(newpanel, name, select=True)
        

if __name__ == '__main__':
    import os, optparse, glob

    usage = r"""%prog imgFiles [options]"""
    p = optparse.OptionParser(usage=usage)
    p.add_option('--suffix', '-S', default=SUF,
                 help='suffix for the output file names (default inputfile + %s)' % SUF)
    p.add_option('--flatFile', '-F',
                 help='flatFielding file required for flatfielding')
    p.add_option('--make', '-m', action='store_true',
                 help='make calibration file (default OFF)')


    options, arguments = p.parse_args()

    if not arguments:
        from ..Priithon import PriApp
        PriApp._maybeExecMain()
    else:
        make = options.make
        del options.make

        fns = []
        for fn in arguments:
            fns += glob.glob(os.path.expandvars(os.path.expanduser(fn)))

        if make:
            outs = [makeFlatConv(fn, suffix=EXT) for fn in fns]
            if len(outs) > 1:
                out = os.path.commonprefix(outs) + EXT
                out = imgio.merge(outs, out, along='w')
                [os.remove(out) for out in outs]
            else:
                out = outs[0]
            print(out, ' saved')
        else:
            for fn in fns:
                out = flatConv(fn, **options.__dict__)
                print(out, ' done')
