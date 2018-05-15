"""plot functions in Y module: Y.plot...
"""
import numpy as N, six
_ERRORS = (ImportError,)
#if six.PY3:
#    _ERRORS += (ModuleNotFoundError,) <-- subclass of ImportError

try:
    import pyqtgraph as pg
except _ERRORS:
    pg = None


try: # 20051117
    plot_defaultStyle
except:
    plot_defaultStyle = '-+'

PLOTS = []
#HOLDS = [] # fixme: hold does not work of plot basis.
CURR = None

#   ['o', 's', 't', 't1', 't2', 't3','d', '+', 'x', 'p', 'h', 'star']
SYMBOLS = {'o': 'o',
           '.': 'o',
           "'": 'o',
           ':': 'o',
           '+': '+',
           'x': 'x',
           't': 't',
           '3': 't',
           '^': 't1',
           't1': 't1',
           '>': 't2',
           't2': 't2',
           '<': 't3',
           't3': 't3',
           's': 's',
           '4': 's',
           'p': 'p',
           '5': 'p',
           'h': 'h',
           '6': 'h',
           'star': 'star',
           '*': 'star'}
COLORS = {(255, 0, 0): 'r',
          (0, 255, 0): 'g',
          (0, 0, 255): 'b',
          (0, 0, 0):   'k',
          (0, 255, 255): 'c',
          (255, 0, 255): 'm'}


def plotSetColorsDefault(colString="rgbkcm", background='w'):
    """
    color-cycle: these colors are used in sequence when multiple graphs in one figure-window
    colors:
      r - red;   g - green;  b - blue
      k - black; c - cyan;   m - magenta
    """
    global plot_colors

    plot_colors = colString

    pg.setConfigOption('background', background)

if pg:
    plotSetColorsDefault()

def _color(pw, color=None):
    if not color and pw == pg:
        color = plot_colors[0]
    elif not color:
        item = _getPlotItems(pw)
        if len(item):
            color = _getPlotItems(pw)[-1].opts['pen']
            if isinstance(color, six.string_types) and color.isalpha():
                if color[0] in plot_colors:
                    i = plot_colors.index(color[0]) + 1
                else:
                    i = 0
            else: # pen object
                color = color.color()
                r, g, b = color.red(), color.green(), color.blue()
                if (r,g,b) in COLORS:
                    i = plot_colors.index(COLORS[(r,g,b)]) + 1
                else:
                    i = 0
            color = plot_colors[ i % len(plot_colors) ]
        else:
            color = plot_colors[0]
    return color

def _pen(pw, color=None):
    color = _color(pw, color)
    pen = pg.mkColor(color)

    return pen

def _brush(pw, color=None):
    color = _color(pw, color)
    brush = pg.mkBrush(color)

    return brush

def _symbolColor(pw, color=None, lineWidth=1, symbol='', symbolSize=3, fillLevel=None):
    # color
    color = _color(pw, color)

    # line or symbol color
    if lineWidth:
        pen = pg.mkPen(color, width=lineWidth)
        kwd = {'pen': pen}
    else:
        kwd = {'pen': None}
        
    if symbol or symbolSize:
        kwd['symbolBrush'] = color
        kwd['symbolPen'] = color
        # symbolPen is outline

    # symbol
    if symbol:
        kwd['symbol'] = SYMBOLS[symbol]
    if symbolSize:
        kwd['symbolSize'] = symbolSize

    # fill
    if fillLevel is not None:
        kwd['fillLevel'] = fillLevel
        
        r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
        if a == 255:
            a = 50
        else:
            a //= 5
        fillColor = pg.mkColor((r,g,b,a))
        kwd['fillBrush'] = fillColor

    return kwd
        


def plotxy(arr1, arr2=None, color=None, hold=None, figureNo=None, lineWidth=1, symbol='', symbolSize=3, fillLevel=None):
    global CURR, PLOTS
    arr1 = N.asarray( arr1 )
    
    if arr2 is not None:
        arr2 = N.asarray( arr2 )
    
    if len(arr1.shape) > 1 and arr1.shape[0] >  arr1.shape[1]:
        arr1 = N.transpose(arr1)

    if arr2 is None:
        arr2 = arr1[1:]
        arr1 = arr1[:1]
    elif len(arr2.shape) > 1 and arr2.shape[0] >  arr2.shape[1]:
        arr2 = N.transpose(arr2)

    # 20040804
    #if arr1.dtype.type == N.uint32:
    #    arr1 = arr1.astype( N.float64 )
    #if arr2.dtype.type == N.uint32:
    #    arr2 = arr2.astype( N.float64 )
    
    x=arr1
    arr=arr2

    pw = plothold(hold, figureNo)
    append = pw == pg

    kwd = _symbolColor(pw, color, lineWidth, symbol, symbolSize, fillLevel)
    #print(kwd)

    if len(arr.shape) == 1:
        pw = pw.plot(x, arr, **kwd)#pen=_color(c, pw))
    else:
        data = []
        for i in range(arr.shape[0]):
            if pw == pg:
                pw = pw.plot(x, arr[i], **kwd)#pen=_color(c, pw))
            else:
                pw.plot(x, arr[i], **kwd)#pen=_color(c, pw))
        
            
    if append:
        PLOTS.append(pw)

def ploty(arrY, color=None, hold=None, figureNo=None, lineWidth=1, symbol='', symbolSize=3, fillLevel=None):
    arrY = N.squeeze(N.asarray( arrY ))
    
    if len(arrY.shape) == 1:
        n = arrY.shape[0]
        x = N.arange(n)
    else:
        if arrY.shape[0] > arrY.shape[1]:
            arrY = N.transpose(arrY)
        n = arrY.shape[1]
        x = N.arange(n)

    plotxy(x, arrY, color, hold, figureNo, lineWidth, symbol, symbolSize, fillLevel)

def plotbar(arrY, x=None, color=None, hold=None, figureNo=None, width=0.6):
    global CURR, PLOTS
    arrY = N.asarray( arrY )
    
    if x is not None:
        x = N.asarray(x)
    else:
        x = N.arange(arrY.shape[-1])
        
    if len(arrY.shape) > 1 and arrY.shape[0] >  arrY.shape[1]:
        arrY = N.transpose(arrY)

    pw = plothold(hold, figureNo)
    append = pw == pg
    if append:
        pw = pg.plot()

    kwd = {}
    kwd['pen'] = _pen(pw, color)
    kwd['brush'] = _brush(pw, color)
    kwd['width'] = width
    

    if len(arrY.shape) == 1:
        bg = pg.BarGraphItem(x=x, height=arrY, **kwd)
        pw.addItem(bg)
    else:
        data = []
        for i in range(arr.shape[0]):
            bg = pg.BarGraphItem(x=x, height=arrY[i], **kwd)
            pw.addItem(bg)
            
    if append:
        PLOTS.append(pw)


def _getPlotItems(pw):
    return pw.getPlotItem().items

def plothold(on=1, figureNo=None):
    #FIXME: does not work as intended
    
    if figureNo is None or type(figureNo) is int:
        fig = _getFig(figureNo)
    else:
        fig = figureNo

    #if on is None and len(HOLDS):
        
    if not on and fig != pg:
        fig.clear()
    return fig
        
def _getFig(figureNo):
    global CURR
    if figureNo is not None:
        if len(PLOTS) > figureNo:
            pw = PLOTS[figureNo]
        elif len(PLOTS) <= figureNo:
            pw = pg
    elif len(PLOTS):
        pw = PLOTS[CURR]
        if pw.isVisible():
            figureNo = CURR
        else:
            pw = pg
            figureNo = CURR + 1
    else:
        pw = pg
        figureNo = 0

    CURR = figureNo
    return pw

def plotDatapoints(dataset=0, figureNo=None):
    """
    returns array (x-vals, y-vals) --> shape=(2,n)

    figureNo None means "current"
    """
    pw = _getFig(figureNo)
    items = _getPlotItems(pw)
    item = items[dataset]
    x = item.xData
    y = item.yData
    return N.array((x, y))

def plotSetYTitle(title='', figureNo=None, units=None):
    """
    title = '' means <no title>
    figureNo None means "current"
    """
    pw = _getFig(figureNo)
    pw.setLabel('left', title, units=units)
    
def plotSetXTitle(title='', figureNo=None, units=None):
    """
    title = '' means <no title>
    figureNo None means "current"
    """
    pw = _getFig(figureNo)
    pw.setLabel('bottom', title, units=units)
    # top, right

def plotClear(figureNo=None):
    """clear all graphs and images from current plot
    """
    pw = _getFig(figureNo)
    pw.clear()
    
