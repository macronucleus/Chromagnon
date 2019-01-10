# Chromagnon
Image correction software for chromatic shifts in fluorescence microscopy.


Acceptable image file formats
-----------------------------
### Reading
* Most microscopy formats

### Writing
* multipage-tiff (imageJ format or ome.tif format)
* DeltaVision (.dv)

How it works
------------
Read the [domument](https://github.com/macronucleus/Chromagnon/releases/download/v0.69/ChromagnonDocumentV065.pdf)

Downloads
---------
The ready to use packages are available [here](https://github.com/macronucleus/Chromagnon/releases)

The source
----------
The source code is written in pure python and works on the following platforms and dependencies.

Platforms successfully tested:
* MacOSX64bit (10.9.5 or higher)
* Windows64bit (XP or higher)
* Linux Ubuntu(16), CentOS(6)

Dependencies:
* `python` (v2.7 or v3.6)
* `numpy`
* `scipy`
* `wxPython` (v3 or v4)
* `PyOpenGL`
* `tifffile` (v0.14.0-v0.15.1)
* `pyFFTW` (optional for fast Fourier transform)
* `javabridge` (optional for reading more image file formats)
* `python-bioformats` (optional for reading more image file formats)
* `lxml` (optional for reading more image file formats)
* `Java Development Kit` (optional for reading more image file
formats)
* `PyPubSub` (optional for source code installation)

How to cite
----------
Please cite our paper:

[Matsuda, Schermelleh, Hirano, Haraguchi, Hiraoka, 2018 "Accurate and fiducial-marker-free correction for three-dimensional chromatic shift in biological fluorescence microscopy"  Sci Rep 8:7583](https://www.nature.com/articles/s41598-018-25922-7)


Authored and maintained by Atsushi Matsuda.
