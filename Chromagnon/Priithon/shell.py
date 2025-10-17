
from wx.py.shell import *
from wx.py import introspect
import six, warnings

###---- introspect ---------------
def hasattr(obj, attr):# am python3
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            return bool(getattr(obj, attr, None))
        except (NameError, ValueError):
            return False

introspect.hasattr = hasattr

#---------------------------------------

class PriShellFrame(ShellFrame):
    def __init__(self, parent=None, id=-1, title='PyShell',
                 pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=wx.DEFAULT_FRAME_STYLE, locals=None,
                 InterpClass=None, introText=None,
                 config=None, dataDir=None,
                 *args, **kwds):
        """Create ShellFrame instance."""
        frame.Frame.__init__(self, parent, id, title, pos, size, style)
        frame.ShellFrameMixin.__init__(self, config, dataDir)

        if size == wx.DefaultSize:
            self.SetSize((750, 525))

        #intro = 'PyShell %s - The Flakiest Python Shell' % VERSION
        #self.SetStatusText(intro.replace('\n', ', '))
        self.shell = PriShell(parent=self, id=-1, introText=introText,
        #self.shell = Shell(parent=self, id=-1, introText=introText,
                           locals=locals, InterpClass=InterpClass,
                           startupScript=self.startupScript,
                           execStartupScript=self.execStartupScript,                                       *args, **kwds)

        # Override the shell so that status messages go to the status bar.
        self.shell.setStatusText = self.SetStatusText

        self.shell.SetFocus()
        self.LoadSettings()

    def OnClose(self, event):
        """Event handler for closing."""
        #
        #before2007: This isn't working the way I want, but I'll leave it for now.

        #20070712 sebVeto
        sebVeto = False
        self.IwantToClose_hack = True # 20080730: otherwise we get into a circle if multiple shell windows are open
        if len(wx.GetTopLevelWindows())>1:
            for f in wx.GetTopLevelWindows():
                if (f is not self and (not hasattr(f, "IwantToClose_hack")
                            or not f.IwantToClose_hack)):
                    f.Close()

        if self.shell.waiting or sebVeto:
            if event.CanVeto():
                event.Veto(True)
        else:
            self.shell.destroy()
            self.Destroy()


class PriShell(Shell):
    def __init__(self, *args, **kwds):
        Shell.__init__(self, *args, **kwds)

    def OnKeyDown(self, event):
        """Key down event handler."""

        key = event.GetKeyCode()
        # If the auto-complete window is up let it do its thing.
        if self.AutoCompActive():
            event.Skip()
            return

        # Prevent modification of previously submitted
        # commands/responses.
        controlDown = event.ControlDown()
        rawControlDown = event.RawControlDown()
        altDown = event.AltDown()
        shiftDown = event.ShiftDown()
        currpos = self.GetCurrentPos()
        endpos = self.GetTextLength()
        selecting = self.GetSelectionStart() != self.GetSelectionEnd()

        if (rawControlDown or controlDown) and shiftDown and key in (ord('F'), ord('f')):
            li = self.GetCurrentLine()
            m = self.MarkerGet(li)
            if m & 1<<0:
                startP = self.PositionFromLine(li)
                self.MarkerDelete(li, 0)
                maxli = self.GetLineCount()
                li += 1 # li stayed visible as header-line
                li0 = li
                while li<maxli and self.GetLineVisible(li) == 0:
                    li += 1
                endP = self.GetLineEndPosition(li-1)
                self.ShowLines(li0, li-1)
                # select reappearing text to allow "hide again"
                self.SetSelection( startP, endP )
                return
            startP,endP = self.GetSelection()
            endP-=1
            startL = self.LineFromPosition(startP)
            endL = self.LineFromPosition(endP)

            # never hide last prompt
            if endL == self.LineFromPosition(self.promptPosEnd):
                endL -= 1

            m = self.MarkerGet(startL)
            self.MarkerAdd(startL, 0)
            self.HideLines(startL+1,endL)
            self.SetCurrentPos( startP ) # to ensure caret stays visible !

        if key == wx.WXK_F12: #seb
            if self.noteMode:
                # self.promptPosStart not used anyway - or ?
                self.promptPosEnd = \
                   self.PositionFromLine( self.GetLineCount()-1 ) + \
                   len(str(sys.ps1))
                self.GotoLine(self.GetLineCount())
                self.GotoPos(self.promptPosEnd)
                self.prompt()  #make sure we have a prompt
                self.SetCaretForeground("black")
                self.SetCaretWidth(1)    #default
                self.SetCaretPeriod(500) #default
            else:
                self.SetCaretForeground("red")
                self.SetCaretWidth(4)
                self.SetCaretPeriod(0) #steady

            self.noteMode = not self.noteMode
            return
        if self.noteMode:
            event.Skip()
            return

        # Return (Enter) is used to submit a command to the
        # interpreter.
        if (not (rawControlDown or controlDown) and not shiftDown and not altDown) and \
           key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            if self.CallTipActive():
                self.CallTipCancel()
            self.processLine()

        # Complete Text (from already typed words)
        elif shiftDown and key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            self.OnShowCompHistory()

        # Ctrl+Return (Ctrl+Enter) is used to insert a line break.
        elif (rawControlDown or controlDown) and key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            if self.CallTipActive():
                self.CallTipCancel()
            if currpos == endpos:
                self.processLine()
            else:
                self.insertLineBreak()

        # Let Ctrl-Alt-* get handled normally.
        elif (rawControlDown or controlDown) and altDown:
            event.Skip()

        # Clear the current, unexecuted command.
        elif key == wx.WXK_ESCAPE:
            if self.CallTipActive():
                event.Skip()
            else:
                self.clearCommand()

                #seb 20070106: autocompletion 
        elif not controlDown and key == wx.WXK_TAB:
            #wx.Bell()
            if self.AutoCompActive():
                self.AutoCompCancel()

            stoppos = self.promptPosEnd
            command = self.GetTextRange(stoppos, currpos)
            #self.autoCompleteShow(command)

            if len(command) and command[-1] in ('(',):
                self.ReplaceSelection('')
                try:
                    self.autoCallTipShow(command, alwaysShow=True)
                except TypeError: # on linux alwaysShow unavailable
                    self.autoCallTipShow(command)
            else:
                from wx.py import introspect
                if sys.version_info.major == 2:
                    import __main__
                    from __main__ import __builtins__ as builtins
                else:
                    import __main__, builtins
                #import introspect, __main__, __builtin__
                root = introspect.getRoot(command)
                if self.more and root=='': # pressing TAB to indent multi-line commands
                    event.Skip()
                    return                           


                #print >> __main__.shell.stderr, "DEBUG root:", root
                #print >> __main__.shell.stderr, "DEBUG command:", command
                #print >> __main__.shell.stderr, "DEBUG command tokens:", '\n'.join(map(str,introspect.getTokens(command)))
                # 20080908:  experiment with argument name completion
                if root=='' and command:
                    beforeParenthesis = command.rpartition('(')[0]
                    if beforeParenthesis:
                        #print >> __main__.shell.stderr, "DEBUG beforeParenthesis:", beforeParenthesis
                        try:
                            object = eval(beforeParenthesis, __main__.__dict__)
                        except:
                            #for debugging
                            pass
                            #import traceback
                            #traceback.print_exc(file=__main__.shell.stderr)
                        else:
                            import inspect
                            (args, varargs, varkw, defaults)=inspect.getargspec(object)
                            if  varargs is not None:
                                args.append( varargs )
                            if  varkw is not None:
                                args.append( varkw )
                            #print >> __main__.shell.stderr, ' '.join(args)
                            options = ' '.join([(s+'=') for s in args])
                            offset=0
                            self.AutoCompShow(offset, options)
                else: # 20080908


                    hasDot = root.rfind('.')
                    if hasDot>=0:
                        self.autoCompleteShow(command, offset=len(root)-hasDot-1)
                    else:
                        rootLower = root.lower()
                        _list = [s for s in __main__.__dict__ if s.lower().startswith(rootLower)]
                        _list.sort()

                        _list2 = [s for s in builtins.__dict__ if s.lower().startswith(rootLower)]
                        _list2.sort()

                        # first matches from __main__ then from __builtin__
                        #   TODO: add separator between the two
                        #if len(_list):
                        #    _list3 = _list + [] + _list2
                        #else:
                        #    _list3 = _list2
                        if len(_list) or len(_list2):
                            _list3 = _list + ['=====__builtins__:'] + _list2

                            options = ' '.join(_list3)
                            offset = len(root)
                            self.AutoCompShow(offset, options)
                            #if self.GetCurrentPos()<self.promptPosEnd:
                            #    #self.SetCurrentPos(self.promptPosEnd+1)
                            #    self.AppendText(' ')


        # Clear the current command
        elif key == wx.WXK_BACK and (rawControlDown or controlDown) and shiftDown:
            self.clearCommand()

        # Increase font size.
        elif (rawControlDown or controlDown) and key in (ord(']'), wx.WXK_NUMPAD_ADD):
            dispatcher.send(signal='FontIncrease')

        # Decrease font size.
        elif (rawControlDown or controlDown) and key in (ord('['), wx.WXK_NUMPAD_SUBTRACT):
            dispatcher.send(signal='FontDecrease')

        # Default font size.
        elif (rawControlDown or controlDown) and key in (ord('='), wx.WXK_NUMPAD_DIVIDE):
            dispatcher.send(signal='FontDefault')

        # Cut to the clipboard.
        elif ((rawControlDown or controlDown) and key in (ord('X'), ord('x'))) \
                 or (shiftDown and key == wx.WXK_DELETE):
            self.Cut()

        # Copy to the clipboard.
        elif (rawControlDown or controlDown) and not shiftDown \
                 and key in (ord('C'), ord('c'), wx.WXK_INSERT):
            self.Copy()

        # Copy to the clipboard, including prompts.
        elif (rawControlDown or controlDown) and shiftDown \
                 and key in (ord('C'), ord('c'), wx.WXK_INSERT):
            self.CopyWithPrompts()

        # Copy to the clipboard, including prefixed prompts.
        elif altDown and not controlDown \
                 and key in (ord('C'), ord('c'), wx.WXK_INSERT):
            self.CopyWithPromptsPrefixed()

        # Home needs to be aware of the prompt.
        #elif (rawControlDown or controlDown) and key == wx.WXK_HOME:
        elif (rawControlDown or controlDown) and key == wx.WXK_HOME:
            home = self.promptPosEnd
            if currpos > home:
                self.SetCurrentPos(home)
                if not selecting and not shiftDown:
                    self.SetAnchor(home)
                    self.EnsureCaretVisible()
            else:
                event.Skip()

        # Home needs to be aware of the prompt.
        elif key == wx.WXK_HOME or ((rawControlDown or controlDown) and key in (ord('A'), ord('a'))):
            home = self.promptPosEnd
            if currpos > home:
                [line_str,line_len] = self.GetCurLine()
                pos=self.GetCurrentPos()
                if line_str[:4] in [sys.ps1,sys.ps2,sys.ps3]:
                    self.SetCurrentPos(pos+4-line_len)
                    #self.SetCurrentPos(home)
                    if not selecting and not shiftDown:
                        self.SetAnchor(pos+4-line_len)
                        self.EnsureCaretVisible()
                else:
                    event.Skip()
            else:
                #event.Skip()
                return

        elif (rawControlDown or controlDown) and key in (ord('E'), ord('e')):#20051104 seb 20170112 am
            event.SetControlDown(False)
            #event.m_keyCode = wx.WXK_END
            #event.KeyCode = wx.WXK_END
            pos = self.GetLastPosition()
            self.SetCurrentPos(pos)
            self.SetAnchor(pos)
            #event.Skip()
            return   

        #
        # The following handlers modify text, so we need to see if
        # there is a selection that includes text prior to the prompt.
        #
        # Don't modify a selection with text prior to the prompt.
        elif selecting and key not in NAVKEYS and not self.CanEdit():
            pass

        # Paste from the clipboard.
        elif ((rawControlDown or controlDown) and not shiftDown and key in (ord('V'), ord('v'))) \
                 or (shiftDown and not controlDown and key == wx.WXK_INSERT):
            self.Paste()

        # manually invoke AutoComplete and Calltips
        elif (rawControlDown or controlDown) and key == wx.WXK_SPACE:
            self.OnCallTipAutoCompleteManually(shiftDown)

        # Paste from the clipboard, run commands.
        elif (rawControlDown or controlDown) and shiftDown and key in (ord('V'), ord('v')):
            self.PasteAndRun()

        # Replace with the previous command from the history buffer.
        elif ((rawControlDown or controlDown) and not shiftDown and key == wx.WXK_UP) \
                 or (altDown and key in (ord('P'), ord('p'))):
            self.OnHistoryReplace(step=+1)

        # Replace with the next command from the history buffer.
        elif ((rawControlDown or controlDown) and not shiftDown and key == wx.WXK_DOWN) \
                 or (altDown and key in (ord('N'), ord('n'))):
            self.OnHistoryReplace(step=-1)

        # Insert the previous command from the history buffer.
        elif ((rawControlDown or controlDown) and shiftDown and key == wx.WXK_UP) and self.CanEdit():
            self.OnHistoryInsert(step=+1)

        # Insert the next command from the history buffer.
        elif ((rawControlDown or controlDown) and shiftDown and key == wx.WXK_DOWN) and self.CanEdit():
            self.OnHistoryInsert(step=-1)

        # Search up the history for the text in front of the cursor.
        elif key == wx.WXK_F8:
            self.OnHistorySearch()

        # Don't backspace over the latest non-continuation prompt.
        elif key == wx.WXK_BACK:
            if selecting and self.CanEdit():
                event.Skip()
            elif currpos > self.promptPosEnd:
                event.Skip()

        # Only allow these keys after the latest prompt.
        elif key in (wx.WXK_TAB, wx.WXK_DELETE):
            if self.CanEdit():
                event.Skip()

        # Don't toggle between insert mode and overwrite mode.
        elif key == wx.WXK_INSERT:
            pass

        # Don't allow line deletion.
        elif controlDown and key in (ord('L'), ord('l')):
            # TODO : Allow line deletion eventually...
            #event.Skip()
            pass

        # Don't allow line transposition.
        elif controlDown and key in (ord('T'), ord('t')):
            # TODO : Allow line transposition eventually...
            # TODO : Will have to adjust markers accordingly and test if allowed...
            #event.Skip()
            pass

        # Basic navigation keys should work anywhere.
        elif key in NAVKEYS:
            event.Skip()

        # Protect the readonly portion of the shell.
        elif not self.CanEdit():
            pass

        elif (rawControlDown or controlDown):
            pass

        else:
            event.Skip()
