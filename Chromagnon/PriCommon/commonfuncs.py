
import sys, os, imp


##------ config IO ----------------
CONFPATH = 'programname.config'
def getConfigPath(fn=None):
    """
    return hidden config file at the home directory
    """
    if not fn:
        fn = CONFPATH
    if sys.platform.startswith('win'):
        ofn = os.path.join(os.getenv('APPDATA'), fn)
    else:
        ofn = os.path.join(os.path.expanduser('~'), '.' + fn)
    return ofn

def readConfig():
    """
    return config as a dictionary
    """
    kwds = {}
    fn = getConfigPath()
    if os.path.exists(fn):
        #with open(fn) as h:
        h = open(fn)
        for line in h:
            if not line.strip():
                continue
            key, val = line.split('=')
            val = val.replace(os.linesep, '')
            val = val.replace('\n', '') # windows does not keep os.linesep \r\n but changes to \n
            if val in ('True', 'False'):
                val = eval(val)
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
    kwds = readConfig()
    kwds.update(newkwds)
    if sys.version_info.major == 3:
        h = open(fn, 'w', newline='')
    else:
        h = open(fn, 'w')
    for key, val in kwds.items():
        h.write('%s=%s%s' % (key, val, os.linesep))
    h.close()

# a helper function for debugging the packaged software
def main_is_frozen():
   return (getattr(sys, "frozen", False) or # new py2exe + pyinstaller
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze
