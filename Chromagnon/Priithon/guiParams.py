
class guiParams(object):
    def __init__(self):
        """
        guiParams is a class that can manages a set of multiple attributes, -> parameters
           which can be "associatred" with one (or no) or multiple gui widgets
           the gui display and the parameter will always have consistent values !

        >>> import guiParams

        >>> pd = guiParams.guiParams()
        >>> Y.buttonBox(itemList=
        ...    pd._bbox(label="coeff0", n='c0', v=0, filter="int", slider=(0, 100), slFilter="", newLine=0)
        ...    , title="guiParams demo", verticalLayout=False, execModule=pd)

        >>> Y.buttonBox(itemList=
        ...     pd._bboxInt('int: ', 'intVal', v=0, slider=True, slmin=0, slmax=100, newLine=True)+
        ...     pd._bboxFloat('float: ', 'floatVal', v=0.0, slider=True, slmin=0.0, slmax=1.0, slDecimals=2, newLine=False)
        ...     , title="guiParams demo", verticalLayout=False, execModule=pd)
        >>> def f(v,n):
        ...     print 'n=>', v
        ...     
        >>> Y._registerEventHandler(pd._paramsDoOnValChg['floatVal'], f)
        """
        #would call  __setattr__: self.paramsVals = {}
        #would call  __setattr__: self.paramsGUIs = {}
        self.__dict__['_paramsVals'] = {}
        self.__dict__['_paramsGUIs'] = {}
        self.__dict__['_paramsDoOnValChg'] = {}
        #     # _paramsDoOnValChg keeps a list functions; get called with (val,paramName)
        self.__dict__['_paramsGUI_setAttrSrc'] = None # "short-memory" for 'which GUI triggered' the value change
        #                                      # this is to prevent e.g. TxtCtrl being 'updated' while typing
        self.__dict__['_paramsOnHold'] = {} # these are currently not triggering event handlers being called

    def __getattr__(self, n):
        try:
            v = self._paramsVals[n]
        except:
            raise AttributeError("parameter `%s` unknown" %(n,))

        return v

    def __setattr__(self, n, v):
        """
        set/change value of given parameter with name n
        trigger all registered event handlers in _paramsDoOnValChg[n]

        call this first, before registering any gui to this parameter
           (as this sets up the necessary book keeping lists)
        """
        import wx
        #self._paramsVals[n] = v

        try:
            n_to_be_held = self.__dict__['_paramsOnHold'][n]
            # True: control is down: change val, but don't trigger evt handlers
            # False: control just released, trigger evt handlers !
        except KeyError:
            n_to_be_held = None
            # None: control is and was not down, trigger only if val really changed

        try:
            # do nothing and return immediately if control is down and value did not change its value
            if n_to_be_held is None:
                # no fixed: if v is an N.array: ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
                try:
                    unchanged = all(self.__dict__['_paramsVals'][n] == v)  # iterable ?
                except TypeError:
                    unchanged = self.__dict__['_paramsVals'][n] == v       # no!

                if unchanged:
                    self.__dict__['_paramsGUI_setAttrSrc'] = None
                    return
        except KeyError:
            pass

        self.__dict__['_paramsVals'][n] = v


        guis  = self.__dict__['_paramsGUIs']
        doOns  = self.__dict__['_paramsDoOnValChg']

        triggeringGUI = self.__dict__['_paramsGUI_setAttrSrc']

        if n not in guis:
            guis[n] = []
            doOns[n] = []
        else:
            for gui in guis[n]:
                if not gui or gui is triggeringGUI:
                    continue
                if isinstance(gui, wx.TextCtrl):
                    #gui.SetValue( str(v) )
                    #20080821 gui.ChangeValue( str(v) )
                    gui.ChangeValue( eval(gui.val2gui+"(v)") )
                else:
                    # wx.Slider
                    #20080821 gui.SetValue( int(v) )
                    gui.SetValue( eval(gui.val2gui+"(v)") )

        self.__dict__['_paramsGUI_setAttrSrc'] = None

        if n_to_be_held == True:
            return
        if n_to_be_held == False:
            del self.__dict__['_paramsOnHold'][n]

        for f in doOns[n]:
            #try:
            f(v,n)
            #except:
            #    print >>sys.stderr, " *** error in doOnLDown **"
            #    traceback.print_exc()
            #    print >>sys.stderr, " *** error in doOnLDown **"


    def __delattr__(self, n):
        del self.__dict__['_paramsVals'][n]
        del self.__dict__['_paramsGUIs'][n]
        del self.__dict__['_paramsDoOnValChg'][n]


    # for PyCrust -- PyShell
    def _getAttributeNames(self):
        return list(self.__dict__['_paramsVals'].keys())
        

    #def _register(self, n, v): #, filterFnc=int):
    #    self.__dict__['_paramsVals'][n] = v
    #    self.__dict__['_paramsGUIs'][n] = []
        

    def _registerGUI(self, n, gui, val2gui=None):#=None):
        """
        connect a "new" gui control to a given paramter name

        call this only AFTER the parameter 'n' has been set -- see __setattr__
        """
        import wx

        try:
            l=self.__dict__['_paramsGUIs'][n]
        except KeyError:
            raise AttributeError("parameter `%s` unknown" %(n,))            
            #    l=self.__dict__['_paramsGUIs'][n] = []

        if val2gui is not None:
            gui.val2gui = val2gui
        elif isinstance(gui, wx.TextCtrl):
            gui.val2gui = "str" 
        elif isinstance(gui, wx.Slider):
            gui.val2gui = "int" 
        elif isinstance(gui, (wx.CheckBox, wx.ToggleButton)):
            gui.val2gui = "bool" 
        else:
            print("DEBUG: GuiParams: what is the type of this gui:", gui)
            gui.val2gui = "int" 
            
        #if gui in not None:
        l.append(gui)

    def _unregisterGUI(self, n, gui):
        try:
            l=self.__dict__['_paramsGUIs'][n]
        except KeyError:
            raise AttributeError("parameter `%s` unknown" %(n,))            
        l.remove(gui)


    def _holdParamEvents(self, n=None, hold=True):
        """
        if `hold`, changing parameter `n` will trigger the event handlers being called
        otherwise, reset to normal, next change will trigger

        if n is None:
           apply / reset hold for all params
        """
        if n is None:
            for n in self.__dict__['_paramsVals'].keys():
                self._holdParamEvents(n, hold)
            return

        if hold:
            self.__dict__['_paramsOnHold'][n]=True
        else:
            try:
                del self.__dict__['_paramsOnHold'][n]
            except KeyError:
                pass

    def _spiffupCtrl(self, b, n, arrowKeyStep):
#                          evt.ControlDown(), 'C'),
#                         (evt.AltDown(),     'A'),
#                         (evt.ShiftDown(),   'S'),
#                         (evt.MetaDown(),
        """
        make control respond to keys:
        arrow up/down change value
        with Shift values change 10-fold faster
        with Ctrl being pressed, event handler are not getting called 
        """
        import wx
        def OnKeyUp(evt):
           keycode = evt.GetKeyCode()
           if keycode == wx.WXK_CONTROL:
               try:
                   self.__dict__['_paramsOnHold'][n]=False
                   v = self.__dict__['_paramsVals'][n]
                   self.__setattr__(n,v)
               except KeyError:
                   pass
           evt.Skip()

        def OnKeyDown(evt):
           keycode = evt.GetKeyCode()

           if keycode == wx.WXK_CONTROL:
               self.__dict__['_paramsOnHold'][n]=True

           if evt.ShiftDown():
               arrowKeyStepLocalVar=arrowKeyStep*10
           else:
               arrowKeyStepLocalVar=arrowKeyStep
           if keycode == wx.WXK_UP:
               v = self.__dict__['_paramsVals'][n]+arrowKeyStepLocalVar
               self.__setattr__(n,v)
           elif keycode == wx.WXK_DOWN:
               v = self.__dict__['_paramsVals'][n]-arrowKeyStepLocalVar
               self.__setattr__(n,v)
           else:
               evt.Skip()

        b.Bind(wx.EVT_KEY_DOWN, OnKeyDown)
        b.Bind(wx.EVT_KEY_UP, OnKeyUp)
           


#     def _bbox(self, label, n, v, filter='int', slider=(0,100), slFilter='', newLine=False):
#         '''
#         return list of tuple to be used in buttonBox contructors itemList

#         label: static text label used in button box (e.g. "min: ")
#         n:     guiParms var name (as string!)
#         v:     inital value
#         filter: string, e.g. 'int' ; function to convert text field's value into guiParam value
#         slider: tuple of min,max value for slider ; 
#                 None if you don't want a slider
#         slFilter: string, e.g. '' ; function to convert slider value into guiParam value: TODO FIXME!!
#         '''
#         self.__setattr__(n,v)
#         l= [
#             ("l\t%s\t"%label,   '', 0,0),
#             ("t _._registerGUI('%s', x)\t%s"%(n, self.__dict__['_paramsVals'][n]), "_.%s = %s(x)"%(n,filter), 0,0),
#             ]
#         if slider is not None:
#             slMin, slMax = slider
#             l += [
#             ("sl _._registerGUI('%s', x)\t%d %d %d"%(n, self.__dict__['_paramsVals'][n], slMin, slMax), "_.%s = %s(x)"%(n,slFilter), 1,0),
#             ]
        
#         if newLine:
#             l += ['\n']
#         return l

    def _bboxInt(self, label, n, v=0, 
                 slider=True, slmin=0, slmax=100, newLine=True,
                 val2txt="str",
                 labelWeight=0, labelExpand=False, 
                 textWeight=0, textExpand=False, textWidth=-1,
                 sliderWeight=1, sliderExpand=False,
                 tooltip="", regFcn=None, regFcnName=None):
        """
        val2txt: can somthing like: val2txt="'%03d'%", because it gets prepended before "(x)"
        """
        return self._bboxItemsGroup(label, n, v, 
                                    txt2val=int, val2txt=val2txt,
                                    slider=(slmin,slmax) if slider else None, 
                                    sl2val=int, 
                                    val2sl='int', 
                                    arrowKeyStep=1,
                                    newLine=newLine,
                                    labelWeight=labelWeight, labelExpand=labelExpand,
                                    textWeight=textWeight, textExpand=textExpand, textWidth=textWidth,
                                    sliderWeight=sliderWeight, sliderExpand=sliderExpand,
                                    tooltip=tooltip, regFcn=regFcn, regFcnName=regFcnName)
    def _bboxFloat(self, label, n, v=0.0, 
                   slider=True, slmin=0.0, slmax=1.0, slDecimals=2, 
                   newLine=True,
                   val2txt="str",
                   labelWeight=0, labelExpand=False, 
                   textWeight=0, textExpand=False, textWidth=-1,
                   sliderWeight=1, sliderExpand=False,
                   tooltip="", regFcn=None, regFcnName=None):
        """
        val2txt: can somthing like: val2txt="'%.2f'%", because it gets prepended before "(x)"
        """
        return self._bboxItemsGroup(label, n, v, 
                                    txt2val=float, val2txt=val2txt,
                                    slider=(slmin,slmax)  if slider else None, 
                                    sl2val=(lambda x:x/10.**slDecimals), 
                                    val2sl='(lambda x:x*%f)'%(10**slDecimals,), 
                                    arrowKeyStep=.1**slDecimals,
                                    newLine=newLine,
                                    labelWeight=labelWeight, labelExpand=labelExpand, 
                                    textWeight=textWeight, textExpand=textExpand, textWidth=textWidth,
                                    sliderWeight=sliderWeight, sliderExpand=sliderExpand,
                                    tooltip=tooltip, regFcn=regFcn, regFcnName=regFcnName)
    def _bboxText(self, label, n, v="", newLine=True,
                  labelWeight=0, labelExpand=False, 
                  textWeight=0, textExpand=False, textWidth=-1,
                  tooltip="", regFcn=None, regFcnName=None):
        return self._bboxItemsGroup(label, n, v, txt2val=str, 
                                    slider=None, 
                                    arrowKeyStep=0,
                                    newLine=newLine,
                                    labelWeight=labelWeight, labelExpand=labelExpand, 
                                    textWeight=textWeight, textExpand=textExpand, textWidth=textWidth,
                                    tooltip=tooltip, regFcn=regFcn, regFcnName=regFcnName)
    



    def _bboxBool(self, label, n, v=False, controls='cb', newLine=False,
                  tooltip="", regFcn=None, regFcnName=None):
        """
        return list of tuple to be used in buttonBox contructors itemList

        label: static text label used in button box (e.g. "min: ")
        n:     guiParms var name (as string!)
        v:     inital value

        controls: string of space spearated "codes" specifying what wxControls should be shown
                 (only first (and maybe last) case-insensitive char is significant)
            "l"  - text label
            "tb" - toggle button
            "c"  - checkbox -- append an "r" make it right-aligned ("cb","cbL","cbR","cR" all match this one...)
          if this code is followed by one (int) number (space separated), 
             its value is used as "weight"
          if this is followed by another number (space separated),
             its value is used as "expand" (bool)
        """
        def fcn(execModule, value, buttonObj, evt):
            #print execModule, value, buttonObj, evt
            #print '-----------------------'
            
            self.__dict__['_paramsGUI_setAttrSrc'] = buttonObj
            self.__setattr__(n,bool(value))
        self.__setattr__(n,v)
        l=[]
        controls = controls.split()
        for i,c in enumerate(controls):
            try:
                int(c)
                continue
            except ValueError:
                pass
            c=c.lower()
            try:
                weight = int(controls[i+1])
            except:
                weight = 0
            try:
                expand = bool(int(controls[i+2]))
            except:
                expand = False
                
            if    c[0] == 'l':
                l.append( ("l\t%s\t"%label,   '', weight,expand,tooltip) )
            elif  c[0] == 't':
                t = "tb x.SetValue(%d);_._registerGUI('%s', x)\t%s"%(v,n, label)
                l.append( (t, fcn, weight,expand,tooltip) )
            elif  c[0] == 'c':
                t = "c x.SetValue(%d);_._registerGUI('%s', x)\t%s"%(v,n, label)
                if c[-1] == 'r': # right aligned
                    t += '\t'
                l.append( (t, fcn, weight,expand,tooltip) )
            else:
                raise ValueError("bool control type '%s' not recognized"%(c,))
        if newLine:
            l += ['\n']

        # register event handlers
        if regFcn is not None:
            from .usefulX import _registerEventHandler
            _registerEventHandler(self.__dict__['_paramsDoOnValChg'][n], newFcn=regFcn, newFcnName=regFcnName) #, oldFcnName='', delAll=False)

        return l

    def _bboxItemsGroup(self, label, n, v=.5, txt2val=float, val2txt="str",
                        slider=(0,1), sl2val=(lambda x:x/100.), val2sl='(lambda x:x*100)', 
                        arrowKeyStep=0.01, newLine=False,
                        labelWeight=0, labelExpand=False, textWeight=0, textExpand=False, textWidth=-1, sliderWeight=1, sliderExpand=False, 
                        tooltip="", regFcn=None, regFcnName=None):
        """
        return list of tuple to be used in buttonBox contructors itemList

        label: static text label used in button box (e.g. "min: ")
        n:     guiParms var name (as string!)
        v:     inital value
        txt2val: function to convert text field's value into guiParam value
        slider: tuple of min,max value for slider ; 
                None if you don't want a slider
        sl2val: function to convert slider value into guiParam value:
        """
        def fcnTxt(execModule, value, buttonObj, evt):
            if len(value):
                self.__dict__['_paramsGUI_setAttrSrc'] = buttonObj
                self.__setattr__(n, txt2val(value))
        def fcnSlider(execModule, value, buttonObj, evt):
            self.__dict__['_paramsGUI_setAttrSrc'] = buttonObj
            self.__setattr__(n, sl2val(value))

        self.__setattr__(n,v)

        if label:
            l= [
                ("l\t%s\t"%label,   '', 
                 labelWeight,labelExpand, tooltip),
                ]
        else:
            l=[]

#             l += [
#             ("t _._spiffupCtrl(x,'%s');_._registerGUI('%s', x)\nif %s>=0:x.SetSizeHints(%s,-1)\t%s"
#              %(n,n, textWidth, textWidth, self.__dict__['_paramsVals'][n]), 
#              fcnTxt, 
#              textWeight,textExpand, tooltip),
#             ]

        if arrowKeyStep==0:
            arrowKeyCode = ""
        else:
            arrowKeyCode = "_._spiffupCtrl(x,'%s', %s);" % (n,arrowKeyStep)


        if textWidth>=0:
            sizeHintCode = ";x.SetSizeHints(%s,-1)" % (textWidth,)
        else:
            sizeHintCode = ""
        
        l += [
            ("t %s_._registerGUI('%s', x, val2gui=%s)%s\t%s"
             %(arrowKeyCode, n, repr(val2txt),
               sizeHintCode, self.__dict__['_paramsVals'][n]), 
             fcnTxt, textWeight,textExpand, tooltip),
            ]


        if slider is not None:
            slMin, slMax = [eval(val2sl)(v) for v in slider]
            slVal0 = eval(val2sl)(self.__dict__['_paramsVals'][n])
            l += [
            ("sl %s_._registerGUI('%s', x, val2gui='''%s''')\t%d %d %d"
             %(arrowKeyCode, n, val2sl,    slVal0, slMin, slMax), 
             fcnSlider, 
             sliderWeight,sliderExpand, tooltip),
            ]
        
        if newLine:
            l += ['\n']

        # register event handlers
        if regFcn is not None:
            from .usefulX import _registerEventHandler
            _registerEventHandler(self.__dict__['_paramsDoOnValChg'][n], newFcn=regFcn, newFcnName=regFcnName) #, oldFcnName='', delAll=False)

        return l


    #def f(s):
    #    return 1234


# class guiHistValue:
#     def __init__(self, id=-1, leftOrRight=0):
#         """
#         leftOrRight =0: use left brace
#         leftOrRight =1: use right brace
#         """
#         self.id = id
#         self.leftOrRight = leftOrRight
         

#     def SetValue(self, v):
#         from Priithon.all import Y
#         if self.leftOrRight ==0:
#             Y.vHistScale(id=self.id, amin=v, amax=None, autoscale=False)
#         else:
#             Y.vHistScale(id=self.id, amin=None, amax=v, autoscale=False)
