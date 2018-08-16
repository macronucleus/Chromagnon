#!/usr/bin/env python

"""
Usage:
    python setup.py [py2app/sdist/install]
on Mac 20180202:
    modify python3.6.sysconfig._get_sysconfigdata_name(check_exists=None)
    ln -s /Users/USER/miniconda3/lib/libpython3.6m.dylib libpython3.6.dylib
    then pythonw setup.py py2app to import javabridge

    install numpy with nomkl like this
    conda nomkl numpy scipy
    see https://github.com/pyinstaller/pyinstaller/issues/2175

The code was tested with Miniconda verion of python
"""
import os, sys, stat
from setuptools import setup
from shutil import rmtree


pyversion = sys.version_info.major

#---------- prepare to build the distribution packages ---------------
if sys.argv[1] == 'py2app':
    suff = 'Mac'

    try:
        from Chromagnon import version as chv
    except ImportError:
        import version as chv
    version = chv.version

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

    home = os.path.expanduser('~')
    script = os.path.join('py', 'Chromagnon', 'chromagnon.py')

    mini = 'miniconda%i' % pyversion
    mainscript = os.path.join(home, 'codes', script)

    conda = os.path.join(home, mini)

# ------- options ----------------------

excludes = ['matplotlib', 'pylab', 'Tkinter', 'Tkconstants', 'tcl',  'doctest', 'pydoc', 'pdb', 'pyqt5', 'pyqtgraph', 'pytz', 'opencv', 'reikna', 'pycuda', 'skcuda', 'wx.py', 'distutils', 'setuptools'] # email is required for bioformats


# ------- Platform ----------------------
# ------- MacOSX options py2app (v0.9)----------------

if sys.platform == 'darwin' and sys.argv[1] == 'py2app':

    packages = ['tifffile', 'javabridge', 'bioformats', 'html'] # py2app cannot find some packages without help, html is for bioformats
    
    libdir = os.path.join(conda, 'lib')

    os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = libdir

    # http://beckism.com/2009/03/pyobjc_tips/
    OPTIONS = {'argv_emulation': False, # to enable ndviewer window
               'site_packages': True,
               'use_pythonpath': True,
               'packages': packages, 
               'excludes': excludes}
    
    extra_options = dict(
         setup_requires=['py2app'],
         app=[mainscript],
         options={'py2app': OPTIONS},
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

    mainscript = os.path.join('Chromagnon', 'chromagnon.py')
    h = open('Chromagnon/version.py')
    line = h.readline()
    exec(line)
    
    packages = ['Chromagnon', 'Chromagnon.Priithon', 'Chromagnon.Priithon.plt', 'Chromagnon.PriCommon', 'Chromagnon.ndviewer', 'Chromagnon.imgio', 'Chromagnon.imgio.mybioformats']

    extra_options = dict(
        install_requires=['numpy', 'scipy', 'wxpython>=3.0', 'pyopengl', 'pillow', 'six', 'tifffile<=0.15.1'],
        packages=packages,
        cmdclass={
            'install': CustomInstallCommand}
        )
        
    if sys.platform.startswith('darwin'):
        extra_options['entry_points'] = {'console_scripts': ['chromagnon=Chromagnon.chromagnon:command_line']}
        extra_options['scripts'] = [mainscript]
    else:
        extra_options['entry_points'] = {'console_scripts': ['chromagnon=Chromagnon.chromagnon:command_line']}
    if not sys.platform.startswith('linux'):
        extra_options['install_requires'].append('PyPubSub')


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
