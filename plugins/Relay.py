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

"""
Handles relaying between networks.
"""

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import supybot.plugins as plugins

import re
import sys
import copy
import time
from itertools import imap, ifilter

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.irclib as irclib
import supybot.drivers as drivers
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks
from supybot.structures import RingBuffer

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Relay', True)
    if yn('Would you like to relay between any channels?'):
        channels = anything('What channels?  Separated them by spaces.')
        conf.supybot.plugins.Relay.channels.set(channels)
    if yn('Would you like to use color to distinguish between nicks?'):
        conf.supybot.plugins.Relay.color.setValue(True)
    output("""Right now there's no way to configure the actual connection to
    the server.  What you'll need to do when the bot finishes starting up is
    use the 'start' command followed by the 'connect' command.  Use the 'help'
    command to see how these two commands should be used.""")

class Networks(registry.SpaceSeparatedListOf):
    List = ircutils.IrcSet
    Value = registry.String

conf.registerPlugin('Relay')
conf.registerChannelValue(conf.supybot.plugins.Relay, 'color',
    registry.Boolean(False, """Determines whether the bot will color relayed
    PRIVMSGs so as to make the messages easier to read."""))
conf.registerChannelValue(conf.supybot.plugins.Relay, 'topicSync',
    registry.Boolean(True, """Determines whether the bot will synchronize
    topics between networks in the channels it relays."""))
conf.registerChannelValue(conf.supybot.plugins.Relay, 'hostmasks',
    registry.Boolean(False, """Determines whether the bot will relay the
    hostmask of the person joining or parting the channel when he or she joins
    or parts."""))
conf.registerChannelValue(conf.supybot.plugins.Relay, 'includeNetwork',
    registry.Boolean(True, """Determines whether the bot will include the
    network in relayed PRIVMSGs; if you're only relaying between two networks,
    it's somewhat redundant, and you may wish to save the space."""))
conf.registerChannelValue(conf.supybot.plugins.Relay, 'detectOtherRelayBots',
    registry.Boolean(False, """Determines whether the bot will detect other
    bots relaying and respond by kickbanning them."""))
conf.registerGlobalValue(conf.supybot.plugins.Relay, 'channels',
    conf.SpaceSeparatedSetOfChannels([], """Determines which channels the bot
    will relay in."""))

class Relay(callbacks.Privmsg):
    noIgnore = True
    priority = sys.maxint
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self._whois = {}
        self.relayedMsgs = {}
        self.lastmsg = {}
        self.ircstates = {}
        self.last20Privmsgs = ircutils.IrcDict()

    def __call__(self, irc, msg):
        try:
            irc = self._getRealIrc(irc)
            if irc not in self.ircstates:
                self._addIrc(irc)
            self.ircstates[irc].addMsg(irc, self.lastmsg[irc])
        finally:
            self.lastmsg[irc] = msg
        callbacks.Privmsg.__call__(self, irc, msg)

    def do376(self, irc, msg):
        L = []
        for channel in self.registryValue('channels'):
            if channel not in irc.state.channels:
                L.append(channel)
        if L:
            irc.queueMsg(ircmsgs.joins(L))
    do377 = do422 = do376

    def _getRealIrc(self, irc):
        if isinstance(irc, irclib.Irc):
            return irc
        else:
            return irc.getRealIrc()

    def _getIrc(self, name):
        for irc in world.ircs:
            if self._getIrcName(irc) == name:
                return irc
        raise KeyError, name

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

    def join(self, irc, msg, args):
        """<channel>

        Starts relaying between the channel <channel> on all networks.  If on a
        network the bot isn't in <channel>, he'll join.  This commands is
        required even if the bot is in the channel on both networks; he won't
        relay between those channels unless he's told to join both
        channels.
        """
        channel = privmsgs.getArgs(args)
        if not ircutils.isChannel(channel):
            irc.error('%r is not a valid channel.' % channel)
            return
        self.registryValue('channels').add(channel)
        for otherIrc in world.ircs: # Should we abstract this?
            if channel not in otherIrc.state.channels:
                otherIrc.queueMsg(ircmsgs.join(channel))
        irc.replySuccess()
    join = privmsgs.checkCapability(join, 'owner')

    def part(self, irc, msg, args):
        """<channel>

        Ceases relaying between the channel <channel> on all networks.  The bot
        will part from the channel on all networks in which it is on the
        channel.
        """
        channel = privmsgs.getArgs(args)
        if not ircutils.isChannel(channel):
            irc.error('%r is not a valid channel.' % channel)
            return
        self.registryValue('channels').remove(channel)
        for otherIrc in world.ircs:
            if channel in otherIrc.state.channels:
                otherIrc.queueMsg(ircmsgs.part(channel))
        irc.replySuccess()
    part = privmsgs.checkCapability(part, 'owner')

    def command(self, irc, msg, args):
        """<network> <command> [<arg> ...]

        Gives the bot <command> (with its associated <arg>s) on <network>.
        """
        if len(args) < 2:
            raise callbacks.ArgumentError
        network = args.pop(0)
        try:
            otherIrc = self._getIrc(network)
        except KeyError:
            irc.error('I\'m not currently on the network %r.' % network)
            return
        Owner = irc.getCallback('Owner')
        Owner.disambiguate(irc, args)
        self.Proxy(otherIrc, msg, args)
    command = privmsgs.checkCapability(command, 'admin')

    def nicks(self, irc, msg, args):
        """[<channel>]

        Returns the nicks of the people in the channel on the various networks
        the bot is connected to.  <channel> is only necessary if the message
        isn't sent on the channel itself.
        """
        realIrc = self._getRealIrc(irc)
        channel = privmsgs.getChannel(msg, args)
        if channel not in self.registryValue('channels'):
            irc.error('I\'m not relaying in %s.' % channel)
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
                    s = 'Somehow I\'m not in %s on %s.'% (channel, network)
                    irc.error(s)
                    return
                numUsers = 0
                for s in Channel.users:
                    s = s.strip()
                    if not s:
                        continue
                    numUsers += 1
                    if s in Channel.ops:
                        ops.append('@%s' % s)
                    elif s in Channel.halfops:
                        halfops.append('%%%s' % s)
                    elif s in Channel.voices:
                        voices.append('+%s' % s)
                    else:
                        usersS.append(s)
                utils.sortBy(ircutils.toLower, ops)
                utils.sortBy(ircutils.toLower, voices)
                utils.sortBy(ircutils.toLower, halfops)
                utils.sortBy(ircutils.toLower, usersS)
                usersS = ', '.join(ifilter(None, imap(', '.join,
                                  (ops,halfops,voices,usersS))))
                users.append('%s (%s): %s' %
                             (ircutils.bold(network), numUsers, usersS))
        users.sort()
        irc.reply('; '.join(users))

    def whois(self, irc, msg, args):
        """<nick>@<network>

        Returns the WHOIS response <network> gives for <nick>.
        """
        nickAtNetwork = privmsgs.getArgs(args)
        realIrc = self._getRealIrc(irc)
        try:
            (nick, network) = nickAtNetwork.split('@', 1)
            if not ircutils.isNick(nick):
                irc.error('%s is not an IRC nick.' % nick)
                return
            nick = ircutils.toLower(nick)
        except ValueError: # If split doesn't work, we get an unpack error.
            if len(world.ircs) == 2:
                # If there are only two networks being relayed, we can safely
                # pick the *other* one.
                nick = ircutils.toLower(nickAtNetwork)
                for otherIrc in world.ircs:
                    if otherIrc != realIrc:
                        network = self._getIrcName(otherIrc)
            else:
                raise callbacks.ArgumentError
        try:
            otherIrc = self._getIrc(network)
        except KeyError:
            irc.error('I\'m not on that network.')
            return
        otherIrc.queueMsg(ircmsgs.whois(nick, nick))
        self._whois[(otherIrc, nick)] = (irc, msg, {})

    def ignore(self, irc, msg, args):
        """[<channel>] <nick|hostmask>

        Ignores everything said or done by <nick|hostmask> in <channel>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        pass

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
                L.append('is an op on %s' % utils.commaAndify(ops))
            if halfops:
                L.append('is a halfop on %s' % utils.commaAndify(halfops))
            if voices:
                L.append('is voiced on %s' % utils.commaAndify(voices))
            if L:
                L.append('is also on %s' % utils.commaAndify(normal))
            else:
                L.append('is on %s' % utils.commaAndify(normal))
        else:
            L = ['isn\'t on any non-secret channels']
        channels = utils.commaAndify(L)
        if '317' in d:
            idle = utils.timeElapsed(d['317'].args[2])
            signon = time.strftime(conf.supybot.humanTimestampFormat(),
                                   time.localtime(float(d['317'].args[3])))
        else:
            idle = '<unknown>'
            signon = '<unknown>'
        if '312' in d:
            server = d['312'].args[2]
        else:
            server = '<unknown>'
        if '301' in d:
            away = '  %s is away: %s.' % (nick, d['301'].args[2])
        else:
            away = ''
        if '320' in d:
            if d['320'].args[2]:
                identify = ' identified'
            else:
                identify = ''
        else:
            identify = ''
        s = '%s (%s) has been%s on server %s since %s (idle for %s) and ' \
            '%s.%s' % (user, hostmask, identify, server, signon, idle,
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
        s = 'There is no %s on %s.' % (nick, self._getIrcName(irc))
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
            s = '%s %s%s %s' % (t, nick, network, ircmsgs.unAction(msg))
        else:
            if color:
                lt = ircutils.mircColor('<', *colors)
                gt = ircutils.mircColor('>', *colors)
            else:
                lt = '<'
                gt = '>'
            s = '%s%s%s%s %s' % (lt, nick, network, gt, msg.args[1])
        return s

    def _addRelayedMsg(self, msg):
        try:
            self.relayedMsgs[msg] += 1
        except KeyError:
            self.relayedMsgs[msg] = 1

    def _sendToOthers(self, irc, msg):
        assert msg.command == 'PRIVMSG' or msg.command == 'TOPIC'
        for otherIrc in world.ircs:
            if otherIrc != irc:
                if msg.args[0] in otherIrc.state.channels:
                    self._addRelayedMsg(msg)
                    otherIrc.queueMsg(msg)

    def _detectRelays(self, irc, msg, channel):
        def isRelayPrefix(s):
            return s and s[0] == '<' and s[-1] == '>'
        def punish():
            punished = False
            for irc in world.ircs:
                if irc.nick in irc.state.channels[channel].ops:
                    self.log.info('Punishing %s in %s on %s for relaying.',
                                  msg.prefix, channel, irc.network)
                    irc.sendMsg(ircmsgs.ban(channel, msg.prefix))
                    kmsg = 'You seem to be relaying, punk.'
                    irc.sendMsg(ircmsgs.kick(channel, msg.nick, kmsg))
                    punished = True
                else:
                    self.log.warning('Can\'t punish %s in %s on %s; '
                                     'I\'m not opped.',
                                     msg.prefix, channel, irc.network)
            return punished
        if channel not in self.last20Privmsgs:
            self.last20Privmsgs[channel] = RingBuffer(20)
        s = ircutils.stripFormatting(msg.args[1])
        s = utils.normalizeWhitespace(s)
        try:
            (prefix, suffix) = s.split(None, 1)
        except ValueError, e:
            pass
        else:
            if isRelayPrefix(prefix):
                parts = suffix.split()
                while parts and isRelayPrefix(parts[0]):
                    parts.pop(0)
                suffix = ' '.join(parts)
                for m in self.last20Privmsgs[channel]:
                    if suffix in m:
                        who = msg.prefix
                        self.log.info('%s seems to be relaying too.', who)
                        if punish():
                            self.log.info('Successfully punished %s.', who)
                        else:
                            self.log.info('Unsuccessfully attempted to '
                                          'punish %s.', who)
                        break
        self.last20Privmsgs[channel].append(s)

    def doPrivmsg(self, irc, msg):
        (channel, text) = msg.args
        if ircutils.isChannel(channel):
            irc = self._getRealIrc(irc)
            if channel not in self.registryValue('channels'):
                return
            if ircmsgs.isCtcp(msg) and \
               'AWAY' not in text and 'ACTION' not in text:
                return
            # Let's try to detect other relay bots.
            if self.registryValue('detectOtherRelayBots', channel):
                self._detectRelays(irc, msg, channel)
            network = self._getIrcName(irc)
            s = self._formatPrivmsg(msg.nick, network, msg)
            m = ircmsgs.privmsg(channel, s)
            self._sendToOthers(irc, m)
            
    def doJoin(self, irc, msg):
        irc = self._getRealIrc(irc)
        channel = msg.args[0]
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        if self.registryValue('hostmasks', channel):
            hostmask = ' (%s)' % msg.prefix
        else:
            hostmask = ''
        s = '%s%s has joined on %s' % (msg.nick, hostmask, network)
        m = ircmsgs.privmsg(channel, s)
        self._sendToOthers(irc, m)

    def doPart(self, irc, msg):
        irc = self._getRealIrc(irc)
        channel = msg.args[0]
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        if self.registryValue('hostmasks', channel):
            hostmask = ' (%s)' % msg.prefix
        else:
            hostmask = ''
        s = '%s%s has left on %s' % (msg.nick, hostmask, network)
        m = ircmsgs.privmsg(channel, s)
        self._sendToOthers(irc, m)

    def doMode(self, irc, msg):
        irc = self._getRealIrc(irc)
        channel = msg.args[0]
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        s = 'mode change by %s on %s: %s' % \
            (msg.nick, network, ' '.join(msg.args[1:]))
        m = ircmsgs.privmsg(channel, s)
        self._sendToOthers(irc, m)

    def doKick(self, irc, msg):
        irc = self._getRealIrc(irc)
        channel = msg.args[0]
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        if len(msg.args) == 3:
            s = '%s was kicked by %s on %s (%s)' % \
                (msg.args[1], msg.nick, network, msg.args[2])
        else:
            s = '%s was kicked by %s on %s' % \
                (msg.args[1], msg.nick, network)
        m = ircmsgs.privmsg(channel, s)
        self._sendToOthers(irc, m)

    def doNick(self, irc, msg):
        irc = self._getRealIrc(irc)
        newNick = msg.args[0]
        network = self._getIrcName(irc)
        s = 'nick change by %s to %s on %s' % (msg.nick, newNick, network)
        for channel in self.registryValue('channels'):
            if newNick in irc.state.channels[channel].users:
                m = ircmsgs.privmsg(channel, s)
                self._sendToOthers(irc, m)

    def doTopic(self, irc, msg):
        irc = self._getRealIrc(irc)
        if msg.nick == irc.nick:
            return
        (channel, newTopic) = msg.args
        if channel not in self.registryValue('channels'):
            return
        network = self._getIrcName(irc)
        if self.registryValue('topicSync', channel):
            m = ircmsgs.topic(channel, newTopic)
        else:
            s = 'topic change by %s on %s: %s' % (msg.nick, network, newTopic)
            m = ircmsgs.privmsg(channel, s)
        self._sendToOthers(irc, m)

    def doQuit(self, irc, msg):
        irc = self._getRealIrc(irc)
        network = self._getIrcName(irc)
        if msg.args:
            s = '%s has quit %s (%s)' % (msg.nick, network, msg.args[0])
        else:
            s = '%s has quit %s.' % (msg.nick, network)
        for channel in self.registryValue('channels'):
            if msg.nick in self.ircstates[irc].channels[channel].users:
                m = ircmsgs.privmsg(channel, s)
                self._sendToOthers(irc, m)

    def _isRelayedPrivmsg(self, msg):
        if msg in self.relayedMsgs:
            self.relayedMsgs[msg] -= 1
            if not self.relayedMsgs[msg]:
                del self.relayedMsgs[msg]
            return True
        else:
            return False

    def outFilter(self, irc, msg):
        irc = self._getRealIrc(irc)
        if msg.command == 'PRIVMSG':
            if not self._isRelayedPrivmsg(msg):
                channel = msg.args[0]
                if channel in self.registryValue('channels'):
                    network = self._getIrcName(irc)
                    s = self._formatPrivmsg(irc.nick, network, msg)
                    relayMsg = ircmsgs.privmsg(channel, s)
                    self._sendToOthers(irc, relayMsg)
        elif msg.command == 'TOPIC' and len(msg.args) > 1 and \
             self.registryValue('topicSync', msg.args[0]):
            (channel, topic) = msg.args
            if channel in self.registryValue('channels'):
                for otherIrc in world.ircs:
                    if otherIrc != irc:
                        try:
                            if otherIrc.state.getTopic(channel) != topic:
                                otherIrc.queueMsg(ircmsgs.topic(channel,topic))
                        except KeyError:
                            self.log.warning('Not on %s on %s -- '
                                             'Can\'t synchronize topics.',
                                             channel, otherIrc.server)

        return msg

Class = Relay

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
