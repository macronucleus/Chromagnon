#!/usr/bin/env python

"""
Usage:
    python setup.py [py2app/py2exe/sdist/install]

The code was tested with Miniconda verion of python
"""
import os, re, sys, stat
from setuptools import setup
from glob import glob
from shutil import rmtree, copytree

#---------- prepare to build the distribution packages ---------------
if sys.argv[1] in ('py2exe', 'py2app'):
    if sys.argv[1] == 'py2exe':
        suff = 'Win'
    elif sys.argv[1] == 'py2app':
        suff = 'Mac'
    
    import Chromagnon as ch
    version = ch.__version__
    chrodir = os.path.dirname(ch.chromagnon.__file__)
    folder = 'ChromagnonV%s%s' % (version.replace('.', ''), suff)
    
    #---------- remove previous build ---------------

    if os.path.exists(folder):#'dist'):
        # http://stackoverflow.com/questions/4829043/how-to-remove-read-only-attrib-directory-with-python-in-windows
        def on_rm_error( func, path, exc_info):
            # path contains the path of the file that couldn't be removed
            # let's just assume that it's read-only and unlink it.
            os.chmod( path, stat.S_IWRITE )
            os.unlink( path )

        rmtree(folder, onerror=on_rm_error)

    if os.path.exists('build'):
        rmtree('./build')

    #---------- Get file system info -----------------

    # conda
    home = os.path.expanduser('~')
    script = os.path.join('py', 'Chromagnon', 'chromagnon.py')

    if sys.platform == 'darwin':
        mini = 'miniconda'
        mainscript = os.path.join(home, 'codes', script)

    elif sys.platform == 'win32':
        mini = 'Miniconda2'
        mainscript = os.path.join('E:'+os.path.sep, script)

    conda = os.path.join(home, mini)

    #-------- prepare extra libraries -----------
    # java development kit (JDK)
    data_files = []
    if len(sys.argv) > 1 and sys.argv[1].startswith('py2'):
        import javabridge
        jdk = javabridge.locate.find_jdk()
        sysroot = os.path.dirname(jdk) + os.path.sep
        for root, ds, fs in os.walk(jdk):
            root0 = root.replace(sysroot, '').replace('1.8.0_112', '')
            data_files += [(root0, [os.path.join(root, f) for f in fs])]

# ------- options ----------------------


excludes = ['matplotlib', 'pylab', 'PIL', 'Tkinter', 'Tkconstants', 'tcl',  'doctest', 'pydoc', 'pdb', 'email', 'OMXlab', 'OMXlab2', 'tenohira', 'packages']


# ------- Platform ----------------------
# ------- MacOSX options py2app (v0.9)----------------

if sys.platform == 'darwin' and sys.argv[1] == 'py2app':

    packages = ['javabridge', 'bioformats'] # py2app can find most packages without help
    
    libdir = os.path.join(conda, 'lib')

    os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = libdir

    # fftw3 and numpy
    ll = os.listdir(libdir)
    libs = ['libfftw3', 'libmkl_avx', 'libmkl_core', 'libmkl_intel', 'libmkl_mc']
    frameworks = []
    for lib in libs:
        pat = re.compile('%s.*?dylib' % lib)
        for l in ll:
            base = os.path.basename(l)
            if pat.match(base):
                frameworks.append(os.path.join(libdir, l))

    # http://beckism.com/2009/03/pyobjc_tips/
    OPTIONS = {'argv_emulation': False, # to enable ndviewer window
               'site_packages': True,
               'use_pythonpath': True,
               'packages': packages, 
               'excludes': excludes,
               #'resources': data_files, # New Mach-O header is too large...
               'frameworks': frameworks}
    
    extra_options = dict(
         setup_requires=['py2app'],
         app=[mainscript],
         options={'py2app': OPTIONS},
     )

# -------- Windows -----------------------
    ### use `pyinstaller Chromagnon.spec` instead of py2exe
    
elif sys.platform == 'win32' and sys.argv[1] == 'py2exe':
    import py2exe
    ## use absolute import in the python codes

    packages = ['xml', 'lxml', 'OpenGL', 'scipy', 'numpy', 'fftw3']
    # Excluding them will make executable unable to import them...
    #excludes += ['javabridge', 'bioformats', 'cv2'] # even though these are copied as data
    
    data_files += [("Microsoft.VC90.CRT", glob(home+r'\Documents\chrom\Microsoft.VC90.CRT\*.*'))]

    ## Since javabridge lib was not loaded with py2exe
    #  here I used some workaround...
    import javabridge
    jav_dir = os.path.join(conda, 'Lib', 'site-packages', 'javabridge')
    data_files += [("javabridge", glob(os.path.join(jav_dir, '*.py[cd]')))]
    data_files += [("javabridge\\jars", glob(os.path.join(jav_dir, 'jars', '*.*')))]

    import bioformats
    bf_dir = os.path.join(conda, 'Lib', 'site-packages', 'bioformats')
    data_files += [("bioformats", glob(os.path.join(bf_dir, '*.pyc')))]
    data_files += [("bioformats\\jars", glob(os.path.join(bf_dir, 'jars', '*.*')))]

    # cv2 recipe seems to be broken, here is the workaound
    import cv2
    data_files += [('cv2', glob(os.path.join(conda, 'Lib', 'site-packages', 'cv2', '*[cdl]')))]
    
    # copy extra dlls
    # numpy 
    data_files += [('', [os.path.join(conda, 'Library', 'bin', lib) for lib in ('libiomp5md.dll', 'mkl_core.dll')])]
    data_files += [('', glob(os.path.join(conda, 'Library', 'bin', '*mkl*dll')))]
    
    # freeglut
    data_files += [('', [os.path.join(conda, 'Library', 'bin', 'freeglut.dll')])]
    
    # fftw3
    data_files += [('', glob(os.path.join(conda, '*fftw*')))]

        
    OPTIONS = {'packages': packages,
                #'optimize':0, # No optimization possible for javabridge is added as data_files
                # instead call this script as
                # >>> python -OO setup.py py2exe --> pyo did not work for javabridge and others
                #'unbuffered': True,
                'custom_boot_script': os.path.join(os.path.dirname(chrodir), 'PriCommon', 'win_runtime.py'),
                'dist_dir': folder,
               'excludes': excludes,
               'skip_archive': True, # to make javabridge importable
               "dll_excludes": ["MSVCP90.dll", 'api-ms-win-core-string-obsolete-l1-1-0.dll', 'api-ms-win-core-largeinteger-l1-1-0.dll', 'api-ms-win-core-stringansi-l1-1-0.dll', 'api-ms-win-core-privateprofile-l1-1-1.dll', 'api-ms-win-core-rtlsupport-l1-2-0.dll', "api-ms-win-core-libraryloader-l1-2-0.dll", 'api-ms-win-mm-time-l1-1-0.dll', 'api-ms-win-core-debug-l1-1-1.dll', 'api-ms-win-core-sidebyside-l1-1-0.dll', 'api-ms-win-core-kernel32-legacy-l1-1-1.dll', 'api-ms-win-core-timezone-l1-1-0.dll', 'api-ms-win-core-processenvironment-l1-2-0.dll', 'api-ms-win-core-util-l1-1-0.dll', 'api-ms-win-core-atoms-l1-1-0.dll', 'api-ms-win-core-winrt-error-l1-1-1.dll', 'api-ms-win-core-delayload-l1-1-1.dll', 'api-ms-win-core-shlwapi-obsolete-l1-2-0.dll', 'api-ms-win-core-localization-obsolete-l1-3-0.dll', "api-ms-win-core-string-l1-1-0.dll", "api-ms-win-core-libraryloader-l1-2-2.dll", "api-ms-win-core-registry-l1-1-0.dll", "api-ms-win-core-string-l2-1-0.dll", "api-ms-win-core-profile-l1-1-0.dll", "api-ms-win-core-processthreads-l1-1-2.dll", "api-ms-win-core-file-l1-2-1.dll", "api-ms-win-core-heap-l1-2-0.dll","api-ms-win-core-heap-l2-1-0.dll","api-ms-win-core-localization-l1-2-1.dll","api-ms-win-core-sysinfo-l1-2-1.dll","api-ms-win-core-synch-l1-2-0.dll","api-ms-win-core-errorhandling-l1-1-1.dll", "api-ms-win-core-registry-l2-2-0.dll", "api-ms-win-security-base-l1-2-0.dll","api-ms-win-core-handle-l1-1-0.dll","api-ms-win-core-io-l1-1-1.dll","api-ms-win-core-com-l1-1-1.dll","api-ms-win-core-memory-l1-1-2.dll","libzmq.pyd","geos_c.dll","api-ms-win-core-string-l1-1-0.dll","api-ms-win-core-string-l2-1-0.dll","api-ms-win*.dll","api-ms-win-core-libraryloader-l1-2-1.dll","api-ms-win-eventing-provider-l1-1-0.dll","api-ms-win-core-libraryloader-l1-2-2.dll","api-ms-win-core-version-l1-1-1.dll","api-ms-win-core-version-l1-1-0.dll", 'crypt32.dll']}
        # crypt32.dll: Error on XP
        # WindowsError: [Error -2146893795] Provider DLL failed to initialize correctly
        # http://stackoverflow.com/questions/27904936/python-exe-file-crashes-while-launching-on-windows-xp

    extra_options = dict(
         setup_requires=['py2exe'],
         console=[{'script': mainscript, 'dest_base': 'Chromagnon'}],
         #windows=[{'script': mainscript, 'dest_base': 'Chromagnon'}],
         data_files=data_files,
         options={'py2exe': OPTIONS},
              )

# --------------- python setup.py sdist/install ------------------
# Normally unix-like platforms will use "setup.py install"

else:
    try:
        import cv2
    except ImportError:
        raise ImportError, 'Please install opencv-python MANUALLY by yourself before installing Chromagnon'

    # http://stackoverflow.com/questions/2159211/use-distribute-setuptools-to-create-symlink-or-run-script
    from setuptools.command.install import install
    class CustomInstallCommand(install):
        """Customized setuptools install command - prints a friendly greeting."""
        def run(self):
            print "Hello, developer, how are you? :)"
            install.run(self)
            #post-processing code
            if sys.platform == 'linux':
                os.command('ln -s %s/Priithon %s/PriCommon/Priithon')

    mainscript = os.path.join('Chromagnon', 'chromagnon.py')
    #mainscript = '.'.join(('chromagnon', 'main'))
    h = open('Chromagnon/version.py')
    line = h.readline()
    exec(line)
    
    packages = ['Chromagnon', 'Chromagnon.Priithon', 'Chromagnon.Priithon.plt', 'Chromagnon.PriCommon', 'Chromagnon.PriCommon.ndviewer', 'Chromagnon.PriCommon.mybioformats']

    if sys.platform.startswith('linux'):
        extra_options = dict(
            install_requires=['numpy', 'scipy', 'wxpython==3.0', 'pyopengl', 'javabridge', 'lxml', 'python-bioformats'],# 'opencv-python'], # HELPME: opencv is not found by setuptools
            packages=packages,
            #scripts=[mainscript], #--> PriCommon not found from main.py also not pythonw
            entry_points = {
                           'gui_scripts': ['chromagnon=chromagnon:main']},
            # -> pythonw is not used?
            cmdclass={
            'install': CustomInstallCommand}
            )
    else:
        extra_options = dict(
            install_requires=['numpy', 'scipy', 'wxpython==3.0', 'pyopengl', 'javabridge', 'lxml', 'python-bioformats'],# 'opencv-python'], # HELPME: opencv is not found by setuptools
            packages=packages,
            scripts=[mainscript], #--> PriCommon not found from main.py also not pythonw
            #entry_points = {
            #               'gui_scripts': ['chromagnon=%s:main' % mainscript]}
            # -> pythonw is not used?
            cmdclass={
            'install': CustomInstallCommand}
            )

    # ln -s ../Priithon PriCommon/Priithon

# -------- Execute -----------------
setup(
    name="Chromagnon",
    author='Atsushi Matsuda',
    version=version,
    **extra_options
)

if sys.argv[1].startswith('py2app'):
    # rename the dist folder
    os.rename('dist', folder)

# --------- some extra operations for JDK -------------
if sys.platform.startswith('darwin') and sys.argv[1] == 'py2app':
    # ont mac, JDK files are simply copied
    target = os.path.join(folder, 'Chromagnon.app', 'Contents', 'Resources', 'jdk')
    copytree(jdk, target)
    
