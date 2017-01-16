# -*- mode: python -*-

# install
# pip install packaging
# conda install appdirs

# execute like...
# pyinstaller --clean E:\py\chromagnon\Chromagnon.spec

block_cipher = None

home='C:\\Users\\Atsushi'

a = Analysis(['E:\\py\\chromagnon\\main.py'],
             pathex=['C:\\Users\\Atsushi\\Documents\\chrom'],
             binaries=[(home+'\\Miniconda2\\Library\\bin\\mkl_avx.dll', ''), (home+'\\Miniconda2\\Library\\bin\\mkl_avx2.dll', ''), (home+'\\Miniconda2\\libfftw3*.dll', ''), (home+'\\Miniconda2\\Library\\bin\\freeglut.dll', '')], 
             datas=[('C:\\Program Files\\Java\\jdk1.8.0_112', 'jdk'), (home+'\\Miniconda2\\Lib\\site-packages\\javabridge\\*.py[cd]', 'javabridge'), (home+'\\Miniconda2\\Lib\\site-packages\\javabridge\\jars\\*', 'javabridge\\jars'), (home+'\\Miniconda2\\Lib\\site-packages\\bioformats\\*.pyc', 'bioformats'), (home+'\\Miniconda2\\Lib\\site-packages\\bioformats\\jars\\*', 'bioformats\\jars')],
             hiddenimports=['six', 'packaging', 'packaging.version', 'packaging.specifiers', 'packaging.requirements', 'appdirs'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['pylab', 'PIL', 'Tkinter', 'matplotlib'],
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
          upx=True,
          console=False,
          windowed=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='ChromagnonV05Win')
