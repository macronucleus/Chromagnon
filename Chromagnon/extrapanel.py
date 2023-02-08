import os, sys
import wx
import numpy as N

try:
    from common import guiFuncs as G, commonfuncs as C, listbox
except (ValueError, ImportError):
    from Chromagnon.common import guiFuncs as G, commonfuncs as C, listbox
    

if sys.version_info.major == 2:
    import aligner, alignfuncs as af
elif sys.version_info.major >= 3:
    try:
        from . import aligner, alignfuncs as af, chromformat
    except (ValueError, ImportError):
        from Chromagnon import aligner, alignfuncs as af, chromformat


class ExtraDialog(wx.Dialog):
    def __init__(self, parent, listRef, confdic={}, outdir=None, refwave=None):


        self.outdir = None

        wx.Dialog.__init__(self, parent, id=-1, title='Extra parameters')
        self.parent = parent

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # -------- output dir -----------
        # \n
        box = G.newSpaceV(sizer)
        bb, box = G.newStaticBox(self, box, title='Output direcotry', size=wx.DefaultSize)

        self.outdir_cb = G.makeCheck(self, box, "same as input direcotry", tip='', defChecked=not(bool(outdir)), targetFunc=self.OnOutDirCb)
        self.chooseOurDirButton = G.makeButton(self, box, self.OnChooseOutDir, title='Choose', tip='', enable=not(self.outdir_cb.GetValue()))

        self.outdir = confdic.get('outdir', '')
        self.outdir_label = G.makeTxt(self, box, self.outdir)
        self.outdir_label.Enable(not(self.outdir_cb.GetValue()))

        # -------- reference wave -----------
        # \n
        box = G.newSpaceV(sizer)
        bb, box = G.newStaticBox(self, box, title='Reference wavelength', size=wx.DefaultSize)
        if listRef and listRef.columnkeys:

            waves1 = [list(listRef.getFile(index)[2].split(',')) for index in listRef.columnkeys]
            waves = set()
            for wave in waves1:
                [waves.add(w) for w in wave]
            waves = list(waves)
            waves.sort()

            if len(waves) > 1:
                # \n
                #box = G.newSpaceV(sizer)
                #bb, box = G.newStaticBox(self, box, title='Reference wavelength', size=wx.DefaultSize)
                if refwave is not None and refwave not in waves:
                    refwave = None
                self.refwave_cb = G.makeCheck(self, box, "auto", tip='', defChecked=not(bool(refwave)), targetFunc=self.OnRefWaveCb)
                label, self.refwave_choice = G.makeListChoice(self, box, '', waves, defValue=refwave or waves[0], tip='Reference wavelength that does not move', targetFunc=self.OnRefWaveChoice)
                self.refwave_choice.Enable(not(self.refwave_cb.GetValue()))

                self.refwave_label = G.makeTxt(self, box, refwave or 'auto')
                self.refwave_label.Enable(not(self.refwave_cb.GetValue()))

        # -------- z accur -----------
        # \n
        box = G.newSpaceV(sizer)
        bb, box = G.newStaticBox(self, box, title='Z-accuracy', size=wx.DefaultSize)
        self.doZ_cb = G.makeCheck(self, box, "align Z", tip='Uncheck if Z axis alignment is not desired', defChecked=True)#bool(confdic.get('doZ', True)))
        
        accurChoice = [str(i) for i in aligner.ACCUR_CHOICE]
        label, self.accurListChoice = G.makeListChoice(self, box, 'Iteration of 3D phase correlation', accurChoice, defValue=confdic.get('accur', accurChoice[0]))

        # -------- max shift -----------
        # \n
        box = G.newSpaceV(sizer)
        bb, box = G.newStaticBox(self, box, title='Maximum shift the channels are possibly misaligned', size=wx.DefaultSize)
        label, self.maxshift_text = G.makeTxtBox(self, box, 'Shift (um)', defValue=confdic.get('max_shift', str(af.MAX_SHIFT)), tip='Maximum shift the channels are possibly misaligned', sizeX=40)

        # --------- Do rotation for time series ------
        # \n
        box = G.newSpaceV(sizer)
        bb, box = G.newStaticBox(self, box, title='Time series alignment', size=wx.DefaultSize)
        self.dorot4time_cb = G.makeCheck(self, box, "Calculate rotation", tip='By default translation in XYZ is examined. If this check box is checked, rotation in addition to translation is aligned as well', defChecked=True)#bool(confdic.get('dorot4time', True)))
        
        # -------- what to do for time series --------
        # \n
        box = G.newSpaceV(sizer)
        bb, box = G.newStaticBox(self, box, title='Time series with mulitple channels', size=wx.DefaultSize)
        if listRef and listRef.columnkeys:

            nt = max([int(listRef.getFile(index)[3]) for index in listRef.columnkeys])
            nw = max([len(listRef.getFile(index)[2].split(',')) for index in listRef.columnkeys])
            if nt > 1 and nw > 1:
                # \n
                #box = G.newSpaceV(sizer)
                #bb, box = G.newStaticBox(self, box, title='Time series with mulitple channels', size=wx.DefaultSize)
                choice = ['time', 'channel']
                label, self.tseriesListChoice = G.makeListChoice(self, box, 'align', choice, defValue=choice[0], tip='Reference wavelength that does not move', targetFunc=self.OnRefWaveChoice)

        # -------- Microscope local distortion --------
        # \n
        box = G.newSpaceV(sizer)
        bb, box = G.newStaticBox(self, box, title='Local distortion of your microscope instrument', size=wx.DefaultSize)

        calibHelpButton = G.makeButton(self, box, self.OnHelpCalib, title='help?')

        self.calibfn = self.parent.extra_parms.get('calibfn', '')
        self.makeCalibChoice(box)
        self.calibfn_dirlabel = G.makeTxt(self, box, os.path.dirname(self.calibfn))
        self.calibfn_baselabel = G.makeTxt(self, box, os.path.basename(self.calibfn))

        calibClearButton = G.makeButton(self, box, self.OnClearCalib, title='Erace selected', tip='')
        
        # -------- OK and Cancel -----------
        btnsizer = wx.StdDialogButtonSizer()

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        sizer.Fit(self)

    def OnOutDirCb(self, evt=None):
        self.chooseOurDirButton.Enable(not(self.outdir_cb.GetValue()))
        self.outdir_label.Enable(not(self.outdir_cb.GetValue()))
        
    def OnChooseOutDir(self, evt=None):
        dlg = wx.DirDialog(self, "Choose a direcotry", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.outdir = dlg.GetPath()
        dlg.Destroy()
        self.outdir_label.SetLabel(self.outdir)

    def OnRefWaveCb(self, evt=None):
        self.refwave_choice.Enable(not(self.refwave_cb.GetValue()))
        self.refwave_label.Enable(not(self.refwave_cb.GetValue()))
        
        if not(self.refwave_cb.GetValue()) and self.refwave_label.GetLabel() == 'auto':
            self.refwave_label.SetLabel(self.refwave_choice.GetStringSelection())

    def OnRefWaveChoice(self, evt=None):
        wave = self.refwave_choice.GetStringSelection()
        self.refwave_label.SetLabel(wave)

    def OnChooseCalib(self, evt=None):
        if self.calibfn:
            dd = os.path.split(self.calibfn)[0]
        else:
            dd = self.parent.lastpath
        dlg = G.FileSelectorDialog(self, dd, wildcard='*.chromagnon.tif', multiple=False)
        
        if dlg.ShowModal() == wx.ID_OK:
            self.calibfn = dlg.GetPath()
        dlg.Destroy()
        self.calibfn_dirlabel.SetLabel(os.path.dirname(self.calibfn))
        self.calibfn_baselabel.SetLabel(os.path.basename(self.calibfn))

    def OnUseCalib(self, evt=None):
        self.calibfn_label.Enable(self.usecalib_cb.GetValue())

    def OnHelpCalib(self, evt=None):
        msg = 'By using this option, you can always apply local chromatic correction of your microscope which is expected to be constant.\n  You still have to measure your biological calibration or blead through reference images to obtain alignment parameters of your samples in addition to this instrumental calibration.\n  To measure local distortion of your microscope, obtain multiple (>5) images with 200nm tetraspec beads as many as possible in the field of view.\n  Then put the files in the reference image list box of Chromagnon and turn on "average reference" check box, choose "Projection" from the local align choice list, and run measurement. The resulting ".chromagnon.tif" can be used as instrumental calibration of your microscope.\n When measuring your biological calibration or blead through reference images, choose "None" for Local align'
        G.openMsg(self, msg=msg, title='Instruction on calibration')

    def OnClearCalib(self, evt=None):
        name = self.calib_choice.GetStringSelection()
        if name and name != self.calib_new:
            C.deleteConfig('calib_'+name)
            self.calibfn_label.SetLabel('')
            self.calibfn = ''
            self.makeCalibChoice()
            old="""
            self.usecalib_c.SetValue(0)"""
        
    def makeCalibChoice(self, box=None):
        confdic = C.readConfig()
        self.calib_microscopes = [key.replace('calib_', '') for key in confdic.keys() if key.startswith('calib_')]
        self.calib_fns = dict([(micro, confdic['calib_'+micro]) for micro in self.calib_microscopes])

        micro = [name for name, fn in self.calib_fns.items() if fn == self.calibfn]
        if micro:
            micro = micro[0]
        else:
            micro = ''

        self.calib_microscopes.insert(0, '')
        self.calib_new = 'New...'
        self.calib_microscopes.append(self.calib_new)
        if box:
            label, self.calib_choice = G.makeListChoice(self, box, 'Microscope', self.calib_microscopes, defValue=micro, targetFunc=self.OnCalibChoice)
        else:
            for i in range(self.calib_choice.GetCount()):
                self.calib_choice.Delete(0)
            for micro in self.calib_microscopes:
                self.calib_choice.Append(micro)

        
    def OnCalibChoice(self, evt=None):
        val = self.calib_choice.GetStringSelection()
        if not val:
            self.setCalib()

        elif val == self.calib_new:
            dlg = CalibrationDialog(self, self.calibfn)
            val1 = dlg.ShowModal()
            if val1 == wx.ID_OK:
                try:
                    fn = os.path.join(*dlg.listCalib.getFile(0)[:2])
                except:
                    G.openMsg(self, 'A .chromagnon.tif file is required', 'Error')
                    self.setCalib()
                    return
                name = dlg.microscope_name.GetValue()
                if name and fn:
                    if name in self.calib_fns:
                         val0 = G.askMsg(parent=self, msg='Would you like to overwrite for %s with new file %s? The previous file was %s' % (name, os.path.basename(fn), self.calib_fns[name]), title='The microscope name already exists')
                         if val0 == wx.ID_NO:
                             return

                    kwds = {'calib_%s' % name: fn}
                    C.saveConfig(**kwds)
                    self.makeCalibChoice()

                    self.calib_fns[name] = fn

                    self.setCalib(name, fn)
                else:
                    self.setCalib()
                    if not name:
                        G.openMsg(self, 'Microscope name is required', 'Error')
            else:
                self.setCalib()
        else:
            self.setCalib(val, self.calib_fns[val])

    def setCalib(self, name='', fn=''):
        self.calib_choice.SetStringSelection(name)
        self.calibfn = fn
        self.calibfn_dirlabel.SetLabel(os.path.dirname(fn))
        self.calibfn_baselabel.SetLabel(os.path.basename(fn))

class CalibrationDialog(wx.Dialog):
    def __init__(self, parent, calibfn=''):
        wx.Dialog.__init__(self, parent, id=-1, title='Microscope calibration file')

        self.calibfn = calibfn
        self.parent = parent.parent
        self.lastpath = None
        #self.aui = None

        # ------ GUI ------
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        box = G.newSpaceV(sizer)
        calibChooseButton = G.makeButton(self, box, self.OnChooseCalibFile, title='Choose file', tip='', enable=True)

        calibClearButton = G.makeButton(self, box, self.OnclearSelected, title='Clear', tip='', enable=True)
        
        # \n
        box = G.newSpaceV(sizer)

        LISTSIZE_X = sum((listbox.SIZE_COL0, listbox.SIZE_COL1, listbox.SIZE_COL2))#, listbox.SIZE_COL3, listbox.SIZE_COL4))
        LISTSIZE_Y = 40
        if sys.platform.startswith('win'):
            LISTSIZE_Y += 20
        elif sys.platform.startswith('linux'):
            LISTSIZE_Y += 10
        self.listCalib = listbox.BasicFileListCtrl(self, wx.NewId(),
                                 style=wx.LC_REPORT
                                 | wx.BORDER_NONE,
                                 #| wx.LC_SORT_ASCENDING,
                                 size=(LISTSIZE_X, LISTSIZE_Y),
                                 multiple=False)
        box.Add(self.listCalib)
        self.listCalib.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
        self.listCalib.setDefaultFileLoadFunc(self._load_func)

        # \n
        box = G.newSpaceV(sizer)
        
        label, self.microscope_name = G.makeTxtBox(self, box, 'Name of microscope', defValue='', tip='Microscope name to identify', sizeX=150, sizeY=-1)

        # -------- OK and Cancel -----------
        btnsizer = wx.StdDialogButtonSizer()

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        sizer.Fit(self)

    def OnChooseCalibFile(self, evt=None):
        if self.calibfn:
            dd = os.path.split(self.calibfn)[0]
        elif self.lastpath:
            dd = self.lastpath
        else:
            dd = self.parent.lastpath
        dlg = G.FileSelectorDialog(self, dd, wildcard='*.chromagnon.tif', multiple=False)
        if dlg.ShowModal() == wx.ID_OK:
            self.calibfn = dlg.GetPath()
        dlg.Destroy()

        self.listCalib.clearAll()
        self.listCalib.addFile(self.calibfn)

    def OnclearSelected(self, evt=None):
        #print(self.listCalib.columnkeys)
        self.listCalib.clearAll()#clearRaw(0)

    def OnDoubleClick(self, evt=None):
        #import six
        #from ndviewer import main as aui
        #from . import chromeditor
        fn = os.path.join(*self.listCalib.getFile(0)[:2])
        self.parent.view(fn)
        old="""
        target = fn
        if not self.aui:
            self.aui = aui.MyFrame(parent=self)
            self.aui.Show()

        newpanel = chromeditor.ChromagnonEditor(self.aui, target)

        if isinstance(target, six.string_types):
            name = os.path.basename(target)
        else:
            name = target.file

        if sys.platform in ('linux2', 'win32'):
            wx.CallAfter(self.aui.imEditWindows.addPage, newpanel, name, select=True)
        else:
            self.aui.imEditWindows.addPage(newpanel, name, select=True)"""

    def _load_func(self, fn):
        if chromformat.is_chromagnon(fn) and chromformat.is_binary(fn):
            h = chromformat.ChromagnonReader(fn)
        else:
            dlg = wx.MessageDialog(self, 'Only ".chromagnon.tif" file is accepted', 'Error in the file format', wx.OK | wx.ICON_EXCLAMATION)
            if dlg.ShowModal() == wx.ID_OK:
                return
                
        self.lastpath = os.path.dirname(fn)
        #C.saveConfig(lastpath=self.lastpath)
        return h
