#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

__revision__ = "$Id$"

import supybot.fix as fix

import sys
import time
import socket
import asyncore
import asynchat

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.drivers as drivers
import supybot.schedule as schedule

class AsyncoreRunnerDriver(drivers.IrcDriver):
    def run(self):
        try:
            timeout = conf.supybot.drivers.poll()
            if not asyncore.socket_map:
                # asyncore should take care of this... but it doesn't?
                time.sleep(timeout)
            else:
                asyncore.poll(timeout)
        except:
            drivers.log.exception('Uncaught exception:')


class AsyncoreDriver(asynchat.async_chat, drivers.ServersMixin):
    def __init__(self, irc, servers=()):
        asynchat.async_chat.__init__(self)
        drivers.ServersMixin.__init__(self, irc, servers=servers)
        self.irc = irc
        self.irc.driver = self # Necessary because of the way we reconnect.
        self.buffer = ''
        self.set_terminator('\n')
        try:
            server = self._getNextServer()
            sock = utils.getSocket(server[0])
            self.set_socket(sock)
            drivers.log.connect(self.currentServer)
            self.connect(server)
        except socket.error, e:
            drivers.log.connectError(self.currentServer, e)
            self.reconnect(wait=True)

    def _scheduleReconnect(self, at=60):
        when = time.time() + at
        if not world.dying:
            drivers.log.reconnect(self.irc.network, when)
        def makeNewDriver():
            self.irc.reset()
            self.scheduled = None
            driver = self.__class__(self.irc, servers=self.servers)
        self.scheduled = schedule.addEvent(makeNewDriver, when)

    def writable(self):
        while self.connected:
            m = self.irc.takeMsg()
            if m:
                self.push(str(m))
            else:
                break
        return asynchat.async_chat.writable(self)

    def handle_error(self):
        self.handle_close()

    def collect_incoming_data(self, s):
        self.buffer += s

    def found_terminator(self):
        start = time.time()
        msg = drivers.parseMsg(self.buffer)
        self.buffer = ''
        if msg is not None:
            self.irc.feedMsg(msg)

    def handle_close(self, wait=True):
        if not wait:
            self._scheduleReconnect(at=0)
        else:
            self._scheduleReconnect()
        if self.socket is not None:
            self.close()
    reconnect = handle_close

    def handle_connect(self):
        pass

    def die(self):
        if self.scheduled:
            schedule.removeEvent(self.scheduled)
        drivers.log.die(self.irc)
        self.reconnect()

try:
    ignore(poller)
except NameError:
    poller = AsyncoreRunnerDriver()

Driver = AsyncoreDriver


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
