__version__=0.1

from . import glfunc, viewerCommon, viewer2, main

import sys
if sys.version_info.major == 3:
    from importlib import reload

reload(glfunc)
reload(viewerCommon)
reload(viewer2)
reload(main)
