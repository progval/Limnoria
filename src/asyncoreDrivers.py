#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

import fix

import re
import sys
import time
import socket
import asyncore
import asynchat

import log
import conf
import ircdb
import world
import drivers
import ircmsgs
import schedule

class AsyncoreRunnerDriver(drivers.IrcDriver):
    def run(self):
        #log.debug(repr(asyncore.socket_map))
        try:
            asyncore.poll(conf.supybot.drivers.poll())
        except:
            log.exception('Uncaught exception:')


class AsyncoreDriver(asynchat.async_chat, object):
    def __init__(self, (server, port), irc):
        asynchat.async_chat.__init__(self)
        self.server = (server, port)
        self.irc = irc
        self.irc.driver = self
        self.buffer = ''
        self.set_terminator('\n')
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.connect(self.server)
        except socket.error, e:
            log.warning('Error connecting to %s: %s', self.server[0], e)
            self.reconnect(wait=True)

    def scheduleReconnect(self):
        when = log.timestamp(time.time()+60)
        if not world.dying:
            log.info('Scheduling reconnect to %s at %s', self.server[0], when)
        def makeNewDriver():
            self.irc.reset()
            driver = self.__class__(self.server, self.irc)
        schedule.addEvent(makeNewDriver, when)

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
        msg = ircmsgs.IrcMsg(self.buffer)
        #log.debug('Time to parse IrcMsg: %s', time.time()-start)
        self.buffer = ''
        self.irc.feedMsg(msg)

    def handle_close(self):
        self.scheduleReconnect()
        self.die()
    reconnect = handle_close

    def handle_connect(self):
        pass

    def die(self):
        log.info('Driver for %s dying.', self.irc)
        self.close()

try:
    ignore(poller)
except NameError:
    poller = AsyncoreRunnerDriver()

Driver = AsyncoreDriver


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
