##
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010, 2013, James McCoy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

"""
Contains simple socket drivers.  Asyncore bugged (haha, pun!) me.
"""

from __future__ import division

import os
import sys
import time
import errno
import select
import socket

from .. import (conf, drivers, log, schedule, utils, world)
from ..utils.iter import imap
try:
    from charade.universaldetector import UniversalDetector
    charadeLoaded = True
except:
    drivers.log.debug('charade module not available, '
                      'cannot guess character encoding if'
                      'using Python3')
    charadeLoaded = False

try:
    import ssl
    SSLError = ssl.SSLError
except:
    drivers.log.debug('ssl module is not available, '
                      'cannot connect to SSL servers.')
    class SSLError(Exception):
        pass


class SocketDriver(drivers.IrcDriver, drivers.ServersMixin):
    _instances = []
    _selecting = [False] # We want it to be mutable.
    def __init__(self, irc):
        self._instances.append(self)
        assert irc is not None
        self.irc = irc
        drivers.IrcDriver.__init__(self, irc)
        drivers.ServersMixin.__init__(self, irc)
        self.conn = None
        self._attempt = -1
        self.servers = ()
        self.eagains = 0
        self.inbuffer = b''
        self.outbuffer = ''
        self.zombie = False
        self.connected = False
        self.writeCheckTime = None
        self.nextReconnectTime = None
        self.resetDelay()
        if self.networkGroup.get('ssl').value and not globals().has_key('ssl'):
            drivers.log.error('The Socket driver can not connect to SSL '
                              'servers for your Python version.  Try the '
                              'Twisted driver instead, or install a Python'
                              'version that supports SSL (2.6 and greater).')
        else:
            self.connect()

    def getDelay(self):
        ret = self.currentDelay
        self.currentDelay = min(self.currentDelay * 2,
                                conf.supybot.drivers.maxReconnectWait())
        return ret

    def resetDelay(self):
        self.currentDelay = 10.0

    def _getNextServer(self):
        oldServer = getattr(self, 'currentServer', None)
        server = drivers.ServersMixin._getNextServer(self)
        if self.currentServer != oldServer:
            self.resetDelay()
        return server

    def _handleSocketError(self, e):
        # (11, 'Resource temporarily unavailable') raised if connect
        # hasn't finished yet.  We'll keep track of how many we get.
        if e.args[0] != 11 or self.eagains > 120:
            drivers.log.disconnect(self.currentServer, e)
            if self in self._instances:
                self._instances.remove(self)
            try:
                self.conn.close()
            except:
                pass
            self.connected = False
            self.scheduleReconnect()
        else:
            log.debug('Got EAGAIN, current count: %s.', self.eagains)
            self.eagains += 1

    def _sendIfMsgs(self):
        if not self.connected:
            return
        if not self.zombie:
            msgs = [self.irc.takeMsg()]
            while msgs[-1] is not None:
                msgs.append(self.irc.takeMsg())
            del msgs[-1]
            self.outbuffer += ''.join(imap(str, msgs))
        if self.outbuffer:
            try:
                if sys.version_info[0] < 3:
                    sent = self.conn.send(self.outbuffer)
                else:
                    sent = self.conn.send(self.outbuffer.encode())
                self.outbuffer = self.outbuffer[sent:]
                self.eagains = 0
            except socket.error, e:
                self._handleSocketError(e)
        if self.zombie and not self.outbuffer:
            self._reallyDie()

    @classmethod
    def _select(cls):
        if cls._selecting[0]:
            return
        try:
            cls._selecting[0] = True
            for inst in cls._instances:
                # Do not use a list comprehension here, we have to edit the list
                # and not to reassign it.
                if not inst.connected or \
                        (sys.version_info[0] == 3 and inst.conn._closed) or \
                        (sys.version_info[0] == 2 and
                            inst.conn._sock.__class__ is socket._closedsocket):
                    cls._instances.remove(inst)
                elif inst.conn.fileno() == -1:
                    inst.reconnect()
            if not cls._instances:
                return
            rlist, wlist, xlist = select.select([x.conn for x in cls._instances],
                    [], [], conf.supybot.drivers.poll())
            for instance in cls._instances:
                if instance.conn in rlist:
                    instance._read()
        except select.error as e:
            if e.args[0] != errno.EINTR:
                # 'Interrupted system call'
                raise
        finally:
            cls._selecting[0] = False
        for instance in cls._instances:
            if instance.irc and not instance.irc.zombie:
                instance._sendIfMsgs()


    def run(self):
        now = time.time()
        if self.nextReconnectTime is not None and now > self.nextReconnectTime:
            self.reconnect()
        elif self.writeCheckTime is not None and now > self.writeCheckTime:
            self._checkAndWriteOrReconnect()
        if not self.connected:
            # We sleep here because otherwise, if we're the only driver, we'll
            # spin at 100% CPU while we're disconnected.
            time.sleep(conf.supybot.drivers.poll())
            return
        self._sendIfMsgs()
        self._select()

    def _read(self):
        """Called by _select() when we can read data."""
        try:
            self.inbuffer += self.conn.recv(1024)
            self.eagains = 0 # If we successfully recv'ed, we can reset this.
            lines = self.inbuffer.split(b'\n')
            self.inbuffer = lines.pop()
            for line in lines:
                if sys.version_info[0] >= 3:
                    #first, try to decode using utf-8
                    try:
                        line = line.decode('utf8', 'strict')
                    except UnicodeError:
                        # if this fails and charade is loaded, try to guess the correct encoding
                        if charadeLoaded:
                            u = UniversalDetector()
                            u.feed(line)
                            u.close()
                            if u.result['encoding']:
                                # try to use the guessed encoding
                                try:
                                    line = line.decode(u.result['encoding'],
                                        'strict')
                                # on error, give up and replace the offending characters
                                except UnicodeError:
                                    line = line.decode(errors='replace')
                            else:
                                # if no encoding could be guessed, fall back to utf-8 and
                                # replace offending characters
                                line = line.decode('utf8', 'replace')
                        # if charade is not loaded, try to decode using utf-8 and replace any
                        # offending characters
                        else:
                            line = line.decode('utf8', 'replace')

                msg = drivers.parseMsg(line)
                if msg is not None:
                    self.irc.feedMsg(msg)
        except socket.timeout:
            pass
        except SSLError, e:
            if e.args[0] == 'The read operation timed out':
                pass
            else:
                self._handleSocketError(e)
                return
        except socket.error, e:
            self._handleSocketError(e)
            return
        if not self.irc.zombie:
            self._sendIfMsgs()

    def connect(self, **kwargs):
        self.reconnect(reset=False, **kwargs)

    def reconnect(self, wait=False, reset=True):
        self._attempt += 1
        self.nextReconnectTime = None
        if self.connected:
            drivers.log.reconnect(self.irc.network)
            if self in self._instances:
                self._instances.remove(self)
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except: # "Transport endpoint not connected"
                pass
            self.conn.close()
            self.connected = False
        if reset:
            drivers.log.debug('Resetting %s.', self.irc)
            self.irc.reset()
        else:
            drivers.log.debug('Not resetting %s.', self.irc)
        if wait:
            self.scheduleReconnect()
            return
        server = self._getNextServer()
        socks_proxy = getattr(conf.supybot.networks, self.irc.network) \
                .socksproxy()
        resolver = None
        try:
            if socks_proxy:
                import socks
        except ImportError:
            log.error('Cannot use socks proxy (SocksiPy not installed), '
                    'using direct connection instead.')
            socks_proxy = ''
        if socks_proxy:
            address = server[0]
        else:
            try:
                address = utils.net.getAddressFromHostname(server[0],
                        attempt=self._attempt)
            except socket.gaierror as e:
                drivers.log.connectError(self.currentServer, e)
                self.scheduleReconnect()
                return
        drivers.log.connect(self.currentServer)
        try:
            self.conn = utils.net.getSocket(address, socks_proxy)
            vhost = conf.supybot.protocols.irc.vhost()
            self.conn.bind((vhost, 0))
        except socket.error, e:
            drivers.log.connectError(self.currentServer, e)
            self.scheduleReconnect()
            return
        # We allow more time for the connect here, since it might take longer.
        # At least 10 seconds.
        self.conn.settimeout(max(10, conf.supybot.drivers.poll()*10))
        try:
            if getattr(conf.supybot.networks, self.irc.network).ssl():
                assert globals().has_key('ssl')
                certfile = getattr(conf.supybot.networks, self.irc.network) \
                        .certfile()
                if not certfile:
                    certfile = None
                elif not os.path.isfile(certfile):
                    drivers.log.warning('Could not find cert file %s.' %
                            certfile)
                    certfile = None
                self.conn = ssl.wrap_socket(self.conn, certfile=certfile)
            self.conn.connect((address, server[1]))
            def setTimeout():
                self.conn.settimeout(conf.supybot.drivers.poll())
            conf.supybot.drivers.poll.addCallback(setTimeout)
            setTimeout()
            self.connected = True
            self.resetDelay()
        except socket.error, e:
            if e.args[0] == 115:
                now = time.time()
                when = now + 60
                whenS = log.timestamp(when)
                drivers.log.debug('Connection in progress, scheduling '
                                  'connectedness check for %s', whenS)
                self.writeCheckTime = when
            else:
                drivers.log.connectError(self.currentServer, e)
                self.scheduleReconnect()
            return
        self._instances.append(self)

    def _checkAndWriteOrReconnect(self):
        self.writeCheckTime = None
        drivers.log.debug('Checking whether we are connected.')
        (_, w, _) = select.select([], [self.conn], [], 0)
        if w:
            drivers.log.debug('Socket is writable, it might be connected.')
            self.connected = True
            self.resetDelay()
        else:
            drivers.log.connectError(self.currentServer, 'Timed out')
            self.reconnect()

    def scheduleReconnect(self):
        when = time.time() + self.getDelay()
        if not world.dying:
            drivers.log.reconnect(self.irc.network, when)
        if self.nextReconnectTime:
            drivers.log.error('Updating next reconnect time when one is '
                              'already present.  This is a bug; please '
                              'report it, with an explanation of what caused '
                              'this to happen.')
        self.nextReconnectTime = when

    def die(self):
        if self in self._instances:
            self._instances.remove(self)
        self.zombie = True
        if self.nextReconnectTime is not None:
            self.nextReconnectTime = None
        if self.writeCheckTime is not None:
            self.writeCheckTime = None
        drivers.log.die(self.irc)

    def _reallyDie(self):
        if self.conn is not None:
            self.conn.close()
        drivers.IrcDriver.die(self)
        # self.irc.die() Kill off the ircs yourself, jerk!

    def name(self):
        return '%s(%s)' % (self.__class__.__name__, self.irc)


Driver = SocketDriver

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

