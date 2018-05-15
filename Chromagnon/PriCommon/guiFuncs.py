import os
import six
import wx
try:
    from ..Priithon import viewerRubberbandMode
except ValueError: # interactive mode
    from Priithon import viewerRubberbandMode

SIZER_KWDS={'flag': wx.ALIGN_CENTRE|wx.ALL|wx.GROW, 'border': 0}

def makePage(notebook, title=''):
    """
    returns panel, verticalSizer
    """
    panel = wx.Panel(notebook, -1)
    notebook.AddPage(panel, title)
    sizer = wx.BoxSizer(wx.VERTICAL)
    panel.SetSizer(sizer)
    return panel, sizer

def newStaticBox(panel, sizer, title='', size=wx.DefaultSize):
    """
    returns staticBox, groupBoxSizer
    """
    staticBox = wx.StaticBox(panel, -1, title, size=size)
    groupBoxSizer = wx.StaticBoxSizer(staticBox, wx.VERTICAL)
    sizer.Add(groupBoxSizer, 0, wx.GROW|wx.ALL, 5)
    return staticBox, groupBoxSizer

def newSpaceV(verticalSizer):
    """
    returns horizontalBoxSizer
    """
    box = wx.BoxSizer(wx.HORIZONTAL)
    verticalSizer.Add(box)#, 0, wx.ALL, 5)
    return box

def newSpaceH(horizontalSizer, size):
    horizontalSizer.Add((size,-1))#,  2, wx.GROW|wx.ALL,5)

def newColumn(horizontalSizer):
    """
    returns verticalBoxSizer
    """
    box = wx.BoxSizer(wx.VERTICAL)
    horizontalSizer.Add(box)
    return box


def makeButton(panel, horizontalSizer, targetFunc, title='', tip='', enable=True, **sizerKwds):
    """
    returns button
    """
    button = wx.Button(panel, -1, str(title))
    if tip is not '':
        button.SetToolTip(wx.ToolTip(str(tip)))
    horizontalSizer.Add(button, **sizerKwds)
    frame = panel.GetTopLevelParent()
    frame.Bind(wx.EVT_BUTTON, targetFunc, button)
    button.Enable(enable)
    return button

def makeToggleButton(panel, horizontalSizer, targetFunc, title, tip='', enable=True, size=wx.DefaultSize, **sizerKwds):
    """
    returns toggle button
    """
    toggle = wx.ToggleButton(panel, -1, str(title), size=size)
    if tip is not None:
        toggle.SetToolTip(wx.ToolTip(str(tip)))
    horizontalSizer.Add(toggle, **sizerKwds)
    frame = panel.GetTopLevelParent()
    frame.Bind(wx.EVT_TOGGLEBUTTON, targetFunc, toggle)
    toggle.Enable(enable)
    return toggle

def makeTxt(panel, horizontalSizer, labelTxt, **sizerKwds):
    """
    return label
    """
    label = wx.StaticText(panel, -1, str(labelTxt))    
    horizontalSizer.Add(label, **sizerKwds)
    #if dynamicFunc:
    #    def changeLabel(txt):
    #        print ' changeding'
    #        txt = dynamicPreTxt + txt + dynamicPostTxt
    #        label.SetLabel(txt)
    #    dynamicFunc = changeLabel
    return label

def makeTxtBox(panel, horizontalSizer, labelTxt, defValue='', tip='', sizeX=40, sizeY=-1, style=0, **sizerKwds):
    """
    returns label, txt
    """
    label = makeTxt(panel, horizontalSizer, labelTxt, **sizerKwds)
    txt = wx.TextCtrl(panel, -1, str(defValue), size=(sizeX,sizeY), style=style)
    if tip is not '':
        txt.SetToolTip(wx.ToolTip(str(tip)))
    horizontalSizer.Add(txt, **sizerKwds)
    return label, txt

def makeListChoice(panel, horizontalSizer, labelTxt, choicelist, defValue='', tip='', targetFunc=None, size=wx.DefaultSize, **sizerKwds):
    """
    returns label, choice
    """
    if labelTxt:
        label = makeTxt(panel, horizontalSizer, labelTxt, **sizerKwds)
    else:
        label = None
    choice = wx.Choice(panel, -1, choices = choicelist, size=size)
    if tip is not '':
        choice.SetToolTip(wx.ToolTip(tip))
    horizontalSizer.Add(choice, **sizerKwds)
    if targetFunc:
        frame = panel.GetTopLevelParent()
        frame.Bind(wx.EVT_CHOICE, targetFunc, choice)
    if defValue is not '':
        choice.SetStringSelection(str(defValue))
    return label, choice

def makeCheck(panel, horizontalSizer, labelTxt, tip='', defChecked=0, targetFunc=None, **sizerKwds):
    """
    returns check
    """
    check = wx.CheckBox(panel, -1, labelTxt)
    if tip is not None:
        check.SetToolTip(wx.ToolTip(str(tip)))
    horizontalSizer.Add(check, **sizerKwds)
    check.SetValue(defChecked)

    if targetFunc:
        frame = panel.GetTopLevelParent()
        frame.Bind(wx.EVT_CHECKBOX, targetFunc, check)
    return check

def makeSpin(panel, horizontalSizer, labelTxt, Range=None, defVal=None, tip='', size=wx.DefaultSize, **sizerKwds):
    """
    returns label, spinctrl
    """
    label = makeTxt(panel, horizontalSizer, labelTxt)
    spn = wx.SpinCtrl(panel, -1, '', size=size)
    if tip:
        spn.SetToolTip(wx.ToolTip(tip))
    horizontalSizer.Add(spn, **sizerKwds)
    if Range is not None: # if None, max=100
        spn.SetRange(*Range)
    if defVal is not None:
        spn.SetValue(defVal)
    return label, spn

def makeCombo(panel, horizontalSizer, labelTxt, choices, defVal='', tip='', size=wx.DefaultSize, targetFunc=None, processEnter=True, **sizerKwds):
    """
    returns label, spinctrl
    """
    if labelTxt:
        label = makeTxt(panel, horizontalSizer, labelTxt)
    else:
        label = None
    if processEnter:
        comb = wx.ComboBox(panel, -1, defVal, choices=choices, style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER | wx.WANTS_CHARS, size=size)
    else:
        comb = wx.ComboBox(panel, -1, defVal, choices=choices, size=size)#style=wx.CB_DROPDOWN | wx.WANTS_CHARS, size=size)
    if tip:
        comb.SetToolTip(wx.ToolTip(tip))
    horizontalSizer.Add(comb, **sizerKwds)

    if targetFunc:
        frame = panel.GetTopLevelParent()
        frame.Bind(wx.EVT_COMBOBOX, targetFunc, comb)

    return label, comb


def makeRadioButtons(panel, horizontalSizer, labelTxts, targetFunc=None, size=wx.DefaultSize, **sizerKwds):
    """
    returns list of radioButtons number of which is determined by labelTxts
    """
    if isinstance(labelTxts, six.string_types):
        nbuts = 1
        labelTxts = [labelTxts]
    else:
        nbuts = len(labelTxts)
    
    ctrls = []
    for i, labelTxt in enumerate(labelTxts):
        if i == 0:
            radio = wx.RadioButton(panel, -1, labelTxt, size=size, style=wx.RB_GROUP)
        else:
            radio = wx.RadioButton(panel, -1, labelTxt, size=size)
        horizontalSizer.Add(radio, **sizerKwds)

        if targetFunc:
            frame = panel.GetTopLevelParent()
            frame.Bind(wx.EVT_RADIOBUTTON, targetFunc, radio)
            
        ctrls.append(radio)
    
    return ctrls

def openMsg(parent=None, msg='', title="You are not ready"):
    dlg = wx.MessageDialog(parent, msg, title, wx.OK | wx.ICON_EXCLAMATION)
    if dlg.ShowModal() == wx.ID_OK:
        return

def askMsg(parent=None, msg='', title=''):
    dlg = wx.MessageDialog(parent, msg, title, wx.YES_NO)
    return dlg.ShowModal()


class FileSelectorDialog(wx.Dialog):
    def __init__(self, parent=None, direc=None, wildcard='*', multiple=True, showHiddenFiles=False):
        """
        file selector dialog with unix-style wildcard

        direc: starting directory
        wildcard: unix-style wildcard
        multiple: style

        use like
        >>> dlg = FileSelectorDialog()
        >>> if dlg.ShowModal() == wx.ID_OK:
        >>>     fns = dlg.GetPaths()
        >>> dlg.Destroy()
        """

        if not direc:
            direc = os.getcwd()
        self.direc=os.path.abspath(direc)
        self.fnPat = wildcard
        self.multiple = multiple
        self.showHiddenFiles = showHiddenFiles

        wx.Dialog.__init__(self, parent, -1, title='')

        
        sizer = wx.BoxSizer(wx.VERTICAL)

        hsz = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(hsz, 0, wx.EXPAND)

        self.up_button = wx.Button(self, wx.ID_UP, style=wx.BU_EXACTFIT)
        hsz.Add(self.up_button)
        #wx.EVT_BUTTON(self, self.up_button.GetId(), self.onUp)
        self.Bind(wx.EVT_BUTTON, self.onUp, id=self.up_button.GetId())
        
        self.txt = wx.TextCtrl(self, wx.ID_ANY, os.path.join(self.direc, self.fnPat))
        hsz.Add(self.txt, 1, wx.EXPAND|wx.ALL, 2)
        #wx.EVT_TEXT(self, self.txt.GetId(), self.refreshList)
        self.Bind(wx.EVT_TEXT, self.refreshList, id=self.txt.GetId())

        hsz = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(hsz, 0, wx.EXPAND)

        if self.multiple:
            style = wx.LB_EXTENDED|wx.LB_NEEDED_SB|wx.LB_HSCROLL
        else:
            style = wx.LB_SINGLE|wx.LB_NEEDED_SB|wx.LB_HSCROLL
        self.lb = wx.ListBox(self, wx.ID_ANY, size=(350,400), style=style)
        sizer.Add(self.lb, 1, wx.EXPAND | wx.ALL, 5)
        
        #wx.EVT_LISTBOX_DCLICK(self, self.lb.GetId(), self.onDClick)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.onDClick, id=self.lb.GetId())

        bsz = wx.StdDialogButtonSizer()
        sizer.Add(bsz, 0, wx.EXPAND)

        button = wx.Button(self, wx.ID_CANCEL)
        bsz.AddButton(button)
        
        button = wx.Button(self, wx.ID_OK)
        bsz.AddButton(button)

        bsz.Realize()

        ll = self.txt.GetLastPosition()
        self.txt.SetInsertionPoint(ll)

        self.refreshList(None)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def getDirec(self):
        return os.path.dirname(self.txt.GetValue())

    def getPath(self):
        """
        combine wildcard with directory
        """
        return os.path.join(self.getDirec(), self.fnPat)

    def GetPath(self):
        """
        return a abs-path
        """
        #s = self.lb.GetStringSelection() # this does not work in some reason

        strings = self.lb.GetStrings()
        s = [strings[idx] for idx in self.lb.GetSelections()]
        if not s:
            return ''
        
        return os.path.join(self.getDirec(), s[0])
    
    def GetPaths(self):
        """
        return list of selected abs-paths
        """
        if self.multiple:
            files = self.lb.GetItems()
            return [os.path.join(self.getDirec(), files[i]) for i in self.lb.GetSelections() if os.path.isfile(os.path.join(self.getDirec(),files[i]))]
        else:
            s = self.lb.GetStringSelection()
            fn = os.path.join(self.getDirec(), s)
            if os.path.isfile(fn):
                return [fn]
            else:
                return []

    def onUp(self, evt=None):
        self.onDClick(fn=os.path.dirname(self.getDirec()))

    def onDClick(self, evt=None, fn=None):
        """
        change directory
        """
        if not fn:
            fn = self.GetPath()
        self.fn = fn

        if os.path.isdir(fn) or os.path.isdir(os.path.normpath(fn)):
            self.direc = os.path.normpath(fn)
            _,self.fnPat = os.path.split(self.txt.GetValue())
            self.txt.SetValue(os.path.join(self.direc, self.fnPat))
            self.refreshList()

    def refreshList(self, ev=None):
        """
        generate list of files:
        1. "../"
        2. all sub dirs
        3. files, only those that match the given file pattern
        """
        import glob
        
        filesGlob = self.txt.GetValue()
        _,self.fnPat = os.path.split(filesGlob)  # in case text for fnPat has changed
        d,f = os.path.split(filesGlob)
        if f == '':
            f = '*'

        # list of sub-dirs -- add trailing '/'
        try:
            ddDirs = sorted( [f1+'/' for f1 in os.listdir(d) if os.path.isdir(os.path.join(d,f1))] )
        except OSError:
            ddDirs = []

        ddFiles = sorted( [f1 for f1 in glob.glob1(d,f) if not os.path.isdir(os.path.join(d,f1))] )
        if not self.showHiddenFiles:
            ddDirs = [f1 for f1 in ddDirs if not f1.startswith('.')]
            ddFiles = [f1 for f1 in ddFiles if not f1.startswith('.')]

        dd = ["../"] + ddDirs + ddFiles

        self.lb.Clear()
        self.lb.InsertItems( dd, 0 )
     
        title = "files in %s" % self.direc
        self.SetTitle(title)


class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, parent):
        wx.FileDropTarget.__init__(self)
        self.myLFV = parent

    def OnDropFiles(self, x, y, filenames):
        import os.path
        fn = filenames[0]

        if os.path.isdir(fn):
            self.myLFV.dir =                 os.path.normpath(fn)
        else:
            self.myLFV.dir,_ = os.path.split(os.path.normpath(fn))

        self.myLFV.txt.SetValue(self.myLFV.getPath())
        self.myLFV.refreshList()

class DummyRubberbandMode(viewerRubberbandMode.viewerRubberbandMode):
    def __init__(self, id=-1, rubberWhat='box', color=(0,1,0), 
                 gfxWhenDone='hide', roiName='1'):
        """
        id can be a viewerID
               or a viewer.GLViewer object
        rubberWhat should be one of:
             'box'
             'line'
             'circle'
             'ellipse'

        gfxWhenDone should be one of: 'hide', 'remove', None
        """
        self.splitND = None
        
        self.id = id
        self.rubberWhat = rubberWhat
        self.color = color
        self.gfxWhenDone = gfxWhenDone
        self.roiName = roiName
        self.gfxIdx = None

    def getData(self, id=None):
        pass
    def getMask(self):
        pass
    def onLeft1(self, xEff, yEff, ev):
        pass
    def onLeft2(self, xEff, yEff, ev):
        pass
    def gfxUpdate(self):
        pass
    def gfxShow(self):
        pass
    def gfxHide(self):
        pass
    def gfxEnable(self, on=True):
        pass
    def gfxRemove(self):
        pass
