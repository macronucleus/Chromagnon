from wx.py.shell import *
from wx.py import introspect
import sys
import six
import warnings

### ---- py2 ------
try:
    PY3
except NameError:
    PY3 = False

###---- introspect ---------------
def hasattr(obj, attr):# am python3
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        try:
            return bool(getattr(obj, attr, None))
        except (NameError, ValueError):
            return False

#def hasattrAlwaysReturnsTrue(obj):
#    return hasattr(obj, 'bogu5_123_aTTri8ute')

class BytesIO_str(six.BytesIO):
    def __init__(self, arg=b''):
        if arg in six.string_types:
            arg = arg.encode()
        six.BytesIO.__init__(self, arg)

def getRoot(command, terminator=None):
    """Return the rightmost root portion of an arbitrary Python command.

    Return only the root portion that can be eval()'d without side
    effects.  The command would normally terminate with a '(' or
    '.'. The terminator and anything after the terminator will be
    dropped."""
    import tokenize
    command = command.split('\n')[-1]
    if command.startswith(sys.ps2):
        command = command[len(sys.ps2):]
    command = command.lstrip()
    command = introspect.rtrimTerminus(command, terminator)
    if terminator == '.':
        tokens = introspect.getTokens(command)
        if not tokens:
            return ''
        if tokens[-1][0] is tokenize.ENDMARKER:
            # Remove the end marker.
            del tokens[-1]
        if tokens[-1][0] is tokenize.NEWLINE:
           # print('removing')
            # Remove the new line introduced after python3.6.7
            del tokens[-1]
        if not tokens:
            return ''
        if terminator == '.' and \
               (tokens[-1][1] != '.' or tokens[-1][0] is not tokenize.OP):
            # Trap decimals in numbers, versus the dot operator.
            return ''

    #print(command)
    # Strip off the terminator.
    if terminator and command.endswith(terminator):
        size = 0 - len(terminator)
        command = command[:size]

    command = command.rstrip()
    tokens = introspect.getTokens(command)
    tokens.reverse()
    line = ''
    start = None
    prefix = ''
    laststring = '.'
    lastline = ''
    emptyTypes = ('[]', '()', '{}')
    for token in tokens:
        tokentype = token[0]
        tokenstring = token[1]
        line = token[4]
        #if tokentype is tokenize.ENDMARKER:
        # Remove the new line introduced after python3.6.7
        if tokentype in (tokenize.ENDMARKER, tokenize.NEWLINE):
            continue
        if PY3 and tokentype is tokenize.ENCODING:
            line = lastline
            break
        if tokentype in (tokenize.NAME, tokenize.STRING, tokenize.NUMBER) \
        and laststring != '.':
            # We've reached something that's not part of the root.
            if prefix and line[token[3][1]] != ' ':
                # If it doesn't have a space after it, remove the prefix.
                prefix = ''
            break
        if tokentype in (tokenize.NAME, tokenize.STRING, tokenize.NUMBER) \
        or (tokentype is tokenize.OP and tokenstring == '.'):
            if prefix:
                # The prefix isn't valid because it comes after a dot.
                prefix = ''
                break
            else:
                # start represents the last known good point in the line.
                start = token[2][1]
        elif len(tokenstring) == 1 and tokenstring in ('[({])}'):
            # Remember, we're working backwords.
            # So prefix += tokenstring would be wrong.
            if prefix in emptyTypes and tokenstring in ('[({'):
                # We've already got an empty type identified so now we
                # are in a nested situation and we can break out with
                # what we've got.
                break
            else:
                prefix = tokenstring + prefix
        else:
            # We've reached something that's not part of the root.
            break
        laststring = tokenstring
        lastline = line
    if start is None:
        start = len(line)
    root = line[start:]
    if prefix in emptyTypes:
        # Empty types are safe to be eval()'d and introspected.
        root = prefix + root
    return root


introspect.hasattr = hasattr
introspect.BytesIO = BytesIO_str
introspect.getRoot = getRoot

### ---- frame.py -------------
# Error at line 899, AttributeError, module wx has no attribute SAVE
if wx.version().startswith('4'):
    wx.SAVE = wx.FD_SAVE
    wx.OVERWRITE_PROMPT = wx.FD_OVERWRITE_PROMPT

### ---- shell --------------------


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
            r= wx.MessageBox("close all other windows ?", 
                             "other open windows !", 
                             style=wx.CENTER|wx.YES_NO|wx.CANCEL|wx.ICON_EXCLAMATION)
            if r == wx.YES:
                for f in wx.GetTopLevelWindows():
                    if (f is not self and (not hasattr(f, "IwantToClose_hack")
                            or not f.IwantToClose_hack)):
                        f.Close()
            elif r == wx.CANCEL:
                self.IwantToClose_hack = False # 20080730 
                sebVeto = True

        if self.shell.waiting or sebVeto:
            if event.CanVeto():
                event.Veto(True)
        else:
            self.shell.destroy()
            self.Destroy()

class PriShell(Shell):
    def __init__(self, *args, **kwds):
        Shell.__init__(self, *args, **kwds)

    ## am
    def GetCurrentPos2Sep(self, currpos, stoppos):
        seps = ('@', '%', '&', '*', '(', ')', '-', '+',  '=', '[', ']', '{', '}', ';', ':', '<', '>', '/', ',')
        for sep in seps:
            command = self.GetTextRange(stoppos, currpos)
            if sep in command and '"' not in command and "'" not in command:
                shiftpos = command.rindex(sep) + 1
                command = self.GetTextRange(stoppos+shiftpos, currpos)
                stoppos += shiftpos
        return stoppos
        
    def OnChar(self, event):
        """Keypress event handler.

        Only receives an event if OnKeyDown calls event.Skip() for the
        corresponding event."""

        if self.noteMode:
            event.Skip()
            return

        # Prevent modification of previously submitted
        # commands/responses.
        if not self.CanEdit():
            return
        key = event.GetKeyCode()
        currpos = self.GetCurrentPos()
        stoppos = self.promptPosEnd
        stoppos = self.GetCurrentPos2Sep(currpos, stoppos) # am
        # Return (Enter) needs to be ignored in this handler.
        if key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            pass
        elif key in self.autoCompleteKeys:
            # Usually the dot (period) key activates auto completion.
            # Get the command between the prompt and the cursor.  Add
            # the autocomplete character to the end of the command.
            #if self.AutoCompActive(): # am
            #    self.AutoCompCancel() # am
            command = self.GetTextRange(stoppos, currpos).strip() + chr(key)
            self.write(chr(key))
            if self.autoComplete:
                #try:
                self.autoCompleteShow(command)
                #except ValueError: # numpy version imcompatibility # am 20210125
                #    pass
        elif key == ord('('):
            # The left paren activates a call tip and cancels an
            # active auto completion.
            #if self.AutoCompActive(): # am
            #    self.AutoCompCancel() # am
            # Get the command between the prompt and the cursor.  Add
            # the '(' to the end of the command.
            self.ReplaceSelection('')
            command = self.GetTextRange(stoppos, currpos).strip() + '('
            self.write('(')
            self.autoCallTipShow(command, self.GetCurrentPos() == self.GetTextLength())
        else:
            # erase call tip ##-- am
            if self.CallTipActive():
                self.CallTipCancel()

            # Allow the normal event handling to take place.
            event.Skip()

    def OnKeyDown(self, event):
        """Key down event handler."""

        key = event.GetKeyCode()
        # If the auto-complete window is up let it do its thing.
        if self.AutoCompActive():
            event.Skip()
            return
        
        # Prevent modification of previously submitted
        # commands/responses.
        controlDown = event.CmdDown() or event.RawControlDown() # 20080407: added CmdDown 20141129 added "Raw"ControlDown
        altDown = event.AltDown()
        shiftDown = event.ShiftDown()
        currpos = self.GetCurrentPos()
        endpos = self.GetTextLength()
        selecting = self.GetSelectionStart() != self.GetSelectionEnd()
        # Return (Enter) is used to submit a command to the
        # interpreter.

        if controlDown and key in (ord('F'), ord('f')): # pressing 'f' gives 'F' on Windows
            dialog = wx.TextEntryDialog(None, "search for:",
                                    'search', '')
            try:
                if dialog.ShowModal() == wx.ID_OK:
                    txt=self.searchTxt = dialog.GetValue()
                    l=len(txt)
                    #search-forward self.SetTargetStart(0)
                    #search-forward self.SetTargetEnd  (self.GetTextLength())
                    self.SetTargetStart(self.GetTextLength())
                    self.SetTargetEnd  (0)
                    pp = self.SearchInTarget( txt )
                    #self.SetCurrentPos( pp )
                    #search-forward self.SetSelection(pp,pp+l)
                    self.SetSelection(pp+l,pp)
            finally:
                dialog.Destroy()
            return
        if controlDown and key in (ord('G'), ord('g')): # pressing 'f' gives 'F' on Windows
            txt=self.searchTxt
            l=len(txt)
            pp = self.GetCurrentPos();
            #search-forward self.SetSelection(pp,pp)
            self.SetSelection(pp-l,pp-l)
            self.SearchAnchor()
            #search-forward pp = self.SearchNext(0, txt)
            pp = self.SearchPrev(0, txt)
            #self.SetCurrentPos( pp )
            #search-forward self.SetSelection(pp,pp+l)
            self.SetSelection(pp+l,pp)
            return
        if controlDown and key in (ord('H'), ord('h')): # pressing 'f' gives 'F' on Windows
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
                self.SetSelection( startP, endP ) # select reappearing text to allow "hide again"
                return
            startP,endP = self.GetSelection()
            endP-=1
            startL,endL = self.LineFromPosition(startP), self.LineFromPosition(endP)

            if endL == self.LineFromPosition(self.promptPosEnd): # never hide last prompt
                endL -= 1

            m = self.MarkerGet(startL)
            self.MarkerAdd(startL, 0)
            self.HideLines(startL+1,endL)
            self.SetCurrentPos( startP ) # to ensure caret stays visible !

        if key == wx.WXK_F12 or controlDown and key in (ord('N'), ord('n')): #seb
            if self.noteMode:
                # self.promptPosStart not used anyway - or ? 
                self.promptPosEnd = self.PositionFromLine( self.GetLineCount()-1 ) + len(str(sys.ps1))
                self.SetCaretForeground("black")
                self.SetCaretWidth(1)    #default
                self.SetCaretPeriod(500) #default
            else:
                self.SetCaretForeground("red")
                self.SetCaretWidth(4)
                self.SetCaretPeriod(0) #steady

            self.noteMode = not self.noteMode
            #seb print "self.noteMode=", self.noteMode
            return
        if self.noteMode:
            event.Skip()
            return

        if not controlDown and key == wx.WXK_RETURN:
            if self.CallTipActive():
                self.CallTipCancel()
            self.processLine()
        # Ctrl+Return (Cntrl+Enter) is used to insert a line break.
        elif controlDown and key == wx.WXK_RETURN:
            if self.CallTipActive():
                self.CallTipCancel()
            #seb 20070106 if currpos == endpos:
            #seb 20070106     self.processLine()
            #seb 20070106 else:
            self.insertLineBreak() # seb: insert always
        # Let Ctrl-Alt-* get handled normally.
        elif controlDown and altDown:
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
                self.autoCallTipShow(command, alwaysShow=True)
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

        # Increase font size.
        elif controlDown and key in (ord(']'),):
            dispatcher.send(signal='FontIncrease')
        # Decrease font size.
        elif controlDown and key in (ord('['),):
            dispatcher.send(signal='FontDecrease')
        # Default font size.
        elif controlDown and key in (ord('='),):
            dispatcher.send(signal='FontDefault')
        # Cut to the clipboard.
        elif (controlDown and key in (ord('X'), ord('x'))) \
        or (shiftDown and key == wx.WXK_DELETE):
            self.Cut()
        # Copy to the clipboard.
        elif controlDown and not shiftDown \
            and key in (ord('C'), ord('c'), wx.WXK_INSERT):
            self.Copy()
        # Copy to the clipboard, including prompts.
        elif controlDown and shiftDown \
            and key in (ord('C'), ord('c'), wx.WXK_INSERT):
            self.CopyWithPrompts()
        # Copy to the clipboard, including prefixed prompts.
        elif altDown and not controlDown \
            and key in (ord('C'), ord('c'), wx.WXK_INSERT):
            self.CopyWithPromptsPrefixed()
        elif controlDown and key in (ord('E'), ord('e')):#20051104 seb 20170112 am
            event.SetControlDown(False)
            #event.m_keyCode = wx.WXK_END
            #event.KeyCode = wx.WXK_END
            pos = self.GetLastPosition()
            self.SetCurrentPos(pos)
            self.SetAnchor(pos)
            #event.Skip()
            return                     
        # Home needs to be aware of the prompt.
        elif key == wx.WXK_HOME \
                 or controlDown and key in (ord('A'), ord('a')):#20051104 seb
            home = self.promptPosEnd
            if 1:#currpos >= home: # 20051101 '>' changed to '>='
                self.SetCurrentPos(home)
                if not selecting and not shiftDown:
                    self.SetAnchor(home)
                    self.EnsureCaretVisible()
            else:
                event.m_controlDown = False#20051104 seb
                event.m_keyCode = wx.WXK_HOME#20051104 seb
                event.Skip()
        #
        # The following handlers modify text, so we need to see if
        # there is a selection that includes text prior to the prompt.
        #
        # Don't modify a selection with text prior to the prompt.
        elif selecting and key not in NAVKEYS and not self.CanEdit():
            pass
        # Paste from the clipboard.
        elif (controlDown and not shiftDown and key in (ord('V'), ord('v'))) \
                 or (shiftDown and not controlDown and key == wx.WXK_INSERT):
            self.Paste()
        # Paste from the clipboard, run commands.
        elif controlDown and shiftDown and key in (ord('V'), ord('v')):
            self.PasteAndRun()
        # Replace with the previous command from the history buffer.
        elif (controlDown and key == wx.WXK_UP) \
                 or (altDown and key in (ord('P'), ord('p'))):
            self.OnHistoryReplace(step=+1)
        # Replace with the next command from the history buffer.
        elif (controlDown and key == wx.WXK_DOWN) \
                 or (altDown and key in (ord('N'), ord('n'))):
            self.OnHistoryReplace(step=-1)
#seb took this out         # Insert the previous command from the history buffer.
#seb took this out         elif (shiftDown and key == wx.WXK_UP) and self.CanEdit():
#seb took this out             self.OnHistoryInsert(step=+1)
#seb took this out         # Insert the next command from the history buffer.
#seb took this out         elif (shiftDown and key == wx.WXK_DOWN) and self.CanEdit():
#seb took this out             self.OnHistoryInsert(step=-1)
#seb took this out         # Search up the history for the text in front of the cursor.
        elif key == wx.WXK_F8 \
                 or controlDown and key in (ord('R'), ord('r')):#20051104 seb
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
        #seb 20070106 # Don't toggle between insert mode and overwrite mode.
        #seb 20070106 elif key == wx.WXK_INSERT:
        #seb 20070106     pass
        # Don't allow line deletion.
        elif controlDown and key in (ord('L'), ord('l')):
            pass
        # Don't allow line transposition.
        elif controlDown and key in (ord('T'), ord('t')):
            pass
        # Basic navigation keys should work anywhere.
        elif key in NAVKEYS:
            event.Skip()
        # Protect the readonly portion of the shell.
        elif not self.CanEdit():
            pass
        else:
            event.Skip()

    
