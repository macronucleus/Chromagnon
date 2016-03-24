#!/usr/bin/env python

"""
A simple parallel processing API for Python, inspired somewhat by the thread
module, slightly less by pypar, and slightly less still by pypvm.

Copyright (C) 2005, 2006, 2007 Paul Boddie <paul@boddie.org.uk>

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free
Software Foundation; either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
details.

You should have received a copy of the GNU Lesser General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__version__ = "0.3.1"

import os
import sys
import select
import socket

try:
    import cPickle as pickle
except ImportError:
    import pickle

# Communications.

class AcknowledgementError(Exception):
    pass

class Channel:

    "A communications channel."

    def __init__(self, pid, read_pipe, write_pipe):

        """
        Initialise the channel with a process identifier 'pid', a 'read_pipe'
        from which messages will be received, and a 'write_pipe' into which
        messages will be sent.
        """

        self.pid = pid
        self.read_pipe = read_pipe
        self.write_pipe = write_pipe
        self.closed = 0

    def __del__(self):

        # Since signals don't work well with I/O, we close pipes and wait for
        # created processes upon finalisation.

        self.close()

    def close(self):

        "Explicitly close the channel."

        if not self.closed:
            self.closed = 1
            self.read_pipe.close()
            self.write_pipe.close()
            #self.wait(os.WNOHANG)

    def wait(self, options=0):

        "Wait for the created process, if any, to exit."

        if self.pid != 0:
            try:
                os.waitpid(self.pid, options)
            except OSError:
                pass

    def _send(self, obj):

        "Send the given object 'obj' through the channel."

        pickle.dump(obj, self.write_pipe)
        self.write_pipe.flush()

    def send(self, obj):

        """
        Send the given object 'obj' through the channel. Then wait for an
        acknowledgement. (The acknowledgement makes the caller wait, thus
        preventing processes from exiting and disrupting the communications
        channel and losing data.)
        """

        self._send(obj)
        if self._receive() != "OK":
            raise AcknowledgementError, obj

    def _receive(self):

        "Receive an object through the channel, returning the object."

        obj = pickle.load(self.read_pipe)
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
            self._send("OK")

# Management of processes and communications.

class Exchange:

    """
    A communications exchange that can be used to detect channels which are
    ready to communicate. Subclasses of this class can define the 'store_data'
    method in order to enable the 'add_wait', 'wait' and 'finish' methods.
    """

    def __init__(self, channels=None, limit=None, reuse=0, autoclose=1):

        """
        Initialise the exchange with an optional list of 'channels'.

        If the optional 'limit' is specified, restrictions on the addition of
        new channels can be enforced and observed through the 'add_wait', 'wait'
        and 'finish' methods. To make use of these methods, create a subclass of
        this class and define a working 'store_data' method.

        If the optional 'reuse' parameter is set to a true value, channels and
        processes will be reused for waiting computations.

        If the optional 'autoclose' parameter is set to a false value, channels
        will not be closed automatically when they are removed from the exchange
        - by default they are closed when removed.
        """

        self.limit = limit
        self.reuse = reuse
        self.autoclose = autoclose
        self.waiting = []
        self.readables = {}
        self.removed = []
        self.poller = select.poll()
        for channel in channels or []:
            self.add(channel)

    def add(self, channel):

        "Add the given 'channel' to the exchange."

        self.readables[channel.read_pipe.fileno()] = channel
        self.poller.register(channel.read_pipe.fileno(), select.POLLIN | select.POLLHUP | select.POLLNVAL | select.POLLERR)

    def active(self):

        "Return a list of active channels."

        return self.readables.values()

    def ready(self, timeout=None):

        """
        Wait for a period of time specified by the optional 'timeout' (or until
        communication is possible) and return a list of channels which are ready
        to be read from.
        """

        fds = self.poller.poll(timeout)
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

        del self.readables[channel.read_pipe.fileno()]
        self.poller.unregister(channel.read_pipe.fileno())
        if self.autoclose:
            channel.close()
            channel.wait()

    # Enhanced exchange methods involving channel limits.

    def add_wait(self, channel):

        """
        Add the given 'channel' to the exchange, waiting if the limit on active
        channels would be exceeded by adding the channel.
        """

        self.wait()
        self.add(channel)

    def wait(self):

        """
        Test for the limit on channels, blocking and reading incoming data until
        the number of channels is below the limit.
        """

        # If limited, block until channels have been closed.

        while self.limit is not None and len(self.active()) >= self.limit:
            self.store()

    def start_waiting(self, channel):

        """
        Start a waiting process given the reception of data on the given
        'channel'.
        """

        if self.waiting:
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

    def finish(self):

        """
        Finish the use of the exchange by waiting for all channels to complete.
        """

        while self.active():
            self.store()

    def store(self):

        "For each ready channel, process the incoming data."

        for channel in self.ready():
            self.store_data(channel)
            self.start_waiting(channel)

    def store_data(self, channel):

        """
        Store incoming data from the specified 'channel'. In subclasses of this
        class, such data could be stored using instance attributes.
        """

        raise NotImplementedError, "store_data"

    # Convenience methods.

    def start(self, callable, *args, **kw):

        """
        Using pprocess.start, create a new process for the given 'callable'
        using any additional arguments provided. Then, monitor the channel
        created between this process and the created process.
        """

        if self.limit is not None and len(self.active()) >= self.limit:
            self.waiting.insert(0, (callable, args, kw))
            return

        self.add_wait(start(callable, *args, **kw))

    def create(self):

        """
        Using pprocess.create, create a new process and return the created
        communications channel to the created process. In the creating process,
        return None - the channel receiving data from the created process will
        be automatically managed by this exchange.
        """

        channel = create()
        if channel.pid == 0:
            return channel
        else:
            self.add_wait(channel)
            return None

    def manage(self, callable):

        """
        Wrap the given 'callable' in an object which can then be called in the
        same way as 'callable', but with new processes and communications
        managed automatically.
        """

        return ManagedCallable(callable, self)

class ManagedCallable:

    "A callable managed by an exchange."

    def __init__(self, callable, exchange):

        """
        Wrap the given 'callable', using the given 'exchange' to monitor the
        channels created for communications between this and the created
        processes. Note that the 'callable' must be parallel-aware (that is,
        have a 'channel' parameter). Use the MakeParallel class to wrap other
        kinds of callable objects.
        """

        self.callable = callable
        self.exchange = exchange

    def __call__(self, *args, **kw):

        "Invoke the callable with the supplied arguments."

        self.exchange.start(self.callable, *args, **kw)

# Abstractions and utilities.

class Map(Exchange):

    "An exchange which can be used like the built-in 'map' function."

    def __init__(self, *args, **kw):
        Exchange.__init__(self, *args, **kw)
        self.init()

    def init(self):

        "Remember the channel addition order to order output."

        self.channel_number = 0
        self.channels = {}
        self.results = []

    def add(self, channel):

        "Add the given 'channel' to the exchange."

        Exchange.add(self, channel)
        self.channels[channel] = self.channel_number
        self.channel_number += 1

    def start(self, callable, *args, **kw):

        """
        Using pprocess.start, create a new process for the given 'callable'
        using any additional arguments provided. Then, monitor the channel
        created between this process and the created process.
        """

        self.results.append(None) # placeholder
        Exchange.start(self, callable, *args, **kw)

    def create(self):

        """
        Using pprocess.create, create a new process and return the created
        communications channel to the created process. In the creating process,
        return None - the channel receiving data from the created process will
        be automatically managed by this exchange.
        """

        self.results.append(None) # placeholder
        return Exchange.create(self)

    def __call__(self, callable, sequence):

        "Wrap and invoke 'callable' for each element in the 'sequence'."

        if not isinstance(callable, MakeParallel):
            wrapped = MakeParallel(callable)
        else:
            wrapped = callable

        self.init()

        # Start processes for each element in the sequence.

        for i in sequence:
            self.start(wrapped, i)

        # Access to the results occurs through this object.

        return self

    def __getitem__(self, i):
        self.finish()
        return self.results[i]

    def __iter__(self):
        self.finish()
        return iter(self.results)

    def store_data(self, channel):

        "Accumulate the incoming data, associating results with channels."

        data = channel.receive()
        self.results[self.channels[channel]] = data
        del self.channels[channel]

class Queue(Exchange):

    """
    An exchange acting as a queue, making data from created processes available
    in the order in which it is received.
    """

    def __init__(self, *args, **kw):
        Exchange.__init__(self, *args, **kw)
        self.queue = []

    def store_data(self, channel):

        "Accumulate the incoming data, associating results with channels."

        data = channel.receive()
        self.queue.insert(0, data)

    def __iter__(self):
        return self

    def next(self):

        "Return the next element in the queue."

        if self.queue:
            return self.queue.pop()
        while self.active():
            self.store()
            if self.queue:
                return self.queue.pop()
        else:
            raise StopIteration

class MakeParallel:

    "A wrapper around functions making them able to communicate results."

    def __init__(self, callable):

        """
        Initialise the wrapper with the given 'callable'. This object will then
        be able to accept a 'channel' parameter when invoked, and to forward the
        result of the given 'callable' via the channel provided back to the
        invoking process.
        """

        self.callable = callable

    def __call__(self, channel, *args, **kw):

        "Invoke the callable and return its result via the given 'channel'."

        channel.send(self.callable(*args, **kw))

class MakeReusable(MakeParallel):

    """
    A wrapper around functions making them able to communicate results in a
    reusable fashion.
    """

    def __call__(self, channel, *args, **kw):

        "Invoke the callable and return its result via the given 'channel'."

        channel.send(self.callable(*args, **kw))
        t = channel.receive()
        while t is not None:
            args, kw = t
            channel.send(self.callable(*args, **kw))
            t = channel.receive()

# Utility functions.

def create():

    """
    Create a new process, returning a communications channel to both the
    creating process and the created process.
    """

    parent, child = socket.socketpair()
    for s in [parent, child]:
        s.setblocking(1)

    pid = os.fork()
    if pid == 0:
        parent.close()
        return Channel(pid, child.makefile("r", 0), child.makefile("w", 0))
    else:
        child.close()
        return Channel(pid, parent.makefile("r", 0), parent.makefile("w", 0))

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
                callable(channel, *args, **kw)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                channel.send(exc_value)
        finally:
            exit(channel)
    else:
        return channel

def waitall():

    "Wait for all created processes to terminate."

    try:
        while 1:
            os.wait()
    except OSError:
        pass

def pmap(callable, sequence, limit=None):

    """
    A parallel version of the built-in map function with an optional process
    'limit'. The given 'callable' should not be parallel-aware (that is, have a
    'channel' parameter) since it will be wrapped for parallel communications
    before being invoked.

    Return the processed 'sequence' where each element in the sequence is
    processed by a different process.
    """

    mymap = Map(limit=limit)
    return mymap(callable, sequence)

# vim: tabstop=4 expandtab shiftwidth=4
