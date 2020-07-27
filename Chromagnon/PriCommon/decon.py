#!/usr/bin/env priithon
from __future__ import print_function
import os, sys, tempfile
import six
from Priithon.all import Mrc
from PriCommon import priismCommands, ppro26 as ppro #, byteSwap
import imgio

PRINTOUT=False
EXT_BLT='_blt'
EXT_DCN='_decon'

DECON_OPT=['wiener', 'method', 'ncycl', 'smooth', 'sub']
FFT_OPT=['gauss1', 'gauss2', 'gauss3', 'gauss4', 'butterworth_smooth']

def parallel(fns, out=None, otf=None, limit=ppro.NCPU, **kwds):
    global PRINTOUT
    if isinstance(fns, six.string_types):
        fns = [fns]
        
    if len(fns) == 1 or limit == 1:
        OLD_PRINT=PRINTOUT
        PRINTOUT=True
        out = [main(fn, out, otf, **kwds) for fn in fns]
        PRINTOUT=OLD_PRINT
        return out
    else:
        return ppro.pmap(main, fns, limit, out, otf, **kwds)

def main(fn, out=None, otf=None, **kwds):
    """
    makelog: True or False
    """
    # setup
    priismCommands.PriismSetup()

    # byteSwap for Softworx
    if 'littleEndian' in kwds:
        littleEndian = kwds.pop('littleEndian')
    else:
        littleEndian = False

    #bilateral
    if 'filterMethod' in kwds:
        filterMethod = kwds.pop('filterMethod')
    else:
        filterMethod = None

    makelog = kwds.pop('makelog', None)

    if filterMethod:
        OPTS = [opt for opt in DECON_OPT] # copy
        if not filterMethod.startswith('f'):
            OPTS += FFT_OPT
        
        fkwds = dict([(key, val) for key, val in kwds.items() if key not in OPTS])

        fn = priismCommands.Filter3D(fn, out, filterMethod=filterMethod, **fkwds)
        if littleEndian:
            out = os.path.extsep.join((fn, byteSwap.DEF_EXT))
            #byteSwap.byteSwap(fn, out)
            # replacing byteSwap
            h = imgio.Reader(fn)#mrcIO.MrcReader(fn)
            o = imgio.Writer(out, hdr=h.hdr, byteorder='<')#mrcIO.MrcWriter(out, h.hdr, byteorder='<')
            for t in range(h.nt):
                for w in range(h.w):
                    o.write3DArr(h.get3DArr(t=t, w=w), t=t, w=w)
            o.close()
            h.close()
            
            os.remove(fn)
            fn = out

    # decon filename
    if not out or filterMethod:
        out = fn + EXT_DCN
    log = os.path.extsep.join((out, 'log'))

    # decon otf
    if isinstance(otf, six.string_types) and os.path.exists(otf):
        ctf = otf
    elif isinstance(otf, six.string_types) and otf.isdigit():
        ctf = findOTFfromNum(otf)
    else:
        ctf = findOTF(fn)
    
    # decon
    options = []
    for key, value in kwds.items():
        if key in DECON_OPT:
            if value == True:
                options.append('-%s' % key)
            else:
                options.append('-%s=%s' % (key, value))
    
    #title = 'OTFfile:%s' % shortenStr(ctf)
    #com = ' '.join(['decon %s %s %s -title="%s" ' % (fn, out, ctf, title)] + options)
    com = ' '.join(['decon %s %s %s ' % (fn, out, ctf)] + options)
    if PRINTOUT:
        print(com)

    if makelog:
        if os.path.exists(log):
            os.remove(log)
        com += ' >> %s' % log
        h = open(log, 'a')
        h.write(com)

    if sys.platform == 'darwin':
        out2 = saveCommand(com)

        import subprocess
        err = subprocess.call(['sh', out2])
        os.remove(out2)
    else:
        err = os.system(com)


    if err:
        raise RuntimeError('Deconvolution failed (exit status %s)\ncommand is: %s' % (err, com))

    if makelog:
        h.close()

    if littleEndian:
        fn = out
        out = os.path.extsep.join((fn, byteSwap.DEF_EXT))
        #byteSwap.byteSwap(fn, out)
        h = imgio.Reader(fn)#mrcIO.MrcReader(fn)
        o = imgio.Writer(out, hdr=h.hdr, byteorder='<')#mrcIO.MrcWriter(out, h.hdr, byteorder='<')
        #h = mrcIO.MrcReader(fn)
        #o = mrcIO.MrcWriter(out, h.hdr, byteorder='<')
        for t in range(h.nt):
            for w in range(h.w):
                o.write3DArr(h.get3DArr(t=t, w=w), t=t, w=w)
        o.close()
        h.close()
        
        os.remove(fn)

    if PRINTOUT:
        print('Done %s' % out)
    return out

# for mac, old 32bit does not work anymore...
def saveCommand(com, out=None):
    """
    com: string of command
    return output file
    """
    if not out:
        import tempfile
        out = tempfile.mktemp(suffix='.com', prefix='decon')
    with open(out, 'w') as f:
        f.write('#!/bin/sh\n\n')

        f.write("{ test -r '/Applications/priism-4.2.7/Priism_setup.sh' && . '/Applications/priism-4.2.7/Priism_setup.sh' ; } || exit 1\n\n")
        
        f.writelines(com)

        #os.chmod(out, 100+200+400+10+20+40)
    return out


def shortenStr(word, nChar=70, lead='...'):
    nw = len(word)
    if nw > nChar:
        nl = len(lead)
        pre = int((nChar - nl) / 2.)
        post = nChar - nl - pre
       # print pre, post, nw, nl
        word = join((word[:pre], lead, word[-post:]))
    return word

    
FILTER_METHODS={'b': 'bilateral',
                'w': 'wghtmean',
                'g': 'gaussian',
                'l': 'laplacian',
                'a': 'avgdev',
                'f2': 'FFilter2D',
                'f3': 'FFilter3D',
                'f4': 'FFilter4D'}

def findMethod(method='b'):
    if len(method) <= 2:
        method = FILTER_METHODS.get(method)
    if not method:
        raise ValueError('Filter3D methods not found')
    return method

def Filter3D(fn, out=None, filterMethod='b', kernel='3:3:3', sigma='1:1:1', sigma_inten=5, iterations=1, **kwds):
    """
    return output file
    """
    method = findMethod(filterMethod)

    if not out:
        base, ext = os.path.splitext(fn)
        out = '_'.join((base, method)) #EXT_BLT
    log = os.path.extsep.join((out, 'log'))

    if method in [FILTER_METHODS['f2'], FILTER_METHODS['f3'], FILTER_METHODS['f4']]:
        #-gauss1=0:0.6:5 -gauss2=0:0.1:-4
        options = []
        g = 0
        for key, value in kwds.items():
            if key.startswith('gauss') and value:
                g += 1
                options.append('-%s=%s' % (key, value))
            elif key.startswith('butterworth_smooth') and value:
                options = ['-%s=%s -mode1=float' % (key, value)] # float!!
                g = 0
                break # epistatic!
        options = ' '.join(options)
        title = options
        if g:
            banks = ' -gaussian_bank=%i ' % g
            options = banks + options

        com = "%s %s %s -title='%s' %s" % (method, fn, out, title, options)
    else:
        options = ' -method="%s" -kernel_size=%s -iterations=%i' % (method, kernel, iterations)
        if method in [FILTER_METHODS['g'], FILTER_METHODS['b']]:
            options += ' -sigma=%s -sigma_inten=%i' % (sigma, sigma_inten)
        title = options

        com = "Filter3D %s %s -title='%s' %s" % (fn, out, title, options)

    if os.path.exists(log):
        os.remove(log)
    com += ' >> %s' % log
    err = os.system(com)
    if err:
        raise RuntimeError('Filter3D had exit status %s\ncommand is: %s' % (err, com))
    
    h = open(log, 'a')
    h.write(com)
    h.close()
    
    return out
    

#### CTF parser
EXT=os.path.extsep + 'otf'
SEP='_'
CON='Confocal'

if os.path.exists('/usr/local/softWoRx'):
    CTFDIR=r"/usr/local/otf" #r"/orient1/matsuda/Applications/otf"
elif os.path.exists('/orion1/programs/otf'): #stylonichia
    CTFDIR = r"/orion1/programs/otf"
elif os.path.exists('/Public/images/otf'): #stylonichia
    CTFDIR = r"/Public/images/otf"
elif os.path.exists('/Applications'): # mac
    CTFDIR=r"/Applications/priism-4.2.7/otf" #
    if not os.path.exists(CTFDIR):
        CTFDIR = r"/Applications/priism-4.2.7/CTF/otf"
elif os.path.exists('/opt/otf'): # others
    CTFDIR = r"/opt/otf"
else:
    CTFDIR = '' # 20200424 Error in py2 Win
    #raise ValueError('otf directory not found')
    #CTFDIR=r"/opt/otf"

    
#if sys.platform == 'darwin':
#    CTFDIR = "/Volumes" + CTFDIR

def CTFparser(ctfdir=None):
    """
    return [[LensNum, fn, desc]]
    """
    if not ctfdir:
        ctfdir = CTFDIR

    ctflist = []
    
    fns = os.listdir(ctfdir)


    for fn in fns:
        if fn.endswith(EXT):
            basefn = fn.replace(EXT, '')
            fnlist = basefn.split(SEP)
            if CON in fnlist:
                continue
            ctflist.append([fnlist[3],
                            os.path.join(ctfdir, fn),
                            SEP.join(fnlist[:3] + fnlist[4:])])
    return ctflist

def findOTF(fn, ctfdir=None):
    doesnotwork = """
    tempfn = tempfile.mktemp(suffix='.txt', prefix='lensNum')
    # header does not work on command line! It stops before extended header
    com = os.system("header %s |sed -n -e '/Lens ID Number\.\.*/ s/Lens ID Number\.\.*//p' |awk '{print $1}' >> %s" % (fn, tempfn))
    if com:
        raise RuntimeError, 'problem in reading header %s' % fn

    h = open(tempfn)
    lensNum = h.readline()
    h.close()
    print 'lensNum: ', lensNum"""
    a = Mrc.Mrc2(fn)
    lensNum = str(a.hdr.LensNum)
    a.close()

    return findOTFfromNum(lensNum, ctfdir)

def findOTFfromNum(lensNum, ctfdir=None):
    ctflist = CTFparser(ctfdir)
    ctf = False
    for ctfseq in ctflist:
        if ctfseq[0] == lensNum:
            ctf = ctfseq[1]
    if not ctf:
        ctf = os.path.join(os.environ['IVE_BASE'], 'CTF', 'lens13.realctf')
        if not os.path.exists(ctf):
            raise RuntimeError('CTF not found!')

    return ctf
    
def makeCTFfile(out, ctfdir=None):
    ctflist = CTFparser(ctfdir)

    h = open(out, 'w')
    for ctf in ctflist:
        h.write('# %s\n' % ctf[2])
        h.write('%s\t"%s"\n\n' % (ctf[0], ctf[1]))
    h.close()
    return out
    
####


#  command execution


if __name__ == '__main__':
    import optparse, glob
    usage = r""" %prog inputfiles [options]
    parallel processing as the number of input filenames"""

    # decon method string
    methodList = "jvc(additive=Jansson-Van Cittert algorithm), ratio(Gold's method), shaw(switch to jvc), daa(enhanced ratio=switch to ratio), rl(Richardson-Lucy)"

    # filter method string
    methodsStr = []
    keys = list(FILTER_METHODS.keys())
    keys.sort()
    for key in keys:
        methodsStr.append(':'.join((key, FILTER_METHODS[key])))
    methodsStr = '\n' + '\n'.join(methodsStr)

    # create options
    p = optparse.OptionParser(usage=usage)
    p.add_option('--out', '-O', default=None,
                 help='output file name for filtered decon if input file is a single file (default=auto)')
    p.add_option('--otf', '-o', default=None,
                 help='[DECON] OTF file or lens ID (default=from the lens ID)')
    # decon options
    p.add_option('--wiener', '-w', type=float, default=0.9,
                 help='[DECON] wiener value (default=0.9)')
    p.add_option('--method', '-m', default='daa',
                 help='[DECON] %s (default=daa)' % methodList)
    p.add_option('--ncycl', '-n', default=15,
                 help='[DECON] number of cycle (default=15)')
    p.add_option('--smooth', '-s', default=0.05,
                 help='[DECON] smooth (0-1) (default=0.05)')
    p.add_option('--sub', '-b', default='0:0:0:0:0',
                 help='[DECON] background subtraction wave0:wave1.. (default=0 for all wavelength)')

    # filter options
    p.add_option('--filterMethod', '-f', default=None,
                 help='[PREFILTER] filter method:%s (default=nothing)' % methodsStr)
    p.add_option('--kernel', '-k', default='3:3:3',
                 help='[PREFILTER_SPACE] kernel size (default=3:3:3)')
    p.add_option('--iterations', '-i', type=int, default=1,
                 help='[PREFILTER_SPACE] number of iterations (default=1)')
    p.add_option('--sigma', '-S', default='1:1:1',
                 help='[PREFILTER_SPACE] sigma for Gaussian filter (default=1:1:1)')
    p.add_option('--sigma_inten', '-j', type=int, default=5,
                 help='[PREFILTER_SPACE] sigma intensity for Gaussian filter (default=5)')
    p.add_option('--butterworth_smooth', '-t', default='2:0.5',
                 help='[PREFILTER_FOURIER] butterworth filter -- central_freq(fraq_Nyquist):sigma(fraq_Nyquist):Amplitude (default=None)')
    p.add_option('--gauss1', '-1', default='0:0.3:1',
                 help='[PREFILTER_FOURIER] 1st Gauss -- central_freq(fraq_Nyquist):sigma(fraq_Nyquist):Amplitude (default=0:0.3:1)')
    p.add_option('--gauss2', '-2', default=None,
                 help='[PREFILTER_FOURIER] 2nd Gauss -- central_freq(fraq_Nyquist):sigma(fraq_Nyquist):Amplitude (default=None)')
    p.add_option('--gauss3', '-3', default=None,
                 help='[PREFILTER_FOURIER] 3rd Gauss -- central_freq(fraq_Nyquist):sigma(fraq_Nyquist):Amplitude (default=None)')
    p.add_option('--gauss4', '-4', default=None,
                 help='[PREFILTER_FOURIER] 4th Gauss -- central_freq(fraq_Nyquist):sigma(fraq_Nyquist):Amplitude (default=None)')

    # SoftWorx
    p.add_option('--littleEndian', '-l', action='store_true', default=False,
                 help='SoftWorx byteorder (default=native byteorder)')
    # parallel
    p.add_option('--limit', '-L', default=ppro.NCPU,#12,
                 help='number of CPU core (default=%i)' % ppro.NCPU)

    options, arguments = p.parse_args()
    if not arguments:
        raise ValueError('please supply image file')

    PRINTOUT=True
    fns = []
    for fn in arguments:
        fns += glob.glob(os.path.expandvars(os.path.expanduser(fn)))
    print(fns)
    out = parallel(fns, **options.__dict__)

    print(out, 'saved')
