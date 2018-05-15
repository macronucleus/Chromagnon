from __future__ import print_function
import sys, os, threading

iWORK_VERSION=['09', '08']
MSOFFICE_VERSION=['2011', '2008', 'X'] # newer has the priority

def openTable(fn):
    """
    return threading.Thread
    """
    return _open(_openTable, (fn,))

def _open(func, args):
    """
    Since some programs locks the main thread, this function creates a thread to run the program
    """
    th = threading.Thread(target=func, args=args)
    th.start()
    return th
    
def _openTable(fn):
    if sys.platform.startswith('linux'):
        for prog in ['oocalc', 'libreoffice --calc']:
            #pass # not working now
            error = os.system('%s "%s"' % (prog, fn))
            if not error:
                break

    elif sys.platform.startswith('darwin'):
        prog = ''
        for v in iWORK_VERSION:
            iworkDir = r"/Applications/iWork '%s" % v
            if os.path.exists(iworkDir):
                prog = 'Numbers'
                break
        if not prog:
            if os.path.exists(r"/Applications/Numbers.app"):
                prog = 'Numbers'
        if not prog:
            for v in MSOFFICE_VERSION:
                officeDir = r'/Applications/Microsoft Office %s' % v
                if os.path.exists(officeDir):
                    officeDir = officeDir.replace(' ', r'\ ')
                    name = 'Microsoft\ Excel'
                    if v != 'X':
                        name += '.app'
                    prog = os.path.join(officeDir, name)
                    break
        if not prog:
            for openoffice in [r'/Applications/NeoOffice.app']:
                if os.path.exists(openoffice):
                    prog = openoffice
        if prog:
            err=os.system(r'open -a %s "%s"' % (prog, fn))
            if err:
                print('program %s exit status %s' % (prog, err))

    elif 'win' in sys.platform:
        try:
            os.system('start excel.exe "%s"' % fn)
        except:
            try:
                from win32com.client import Dispatch
                xl = Dispatch('Excel.Application')
                wb = xl.Workbooks.Open(fn)
            except:
                pass

def openImage(fn):
    if sys.platform.startswith('darwin'):
        prog = 'Preview'
        if prog:
            err=os.system(r'open -a %s %s' % (prog, fn))
            if err:
                print('program %s exit status %s' % (prog, err))
