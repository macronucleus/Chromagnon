#!/usr/bin/env python

# install the newest python2.7 or python2.6 from python.org
# install wxpython.dmg
# according to http://trac.wxwidgets.org/ticket/14523
commandaftermount = 'sudo installer -pkg /Volumes/wxPython2.9-osx-2.9.4.0-cocoa-py2.7/wxPython2.9-osx-cocoa-py2.7.pkg -target /'
# scipy and numpy requires fortran
# install gfortran.dmg
# xcode-select --install
# xcodebuild -license
# Xcode (registration required) and commandline developer tools for gfortran

# if pip does not work due to ssl certificate, install easy_install pip=1.2.1

import sys, os, urllib, tempfile, subprocess, tarfile, shutil, stat

url = 'https://raw.github.com/pypa/pip/master/contrib/get-pip.py'
PYVERSION = '%i.%i' % tuple(sys.version_info[:2])

def main(*pipargs):
    installPIP()
    installDependens(*pipargs)
    installPriithon()

def installPIP():
    dd = tempfile.gettempdir()
    getpip, header = urllib.urlretrieve(url, os.path.join(dd, os.path.basename(url)))

    print 'installing pip for python%s' % PYVERSION
    result = subprocess.call(('python%s' % PYVERSION, getpip))
    if result:
        raise RuntimeError, 'pip was not installed properly'

    os.remove(getpip)
    print 'installation of pip complete'
    print

def installDependens(*pipargs):
    logfn = tempfile.mktemp()

    stdin = open('/dev/null', 'r')
    

    packages = ['numpy', 'scipy', 'Pillow', 'PyOpenGL', 'PyOpenGL-accelerate', 'matplotlib', 'PyFFTW3'] # if possible also OpenGLContext not conaptible for OpenGL3??

    pipcall = ['pip', 'list', '>', logfn]
    os.system(' '.join(pipcall))

    installed = []
    packagesl = [p.lower() for p in packages]
    h = open(logfn)
    lines = h.readlines()
    for line in lines:
        name = line.split()[0].lower()
        if name in packagesl:
            installed.append(packages[packagesl.index(name)])
    h.close()
    os.remove(logfn)
    
    tobeinstalled = [pkg for pkg in packages if pkg not in installed]

    print 'Intalled:', installed
    print 'To be installed:', tobeinstalled

    pipcalls = ['pip', 'install']

    failed = []
    
    for package in tobeinstalled:
        pipcall = pipcalls + [package] + list(pipargs)
        print '****installing ', package

        if package == 'matplotlib' and sys.platform == 'darwin':
            # according to https://gist.github.com/ahankinson/985173
            #pipcall = ['export', 'LDFLAGS="-L/usr/X11/lib";', 'export', 'CFLAGS="-I/usr/X11/include', '-I/usr/X11/include/freetype2', '-I/usr/X11/include/libpng12";'] + pipcalls + ['-e', 'git+git@github.com:matplotlib/matplotlib.git#egg=matplotlib']
            #old="""
            targetdir = '/usr/X11/include/freetype2'
            if os.path.isdir(targetdir) and not os.path.exists(targetdir[:-1]):
                result = subprocess.call(['ln', '-s',
                                          '%s/freetype' % targetdir,
                                          targetdir[:-1]])
                if result:
                    raise RuntimeError, 'creating a simbolic link failed'#"""
        elif package == 'PyFFTW3':
            url = 'http://www.fftw.org/fftw-3.3.3.tar.gz'
            pkgs = ['', '--enable-float', '--enable-long-double']
            for i, conf in enumerate(pkgs):
                configs = ['--enable-threads', '--enable-shared', conf]
                configMake(url, configs, download=not(i), retainpkg=(i==(len(pkgs)-1)))
                
        out = subprocess.check_output(pipcall, stderr=subprocess.STDOUT)

        errs = checkError(out)
        if errs:
            failed.append(package)
        else:
            print 'installing %s done' % package

    if failed:
        print 'following installation failed', failed

    return failed

def checkError(out):
    err = "Error"
    err_lines = []
    for line in out:
        if err in line or err.lower() in line:
            err_lines.append(line)
            print line
    return err_lines

def configMake(url, configs=[], download=True, retainpkg=True):
    curr_dir = os.getcwd()

    dd = tempfile.gettempdir()
    if download:
        pkg, header = urllib.urlretrieve(url, os.path.join(dd, os.path.basename(url)))
    else:
        pkg = os.path.join(dd, os.path.basename(url))
        
    extracted, ext = os.path.splitext(pkg)
    if extracted.endswith('tar'):
        extracted, ext2 = os.path.splitext(extracted)
        ext = ext2 + ext

    if 'tar' in ext:
        os.chdir(dd)
        tar = tarfile.open(pkg)
        tar.extractall()
        tar.close()
    else:
        extracted = pkg

    os.chdir(extracted)

    subprocess.call(['./configure'] + configs)
    subprocess.call(['make'])
    subprocess.call(['make', 'install'])
    subprocess.call(['rm', '-R', extracted])

    if not retainpkg:
        os.remove(pkg)

    os.chdir(curr_dir)

def installPriithon(targetdir=None, ext=['py', 'ico', 'txt']):
    """
    targetdir: such as site-packages
    """
    # root source direcotry
    dirname = os.path.dirname(__file__)

    subdir = [''] + [d for d in os.listdir(dirname) if os.path.isdir(d)]


    # root target directory
    if not targetdir:
        try:
            import site
            targetdir = site.getsitepackages()[0]
        except ImportError:
            from distutils.sysconfig import get_python_lib
            targetdir = get_python_lib()

    outdir = os.path.join(targetdir, 'Priithon')
    if not os.path.isdir(targetdir):
        os.mkdir(outdir)
        print 'making dir %s' % outdir


    # copy directories
    for pkg in subdir:
        # source directory
        if pkg:
            srcdir = os.path.join(dirname, pkg)
        else:
            srcdir = dirname

        # target directory
        if pkg:
            targetdir = os.path.join(outdir, pkg)
            if not os.path.isdir(targetdir):
                os.mkdir(targetdir)
                print 'making dir %s' % targetdir
        else:
            targetdir = outdir

        # list files
        fs = [ff for ff in os.listdir(srcdir) 
              if ff.endswith(ext) and not ff.startswith(('.'))]
        
        # copy files
        for fn in fs:
            src = os.path.join(srcdir, fn)
            des = os.path.join(targetdir, fn)
            try:
                shutil.copyfile(src, des)
                os.chmod(des, stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH) # a+rx|u+w

            except  (IOError, os.error), why:
                print "Can't copy %s to %s: %s" % (fn, out, why)
            print 'copied %s %s -> %s' % (fn, srcdir, targetdir)

if __name__ == '__main__':
    main()
