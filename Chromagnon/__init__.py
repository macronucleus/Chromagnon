
import sys
if sys.version_info.major == 3:
    from importlib import reload

__author__ = "Atsushi Matsuda"

try:
    from . import version, cutoutAlign, alignfuncs, chromformat, aligner, chromeditor, threads, flatfielder, extrapanel, chromagnon
except (ValueError, ImportError):
    try:
        from Chromagnon import version, cutoutAlign, alignfuncs, chromformat, aligner, chromeditor, threads, flatfielder, extrapanel, chromagnon
    except ImportError:
        import version, cutoutAlign, alignfuncs, chromformat, aligner, chromeditor, threads, flatfielder, extrapanel, chromagnon

reload(version)
reload(cutoutAlign)
reload(alignfuncs)
reload(chromformat)
reload(aligner)
reload(chromeditor)
reload(threads)
reload(flatfielder)
reload(extrapanel)
reload(chromagnon)
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


