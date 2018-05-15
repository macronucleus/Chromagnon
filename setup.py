#!/usr/bin/env python

"""
Usage:
    python setup.py [py2app/py2exe/sdist/install]
on Mac 20180202:
    modify python3.6.sysconfig._get_sysconfigdata_name(check_exists=None)
    ln -s /Users/USER/miniconda3/lib/libpython3.6m.dylib libpython3.6.dylib
    then pythonw setup.py py2app to import javabridge

    install numpy with nomkl like this
    conda nomkl numpy scipy
    see https://github.com/pyinstaller/pyinstaller/issues/2175

The code was tested with Miniconda verion of python
"""
import os, re, sys, stat
from setuptools import setup
from glob import glob
from shutil import rmtree, copytree

pyversion = sys.version_info.major

#---------- prepare to build the distribution packages ---------------
if sys.argv[1] in ('py2exe', 'py2app'):
    if sys.argv[1] == 'py2exe':
        suff = 'Win'
    elif sys.argv[1] == 'py2app':
        suff = 'Mac'

    try:
        from Chromagnon import version as chv
    except ImportError:
        import version as chv
    version = chv.version
    chrodir = os.path.dirname(chv.__file__)
    folder = 'ChromagnonV%s%s' % (version.replace('.', ''), suff)
    
    #---------- remove previous build ---------------

    if os.path.exists(folder):
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
        mini = 'miniconda%i' % pyversion
        mainscript = os.path.join(home, 'codes', script)

    elif sys.platform == 'win32':
        mini = 'Miniconda%i' % pyversion
        mainscript = os.path.join('F:'+os.path.sep, script)

    conda = os.path.join(home, mini)

    #-------- prepare extra libraries -----------
    # java development kit (JDK) -- > let users to install
    data_files = []
    if 0:#len(sys.argv) > 1 and sys.argv[1].startswith('py2'):
        import javabridge
        jdk = javabridge.locate.find_jdk()
        sysroot = os.path.dirname(jdk) + os.path.sep
        for root, ds, fs in os.walk(jdk):
            root0 = root.replace(sysroot, '').replace('1.8.0_112', '')
            data_files += [(root0, [os.path.join(root, f) for f in fs])]

# ------- options ----------------------


excludes = ['matplotlib', 'pylab', 'Tkinter', 'Tkconstants', 'tcl',  'doctest', 'pydoc', 'pdb', 'pyqt5', 'pyqtgraph', 'pytz', 'opencv', 'reikna', 'pycuda', 'skcuda', 'wx.py', 'distutils', 'setuptools'] # email is required for bioformats


# ------- Platform ----------------------
# ------- MacOSX options py2app (v0.9)----------------

if sys.platform == 'darwin' and sys.argv[1] == 'py2app':

    packages = ['tifffile', 'javabridge', 'bioformats', 'html'] # py2app cannot find some packages without help, html is for bioformats
    
    libdir = os.path.join(conda, 'lib')

    os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = libdir

    # fftw3 and numpy
    ll = os.listdir(libdir)
    libs = []#'libmkl_avx', 'libmkl_core', 'libmkl_intel', 'libmkl_mc', 'libfftw3', 'libwx', 'libiconv']
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
               #'plist': {'PyRuntimeLocations': ['@executable_path/../Frameworks/libpython3.4m.dylib', '/home/micronucleus/miniconda3/lib/libpython3.4m.dylib']}}
    
    extra_options = dict(
         setup_requires=['py2app'],
         app=[mainscript],
         options={'py2app': OPTIONS},
     )

# -------- Windows -----------------------
    ### verion <= V0.5; use `pyinstaller Chromagnon.spec` instead of py2exe
    ### verion >= V0.6; use this script with python2.7 miniconda
    # copy Chromagnon, Priithon, PriCommon, ndviewer, imgio to site-package
    # also copy all api-ms-win-*.dll in Miniconda3 to Miniconda2

    ## version >=V0.6
    # with python3.5, "ValueError: attempted relative import beyond top-level package" no matter what I tried
    # with pyinstaller, AttributeError: scipy.optimize __reduce_cython__ with python2.7 and 3.5, even though Cython was installed.
    
elif sys.platform == 'win32' and sys.argv[1] == 'py2exe':
    import py2exe
    ## use absolute import in the python codes

    packages = ['xml', 'lxml', 'OpenGL', 'scipy', 'numpy']
    # Excluding below will make executable unable to import them...
    #excludes += ['javabridge', 'bioformats'] # even though these are copied as data
    
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

    # copy extra dlls
    # numpy 
    data_files += [('', [os.path.join(conda, 'Library', 'bin', lib) for lib in ('libiomp5md.dll', 'mkl_core.dll')])]
    data_files += [('', glob(os.path.join(conda, 'Library', 'bin', '*mkl*dll')))]
    
    # freeglut
    if pyversion == 2:
        data_files += [('', [os.path.join(conda, 'Library', 'bin', 'freeglut.dll')])]
    elif pyversion == 3:
        data_files += [('', [os.path.join(conda, 'glut64.dll')])]

    # tifffile
    data_files += [('tifffile', [os.path.join(conda, 'Lib', 'site-packages', 'tifffile', '_tifffile.pyd')])]

    # priithon (in some reason, Priithon and most of PriCommon are not included...)
    data_files += [('Priithon', glob(os.path.join(conda, 'Lib', 'site-packages', 'Priithon', '*.pyc')))]
    data_files += [('Priithon\\plt', glob(os.path.join(conda, 'Lib', 'site-packages', 'Priithon', 'plt', '*.pyc')))]
    data_files += [('PriCommon', glob(os.path.join(conda, 'Lib', 'site-packages', 'PriCommon', '*.pyc')))]

    # copied Library\mingw-w64\bin\liblzma-5.dll to Library\bin
        
    OPTIONS = {'packages': packages,
                #'optimize':0, # No optimization possible for javabridge is added as data_files
                # instead call this script as
                # >>> python -OO setup.py py2exe --> pyo did not work for javabridge and others
                #'unbuffered': True,
                #'custom_boot_script': os.path.join(os.path.dirname(chrodir), 'PriCommon', 'win_runtime.py'),
                'dist_dir': folder,
               'excludes': excludes,
               #'skip_archive': True, # to make javabridge importable
               #'bundle_files': 1, not supported on win64
               'compressed': True,
               "dll_excludes": ["MSVCP90.dll",
                                    'api-ms-win-core-string-obsolete-l1-1-0.dll', 'api-ms-win-core-largeinteger-l1-1-0.dll', 'api-ms-win-core-stringansi-l1-1-0.dll', 'api-ms-win-core-privateprofile-l1-1-1.dll', 'api-ms-win-core-rtlsupport-l1-2-0.dll', "api-ms-win-core-libraryloader-l1-2-0.dll", 'api-ms-win-mm-time-l1-1-0.dll', 'api-ms-win-core-debug-l1-1-1.dll', 'api-ms-win-core-sidebyside-l1-1-0.dll', 'api-ms-win-core-kernel32-legacy-l1-1-0.dll', 'api-ms-win-core-kernel32-legacy-l1-1-1.dll', 'api-ms-win-core-timezone-l1-1-0.dll', 'api-ms-win-core-processenvironment-l1-2-0.dll', 'api-ms-win-core-atoms-l1-1-0.dll', 'api-ms-win-core-winrt-error-l1-1-0.dll', 'api-ms-win-core-winrt-error-l1-1-1.dll', 'api-ms-win-core-delayload-l1-1-0.dll', 'api-ms-win-core-delayload-l1-1-1.dll', 'api-ms-win-core-shlwapi-obsolete-l1-1-0.dll', 'api-ms-win-core-shlwapi-obsolete-l1-2-0.dll', 'api-ms-win-core-localization-obsolete-l1-2-0.dll', 'api-ms-win-core-localization-obsolete-l1-3-0.dll', "api-ms-win-core-registry-l1-1-0.dll", "api-ms-win-core-string-l2-1-0.dll", "api-ms-win-core-processthreads-l1-1-2.dll",  "api-ms-win-core-file-l1-2-1.dll", "api-ms-win-core-heap-l1-2-0.dll","api-ms-win-core-heap-l2-1-0.dll", "api-ms-win-core-localization-l1-2-1.dll","api-ms-win-core-sysinfo-l1-2-1.dll","api-ms-win-core-errorhandling-l1-1-1.dll", "api-ms-win-core-registry-l2-2-0.dll", "api-ms-win-security-base-l1-2-0.dll","api-ms-win-security-base-l1-1-0.dll", "api-ms-win-core-io-l1-1-1.dll","api-ms-win-core-com-l1-1-1.dll","api-ms-win-core-memory-l1-1-2.dll","libzmq.pyd","geos_c.dll", "api-ms-win-core-string-l2-1-0.dll","api-ms-win*.dll","api-ms-win-core-libraryloader-l1-2-1.dll","api-ms-win-eventing-provider-l1-1-0.dll","api-ms-win-core-libraryloader-l1-2-2.dll","api-ms-win-core-version-l1-1-1.dll","api-ms-win-core-version-l1-1-0.dll", 'crypt32.dll']}
        # provided by Miniconda3
        # 'api-ms-win-core-debug-l1-1-0.dll',
        # "api-ms-win-core-errorhandling-l1-1-0.dll",
        # "api-ms-win-core-file-l1-1-0.dll",
        # "api-ms-win-core-handle-l1-1-0.dll",
        # "api-ms-win-core-heap-l1-1-0.dll",
        # "api-ms-win-core-localization-l1-2-0.dll",
        # "api-ms-win-core-memory-l1-1-0.dll",
        # 'api-ms-win-core-processenvironment-l1-1-0.dll',
        # "api-ms-win-core-processthreads-l1-1-0.dll", "api-ms-win-core-processthreads-l1-1-1.dll",
        # "api-ms-win-core-profile-l1-1-0.dll",
        # 'api-ms-win-core-rtlsupport-l1-1-0.dll',
        #  "api-ms-win-core-string-l1-1-0.dll",
        # "api-ms-win-core-synch-l1-1-0.dll","api-ms-win-core-synch-l1-2-0.dll",
        # 'api-ms-win-core-timezone-l1-1-0.dll',
        # 'api-ms-win-core-util-l1-1-0.dll',
        
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
    # http://stackoverflow.com/questions/2159211/use-distribute-setuptools-to-create-symlink-or-run-script
    from setuptools.command.install import install
    class CustomInstallCommand(install):
        """Customized setuptools install command."""
        def run(self):
            install.run(self)
            #post-processing code
            #if sys.platform == 'linux':
            #    os.command('ln -s %s/Priithon %s/PriCommon/Priithon')

    mainscript = os.path.join('Chromagnon', 'chromagnon.py')
    #mainscript = '.'.join(('chromagnon', 'main'))
    h = open('Chromagnon/version.py')
    line = h.readline()
    exec(line)
    
    packages = ['Chromagnon', 'Chromagnon.Priithon', 'Chromagnon.Priithon.plt', 'Chromagnon.PriCommon', 'Chromagnon.ndviewer', 'Chromagnon.imgio', 'Chromagnon.imgio.mybioformats']

    if sys.platform.startswith('linux'):
        extra_options = dict(
            install_requires=['numpy', 'scipy', 'wxpython==3.0', 'pyopengl', 'javabridge', 'lxml', 'python-bioformats'],
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
            install_requires=['numpy', 'scipy', 'wxpython', 'pyopengl', 'javabridge', 'lxml', 'python-bioformats', 'pyfftw', 'six', 'tifffile'],
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
if 0:#sys.platform.startswith('darwin') and sys.argv[1] == 'py2app':
    # ont mac, JDK files are simply copied
    target = os.path.join(folder, 'Chromagnon.app', 'Contents', 'Resources', 'jdk')
    copytree(jdk, target)
    
