#!/usr/bin/env python

"""
Usage:
    python setup.py [py2app/sdist/install]

The code was tested with Miniconda verion of python
"""
import os, sys, stat
from setuptools import setup
from shutil import rmtree


pyversion = sys.version_info.major

# http://stackoverflow.com/questions/2159211/use-distribute-setuptools-to-create-symlink-or-run-script
# to make symlink during installation
from setuptools.command.install import install
class CustomInstallCommand(install):
    """Customized setuptools install command."""
    def run(self):
        install.run(self)
        # post-processing code

mainscript = os.path.join('Chromagnon', 'chromagnon.py')
h = open('Chromagnon/version.py')
line = h.readline()
exec(line)
h.close()

packages = ['Chromagnon', 'Chromagnon.common', 'Chromagnon.Priithon', 'Chromagnon.Priithon.plt', 'Chromagnon.PriCommon', 'Chromagnon.ndviewer', 'Chromagnon.imgio', 'Chromagnon.imgio.mybioformats']

extra_options = dict(
    install_requires=['numpy', 'scipy', 'tifffile<=2021.7.2', 'chardet', 'six'],
    packages=packages,
    cmdclass={
        'install': CustomInstallCommand}
    )

if sys.platform.startswith('darwin'):
    extra_options['entry_points'] = {'console_scripts': ['chromagnon=Chromagnon.chromagnon:command_line']}
    extra_options['scripts'] = [mainscript]
else:
    extra_options['entry_points'] = {'console_scripts': ['chromagnon=Chromagnon.chromagnon:command_line']}

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
