
__author__ = "Atsushi Matsuda"

import sys
if sys.version_info.major == 3:
    from importlib import reload

if getattr(sys, 'frozen', False):
    import warnings
    warnings.simplefilter('ignore')

try:
    from . import version, cutoutAlign, alignfuncs, chromformat, aligner, threads, chromagnon
except (ValueError, ImportError):
    try:
        from Chromagnon import version, cutoutAlign, alignfuncs, chromformat, aligner, threads, chromagnon
    except ImportError:
        import version, cutoutAlign, alignfuncs, chromformat, aligner, threads, chromagnon

reload(version)
reload(cutoutAlign)
reload(alignfuncs)
reload(chromformat)
reload(aligner)
reload(threads)
reload(chromagnon)

try:
    import wx
    try:
        from . import chromeditor, flatfielder, extrapanel
    except (ValueError, ImportError):
        try:
            from Chromagnon import chromeditor, flatfielder, extrapanel
        except ImportError:
            import chromeditor, flatfielder, extrapanel
    reload(chromeditor)
    reload(flatfielder)
    reload(extrapanel)
except ImportError:
    pass


try:
    from . import testfuncs
    reload(testfuncs)
except ImportError:
    try:
        import testfuncs
        reload(testfuncs)
    except ImportError:
        pass

__version__ = version.version


