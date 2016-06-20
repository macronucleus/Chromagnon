# Chromagnon
Image correction software for chromatic shifts in fluorescence microscopic images
Acceptable image file formats are multipage-tiff (.tif) and DeltaVision (.dv).

How it works
------------
Read the domument: https://github.com/macronucleus/chromagnon/releases/download/Doc-0.3/Document.pdf

Downloads
---------
The ready to use packages are available.
* Mac (10.9-): https://github.com/macronucleus/chromagnon/releases/tag/mac-v0.3
* Windows (64-bit): https://github.com/macronucleus/chromagnon/releases/tag/win-v0.3

The source
----------
The source code are written in pure python and works on the following platforms and dependencies.

Platforms successfully tested:
* MacOSX64bit (10.9.5-10.11.1)
* Windows64bit (7-8)
* Linux Ubuntu 10.4

Dependencies:
* python (2.5 - 2.7)
* opencv (2.4.0 - 2.4.8)
* numpy (1.3.0 - 1.7.1)
* scipy (0.7.1rc3 - 0.13.2)
* wxpython (2.8.9.2 - 3.0.0.0)
* pyopengl (2.0.2.01 - 3.0.2)
* fftw3 (0.2.1) with FFTW3.3.4
* tifffile (0.7.0)

Run the following command on the terminal to run Chromagnon.
>> pythonw ~/chromagnon/main.py

Authored and maintained by Atsushi Matsuda.