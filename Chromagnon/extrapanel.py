import os, sys
import wx
import numpy as N

try:
    from PriCommon import guiFuncs as G
except (ValueError, ImportError):
    from Chromagnon.PriCommon import guiFuncs as G
    

if sys.version_info.major == 2:
    import aligner, alignfuncs as af
elif sys.version_info.major >= 3:
    try:
        from . import aligner, alignfuncs as af
    except (ValueError, ImportError):
        from Chromagnon import aligner, alignfuncs as af


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
        accurChoice = [str(i) for i in aligner.ACCUR_CHOICE]
        label, self.accurListChoice = G.makeListChoice(self, box, 'Iteration of 3D phase correlation', accurChoice, defValue=confdic.get('accur', accurChoice[0]))

        # -------- max shift -----------
        # \n
        box = G.newSpaceV(sizer)
        bb, box = G.newStaticBox(self, box, title='Maximum shift the channels are possibly misaligned', size=wx.DefaultSize)
        label, self.maxshift_text = G.makeTxtBox(self, box, 'Shift (um)', defValue=confdic.get('max_shift', str(af.MAX_SHIFT)), tip='Maximum shift the channels are possibly misaligned', sizeX=40)
        
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

        G.makeTxt(self, box, 'Local alignment of Tetraspec beads (chromagnon.tif)')
        
        self.chooseOurCalibButton = G.makeButton(self, box, self.OnHelpCalib, title='help?')
        self.chooseOurCalibButton = G.makeButton(self, box, self.OnChooseCalib, title='Choose', tip='')
        self.usecalib_cb = G.makeCheck(self, box, "Use calibration", tip='', defChecked=bool(confdic.get('use_calib', '')), targetFunc=self.OnUseCalib)

        self.calibfn = confdic.get('calibfn', '')
        self.calibfn_label = G.makeTxt(self, box, self.calibfn)
        self.calibfn_label.Enable(not(self.usecalib_cb.GetValue()))
        
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
        self.calibfn_label.SetLabel(self.calibfn)

    def OnUseCalib(self, evt=None):
        self.calibfn_label.Enable(self.usecalib_cb.GetValue())

    def OnHelpCalib(self, evt=None):
        msg = 'By using this option, you can always apply local chromatic correction of your microscope which is expected to be constant.\n  You still have to measure your biological calibration sample or blead through methods to obtain alignment parameters of your samples in addition to this instrumental calibration.\n  To measure local distortion of your microscope, obtain multiple (>5) images with 200nm tetraspec beads as many as possible in the field of view.\n  Then put the files in the reference image list box of Chromagnon and turn on "average reference" check box, and run measurement. The resulting ".chromagnon.tif" can be used as instrumental calibration of your microscope.'
        G.openMsg(self, msg=msg, title='Instruction on calibration')
