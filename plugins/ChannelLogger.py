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
Logs each channel to its own individual logfile.
"""

from baseplugin import *

import time
from cStringIO import StringIO

import conf
import debug
import world
import irclib
import ircmsgs
import ircutils

###
# Logger: Handles logging of IRC channels to files.
###
class ChannelLogger(irclib.IrcCallback):
    logs = ircutils.IrcDict()
    def __init__(self):
        self.laststate = irclib.IrcState()
        self.lastMsg = None
        world.flushers.append(self.flush)

    def __call__(self, irc, msg):
        super(self.__class__, self).__call__(irc, msg)
        #self.__class__.__bases__[0].__call__(self, irc, msg)
        if self.lastMsg:
            self.laststate.addMsg(irc, self.lastMsg)
        self.lastMsg = msg

    def reset(self):
        for log in self.logs.itervalues():
            log.close()
        self.logs = ircutils.IrcDict()

    def flush(self):
        for log in self.logs.itervalues():
            log.flush()

    def getLog(self, channel):
        if channel in self.logs:
            return self.logs[channel]
        else:
            try:
                log = file(os.path.join(conf.logDir, '%s.log' % channel), 'a')
                self.logs[channel] = log
                return log
            except IOError:
                debug.recoverableException()
                return StringIO()

    def timestamp(self, log):
        log.write(time.strftime(conf.logTimestampFormat))
        log.write('  ')

    def doPrivmsg(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if ircutils.isChannel(channel):
                log = self.getLog(channel)
                self.timestamp(log)
                nick = msg.nick or irc.nick
                if ircmsgs.isAction(msg):
                    log.write('* %s %s\n' % (nick, ircmsgs.unAction(msg)))
                else:
                    log.write('<%s> %s\n' % (nick, text))

    def doNotice(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if ircutils.isChannel(channel):
                log = self.getLog(channel)
                self.timestamp(log)
                log.write('-%s- %s\n' % (msg.nick, text))

    def doJoin(self, irc, msg):
        for channel in msg.args[0].split(','):
            log = self.getLog(channel)
            self.timestamp(log)
            log.write('*** %s has joined %s\n' %\
                      (msg.nick or msg.prefix, channel))

    def doKick(self, irc, msg):
        (channel, target, kickmsg) = msg.args
        log = self.getLog(channel)
        self.timestamp(log)
        log.write('*** %s was kicked by %s (%s)\n' % \
                  (target, msg.nick, kickmsg))

    def doPart(self, irc, msg):
        for channel in msg.args[0].split(','):
            log = self.getLog(channel)
            self.timestamp(log)
            log.write('*** %s has left %s\n' % (msg.nick, channel))

    def doMode(self, irc, msg):
        channel = msg.args[0]
        if ircutils.isChannel(channel):
            log = self.getLog(channel)
            self.timestamp(log)
            log.write('*** %s sets mode: %s %s\n' % \
                      (msg.nick or msg.prefix, msg.args[1],
                       ' '.join(msg.args[2:])))

    def doTopic(self, irc, msg):
        channel = msg.args[0]
        log = self.getLog(channel)
        self.timestamp(log)
        log.write('*** %s changes topic to "%s"\n' % (msg.nick, msg.args[1]))

    def doQuit(self, irc, msg):
        for (channel, chan) in self.laststate.channels.iteritems():
            if msg.nick in chan.users:
                log = self.getLog(channel)
                log.write('*** %s has quit IRC\n' % msg.nick)

    def outFilter(self, irc, msg):
        # Gotta catch my own messages *somehow* :)
        # Let's try this little trick...
        m = ircmsgs.IrcMsg(msg=msg, prefix=irc.prefix)
        self(irc, m)
        return msg


Class = ChannelLogger
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
