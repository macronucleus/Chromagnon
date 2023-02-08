import sys
from .seb import *
from numpy import *
from . import wxplt
import six


from . import plot_objects

plot_module = wxplt
#seb plot_class = gui_thread.register(plot_module.plot_frame)
plot_class = plot_module.plot_frame

_figure = []
_active = None
_parent = None # added 20220908

def figure(which_one = None):
    global _figure; global _active
    if which_one is None:
        title ='Figure %d' % len(_figure)
        _figure.append(plot_class(title=title, parent=_parent)) # parent added 20220908
        _active = _figure[-1]
    elif (type(which_one) == type(1)) or (type(which_one) == type(1.)):
        try:    
            _active = _figure[int(which_one)]
            _active.Raise()
        except IndexError:
            msg = "There are currently only %d active figures" % len(_figure)
            raise IndexError(msg)
    elif which_one in _figure:
        _active = which_one
        _active.Raise()
    else:
        try:
            if which_one.__type_hack__ == "plot_canvas":
                _active = which_one
                _figure.append(_active)
                _active.Raise()
            else:
                raise ValueError("The specified figure or index is not not known")
        except (AttributeError):
            pass
    fig = current()
    return fig
    
    
def validate_active():
    global _active
    if _active is None: figure()
    try:
        notworking="""
        # seb-20050723-noGui_Thread if not _active.proxy_object_alive:
        if not hasattr(_active, 'Show'): # is _active wxFrame not deleted ?
            _active = None
            figure()"""
        _active.IsActive() # -> wx error
        #figure()
    except:
        _active = None  # seb-20040824
        figure()        # seb-20040824
        pass
    
def current():
    return _active

#seb   20080901 - this ( redraw() )appears to be broken: 
#      ..../plt/wxplt.py", line 806, in __getattr__
#      AttributeError: 'plot_canvas' object has no attribute 'redraw'
def redraw():
    validate_active()
    _active.redraw()

def close(which_one = None):
    global _figure; global _active
    if which_one is None:
        try:
            _active.Close()
            _figure.remove(_active)
        except ValueError:
            pass
            
        try: 
            # should make sure the new plot window really exist
            set_new_active()
        except IndexError: _active = None
    elif which_one == 'all':
        for fig in _figure: fig.Close()
        _active = None
    else:
        raise NotImplementedError("currently close only works with"\
                                   " _active window or 'all'")
        #try: 
        #   _figure.remove(which_one)
        #   which_one.close()
        #except ValueError:
        #   which_one.close() 

def set_new_active():
    # should validate new active here
    try:
        _active = _figure[-1]
    except IndexError:
        _active = None    
        

def _auto_all():
    validate_active()
    _active.x_axis.bounds = ['auto','auto']
    _active.y_axis.bounds = ['auto','auto']
    _active.x_axis.tick_interval = 'auto'
    _active.y_axis.tick_interval = 'auto'    
def autoscale():
    validate_active()
    _auto_all()
    _active.update()

def _an_axis(ax,setting):
    ticks = ax.ticks
    interval = ax.ticks[1]- ax.ticks[0]
    if setting in ['normal','auto']:
        ax.bounds = ['auto','auto']
    elif setting == 'freeze':
        ax.bounds = [axes[0],axes[1]]
        ax.tick_interval = interval
    elif setting in ['tight','fit']:
        ax.bounds = ['fit','fit']
        ax.tick_interval = 'auto'
    else:
        ax.bounds = [setting[0],setting[1]]
        if len(setting) > 2:
            ax.tick_interval = setting[2]
            
def xaxis(rng):
    validate_active()
    _an_axis(_active.x_axis,rng)
    _active.update()
    
def yaxis(rng):
    validate_active()
    _an_axis(_active.y_axis,rng)
    _active.update()

def title(name):
    validate_active()
    #seb _active.title.text = name
    #seb _active.update()
    _active.client.title.text = name
    _active.client.update()

def xtitle(name):
    validate_active()
    _active.x_title.text = name
    _active.update()

def ytitle(name):
    validate_active()
    _active.y_title.text = name
    _active.update()

on = 'on'
off = 'off'
def grid(state=None):
    validate_active()
    if state is None:
        if _active.x_axis.grid_visible in ['on','yes']:
            _active.x_axis.grid_visible = 'off'
            _active.y_axis.grid_visible = 'off'
        else:
            _active.x_axis.grid_visible = 'on'
            _active.y_axis.grid_visible = 'on'
    elif state in ['on','off','yes','no']:
        _active.x_axis.grid_visible = state
        _active.y_axis.grid_visible = state
    else:
        raise ValueError('grid argument can be "on","off",'\
                          '"yes","no". Not ' + state)        
    _active.update()

def hold(state):
    validate_active()
    if state in ['on','off','yes','no']:
        _active.hold = state
    else:
        raise ValueError('holds argument can be "on","off",'\
                          '"yes","no". Not ' + state)        
    
def axis(setting):
    validate_active()
    x_ticks = _active.x_axis.ticks
    #CHECK print type(x_ticks), dir(x_ticks)    
    x_interval = float(x_ticks[1]- x_ticks[0])
    y_ticks = _active.y_axis.ticks
    y_interval = float(y_ticks[1]- y_ticks[0])
    axes = array((x_ticks[0],x_ticks[-1],y_ticks[0],y_ticks[-1]),float64)
    # had to use client below cause of __setattr__ troubles in plot_frame
    if setting == 'normal':
        _active.client.aspect_ratio = setting
        _auto_all()
        self.x_axis.bounds = ['auto','auto']
        self.y_axis.bounds = ['auto','auto']
        self.x_axis.tick_interval = 'auto'
        self.y_axis.tick_interval = 'auto'    

    elif setting == 'equal':
        _active.client.aspect_ratio = setting    
    elif setting == 'freeze':
        _active.x_axis.bounds = [axes[0],axes[1]]
        _active.y_axis.bounds = [axes[2],axes[3]]
        _active.x_axis.tick_interval = x_interval
        _active.x_axis.tick_interval = y_interval        
    elif setting in ['tight','fit']:
        _active.x_axis.bounds = ['fit','fit']
        _active.y_axis.bounds = ['fit','fit']
        _active.x_axis.tick_interval = 'auto'
        _active.x_axis.tick_interval = 'auto'
    else:
        _active.x_axis.bounds = [setting[0],setting[1]]
        _active.y_axis.bounds = [setting[2],setting[3]]
    _active.update()    

def save(file_name,format='png'):
    _active.save(file_name,format)


##########################################################
#----------------- plotting machinery -------------------#
##########################################################

#---- array utilities ------------

def is1D(a):
    ashape = shape(a)
    if(len(ashape) == 1):
        return 1
    if(ashape[0] == 1 or ashape[1]==1):
        return 1
    return 0
    
def row(a):
    return reshape(asarray(a),[1,-1])
def col(a):
    return reshape(asarray(a),[-1,1])

class SizeMismatch(Exception):
    pass
class SizeError(Exception):
    pass
#SizeMismatch = 'SizeMismatch'
#SizeError = 'SizeError'
NotImplemented = 'NotImplemented'

#------------ Numerical constants ----------------

# really should do better than this...
BIG = 1e20
SMALL = 1e-20

#------------ plot group parsing -----------------
#from types import *

def plot_groups(data):
    remains = data; groups = []
    while len(remains):
        group,remains = get_plot_group(remains)
        groups.append(group)
    return groups        
    
def get_plot_group(data):
    group = ()
    remains = data
    state = 0
    finished = 0
    while(len(remains) > 0 and not finished):
        el = remains[0]
        if(state == 0):
            el = asarray(el)
            state = 1 
        elif(state == 1):
            if isinstance(el, six.string_types):
                finished = 1
            else:
                el = asarray(el)
            state = 2
        elif(state == 2):
            finished = 1
            if not isinstance(el, six.string_types):
                break
        try:
            if el.typecode() == 'D':
                print('warning plotting magnitude of complex values')
                el = abs(el)
        except:
            pass
        group = group + (el,)
        remains = remains[1:]       
    return group, remains           

#20060726  - now in numpy
#20060726 def hstack(tup):
#20060726   #horizontal stack (column wise)
#20060726   return concatenate(tup,1)

# #20060824 BUT numpy doesn't like float32 together with int32
# #HACK
# def hstack(tup):
#     #horizontal stack (column wise)
#     tup = N.astup[0], dtype=tup[1].dtype), tup[1]
#     return concatenate(tup,1)

def lines_from_group(group):
    lines = []
    plotinfo = ''
    x = group[0]
    ar_num = 1
    if len(group) > 1:
        if isinstance(group[1], six.string_types):
            plotinfo = group[1]
        else:
            ar_num = 2
            y = group[1]
    if len(group) == 3:
        plotinfo = group[2]
    #force 1D arrays to 2D columns
    if is1D(x): 
        x = col(x)
    if ar_num == 2 and is1D(y):  
        y = col(y)
    
    xs = shape(x)            
    if ar_num == 2:  ys = shape(y)
    #test that x and y have compatible shapes
    if ar_num == 2:
        #check that each array has the same number of rows
        if(xs[0] != ys[0] ):
            raise SizeMismatch('rows', xs, ys)
        #check that x.cols = y.cols
        #no error x has 1 column
        if(xs[1] > 1 and xs[1] != ys[1]):
            raise SizeMismatch('cols', xs, ys)
    
    #plot x against index
    if(ar_num == 1):
        for y_data in transpose(x):
            index = arange(len(y_data), dtype=dtypeBigEnough(y_data) )#dtype HACK: numpy doesn't like float32 together with int32
            pts = hstack(( col(index), col(y_data) ))
            pts = remove_bad_vals(pts)
            line = plot_module.line_object(pts)            
            lines.append(line)
    #plot x vs y                    
    elif(ar_num ==2):
        #x is effectively 1D
        if(xs[1] == 1):
            for y_data in transpose(y):
                xx = x.astype(dtypeBigEnough(y_data) )#dtype HACK: numpy doesn't like float32 together with int32
                pts = hstack(( col(xx), col(y_data) ))
                pts = remove_bad_vals(pts)
                line = plot_module.line_object(pts)
                lines.append(line)
        #x is 2D                    
        else:
            x = transpose(x); y = transpose(y)
            for i in range(len(x)):
                pts = hstack(( col(x[i]), col(y[i]) ))
                pts = remove_bad_vals(pts)
                line = plot_module.line_object(pts)
                lines.append(line)
    color,marker,line_type = process_format(plotinfo)
    #print color,marker,line_type
    for line in lines:
        if color != 'auto':
            line.color = 'custom'
            line.set_color(color)
            #print color
        if not marker:
            line.marker_type = 'custom'
            line.markers.visible = 'no'
            #print marker
        elif marker != 'auto':
            line.marker_type = 'custom'
            line.markers.symbol = marker
            line.markers.visible = 'yes'
            #print marker
        if not line_type:
            line.line_type = 'custom'
            line.line.visible = 'no'
        elif line_type != 'auto':
            line.line_type = 'custom'
            line.line.visible = 'yes'
            line.line.style = line_type
            #print line_type
        #print line.markers.visible,    line.line.visible,
    return lines

import re
color_re = re.compile('[ymcrgbwk]')
color_trans = {'y':'yellow','m':'magenta','c':'cyan','r':'red','g':'green',
               'b':'blue', 'w':'white','k':'black'}
# this one isn't quite right               
marker_re = re.compile('[ox+s^v]|(?:[^-])[.]')
marker_trans = {'.':'dot','o':'circle','x':'cross','+':'plus','s':'square',
                '^':'triangle','v':'down_triangle'}

line_re = re.compile('--|-\.|[-:]')
line_trans = {'-':'solid',':':'dot','-.':'dot dash','--':'dash'}
def process_format(format):
    if format == '':
        return 'auto','auto','auto'
    color,marker,line = 'auto',None,None
    m = color_re.findall(format)
    if len(m): color = color_trans[m[0]]
    m = marker_re.findall(format)
    # the -1 takes care of 'r.', etc
    if len(m): marker = marker_trans[m[0][-1]]    
    m = line_re.findall(format)
    if len(m): line = line_trans[m[0]]
    return color,marker,line
    
def remove_bad_vals(x):
    # !! Fix axis order when interface changed.
    # mapping:
    #    NaN -> 0
    #    Inf -> limits.double_max
    #   -Inf -> limits.double_min
    y = nan_to_num(x)    
    #seb big = limits.double_max / 10
    #seb small = limits.double_min / 10
    big = big_for(x)  # was broken (OverflowError) for Float32
    small = small_for(x)
    y = clip(y,small,big)
    return y

def stem(*data):
    if len(data) == 1:
        n = arange(len(data[0]))
        x = data[0]
        ltype = ['b-','mo']
    if len(data) == 2:
        if type(data[1]) is bytes:
            ltype = [data[1],'mo']
            n = arange(len(data[0]))
            x = data[0]
        elif type(data[1]) in [list, tuple]:
            n = arange(len(data[0]))
            x = data[0]            
            ltype = data[1][:2]
        else:
            n = data[0]
            x = data[1]
            ltype = ['b-','mo']
    elif len(data) > 2:
        n = data[0]
        x = data[1]
        ltype = data[2]
        if type(ltype) is bytes:
            ltype = [ltype,'mo']
    else:
        raise ValueError("Invalid input arguments.")

    if len(n) != len(x):
        raise SizeMismatch('lengths', len(n), len(x))
    # line at zero:
    newdata = []
    newdata.extend([[n[0],n[-1]],[0,0],ltype[0]])

    # stems
    for k in range(len(x)):
        newdata.extend([[n[k],n[k]],[0,x[k]],ltype[0]])

    # circles
    newdata.extend([n,x,ltype[1]])
    keywds = {'fill_style': 'transparent'}
    return plot(*newdata,**keywds)
    
                           
    
def plot(*data,**keywds):
    groups = plot_groups(data)
    lines = []
    for group in groups:
        lines.extend(lines_from_group(group))
        #default to markers being invisible
        #lines[-1].markers.visible = 'no'
    # check for hold here
    for name in list(plot_objects.poly_marker._attributes.keys()):
        value = keywds.get(name)
        if value is not None:
            for k in range(len(lines)):
                exec('lines[k].markers.%s = value' % name)
    validate_active()
    if not _active.hold in ['on','yes']:
        _active.line_list.data = [] # clear it out
        _active.image_list.data = [] # clear it out
    for i in lines:
        _active.line_list.append(i)
    _active.update()                
    return _active

def markers(visible=None):
    pass

#-------------------------------------------------------------------#
#--------------------------- image ---------------------------------#
#-------------------------------------------------------------------#

def image(img,x=None,y=None,colormap = 'grey',scale='no'):
    """Colormap should really default to the current colormap..."""
    # check for hold here    
    validate_active()
    image = wxplt.image_object(img,x,y,colormap=colormap,scale=scale)    
    if not _active.hold in ['on','yes']:
        _active.line_list.data = [] # clear it out
        _active.image_list.data = [] # clear it out
        _active.image_list.append(image)
        try:
            axis('equal')
        except AttributeError:
            # cluge to handle case where ticks didn't exist when
            # calling axis()
            _active.client.layout_all()
            axis('equal')
    else:
        _active.image_list.append(image)
        _active.update()                
    return _active

def imagesc(img,x=None,y=None,colormap = 'grey'):
    image(img,x,y,colormap,scale='yes')
    
#matlab equivalence
xlabel = xtitle
ylabel = ytitle     

def speed_test():
    p = plot([1,2,3],'r:o')
    s1 = (200,200)
    s2 = (400,400)
    p.SetSize(s1)
    for i in range(20):
        if p.GetSizeTuple()[0] == 200: 
            p.SetSize(s2)
        else: 
            p.SetSize(s1)
