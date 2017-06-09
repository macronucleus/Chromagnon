#!/usr/bin/env priithon
try: # inside package
    from ..Priithon import Mrc
except ValueError: # Attempted relative import beyond toplevel package
    from Priithon import Mrc
import OMXlab as O
import os

DEF_BYTE = '<'
DEF_EXT = 'dv'

def byteSwap(fn, out=None, byteOrder=DEF_BYTE):
    """
    change byteorder
    """
    if not out:
        out = os.path.extsep.join((fn, DEF_EXT))
        
    src = O.mrcIO.Mrc3(fn)

    dt = decideDtype(src.hdr.PixelType, byteOrder)

    extFloats = extInts = None
    if src.hdr.NumFloats:
        extFloats = src.extFloats
    if src.hdr.NumIntegers:
        extInts = src.extInts
    
    des = O.mrcIO.newOutFile(out, src.hdr, extInts, extFloats, askIfExist=None)

    for slot in des.hdr.__slots__:
        val = des.hdr.__getattr__(slot)
        dtype = val.dtype.str
        if dtype[0] != '|':
            dtype = byteOrder + dtype[1:]
            des.hdr.__setattr__(slot, val.astype(dtype))

    # this is for ImageJ
    if extFloats is None and extInts is None:
        #nsecs = des.hdr.Num[-1]
        des.makeExtendedHdr(1, 1)#nsecs,nsecs)
        des.hdr.NumFloats = 1 #nsecs
        des.hdr.NumIntegers = 1

    O.mrcIO.writeHeader(des)

    nsec = src.hdr.Num[-1]
    for i in range(nsec):
        a = O.mrcIO._input(src, i)
        O.mrcIO._output(des, a.astype(dt), i)
    src.close()
    des.close()
    return out

def decideDtype(pxtype, byteOrder=DEF_BYTE):
    if pxtype == 0:
        dt = '%su1'
    elif pxtype == 1:
        dt = '%si2'
    elif pxtype == 2:
        dt = '%sf4'
    elif pxtype == 3:
        raise ValueError, 'Complex 2 signed 16-bit integers??'
    elif pxtype == 4:
        dt = '%sc8'
    elif pxtype == 5:
        dt = '%si2'
    elif pxtype == 6:
        dt = '%su2'
    elif pxtype == 7:
        dt = '%si4'
    dt = dt % byteOrder

    return dt

def main(*args):
    """
    aks for filenames
    tells you finished files using shell Messages
    """
    import wx
    from Priithon.all import Y
    
    dlg = wx.FileDialog(None, 'Choose image files', style=wx.OPEN|wx.MULTIPLE|wx.CHANGE_DIR)
    if dlg.ShowModal() == wx.ID_OK:
        fns = dlg.GetPaths()
        if fns:
            if isinstance(fns, basestring):
                fns = [fns]
            for fn in fns:
                #out = os.path.extsep.join((fn, DEF_EXT))
                out = byteSwap(fn)#, out, DEF_BYTE)
                if hasattr(Y, 'shellMessage'):
                    Y.shellMessage(out.join(('#', '---done\n')))
                else:
                    print out.join(('#', '---done\n'))
                Y.refresh()
    

if __name__ == '__main__':
    import  optparse, glob
    usage = r""" %prog inputfiles [options]"""
    usage += "\n\toutput filenames will be input%s%s\n\tif no input file supplied, then opens a file dialog" % (os.path.extsep, DEF_EXT)
    p = optparse.OptionParser(usage=usage)
    p.add_option('--byteOrder', '-b', default=DEF_BYTE,
                 help='byte order string (default="%s")' % DEF_BYTE)

    options, arguments = p.parse_args()
    if not arguments:
        from Priithon import PriApp
        PriApp._maybeExecMain()
    else:
        fns = []
        for fn in arguments:
            fns += glob.glob(os.path.expandvars(os.path.expanduser(fn)))
            
        for fn in fns:
            out = byteSwap(fn, **options.__dict__)
            print out, 'saved'
