__author__ = "Atsushi Matsuda"


try:
    from . import version, cutoutAlign, alignfuncs, chromformat, aligner, chromeditor, threads, flatfielder, chromagnon
except:
    import version, cutoutAlign, alignfuncs, chromformat, aligner, chromeditor, threads, flatfielder, chromagnon

reload(version)
reload(cutoutAlign)
reload(alignfuncs)
reload(chromformat)
reload(aligner)
reload(chromeditor)
reload(threads)
reload(flatfielder)
reload(chromagnon)
try:
    from . import testfuncs
    reload(testfuncs)
except ImportError:
    pass

__version__ = version.version


