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

__revision__ = "$Id$"

import plugins

import time
from cStringIO import StringIO

import os
import conf
import world
import irclib
import ircmsgs
import ircutils
import registry
import callbacks

conf.registerPlugin('ChannelLogger')
conf.registerGlobalValue(conf.supybot.plugins.ChannelLogger,
    'flushImmediately', registry.Boolean(False, """Determines whether channel
    logfiles will be flushed anytime they're written to, rather than being
    buffered by the operating system."""))
conf.registerChannelValue(conf.supybot.plugins.ChannelLogger, 'timestamp',
    registry.Boolean(True, """Determines whether the logs for this channel are
    timestamped with the timestamp in supybot.log.timestampFormat."""))
conf.registerChannelValue(conf.supybot.plugins.ChannelLogger, 'noLogPrefix',
    registry.String('[nolog]', """Determines what string a message should be
    prefixed with in order not to be logged.  If you don't want any such
    prefix, just set it to the empty string."""))

class ChannelLogger(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.lastMsg = None
        self.laststate = None
        self.logs = ircutils.IrcDict()
        world.flushers.append(self.flush)

    def die(self):
        for log in self.logs.itervalues():
            log.close()
        if self.flush in world.flushers:
            world.flushers.remove(self.flush)

    def __call__(self, irc, msg):
        try:
            super(self.__class__, self).__call__(irc, msg)
            if self.lastMsg:
                self.laststate.addMsg(irc, self.lastMsg)
            else:
                self.laststate = irc.state.copy()
        finally:
            # We must make sure this always gets updated.
            self.lastMsg = msg

    def reset(self):
        for log in self.logs.itervalues():
            log.close()
        self.logs = ircutils.IrcDict()

    def flush(self):
        try:
            for log in self.logs.itervalues():
                log.flush()
        except ValueError, e:
            if e.args[0] != 'I/O operation on a closed file':
                self.log.exception('Odd exception:')

    def getLog(self, channel):
        if channel in self.logs:
            return self.logs[channel]
        else:
            try:
                logDir = conf.supybot.directories.log()
                log = file(os.path.join(logDir, '%s.log' % channel), 'a')
                self.logs[channel] = log
                return log
            except IOError:
                self.log.exception('Error opening log:')
                return StringIO()

    def timestamp(self, log):
        format = conf.supybot.log.timestampFormat()
        if format:
            log.write(time.strftime(format))
            log.write('  ')

    def doLog(self, channel, s):
        log = self.getLog(channel)
        if self.registryValue('timestamp', channel):
            self.timestamp(log)
        log.write(s)
        if self.registryValue('flushImmediately'):
            log.flush()

    def doPrivmsg(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            noLogPrefix = self.registryValue('noLogPrefix', channel)
            if noLogPrefix and text.startswith(noLogPrefix):
                text = '-= THIS MESSAGE NOT LOGGED =-'
            if ircutils.isChannel(channel):
                nick = msg.nick or irc.nick
                if ircmsgs.isAction(msg):
                    self.doLog(channel,
                               '* %s %s\n' % (nick, ircmsgs.unAction(msg)))
                else:
                    self.doLog(channel, '<%s> %s\n' % (nick, text))

    def doNotice(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if ircutils.isChannel(channel):
                self.doLog(channel, '-%s- %s\n' % (msg.nick, text))

    def doJoin(self, irc, msg):
        for channel in msg.args[0].split(','):
            self.doLog(channel,
                       '*** %s has joined %s\n' %
                       (msg.nick or msg.prefix, channel))

    def doKick(self, irc, msg):
        if len(msg.args) == 3:
            (channel, target, kickmsg) = msg.args
        else:
            (channel, target) = msg.args
            kickmsg = ''
        if kickmsg:
            self.doLog(channel,
                       '*** %s was kicked by %s (%s)\n' %
                       (target, msg.nick, kickmsg))
        else:
            self.doLog(channel,
                       '*** %s was kicked by %s\n' % (target, msg.nick))

    def doPart(self, irc, msg):
        for channel in msg.args[0].split(','):
            self.doLog(channel, '*** %s has left %s\n' % (msg.nick, channel))

    def doMode(self, irc, msg):
        channel = msg.args[0]
        if ircutils.isChannel(channel) and msg.args[1:]:
            self.doLog(channel,
                       '*** %s sets mode: %s %s\n' %
                       (msg.nick or msg.prefix, msg.args[1],
                        ' '.join(msg.args[2:])))

    def doTopic(self, irc, msg):
        if len(msg.args) == 1:
            return # It's an empty TOPIC just to get the current topic.
        channel = msg.args[0]
        self.doLog(channel,
                   '*** %s changes topic to "%s"\n' % (msg.nick, msg.args[1]))

    def doQuit(self, irc, msg):
        for (channel, chan) in self.laststate.channels.iteritems():
            if msg.nick in chan.users:
                self.doLog(channel, '*** %s has quit IRC\n' % msg.nick)

    def outFilter(self, irc, msg):
        # Gotta catch my own messages *somehow* :)
        # Let's try this little trick...
        if msg.command != 'PART':
            m = ircmsgs.IrcMsg(msg=msg, prefix=irc.prefix)
            self(irc, m)
        return msg


Class = ChannelLogger
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
