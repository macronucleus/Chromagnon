# Array I/O to text files
#

# seb changed Numeric to numarray - 2003-Apr-07
# seb changed numarray to numpy  - 2006-Jul-22

# Written by Konrad Hinsen <hinsen@cnrs-orleans.fr>
# last revision: 2001-12-5
#

"""This module contains elementary support for I/O of one- and
two-dimensional numerical arrays to and from plain text files. The
text file format is very simple and used by many other programs as
well:

- each line corresponds to one row of the array

- the numbers within a line are separated by white space

- lines starting with # are ignored (comment lines)

An array containing only one line or one column is returned as a
one-dimensional array on reading. One-dimensional arrays are written
as one item per line.

Numbers in files to be read must conform to Python/C syntax.  For
reading files containing Fortran-style double-precision numbers
(exponent prefixed by D), use the module Scientific.IO.FortranFormat.
"""

#from Scientific.IO.TextFile import TextFile
from Scientific_IO_TextFile import TextFile
import string, numpy



def readArray(filename, comment='#', sep=None):
    """Return an array containing the data from file |filename|. This
    function works for arbitrary data types (every array element can be
    given by an arbitrary Python expression), but at the price of being
    slow. For large arrays, use readFloatArray or readIntegerArray
    if possible.

    ignore all lines that start with any character contained in comment
    """
    data = []
    for line in TextFile(filename):
        if not line[0] in comment:
            data.append(map(eval, string.split(line, sep)))
    a = numpy.array(data)
    if a.shape[0] == 1 or a.shape[1] == 1:
        a = numpy.ravel(a)
    return a

def readArray_conv(filename, fn, comment='#', dtype=None, sep=None):
    """
    Return an array containing the data from file |filename|. This
    function works for arbitrary data types (every array element can be
    given by an arbitrary Python expression), but at the price of being
    slow. 
   
    fn is called for each "cell" value.
    if dtype is None, uses "minimum type" (ref. Numpy doc)
    if sep is None, any white space is seen as field separator
    ignore all lines that start with any character contained in comment
    """
    data = []
    for line in TextFile(filename):
        if not line[0] in comment:
            data.append(map(fn, string.split(line, sep)))
    a = numpy.array(data)
    if a.shape[0] == 1 or a.shape[1] == 1:
        a = numpy.ravel(a)
    return a

def readFloatArray(filename, dtype=numpy.float64, sep=None): ## seb added type argument
    "Return a floating-point array containing the data from file |filename|."
    data = []
    for line in TextFile(filename):
        if line[0] != '#':
            data.append(map(string.atof, string.split(line, sep)))
    a = numpy.array(data, dtype=dtype) ## seb added type argument
    if a.shape[0] == 1 or a.shape[1] == 1:
        a = numpy.ravel(a)
    return a

def readIntegerArray(filename, dtype=numpy.int32, sep=None): ## seb added type argument
    "Return an integer array containing the data from file |filename|."
    data = []
    for line in TextFile(filename):
        if line[0] != '#':
            data.append(map(string.atoi, string.split(line, sep)))
    a = numpy.array(data, dtype=dtype) ## seb added type argument
    if a.shape[0] == 1 or a.shape[1] == 1:
        a = numpy.ravel(a)
    return a

def writeArray(array, filename, mode='w', sep=' '):
    """Write array |a| to file |filename|. |mode| can be 'w' (new file)
       or 'a' (append)."""
    file = TextFile(filename, mode)
    if len(array.shape) == 1:
        array = array[:, numpy.newaxis]
    for line in array:
        #for element in line:
        #    file.write(`element` + sep)
        file.write(sep.join([`element` for element in line]))
        file.write('\n')
    file.close()

#
# Write several data sets (one point per line) to a text file,
# with a separator line between data sets. This is sufficient
# to make input files for most plotting programs.
#
def writeDataSets(datasets, filename, separator = ''):
    """Write each of the items in the sequence |datasets|
    to the file |filename|, separating the datasets by a line
    containing |separator|. The items in the data sets can be
    one- or two-dimensional arrays or equivalent nested sequences.
    The output file format is understood by many plot programs.
    """
    file = TextFile(filename, 'w')
    nsets = len(datasets)
    for i in range(nsets):
        d = numpy.array(datasets[i])
        if len(d.shape) == 1:
            d = d[:, numpy.newaxis]
        for point in d:
            for number in point:
                file.write(`number` + ' ')
            file.write('\n')
        if (i < nsets-1):
            file.write(separator + '\n')
    file.close()
