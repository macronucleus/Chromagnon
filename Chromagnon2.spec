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
    #src = os.path.abspath(os.path.join('Z:', 'src', 'Chromagnon', 'Chromagnon'))


    suffix = 'Win' + ex_suffix
else: # mac + linux
    if os.path.isdir(os.path.expanduser('~/codes')):
        CODE='codes'
    elif os.path.isdir(os.path.expanduser('~/local')):
        CODE='local'
    else:
        raise ValueError('directory for codes not found')
    
    code=os.path.join(home, CODE, 'py')
    #src = os.path.join(home, CODE, 'src', 'Chromagnon', 'Chromagnon')
    
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
#prog = os.path.abspath(os.path.join(src, 'Chromagnon', module))
prog = os.path.abspath(os.path.join(code, 'Chromagnon', module))

    
# ------- pyinstaller

# java files for the pip version (also for old mac)
pip = True #
if pip:
    try:
        import javabridge,  bioformats
        os.environ['JDK_HOME'] = os.environ['JAVA_HOME']
        jv = os.path.dirname(javabridge.__file__)
        bf = os.path.dirname(os.path.dirname(bioformats.__file__))
        datas = [(os.path.join(jv, 'jars', '*'), os.path.join('javabridge', 'jars')), (os.path.join(bf, 'bioformats', 'jars', '*'), os.path.join('bioformats', 'jars'))]
        console=True
        
    except ImportError:
        console = False
        datas = []
        #pass
else:
    console = False
    datas = []
    


# execution
a = Analysis([prog],
             pathex=[code],
             datas = datas,
            # runtime_hooks = rtm,
            # hiddenimports=['numpy', 'numpy.core._multiarray_umath', 'scipy._lib.array_api_compat.numpy.fft', 'scipy.special._special_ufuncs'],
            excludes=['pylab', 'Tkinter', 'matplotlib', 'pdb', 'pyqt5', 'pyqtgraph', 'pytz', 'openjdk'])

if True:
    # Avoid warning
    # https://stackoverflow.com/questions/66069360/pyinstaller-onefile-warning-file-already-exists-but-should-not

    if sys.platform.startswith('win'):
        to_remove = ["_AES", "_ARC4", "_DES", "_DES3", "_SHA256", "_counter"]
        dname = f'%s.cp37-win_amd64.pyd'
    elif sys.platform == 'darwin':
        to_remove = ["_asyncio", "_bisect", "_blake2", "_bz2", "_codecs_cn", "_codecs_hk", "_codecs_iso2022", u'_codecs_iso2022', u'_codecs_jp', u'_codecs_kr', u'_codecs_tw', u'_contextvars', u'_csv', u'_ctypes', u'_datetime', u'_decimal', u'_elementtree', u'_hashlib', u'_heapq', u'_json', u'_lzma', u'_md5', u'_multibytecodec', u'_multiprocessing', u'_opcode', u'_pickle', u'_posixshmem', u'_posixsubprocess', u'_queue', u'_random', u'_scproxy', u'_sha1', u'_sha256', u'_sha3', u'_sha512', u'_socket', u'_ssl', u'_statistics', u'_struct', u'_tkinter', u'_uuid', u'array', u'binascii', u'fcntl', u'grp', u'math', u'mmap', u'pyexpat', u'readline', u'resource', u'select', u'syslog', u'termios', u'unicodedata', u'zlib']

        dname = f'%s.cpython-310-darwin.so'
        
    for b in a.binaries:
        found = any(
            dname % crypto in b[1]
            for crypto in to_remove
        )
        if found and not ('numpy' in b[1]):
            print(f"Removing {b[1]}")
            a.binaries.remove(b)

pyz = PYZ(a.pure)

if debug:
    exe = EXE(pyz, a.scripts, exclude_binaries=True)
    coll = COLLECT(exe, a.binaries, a.datas)
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, console=console, name='%s%s%s' % (name, cversion, suffix))#'Chromagnon')#, target_arch='universal2')
    ## universal does not work for scipy
    # PyInstaller.utils.osx.IncompatibleBinaryArchError: /Users/matsuda/miniconda3/envs/chrom2/lib/python3.12/lib-dynload/_struct.cpython-312-darwin.so is not a fat binary!
    if sys.platform.startswith('darwin'):
        app = BUNDLE(exe,
                    name='%s%s%s.app' % (name, cversion, suffix),
                   # icon=None,
                   # bundle_identifier=None,
                    info_plist={'CFBundleShortVersionString': '.'.join((cversion[0], cversion[1:])),
                                'NSHighResolutionCapable': 'True'})
    


