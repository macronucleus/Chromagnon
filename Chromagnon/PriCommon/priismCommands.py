#!/usr/bin/python
import os, sys

PRII='priism-4.2.7'

PRI_DIR=os.path.expanduser('~')
if sys.platform == 'darwin':
    if os.path.exists('/Applications/%s' % PRII):
        PRI_DIR='/Applications'
    elif os.path.exists(os.path.expanduser('~/%s' % PRII)):
        PRI_DIR=os.path.expanduser('~')
elif sys.platform.startswith('linux'):
    if os.path.exists('/usr/local/%s' % PRII):
        PRI_DIR='/usr/local'
    elif os.path.exists('/opt/%s' % PRII):
        PRI_DIR='opt'

EXT_POL='pol'

def PriismSetup():
    """
    this is not working!!
    """
    setup = priismPath()
    if 'IVE_EXE' not in os.environ:
        
        if os.path.exists(setup):
            com = '. %s' % setup
            print com
            err = os.system(com)
            if err:
                raise RuntimeError, 'Priism setup failed, exit status %s' % err
    else:
        pass
        #print 'Priism already set up'

def priismPath():
    setup = os.path.join(' ', PRI_DIR, PRII, 'Priism_setup.sh')
    setup = setup.replace(' ', '')
    return setup

def objFinder(infile, polfile=None, border=1, spacing=4, minpts=100, outerOnly=True,**kwds):
    """
    infile: binary file

    kwds: x=start:end, y, z, w, t
    """
    PriismSetup()

    if not polfile:
        polfile = os.path.extsep.join((infile, EXT_POL))

    # make command string
    excStr = '2DObjFinder %s -poly=%s -border=%i -spacing=%i -minpts=%i ' % (infile, polfile, border, spacing, minpts)
    if outerOnly:
        excStr += '-outer_only '

    for key, value in kwds.iteritems():
        excStr += '-%s=%s '% (key, value)

    # execute command
    status = os.system(excStr)
    if status:
        raise RuntimeError, '2DObjectFinder, exit status %i, check if the input image is binary or maybe you are running without X?\ncommad: %s' % (status, excStr)
    #print excStr
    return polfile

## Filter3D
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
        raise ValueError, 'Filter3D methods not found'
    return method

def Filter3D(fn, out=None, filterMethod='b', kernel='3:3:3', sigma='1:1:1', sigma_inten=5, iterations=1, **kwds):
    """
    kwds for methods f2-4: {'butterworth_smooth': '2:0.5'} for butterworth
          {'gauss1': '0:0.6:5', 'gauss2': '0:0.1:-4'} for gaussians
    kwds for region: {'zyxslc': slices, 'tslc': slice(), 'ws': []}
    return output file
    """
    method = findMethod(filterMethod)

    if not out:
        #base, ext = os.path.splitext(fn)
        out = '_'.join((fn, method)) #EXT_BLT
    log = os.path.extsep.join((out, 'log'))

    if method in [FILTER_METHODS['f2'], FILTER_METHODS['f3'], FILTER_METHODS['f4']]:
        #-gauss1=0:0.6:5 -gauss2=0:0.1:-4
        options = _generalOptions(**kwds)
        g = 0
        for key, value in kwds.iteritems():
            if key.startswith('gauss') and value:
                g += 1
        if g:
            banks = ' -gaussian_bank=%i ' % g
            options = banks + options
        title = options

        com = "%s %s %s -title='%s' %s" % (method, fn, out, title, options)

    else:
        options = ' -method="%s" -kernel_size=%s -iterations=%i' % (method, kernel, iterations)
        if method in [FILTER_METHODS['g'], FILTER_METHODS['b']]:
            options += ' -sigma=%s' % sigma
        if method in [FILTER_METHODS['b']]:
            options += ' -sigma_inten=%i' % sigma_inten
        title = options

        options += _generalOptions(**kwds)
        com = "Filter3D %s %s -title='%s' %s" % (fn, out, title, options)

    _execCom(com, log)
    
    return out

TRUNPROJ_METHODS=['sum', 'average', 'max']
def Proj(fn, out=None, along='z', step=3, group=3, method=TRUNPROJ_METHODS[1], *args, **kwds):
    if not out:
        out = fn + '_%sproj_g%is%i' % (along, group, step)

    program = 'RunProj'
    if along == 't':
        program = 'T-' + program
    options = '-%s_group=%i -%s_step=%i -%s_%s' % (along, group, along, step, method, along)
    options += _generalOptions(*args, **kwds)
    com = '%s %s %s %s' % (program, fn, out, options)

    _execCom(com)
    
    return out
    
def CopyRegion(fn, out=None, *args, **kwds):
    if not out:
        out = fn + '_cp'

    program = 'CopyRegion'

    options = _generalOptions(*args, **kwds)

    com = '%s %s %s %s' % (program, fn, out, options)

    #print com
    _execCom(com)

    return out

def _execCom(com, log=None):
    if log:
        if os.path.exists(log):
            os.remove(log)
            com += ' >> %s' % log

    err = os.system(com)
    #print com
    if err:
        program = com.split()[0]
        raise RuntimeError, '%s had exit status %s\ncommand is: %s' % (program, err, com)

    if log:
        h = open(log, 'a')
        h.write(com)
        h.close()

def _generalOptions(zyxslc=None, tslc=None, ws=[], *args, **kwds):
    """
    ws: ex [1,3]
    """
    dims = ['x', 'y', 'z']
    slcs = []
    if zyxslc:
        i = 0
        for slc in zyxslc[::-1]:
            if type(slc) is slice:
                slcs += [(dims[i], slc)]
                i += 1
    if tslc:
        slcs = [('t', tslc)] + slcs

    options = ''
    for d, slc in slcs:
        if slc.start is not None:
            if slc.step is not None:
                options += ' -%s=%i:%i:%i' % (d, slc.start, slc.stop-1, slc.step)
            else:
                options += ' -%s=%i:%i' % (d, slc.start, slc.stop-1)
        else:
            options += ' -%s=0:%i' % (d, slc.stop-1)
    
    if ws:
        options += ' -w='+ ':'.join([str(w) for w in ws])

    for key, value in kwds.iteritems():
        options += ' -%s=%s' % (key, value)

    return options

# main
if __name__ == '__main__':
    PriismSetup()
