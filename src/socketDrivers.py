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

from __future__ import division

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
    def __init__(self, (server, port), irc, reconnectWaits=(0, 60, 300)):
        global instances
        instances += 1
        conf.poll = originalPoll / instances
        self.server = (server, port)
        drivers.IrcDriver.__init__(self) # Must come after server is set.
        self.irc = irc
        self.irc.driver = self
        self.inbuffer = ''
        self.outbuffer = ''
        self.connected = False
        self.reconnectWaitsIndex = 0
        self.reconnectWaits = reconnectWaits
        self.reconnect()

    def _sendIfMsgs(self):
        #debug.methodNamePrintf(self, '_sendIfMsgs')
        msgs = [self.irc.takeMsg()]
        while msgs[-1] is not None:
            msgs.append(self.irc.takeMsg())
        del msgs[-1]
        self.outbuffer += ''.join(map(str, msgs))
        if self.outbuffer:
            try:
                sent = self.conn.send(self.outbuffer)
                self.outbuffer = self.outbuffer[sent:]
            except socket.error, e:
                # (11, 'Resource temporarily unavailable') raised if connect
                # hasn't finished yet.
                if e.args[0] != 11:
                    s = 'Disconnect from %s: %s' % (self.server, e.args[1])
                    debug.msg(s, 'normal')
                    self.die()
        
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
                start = time.time()
                msg = ircmsgs.IrcMsg(line)
                debug.msg('Time to parse IrcMsg: %s' % (time.time()-start),
                          'verbose')
                try:
                    self.irc.feedMsg(msg)
                except:
                    debug.msg('Exception caught outside Irc object.', 'normal')
                    debug.recoverableException()
        except socket.timeout:
            pass
        except socket.error, e:
            # Same as with _sendIfMsgs.
            if e.args[0] != 11:
                s = 'Disconnect from %s: %s' % (self.server, e.args[1])
                debug.msg(s, 'normal')
                self.die()
            return
        self._sendIfMsgs()
        
    def reconnect(self):
        #debug.methodNamePrintf(self, 'reconnect')
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.settimeout(conf.poll)
        if self.reconnectWaitsIndex < len(self.reconnectWaits)-1:
            self.reconnectWaitsIndex += 1
        try:
            self.conn.connect(self.server)
        except socket.error, e:
            if e.args[0] != 115:
                debug.msg('Error connecting to %s: %s' % (self.server, e))
                self.die()
        self.connected = True
        self.reconnectWaitPeriodsIndex = 0
        

    def die(self):
        #debug.methodNamePrintf(self, 'die')
        self.irc.reset()
        self.conn.close()
        self.connected = False
        when = time.time() + self.reconnectWaits[self.reconnectWaitsIndex]
        whenS = time.strftime(conf.logTimestampFormat, time.localtime(when))
        debug.msg('Scheduling reconnect to %s at %s' % (self.server, whenS),
                  'normal')
        schedule.addEvent(self.reconnect, when)

    def name(self):
        return '%s%s' % (self.__class__.__name__, self.server)


Driver = SocketDriver

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

