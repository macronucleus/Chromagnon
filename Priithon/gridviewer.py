__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

# from wxPython.grid import *
import wx 
import wx.grid
# from wx import grid

import numpy as N

#---------------------------------------------------------------------------

class HugeTable(wx.grid.PyGridTableBase):

    """
    This is all it takes to make a custom data table to plug into a
    wxGrid.  There are many more methods that can be overridden, but
    the ones shown below are the required ones.  This table simply
    provides strings containing the row and column values.
    """

    def __init__(self, arr, originLeftBottom):
        wx.grid.PyGridTableBase.__init__(self)
        self.arr = arr
        self.originLeftBottom = originLeftBottom
        if self.arr.dtype.type in (N.uint8, ):
            self.width = 3
        elif self.arr.dtype.type in (N.int16, N.uint16, N.int32):
            self.width = 5
        else:
            self.width = 7
        if self.arr.dtype.type in (N.uint8, N.int16, N.uint16, N.int32):
            self.decimals = 0
        else:
            self.decimals = 2
    def GetNumberRows(self):
        return self.arr.shape[0]

    def GetNumberCols(self):
        return self.arr.shape[1]

    def IsEmptyCell(self, row, col):
        return False

    def GetValue(self, row, col):
        if self.originLeftBottom:
            row = self.arr.shape[0]-row-1
        return "%*.*f" %\
            ( self.width, self.decimals,
              self.arr[row, col] )
    
            
    def SetValue(self, row, col, value):
        #print repr(value)
        if self.originLeftBottom:
            self.arr[self.arr.shape[0]-row-1, col] = float(value)
        else:
            self.arr[row, col] = float(value)
    def GetColLabelValue(self, col):
        return str(col)
    def GetRowLabelValue(self, row):
        if self.originLeftBottom:
            return str(self.arr.shape[0]-row-1)
        else:
            return str(row)

#---------------------------------------------------------------------------



class HugeTableGrid(wx.grid.Grid):
    def __init__(self, parent, arr, originLeftBottom=1):
        wx.grid.Grid.__init__(self, parent, -1, size=(600,400))

        self.table = HugeTable(arr, originLeftBottom)

        # The second parameter means that the grid is to take ownership of the
        # table and will destroy it when done.  Otherwise you would need to keep
        # a reference to it and call it's Destroy method later.
        self.SetTable(self.table, True)
        
        wx.grid.EVT_GRID_CELL_RIGHT_CLICK(self, self.OnRightDown)  #added

    def OnRightDown(self, event):
        decimID = wx.NewId()
        widthID = wx.NewId()
        menu = wx.Menu()
        menu.Append(decimID, "Set decimals")
        menu.Append(widthID, "Set width")
        

        def setDecim(event, self=self):# , row=row):
            n = wx.GetNumberFromUser("Number of decimal places", "", "number of decimals", self.table.decimals)
            if n<0:
                return

            self.table.decimals = n
            self.Refresh()


        def setWidth(event, self=self):#, row=row):
            n = wx.GetNumberFromUser("Width of each cell", "", "Cell width", self.table.width)
            if n<0:
                return

            self.table.width = n
            self.Refresh()

        self.Bind(wx.EVT_MENU, setDecim, id=decimID)
        self.Bind(wx.EVT_MENU, setWidth, id=widthID)
        self.PopupMenu(menu)
        menu.Destroy()






#---------------------------------------------------------------------------

class ArrayGrid(wx.Frame):
    def __init__(self, parent, arr, title):
        wxFrame.__init__(self, parent, -1, title)
        global grid
        grid = HugeTableGrid(self, arr)

        grid.EnableDragRowSize(0)
        grid.SetDefaultCellAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
        grid.SetFont(wx.SWISS_FONT)
        grid.AutoSizeColumns()

#---------------------------------------------------------------------------

#  #  #  if __name__ == '__main__':
#  #  #      import sys
#  #  #      app = wxPySimpleApp()

#  #  #      app.MainLoop()

def gridview0(arr, title="grid viewer"):
    global frame

    if len(arr.shape) != 2:
        raise ValueError, "array must be of dimension 2"
    frame = ArrayGrid(None, arr, title)
    frame.SetSize((600,300))
    frame.Show(True)

#---------------------------------------------------------------------------


def gridview(array, title="2d viewer", originLeftBottom=1):
    try:
        from scipy.sparse import spmatrix
        if not isinstance(array, spmatrix):
            array = N.asanyarray(array)
    except:
        array = N.asanyarray(array)

    if array.ndim == 1:
        array = array.view()
        array.shape = (-1,len(array))
    if len(array.shape) != 2:
        raise ValueError, "array must be of dimension 2"

    ###########size = (400,400)
    frame = wx.Frame(None, -1, title)
#    grid = wx.Window(frame, -1)
    global grid
    grid = HugeTableGrid(frame, array, originLeftBottom)

    grid.EnableDragRowSize(0)
    grid.SetDefaultCellAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
    grid.SetFont(wx.SWISS_FONT)
    #grid.AutoSizeColumns()

    grid.SetDefaultColSize(40,True)
    grid.SetRowLabelSize(30)

    p1 = wx.Panel(frame, -1)
    p1_sizer = wx.BoxSizer(wx.HORIZONTAL)

    nz = 1
    if nz == 1:
        label = wx.StaticText(p1, -1, "---------->")
        #label.SetHelpText("This is the help text for the label")
        p1_sizer.Add(label, 0, wx.GROW|wx.ALL, 2)
        #z0 = 0
        #self.z = z0  ## CHECK worker thread 

    else:
        #self.lastZ = -1 # remember - for checking if update needed
        #z0 = 0
        #self.z = z0
        #slider = wx.Slider(panel1, 1001, z0, 0, self.nz-1,
        #                   wx.DefaultPosition, wx.DefaultSize,
        #                   #wx.SL_VERTICAL
        #                   wx.SL_HORIZONTAL
        #                   | wx.SL_AUTOTICKS | wx.SL_LABELS )
        #slider.SetTickFreq(5, 1)
        #box.Add(slider, 1, wx.EXPAND)
        #box.Add(slider, 0, wx.GROW|wx.ALL, 2)
        #box.Add(slider, 1, wx.EXPAND)
        #wx.EVT_SLIDER(frame, slider.GetId(), self.OnSlider)
        #self.slider = slider
        pass
            
    label2 = wx.StaticText(p1, -1, "<- move mouse over image ->")
    #label2.SetHelpText("This is the help text for the label")
    
    #p1_sizer.Add(label2, 0, wx.GROW|wx.ALL, 2)
    p1.SetAutoLayout(True)
    p1.SetSizer(p1_sizer)
    
    
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(label2, 0, wx.GROW|wx.ALL, 2)
    sizer.Add(p1, 0, wx.GROW|wx.ALL, 2)
    sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 5);
        

    frame.SetSizer(sizer);
    # sizer.SetSizeHints(frame) 
    #2.4auto  frame.SetAutoLayout(1)
    sizer.Fit(frame)

    frame.Show(1)
    frame.Layout() # hack for Linux-GTK
    # return grid
