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
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

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
conf.registerChannelValue(conf.supybot.plugins.ChannelLogger,
    'includeNetworkName', registry.Boolean(True, """Determines whether the bot
    will include the name of the network in the filename for channel logs.
    Since this is a channel-specific value, you can override for any channel.
    You almost certainly want this to be True if you're relaying in a given
    channel."""))
conf.registerChannelValue(conf.supybot.plugins.ChannelLogger, 'rotateLogs',
    registry.Boolean(False, """Determines whether the bot will automatically
    rotate the logs for this channel."""))
conf.registerChannelValue(conf.supybot.plugins.ChannelLogger,
    'filenameTimestamp', registry.String('%d-%a-%Y', """Determines how to
    represent the timestamp used for the filename in rotated logs.  When this
    timestamp changes, the old logfiles will be closed and a new one started.
    The format characters for the timestamp are in the time.strftime docs at
    python.org.  In order for your logs to be rotated, you'll also have to
    enable supybot.plugins.ChannelLogger.rotateLogs."""))

class FakeLog(object):
    def flush(self):
        return
    def close(self):
        return
    def write(self, s):
        return

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
        world.flushers = [x for x in world.flushers
                          if hasattr(x, 'im_class') and x.im_class == self]

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
        self.logs.clear()

    def flush(self):
        self.checkLogNames()
        try:
            for log in self.logs.itervalues():
                log.flush()
        except ValueError, e:
            if e.args[0] != 'I/O operation on a closed file':
                self.log.exception('Odd exception:')

    def logNameTimestamp(self, channel):
        format = self.registryValue('filenameTimestamp', channel)
        return time.strftime(format)

    def getLogName(self, channel):
        if self.registryValue('rotateLogs', channel):
            return '%s.%s.log' % (channel, self.logNameTimestamp(channel))
        else:
            return '%s.log' % channel

    def checkLogNames(self):
        for (channel, log) in self.logs.items():
            if self.registryValue('rotateLogs', channel):
                name = self.getLogName(channel)
                if name != log.name:
                    log.close()
                    del self.logs[channel]

    def getLog(self, channel):
        self.checkLogNames()
        if channel in self.logs:
            return self.logs[channel]
        else:
            try:
                logDir = conf.supybot.directories.log()
                name = self.getLogName(channel)
                log = file(os.path.join(logDir, name), 'a')
                self.logs[channel] = log
                return log
            except IOError:
                self.log.exception('Error opening log:')
                return FakeLog()

    def timestamp(self, log):
        format = conf.supybot.log.timestampFormat()
        if format:
            log.write(time.strftime(format))
            log.write('  ')

    def normalizeChannel(self, irc, channel):
        channel = channel.replace('.', ',')
        if self.registryValue('includeNetworkName', channel):
            channel = '%s@%s' % (channel, irc.network)
        return ircutils.toLower(channel)

    def doLog(self, irc, channel, s):
        channel = self.normalizeChannel(irc, channel)
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
                    self.doLog(irc, channel,
                               '* %s %s\n' % (nick, ircmsgs.unAction(msg)))
                else:
                    self.doLog(irc, channel, '<%s> %s\n' % (nick, text))

    def doNotice(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if ircutils.isChannel(channel):
                self.doLog(irc, channel, '-%s- %s\n' % (msg.nick, text))

    def doJoin(self, irc, msg):
        for channel in msg.args[0].split(','):
            self.doLog(irc, channel,
                       '*** %s has joined %s\n' %
                       (msg.nick or msg.prefix, channel))

    def doKick(self, irc, msg):
        if len(msg.args) == 3:
            (channel, target, kickmsg) = msg.args
        else:
            (channel, target) = msg.args
            kickmsg = ''
        if kickmsg:
            self.doLog(irc, channel,
                       '*** %s was kicked by %s (%s)\n' %
                       (target, msg.nick, kickmsg))
        else:
            self.doLog(irc, channel,
                       '*** %s was kicked by %s\n' % (target, msg.nick))

    def doPart(self, irc, msg):
        for channel in msg.args[0].split(','):
            self.doLog(irc, channel,
                       '*** %s has left %s\n' % (msg.nick, channel))

    def doMode(self, irc, msg):
        channel = msg.args[0]
        if ircutils.isChannel(channel) and msg.args[1:]:
            self.doLog(irc, channel,
                       '*** %s sets mode: %s %s\n' %
                       (msg.nick or msg.prefix, msg.args[1],
                        ' '.join(msg.args[2:])))

    def doTopic(self, irc, msg):
        if len(msg.args) == 1:
            return # It's an empty TOPIC just to get the current topic.
        channel = msg.args[0]
        self.doLog(irc, channel,
                   '*** %s changes topic to "%s"\n' % (msg.nick, msg.args[1]))

    def doQuit(self, irc, msg):
        for (channel, chan) in self.laststate.channels.iteritems():
            if msg.nick in chan.users:
                self.doLog(irc, channel, '*** %s has quit IRC\n' % msg.nick)

    def outFilter(self, irc, msg):
        # Gotta catch my own messages *somehow* :)
        # Let's try this little trick...
        if msg.command != 'PART':
            m = ircmsgs.IrcMsg(msg=msg, prefix=irc.prefix)
            self(irc, m)
        return msg


Class = ChannelLogger
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
