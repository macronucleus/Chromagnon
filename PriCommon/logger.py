import logging
try:
    from Priithon.all import Y
except ImportError:
    pass # not priithon

THRESHOLD = logging.DEBUG
LEVEL_DIC = {'debug': logging.DEBUG,
             'info': logging.INFO,
             'warning': logging.WARNING,
             'error': logging.ERROR,
             'critical': logging.CRITICAL}
LOGS = []
LOG_FN = None

def getLogger(name):
    """
    return logger
    """
    global LOGS
    if LOG_FN:
        logging.basicConfig(filename=LOG_FN)
    else:
        logging.basicConfig()
    log = logging.getLogger(name)
    log.setLevel(THRESHOLD)
    LOGS.append(log)
    return log

def debug(log, msg, level=logging.DEBUG):
    """
    do logging
    """
    level = _getLevelName(level)
    exec('log.%s(msg)' % level)
    if log.getEffectiveLevel() <= level:
        try:
            Y.refresh()
        except:
            pass
    else:
        pass

def setLevel(level):
    """
    set global log threshould
    level can be integer or string, see LEVEL_DIC
    """
    global THRESHOLD, LOGS
    level = _getLevel(level)
    #print level
    for log in LOGS:
        log.setLevel(level)
       # debug(log, 'setLevel %i' % (level+1))
    THRESHOLD = level

def _getLevelName(level):
    """
    return string
    """
    if isinstance(level, basestring):
        if level not in LEVEL_DIC.keys():
            raise ValueError, '%s not found' % level
    else:
        level = logging.getLevelName(level).lower()
    return level.lower()

def _getLevel(level):
    """
    return number
    """
    if isinstance(level, basestring):
        level = level.lower()
        if level not in LEVEL_DIC.keys():
            raise ValueError, '%s not found' % level
        else:
            level = LEVEL_DIC[level]
    return level

def setLogFile(fn, maxBytes=1000000):
    global LOG_FN
    from logging import handlers
    handler = handlers.RotatingFileHandler(
              fn, maxBytes=maxBytes, backupCount=5)

    for log in LOGS:
        #print log.name
        log.addHandler(handler)

    LOG_FN = fn
