"""
Priithon pyshell / view / view2 support file drag-and-drop
    -> a popup menu presents a choice of what to do
"""
__author__  = "Sebastian Haase <haase@msg.ucsf.edu>"
__license__ = "BSD license - see LICENSE file"

import wx

NO_SPECIAL_GUI_EXCEPT = True # instead rely on Priithon's guiExceptionFrame (Y._fixGuiExceptHook())

Menu_paste = wx.NewId()
Menu_view = wx.NewId()
Menu_view2 = wx.NewId()
Menu_assign = wx.NewId()
Menu_assignFN = wx.NewId()
Menu_assignList= wx.NewId()
Menu_dir = wx.NewId()
Menu_cd = wx.NewId()
Menu_appSysPath = wx.NewId()
Menu_exec = wx.NewId()
Menu_import = wx.NewId()
Menu_importAs = wx.NewId()
Menu_editor = wx.NewId()
Menu_editor2 = wx.NewId()
Menu_assignSeq = wx.NewId()
Menu_viewSeq = wx.NewId()

#seb : File drag and drop
class FileDropTarget(wx.FileDropTarget):
    def __init__(self, parent, pyshell=None):
        wx.FileDropTarget.__init__(self)

        self.parent = parent

        if pyshell is not None:
            self.pyshell = pyshell
        else:
            import __main__
            if hasattr(__main__, 'shell'):
                self.pyshell = __main__.shell
            else:
                self.pyshell = None

    def OnDropFiles(self, x, y, filenames):
        if len(filenames) == 1:
            self.txt = 'r\"%s\"' % filenames[0]
        else:
            self.txt = '[ '
            for f in filenames:
                self.txt += 'r\"%s\" , ' % f
            self.txt += ']'

            #         #wx26 n = len(txt)
            #         #wx26 self.pyshell.AppendText(n, txt)
            #         self.pyshell.AppendText(txt)
            #         pos = self.pyshell.GetCurrentPos() + len(txt)
            #         self.pyshell.SetCurrentPos( pos )
            #         self.pyshell.SetSelection( pos, pos )

        m = wx.Menu()

        import os
        if len(filenames) == 1:
            self.fn_or_fns = filenames[0]
            ## filenames = filenames[0] # danger : misleading name (plural used for a single filename)
            fUPPER_ending = self.fn_or_fns[-5:].upper()
            if os.path.isdir(self.fn_or_fns):
                m.Append(Menu_dir,  "open directory-list-viewer")
                m.Append(Menu_cd,   "change working directory")
                m.Append(Menu_appSysPath,   "append to sys.path")
                m.Append(Menu_assignFN,   "assign dirname to var")
            elif fUPPER_ending.endswith('.PY') or \
                 fUPPER_ending.endswith('.PYW') or \
                 fUPPER_ending.endswith('.PYC'):
                m.Append(Menu_exec,   "execute py-file")
                m.Append(Menu_import,   "import")
                m.Append(Menu_importAs,   "import as ...")
                m.Append(Menu_editor,   "edit py-file")
                m.Append(Menu_assignFN,   "assign filename to var")
            else:
                m.Append(Menu_assign,  "load and assign to var")
                m.Append(Menu_view,   "view")
                m.Append(Menu_view2,    "view multi-color")
                m.Append(Menu_editor2,   "edit text file")
                m.Append(Menu_assignFN,   "assign filename to var")

        else:
            self.fn_or_fns = filenames
            m.Append(Menu_view,        "view files separately")
            m.Append(Menu_view2,       "view files as one multi-color")
            m.Append(Menu_assignSeq,   "load and assign img seq into one array var")
            m.Append(Menu_viewSeq,     "view image sequence")
            m.Append(Menu_assignList,  "assign list of names to var")
            
        m.Append(Menu_paste,   "paste")

        wx.EVT_MENU(self.parent, Menu_assign, self.onAssign)
        wx.EVT_MENU(self.parent, Menu_assignFN, self.onAssignFN)
        wx.EVT_MENU(self.parent, Menu_assignList,self.onAssignList)
        wx.EVT_MENU(self.parent, Menu_paste, self.onPaste)
        wx.EVT_MENU(self.parent, Menu_view,  self.onView)
        wx.EVT_MENU(self.parent, Menu_view2,  self.onView2)
        wx.EVT_MENU(self.parent, Menu_dir,  self.onDir)
        wx.EVT_MENU(self.parent, Menu_cd,  self.onCd)
        wx.EVT_MENU(self.parent, Menu_appSysPath,  self.onAppSysPath)
        wx.EVT_MENU(self.parent, Menu_assignSeq, self.onAssignSeq)
        wx.EVT_MENU(self.parent, Menu_viewSeq, self.onViewSeq)

        wx.EVT_MENU(self.parent, Menu_exec,  self.onExe)
        wx.EVT_MENU(self.parent, Menu_import,  self.onImport)
        wx.EVT_MENU(self.parent, Menu_importAs,  self.onImportAs)
        wx.EVT_MENU(self.parent, Menu_editor,  self.onEditor)
        wx.EVT_MENU(self.parent, Menu_editor2,  self.onEditor2)
        
        self.parent.PopupMenuXY(m, x,y)



    def onPaste(self, ev):
        try:
            self.pyshell.AppendText(self.txt)
        except:
            n = len(self.txt)
            self.pyshell.AppendText(n, self.txt)

        pos = self.pyshell.GetCurrentPos() + len(self.txt)
        self.pyshell.SetCurrentPos( pos )
        self.pyshell.SetSelection( pos, pos )
    def onView(self, ev):
        from Priithon.all import Y
        Y.view(self.fn_or_fns) # 'list' for "view separately"

        self.pyshell.addHistory("Y.view( %s )"%(self.txt,))
    def onView2(self, ev):
        from Priithon.all import Y
        if isinstance(self.fn_or_fns, (list, tuple)) and len(self.fn_or_fns) > 1:
            f = tuple( self.fn_or_fns )  # 'tuple' for "view as mock-adarray"
            self.txt = '( '
            for fff in self.fn_or_fns:
                self.txt += 'r\"%s\" , ' % fff
            self.txt += ')'
        else:
            f = self.fn_or_fns
        Y.view2(f, colorAxis='smart')
        self.pyshell.addHistory("Y.view2( %s, colorAxis='smart')"%(self.txt,))
    def onDir(self, ev):
        from Priithon.all import Y
        Y.listFilesViewer(self.fn_or_fns)
        self.pyshell.addHistory("Y.listFilesViewer(r\"%s\")"%(self.fn_or_fns,))
    def onCd(self, ev):
        import os
        os.chdir( self.fn_or_fns )
        self.pyshell.addHistory("os.chdir(r\"%s\")"%(self.fn_or_fns,))
    def onAppSysPath(self, ev):
        import sys
        from Priithon.all import Y
        sys.path.append( self.fn_or_fns )
        s = "sys.path.append(r\"%s\")"% (self.fn_or_fns,)
        Y.shellMessage("###  %s\n"% s)
        self.pyshell.addHistory(s)

    def onAssign(self, ev):
        fn = self.fn_or_fns
        from Priithon.all import Y
        a = Y.load(fn)
        if a is not None:
            v = Y.assignNdArrToVarname(a, "Y.load( r'%s' )"%fn)
            if v is not None:
                self.pyshell.addHistory("%s = Y.load( r'%s' )"%(v,fn))
    def onAssignFN(self, ev):
        v = wx.GetTextFromUser("assign filename to varname:", 'new variable')
        if not v:
            return
        import __main__
        try:
            exec '%s = %s' % (v,self.txt) in __main__.__dict__
        except:
            if NO_SPECIAL_GUI_EXCEPT:
                raise
            import sys
            e = sys.exc_info()
            wx.MessageBox("Error when assigning filename to __main__.%s: %s - %s" %\
                          (v, str(e[0]), str(e[1]) ),
                          "Bad Varname  !?",
                          style=wx.ICON_ERROR)
        else:
            from Priithon.all import Y
            s = "%s = %s"% (v, self.txt)
            Y.shellMessage("### %s\n"% (s,))
            self.pyshell.addHistory(s)
    def onAssignList(self, ev):
        v = wx.GetTextFromUser("assign list to varname:", 'new variable')
        if not v:
            return
        import __main__
        try:
            exec '%s = %s' % (v, self.fn_or_fns) in __main__.__dict__
        except:
            if NO_SPECIAL_GUI_EXCEPT:
                raise
            import sys
            e = sys.exc_info()
            wx.MessageBox("Error when assigning list to __main__.%s: %s - %s" %\
                          (v, str(e[0]), str(e[1]) ),
                          "Bad Varname  !?",
                          style=wx.ICON_ERROR)
        else:
            from Priithon.all import Y
            Y.shellMessage("### %s = <list of files>\n"% (v,))

    def onAssignSeq(self, ev):
        from Priithon.all import Y
        v = wx.GetTextFromUser("assign image sequence to array varname:", 'new variable')
        if not v:
            return
        import __main__
        try:
            exec '%s = U.loadImg_seq(%s)' % (v,self.fn_or_fns) in __main__.__dict__
        except:
            if NO_SPECIAL_GUI_EXCEPT:
                raise
            import sys
            e = sys.exc_info()
            wx.MessageBox("Error when loading and assigning img.seq. to __main__.%s: %s - %s" %\
                          (v, str(e[0]), str(e[1]) ),
                          "Bad Varname  !?",
                          style=wx.ICON_ERROR)
        else:
            Y.shellMessage("### %s = U.loadImg_seq(<list of files>)\n"% (v,))

    def onViewSeq(self, ev):
        from Priithon.all import Y,U
        try:
            Y.view( U.loadImg_seq( self.fn_or_fns ) )
        except:
            if NO_SPECIAL_GUI_EXCEPT:
                raise
            import sys
            e = sys.exc_info()
            wx.MessageBox("Error when loading image sequence: %s - %s" %\
                          (str(e[0]), str(e[1]) ),
                          "Non consistent image shapes  !?",
                          style=wx.ICON_ERROR)
        else:
            s = "Y.view( U.loadImg_seq(<fileslist>) )"
            Y.shellMessage("###  %s\n"% s)


    def onExe(self, ev):
        import sys,os,__main__
        p   = os.path.dirname( self.fn_or_fns )
        sys.path.insert(0, p)
        try:
            try:
                self.pyshell.addHistory("execfile(r\"%s\")"%(self.fn_or_fns,))
                execfile(self.fn_or_fns, __main__.__dict__)
            except:
                if NO_SPECIAL_GUI_EXCEPT:
                    raise
                e = sys.exc_info()
                wx.MessageBox("Error on execfile: %s - %s" %\
                              (str(e[0]), str(e[1]) ),
                              "Bad Varname  !?",
                              style=wx.ICON_ERROR)
            else:
                from Priithon.all import Y
                Y.shellMessage("### execfile('%s')\n"%(self.fn_or_fns,))
                self.pyshell.addHistory("execfile('%s')\n"%(self.fn_or_fns,))
        finally:
            #20090319 del sys.path[0]
            sys.path.remove(p)

    def onImport(self, ev):
        import sys,os, __main__
        p   = os.path.dirname( self.fn_or_fns )
        sys.path.insert(0, p)
        try:
            try:
                mod = os.path.basename( self.fn_or_fns )
                mod = os.path.splitext( mod )[0]
                exec ('import %s' % mod) in __main__.__dict__
                self.pyshell.addHistory("import %s"%mod)
            except:
                if NO_SPECIAL_GUI_EXCEPT:
                    raise
                import sys
                e = sys.exc_info()
                wx.MessageBox("Error on import: %s - %s" %\
                              (str(e[0]), str(e[1]) ),
                              "Bad Varname  !?",
                              style=wx.ICON_ERROR)
            else:
                from Priithon.all import Y
                Y.shellMessage("### import %s\n"% (mod,))
        finally:
            if wx.MessageBox("leave '%s' in front of sys.path ?" % (p,), 
                             "Python import search path:", style=wx.YES_NO) != wx.YES:
                #20090319 del sys.path[0]
                sys.path.remove(p)

    def onImportAs(self, ev):
        v = wx.GetTextFromUser("import module as :", 'new mod name')
        if not v:
            return
        import sys,os, __main__
        p   = os.path.dirname( self.fn_or_fns )
        sys.path.insert(0, p)
        try:
            try:
                mod = os.path.basename( self.fn_or_fns )
                mod = os.path.splitext( mod )[0]
                s = 'import %s as %s' % (mod, v)
                exec (s) in __main__.__dict__
                self.pyshell.addHistory(s)
            except:
                if NO_SPECIAL_GUI_EXCEPT:
                    raise
                import sys
                e = sys.exc_info()
                wx.MessageBox("Error on 'import %s as %s': %s - %s" %\
                              (mod, v, str(e[0]), str(e[1]) ),
                              "Bad Varname  !?",
                              style=wx.ICON_ERROR)
            else:
                from Priithon.all import Y
                Y.shellMessage("### import %s as %s\n"% (mod,v))
        finally:
            if wx.MessageBox("leave '%s' in front of sys.path ?" % (p,), 
                             "Python import search path:", style=wx.YES_NO) != wx.YES:
                #20090319 del sys.path[0]
                sys.path.remove(p)

    def onEditor2(self, ev):
        self.onEditor(ev, checkPyFile=False)
    def onEditor(self, ev, checkPyFile=True):
        import sys,os, __main__
        try:
            #mod = os.path.basename( filenames )
            mod = self.fn_or_fns
            if checkPyFile:
                mod = os.path.splitext( mod )[0]
                mod += '.py'
                if not os.path.isfile(mod):
                    r= wx.MessageBox("do you want to start editing a new .py-file ?", 
                                     "py file not found !", 
                                     style=wx.CENTER|wx.YES_NO|wx.CANCEL|wx.ICON_EXCLAMATION)
                    if r != wx.YES:
                        return

            from Priithon.all import Y
            Y.editor(mod)
            self.pyshell.addHistory("Y.editor( %s )"%mod)
        except:
            if NO_SPECIAL_GUI_EXCEPT:
                raise
            import sys
            e = sys.exc_info()
            wx.MessageBox("Error on starting Y.editor: %s - %s" %\
                              (str(e[0]), str(e[1]) ),
                          "Error  !?",
                          style=wx.ICON_ERROR)
