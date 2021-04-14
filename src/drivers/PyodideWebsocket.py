##
# Copyright (c) 2021, Valentin Lorentz
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
Contains an experimental driver, that relies on Pyodide to run in the browser
and connect via WebSocket
"""
import time
import socket
import asyncio
import ipaddress

import js  # Pyodide

from .. import (conf, drivers, log, utils, world)

class SynchronousWebsocket:
    def __init__(self, hostname, port):
        WebSocket = js.WebSocket
        try:
            ipaddress.IPv6Address(hostname)
        except ipaddress.AddressValueError:
            pass # not an IPv6 address
        else:
            hostname = '[%s]' % hostname
        url = 'ws://%s:%d' % (hostname, port)
        self.ws = WebSocket.new(url, 'text.ircv3.net')
        self.ws.onmessage = self._onmessage
        self.ws.onerror = self._onerror
        self.ws.onclose = self._onclose
        self.ws.onopen = self._onopen

        self.inbuffer = []
        self.closed = False
        self.open = False

    def _onmessage(self, event):
        self.inbuffer.append(event.data)

    def _onerror(self, event):
        drivers.log.error("Websocket error: %s", event)

    def _onclose(self, event):
        self.closed = True

    def _onopen(self, event):
        self.open = True

    def send(self, data):
        self.ws.send(data)

    def readmany(self):
        # FIXME: Not thread-safe. Does it matter in a browser?
        lines = self.inbuffer[:]
        self.inbuffer[:] = []
        return lines


class PyodideWebsocketDriver(drivers.IrcDriver, drivers.ServersMixin):
    def __init__(self, irc):
        assert irc is not None
        self.irc = irc
        drivers.IrcDriver.__init__(self, irc)
        drivers.ServersMixin.__init__(self, irc)
        self.nextReconnectTime = None
        self.connected = False
        self._attempt = -1

        self.connect()

    def run(self):
        now = time.time()
        if self.nextReconnectTime is not None and now > self.nextReconnectTime:
            self.reconnect()
        self.connected = not self.conn.closed
        if not self.connected:
            # We sleep here because otherwise, if we're the only driver, we'll
            # spin at 100% CPU while we're disconnected.
            time.sleep(conf.supybot.drivers.poll())
            return

        # Send messages
        if self.conn.open:
            while True:
                msg = self.irc.takeMsg()
                if msg is None:
                    break
                self.conn.send(str(msg))
        else:
            drivers.log.debug('Cannot send messages yet.')

        # Receive messages
        for line in self.conn.readmany():
            msg = drivers.parseMsg(line)
            self.irc.feedMsg(msg)

    def connect(self, **kwargs):
        self.reconnect(reset=False, **kwargs)

    def reconnect(self, wait=False, reset=True, server=None):
        self._attempt += 1
        self.nextReconnectTime = None
        if self.connected:
            self.onDisconnect()
            drivers.log.reconnect(self.irc.network)
            self.conn.close(1000)  # 1000 = Normal closure
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

        drivers.log.connect(self.currentServer)
        try:
            self.conn = SynchronousWebsocket(
                self.currentServer.hostname,
                port=self.currentServer.port,
                )
        except socket.error as e:
            drivers.log.connectError(self.currentServer, e)
            self.scheduleReconnect()
            return

Driver = PyodideWebsocketDriver

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

