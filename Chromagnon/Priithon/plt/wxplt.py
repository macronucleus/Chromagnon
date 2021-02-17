import wx
import string
from numpy import *
import time

from .plot_utility import *
from .plot_objects import *

def loop():
    global bub
    bub.SetSize((400,400))
    for i in range(20):
        #if bub.GetSizeTuple()[0] ==400: bub.SetSize((200,200))
        #else: bub.SetSize((400,400))
        #bub.client.layout_all()
        bub.client.draw_graph_area()

# Issues:
#  -- Fix textobject.size() for non-90 degree rotations
#  -- Auto attributes haven't been fully thought through
#  -- Axis titles probably should be axis properties
#     This might save some current layout problems.
#  -- Little attention has been paid to round off errors.
#     Occassionly you'll see the consequences in a miss
#     placed grid line or slightly off markers, but overall
#     it's not so bad.
#  -- Could use a more sophisticated property setting scheme,
#     perhaps like graphite????  Anyway you can do bad things
#     such as assign a string instead of a text_object to
#     titles, etc.  This is bad.  Optional typing in future
#     Python would remove the need for fancy property type
#     checking system (I think).  Hope it comes to pass...
#  -- This should be split up into several modules.  Probably
#     a package.
#  -- Printing on windows does not print out line styles.  
#     Everything is printed as solid lines. argh!
#     Update: This seems like an issue with calling dc.SetUserScale
#     If this isn't called, the problem is fixed - but the graph is 
#     tiny!!!  Should I work out the appropriate scaling in draw()
#     or should the SetUserScale() method maintain line types?
#  -- Print Preview scaling is not correct.  Not sure why not,
#     but it looks lit the dc size is different the printer dc size.
#     How to fix?
#  -- Rotated text does not print with correct font type. Is this
#     a wxPython(windows) problem or mine?
#  -- Plot windows do not become top window when using gui_thread.

# To Add:
#  -- Legend
#  -- MouseDown support for changing fonts


#make this a box_object?


aspect_ratios = ['normal', 'equal']

#seb 
class plot_canvas(wx.Window,property_object):
    _attributes = {
       'background_color': ['light grey',colors,"Window background color" \
                                           " Currently broken"],
       'aspect_ratio': ['normal',aspect_ratios,"Set the axis aspect ratio"],
       'hold': ['off',['on','off'],"Used externally for adding lines to plot"],
     }

    __type_hack__ = "plot_canvas"
    
    #background color is not working...
    def __init__(self, parent, id = -1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, **attr):
        wx.Window.__init__(self, parent, id, pos,size)
        self.Bind(wx.EVT_PAINT, self.on_paint)

        property_object.__init__(self, attr)
        if wx.version().startswith('3'):
            background = wx.NamedColour(self.background_color)
        else:
            background = wx.Colour(self.background_color)
        self.backgroundBrush = wx.Brush(background)

        self.SetBackgroundColour(background) 
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM) # seb added: no flickering
        ##self.title = text_object('')
        ##self.x_title = text_object('')
        ##self.y_title = text_object('')
        self.title = text_window(self,'')
        self.x_title = text_window(self,'')
        self.y_title = text_window(self,'')
        self.all_titles = [self.title,self.x_title,self.y_title] #handy to have
        ##self.x_axis = axis_object(graph_location='above',rotate=0)        
        ##self.y_axis = axis_object(graph_location='right',rotate=90)
        self.x_axis = axis_window(self,graph_location='above',rotate=0)        
        self.y_axis = axis_window(self,graph_location='right',rotate=90)

        self.image_list = graphic_list()
        self.line_list = auto_line_list()  # make this the data object.
        self.legend = legend_object() 
        self.text_list = None  # list of text objects to place on screen
        self.overlays = None   # list of objects to draw on top of graph 
                               # (boxes, circles, etc.)
        ##self.y2_axis = axis_object(graph_location='left',rotate=90) 
        self.client_size = (0,0)
        # zoom selection helpers
        self._mouse_selection = 0
        self._mouse_selection_start = wx.Point(0,0)
        self._mouse_selection_stop = wx.Point(0,0)

        #20090603: zoom history
        self.zoom_hist = []
        self.zoom_hist_i=0
        self.on_zoom_forget()

        # mouse events
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_event)
        self.Bind(wx.EVT_LEFT_UP, self.on_mouse_event)
        self.Bind(wx.EVT_MOTION, self.on_mouse_event)
        self.Bind(wx.EVT_SIZE, self.update)

    # event handler

    def on_mouse_event(self, event):
        if event.LeftDown():
            # start zoom selection
            self._mouse_selection_start = event.GetPosition()
            self._mouse_selection_stop = event.GetPosition()
            self._mouse_selection = 1
        elif event.LeftUp() and self._mouse_selection:
            # zoom in
            self.zoom(event.GetPosition())
            self._mouse_selection = 0
        elif event.LeftIsDown() and self._mouse_selection:
            # update zoom selection
            self.rubberband(event.GetPosition())
        else:
            pass

    def on_auto_zoom(self,event):
        self.auto_zoom()    
    def on_prev_zoom(self,event):
        self.prev_zoom()    
    def on_next_zoom(self,event):
        self.next_zoom()    
    def on_zoom_forget(self,event=None):
        self.zoom_hist_i = -1 # force clearing of old hist
        self._saveZoomHist()


    def axis(self, setting):
        #seb:     # copy pasted from   interface.py::.axis(setting)
        #         except this is not just for "active" figure
        x_ticks = self.x_axis.ticks
        #CHECK print type(x_ticks), dir(x_ticks)    
        x_interval = float(x_ticks[1]- x_ticks[0])
        y_ticks = self.y_axis.ticks
        y_interval = float(y_ticks[1]- y_ticks[0])
        axes = array((x_ticks[0],x_ticks[-1],y_ticks[0],y_ticks[-1]),float64)
        # had to use client below cause of __setattr__ troubles in plot_frame
        if setting == 'normal':
            self.aspect_ratio = setting
            #plt.interface._auto_all()
            self.x_axis.bounds = ['auto','auto']
            self.y_axis.bounds = ['auto','auto']
            self.x_axis.tick_interval = 'auto'
            self.y_axis.tick_interval = 'auto'    
        elif setting == 'equal':
            self.aspect_ratio = setting    
        elif setting == 'freeze':
            self.x_axis.bounds = [axes[0],axes[1]]
            self.y_axis.bounds = [axes[2],axes[3]]
            self.x_axis.tick_interval = x_interval
            self.x_axis.tick_interval = y_interval        
        elif setting in ['tight','fit']:
            self.x_axis.bounds = ['fit','fit']
            self.y_axis.bounds = ['fit','fit']
            self.x_axis.tick_interval = 'auto'
            self.x_axis.tick_interval = 'auto'
        else:
            self.x_axis.bounds = [setting[0],setting[1]]
            self.y_axis.bounds = [setting[2],setting[3]]
        self._saveZoomHist()
        self.update()    

    def on_equal_aspect_ratio(self,event):
        self.axis(setting='equal')
    def on_any_aspect_ratio(self,event):
        self.axis(setting='normal')
    def on_axis_freeze(self,event):
        self.axis(setting='freeze')
    def on_axis_tight(self,event):
        self.axis(setting='tight')

    def on_paint(self, event):
        #self.draw(wx.PaintDC(self))
        self.draw(wx.BufferedPaintDC(self))  # seb: no flickering

    def on_right_down(self,event):
        menu_found = 0
        pos = event.GetX(),event.GetY()
        dc = wx.ClientDC(self)
        for title in self.all_titles:
            title.set_dc(dc) # this dc stuff is a pain...
            if title.contains(pos):
                title.format_popup(pos)
                break
                menu_found = 1
            title.clear_dc()
        if not menu_found:
            if self.x_axis.contains(pos,dc):
                self.x_axis.format_popup(pos)
            elif self.y_axis.contains(pos,dc):
                self.y_axis.format_popup(pos)
            else:
                self.format_popup(pos)

    def format_popup(self,pos):
        menu = wx.Menu()
        menu.Append(505, 'previous zoom', 'previous zoom')
        menu.Enable(505, len(self.zoom_hist) and self.zoom_hist_i>0)
        menu.Append(500, 'Auto Zoom', 'Auto Zoom')
        menu.Append(506, 'next zoom', 'next zoom')
        menu.Enable(506, len(self.zoom_hist) and self.zoom_hist_i<len(self.zoom_hist)-1)
        menu.Append(507, 'clear zoom history', 'clear zoom history')
        menu.Append(501, 'X-Y equal aspect ratio', 'X-Y equal - set aspect ratio to 1')
        menu.Append(502, 'X-Y any aspect ratio', 'X-Y equal - set aspect ratio to "normal"')
        menu.Append(503, 'make X-Y axes a tight fit', 'fit X-Y axes to a fraction of the grid spacing"')
        menu.Append(504, 'freeze X-Y axes bounds', 'freeze X-Y axes grid"')
        self.Bind(wx.EVT_MENU, self.on_prev_zoom, id=505)
        self.Bind(wx.EVT_MENU, self.on_next_zoom, id=506)
        self.Bind(wx.EVT_MENU, self.on_zoom_forget, id=507)
        self.Bind(wx.EVT_MENU, self.on_auto_zoom, id=500)
        self.Bind(wx.EVT_MENU, self.on_equal_aspect_ratio, id=501)
        self.Bind(wx.EVT_MENU, self.on_any_aspect_ratio, id=502)
        self.Bind(wx.EVT_MENU, self.on_axis_tight, id=503)
        self.Bind(wx.EVT_MENU, self.on_axis_freeze, id=504)
        #20090603 (called by default) menu.UpdateUI()
        if wx.version().startswith('3'):
            self.PopupMenuXY(menu) #20090603 (default mouse cursor pos) ,pos[0],pos[1])
        else:
            self.PopupMenu(menu)
    # workers
    
    def rubberband(self, new):
        """Delete previous selection band and paint new one."""
        if self._mouse_selection:
            dc = wx.ClientDC(self)
            dc.SetLogicalFunction(wx.XOR)
            dc.SetPen(wx.GREY_PEN)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            diff = self._mouse_selection_stop - self._mouse_selection_start
            dc.DrawRectangle(self._mouse_selection_start.x,
                             self._mouse_selection_start.y, diff.x, diff.y)
            self._mouse_selection_stop = new
            diff = self._mouse_selection_stop - self._mouse_selection_start
            dc.DrawRectangle(self._mouse_selection_start.x,
                             self._mouse_selection_start.y, diff.x, diff.y)

    def save(self,path,image_type):
        w,h = self.GetSizeTuple()
        bitmap = wx.EmptyBitmap(w,h)
        dc = wx.MemoryDC()
        dc.SelectObject(bitmap)
        #self.update()
        # The background isn't drawn right without this cluge.   
        #fill_color = get_color(self.background_color)
        fill_color = get_color('white')        
        dc.SetPen(wx.Pen(fill_color))
        dc.SetBrush(wx.Brush(fill_color)) #how to handle transparency???
        dc.DrawRectangle(0,0,w,h)
        dc.SetPen(wx.NullPen)
        dc.SetBrush(wx.NullBrush)
        # end cluge
        self.draw(dc)
        image = wx.ImageFromBitmap(bitmap)
        wx.InitAllImageHandlers()
        image.SaveFile(path,image_type_map[image_type])

    def layout_all(self,dc=None):
        #settingbackgroundcolors
        #background = wx.NamedColour(self.background_color)
        #if self.GetBackgroundColour() != background:
        #   self.SetBackgroundColour(background) 
           #self.Clear()
        #   print 'refreshing'  
        if not dc:
            dc = wx.ClientDC(self)
        if wx.version().startswith('3'):
            self.client_size = self.GetClientSizeTuple()#seb An array doesn't make sense as a truth value: array(self.GetClientSizeTuple())
        else:
            self.client_size = self.GetClientSize()
        # set the device context for all titles so they can
        # calculate their size
        for text_obj in self.all_titles:
            text_obj.set_dc(dc)
            
        graph_area = box_object((0,0),self.client_size)
        graph_area.inflate(.95) # shrink box slightly
        
        # shrink graph area to make room for titles
        graph_area = self.layout_border_text(graph_area)        
        # layout axis and graph data
        graph_area = self.layout_graph(graph_area,dc)
        # center titles around graph area.
        self.finalize_border_text(graph_area,dc)   
        self.graph_box = graph_area
        # clear the dc for all titles
        # ? neccessary ?
        for text_obj in self.all_titles:
            text_obj.clear_dc()
        self.layout_data()
        
        #self.legend.layout(self.line_list,graph_area,dc)
        
    def layout_border_text(self,graph_area):
        # Shrink graph area to make room for titles.
        # Also, specify where the text is to live
        # in realation to the graph.  This only
        # specifies one axis.  The other can only
        # be specified after the final graph area
        # is calculated.
        margin = 4
        graph_area.trim_top(self.title.height()+margin)
        graph_area.trim_bottom(self.x_title.height()+margin)            
        self.y_title.rotate = 90 # make sure it is rotated
        graph_area.trim_left(self.y_title.width()+margin)
        #this is just to make so extra room for axis labels
        #on the x axis...
        graph_area.trim_right(12)
        return graph_area

    def layout_data(self):    
        # get scale and offset
        axis_range = array((self.x_axis.range(),self.y_axis.range()),float64)
        axis_range[axis_range==0] = 1 # seb: ZeroDivisionError
        # negative y to account for positve down in window coordinates
        scale = self.graph_box.size() / axis_range * array((1.,-1.))
        offset = self.graph_to_window(array((0.,0.)))
        self.image_list.scale_and_shift(scale,offset)
        self.line_list.scale_and_shift(scale,offset)        
        #self.legend 
        #self.text_list
        #self.overlays
        
    def layout_graph(self,graph_area,dc):                        
        self.axes = []
        #data_x_bounds,data_y_bounds = [0,6.28], [-1.1,1000]
        #jeez this is unwieldy code...
        smalls = []; bigs =[]
        if len(self.line_list):
            p1,p2 =  self.line_list.bounding_box()
            smalls.append(p1);bigs.append(p2)
        if len(self.image_list):
            p1,p2 =  self.image_list.bounding_box()
            smalls.append(p1);bigs.append(p2)        
        if len(smalls):    
            min_point = minimum.reduce(smalls)
            max_point = maximum.reduce(bigs)
        else:
            min_point = array((-1.,-1.),)
            max_point = array((1.,1.))               
        data_x_bounds = array((min_point[0],max_point[0]))
        data_y_bounds = array((min_point[1],max_point[1]))
        self.x_axis.calculate_ticks(data_x_bounds)
        height = self.x_axis.max_label_height(dc)
        graph_area.trim_bottom(height)
        self.y_axis.calculate_ticks(data_y_bounds)
        width = self.y_axis.max_label_width(dc)
        graph_area.trim_left(width)
        if self.aspect_ratio == 'equal':
            x_scale = float(graph_area.width()) / self.x_axis.range()
            y_scale = float(graph_area.height()) / self.y_axis.range()
            #print 'scales:', x_scale,y_scale,self.x_axis.range(),self.y_axis.range()
            if x_scale > y_scale:
                new_width = y_scale * self.x_axis.range()
                remove = .5 * (graph_area.width() - new_width)
                graph_area.trim_left(remove)
                graph_area.trim_right(remove)
            else:    
                new_height = x_scale * self.y_axis.range()
                remove = .5 * (graph_area.height() - new_height)
                graph_area.trim_top(remove)
                graph_area.trim_bottom(remove)
        #self.y2_axis = axis_object(graph_location='left',rotate=90)
        #self.y2_axis.label_location = 'plus'
        #self.y2_axis.calculate_ticks(y2bounds)
        #width = self.y2_axis.max_label_width(dc)
        #graph_area.trim_right(width)
        self.x_axis.layout(graph_area,dc)
        self.x_axis.move((graph_area.left(),graph_area.bottom()))
        self.axes.append(self.x_axis)
        self.y_axis.layout(graph_area,dc)
        self.y_axis.move((graph_area.left(),graph_area.bottom()))
        self.axes.append(self.y_axis)
        #self.y2_axis.grid_color = 'wheat'
        #self.y2_axis.layout(graph_area,dc)
        #self.y2_axis.move((graph_area.right(),graph_area.bottom()))
        #self.axes.append(self.y2_axis)
        self.border = border_object()
        self.border.layout(graph_area,self.x_axis,self.y_axis)
        return graph_area
        
    def finalize_border_text(self,graph_area,dc):
        # Center the titles around the graph.
        # -- Really need to make axis object box_objects.
        #    Use this to help determine more appropriate 
        #    title location.  Current works fine
        #    if axis labels are beside graph.  Title
        #    will be to far away if they are in center of graph        
        margin = 4
        if self.title:   
            self.title.center_on_x_of(graph_area)
            self.title.above(graph_area,margin)
        if self.x_title: 
            offset = self.x_axis.max_label_height(dc)
            self.x_title.center_on_x_of(graph_area)
            self.x_title.below(graph_area,margin + offset)
        if self.y_title: 
            offset = self.y_axis.max_label_width(dc)
            self.y_title.center_on_y_of(graph_area)
            self.y_title.left_of(graph_area,margin+offset)
        #if self.y2_title:self.y2_title.center_on_y_of(graph_area)
    
    def graph_to_window(self,pts):
        axis_range =  array((self.x_axis.range(),self.y_axis.range()))
        axis_range[axis_range==0] = 1 # seb: ZeroDivisionError
        # negative y to account for positve down in window coordinates
        scale = self.graph_box.size() / axis_range * array((1.,-1.))
        graph_min = array((self.x_axis.ticks[0],self.y_axis.ticks[0]))
        zero_offset = (array((0.,0))- graph_min)  * scale 
        graph_offset = array((self.graph_box.left(),self.graph_box.bottom()))
        return pts * scale + zero_offset + graph_offset
                   
    def reset_size(self, dc = None):
        if wx.version().startswith('3'):
            new_size = self.GetClientSizeTuple()
        else:
            new_size = self.GetClientSize()
        if new_size != self.client_size:
            self.layout_all(dc)
            self.client_size = new_size

    def draw_graph_area(self,dc=None):
        if not dc: dc = wx.ClientDC(self)                                     
        self.layout_data() # just to check how real time plot would go...

        gb = self.graph_box
        #clear the plot area
        # SHOULD SET PEN HERE TO FILL BACKGROUND WITH CORRECT COLOR
        fill_color = get_color('white')
        dc.SetPen(wx.Pen(fill_color))
        dc.SetBrush(wx.Brush(fill_color))
        # NEEDED FOR REAL-TIME PLOTTING
        dc.DrawRectangle(gb.left(),gb.top(),
                         gb.width()+1,gb.height()+1)
        #needed to make sure images stay within bounds
        ##dc.SetClippingRegion(gb.left()-1,gb.top()-1,
        ##                     gb.width()+2,gb.height()+2)  # mod by GAP 26092003
        dc.SetClippingRegion(int(gb.left()-1),int(gb.top()-1),
                             int(gb.width()+2),int(gb.height()+2))
        # draw images
        self.image_list.draw(dc)
        dc.DestroyClippingRegion()        
        # draw axes lines and tick marks               
        #t1 = time.clock()    
        for axis in self.axes:
            axis.draw_lines(dc)
        #for axis in self.axes:
        #    axis.draw_grid_lines(dc)
        #for axis in self.axes:
        #    axis.draw_ticks(dc)    
        #t2 = time.clock()
        #print 'lines:', t2 - t1
        #draw border
        #t1 = time.clock(); self.border.draw(dc); t2 = time.clock()
        #print 'border:', t2 - t1                    
        # slightly larger clipping area so that marks
        # aren't clipped on edges
        # should really clip markers and lines separately
        # draw lines
        self.line_list.clip_box(self.graph_box)
        self.line_list.draw(dc)
        # draw text        
        # draw legend
        # self.legend.draw(dc)
        # draw overlay objects
        
    def draw(self,dc=None):
        #if not len(self.line_list) or len(self.image_list):
        #    return
        # resize if necessary
        #print 'draw'
        #print 'dc:',dc
        #t1 = time.clock();;t2 = time.clock()
        self.reset_size(dc)
        #print 'resize:',t2 - t1        
        if not dc: dc = wx.ClientDC(self)
        dc.SetBackground( self.backgroundBrush ) #seb  added: no flickering
        dc.Clear()                               #seb  added: no flickering

        # draw titles and axes labels
        #t1 = time.clock()    
        for text in self.all_titles:
            text.draw(dc)        
        for axis in self.axes:
            axis.draw_labels(dc)
        #t2 = time.clock()
        #print 'text:',t2 - t1
        self.draw_graph_area(dc)
            
    def update(self,event=None):
        self.client_size = (0,0) # forces the layout
        self.Refresh()

    def _saveZoomHist(self):
        self.zoom_hist = self.zoom_hist[:self.zoom_hist_i+1] + [
            (self.x_axis.bounds, self.y_axis.bounds, 
             self.x_axis.tick_interval, self.y_axis.tick_interval, 
             self.aspect_ratio)
            ]
        self.zoom_hist_i = len(self.zoom_hist)-1 # points to (current) hist index, where new zooms are appended
    def _setFromZoomHist(self):
        (self.x_axis.bounds, self.y_axis.bounds, 
         self.x_axis.tick_interval, self.y_axis.tick_interval,
         self.aspect_ratio) = self.zoom_hist[self.zoom_hist_i]
        
    def auto_zoom(self):
        # zoom to full scale
        # cannot call autoscale(), since validate_active() apparently
        # leads to a race condition:(
        self.x_axis.bounds = ['auto','auto']
        self.y_axis.bounds = ['auto','auto']
        self.x_axis.tick_interval = 'auto'
        self.y_axis.tick_interval = 'auto'

        self._saveZoomHist()
        self.update()
    def prev_zoom(self):
        
        self.zoom_hist_i -= 1
        if self.zoom_hist_i < 0:
            self.zoom_hist_i += len(self.zoom_hist)
        
        self._setFromZoomHist()
        self.update()
    def next_zoom(self):
        
        #self.x_axis.bounds = ['auto','auto']
        #self.y_axis.bounds = ['auto','auto']
        #self.x_axis.tick_interval = 'auto'
        #self.y_axis.tick_interval = 'auto'
        self.zoom_hist_i += 1
        if self.zoom_hist_i >= len(self.zoom_hist):
            self.zoom_hist_i = 0
        
        self._setFromZoomHist()
        self.update()
    
    def zoom(self, stop):
        """Delete selection band and zoom selection to full scale."""
        # delete rubberband
        dc = wx.ClientDC(self)
        dc.SetLogicalFunction(wx.XOR)
        dc.SetPen(wx.GREY_PEN)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        diff = self._mouse_selection_stop - self._mouse_selection_start
        dc.DrawRectangle(self._mouse_selection_start.x,
                         self._mouse_selection_start.y, diff.x, diff.y)
        self._mouse_selection_stop = stop
        # get zoom-area coordinates
        p1 = self._mouse_selection_start
        p2 = self._mouse_selection_stop
        gb = self.graph_box
        if abs(p1.x-p2.x) < 3 and abs(p1.y-p2.y) < 3:
            # zoom aborted (we assume)
            return
        left = float(min(p1.x, p2.x) - gb.left()) / gb.width()
        right = float(max(p1.x, p2.x) - gb.left()) / gb.width()
        top = float(min(p1.y, p2.y) - gb.top()) / gb.height()
        bottom = float(max(p1.y, p2.y) - gb.top()) / gb.height()
        # convert to real bounds
        width = self.x_axis.ticks[-1] - self.x_axis.ticks[0]
        height = self.y_axis.ticks[-1] - self.y_axis.ticks[0]
        left = left * width + self.x_axis.ticks[0]
        right = right * width + self.x_axis.ticks[0]
        top = self.y_axis.ticks[-1] - top * height
        bottom = self.y_axis.ticks[-1] - bottom * height
        x_int = auto_interval([left, right])
        y_int = auto_interval([bottom,top])

        self.x_axis.bounds = auto_bounds([left, right],x_int)
        self.y_axis.bounds = auto_bounds([bottom, top],y_int)
        self._saveZoomHist()

        self.update()




#------------------ tick utilities -----------------------
# flexible log function
#------------------ end tick utilities -----------------------

class graph_printout(wx.Printout):
    """Print wrapper."""
    # Do not change method names in this class,
    # we have to override wxPrintout methods here!
    def __init__(self, graph):
        wx.Printout.__init__(self)
        self.graph = graph

    def HasPage(self, page):
        if page == 1:
            return True
        else:
            return False

    def GetPageInfo(self):
        return (1, 1, 1, 1)

    def OnPrintPage(self, page):
        dc = self.GetDC()
        # .5 inch margins are automatic
        # on my HP.  Probably not standard.
        # Need smarter margin control.
        w_inch,h_inch = self.GetPPIPrinter()
        x_margin = .0* w_inch
        y_margin = .0* h_inch
        #-------------------------------------------
        # One possible method of setting scaling factors...
        #print w_inch,h_inch
        #print dc.GetSizeTuple()        
        graph_box = box_object((0,0),self.graph.GetSizeTuple())
        # Get the size of the DC in pixels
        page_size = dc.GetSizeTuple()
        #print 'dc size:',page_size
        #page_size = self.GetPageSizePixels()
        #print 'page size:',page_size
        print_box = box_object((0,0),page_size)        
        print_box.trim_left(x_margin)
        print_box.trim_right(x_margin)
        print_box.trim_top(y_margin)
        print_box.trim_bottom(y_margin)
        # Calculate a suitable scaling factor
        scales = array(print_box.size(), float64)/graph_box.size()
        # Use x or y scaling factor, whichever fits on the DC
        scale = min(scales)
        # resize the graph and center on the page
        graph_box.inflate(scale)
        graph_box.center_on(print_box)
        # set the device scale and origin
        dc.SetUserScale(scale, scale)
        dc.SetDeviceOrigin(graph_box.left(),graph_box.top())
        #-------------------------------------------
        #print 'print dc size:', dc.GetSizeTuple()
        self.graph.draw(dc)
        return True


class plot_window(plot_canvas):
    """Plot canvas window.

    This is a complete q+d hack, but it does (somewhat) work.
    """
    def __init__(self, parent, id = -1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize,**attr):
        plot_canvas.__init__(self, parent, id, pos, size)
        self.parent = parent
        self.proxy_object_alive = True
        scipy.plt.figure(self)
        self.layout_all()
        scipy.plt.xaxis('fit')
        # initial print setup
        self.print_data = wx.PrintData()
        self.print_data.SetPaperId(wx.PAPER_LETTER)
        self.print_data.SetOrientation(wx.LANDSCAPE)

    def add(self, x, y, **keywds):
        """Add data to plot."""
        groups = scipy.plt.plot_groups([x, y, 'b-'])
        lines = []
        for group in groups:
            lines.extend(scipy.plt.lines_from_group(group))
        # check for hold here
        for name in list(plot_objects.poly_marker._attributes.keys()):
            value = keywds.get(name)
            if value is not None:
                for k in range(len(lines)):
                    exec('lines[k].markers.%s = value' % name)
        for i in lines:
            self.line_list.append(i)
        self.update();

    def clear(self):
        """Clear canvas, remove all plots."""
        self.line_list = auto_line_list()
        scipy.plt.autoscale()

    def set_title(self, title):
        """Set plot title."""
        self.title = text_window(self, title)
        self.all_titles[0] = self.title
        self.update()
        
    def set_xaxis_title(self, xtitle):
        """Set x-axis title"""
        self.x_title = text_window(self, xtitle)
        self.all_titles[1] = self.x_title
        self.update()

    def set_yaxis_title(self, ytitle):
        """Set y-axis title"""
        self.y_title = text_window(self, ytitle)
        self.all_titles[2] = self.y_title
        self.update()

    def printout(self, paper=None):
        """Print current plot."""
        if paper != None:
            self.print_data.SetPaperId(paper)
        pdd = wx.PrintDialogData()
        pdd.SetPrintData(self.print_data)
        printer = wx.Printer(pdd)
        out = graph_printout(self)
        print_ok = printer.Print(self.parent, out)
        if print_ok:
            self.print_data = printer.GetPrintDialogData().GetPrintData()
        out.Destroy()

    def print_preview(self):
        """Print-preview current plot."""
        printout = graph_printout(self)
        printout2 = graph_printout(self)
        self.preview = wx.PrintPreview(printout, printout2, self.print_data)
        if not self.preview.Ok():
            wx.MessageDialog(self, "Print Preview failed.\n" \
                               "Check that default printer is configured\n", \
                               "Print error", wx.OK|wx.CENTRE).ShowModal()
        else:
            frame = wx.PreviewFrame(self.preview, self.parent, "Preview")
            frame.Initialize()
            frame.SetPosition(self.GetPosition())
            frame.SetSize(self.GetSize())
            frame.Show(True)


class plot_frame(wx.Frame):
    """wxFrame for interactive use of plot_canvas."""
    TITLE_FONT = 210
    AXIS_FONT = 211
    LABEL_FONT = 212
    
    TITLE_TEXT,X_TEXT,Y_TEXT = 220,221,222

    default_size = (500,400) # the default on Linux is always tiny???
    
    def __init__(self, parent=None, id = -1, title = '', 
                 pos=wx.DefaultPosition,
                 size=default_size,visible=1):
        wx.Frame.__init__(self, parent, id, title,pos,size)
        # seb-20040824 wx.EVT_CLOSE(self, self.OnCloseWindow) #added by BEC
        # Now Create the menu bar and items
        self.mainmenu = wx.MenuBar()
        menu = wx.Menu()
        menu.Append(200, '&Save As...', 'Save plot to image file')
        self.Bind(wx.EVT_MENU, self.file_save_as, id=200)
        menu.Append(201, '&Save As CSV ...', 'Save plot to CSV text file')
        self.Bind(wx.EVT_MENU, self.file_save_csv, id=201)
        menu.Append(203, '&Print...', 'Print the current plot')
        self.Bind(wx.EVT_MENU, self.file_print, id=203)
        menu.Append(204, 'Print Pre&view', 'Preview the current plot')
        self.Bind(wx.EVT_MENU, self.file_preview, id=204)
        menu.Append(205, 'Close', 'Close plot')
        self.Bind(wx.EVT_MENU, self.file_close, id=205)
        self.mainmenu.Append(menu, '&File')
        menu = wx.Menu()
        menu.Append(self.TITLE_TEXT, '&Graph Title', 'Title for plot')
        self.Bind(wx.EVT_MENU, self.title, id=self.TITLE_TEXT)
        menu.Append(self.X_TEXT, '&X Title', 'Title for X axis')
        self.Bind(wx.EVT_MENU, self.title, id=self.X_TEXT)
        menu.Append(self.Y_TEXT, '&Y Title', 'Title for Y axis')
        self.Bind(wx.EVT_MENU, self.title, id=self.Y_TEXT)
        self.mainmenu.Append(menu, '&Titles')
        #menu = wx.Menu()        
        #menu.Append(300, '&Profile', 'Check the hot spots in the program')
        #wx.EVT_MENU(self,300,self.OnProfile)
        #self.mainmenu.Append(menu, '&Utility')
        self.SetMenuBar(self.mainmenu)
        # A status bar to tell people what's happening
        self.CreateStatusBar(1)
        self.print_data = wx.PrintData()
        self.print_data.SetPaperId(wx.PAPER_LETTER)
        self.client = plot_canvas(self)
        if visible: self.Show(1)
        self.Raise()
        self.SetFocus()        
                    
    def plot_draw(self, event):
        #self.client.graphics = _InitObjects()
        self.client.title.text = 'Bubba'
        self.client.x_title.text = 'x title'
        self.client.y_title.text = 'y title'
        #self.client.y2_title.text = 'y2 title'
        for i in _InitObjects():
            self.client.line_list.append(i)
        #self.client.image_list.append(lena_obj())    
        self.client.draw();


    def profile(self, event):
        import profile
        #self.client.graphics = _InitObjects()
        self.client.title.text = 'Bubba'
        self.client.x_title.text = 'x title'
        self.client.y_title.text = 'y title'
        #self.client.y2_title.text = 'y2 title'
        #for i in _InitObjects():
        #    self.client.line_list.append(i)
        #self.client.image_list.append(lena_obj())    
        global bub
        bub = self
        profile.run('from plt import loop;loop()','profile')        
        
    def file_print(self, event):
        self.print_data.SetPaperId(wx.PAPER_LETTER)
        pdd = wx.PrintDialogData()
        pdd.SetPrintData(self.print_data)
        printer = wx.Printer(pdd)
        printout = graph_printout(self.client)
        print_ok = printer.Print(self, printout)
        #Is Abort() not wrapped?
        #if not printer.Abort() and not print_ok:     
        #    wx.MessageBox("There was a problem printing.\n" \
        #                    "Perhaps your current printer is not set correctly?",
        #                    "Printing", wx.OK)
        #else:
        #    self.print_data = printer.GetPrintDialogData().GetPrintData()
        if print_ok:
            self.print_data = printer.GetPrintDialogData().GetPrintData()
        printout.Destroy()

    def file_preview(self, event):
        printout = graph_printout(self.client)
        printout2 = graph_printout(self.client)
        self.preview = wx.PrintPreview(printout, printout2, self.print_data)
        if not self.preview.Ok():
            #self.log.WriteText("Print Preview failed." \
            #                   "Check that default printer is configured\n")
            print("Print Preview failed." \
                  "Check that default printer is configured\n")
            return
        frame = wx.PreviewFrame(self.preview, self, "Preview")
        frame.Initialize()
        frame.SetPosition(self.GetPosition())
        frame.SetSize(self.GetSize())
        frame.Show(True)

    def file_save_as(self, event):
        import os
        wildcard = "PNG files (*.png)|*.png|" \
                   "BMP files (*.bmp)|*.bmp|" \
                   "JPEG files (*.jpg)|*.jpg|" \
                   "PCX files (*.pcx)|*.pcx|" \
                   "TIFF files (*.tif)|*.tif|" \
                   "All Files |*"
        dlg = wx.FileDialog(self, "Save As", ".", "", wildcard, wx.FD_SAVE)#SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            f = dlg.GetPath()
            dummy, ftype = os.path.splitext(f)
            # strip .
            ftype = ftype[1:]
            if ftype in list(image_type_map.keys()):
                self.client.save(dlg.GetPath(),ftype)
            else:
                msg = "Extension is currently used to determine file type." \
                      "'%s' is not a valid extension."  \
                      "You may use one of the following extensions. %s" \
                          % (ftype,list(image_type_map.keys()))   
                d = wx.MessageDialog(self,msg,style=wx.OK)
                d.ShowModal()
                d.Destroy()
        dlg.Destroy()

    def file_save_csv(self, event, csv_sep='\t'):
        import os
        wildcard = "CSV files (*.csv)|*.csv|" \
                   "BMP files (*.tsv)|*.tsv|" \
                   "JPEG files (*.txt)|*.txt|" \
                   "All Files |*"
        dlg = wx.FileDialog(self, "Save CSV As", ".", "", wildcard, wx.SAVE|wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            fn = dlg.GetPath()
            #from priithon.all import U
            #U.writeArray(vstack([
            #ll = self.client.line_list
            f = file(fn, "w")
            for dataset in self.client.line_list:
                ps = dataset.points
                ps = asanyarray( ps )
                for x_y in ps.T:
                    for el in x_y:
                        f.write(repr(el) + csv_sep)
                    f.write('\n')
            f.close()
        dlg.Destroy()

    def file_close(self, event):
        self.Close()

    # seb-20040824#added by BEC. I don't know if this is the correct action for closing the plot window...bu it works.
    # seb-20040824def OnCloseWindow(self, event):
    # seb-20040824    self.Show(0)	    
        
    def format_font(self,event):
        font_attr,color_attr = 'font','color'
        if event.GetId() == self.TITLE_FONT:
            texts = [self.client.title]
        elif event.GetId() == self.AXIS_FONT:            
            texts = [self.client.x_title,self.client.y_title]
           #texts = [self.client.y_title]
        elif event.GetId() == self.LABEL_FONT:
            texts = [self.client.x_axis,self.client.y_axis]
            font_attr,color_attr = 'label_font','label_color'
        data = wx.FontData()
        current_color = get_color(getattr(texts[0],color_attr))
        current_font = getattr(texts[0],font_attr)
        data.SetColour(current_color)
        data.SetInitialFont(current_font)
        dlg = wx.FontDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            font = data.GetChosenFont()
            color = data.GetColour()
            rgb = color.Red(),color.Green(),color.Blue()
            for text in texts:
                setattr(text,color_attr,rgb)
                setattr(text,font_attr,font)
                self.client.update()
        dlg.Destroy()

    def title(self,event):
        if event.GetId() == self.TITLE_TEXT:
            title = self.client.title
            prompt = 'Enter graph title'
        elif event.GetId() == self.X_TEXT:            
            title = self.client.x_title
            prompt = 'Enter x axis title'
        elif event.GetId() == self.Y_TEXT:
            title = self.client.y_title
            prompt = 'Enter y axis title'        
        dlg = wx.TextEntryDialog(self, prompt,'', title.text)
        if dlg.ShowModal() == wx.ID_OK:
            title.text = dlg.GetValue()
        dlg.Destroy()
        self.client.update()

    def update(self):
        self.client.update()
            
    def __getattr__(self,key):
        try:        
            return self.__dict__[key]
        except KeyError:  
            return getattr(self.__dict__['client'],key)
    """        
    def __setattr__(self,key,val):
        #print key,val
        #if plot_canvas._attributes.has_key(key):
        #    self.__dict__['client'].__dict__[key] = val
        #    return None
        self.__dict__[key] = val
    """    


# global functions

def lena_obj():
    import pickle
    import wxplt, os
    d,junk = os.path.split(os.path.abspath(wxplt.__file__))
    fname = os.path.join(d,'lena.dat')
    f = open(fname,'rb')
    import pickle
    lena = array(pickle.load(f))
    f.close()
    #x_bounds = array((0.,1))
    #y_bounds = array((0.,1))
    #return image_object(lena,x_bounds,y_bounds,colormap='grey')
    return image_object(lena,colormap='grey')

def lena():
    import pickle
    import wxplt, os
    d,junk = os.path.split(os.path.abspath(wxplt.__file__))
    fname = os.path.join(d,'lena.dat')
    f = open(fname,'rb')
    import pickle
    lena = array(pickle.load(f))
    f.close()
    return lena

def _InitObjects():
    # 100 points sin function, plotted as green circles
    data1 = 2.*pi*arange(200)/200.
    data1.shape = (100, 2)
    data1[:,1] = sin(data1[:,0])
    #markers1 = poly_marker(data1, color='green', marker='circle',size=1)
    markers1 = line_object(data1)
    
    # 50 points cos function, plotted as red line
    data1 = 2.*pi*arange(100)/100.
    data1.shape = (50,2)
    data1[:,1] = cos(data1[:,0])
    #lines = poly_line(data1, color='red')
    lines = line_object(data1)
    # A few more points...
    #markers2 = poly_marker([(0., 0.), (pi/4., 1.), (pi/2, 0.),
    #                      (3.*pi/4., -1)], color='blue',
    #                      fillcolor='green', marker='cross')
    markers2 = line_object([(0., 0.), (pi/4., 1.), (pi/2, 0.),(3.*pi/4., -1)])
    # An Image
    return [markers1]#, lines, markers2]


def test_axis():
    a = axis_object(rotate = 0)
    graph_area = box_object((10,10),(100,100))
    bounds = (-1.,1.)
    a.calculate_ticks(bounds)
    dummy_dc = 0
    a.layout(graph_area,dummy_dc)
    print(a.tick_points)
    
    bounds = (0.,1.)
    a.calculate_ticks(bounds)
    a.layout(graph_area,dummy_dc)
    print(a.tick_points)
    print(a.tick_start)
    print(a.tick_stop)



if __name__ == '__main__':
        
    class MyApp(wx.App):
        def OnInit(self):
            frame = plot_frame(None, -1, "Graph",size=(400,400))
            frame.Show(True)
            self.SetTopWindow(frame)
            #frame.OnPlotDraw(None)
            return True


    app = MyApp(0)
    app.MainLoop()
