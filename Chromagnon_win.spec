# -*- mode: python -*-

# install
# conda install appdirs packaging

# execute like...
# pyinstaller --clean E:\py\Chromagnon\Chromagnon_win.spec
# if applicable... --upx-dir=upx394w

import sys
pyversion = sys.version_info.major
if pyversion == 3:
    glut = 'glut64.dll'
elif pyversion == 2:
    glut = 'Library\\bin\\freeglut.dll'

# ----chromagnon version
with open('E:\\py\\Chromagnon\\version.py') as h:
    line = next(h)
    cversion = line.split()[-1][1:-1].replace('.', '')
# ------

block_cipher = None

home='C:\\Users\\Atsushi'

# put chromagnon.py in some other place to make the top-level different from sys.path
# $ cp -R ~/codes/py/Chromagnon ~/codes/gitchrom/
# $ cp -R ~/codes/py/imgio ~/codes/gitchrom/Chromagnon/
# $ cp -R ~/codes/py/ndviewer ~/codes/gitchrom/Chromagnon/
# $ cp -R ~/codes/py/PriCommon ~/codes/gitchrom/Chromagnon/
# $ cp -R ~/codes/py/Priithon ~/codes/gitchrom/Chromagnon/

#a = Analysis(['F:\\gitchrom\\Chromagnon\\chromagnon.py'],
a = Analysis(['E:\\py\\src\\Chromagnon\\Chromagnon\\Chromagnon\\chromagnon.py'],
             pathex=['E:\\py'],
             binaries=[(home+'\\Miniconda%i\\Library\\bin\\mkl_avx.dll' % pyversion, ''), (home+'\\Miniconda%i\\Library\\bin\\mkl_avx2.dll' % pyversion, ''), (home+'\\Miniconda%i\\%s' % (pyversion, glut), '')],
             datas=[(home+'\\Miniconda%i\\Lib\\site-packages\\javabridge\\*.pyd' % pyversion, 'javabridge'), (home+'\\Miniconda%i\\Lib\\site-packages\\javabridge\\jars\\*' % pyversion, 'javabridge\\jars'), (home+'\\Miniconda%i\\Lib\\site-packages\\bioformats\\jars\\*' % pyversion, 'bioformats\\jars'), ('E:\\py\\Priithon\\*.py', 'Priithon'), ('E:\\py\\Priithon\\plt\\*.py', 'Priithon\\plt'), ('E:\\py\\PriCommon\\*.py', 'PriCommon')],
             hiddenimports=['six', 'packaging', 'packaging.version', 'packaging.specifiers', 'packaging.requirements', 'appdirs'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['pylab', 'Tkinter', 'matplotlib', 'pdb', 'pyqt5', 'pyqtgraph', 'pytz', 'opencv', 'reikna', 'pycuda', 'skcuda', 'wx.py', 'distutils', 'setuptools'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Chromagnon',
          debug=False,
          strip=False,
          upx=False,#True,
          console=False,
          windowed=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False, #True,
               name='ChromagnonV%sWin' % cversion)

# 20180412
# File "stringsource", line 103, in init scipy.optimize._trlib._trlib
#AttributeError: type object 'scipy.optimize._trlib._trlib.array' has no attribute '__reduce_cython__'
# copied Library\mingw-w64\bin\liblzma-5.dll to Library\bin -> no change
# same for python 2.7 and 3.5
# according to https://github.com/pyinstaller/pyinstaller/issues/2987
# this occurs with scipy >= 1.0.0, so scipy was downgraded to 0.19, and it worked

# 20180413
# Javabridge from PIP results in opening and closing of command prompt many times during the program is running, installing the conda-version of Javabridge solved the problem
