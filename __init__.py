__author__ = "Atsushi Matsuda"

import alignfuncs, aligner, listbox, chromeditor, threads, flatfielder, main, testfuncs

reload(alignfuncs)
reload(aligner)
reload(listbox)
reload(chromeditor)
reload(threads)
reload(flatfielder)
reload(main)
reload(testfuncs)

__version__ = main.__version__

#######
# Version history
#
# v0.4
# 1. Compatible with SIR images after discarding below 0.
# 2. Added a function to modify the output file suffix by the user.
# 3. Improved the criteria for the automatic Z mag calculation
# 4. Improved initial guess box
# 5. Added flat fielder
# 6. Fixed key event responses of the viewer
# 7. Fixed the crushing event when opening too many images
# 8. Added the "up" button for the file selector
# 9. The local distortion calculation was improved.
# 10.Added command line options.
# 11.Finding best reference sections are now compatible with bright field images.
# 12.Global correction includes 3DXcorr before finish.


# Things to do:
# * 3D local alignment
# * Add command line options for Flat fielder
