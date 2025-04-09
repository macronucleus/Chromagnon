# -*- mode: python -*-

# install
# conda install appdirs packaging

# linux used envs

# execute like...
# $ cd ~/chrom/Chromagnon
# $ source activate chrom
# $ pyinstaller --clean ~/codes/py/Chromagnon/Chromagnon.spec
# on mac and linux use packChromagnon.sh

# on mac, make disk image
# on linux (centOS use arcadia not omx)
# tar -jcvf ChromagnonV065Ubuntu.tar.bz2 ChromagnonV065Ubuntu
# on windows
# pyinstaller --clean Z:\py\Chromagnon\Chromagnon.spec
# if applicable... --upx-dir=upx394w

# 20240928 OnMacM2
# $ mamba install libsqlite --force-reinstall
# Error with pydantic
# $pip install -U pyinstaller-hooks-contrib

# pyinstaller should be installed from pip 

import sys, os
pyversion = sys.version_info.major

console=False
ex_suffix = ''
module='chromagnon.py'

debug = False
block_cipher = None

# ------ platform dependence ---
conda = os.getenv('CONDA_PREFIX')
binaries = []
home=os.path.expanduser('~')
name = 'Chromagnon'


        


# ------ platform dependence ---
# win
if sys.platform.startswith('win'):
    if not conda:
        conda = os.path.join(home, 'Miniconda%i' % pyversion)
    
    site=os.path.join(conda, 'Lib', 'site-packages')
    libbin = os.path.join(conda, 'Library', 'bin')

    code=os.path.abspath(os.path.join('Z:', 'py'))
    src = os.path.abspath(os.path.join('Z:', 'src', 'Chromagnon', 'Chromagnon'))

    suffix = 'Win' + ex_suffix
else: # mac + linux
    if os.path.isdir(os.path.expanduser('~/codes')):
        CODE='codes'
    elif os.path.isdir(os.path.expanduser('~/local')):
        CODE='local'
    else:
        raise ValueError('directory for codes not found')
    
    code=os.path.join(home, CODE, 'py')
    src = os.path.join(home, CODE, 'src', 'Chromagnon', 'Chromagnon')

    # mac
    if sys.platform == 'darwin':
        suffix = 'Mac' + ex_suffix
        #jvm = 'libjvm.dylib'
        pylibpath = os.path.join(conda, 'lib')
    # linux
    else:
        suffix = ''
    
# ------ chromagnon version
if sys.platform.startswith(('win', 'darwin')):
    with open(os.path.join(code, 'Chromagnon', 'version.py')) as h:
        line = next(h)
        cversion = line.split()[-1][1:-1].replace('.', '')
else:
    cversion = ''
prog = os.path.abspath(os.path.join(src, 'Chromagnon', module))

    
# ------- pyinstaller

# execution
a = Analysis([prog],
             pathex=[code],
             hiddenimports=['scipy._lib.array_api_compat.numpy.fft', 'scipy.special._special_ufuncs'])

pyz = PYZ(a.pure)

if debug:
    exe = EXE(pyz, a.scripts, exclude_binaries=True)
    coll = COLLECT(exe, a.binaries, a.datas)
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, console=False, name='%s%s%s' % (name, cversion, suffix))#'Chromagnon')#, target_arch='universal2')
    ## universal does not work for scipy
    # PyInstaller.utils.osx.IncompatibleBinaryArchError: /Users/matsuda/miniconda3/envs/chrom2/lib/python3.12/lib-dynload/_struct.cpython-312-darwin.so is not a fat binary!
    if sys.platform.startswith('darwin'):
        app = BUNDLE(exe,
                    name='%s%s%s.app' % (name, cversion, suffix),
                   # icon=None,
                   # bundle_identifier=None,
                    info_plist={'CFBundleShortVersionString': '.'.join((cversion[0], cversion[1:])),
                                'NSHighResolutionCapable': 'True'})
    


