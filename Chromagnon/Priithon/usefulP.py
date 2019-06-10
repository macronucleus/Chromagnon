"""plot functions in Y module: Y.plot...
"""
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import wx
wx.PyDeadObjectError = RuntimeError # wx 3->4

import numpy as N
try: # 20051117
    plot_defaultStyle
except:
    plot_defaultStyle = '-+'
    

def plotSetColorsDefault(colString="rgbkcm"):
    """
    color-cycle: these colors are used in sequence when multiple graphs in one figure-window
    colors:
      r - red;   g - green;  b - blue
      k - black; c - cyan;   m - magenta
    """
    global plot_colors

    plot_colors = colString

plotSetColorsDefault()

def _col(c, overwriteHold=False):
    from . import plt
    plt.validate_active()
    fig = plt.interface._active
    #figwxid = fig.GetId()

    if c[0].isalpha() and c[0] not in 'xo':   #start colorString with letter to specify color
        if len(c) == 1:
            return c+plot_defaultStyle
        else:
            return c
    if c[0].isdigit():         #start colorString with digit to set new position in color-cycle
        
        fig._sebCurrentColorIndex = int(c[0])
        i = fig._sebCurrentColorIndex
        fig._sebCurrentColorIndex+=1

        if len(c) == 1:
            return c+plot_defaultStyle
        else:
            return c
    else: #20050723 if i is None:
        if not overwriteHold and fig.hold not in ['on','yes']:
            i = fig._sebCurrentColorIndex = 0
        else:
            if not hasattr(fig, "_sebCurrentColorIndex"):
                fig._sebCurrentColorIndex = 0
            i = fig._sebCurrentColorIndex
        fig._sebCurrentColorIndex +=1
    return plot_colors[ i % len(plot_colors) ]+c

def _getFig(figureNo):
    from . import plt
    if figureNo is None:
        plt.validate_active()
        fig = plt.interface._active
    else:
        fig = plt.interface._figure[figureNo]

    return fig

def plotDatapoints(dataset=0, figureNo=None):
    """
    returns array (x-vals, y-vals) --> shape=(2,n)

    figureNo None means "current"
    """
    fig = _getFig(figureNo)

    a = N.asarray( fig.client.line_list[dataset].points )
    return N.transpose(a)

                    
def plotGetXminmax(figureNo=None):
    """
    returns tuple (left, right) values on X-axis
    figureNo None means "current"
    """
    fig = _getFig(figureNo)
    pc = fig.client                   # canvas

    return pc.x_axis.ticks[0], pc.x_axis.ticks[-1]

def plotGetYminmax(figureNo=None):
    """
    returns tuple (bottom,top) values on Y-axis
    figureNo None means "current"
    """
    fig = _getFig(figureNo)
    pc = fig.client                   # canvas

    return pc.y_axis.ticks[0], pc.y_axis.ticks[-1]

def plotSetColor(color=(255,0,0), dataset=0, plotNofigureNo=None):
    """
    set color of a dataset in a figure

    figureNo None means "current"
    """
    fig = _getFig(figureNo)

    fig.client.line_list[dataset].set_color(color)
    fir.Refresh()

def plotRefresh(figureNo=None):
    """
    refresh / update graph in figure

    figureNo None means "current"
    """
    fig = _getFig(figureNo)
    fig.Refresh()

def plotChangeDatapoints(xyPointArray, dataset=0, figureNo=None, refreshNow=True):
    """
    refresh / update graph in figure

    figureNo None means "current"

    HACK / FIXME only change line, ignore markers
    """
    import numpy
    fig = _getFig(figureNo)      
    lineObj = fig.client.line_list[dataset]
    
    lineObj.line.points = numpy.asarray( xyPointArray )

    if refreshNow:
        fig.Refresh()



def plotSetFrameTitle(title, figureNo=None):
    """
    figureNo None means "current"
    """
    fig = _getFig(figureNo)
    fig.SetTitle(title)
def plotSetTitle(title='', figureNo=None):
    """
    title = '' means <no title>
    figureNo None means "current"
    """
    fig = _getFig(figureNo)

    fig.client.title.text=title
    fig.client.update()
def plotSetXTitle(title='', figureNo=None):
    """
    title = '' means <no title>
    figureNo None means "current"
    """
    fig = _getFig(figureNo)

    fig.client.x_title.text=title
    fig.client.update()
def plotSetYTitle(title='', figureNo=None):
    """
    title = '' means <no title>
    figureNo None means "current"
    """
    fig = _getFig(figureNo)

    fig.client.y_title.text=title
    fig.client.update()

def plotSetAxis(setting='equal', figureNo=None):
    """
    set axis settings for both X and Y axes
    settings can be one of:
       'normal':
       'equal':
       'freeze':
       or 'tight' or'fit':
       or a 4-tuple (xMin,xMax,yMin,yMax)
      
    figureNo None means "current"
    """
    fig = _getFig(figureNo)
    fig.axis(setting)

def plotSetXAxis(bounds=('fit','fit', 'auto'), figureNo=None):
    """
    bounds is a tuple: (leftBound,rightBound, interval)
    [the third is optional]
    leftBound, rightBound can be one of:
       <a value>
       'auto'       (default) sets bound to near tickMark
       'fit'        sets bound to  "tightly" fit the datapoints
       None or ''   do not change
    interval can be one of:
       'auto'  (default) sets tick intervals "nicely" (linearly spaced)
       <a value>
    

    figureNo None means "current"
    """
    fig = _getFig(figureNo)

    if bounds[0] is None or bounds[0]=='':    #fixme - broken ?
        bounds[0] = fig.client.x_axis.bounds[0]
    if bounds[1] is None or bounds[1]=='':   #fixme - broken ?
        bounds[1] = fig.client.x_axis.bounds[1]

    fig.client.x_axis.bounds = bounds[:2]
    if len(bounds)>2:
            fig.client.x_axis.tick_interval = bounds[2]
    fig.client.update()

def plotSetYAxis(bounds=('fit','fit', 'auto'), figureNo=None):
    """
    bounds is a tuple: (leftBound,rightBound, interval)
    [the third is optional]
    leftBound, rightBound can be one of:
       <a value>
       'auto'       (default) sets bound to near tickMark
       'fit'        sets bound to  "tightly" fit the datapoints
       None or ''   do not change
    interval can be one of:
       'auto'  (default) sets tick intervals "nicely" (linearly spaced)
       <a value>
    

    figureNo None means "current"
    """
    fig = _getFig(figureNo)

    if bounds[0] is None or bounds[0]=='':       #fixme - broken ?
        bounds[0] = fig.client.y_axis.bounds[0]
    if bounds[1] is None or bounds[1]=='':       #fixme - broken ?
        bounds[1] = fig.client.y_axis.bounds[1]
    fig.client.y_axis.bounds = bounds[:2]
    if len(bounds)>2:
            fig.client.y_axis.tick_interval = bounds[2]
    fig.client.update()
                  




def plotSliderX(plotXWidth=None, xmax=None, figureNo=None):
    """
    xmax None means 'use "width" of dataset'
    
    plotXWidth None mean xmax/10
    figureNo None means "current"
    """
    fig = _getFig(figureNo)

    if xmax is None:
        xmax = max([len(ll.points) for ll in fig.client.line_list])

    if plotXWidth is None:
        plotXWidth = xmax // 10
    nz = xmax-plotXWidth
    if nz < 1:     # what now
        nz = xmax  # better idea ?

    from . import zslider

    if not hasattr(fig, "seb_xslider") or \
       not hasattr(fig.seb_xslider, "Show"):
        fig.seb_xslider = zslider.ZSlider(nz, title="x-slider for %s"%fig.GetTitle())
        fig.seb_xslider.SetSize((fig.GetSize()[0], -1))
        rect=fig.GetRect()
        fig.seb_xslider.SetPosition((rect[0],rect[1]+rect[3]+20)) # 20 is HACK ?for window-title-bar?
    fig.seb_xslider.zslider.SetRange(0, nz)
    fig.seb_xslider.doOnZchange = lambda x: plotSetXAxis(bounds=(x, x+plotXWidth, 'auto'), figureNo=None)





def plotFigure(which_one = None):
    """if which_one = None       : start a new plot window
       if which_one is 'integer' : select that figure as active
    """
    from . import plt
    try:
        return plt.figure(which_one)
        #if which_one is None:
        #    plothold(on=0)
    except wx.PyDeadObjectError: 
        print("** figure '%s' invalid - made new one **"%which_one)

def plotFigureGetNo(createNewIfNeeded=False):
    """
    return figureNo of current figure
    """
    from . import plt
    try:
        figNo = plt.interface._figure.index(plt.interface._active)
        if not plt.interface._figure[figNo]:
            raise RuntimeError("active figure was probably closed")
        return figNo
        
    except:
        if createNewIfNeeded:
            plotFigure()
            return plt.interface._figure.index(plt.interface._active)
        if plt.interface._active is None:
            raise RuntimeError("no figure window open (active)")
        raise

def plotRaise(figureNo=None):
    """bring current plotframe to the top"""
    fig = _getFig(figureNo)
    fig.Raise()

def plotClear(figureNo=None):
    """clear all graphs and images from current plot
    """
    # see interface: if not _active.hold in ['on','yes']:
    fig = _getFig(figureNo)

    fig.line_list.data = [] # clear it out
    fig.image_list.data = [] # clear it out
    try:
        del fig._sebCurrentColorIndex # reset colors 
    except AttributeError:
        pass
    fig.update()
    
def plotClose(which_one = None):
    """
    close plot window
    """
    from . import plt
    plt.close(which_one)

def plotxy(arr1,arr2=None,c=plot_defaultStyle, logY=False, logX=False, hold=None, smartTranspose=True, logZeroOffset=.01, figureNo=None):
    """
    arr1 is a "table" of x,y1,...,yn values
    if arr2 is given than arr1 contains only the x values
            and arr2 is "table" y1,...,y2
    if hold is not None:
        if hold is True
            turn plothold on before drawing
        else
            turn plothold off before drawing
    otherwise
        do nothing about current hold setting

    if logY or logX the respective axis is shown in log10 (after applying abs() and adding logZeroOffset)

    if smartTranspose:
        transpose tables if that makes fewer graphs with each more data-points

    if figureNo is not None:
       use that figure instead and switch back to current afterwards
    """
    arr1 = N.asarray( arr1 )

    if arr2 is not None:
        if type(arr2) == str:
            c = arr2
            arr2 = None
        else:
            arr2 = N.asarray( arr2 )
    
    if smartTranspose and len(arr1.shape) > 1 and arr1.shape[0] >  arr1.shape[1]:
        arr1 = N.transpose(arr1)

    if arr2 is None:
        arr2 = arr1[1:]
        arr1 = arr1[:1]
    elif smartTranspose and len(arr2.shape) > 1 and arr2.shape[0] >  arr2.shape[1]:
        arr2 = N.transpose(arr2)

    # 20040804
    if arr1.dtype.type == N.uint32:
        arr1 = arr1.astype( N.float64 )
    if arr2.dtype.type == N.uint32:
        arr2 = arr2.astype( N.float64 )
    # 20190410
    if N.iscomplexobj(arr1):
        arr1 = N.abs(arr1)
    if N.iscomplexobj(arr2):
        arr2 = N.abs(arr2)
        
    
    x=arr1
    arr=arr2

    if logX:
        x = N.log10(abs(x)+logZeroOffset)
    if logY:
        arr = N.log10(abs(arr)+logZeroOffset)

    from . import plt
    if figureNo is not None:
        _oldActive = plt.interface._active
        #plotFigure(figureNo)  # would Raise !!
        plt.interface._active = plt.interface._figure[figureNo]
        #fig = plt.interface._figure[figureNo]        

    if hold is not None:
        plothold(hold)


    if len(arr.shape) == 1:
        plt.plot(
            x, arr, _col(c))
    else:
        data = []
        for i in range(arr.shape[0]):
            data.extend( (x, arr[i], _col(c, overwriteHold=i>0)) )
            plt.plot( *data )

    if figureNo is not None:
        plt.interface._active = _oldActive

def ploty(arrY, c=plot_defaultStyle, logY=False, logX=False, hold=None, smartTranspose=True, logZeroOffset=.01, figureNo=None, symbolSize=0):
    """
    arrY is a "table" of y1,...,yn values
    x-values of 0,1,2,3,4 are used as needed

    if hold is not None:
        if hold is True
            turn plothold on before drawing
        else
            turn plothold off before drawing
    otherwise
        do nothing about current hold setting

    if logY or logX the respective axis is shown in log10 (after applying abs() and adding logZeroOffset)

    if smartTranspose:
        transpose tables if that makes fewer graphs with each more data-points

    if figureNo is not None:
       use that figure instead and switch back to current afterwards
    """
    arrY = N.asarray( arrY )

    if hold is not None:
        plothold(hold, figureNo)

    if len(arrY.shape) == 1 and not logX:
        #if logX:
        #    raise ValueError, 'Cannot use logX=True to plot x="axis-index"'
        #plotxy(arrY) # CHECK
        from . import plt
        if figureNo is not None:
            _oldActive = plt.interface._active
            #plotFigure(figureNo)  # would Raise !!
            plt.interface._active = plt.interface._figure[figureNo]
            #fig = plt.interface._figure[figureNo]        
        

        if logY:
            arrY = N.log10(abs(arrY)+logZeroOffset)
        if N.iscomplexobj(arrY):
            arrY = N.abs(arrY)
        plt.plot(arrY, _col(c))
        if figureNo is not None:
            plt.interface._active = _oldActive

    else:
        if len(arrY.shape) == 1: # !! logX is True
            n = arrY.shape[0]
            x = N.arange(n)
        else:
            if smartTranspose and arrY.shape[0] > arrY.shape[1]:
                arrY = N.transpose(arrY)
            n = arrY.shape[1]
            x = N.arange(n)
        plotxy(x, arrY,c, logY, logX, smartTranspose=smartTranspose, logZeroOffset=logZeroOffset, figureNo=figureNo)

def plothold(on=1, figureNo=None):
    fig = _getFig(figureNo)
    
    fig.hold = on and "on" or "off"

    #if on:   plt.hold("on")
    #else:    plt.hold("off")
    #global _plotholded
    #_plotholded = on

def plotsave(fn=None, format='png', figureNo=None):
    """
    save "screenshot"(?) of plot
    if fn is None calls FN() for you
    """
    
    if fn is None:
        from Priithon.usefulX import FN
        fn = FN(1)
        if not fn:
            return 

    fig = _getFig(figureNo)
    fig.save(fn, format)

# 20070927:  not used
# def maparr(arr, fn, width, dtype=N.float64):
#     out = N.array( shape=(arr.shape[0], width), dtype=dtype)
#     for i in range(arr.shape[0]):
#         out[i] = apply(fn, (arr[i],) )

#     return out
# def maparrt(arr, fn, width, dtype=N.float64):
#     out = N.empty( shape=(arr.shape[1], width), dtype=dtype)
#     for i in range(arr.shape[1]):
#         out[i] = apply(fn, (arr[:,i],) )

#     return out

def plotMouse__graph2window(pts, figureNo=None):
    fig = _getFig(figureNo)

    pc = fig.client                   # canvas
    return pc.graph_to_window(pts)
    
def plotMouse__window2graph(p, figureNo=None):
    fig = _getFig(figureNo)

    pc = fig.client                   # canvas
    gb = pc.graph_box

    x,y = p
    left = float(x - gb.left()) / gb.width()
    top =  float(y - gb.top()) / gb.height()
    # convert to real bounds
    width = pc.x_axis.ticks[-1] - pc.x_axis.ticks[0]
    height = pc.y_axis.ticks[-1] - pc.y_axis.ticks[0]
    left = left * width + pc.x_axis.ticks[0]
    top = pc.y_axis.ticks[-1] - top * height

    return left,top

def plotMouseEventHandlerSet(handler=None, figureNo=None):
    """
    if handler is None: reset to default mouse handler (zooming)

    exampler `handler`:
      def h(evt):
         p = evt.GetPosition()
         if evt.LeftDown():
            print plotMouse__window2graph(p)
    """
    fig = _getFig(figureNo)
    #import wx

    pc = fig.client                   # canvas

    if handler is None:
        handler = pc.on_mouse_event
    
    wx.EVT_LEFT_DOWN(pc, handler)
    wx.EVT_LEFT_UP(pc, handler)
    wx.EVT_MOTION(pc, handler)
    wx.EVT_MOTION(pc, handler)

def plotMouseEventHandlerSet_fct_XY_OnLeft(fct_XY, onlyOnClick=True, figureNo=None):
    """
    shortcut for handler functions as shown as example in
    mouseEventHandlerSet;
    if onlyOnClick is False, call fct when LeftIsDown,
         i.e. also while moving when button kept down
    
    example `fct_XY`
      def fct_XY(x,y):
         print x,y
    """
    
    def h(evt):
        p = evt.GetPosition()
        if onlyOnClick:
            if evt.LeftDown():
                x,y = plotMouse__window2graph(p, figureNo)
                fct_XY(x,y)
        else:
            if evt.LeftIsDown():
                x,y = plotMouse__window2graph(p, figureNo)
                fct_XY(x,y)
                
    plotMouseEventHandlerSet(h, figureNo)
