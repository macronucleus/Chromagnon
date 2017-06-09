
v0.5 (Jan. 2017)
----
1. Included `Bioformats` (affected to `aligner.py`, `ndviewer`, `listbox.py`)
2. Added `chromformat.py` to accomodate string format for wavelength
3. Compatible with `OpenCV3.3`
4. Fixed instability when opening viewer on Linux
5. Warning message for init guess was changed slightly
6. Added `setup.py`
7. Changed the package name `chromagnon` to `Chromagnon`, and the
   module name `main.py` to `chromagnon.py` to be compatible with
   "script" scheme on Mac and Windows installation from the source.
8. Changed directory structure to include Priithon and PriCommon
inside Chromagnon
9. Added entry_points or scripts to `setup.py`
10. Removed grid view for local alignment.

v0.4 (Sep. 2016)
----
1. Compatible with SIR images after discarding below 0.
2. Added a function to modify the output file suffix by the user.
3. Improved the criteria for the automatic Z mag calculation
4. Improved initial guess box
5. Added flat fielder
6. Fixed key event responses of the viewer
7. Fixed the crushing event when opening too many images
8. Added the "up" button for the file selector
9. The local distortion calculation was improved.
10.Added command line options.
11.Finding best reference sections are now compatible with bright field images.
12.Global correction includes 3DXcorr before finish.
