###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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

import time

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.utils.structures import MultiSet, TimeoutQueue
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Relay')

class Relay(callbacks.Plugin):
    noIgnore = True
    def __init__(self, irc):
        self.__parent = super(Relay, self)
        self.__parent.__init__(irc)
        self._whois = {}
        self.lastmsg = {}
        self.ircstates = {}
        self.queuedTopics = MultiSet()
        self.lastRelayMsgs = ircutils.IrcDict()

    def __call__(self, irc, msg):
        try:
            irc = self._getRealIrc(irc)
            if irc not in self.ircstates:
                self._addIrc(irc)
            self.ircstates[irc].addMsg(irc, self.lastmsg[irc])
        finally:
            self.lastmsg[irc] = msg
        self.__parent.__call__(irc, msg)

    def do376(self, irc, msg):
        networkGroup = conf.supybot.networks.get(irc.network)
        for channel in self.registryValue('channels'):
            if self.registryValue('channels.joinOnAllNetworks', channel):
                if channel not in irc.state.channels:
                    irc.queueMsg(networkGroup.channels.join(channel))
    do377 = do422 = do376

    def _getRealIrc(self, irc):
        if isinstance(irc, irclib.Irc):
            return irc
        else:
            return irc.getRealIrc()

    def _getIrcName(self, irc):
        # We should allow abbreviations at some point.
        return irc.network

    def _addIrc(self, irc):
        # Let's just be extra-special-careful here.
        if irc not in self.ircstates:
            self.ircstates[irc] = irclib.IrcState()
        if irc not in self.lastmsg:
            self.lastmsg[irc] = ircmsgs.ping('this is just a fake message')
        if irc.afterConnect:
            # We've probably been reloaded.  Let's send some messages to get
            # our IrcState objects up to current.
            for channel in self.registryValue('channels'):
                irc.queueMsg(ircmsgs.who(channel))
                irc.queueMsg(ircmsgs.names(channel))

    @internationalizeDocstring
    def join(self, irc, msg, args, channel):
        """[<channel>]

        Starts relaying between the channel <channel> on all networks.  If on a
        network the bot isn't in <channel>, he'll join.  This commands is
        required even if the bot is in the channel on both networks; he won't
        relay between those channels unless he's told to join both
        channels.  If <channel> is not given, starts relaying on the channel
        the message was sent in.
        """
        self.registryValue('channels').add(channel)
        for otherIrc in world.ircs:
            if channel not in otherIrc.state.channels:
                networkGroup = conf.supybot.networks.get(otherIrc.network)
                otherIrc.queueMsg(networkGroup.channels.join(channel))
        irc.replySuccess()
    join = wrap(join, ['channel', 'admin'])

    @internationalizeDocstring
    def part(self, irc, msg, args, channel):
        """<channel>

        Ceases relaying between the channel <channel> on all networks.  The bot
        will part from the channel on all networks in which it is on the
        channel.
        """
        self.registryValue('channels').discard(channel)
        for otherIrc in world.ircs:
            if channel in otherIrc.state.channels:
                otherIrc.queueMsg(ircmsgs.part(channel))
        irc.replySuccess()
    part = wrap(part, ['channel', 'admin'])

    @internationalizeDocstring
    def nicks(self, irc, msg, args, channel):
        """[<channel>]

        Returns the nicks of the people in the channel on the various networks
        the bot is connected to.  <channel> is only necessary if the message
        isn't sent on the channel itself.
        """
        realIrc = self._getRealIrc(irc)
        if channel not in self.registryValue('channels'):
            irc.error(format('I\'m not relaying in %s.', channel))
            return
        users = []
        for otherIrc in world.ircs:
            network = self._getIrcName(otherIrc)
            ops = []
            halfops = []
            voices = []
            usersS = []
            if network != self._getIrcName(realIrc):
                try:
                    Channel = otherIrc.state.channels[channel]
                except KeyError:
                    users.append(format('(not in %s on %s)',channel,network))
                    continue
                numUsers = 0
                for s in Channel.users:
                    s = s.strip()
                    if not s:
                        continue
                    numUsers += 1
                    if s in Channel.ops:
                        ops.append('@' + s)
                    elif s in Channel.halfops:
                        halfops.append('%' + s)
                    elif s in Channel.voices:
                        voices.append('+' + s)
                    else:
                        usersS.append(s)
                utils.sortBy(ircutils.toLower, ops)
                utils.sortBy(ircutils.toLower, voices)
                utils.sortBy(ircutils.toLower, halfops)
                utils.sortBy(ircutils.toLower, usersS)
                usersS = ', '.join(filter(None, list(map(', '.join,
                                  (ops,halfops,voices,usersS)))))
                users.append(format('%s (%i): %s',
                                    ircutils.bold(network), numUsers, usersS))
        users.sort()
        irc.reply('; '.join(users))
    nicks = wrap(nicks, ['channel'])

    def do311(self, irc, msg):
        irc = self._getRealIrc(irc)
        nick = ircutils.toLower(msg.args[1])
        if (irc, nick) not in self._whois:
            return
        else:
            self._whois[(irc, nick)][-1][msg.command] = msg

    # These are all sent by a WHOIS response.
    do301 = do311
    do312 = do311
    do317 = do311
    do319 = do311
    do320 = do311

    def do318(self, irc, msg):
        irc = self._getRealIrc(irc)
        nick = msg.args[1]
        loweredNick = ircutils.toLower(nick)
        if (irc, loweredNick) not in self._whois:
            return
        (replyIrc, replyMsg, d) = self._whois[(irc, loweredNick)]
        hostmask = '@'.join(d['311'].args[2:4])
        user = d['311'].args[-1]
        if '319' in d:
            channels = d['319'].args[-1].split()
            ops = []
            voices = []
            normal = []
            halfops = []
            for channel in channels:
                if channel.startswith('@'):
                    ops.append(channel[1:])
                elif channel.startswith('%'):
                    halfops.append(channel[1:])
                elif channel.startswith('+'):
                    voices.append(channel[1:])
                else:
                    normal.append(channel)
            L = []
            if ops:
                L.append(format(_('is an op on %L'), ops))
            if halfops:
                L.append(format(_('is a halfop on %L'), halfups))
            if voices:
                L.append(format(_('is voiced on %L'), voices))
            if normal:
                if L:
                    L.append(format(_('is also on %L'), normal))
                else:
                    L.append(format(_('is on %L'), normal))
        else:
            L = [_('isn\'t on any non-secret channels')]
        channels = format('%L', L)
        if '317' in d:
            idle = utils.timeElapsed(d['317'].args[2])
            signon = time.strftime(conf.supybot.reply.format.time(),
                                   time.localtime(float(d['317'].args[3])))
        else:
            idle = _('<unknown>')
            signon = _('<unknown>')
        if '312' in d:
            server = d['312'].args[2]
        else:
            server = _('<unknown>')
        if '301' in d:
            away = format(_('  %s is away: %s.'), nick, d['301'].args[2])
        else:
            away = ''
        if '320' in d:
            if d['320'].args[2]:
                identify = _(' identified')
            else:
                identify = ''
        else:
            identify = ''
        s = format(_('%s (%s) has been%s on server %s since %s (idle for %s) '
                   'and %s.%s'),
                   user, hostmask, identify, server, signon, idle,
                   channels, away)
        replyIrc.reply(s)
        del self._whois[(irc, loweredNick)]

    def do402(self, irc, msg):
        irc = self._getRealIrc(irc)
        nick = msg.args[1]
        loweredNick = ircutils.toLower(nick)
        if (irc, loweredNick) not in self._whois:
            return
        (replyIrc, replyMsg, d) = self._whois[(irc, loweredNick)]
        del self._whois[(irc, loweredNick)]
        s = format(_('There is no %s on %s.'), nick, self._getIrcName(irc))
        replyIrc.reply(s)

    do401 = do402

    def _formatPrivmsg(self, nick, network, msg):
        channel = msg.args[0]
        if self.registryValue('includeNetwork', channel):
            network = '@' + network
        else:
            network = ''
        # colorize nicks
        color = self.registryValue('color', channel) # Also used further down.
        if color:
            nick = ircutils.IrcString(nick)
            newnick = ircutils.mircColor(nick, *ircutils.canonicalColor(nick))
            colors = ircutils.canonicalColor(nick, shift=4)
            nick = newnick
        if ircmsgs.isAction(msg):
            if color:
                t = ircutils.mircColor('*', *colors)
            else:
                t = '*'
            s = format('%s %s%s %s', t, nick, network, ircmsgs.unAction(msg))
        else:
            if color:
                lt = ircutils.mircColor('<', *colors)
                gt = ircutils.mircColor('>', *colors)
            else:
                lt = '<'
                gt = '>'
            s = format('%s%s%s%s %s', lt, nick, network, gt, msg.args[1])
        return s

    def _sendToOthers(self, irc, msg):
        assert msg.command in ('PRIVMSG', 'NOTICE', 'TOPIC')
        for otherIrc in world.ircs:
            if otherIrc != irc and not otherIrc.zombie:
                if msg.args[0] in otherIrc.state.channels:
                    msg.tag('relayedMsg')
                    otherIrc.queueMsg(msg)

    def _checkRelayMsg(self, msg):
        channel = msg.args[0]
        if channel in self.lastRelayMsgs:
            q = self.lastRelayMsgs[channel]
            unformatted = ircutils.stripFormatting(msg.args[1])
            normalized = utils.str.normalizeWhitespace(unformatted)
            for s in q:
                if s in normalized:
                    return True
        return False

    def _punishRelayers(self, msg):
        assert self._checkRelayMsg(msg), 'Punishing without checking.'
        who = msg.prefix
        channel = msg.args[0]
        def notPunishing(irc, s, *args):
            self.log.info('Not punishing %s in %s on %s: %s.',
                          msg.prefix, channel, irc.network, s, *args)
        for irc in world.ircs:
            if channel in irc.state.channels:
                if irc.nick in irc.state.channels[channel].ops:
                    if who in irc.state.channels[channel].bans:
                        notPunishing(irc, 'already banned')
                    else:
                        self.log.info('Punishing %s in %s on %s for relaying.',
                                      who, channel, irc.network)
                        irc.sendMsg(ircmsgs.ban(channel, who))
                        kmsg = _('You seem to be relaying, punk.')
                        irc.sendMsg(ircmsgs.kick(channel, msg.nick, kmsg))
                else:
                    notPunishing(irc, 'not opped')

    def doPrivmsg(self, irc, msg):
        if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
            return
        (channel, text) = msg.args
        if irc.isChannel(channel):
            irc = self._getRealIrc(irc)
            if channel not in self.registryValue('channels'):
                return
            ignores = self.registryValue('ignores', channel)
            for ignore in ignores:
                if ircutils.hostmaskPatternEqual(ignore, msg.prefix):
                    self.log.debug('Refusing to relay %s, ignored by %s.',
                                   msg.prefix, ignore)
                    return
            # Let's try to detect other relay bots.
            if self._checkRelayMsg(msg):
                if self.registryValue('punishOtherRelayBots', channel):
                    self._punishRelayers(msg)
                # Either way, we don't relay the message.
                else:
                    self.log.warning('Refusing to relay message from %s, '
                                     'it appears to be a relay message.',
                                     msg.prefix)
            else:
                network = self._getIrcName(irc)
                s = self._formatPrivmsg(msg.nick, network, msg)
                m = self._msgmaker(channel, s)
                self._sendToOthers(irc, m)

    def _msgmaker(self, target, s):
        msg = dynamic.msg
        channel = dynamic.channel
        if self.registryValue('noticeNonPrivmsgs', dynamic.channel) and \
           msg.command != 'PRIVMSG':
            return ircmsgs.notice(target, s)
        else:
            return ircmsgs.privmsg(target, s)

    def doJoin(self, irc, msg):
        irc = self._getRealIrc(irc)
        channel = msg.args[0]
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        if self.registryValue('hostmasks', channel):
            hostmask = format(' (%s)', msg.prefix.split('!')[1])
        else:
            hostmask = ''
        s = format(_('%s%s has joined on %s'), msg.nick, hostmask, network)
        m = self._msgmaker(channel, s)
        self._sendToOthers(irc, m)

    def doPart(self, irc, msg):
        irc = self._getRealIrc(irc)
        channel = msg.args[0]
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        if self.registryValue('hostmasks', channel):
            hostmask = format(' (%s)', msg.prefix.split('!')[1])
        else:
            hostmask = ''
        if len(msg.args) > 1:
            s = format(_('%s%s has left on %s (%s)'),
                       msg.nick, hostmask, network, msg.args[1])
        else:
            s = format(_('%s%s has left on %s'), msg.nick, hostmask, network)
        m = self._msgmaker(channel, s)
        self._sendToOthers(irc, m)

    def doMode(self, irc, msg):
        irc = self._getRealIrc(irc)
        channel = msg.args[0]
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        s = format(_('mode change by %s on %s: %s'),
                   msg.nick, network, ' '.join(msg.args[1:]))
        m = self._msgmaker(channel, s)
        self._sendToOthers(irc, m)

    def doKick(self, irc, msg):
        irc = self._getRealIrc(irc)
        channel = msg.args[0]
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        if len(msg.args) == 3:
            s = format(_('%s was kicked by %s on %s (%s)'),
                       msg.args[1], msg.nick, network, msg.args[2])
        else:
            s = format(_('%s was kicked by %s on %s'),
                       msg.args[1], msg.nick, network)
        m = self._msgmaker(channel, s)
        self._sendToOthers(irc, m)

    def doNick(self, irc, msg):
        irc = self._getRealIrc(irc)
        newNick = msg.args[0]
        network = self._getIrcName(irc)
        s = format(_('nick change by %s to %s on %s'), msg.nick,newNick,network)
        for channel in self.registryValue('channels'):
            if channel in irc.state.channels:
                if newNick in irc.state.channels[channel].users:
                    m = self._msgmaker(channel, s)
                    self._sendToOthers(irc, m)

    def doTopic(self, irc, msg):
        irc = self._getRealIrc(irc)
        (channel, newTopic) = msg.args
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        if self.registryValue('topicSync', channel):
            m = ircmsgs.topic(channel, newTopic)
            for otherIrc in world.ircs:
                if irc != otherIrc:
                    try:
                        if otherIrc.state.getTopic(channel) != newTopic:
                            if (otherIrc, newTopic) not in self.queuedTopics:
                                self.queuedTopics.add((otherIrc, newTopic))
                                otherIrc.queueMsg(m)
                            else:
                                self.queuedTopics.remove((otherIrc, newTopic))

                    except KeyError:
                        self.log.warning('Not on %s on %s, '
                                         'can\'t sync topics.',
                                         channel, otherIrc.network)
        else:
            s = format(_('topic change by %s on %s: %s'),
                       msg.nick, network, newTopic)
            m = self._msgmaker(channel, s)
            self._sendToOthers(irc, m)

    def doQuit(self, irc, msg):
        irc = self._getRealIrc(irc)
        network = self._getIrcName(irc)
        if msg.args:
            s = format(_('%s has quit %s (%s)'), msg.nick, network, msg.args[0])
        else:
            s = format(_('%s has quit %s.'), msg.nick, network)
        for channel in self.registryValue('channels'):
            if channel in self.ircstates[irc].channels:
                if msg.nick in self.ircstates[irc].channels[channel].users:
                    m = self._msgmaker(channel, s)
                    self._sendToOthers(irc, m)

    def doError(self, irc, msg):
        irc = self._getRealIrc(irc)
        network = self._getIrcName(irc)
        s = format(_('disconnected from %s: %s'), network, msg.args[0])
        for channel in self.registryValue('channels'):
            m = self._msgmaker(channel, s)
            self._sendToOthers(irc, m)

    def outFilter(self, irc, msg):
        irc = self._getRealIrc(irc)
        if msg.command == 'PRIVMSG':
            if msg.relayedMsg:
                self._addRelayMsg(msg)
            else:
                channel = msg.args[0]
                if channel in self.registryValue('channels'):
                    network = self._getIrcName(irc)
                    s = self._formatPrivmsg(irc.nick, network, msg)
                    relayMsg = self._msgmaker(channel, s)
                    self._sendToOthers(irc, relayMsg)
        return msg

    def _addRelayMsg(self, msg):
        channel = msg.args[0]
        if channel in self.lastRelayMsgs:
            q = self.lastRelayMsgs[channel]
        else:
            q = TimeoutQueue(60) # XXX Make this configurable.
            self.lastRelayMsgs[channel] = q
        unformatted = ircutils.stripFormatting(msg.args[1])
        normalized = utils.str.normalizeWhitespace(unformatted)
        q.enqueue(normalized)


Class = Relay

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
