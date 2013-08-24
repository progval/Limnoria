###
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

import time
import errno
import select
import socket

from .. import (conf, drivers, log, schedule, utils, world)
from ..utils.iter import imap

try:
    import ssl
except ImportError:
    drivers.log.debug('ssl module is not available, '
                      'cannot connect to SSL servers.')
    ssl = None

class SocketDriver(drivers.IrcDriver, drivers.ServersMixin):
    def __init__(self, irc):
        self.irc = irc
        drivers.IrcDriver.__init__(self, irc)
        drivers.ServersMixin.__init__(self, irc)
        self.conn = None
        self.servers = ()
        self.eagains = 0
        self.inbuffer = ''
        self.outbuffer = ''
        self.zombie = False
        self.connected = False
        self.writeCheckTime = None
        self.nextReconnectTime = None
        self.resetDelay()
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
        if not self.zombie:
            msgs = [self.irc.takeMsg()]
            while msgs[-1] is not None:
                msgs.append(self.irc.takeMsg())
            del msgs[-1]
            self.outbuffer += ''.join(imap(str, msgs))
        if self.outbuffer:
            try:
                sent = self.conn.send(self.outbuffer)
                self.outbuffer = self.outbuffer[sent:]
                self.eagains = 0
            except socket.error, e:
                self._handleSocketError(e)
        if self.zombie and not self.outbuffer:
            self._reallyDie()

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
        try:
            self.inbuffer += self.conn.recv(1024)
            self.eagains = 0 # If we successfully recv'ed, we can reset this.
            lines = self.inbuffer.split('\n')
            self.inbuffer = lines.pop()
            for line in lines:
                msg = drivers.parseMsg(line)
                if msg is not None:
                    self.irc.feedMsg(msg)
        except socket.timeout:
            pass
        except ssl.SSLError, e:
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
        self.nextReconnectTime = None
        if self.connected:
            drivers.log.reconnect(self.irc.network)
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
        host = server[0]
        address = None
        drivers.log.connect(self.currentServer)
        for addrinfo in socket.getaddrinfo(server[0], None,
                                           socket.AF_UNSPEC,
                                           socket.SOCK_STREAM):
            address = addrinfo[4][0]
            try:
                self.conn = socket.socket(addrinfo[0], addrinfo[1])
                if self.networkGroup.get('ssl').value:
                    if ssl:
                        self.plainconn = self.conn
                        self.conn = ssl.wrap_socket(self.conn)
                    else:
                        drivers.log.error('ssl module not available, '
                                  'cannot connect to SSL servers.')
                        return
                vhost = conf.supybot.protocols.irc.vhost()
                self.conn.bind((vhost, 0))
            except socket.error, e:
                msg = host
                if host != address:
                    msg = '%s (%s)' % (host, address)
                drivers.log.connectError(msg, e)
                continue
            # We allow more time for the connect here, since it might take longer.
            # At least 10 seconds.
            self.conn.settimeout(max(10, conf.supybot.drivers.poll()*10))
            try:
                self.conn.connect((addrinfo[4][0], server[1]))
                self.conn.settimeout(conf.supybot.drivers.poll())
                self.connected = True
                self.resetDelay()
                break
            except socket.error, e:
                if e.args[0] == errno.EINPROGRESS:
                    now = time.time()
                    when = now + 60
                    whenS = log.timestamp(when)
                    drivers.log.debug('Connection in progress, scheduling '
                                      'connectedness check for %s', whenS)
                    self.writeCheckTime = when
                    break
                msg = host
                if host != address:
                    msg = '%s (%s)' % (host, address)
                drivers.log.connectError(msg, e)
                continue
        if not self.connected:
            self.scheduleReconnect()

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

