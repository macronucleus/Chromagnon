# Chromagnon
Image correction software for chromatic shifts in fluorescence microscopy.


Acceptable image file formats
-----------------------------
### Reading
* Most microscopy formats
### Writing
* multipage-tiff (ome.tif)
* DeltaVision (.dv)

How it works
------------
Read the [domument](https://github.com/macronucleus/chromagnon/releases/download/Doc-0.5/Document.pdf)

Downloads
---------
The ready to use packages are available [here](https://github.com/macronucleus/Chromagnon/releases)

The source
----------
The source codes are written in pure python and works on the following platforms and dependencies.

Platforms successfully tested:
* MacOSX64bit (10.9.5-10.11.6)
* Windows64bit (XP-10)
* Linux Ubuntu(16)

Dependencies:
* python (2.7)
* opencv
* numpy
* scipy
* wxpython
* pyopengl
* fftw3 with FFTW3.3.4
* javabridge
* bioformats

Run the following command on the terminal to run Chromagnon.
>> pythonw ~/chromagnon/main.py

Authored and maintained by Atsushi Matsuda.
