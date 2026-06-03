"""
hwc_gui.py - wxPython GUI for hardware controller (hwc.py)

Loads a Chromagnon CSV or accepts manual Z-shift inputs per channel,
then drives the motorized camera stages.
"""

import wx
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
    import importlib
    hwc = importlib.import_module(f'{_PKG_NAME}.hwc')
    chromformat = importlib.import_module(f'{_PKG_NAME}.chromformat')

# ── constants ──────────────────────────────────────────────────────────────────
MAG_DEFAULT = hwc.MAG
REFWAVE_DEFAULT = hwc.REFWAVE

WAVE_LABELS = {
    0: 'Ch 0 (optosigma S)',
    2: 'Ch 2 (optosigma T)',
    3: 'Ch 3 (thorlabs U)',
}

CHANNELS = sorted(hwc.STAGES.keys())

_POS_UNKNOWN = '---'


# ── helpers ────────────────────────────────────────────────────────────────────

def read_csv_shifts(csvfn, refwave=REFWAVE_DEFAULT, t=0, mag=MAG_DEFAULT):
    return hwc.get_move_amount_from_csv(csvfn, refwave=refwave, t=t, mag=mag)


# ── main frame ─────────────────────────────────────────────────────────────────

class HwcFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title='HWC – Hardware Z Controller', size=(900, 700))
        self.SetMinSize((800, 600))

        # cumulative jog offset per channel, in sample-side µm
        self.jog_offset = {w: 0.0 for w in CHANNELS}

        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)

        # ── Parameters ────────────────────────────────────────────────────────
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

        # ── CSV ───────────────────────────────────────────────────────────────
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

        # ── Channel table ─────────────────────────────────────────────────────
        table_box = wx.StaticBox(panel, label='Channels')
        table_sizer = wx.StaticBoxSizer(table_box, wx.VERTICAL)

        # columns: Channel | Current pos | Jog offset (sample) | Z shift | Enable
        grid = wx.FlexGridSizer(rows=len(CHANNELS) + 1, cols=5, vgap=6, hgap=10)
        grid.AddGrowableCol(3, 1)

        bold_font = self.GetFont()
        bold_font.MakeBold()
        for h in ('Channel', 'Current pos (µm)', 'Jog offset\n(sample µm)', 'Z shift at camera (µm)', 'Enable'):
            lbl = wx.StaticText(panel, label=h)
            lbl.SetFont(bold_font)
            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)

        self.shift_ctrls = {}      # wave_idx -> TextCtrl
        self.enable_ctrls = {}     # wave_idx -> CheckBox
        self.pos_labels = {}       # wave_idx -> StaticText (hardware position)
        self.offset_labels = {}    # wave_idx -> StaticText (cumulative jog offset)

        mono_font = wx.Font(10, wx.FONTFAMILY_TELETYPE,
                            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        for w in CHANNELS:
            label = WAVE_LABELS.get(w, f'Ch {w}')
            grid.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL)

            pos_lbl = wx.StaticText(panel, label=_POS_UNKNOWN, size=(120, -1),
                                    style=wx.ST_NO_AUTORESIZE)
            pos_lbl.SetFont(mono_font)
            self.pos_labels[w] = pos_lbl
            grid.Add(pos_lbl, 0, wx.ALIGN_CENTER_VERTICAL)

            off_lbl = wx.StaticText(panel, label='0.0000', size=(110, -1),
                                    style=wx.ST_NO_AUTORESIZE)
            off_lbl.SetFont(mono_font)
            self.offset_labels[w] = off_lbl
            grid.Add(off_lbl, 0, wx.ALIGN_CENTER_VERTICAL)

            tc = wx.TextCtrl(panel, value='0.0', size=(120, -1))
            self.shift_ctrls[w] = tc
            grid.Add(tc, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

            cb = wx.CheckBox(panel)
            cb.SetValue(True)
            self.enable_ctrls[w] = cb
            grid.Add(cb, 0, wx.ALIGN_CENTER_VERTICAL)

        table_sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 8)
        outer.Add(table_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        clear_btn = wx.Button(panel, label='Clear shifts')
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        btn_sizer.Add(clear_btn, 0, wx.RIGHT, 8)

        reset_btn = wx.Button(panel, label='Reset jog offsets')
        reset_btn.SetToolTip('全チャンネルの Jog offset を 0 にリセット')
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset_offsets)
        btn_sizer.Add(reset_btn, 0, wx.RIGHT, 8)

        self.refresh_btn = wx.Button(panel, label='Refresh positions')
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        btn_sizer.Add(self.refresh_btn, 0, wx.RIGHT, 20)

        self.move_btn = wx.Button(panel, label='Move stages', size=(130, -1))
        self.move_btn.SetBackgroundColour(wx.Colour(60, 140, 60))
        self.move_btn.SetForegroundColour(wx.WHITE)
        self.move_btn.Bind(wx.EVT_BUTTON, self.on_move)
        btn_sizer.Add(self.move_btn, 0)

        outer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 12)

        # ── Manual jog ───────────────────────────────────────────────────────
        jog_box = wx.StaticBox(panel, label='Manual jog  (sample-side µm → stage move)')
        jog_sizer = wx.StaticBoxSizer(jog_box, wx.HORIZONTAL)

        jog_sizer.Add(wx.StaticText(panel, label='Channel:'), 0,
                      wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 6)
        self.jog_ch = wx.Choice(panel,
                                choices=[WAVE_LABELS.get(w, f'Ch {w}') for w in CHANNELS])
        self.jog_ch.SetSelection(0)
        jog_sizer.Add(self.jog_ch, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        jog_sizer.Add(wx.StaticText(panel, label='  Distance (µm, sample):'), 0,
                      wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)
        self.jog_dist = wx.TextCtrl(panel, value='1.0', size=(80, -1))
        jog_sizer.Add(self.jog_dist, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        jog_sizer.Add(wx.StaticText(panel, label='  →  stage:'), 0,
                      wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        self.jog_preview = wx.StaticText(panel, label='---  µm', size=(110, -1))
        self.jog_preview.SetFont(mono_font)
        jog_sizer.Add(self.jog_preview, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)

        self.jog_dist.Bind(wx.EVT_TEXT, self.on_jog_dist_changed)
        self.jog_ch.Bind(wx.EVT_CHOICE, self.on_jog_dist_changed)

        jog_sizer.AddStretchSpacer()

        jog_neg_btn = wx.Button(panel, label='− Move', size=(80, -1))
        jog_neg_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_jog(e, sign=-1))
        jog_sizer.Add(jog_neg_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)

        jog_pos_btn = wx.Button(panel, label='＋ Move', size=(80, -1))
        jog_pos_btn.SetBackgroundColour(wx.Colour(50, 110, 200))
        jog_pos_btn.SetForegroundColour(wx.WHITE)
        jog_pos_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_jog(e, sign=+1))
        jog_sizer.Add(jog_pos_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 6)

        outer.Add(jog_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # ── Log ───────────────────────────────────────────────────────────────
        log_box = wx.StaticBox(panel, label='Log')
        log_sizer = wx.StaticBoxSizer(log_box, wx.VERTICAL)
        self.log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
                               size=(-1, 110))
        self.log.SetFont(mono_font)
        log_sizer.Add(self.log, 1, wx.EXPAND | wx.ALL, 4)
        outer.Add(log_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(outer)
        self.Centre()
        self.Show()

        self.Bind(wx.EVT_CLOSE, self.on_close)

        # Try to open stages in background on startup
        threading.Thread(target=self._open_stages_thread, daemon=True).start()

    # ── startup / shutdown ────────────────────────────────────────────────────

    def _open_stages_thread(self):
        opened = hwc.open_stages()
        wx.CallAfter(self._on_stages_opened, opened)

    def _on_stages_opened(self, opened):
        if opened:
            self.log_line('Stages connected: ' + ', '.join(opened.keys()))
        else:
            self.log_line('WARNING: No stages could be connected.')
        # Auto-read positions after connection
        threading.Thread(target=self._refresh_thread, daemon=True).start()

    def on_close(self, event):
        hwc.close_stages()
        event.Skip()  # proceed with normal close

    # ── event handlers ────────────────────────────────────────────────────────

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

        for w, zum in shifts.items():
            if w in self.shift_ctrls:
                self.shift_ctrls[w].SetValue(f'{zum:.4f}')
                self.enable_ctrls[w].SetValue(True)

        self.log_line(f'Loaded: {os.path.basename(path)}')
        for w, zum in shifts.items():
            self.log_line(f'  {WAVE_LABELS.get(w, f"Ch {w}")}: {zum:.4f} µm')

    def on_clear(self, event):
        for w in CHANNELS:
            self.shift_ctrls[w].SetValue('0.0')

    def on_reset_offsets(self, event):
        for w in CHANNELS:
            self.jog_offset[w] = 0.0
            self.offset_labels[w].SetLabel('0.0000')
        self.log_line('Jog offsets reset to 0.')

    # ── jog helpers ───────────────────────────────────────────────────────────

    def _jog_camera_um(self):
        """Return (wave_idx, camera_um) from current jog inputs, or raise ValueError."""
        raw = self.jog_dist.GetValue().strip()
        sample_um = float(raw)
        mag = float(self.mag_ctrl.GetValue())
        camera_um = hwc.get_shift_amount_at_camera(sample_um, mag)
        w = CHANNELS[self.jog_ch.GetSelection()]
        return w, camera_um

    def on_jog_dist_changed(self, event):
        try:
            _, camera_um = self._jog_camera_um()
            self.jog_preview.SetLabel(f'{camera_um:.4f}  µm')
        except (ValueError, ZeroDivisionError):
            self.jog_preview.SetLabel('---  µm')

    def on_jog(self, event, sign):
        try:
            w, camera_um = self._jog_camera_um()
            sample_um = float(self.jog_dist.GetValue().strip())
        except (ValueError, ZeroDivisionError):
            wx.MessageBox('Enter a valid numeric distance.', 'Input error', wx.ICON_ERROR)
            return

        camera_um *= sign
        sample_um *= sign
        label = WAVE_LABELS.get(w, f'Ch {w}')
        direction = '+' if sign > 0 else '−'

        if wx.MessageBox(
                f'Jog {label} by {direction}{abs(camera_um):.4f} µm at stage\n'
                f'(= {direction}{abs(sample_um):.4f} µm at sample)?',
                'Confirm jog', wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
            return

        self.move_btn.Disable()
        self.refresh_btn.Disable()
        self.log_line(f'Jogging {label}: {camera_um:+.4f} µm at stage '
                      f'({sample_um:+.4f} µm at sample)…')
        threading.Thread(target=self._jog_thread,
                         args=({w: camera_um}, w, sample_um), daemon=True).start()

    def _jog_thread(self, dic, w, sample_um):
        try:
            hwc.move(dic)
            wx.CallAfter(self._accumulate_offset, w, sample_um)
            wx.CallAfter(self.log_line, 'Jog done.')
            positions = hwc.get_positions()
            wx.CallAfter(self._apply_positions, positions)
        except Exception as e:
            wx.CallAfter(self.log_line, f'ERROR during jog: {e}')
            wx.CallAfter(wx.MessageBox, f'Jog failed:\n{e}', 'Error', wx.ICON_ERROR)
        finally:
            wx.CallAfter(self.move_btn.Enable)
            wx.CallAfter(self.refresh_btn.Enable)

    def _accumulate_offset(self, w, sample_um):
        self.jog_offset[w] += sample_um
        total = self.jog_offset[w]
        self.offset_labels[w].SetLabel(f'{total:+.4f}')
        self.log_line(f'  Jog offset {WAVE_LABELS.get(w, f"Ch {w}")}: '
                      f'{total:+.4f} µm (sample)')

    # ── stage position ────────────────────────────────────────────────────────

    def on_refresh(self, event):
        self.refresh_btn.Disable()
        self.log_line('Reading stage positions…')
        threading.Thread(target=self._refresh_thread, daemon=True).start()

    def _refresh_thread(self):
        try:
            positions = hwc.get_positions()
            wx.CallAfter(self._apply_positions, positions)
        except Exception as e:
            wx.CallAfter(self.log_line, f'ERROR reading positions: {e}')
        finally:
            wx.CallAfter(self.refresh_btn.Enable)

    def _apply_positions(self, positions):
        for w in CHANNELS:
            if w in positions:
                self.pos_labels[w].SetLabel(f'{positions[w]:.4f}')
            else:
                self.pos_labels[w].SetLabel('N/A')
        self.log_line('Positions updated:')
        for w in CHANNELS:
            label = WAVE_LABELS.get(w, f'Ch {w}')
            if w in positions:
                self.log_line(f'  {label}: {positions[w]:.4f} µm')
            else:
                self.log_line(f'  {label}: not available (stage not connected?)')

    # ── move all ─────────────────────────────────────────────────────────────

    def on_move(self, event):
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
        if wx.MessageBox(f'Move the following stages?\n\n{summary}',
                         'Confirm move', wx.YES_NO | wx.ICON_QUESTION) != wx.YES:
            return

        self.move_btn.Disable()
        self.log_line('Moving stages…')
        threading.Thread(target=self._move_thread, args=(dic,), daemon=True).start()

    def _move_thread(self, dic):
        try:
            result = hwc.move(dic)
            wx.CallAfter(self.log_line, 'Move done:')
            for module, axes in result.items():
                for axis, zum in axes.items():
                    wx.CallAfter(self.log_line, f'  {module}/{axis}: {zum:.4f} µm')
            positions = hwc.get_positions()
            wx.CallAfter(self._apply_positions, positions)
        except Exception as e:
            wx.CallAfter(self.log_line, f'ERROR during move: {e}')
            wx.CallAfter(wx.MessageBox, f'Stage move failed:\n{e}', 'Error', wx.ICON_ERROR)
        finally:
            wx.CallAfter(self.move_btn.Enable)

    # ── utility ───────────────────────────────────────────────────────────────

    def log_line(self, text):
        self.log.AppendText(text + '\n')


# ── entry point ────────────────────────────────────────────────────────────────

def main():
    app = wx.App(False)
    HwcFrame()
    app.MainLoop()


if __name__ == '__main__':
    main()
