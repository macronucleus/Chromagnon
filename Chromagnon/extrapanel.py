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
        if listRef and listRef.columnkeys:

            waves1 = [list(listRef.getFile(index)[2].split(',')) for index in listRef.columnkeys]
            waves = set()
            for wave in waves1:
                [waves.add(w) for w in wave]
            waves = list(waves)
            waves.sort()

            if len(waves) > 1:
                # \n
                box = G.newSpaceV(sizer)
                bb, box = G.newStaticBox(self, box, title='Reference wavelength', size=wx.DefaultSize)
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
        if listRef and listRef.columnkeys:

            nt = max([int(listRef.getFile(index)[3]) for index in listRef.columnkeys])
            nw = max([len(listRef.getFile(index)[2].split(',')) for index in listRef.columnkeys])
            if nt > 1 and nw > 1:
                # \n
                box = G.newSpaceV(sizer)
                bb, box = G.newStaticBox(self, box, title='Time series with mulitple channels', size=wx.DefaultSize)
                choice = ['time', 'channel']
                label, self.tseriesListChoice = G.makeListChoice(self, box, 'align', choice, defValue=choice[0], tip='Reference wavelength that does not move', targetFunc=self.OnRefWaveChoice)
        
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
