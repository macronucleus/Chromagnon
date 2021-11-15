
import sys, os, imp, io
import chardet

#==== find encoding =====

def findEncoding(fn):
    det = chardet.UniversalDetector()
    with open(fn, 'rb') as h:
        for line in h:
            det.feed(line)
            if det.done:
                break
    result = det.close()
    return result['encoding']
    
##------ config IO ----------------
CONFPATH = 'programname.config'
def getConfigPath(fn=None, appname='Priithon'):
    """
    return hidden config file at the home directory
    """
    if not fn:
        fn = CONFPATH
    if sys.platform.startswith('win'):
        ofn = os.path.join(os.getenv('APPDATA'), appname, fn)
    else:
        ofn = os.path.join(os.path.expanduser('~'), '.' + appname, fn)
    return ofn

def readConfig(fn=None):
    """
    return config as a dictionary
    """
    kwds = {}
    if not fn:
        fn = getConfigPath()
    if os.path.exists(fn):
        encoding = findEncoding(fn)
        if sys.version_info.major == 3:
            h = open(fn, encoding=encoding)#'utf-8')
        else:
            h = io.open(fn, encoding=encoding)#'utf-8')
        for line in h:
            if not line.strip():
                continue
            key, val = line.split('=')
            val = val.replace(os.linesep, '')
            val = val.replace('\n', '') # windows does not keep os.linesep \r\n but changes to \n
            if val in ('True', 'False'):
                val = eval(val)
            elif val and val[0].isdigit():
                try:
                    val = eval(val)
                except:
                    pass
            kwds[key] = val
        h.close()
    return kwds

def saveConfig(**newkwds):
    """
    write dictionary into a text file
    the config file name can be changed by
    confpath: blabla..
    """
    if not newkwds:
        return
    fn = getConfigPath(newkwds.pop('confpath', CONFPATH))
    dirname = os.path.dirname(fn)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
    kwds = readConfig()
    kwds.update(newkwds)
    if sys.version_info.major == 3:
        h = open(fn, 'w', newline='', encoding='utf-8')
    else:
        #h = open(fn, 'w')
        h = io.open(fn, 'w', encoding='utf-8')
    for key, val in kwds.items():
        h.write('%s=%s%s' % (key, val, os.linesep))
    h.close()

def deleteConfig(name, **kwds):
    """
    delete entry with "name"
    """
    fn = getConfigPath(kwds.pop('confpath', CONFPATH))
    kwds = readConfig()

    if sys.version_info.major == 3:
        h = open(fn, 'w', newline='', encoding='utf-8')
    else:
        h = io.open(fn, 'w', encoding='utf-8')
    for key, val in kwds.items():
        if key != name:
            h.write('%s=%s%s' % (key, val, os.linesep))
    h.close()

# a helper function for debugging the packaged software
def main_is_frozen():
   return (getattr(sys, "frozen", False) or # new py2exe + pyinstaller
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze
