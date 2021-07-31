##
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010, 2013, James McCoy
# Copyright (c) 2010-2021, Valentin Lorentz
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
import asyncio
import threading

import ipaddress

from .. import (conf, drivers, log, utils, world)
from ..utils import minisix
from ..utils.str import decode_raw_line

try:
    import ssl
    SSLError = ssl.SSLError
except:
    drivers.log.debug('ssl module is not available, '
                      'cannot connect to SSL servers.')
    class SSLError(Exception):
        pass


class SocketDriver(drivers.IrcDriver, drivers.ServersMixin):
    def __init__(self, irc):
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
        if self.networkGroup.get('ssl')() and 'ssl' not in globals():
            drivers.log.error('The Socket driver can not connect to SSL '
                              'servers for your Python version.')
            self.ssl = False
        else:
            self.ssl = self.networkGroup.get('ssl')()
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
        # 'e is None' means the socket was closed.
        #
        # (11, 'Resource temporarily unavailable') raised if connect
        # hasn't finished yet.  We'll keep track of how many we get.
        if e is None or e.args[0] != 11 or self.eagains > 120:
            drivers.log.disconnect(self.currentServer, e)
            try:
                self.conn.close()
            except:
                pass
            self.connected = False
            if self.irc is None:
                return
            self.scheduleReconnect()
        else:
            log.debug('Got EAGAIN, current count: %s.', self.eagains)
            self.eagains += 1

    async def _sendIfMsgs(self):
        if not self.connected:
            return
        if not self.zombie:
            msgs = [self.irc.takeMsg()]
            while msgs[-1] is not None:
                msgs.append(self.irc.takeMsg())
            del msgs[-1]
            self.outbuffer += ''.join(map(str, msgs))
        if self.outbuffer:
            loop = asyncio.get_event_loop()
            try:
                await loop.sock_sendall(self.conn, self.outbuffer.encode())
                self.outbuffer = ''
                self.eagains = 0
            except socket.error as e:
                self._handleSocketError(e)
        if self.zombie and not self.outbuffer:
            self._reallyDie()

    async def run(self):
        now = time.time()
        if self.nextReconnectTime is not None and now > self.nextReconnectTime:
            self.reconnect()
        elif self.writeCheckTime is not None and now > self.writeCheckTime:
            self._checkAndWriteOrReconnect()
        if not self.connected:
            return
        await asyncio.gather(
            self._sendIfMsgs(),
            self._read(),
        )

    async def _read(self):
        """Called by _select() when we can read data."""
        loop = asyncio.get_event_loop()
        try:
            new_data = await loop.sock_recv(self.conn, 1024)
            if not new_data:
                # Socket was closed
                self._handleSocketError(None)
                return

            self.inbuffer += new_data
            self.eagains = 0 # If we successfully recv'ed, we can reset this.
            lines = self.inbuffer.split(b'\n')
            self.inbuffer = lines.pop()
            for line in lines:
                if self.irc is not None \
                        and 'UTF8ONLY' in self.irc.state.supported:
                    # No need for the fancy charset-guessing used in
                    # decode_raw_line.
                    try:
                        line = line.decode('utf8')
                    except UnicodeError:
                        drivers.log.exception('Could not decode line %r', line)
                        continue
                else:
                    line = decode_raw_line(line)

                msg = drivers.parseMsg(line)
                if msg is not None and self.irc is not None:
                    # self.irc may be None if this driver is already dead,
                    # see comment in _handleSocketError
                    self.irc.feedMsg(msg)
        except socket.timeout:
            pass
        except SSLError as e:
            if e.args[0] == 'The read operation timed out':
                pass
            else:
                self._handleSocketError(e)
                return
        except socket.error as e:
            self._handleSocketError(e)
            return
        if self.irc and not self.irc.zombie:
            await self._sendIfMsgs()

    def connect(self, **kwargs):
        self.reconnect(reset=False, **kwargs)

    def reconnect(self, wait=False, reset=True, server=None):
        self._attempt += 1
        self.nextReconnectTime = None
        if self.connected:
            self.onDisconnect()
            drivers.log.reconnect(self.irc.network)
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
            if server is not None:
                # Make this server be the next one to be used.
                self.servers.insert(0, server)
            self.scheduleReconnect()
            return
        self.currentServer = server or self._getNextServer()
        network_config = getattr(conf.supybot.networks, self.irc.network)
        if self.currentServer.attempt is None:
            self.currentServer = self.currentServer._replace(attempt=self._attempt)
        else:
            self._attempt = self.currentServer.attempt
        socks_proxy = network_config.socksproxy()
        try:
            if socks_proxy:
                import socks
        except ImportError:
            log.error('Cannot use socks proxy (SocksiPy not installed), '
                    'using direct connection instead.')
            socks_proxy = ''
        if socks_proxy:
            # Do not try to resolve, let the SOCKS proxy do it.
            # (Avoids leaking DNS queries *and* is necessary for onion
            # services)
            address = self.currentServer.hostname
        else:
            try:
                address = utils.net.getAddressFromHostname(
                    self.currentServer.hostname,
                    attempt=self._attempt)
            except (socket.gaierror, socket.error) as e:
                drivers.log.connectError(self.currentServer, e)
                self.scheduleReconnect()
                return
        drivers.log.connect(self.currentServer, socks_proxy=socks_proxy)
        try:
            self.conn = utils.net.getSocket(
                    address,
                    port=self.currentServer.port,
                    socks_proxy=socks_proxy,
                    vhost=conf.supybot.protocols.irc.vhost(),
                    vhostv6=conf.supybot.protocols.irc.vhostv6(),
                    )
        except socket.error as e:
            drivers.log.connectError(self.currentServer, e)
            self.scheduleReconnect()
            return
        # We allow more time for the connect here, since it might take longer.
        # At least 10 seconds.
        try:
            # Connect before SSL, otherwise SSL is disabled if we use SOCKS.
            # See http://stackoverflow.com/q/16136916/539465
            self.conn.connect((address, self.currentServer.port))
            if network_config.ssl() or \
                    self.currentServer.force_tls_verification:
                self.starttls()

            # Suppress this warning for loopback IPs.
            if (not network_config.requireStarttls()) and \
                    (not network_config.ssl()) and \
                    (not self.currentServer.force_tls_verification):

                try:
                    is_loopback = ipaddress.ip_address(address).is_loopback
                except ValueError:
                    # address is a hostname, eg. because we're using a SOCKS
                    # proxy
                    is_loopback = False
                if not is_loopback and not address.endswith('.onion'):
                    drivers.log.warning(('Connection to network %s '
                        'does not use SSL/TLS, which makes it vulnerable to '
                        'man-in-the-middle attacks and passive eavesdropping. '
                        'You should consider upgrading your connection to SSL/TLS '
                        '<http://docs.limnoria.net/en/latest/use/faq.html#how-to-make-a-connection-secure>')
                        % self.irc.network)

            self.connected = True
            self.resetDelay()
        except socket.error as e:
            if len(e.args) >= 1 and e.args[0] == 115:
                # e.args may be () in some circumstances,
                # eg. when e is an instance of socks.GeneralProxyError
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
        drivers.IrcDriver.die(self)
        drivers.ServersMixin.die(self)

    def _reallyDie(self):
        if self.conn is not None:
            self.conn.close()
        drivers.IrcDriver.die(self)
        # self.irc.die() Kill off the ircs yourself, jerk!

    def name(self):
        return '%s(%s)' % (self.__class__.__name__, self.irc)

    def anyCertValidationEnabled(self):
        """Returns whether any kind of certificate validation is enabled, other
        than Server.force_tls_verification."""
        network_config = getattr(conf.supybot.networks, self.irc.network)
        return any([
            conf.supybot.protocols.ssl.verifyCertificates(),
            network_config.ssl.serverFingerprints(),
            network_config.ssl.authorityCertificate(),
        ])

    def starttls(self):
        assert 'ssl' in globals()
        network_config = getattr(conf.supybot.networks, self.irc.network)
        certfile = network_config.certfile()
        if not certfile:
            certfile = conf.supybot.protocols.irc.certfile()
        if not certfile:
            certfile = None
        elif not os.path.isfile(certfile):
            drivers.log.warning('Could not find cert file %s.' %
                    certfile)
            certfile = None
        if self.currentServer.force_tls_verification \
                and not self.anyCertValidationEnabled():
            verifyCertificates = True
        else:
            verifyCertificates = conf.supybot.protocols.ssl.verifyCertificates()
            if not self.currentServer.force_tls_verification \
                    and not self.anyCertValidationEnabled():
                drivers.log.warning('Not checking SSL certificates, connections '
                        'are vulnerable to man-in-the-middle attacks. Set '
                        'supybot.protocols.ssl.verifyCertificates to "true" '
                        'to enable validity checks.')
        try:
            self.conn = utils.net.ssl_wrap_socket(self.conn,
                    logger=drivers.log,
                    hostname=self.currentServer.hostname,
                    certfile=certfile,
                    verify=verifyCertificates,
                    trusted_fingerprints=network_config.ssl.serverFingerprints(),
                    ca_file=network_config.ssl.authorityCertificate(),
                    )
        except ssl.CertificateError as e:
            drivers.log.error(('Certificate validation failed when '
                'connecting to %s: %s\n'
                'This means either someone is doing a man-in-the-middle '
                'attack on your connection, or the server\'s certificate is '
                'not in your trusted fingerprints list.')
                % (self.irc.network, e.args[0]))
            raise ssl.CertificateError('Aborting because of failed certificate '
                    'verification.')



Driver = SocketDriver

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

