v0.6 (Feb. 2018)
----
1. Updated to Python3.6, wxpython, OpenGL, bioformats
2. The ndviewer package was moved to the higher level in the directory structure.
3. image IO modules were moved to imgIO package.
4. Added MultitifIO (for `ImageJ` format) and ImgSeqIO (for `file
   sequence`) to `imgio`.
5. Multitiff (ome and imageJ) file formats were now read by `MultitifReader` instead of
previously used `BioformatsReader`
6. empty -> zeros in `imgResample` to prevent values outside the
shifted image.
7. ndviewer uses isotropic magnification for orthgonal view, changes
in `main.py`, `viewerCommon.py`, `glfunc.py`.
8. chromeditor view magZ was fixed (`ndviewer.viewer2.py`).
9. ImageJ file format is written by `MultitifReader`.
10. Chromagnon tif format was changed to a custom `imageJ` format.
11. `pyfftw3` was changed to `pyfftw`.
12. Replaced functions of `opencv` with `scipy`.
13. Log file time was fixed and now contains more information.
14. Lastpath was changed when files were read by Drag and Drop.
15. Fixed Y axis orientation for non-MRC images.
16. `open(newline='')` in `commonfuncs.py` and `chromformat.py`
17. Fixed autosort on Windows (`listbox.py` and `chromeditor.py`)
18. Used nomkl numpy and scipy
19. JDK removed and added a dialog to navigate to download
(`PriCommon.listbox.py`)
20. Added functions to detect and fix saturated pixels
(`alignfuncs.py` and `aligner.py`)
21. Fixed imgSequence bug for uint8 data type in
`imgio.bioformatsIO.py`.
22. Added calcuration for min and max for dv files (`imgio.mrcIO.py`)
23. The lsm format is read by `imgio.multitifIO.py`
24. Fixed wrong unit conversion for pixel size in
`imgio.multitifIO.py` and `imgio.bioformatsIO.py`
25. Fixed AttributeError for `mouse_last_x` in `ndvierwer.viewer2.py`
26. (v0.61) Fixed broken command line options.
27. (v0.61) Fixed importError when installed from the source (to
import `imgio` from `PriCommon`)
28. (v0.61) Fixed division error in `imgio.multitifIO.py` for
python2.7.
29. (v0.62) Z mag correction is done with zoomed image. 
30. (v0.62) An error when executing without suffix was solved.
31. (v0.62) Z mag selection was removed and averaging function
    added.
32. (v0.62) Edge pixels (including vertical) are removed for
quadrisection phase correlation.
33. (v0.62) ImageJ metadata is copied in `imgio.multitifIO.py`.
34. (v0.63) entry_points for source code installation was fixed
35. (v0.63) relative and absolute import was re-organized.
36. (v0.63) `ome.tif` was removed from the selection list for the
output file when `python-bioformats` is not installed.
37. (v0.63) z translation calculation mistake introduced in v0.62 was
fixed.
38. (v0.64) `imgio.multitifIO.py` was fixed for reading single
wavelength and ome.tif.
39. (v0.64) Errors in `PriCommon.flatconv.py` was fixed and put the
version number in `flatfielder.py` (v0.2).
40. (v0.64) Version number added to the command line option.
41. (v0.65) Choice for number of iterations to do 3D cross
correlation.
42. (v0.65) A problem to select regions with SoftWorx was fixed by
fixing extended header for dv files (`imgio.mrcIO.py`).
43. (v0.65) `alignfuncs.chopShapeND` was fixed to chop an image shape
with the exact number of pixels to chop.
44. (v0.65) `imgio.multitifIO.py` was fixed for reading channel data
of `ome.tif` and `lsm` file formats.
45. (v0.65) default wild card was changed from `*.*dv` to `*`.
46. (v0.66) Error message when the reference wavelength was not found
in the target image was fixed. (`chromformat.py`)
47. (v0.66) Multitiff reader dtype was also read not only 
from series but also form page. (`imgio.multitifIO.py`)
48. (v0.66) Warning message was ignored when chromagnon was run as
__main__. (`chromagnon.py`)
49. (v0.66) When not or only one wavelength is in common, then the
    program shows a warning message and quits. When at least two
    wavelengths are in common, the the program proceeds to align the
    comon two channels and leaves the uncommon channels
    unaligned. (`chromagnon.py` and `aignfuncs.py`)
50. (v0.66) `ImageIOError` was created in `imgio.generalIO.py`.
51. (v0.67) If dtype was not found in `tifffile`, then the file is read
    by `bioformats`.

v0.5 (Jan. 2017)
----
1. Included `Bioformats` (affected to `aligner.py`, `ndviewer`, `listbox.py`)
2. Added `chromformat.py` to accomodate string format for wavelength
3. Compatible with `OpenCV3.3`
4. Fixed instability when opening viewer on Linux
5. Warning message for init guess was changed slightly
6. Added `setup.py`
7. (v0.5.6) Changed the package name `chromagnon` to `Chromagnon`, and the
   module name `main.py` to `chromagnon.py` to be compatible with
   "script" scheme on Mac and Windows installation from the source.
8. (v0.5.6) Changed directory structure to include Priithon and PriCommon
inside Chromagnon
9. (v0.5.6) Added entry_points or scripts to `setup.py`
10. (v0.5.6) Removed grid view for local alignment.
11. (v0.5.7) Alternative calculation is changed from simplex to
logpolar transformation for YX plane.
12. (v0.5.7) the choice list for "min window size" was added and
default was changed from 30 to 240. <-- deleted! Using fixed value 60.
13. (v0.5.7) Add an autofocus button and fixed a bug in ndviewer
    ("mydoc.roi_start" not found).
14. (v0.5.7) Fixed errors in flat fielder (name and viewer) (in `flatfielder.py`).
15. (v0.5.7) Fixed errors when local alignment was
    used as and initial guess for images with different sizes from the
    original image (in `chromformat.py`).
16. (v0.5.7) Local alignment now uses frequency space interpolation instead
of 3rd order spline interpolation, and filled the space without
siginificant signals. Also codes were fixed to reflect the results,
and window size for optimal alignment.
17. (v0.5.7) Initial guess for affine Z alignment was fixed.
18. (v0.5.7) Viewing local alignment became much nicer to see small
shifts.
19. (v0.5.7) A progress bar was added.
20. (v0.5.7) Initguess removed (which reduces registration accuracy)
21. (v0.5.7) Cross correlation padding was added (in `xcorr.py`)
22. (v0.5.7) The maximum window size for local registration was added.
23. (v0.5.7) Fixed unequal shape in phase contrast filter (in
    `xcorr.py`), and moving phase contrast filter before xcorr (`alignfunc.py`), improving z
    registration accuracy.
24. (v0.5.7) Changed nyquist for phase contrast filter (in `xcorr.py`)
25. (v0.5.7) Changed _ALN file pattern (in `PriCommon.bioformats.py`)

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
