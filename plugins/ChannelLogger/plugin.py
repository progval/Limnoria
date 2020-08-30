###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009-2010, James McCoy
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

import os
import sys
import time

import supybot.conf as conf
import supybot.world as world
import supybot.ircdb as ircdb
import supybot.utils as utils
import supybot.irclib as irclib
import supybot.utils.minisix as minisix
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('ChannelLogger')

if minisix.PY2:
    from io import open

class FakeLog(object):
    def flush(self):
        return
    def close(self):
        return
    def write(self, s):
        return

class ChannelLogger(callbacks.Plugin):
    """This plugin allows the bot to log channel conversations to disk."""
    noIgnore = True
    echoMessage = True

    def __init__(self, irc):
        self.__parent = super(ChannelLogger, self)
        self.__parent.__init__(irc)
        self.logs = {}
        self.flusher = self.flush
        world.flushers.append(self.flusher)

        # 10 minutes is long enough to be confident the server won't send
        # messages after they timeouted.
        self._emitted_relayed_msgs = utils.structures.ExpiringDict(10*60)

    def die(self):
        for log in self._logs():
            log.close()
        world.flushers = [x for x in world.flushers if x is not self.flusher]

    def reset(self):
        for log in self._logs():
            log.close()
        self.logs.clear()

    def _logs(self):
        for logs in self.logs.values():
            for log in logs.values():
                yield log

    def flush(self):
        self.checkLogNames()
        for log in self._logs():
            try:
                log.flush()
            except ValueError as e:
                if e.args[0] != 'I/O operation on a closed file':
                    self.log.exception('Odd exception:')

    def logNameTimestamp(self, network, channel):
        format = self.registryValue('filenameTimestamp', channel, network)
        return time.strftime(format)

    def getLogName(self, network, channel):
        if self.registryValue('rotateLogs', channel, network):
            name = '%s.%s.log' % (channel, self.logNameTimestamp(network, channel))
        else:
            name = '%s.log' % channel
        return utils.file.sanitizeName(name)

    def getLogDir(self, irc, channel):
        channel = self.normalizeChannel(irc, channel)
        logDir = conf.supybot.directories.log.dirize(self.name())
        if self.registryValue('directories'):
            if self.registryValue('directories.network'):
                logDir = os.path.join(logDir,  irc.network)
            if self.registryValue('directories.channel'):
                logDir = os.path.join(logDir, utils.file.sanitizeName(channel))
            if self.registryValue('directories.timestamp'):
                format = self.registryValue('directories.timestamp.format')
                timeDir =time.strftime(format)
                logDir = os.path.join(logDir, timeDir)
        if not os.path.exists(logDir):
            os.makedirs(logDir)
        return logDir

    def checkLogNames(self):
        for (irc, logs) in self.logs.items():
            for (channel, log) in list(logs.items()):
                if self.registryValue('rotateLogs', channel, irc.network):
                    name = self.getLogName(irc.network, channel)
                    if name != os.path.basename(log.name):
                        log.close()
                        del logs[channel]

    def getLog(self, irc, channel):
        self.checkLogNames()
        try:
            logs = self.logs[irc]
        except KeyError:
            logs = ircutils.IrcDict()
            self.logs[irc] = logs
        if channel in logs:
            return logs[channel]
        else:
            try:
                name = self.getLogName(irc.network, channel)
                logDir = self.getLogDir(irc, channel)
                log = open(os.path.join(logDir, name), encoding='utf-8', mode='a')
                logs[channel] = log
                return log
            except IOError:
                self.log.exception('Error opening log:')
                return FakeLog()

    def timestamp(self, log):
        format = conf.supybot.log.timestampFormat()
        if format:
            string = time.strftime(format) + '  '
            if minisix.PY2:
                string = string.decode('utf8', 'ignore')
            log.write(string)

    def normalizeChannel(self, irc, channel):
        return ircutils.toLower(channel)

    def doLog(self, irc, channel, s, *args):
        if not self.registryValue('enable', channel, irc.network):
            return
        s = format(s, *args)
        channel = self.normalizeChannel(irc, channel)
        log = self.getLog(irc, channel)
        if self.registryValue('timestamp', channel, irc.network):
            self.timestamp(log)
        if self.registryValue('stripFormatting', channel, irc.network):
            s = ircutils.stripFormatting(s)
        if minisix.PY2:
            s = s.decode('utf8', 'ignore')
        log.write(s)
        if self.registryValue('flushImmediately'):
            log.flush()

    def doPrivmsg(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if irc.isChannel(channel):
                noLogPrefix = self.registryValue('noLogPrefix',
                                                 channel, irc.network)
                cap = ircdb.makeChannelCapability(channel, 'logChannelMessages')
                try:
                    logChannelMessages = ircdb.checkCapability(msg.prefix, cap,
                        ignoreOwner=True)
                except KeyError:
                    logChannelMessages = True
                nick = msg.nick or irc.nick
                rewriteRelayed = self.registryValue('rewriteRelayed',
                                                    channel, irc.network)
                if msg.tagged('ChannelLogger__relayed'):
                    wasRelayed = True
                elif 'label' in msg.server_tags:
                    label = msg.server_tags['label']
                    if label in self._emitted_relayed_msgs:
                        del self._emitted_relayed_msgs[label]
                        wasRelayed = True
                    else:
                        wasRelayed = False
                else:
                    wasRelayed = False

                if rewriteRelayed and wasRelayed:
                    (nick, text) = text.split(' ', 1)
                    nick = nick[1:-1]
                    msg.args = (recipients, text)
                if (noLogPrefix and text.startswith(noLogPrefix)) or \
                        not logChannelMessages:
                    text = '-= THIS MESSAGE NOT LOGGED =-'
                if ircmsgs.isAction(msg):
                    self.doLog(irc, channel,
                               '* %s %s\n', nick, ircmsgs.unAction(msg))
                else:
                    self.doLog(irc, channel, '<%s> %s\n', nick, text)

    def doNotice(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if irc.isChannel(channel):
                self.doLog(irc, channel, '-%s- %s\n', msg.nick, text)

    def doNick(self, irc, msg):
        oldNick = msg.nick
        newNick = msg.args[0]
        for channel in msg.tagged('channels'):
            self.doLog(irc, channel,
                       '*** %s is now known as %s\n', oldNick, newNick)

    def doInvite(self, irc, msg):
        (target, channel) = msg.args
        self.doLog(irc, channel,
                   '*** %s <%s> invited %s to %s\n',
                   msg.nick, msg.prefix, target, channel)

    def doJoin(self, irc, msg):
        for channel in msg.args[0].split(','):
            if(self.registryValue('showJoinParts', channel, irc.network)):
                self.doLog(irc, channel,
                           '*** %s <%s> has joined %s\n',
                           msg.nick, msg.prefix, channel)

    def doKick(self, irc, msg):
        if len(msg.args) == 3:
            (channel, target, kickmsg) = msg.args
        else:
            (channel, target) = msg.args
            kickmsg = ''
        if kickmsg:
            self.doLog(irc, channel,
                       '*** %s was kicked by %s (%s)\n',
                       target, msg.nick, kickmsg)
        else:
            self.doLog(irc, channel,
                       '*** %s was kicked by %s\n', target, msg.nick)

    def doPart(self, irc, msg):
        if len(msg.args) > 1:
            reason = " (%s)" % msg.args[1]
        else:
            reason = ""
        for channel in msg.args[0].split(','):
            if(self.registryValue('showJoinParts', channel, irc.network)):
                self.doLog(irc, channel,
                           '*** %s <%s> has left %s%s\n',
                           msg.nick, msg.prefix, channel, reason)

    def doMode(self, irc, msg):
        channel = msg.args[0]
        if irc.isChannel(channel) and msg.args[1:]:
            self.doLog(irc, channel,
                       '*** %s sets mode: %s %s\n',
                       msg.nick or msg.prefix, msg.args[1],
                        ' '.join(msg.args[2:]))

    def doTopic(self, irc, msg):
        if len(msg.args) == 1:
            return # It's an empty TOPIC just to get the current topic.
        channel = msg.args[0]
        self.doLog(irc, channel,
                   '*** %s changes topic to "%s"\n', msg.nick, msg.args[1])

    def doQuit(self, irc, msg):
        if len(msg.args) == 1:
            reason = " (%s)" % msg.args[0]
        else:
            reason = ""
        for channel in msg.tagged('channels'):
            if(self.registryValue('showJoinParts', channel, irc.network)):
                self.doLog(irc, channel,
                           '*** %s <%s> has quit IRC%s\n',
                           msg.nick, msg.prefix, reason)

    def outFilter(self, irc, msg):
        # Mark/remember outgoing relayed messages, so we can rewrite them if
        # rewriteRelayed is True.
        if msg.command in ('PRIVMSG', 'NOTICE'):
            rewriteRelayed = self.registryValue(
                'rewriteRelayed', msg.channel, irc.network)
            if rewriteRelayed and  'echo-message' in irc.state.capabilities_ack:
                assert 'labeled-response' in irc.state.capabilities_ack, \
                    'echo-message was negotiated without labeled-response.'
                # If we negotiated the echo-message cap, we have to remember
                # this message was relayed when the server sends it back to us.
                if 'label' not in msg.server_tags:
                    msg.server_tags['label'] = ircutils.makeLabel()
                if msg.tagged('relayedMsg'):
                    # Remember this was a relayed message, in case
                    # rewriteRelayed is True.
                    self._emitted_relayed_msgs[msg.server_tags['label']] = True
            else:
                # Else, we can simply rely on internal tags, because echos are
                # simulated.
                if msg.tagged('relayedMsg'):
                    msg.tag('ChannelLogger__relayed')
        return msg


Class = ChannelLogger
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
