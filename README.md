# Chromagnon
Image correction software for chromatic shifts in fluorescence microscopy.


Acceptable image file formats
-----------------------------
### Reading
* Most microscopy formats (same as ImageJ)

### Writing
* multipage-tiff (imageJ format or ome.tif format)
* DeltaVision (.dv)

How it works
------------
Read the [document](https://github.com/macronucleus/Chromagnon/releases/download/Doc-v0.5/ChromagnonDocumentV090.pdf).

If you prefer, watch the
[movie](https://www.jove.com/v/60800/high-accuracy-correction-3d-chromatic-shifts-age-super-resolution)
by JoVE.

[The full text article](https://www.jove.com/video/60800) describes
in more detail about
sample preparation, software usage, trouble shooting, etc...


Downloads
---------
The ready to use packages are available
[here](https://github.com/macronucleus/Chromagnon/releases)

Example Images
--------------
Example images for testing are available  [(422 MB)](https://github.com/macronucleus/Chromagnon/releases/download/exampleimages/SampleImages.zip)

The source
----------
The source code is written in pure python and works on the following platforms and dependencies.

Platforms successfully tested:
* MacOSX64bit (10.9.5 or higher)
* Windows64bit (XP or higher)
* Linux Ubuntu(16-18), CentOS(6)

Dependencies:
* `python` (v2.7 or >v3.6)
* `numpy`
* `scipy`
* `tifffile <= 2021.7.2` 
* `chardet`
* `wxPython` (optional for GUI)
* `PyOpenGL` (optional for GUI)
* `pyFFTW` (optional for fast Fourier transform)
* `javabridge` (optional for reading more image file formats)
* `python-bioformats` (optional for reading more image file formats)
* `lxml` (optional for reading more image file formats)
* `Java Development Kit` (optional for reading more image file
formats)

How to cite
----------
Please cite our paper:

1. [Matsuda, Schermelleh, Hirano, Haraguchi, Hiraoka, 2018 "Accurate and fiducial-marker-free correction for three-dimensional chromatic shift in biological fluorescence microscopy"  Sci Rep 8:7583](https://www.nature.com/articles/s41598-018-25922-7)

2. [Matsuda, Kojin, Schermelleh, Haraguchi, Hiraoka, 2020 "High-Accuracy Correction of 3D Chromatic Shifts in the Age of Super-Resolution Biological Imaging Using Chromagnon." J. Vis. Exp. (160), e60800](https://www.jove.com/video/60800)

Authored and maintained by Atsushi Matsuda.
