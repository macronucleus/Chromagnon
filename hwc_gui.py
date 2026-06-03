"""
hwc_gui.py - wxPython GUI for hardware controller (hwc.py)

Loads a Chromagnon CSV or accepts manual Z-shift inputs per channel,
then drives the motorized camera stages.
"""

import wx
import wx.lib.scrolledpanel as scrolled
import threading
import os
import sys

# Allow running as standalone script (python hwc_gui.py) or as package module
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
_PKG_NAME = os.path.basename(_THIS_DIR)  # 'Chromagnon'

if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

try:
    from . import hwc
    from . import chromformat
except ImportError:
    # Running as __main__ — import via package name
    import importlib
    hwc = importlib.import_module(f'{_PKG_NAME}.hwc')
    chromformat = importlib.import_module(f'{_PKG_NAME}.chromformat')

# ── constants ──────────────────────────────────────────────────────────────────
MAG_DEFAULT = hwc.MAG
REFWAVE_DEFAULT = hwc.REFWAVE

# Human-readable labels for each wave index (keys from hwc.STAGES)
WAVE_LABELS = {
    0: 'Ch 0 (optosigma S)',
    2: 'Ch 2 (optosigma T)',
    3: 'Ch 3 (thorlabs U)',
}

# All channel indices defined in STAGES
CHANNELS = sorted(hwc.STAGES.keys())


# ── helpers ────────────────────────────────────────────────────────────────────

def read_csv_shifts(csvfn, refwave=REFWAVE_DEFAULT, t=0, mag=MAG_DEFAULT):
    """Return {wave_index: z_um_at_camera} from a Chromagnon CSV."""
    return hwc.get_move_amount_from_csv(csvfn, refwave=refwave, t=t, mag=mag)


# ── main frame ─────────────────────────────────────────────────────────────────

class HwcFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title='HWC – Hardware Z Controller', size=(560, 560))
        self.SetMinSize((480, 480))

        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)

        # ── Magnification / refwave row ────────────────────────────────────────
        param_box = wx.StaticBox(panel, label='Parameters')
        param_sizer = wx.StaticBoxSizer(param_box, wx.HORIZONTAL)

        param_sizer.Add(wx.StaticText(panel, label='Magnification:'), 0,
                        wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        self.mag_ctrl = wx.TextCtrl(panel, value=f'{MAG_DEFAULT:.4f}', size=(90, -1))
        param_sizer.Add(self.mag_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        param_sizer.Add(wx.StaticText(panel, label='  Ref wave index:'), 0,
                        wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)
        self.refwave_ctrl = wx.SpinCtrl(panel, value=str(REFWAVE_DEFAULT),
                                        min=0, max=10, size=(60, -1))
        param_sizer.Add(self.refwave_ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        outer.Add(param_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # ── CSV section ────────────────────────────────────────────────────────
        csv_box = wx.StaticBox(panel, label='Load Chromagnon CSV')
        csv_sizer = wx.StaticBoxSizer(csv_box, wx.HORIZONTAL)

        self.csv_path = wx.TextCtrl(panel, style=wx.TE_READONLY)
        csv_sizer.Add(self.csv_path, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)

        browse_btn = wx.Button(panel, label='Browse…')
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        csv_sizer.Add(browse_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 6)

        load_btn = wx.Button(panel, label='Load & Fill')
        load_btn.Bind(wx.EVT_BUTTON, self.on_load_csv)
        csv_sizer.Add(load_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        outer.Add(csv_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # ── Manual input table ─────────────────────────────────────────────────
        manual_box = wx.StaticBox(panel, label='Z shift at camera [µm]  (manual or filled from CSV)')
        manual_sizer = wx.StaticBoxSizer(manual_box, wx.VERTICAL)

        grid = wx.FlexGridSizer(rows=len(CHANNELS) + 1, cols=3, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)

        # Header
        for h in ('Channel', 'Z shift at camera (µm)', 'Enable'):
            lbl = wx.StaticText(panel, label=h)
            font = lbl.GetFont()
            font.MakeBold()
            lbl.SetFont(font)
            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)

        self.shift_ctrls = {}   # wave_idx -> TextCtrl
        self.enable_ctrls = {}  # wave_idx -> CheckBox

        for w in CHANNELS:
            label = WAVE_LABELS.get(w, f'Ch {w}')
            grid.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL)

            tc = wx.TextCtrl(panel, value='0.0', size=(120, -1))
            self.shift_ctrls[w] = tc
            grid.Add(tc, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

            cb = wx.CheckBox(panel)
            cb.SetValue(True)
            self.enable_ctrls[w] = cb
            grid.Add(cb, 0, wx.ALIGN_CENTER_VERTICAL)

        manual_sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 8)
        outer.Add(manual_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # ── Action buttons ─────────────────────────────────────────────────────
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        clear_btn = wx.Button(panel, label='Clear')
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        btn_sizer.Add(clear_btn, 0, wx.RIGHT, 8)

        move_btn = wx.Button(panel, label='Move stages', size=(130, -1))
        move_btn.SetBackgroundColour(wx.Colour(60, 140, 60))
        move_btn.SetForegroundColour(wx.WHITE)
        move_btn.Bind(wx.EVT_BUTTON, self.on_move)
        btn_sizer.Add(move_btn, 0)

        outer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 12)

        # ── Log area ──────────────────────────────────────────────────────────
        log_box = wx.StaticBox(panel, label='Log')
        log_sizer = wx.StaticBoxSizer(log_box, wx.VERTICAL)
        self.log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
                               size=(-1, 120))
        self.log.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE,
                                 wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        log_sizer.Add(self.log, 1, wx.EXPAND | wx.ALL, 4)
        outer.Add(log_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(outer)
        self.Centre()
        self.Show()

    # ── event handlers ─────────────────────────────────────────────────────────

    def on_browse(self, event):
        with wx.FileDialog(self, 'Open Chromagnon CSV',
                           wildcard='CSV files (*.csv)|*.csv|All files (*.*)|*.*',
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.csv_path.SetValue(dlg.GetPath())

    def on_load_csv(self, event):
        path = self.csv_path.GetValue().strip()
        if not path:
            wx.MessageBox('Please select a CSV file first.', 'No file', wx.ICON_WARNING)
            return
        if not os.path.isfile(path):
            wx.MessageBox(f'File not found:\n{path}', 'Error', wx.ICON_ERROR)
            return

        try:
            mag = float(self.mag_ctrl.GetValue())
            refwave = self.refwave_ctrl.GetValue()
            shifts = read_csv_shifts(path, refwave=refwave, mag=mag)
        except Exception as e:
            wx.MessageBox(f'Failed to read CSV:\n{e}', 'Error', wx.ICON_ERROR)
            self.log_line(f'ERROR reading CSV: {e}')
            return

        # Fill text controls with computed values
        for w, zum in shifts.items():
            if w in self.shift_ctrls:
                self.shift_ctrls[w].SetValue(f'{zum:.4f}')
                self.enable_ctrls[w].SetValue(True)

        self.log_line(f'Loaded: {os.path.basename(path)}')
        for w, zum in shifts.items():
            label = WAVE_LABELS.get(w, f'Ch {w}')
            self.log_line(f'  {label}: {zum:.4f} µm')

    def on_clear(self, event):
        for w in CHANNELS:
            self.shift_ctrls[w].SetValue('0.0')

    def on_move(self, event):
        # Collect enabled channels
        dic = {}
        for w in CHANNELS:
            if not self.enable_ctrls[w].GetValue():
                continue
            raw = self.shift_ctrls[w].GetValue().strip()
            try:
                val = float(raw)
            except ValueError:
                wx.MessageBox(f'Invalid value for {WAVE_LABELS.get(w, f"Ch {w}")}: "{raw}"',
                              'Input error', wx.ICON_ERROR)
                return
            dic[w] = val

        if not dic:
            wx.MessageBox('No channels enabled.', 'Nothing to do', wx.ICON_INFORMATION)
            return

        summary = '\n'.join(f'  {WAVE_LABELS.get(w, f"Ch {w}")}: {z:.4f} µm'
                            for w, z in dic.items())
        if wx.MessageBox(
                f'Move the following stages?\n\n{summary}',
                'Confirm move', wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
            return

        self.log_line('Moving stages…')
        # Run in thread so the UI stays responsive
        threading.Thread(target=self._move_thread, args=(dic,), daemon=True).start()

    def _move_thread(self, dic):
        try:
            result = hwc.move(dic)
            wx.CallAfter(self.log_line, 'Done. Result:')
            for module, axes in result.items():
                for axis, zum in axes.items():
                    wx.CallAfter(self.log_line, f'  {module}/{axis}: {zum:.4f} µm')
        except Exception as e:
            wx.CallAfter(self.log_line, f'ERROR during move: {e}')
            wx.CallAfter(wx.MessageBox, f'Stage move failed:\n{e}', 'Error', wx.ICON_ERROR)

    # ── utility ────────────────────────────────────────────────────────────────

    def log_line(self, text):
        self.log.AppendText(text + '\n')


# ── entry point ────────────────────────────────────────────────────────────────

def main():
    app = wx.App(False)
    HwcFrame()
    app.MainLoop()


if __name__ == '__main__':
    main()
