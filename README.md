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
Read the [domument](https://github.com/macronucleus/Chromagnon/releases/download/Doc-v0.5/DocumentV06.pdf)

Downloads
---------
The ready to use packages are available [here](https://github.com/macronucleus/Chromagnon/releases/tag/v0.6)

The source
----------
The source codes are written in pure python and works on the following platforms and dependencies.

Platforms successfully tested:
* MacOSX64bit (10.9.5 or higher)
* Windows64bit (XP or higher)
* Linux Ubuntu(16), CentOS(6)

Dependencies:
* python (2.7 or 3.6)
* numpy
* scipy
* wxpython (v3 or v4)
* pyopengl
* PyFFTW
* tifffile (version '2018.02.18')
* javabridge
* bioformats
* lxml

Authored and maintained by Atsushi Matsuda.
