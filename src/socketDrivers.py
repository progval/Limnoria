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

"""
Contains simple socket drivers.  Asyncore bugged (haha, pun!) me.
"""

from fix import *

import time
import socket

import conf
import debug
import drivers
import ircmsgs
import schedule

instances = 0
originalPoll = conf.poll

class SocketDriver(drivers.IrcDriver):
    def __init__(self, (server, port), irc):
        global instances
        instances += 1
        conf.poll = originalPoll / instances
        drivers.IrcDriver.__init__(self)
        self.server = (server, port)
        self.irc = irc
        self.irc.driver = self
        self.inbuffer = ''
        self.outbuffer = ''
        self.connected = False
        self.reconnect()

    def _sendIfMsgs(self):
        #debug.methodNamePrintf(self, '_sendIfMsgs')
        msgs = [self.irc.takeMsg()]
        while msgs[-1] is not None:
            msgs.append(self.irc.takeMsg())
        del msgs[-1]
        for msg in msgs:
            msg.prefix = ''
            msg._str = None
        self.outbuffer += ''.join(map(str, msgs))
        if self.outbuffer:
            sent = self.conn.send(self.outbuffer)
            self.outbuffer = self.outbuffer[sent:]
        
    def run(self):
        #debug.methodNamePrintf(self, 'run')
        if not self.connected:
            time.sleep(conf.poll) # Otherwise we might spin.
            return
        self._sendIfMsgs()
        try:
            self.inbuffer += self.conn.recv(1024)
            lines = self.inbuffer.split('\n')
            self.inbuffer = lines.pop()
            for line in lines:
                msg = ircmsgs.IrcMsg(line)
                self.irc.feedMsg(msg)
        except socket.timeout:
            pass
        self._sendIfMsgs()
        
    def reconnect(self):
        #debug.methodNamePrintf(self, 'reconnect')
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.settimeout(conf.poll)
        self.conn.connect(self.server)
        self.connected = True

    def die(self):
        #debug.methodNamePrintf(self, 'die')
        self.conn.close()
        self.connected = False
        schedule.addEvent(self.reconnect, time.time()+300)


Driver = SocketDriver

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

