#! /usr/local/bin python2.5

# modified from pprocess.py
# woks only on unix-based os (includeing mac)
# got idea from
# http://www.freenetpages.co.uk/hp/alan.gauld/tutipc.htm

import os # os.fork() only on Unix
import sys
import select # polling works on pipes on Unix
#import socket
import traceback
import time
from packages import pprocess, logger

try:
    import cPickle as pickle
except ImportError:
    import pickle

log = logger.getLogger('ppro.py')
def debug(msg):
    logger.debug(log, msg)

try:
    from packages import ncpucores
    NCPU = ncpucores.determineNumberOfCPUs()
except ImportError: # such as python version <2.4
    NCPU = 2

TERM = 'terminate'
EXIT = 'exiting'
DONE = 'I am done with this task, feed me the next'
PARA = False
PROTOCOL = pickle.HIGHEST_PROTOCOL
#TIMEOUT = 1000 # ms or None

# Communications.
# pipe_in  parent -> child
#          give      receive
# pipe_out paretn <- child
#          get       send

#class AcknowledgementError(Exception):
#    pass

class ChannelBiDir(pprocess.Channel):

    "A bi-directional communications channel."

    def __init__(self, pid, read_pipe_out, write_pipe_out, read_pipe_in, write_pipe_in):

        """
        Initialise the channel with a process identifier 'pid', a 'read_pipe_out'
        from which messages will be received, and a 'write_pipe_out' into which
        messages will be sent.
        """

        self.pid = pid
        self.read_pipe_out = read_pipe_out
        self.write_pipe_out = write_pipe_out
        self.read_pipe_in = read_pipe_in
        self.write_pipe_in = write_pipe_in
        self.pickler_out = pickle.Pickler(self.write_pipe_out, PROTOCOL)
        self.pickler_in = pickle.Pickler(self.write_pipe_in, PROTOCOL)
        self.closed = 0
        self.exited = 0


    def close(self):

        "Explicitly close the channel."

        if not self.closed:
            self.closed = 1
            self.read_pipe_out.close()
            self.write_pipe_out.close()
            self.read_pipe_in.close()
            self.write_pipe_in.close()
           #self.wait(os.WNOHANG)

    def wait(self, options=0):

        "Wait for the created process, if any, to exit."

        if self.pid != 0:
            debug('channel wait')
            
            try:
                os.waitpid(self.pid, options)
            except OSError:
                pass

    def _send(self, obj):

        "Send the given object 'obj' through the channel."

        self.pickler_out.clear_memo()
        self.pickler_out.dump(obj)
       # pickle.dump(obj, self.write_pipe_out)
        self.write_pipe_out.flush()

    def send(self, obj):

        """
        Send the given object 'obj' through the channel. Then wait for an
        acknowledgement. (The acknowledgement makes the caller wait, thus
        preventing processes from exiting and disrupting the communications
        channel and losing data.)
        """

        self._send(obj)
        #if self._get() != "OK":
        #    raise AcknowledgementError, obj

    def _get(self):

        "Receive an object through the channel, returning the object."

        obj = pickle.load(self.read_pipe_out)
        try: # since traceback object cannot be pickled, this is a little dirty
            if isinstance(obj[0], Exception):
                print
                print '*** error in child process %i***' % self.pid
                for tbstr in obj[1]:
                    print tbstr,
                print 
                print '*** error of the parent process ***'
                raise obj[0] # this is not the best way, but ...
            else:
                return obj
        except (TypeError, IndexError):
            return obj
       # if isinstance(obj, Exception):
       #     raise obj
       # else:
       #     return obj

    def get(self):

        """
        Receive an object through the channel, returning the object. Send an
        acknowledgement of receipt. (The acknowledgement makes the sender wait,
        thus preventing processes from exiting and disrupting the communications
        channel and losing data.)
        """

      #  try:
        obj = self._get()
        return obj
     #   finally:
     #       pass
            #self._send("OK")

    def _give(self, obj):

        "Send the given object 'obj' through the channel."

        self.pickler_in.clear_memo()
        self.pickler_in.dump(obj)
       # pickle.dump(obj, self.write_pipe_in)
        self.write_pipe_in.flush()

    def give(self, obj):
        self._give(obj)
       # if self._receive() != "OK":
       #     raise AcknowledgementError, obj

    def _receive(self):

        "Receive an object through the channel, returning the object."

        obj = pickle.load(self.read_pipe_in)
        if isinstance(obj, Exception):
            raise obj
        else:
            return obj

    def receive(self):

        """
        Receive an object through the channel, returning the object. Send an
        acknowledgement of receipt. (The acknowledgement makes the sender wait,
        thus preventing processes from exiting and disrupting the communications
        channel and losing data.)
        """

        try:
            obj = self._receive()
            return obj
        finally:
            pass
            #self._give("OK")


# Management of processes and communications.

class ExchangeLargeData(pprocess.Exchange):

    """
    A communications exchange that can be used to detect channels which are
    ready to communicate. Subclasses of this class can define the 'store_data'
    method in order to enable the 'add_wait', 'wait' and 'finish' methods.
    """

    def __init__(self, channels=None, limit=NCPU, reuse=0, autoclose=1):
        pprocess.Exchange.__init__(self, channels, limit, reuse, autoclose)

    def add(self, channel):

        "Add the given 'channel' to the exchange."

        self.readables[channel.read_pipe_out.fileno()] = channel
        self.poller.register(channel.read_pipe_out.fileno(), select.POLLIN | select.POLLHUP | select.POLLNVAL | select.POLLERR)

    def ready(self, timeout=None): # milisecond

        """
        Wait for a period of time specified by the optional 'timeout' (or until
        communication is possible) and return a list of channels which are ready
        to be read from.
        """
        debug('before polling')# self.readables %s' % self.readables)
        
        channels = self.readables.values()
        for channel in channels:
            if channel.exited:
                self.remove(channel)

        if not self.readables:
            return []

        fds = self.poller.poll(timeout)
        debug('after polling: fd done %s' % fds)
        
        readables = []
        self.removed = []

        for fd, status in fds:
            channel = self.readables[fd]
            removed = 0

            # Remove ended/error channels.

            if status & (select.POLLHUP | select.POLLNVAL | select.POLLERR):
                self.remove(channel)
                self.removed.append(channel)
                removed = 1

            # Record readable channels.

            if status & select.POLLIN:
                if not (removed and self.autoclose):
                    readables.append(channel)

        return readables

    def remove(self, channel):

        """
        Remove the given 'channel' from the exchange.
        """

        del self.readables[channel.read_pipe_out.fileno()]
        self.poller.unregister(channel.read_pipe_out.fileno())
        if self.autoclose:
            channel.close()
            channel.wait()

    def wait(self):

        """
        Test for the limit on channels, blocking and reading incoming data until
        the number of channels is below the limit.
        """

        # If limited, block until channels have been closed.

        while self.limit is not None and len(self.active()) >= self.limit:
            debug('exchange wait %s' % len(self.active()))
            
            self.store()

    def start_waiting(self, channel):

        """
        Start a waiting process given the reception of data on the given
        'channel'.
        """

        if self.waiting:
            debug(str(self.waiting))
            callable, args, kw = self.waiting.pop()

            # Try and reuse existing channels if possible.

            if self.reuse:

                # Re-add the channel - this may update information related to
                # the channel in subclasses.

                self.add(channel)
                channel.send((args, kw))
            else:
                self.add(start(callable, *args, **kw))

        # Where channels are being reused, but where no processes are waiting
        # any more, send a special value to tell them to quit.

        elif self.reuse:
            channel.send(None)

    # Convenience methods.

    def start(self, callable, *args, **kw):

        """
        Using pprocess.start, create a new process for the given 'callable'
        using any additional arguments provided. Then, monitor the channel
        created between this process and the created process.
        """

        if self.limit is not None and len(self.active()) >= self.limit:
            debug('exchange start %s %s' % (self.active(), self.waiting))
            
            self.waiting.insert(0, (callable, args, kw))
            return

        channel = start(callable, *args, **kw)
        self.add_wait(channel)
        return channel

    def manage(self, callable):

        """
        Wrap the given 'callable' in an object which can then be called in the
        same way as 'callable', but with new processes and communications
        managed automatically.
        """

        return ManagedCallable(callable, self)

    def checkError(self, timeout=None):
        """
        time
        """
        stolled = self.ready(timeout) # check error in child processes
        for channel in stolled:
            debug('channel %i in ready()' % channel.pid)
            x = channel.get() # this should raise error
            debug('%s' % x)


    def getNextChannels(self, processor=None):
        """
        processor is a function to process returned data one at a time
        only accept arguments from child process
        returned value is stored in self.data
        """
        channels = []
        while not channels:
            channels = self.ready(1) # quick check
            if not channels:
                time.sleep(0.1)
        for channel in channels:
            x = channel.get() # if error, this will raise
            if processor:
                ret = processor(*x)
                if ret is not None:
                    if type(ret) == self.data:
                        self.data += ret
                    elif type(self.data) == list:
                        self.data += [ret]
                    elif type(self.data) == tuple:
                        self.data += (ret)
            elif x != DONE:
                raise RuntimeError, 'got this %s' % x
        return channels
            

class ManagedCallable(pprocess.ManagedCallable):

    "A callable managed by an exchange."

    def __init__(self, callable, exchange):
        pprocess.ManagedCallable.__init__(self, callable, exchange)

    def __call__(self, *args, **kw):

        "Invoke the callable with the supplied arguments."

        return self.exchange.start(self.callable, *args, **kw)

class MapMoreArgs(pprocess.Map):
    def __init__(self, *args, **kw):
        pprocess.Map.__init__(self, *args, **kw)

    def __call__(self, callable, sequence, *args, **kw):

        "Wrap and invoke 'callable' for each element in the 'sequence'."

        if not isinstance(callable, pprocess.MakeParallel):
            wrapped = pprocess.MakeParallel(callable)
        else:
            wrapped = callable

        self.init()

        # Start processes for each element in the sequence.

        for i in sequence:
            self.start(wrapped, i, *args, **kw)

        # Access to the results occurs through this object.

        self.finish()
        return self

    def __getitem__(self, i):
       # self.finish()
        return self.results[i]

    def __iter__(self):
        #self.finish()
        return iter(self.results)

    def __str__(self):
        return str(self.results)

    def __repr__(self):
        return repr(self.results)

class MakeParallel:

    "A wrapper around functions making them able to communicate results."

    def __init__(self, callable, sendEveryTime=None, terminator=TERM):

        """
        Initialise the wrapper with the given 'callable'. This object will then
        be able to accept a 'channel' parameter when invoked, and to forward the
        result of the given 'callable' via the channel provided back to the
        invoking process.
        """
        self.callable = callable
        self.terminator = terminator
        self.sendEveryTime = sendEveryTime

    def __call__(self, channel, *args, **kw):

        "Invoke the callable and return its result via the given 'channel'."

        ret = []
        x = 1
        if x == self.terminator:
            x += 1
        while True:
            x = channel.receive()
            if type(x) == type(self.terminator) and x == self.terminator:
                break
            if self.sendEveryTime:
                channel.send(self.callable(x, *args, **kw))
            else:
                ret.append(self.callable(x, *args, **kw))
                channel.send(DONE)
        if not self.sendEveryTime:
            channel.send(ret)

# Utility functions.
def create_socket():

    """
    Create a new process, returning a communications channel to both the
    creating process and the created process.
    """
    # this is more delicate than os.pipe(), so not using here
    import socket
    parent, child = socket.socketpair()
   # for s in [parent, child]:
   #     s.setblocking(1) # = timeout None

    pid = os.fork()
    if pid == 0:
        return ChannelBiDir(pid, child.makefile("r", 0), child.makefile("w", 0), parent.makefile('r', 0), parent.makefile('w', 0))
    else:
        return ChannelBiDir(pid, parent.makefile("r", 0), parent.makefile("w", 0), child.makefile('r', 0), child.makefile('w', 0))



def create():

    """
    Create a new process, returning a communications channel to both the
    creating process and the created process.
    """
    ClientReceive, ServerSend = os.pipe() # in
    ServerReceive,ClientSend = os.pipe() # out

    pid = os.fork()

    ClientReceive = os.fdopen(ClientReceive)
    ServerSend = os.fdopen(ServerSend, 'w')
    ServerReceive = os.fdopen(ServerReceive)
    ClientSend = os.fdopen(ClientSend, 'w')

    return ChannelBiDir(pid, ClientReceive, ServerSend, ServerReceive, ClientSend)

def exit(channel):

    """
    Terminate a created process, closing the given 'channel'.
    """

    channel.close()
    os._exit(0)

def start(callable, *args, **kw):

    """
    Create a new process which shall start running in the given 'callable'.
    Additional arguments to the 'callable' can be given as additional arguments
    to this function.

    Return a communications channel to the creating process. For the created
    process, supply a channel as the 'channel' parameter in the given 'callable'
    so that it may send data back to the creating process.
    """

    channel = create()
    if channel.pid == 0:
        try:
            try:
                callable(channel, *args, **kw)  # MakeParallel send(exec)
            except: # trace back object cannot be pickled
                import traceback
                exc_type, exc_value, exc_traceback = sys.exc_info()
                formatted = traceback.format_exception(exc_type, exc_value, exc_traceback) 
                
                channel.send((exc_value, formatted))
        finally:
            channel.send(EXIT)
            exit(channel)
    else:
        return channel

def parallelFeeder(consumer, seq, exchange=None, processor=None, *args, **kwds):
    """
    feed seq by single CPU and consumed by limit-1 CPUs

    seq:       any sequence or generator/iterator
    consumer:  function to consume one feed at a time, 1st argument == one feed from seq
    exchange:  ExchangeLargeData class object
    args/kwds: for consumer

    return exchange object with data attribute
    """
    call = exchange.manage(MakeParallel(consumer, bool(processor))) # -> __call__

    # create channels -> start
    channels = [call(*args, **kwds) for i in range(exchange.limit)]
    exchange.pids = [channel.pid for channel in channels]
    exchange.checkError(1)

    # Feed seq
    clist = []
    for i, x in enumerate(seq):
        if i < exchange.limit:
            channel = channels[i % exchange.limit]
        elif clist:
            channel = clist.pop()
        else:
            clist = exchange.getNextChannels(processor)
            channel = clist.pop()

        channel.give(x)

    # send termination signals
    for channel in channels:
        channel.give(TERM)
       # debug('is it already processed ?? %s' % channel.get()) #-> yes!!

    debug( 'just before finishing')

    exchange.finish() # -> start
    debug( 'done')

    return exchange





def makeExchange(limit=NCPU):
    """
    return ExchangeLargeData class object
    """
    exchange = ExchangeLargeData(limit=limit)
    exchange.data = []
    exchange.pids = []

    def recordThem(ch):
        if exchange.pids.count(ch.pid):
            idx = exchange.pids.index(ch.pid)
        else:
            idx = None
        while 1:
            data = ch.get()
            debug('get %i' % (ch.pid))
            if data == DONE:
                continue
            elif data == EXIT:
                debug('data is EXIT')
                ch.exited = 1
                break
            else:
                #if idx is None:
                exchange.data += data # the order is always mixed up
                #else:
                #    exchange.data[idx::exchange.limit] = data

    exchange.store_data = recordThem

    return exchange

def pmapLarge(consumer, seq, limit=NCPU, processor=None, *args, **kwds):
    """
    feed seq by single CPU and consumed by limit CPUs

    consumer:  function to consume one feed at a time, 1st argument == one feed from seq
    seq:       any sequence or generator/iterator
    args/kwds: for consumer
    processor: function to process arguments value returned from consumer

    return exchange object with data attribute
    """
    global log
    level = log.getEffectiveLevel()
    logger.setLevel('info')

    exchange = makeExchange(limit)
    exchange = parallelFeeder(consumer, seq, exchange, processor, *args, **kwds)

    logger.setLevel(level)
    return exchange.data

def test(limit=2):
    global log
    level = log.getEffectiveLevel()
    logger.setLevel('debug')
    ret = pmapLarge(func, range(8), limit)
    logger.setLevel(level)
    return ret

def func(val):
    return val**2

def pmap(callable, sequence, limit=NCPU, *args, **kwds):

    """
    A parallel version of the built-in map function with an optional process
    'limit'. The given 'callable' should not be parallel-aware (that is, have a
    'channel' parameter) since it will be wrapped for parallel communications
    before being invoked.

    Return the processed 'sequence' where each element in the sequence is
    processed by a different process.
    """
    global log
    level = log.getEffectiveLevel()
    logger.setLevel('info')

    mymap = MapMoreArgs(limit=limit)
    x = mymap(callable, sequence, *args, **kwds)

    logger.setLevel(level)
    return x

pversion = sys.version_info
#print 'python version', pversion
if 0:#pversion[0] == 2 and pversion[1] >= 6:
    #print 'importing ppro26'
    from ppro26 import *
