

import sys, os

#### javabridge for py2exe
# following workaround should be put before importing anything involved.
INIT = False
import imp
def main_is_frozen():
   return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze

def init_java_home():
    global INIT
    if not INIT:
        if sys.platform.startswith('win'):
            # py2exe emit warnings as error messages if it is not supressed.
            import warnings
            warnings.simplefilter('ignore')

        if main_is_frozen(): # py2exe
            cwd = os.path.dirname(os.path.abspath(sys.argv[0]))
            if sys.platform.startswith('win'):
                jdk = os.path.join(cwd, 'jdk')
            elif sys.platform.startswith('darwin'):
                jdk = os.path.join(os.path.dirname(cwd), 'Resources', 'jdk')
            print 'jdk is', jdk
            if not os.getenv('JDK_HOME'):
                os.environ['JDK_HOME'] = jdk
            if not os.getenv('JAVA_HOME'):
                os.environ['JAVA_HOME'] = jdk

            if sys.platform.startswith('win') and cwd not in os.getenv('PATH'):
                os.environ['PATH'] = cwd + ';' + os.environ['PATH']
                print 'path set at ', cwd
                print os.environ['PATH']
                
            INIT = True
        else:
            print 'this is not frozen'

init_java_home()
