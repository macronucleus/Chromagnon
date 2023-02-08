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

# pyinstaller should be installed from pip 

import sys, os
pyversion = sys.version_info.major

PLUGIN= '' #vcat5'
if PLUGIN == '':
    console=False
    ex_suffix = ''
    module='chromagnon.py'
elif PLUGIN:
    console=True
    ex_suffix = '_%s' % PLUGIN
    module='%s_chromagnon.py' % PLUGIN


block_cipher = None

# ------ platform dependence ---
conda = os.getenv('CONDA_PREFIX')
binaries = []
home=os.path.expanduser('~')
name = 'Chromagnon'

# win
if sys.platform.startswith('win'):
    if not conda:
        conda = os.path.join(home, 'Miniconda%i' % pyversion)
    
    site=os.path.join(conda, 'Lib', 'site-packages')
    libbin = os.path.join(conda, 'Library', 'bin')

    code=os.path.abspath(os.path.join('Z:', 'py'))
    src = os.path.abspath(os.path.join('Z:', 'src', 'Chromagnon', 'Chromagnon'))


    binaries = [(os.path.join(libbin, 'mkl_avx.dll'), '.'), (os.path.join(libbin, 'mkl_avx2.dll'), '.')]
    if not PLUGIN:
        if pyversion == 3:
            glut = 'glut64.dll'
        elif pyversion == 2:
            glut = os.path.join(libbin, 'freeglut.dll')
        binaries += [(os.path.join(home, conda, glut), '.')]
    pylib = 'pyd'
    jvm = 'jvm.dll'
    suffix = 'Win' + ex_suffix
    
else: # mac + linux
    code=os.path.join(home, 'codes', 'py')
    src = os.path.join(home, 'codes', 'src', 'Chromagnon', 'Chromagnon')

    site=os.path.join(conda, 'lib', 'python%i.%i' % (pyversion, sys.version_info.minor), 'site-packages')
    print('site is', site)

    pylib = 'so'
    # mac
    if sys.platform == 'darwin':
        suffix = 'Mac' + ex_suffix
        jvm = 'libjvm.dylib'
    # linux
    else:
        suffix = ''
        #import platform
        #dist = platform.dist()[0] # newer platform does not have dist attribute
        ldpath = os.getenv('LD_LIBRARY_PATH', '').split(':')

        pylibpath = os.path.join(conda, 'lib')
        if pylibpath not in ldpath:
            os.environ['LD_LIBRARY_PATH'] = ':'.join((os.getenv('LD_LIBRARY_PATH', ''), pylibpath))

        jvm = 'libjvm.so'
        name = name.lower()


prog = os.path.abspath(os.path.join(src, 'Chromagnon', module))
#DISTPATH=os.path.relpath(os.path.join(src, 'dist')) # not working??
        
# ------ chromagnon version
if sys.platform.startswith(('win', 'darwin')):
    with open(os.path.join(code, 'Chromagnon', 'version.py')) as h:
        line = next(h)
        cversion = line.split()[-1][1:-1].replace('.', '')
else:
    cversion = ''
# ------- pyinstaller

datas = [(os.path.join(code, 'Priithon', '*.py'), 'Priithon'), (os.path.join(code, 'Priithon', 'plt', '*.py'), os.path.join('Priithon', 'plt')), (os.path.join(code, 'PriCommon', '*.py'), 'PriCommon'), (os.path.join(code, 'common', '*.py'), 'common'), (os.path.join(site, 'tifffile', '*.%s' % pylib), 'tifffile')]
if 0:#sys.platform.startswith('linux'):
    datas += [(os.path.join(pylibpath, 'libglut.*'), 'lib')]
    
if not PLUGIN:
    #datas += [(os.path.join(site, 'javabridge', '*.%s' % pylib), 'javabridge'), (os.path.join(site, 'javabridge', 'jars', '*'), os.path.join('javabridge', 'jars')), (os.path.join(site, 'bioformats', 'jars', '*'), os.path.join('bioformats', 'jars'))]
    datas += [(os.path.join(site, 'javabridge', 'jars', '*'), os.path.join('javabridge', 'jars')), (os.path.join(site, 'bioformats', 'jars', '*'), os.path.join('bioformats', 'jars'))]#, (os.path.join(os.path.dirname(site), 'lib-dynload', '_posixsubprocess.cpython-37m-x86_64-linux-gnu.so'), os.path.join('lib', 'python3.7', 'lib-dynload'))]
    
a = Analysis([prog],
             pathex=[code],
             binaries=binaries,
             datas=datas,
             hiddenimports=['six', 'packaging', 'packaging.version', 'packaging.specifiers', 'packaging.requirements', 'appdirs', 'scipy.spatial.transform._rotation_groups'],#, '_posixsubprocess', 'subprocess', 'multiprocessing'],
             

             hookspath=[],
             runtime_hooks=[],
             excludes=['pylab', 'Tkinter', 'matplotlib', 'pdb', 'pyqt5', 'pyqtgraph', 'pytz', 'opencv', 'reikna', 'pycuda', 'skcuda', 'wx.py', 'distutils', 'setuptools'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher,)

exe = EXE(pyz,
          a.scripts,
          a.binaries - TOC([(jvm, None, None)]),
          a.zipfiles,
          a.datas,
          name='%s%s%s' % (name, cversion, suffix),
          debug=False,
          strip=False,
          upx=False, #True,
          runtime_tmpdir=None,
          console=console)#False)



if sys.platform.startswith('darwin'):
    app = BUNDLE(exe,
                 name='Chromagnon%s%s.app' % (cversion, suffix),
                 icon=None,
                 bundle_identifier=None,
                 info_plist={'CFBundleShortVersionString': '.'.join((cversion[0], cversion[1:])),
                            'NSHighResolutionCapable': 'True'})


# 20180412
# File "stringsource", line 103, in init scipy.optimize._trlib._trlib
#AttributeError: type object 'scipy.optimize._trlib._trlib.array' has no attribute '__reduce_cython__'
# copied Library\mingw-w64\bin\liblzma-5.dll to Library\bin -> no change
# same for python 2.7 and 3.5
# according to https://github.com/pyinstaller/pyinstaller/issues/2987
# this occurs with scipy >= 1.0.0, so scipy was downgraded to 0.19, and it worked

# according to https://github.com/pyinstaller/pyinstaller/issues/2987
# add 'scipy._lib.messagestream' to hiddenimports
# and add option `--paths C:/Users/sc/AppData/Local/Programs/Python/Python36/Lib/site-packages/scipy/extra-dll`
# scipy >= 1.0 works, but increases sile size a lot... (112Mb -> 347Mb)
    
# 20180413
# Javabridge from PIP results in opening and closing of command prompt many times during the program is running, installing the conda-version of Javabridge solved the problem
