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
Handles relaying between networks.
"""

import plugins

import re
import sys
import time

import conf
import debug
import utils
import world
import irclib
import drivers
import ircmsgs
import ircutils
import privmsgs
import callbacks

def configure(onStart, afterConnect, advanced):
    import socket
    from questions import expect, anything, something, yn
    onStart.append('load Relay')
    startNetwork = anything('What is the name of the network you\'re ' \
                            'connecting to first?')
    onStart.append('relay start %s' % startNetwork)
    while yn('Do you want to connect to another network for relaying?') == 'y':
        network = anything('What is the name of the network you want to ' \
                           'connect to?')
        server = ''
        while not server:
            server = anything('What server does that network use?')
            try:
                print 'Looking up %s' % server
                ip = socket.gethostbyname(server)
                print 'Found %s (%s)' % (server, ip)
            except socket.error:
                print 'Sorry, but I couldn\'t find that server.'
                server = ''
        if yn('Does that server require you to connect on a port other than '
              'the default port for IRC (6667)?') == 'y':
            port = ''
            while not port:
                port = anything('What port is that?')
                try:
                    int(port)
                except ValueError:
                    print 'Sorry, but that isn\'t a valid port.'
                    port = ''
            server = ':'.join((server, port))
        onStart.append('relay connect %s %s' % (network, server))
    channel = anything('What channel would you like to relay between?')
    afterConnect.append('relay join %s' % utils.dqrepr(channel))
    while yn('Would like to relay between any more channels?') == 'y':
        channel = anything('What channel?')
        afterConnect.append('relay join %s' % channel)
    if yn('Would you like to use color to distinguish between nicks?') == 'y':
        afterConnect.append('relay color 2')


class Relay(callbacks.Privmsg, plugins.Configurable):
    noIgnore = True
    priority = sys.maxint
    configurables = plugins.ConfigurableDictionary(
        [('color', plugins.ConfigurableBoolType, True,
          """Determines whether the bot will color relayed PRIVMSGs so as to
          make the messages easier to read."""),]
    )
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        plugins.Configurable.__init__(self)
        self.ircs = {}
        self._color = 0
        self._whois = {}
        self.started = False
        self.ircstates = {}
        self.lastmsg = {}
        self.channels = ircutils.IrcSet()
        self.abbreviations = {}
        self.originalIrc = None

    def __call__(self, irc, msg):
        if self.started:
            try:
                if not isinstance(irc, irclib.Irc):
                    irc = irc.getRealIrc()
                self.ircstates[irc].addMsg(irc, self.lastmsg[irc])
            finally:
                self.lastmsg[irc] = msg
        callbacks.Privmsg.__call__(self, irc, msg)

    def die(self):
        callbacks.Privmsg.die(self)
        plugins.Configurable.die(self)
        for irc in self.abbreviations:
            if irc != self.originalIrc:
                irc.callbacks[:] = []
                irc.die()

    def do376(self, irc, msg):
        if self.channels:
            irc.queueMsg(ircmsgs.joins(self.channels))
    do377 = do376
    do422 = do376

    def start(self, irc, msg, args):
        """<network abbreviation for current server>

        This command is necessary to start the Relay plugin; the
        <network abbreviation> is the abbreviation that the network the
        bot is currently connected to should be shown as to other networks.
        For instance, if the network abbreviation is 'oftc', then when
        relaying messages from that network to other networks, the users
        will show up as 'user@oftc'.
        """
        if isinstance(irc, irclib.Irc):
            realIrc = irc
        else:
            realIrc = irc.getRealIrc()
        self.originalIrc = realIrc
        abbreviation = privmsgs.getArgs(args)
        self.ircs[abbreviation] = realIrc
        self.abbreviations[realIrc] = abbreviation
        self.ircstates[realIrc] = irclib.IrcState()
        self.lastmsg[realIrc] = ircmsgs.ping('this is just a fake message')
        self.started = True
        irc.reply(msg, conf.replySuccess)
    start = privmsgs.checkCapability(start, 'owner')

    def connect(self, irc, msg, args):
        """<network abbreviation> <domain:port> (port defaults to 6667)

        Connects to another network at <domain:port>.  The network
        abbreviation <network abbreviation> is used when relaying messages from
        that network to other networks.
        """
        if not self.started:
            irc.error(msg, 'You must use the start command first.')
            return
        abbreviation, server = privmsgs.getArgs(args, required=2)
        if isinstance(irc, irclib.Irc):
            realIrc = irc
        else:
            realIrc = irc.getRealIrc()
        if ':' in server:
            (server, port) = server.split(':')
            port = int(port)
        else:
            port = 6667
        newIrc = irclib.Irc(irc.nick, callbacks=realIrc.callbacks)
        newIrc.state.history = realIrc.state.history
        driver = drivers.newDriver((server, port), newIrc)
        newIrc.driver = driver
        self.ircs[abbreviation] = newIrc
        self.abbreviations[newIrc] = abbreviation
        self.ircstates[newIrc] = irclib.IrcState()
        self.lastmsg[newIrc] = ircmsgs.ping('this is just a fake message')
        irc.reply(msg, conf.replySuccess)
    connect = privmsgs.checkCapability(connect, 'owner')

    def disconnect(self, irc, msg, args):
        """<network>

        Disconnects and ceases to relay to and from the network represented by
        the network abbreviation <network>.
        """
        if not self.started:
            irc.error(msg, 'You must use the start command first.')
            return
        network = privmsgs.getArgs(args)
        otherIrc = self.ircs[network]
        otherIrc.driver.die()
        world.ircs.remove(otherIrc)
        del self.ircs[network]
        del self.abbreviations[otherIrc]
        irc.reply(msg, conf.replySuccess)
    disconnect = privmsgs.checkCapability(disconnect, 'owner')

    def join(self, irc, msg, args):
        """<channel>

        Starts relaying between the channel <channel> on all networks.  If on a
        network the bot isn't in <channel>, he'll join.  This commands is
        required even if the bot is in the channel on both networks; he won't
        relay between those channels unless he's told to oin both
        channels.
        """
        if not self.started:
            irc.error(msg, 'You must use the start command first.')
            return
        channel = privmsgs.getArgs(args)
        if not ircutils.isChannel(channel):
            irc.error(msg, '%r is not a valid channel.' % channel)
            return
        self.channels.add(ircutils.toLower(channel))
        for otherIrc in self.ircs.itervalues():
            if channel not in otherIrc.state.channels:
                otherIrc.queueMsg(ircmsgs.join(channel))
        irc.reply(msg, conf.replySuccess)
    join = privmsgs.checkCapability(join, 'owner')

    def part(self, irc, msg, args):
        """<channel>

        Ceases relaying between the channel <channel> on all networks.  The bot
        will part from the channel on all networks in which it is on the
        channel.
        """
        if not self.started:
            irc.error(msg, 'You must use the start command first.')
            return
        channel = privmsgs.getArgs(args)
        if not ircutils.isChannel(channel):
            irc.error(msg, '%r is not a valid channel.' % channel)
            return
        self.channels.remove(ircutils.toLower(channel))
        for otherIrc in self.ircs.itervalues():
            if channel in otherIrc.state.channels:
                otherIrc.queueMsg(ircmsgs.part(channel))
        irc.reply(msg, conf.replySuccess)
    part = privmsgs.checkCapability(part, 'owner')

    def say(self, irc, msg, args):
        """<network> [<channel>] <text>

        Says <text> on <channel> (using the current channel if unspecified)
        on <network>.
        """
        if not self.started:
            irc.error(msg, 'You must use the start command first.')
            return
        if not args:
            raise callbacks.ArgumentError
        network = args.pop(0)
        channel = privmsgs.getChannel(msg, args)
        text = privmsgs.getArgs(args)
        if network not in self.ircs:
            irc.error(msg, 'I\'m not currently on %s.' % network)
            return
        if channel not in self.channels:
            irc.error(msg, 'I\'m not currently relaying to %s.' % channel)
            return
        self.ircs[network].queueMsg(ircmsgs.privmsg(channel, text))
    say = privmsgs.checkCapability(say, 'admin')

    def names(self, irc, msg, args):
        """[<channel>] (only if not sent in the channel itself.)

        The <channel> argument is only necessary if the message isn't sent on
        the channel itself.  Returns the nicks of the people in the channel on
        the various networks the bot is connected to.
        """
        if not self.started:
            irc.error(msg, 'You must use the start command first.')
            return
        if isinstance(irc, irclib.Irc):
            realIrc = irc
        else:
            realIrc = irc.getRealIrc()
        channel = privmsgs.getChannel(msg, args)
        if channel not in self.channels:
            irc.error(msg, 'I\'m not relaying %s.' % channel)
            return
        users = []
        for (abbreviation, otherIrc) in self.ircs.iteritems():
            ops = []
            halfops = []
            voices = []
            usersS = []
            if abbreviation != self.abbreviations[realIrc]:
                try:
                    Channel = otherIrc.state.channels[channel]
                except KeyError:
                    s = 'Somehow I\'m not in %s on %s.'% (channel,abbreviation)
                    irc.error(msg, s)
                    return
                for s in Channel.users:
                    s = s.strip()
                    if not s:
                        continue
                    elif s in Channel.ops:
                        ops.append('@%s' % s)
                    elif s in Channel.halfops:
                        halfops.append('%%%s' % s)
                    elif s in Channel.voices:
                        voices.append('+%s' % s)
                    else:
                        usersS.append(s)
                map(list.sort, (ops, halfops, voices, usersS))
                usersS = ', '.join(filter(None, map(', '.join,
                    (ops,halfops,voices,usersS))))
                users.append('%s: %s' % (ircutils.bold(abbreviation), usersS))
        irc.reply(msg, '; '.join(users))

    def whois(self, irc, msg, args):
        """<nick>@<network>

        Returns the WHOIS response <network> gives for <nick>.
        """
        if not self.started:
            irc.error(msg, 'You must use the start command first.')
            return
        nickAtNetwork = privmsgs.getArgs(args)
        if isinstance(irc, irclib.Irc):
            realIrc = irc
        else:
            realIrc = irc.getRealIrc()
        try:
            (nick, network) = nickAtNetwork.split('@', 1)
            if not ircutils.isNick(nick):
                irc.error(msg, '%s is not an IRC nick.' % nick)
                return
            nick = ircutils.toLower(nick)
        except ValueError:
            if len(self.abbreviations) == 2:
                # If there are only two networks being relayed, we can safely
                # pick the *other* one.
                nick = ircutils.toLower(nickAtNetwork)
                for (keyIrc, net) in self.abbreviations.iteritems():
                    if keyIrc != realIrc:
                        network = net
            else:
                raise callbacks.ArgumentError
        if network not in self.ircs:
            irc.error(msg, 'I\'m not on that network.')
            return
        otherIrc = self.ircs[network]
        otherIrc.queueMsg(ircmsgs.whois(nick, nick))
        self._whois[(otherIrc, nick)] = (irc, msg, {})

    def do311(self, irc, msg):
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        nick = ircutils.toLower(msg.args[1])
        if (irc, nick) not in self._whois:
            return
        else:
            self._whois[(irc, nick)][-1][msg.command] = msg

    do312 = do311
    do317 = do311
    do319 = do311

    def do318(self, irc, msg):
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        nick = ircutils.toLower(msg.args[1])
        if (irc, nick) not in self._whois:
            return
        (replyIrc, replyMsg, d) = self._whois[(irc, nick)]
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
            signon = time.strftime(conf.humanTimestampFormat,
                                   time.localtime(float(d['317'].args[3])))
        else:
            idle = '<unknown>'
            signon = '<unknown>'
        if '312' in d:
            server = d['312'].args[2]
        else:
            server = '<unknown>'
        s = '%s (%s) has been on server %s since %s (idle for %s) and %s.' % \
            (user, hostmask, server, signon, idle, channels)
        replyIrc.reply(replyMsg, s)
        del self._whois[(irc, nick)]

    def do402(self, irc, msg):
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        nick = ircutils.toLower(msg.args[1])
        if (irc, nick) not in self._whois:
            return
        (replyIrc, replyMsg, d) = self._whois[(irc, nick)]
        s = 'There is no %s on %s.' % (nick, self.abbreviations[irc])
        replyIrc.reply(replyMsg, s)

    do401 = do402

    def _formatPrivmsg(self, nick, network, msg):
        # colorize nicks
        color = self.configurables.get('color', msg.args[0])
        if color:
            nick = ircutils.mircColor(nick, *ircutils.canonicalColor(nick))
            colors = ircutils.canonicalColor(nick, shift=4)
        if ircmsgs.isAction(msg):
            if color:
                t = ircutils.mircColor('*', *colors)
            else:
                t = '*'
            s = '%s %s@%s %s' % (t, nick, network, ircmsgs.unAction(msg))
        else:
            if color:
                lt = ircutils.mircColor('<', *colors)
                gt = ircutils.mircColor('>', *colors)
            else:
                lt = '<'
                gt = '>'
            s = '%s%s@%s%s %s' % (lt, nick, network, gt, msg.args[1])
        return s

    def _sendToOthers(self, irc, msg):
        assert msg.command == 'PRIVMSG'
        for otherIrc in self.ircs.itervalues():
            if otherIrc != irc:
                if msg.args[0] in otherIrc.state.channels:
                    otherIrc.queueMsg(msg)

    def doPrivmsg(self, irc, msg):
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        if self.started and ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
            if channel not in self.channels:
                return
            abbreviation = self.abbreviations[irc]
            s = self._formatPrivmsg(msg.nick, abbreviation, msg)
            m = ircmsgs.privmsg(channel, s)
            self._sendToOthers(irc, m)

    def doJoin(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            channel = msg.args[0]
            if channel not in self.channels:
                return
            abbreviation = self.abbreviations[irc]
            s = '%s (%s) has joined on %s' % (msg.nick,msg.prefix,abbreviation)
            m = ircmsgs.privmsg(channel, s)
            self._sendToOthers(irc, m)

    def doPart(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            channel = msg.args[0]
            if channel not in self.channels:
                return
            abbreviation = self.abbreviations[irc]
            s = '%s (%s) has left on %s' % (msg.nick, msg.prefix, abbreviation)
            m = ircmsgs.privmsg(channel, s)
            self._sendToOthers(irc, m)

    def doMode(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            channel = msg.args[0]
            if channel not in self.channels:
                return
            abbreviation = self.abbreviations[irc]
            s = 'mode change by %s on %s: %s' % \
                (msg.nick, abbreviation, ' '.join(msg.args[1:]))
            m = ircmsgs.privmsg(channel, s)
            self._sendToOthers(irc, m)

    def doKick(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            channel = msg.args[0]
            if channel not in self.channels:
                return
            abbrev = self.abbreviations[irc]
            if len(msg.args) == 3:
                s = '%s was kicked by %s on %s (%s)' % \
                    (msg.args[1], msg.nick, abbrev, msg.args[2])
            else:
                s = '%s was kicked by %s on %s' % \
                    (msg.args[1], msg.nick, abbrev)
            m = ircmsgs.privmsg(channel, s)
            self._sendToOthers(irc, m)

    def doNick(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            newNick = msg.args[0]
            network = self.abbreviations[irc]
            s = 'nick change by %s to %s on %s' % (msg.nick, newNick, network)
            for channel in self.channels:
                if newNick in irc.state.channels[channel].users:
                    m = ircmsgs.privmsg(channel, s)
                    self._sendToOthers(irc, m)

    def doTopic(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            if msg.nick == irc.nick:
                return
            newTopic = msg.args[1]
            network = self.abbreviations[irc]
            s = 'topic change by %s on %s: %s' % (msg.nick, network, newTopic)
            m = ircmsgs.privmsg(msg.args[0], s)
            self._sendToOthers(irc, m)

    def doQuit(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            network = self.abbreviations[irc]
            if msg.args:
                s = '%s has quit %s (%s)' % (msg.nick, network, msg.args[0])
            else:
                s = '%s has quit %s.' % (msg.nick, network)
            for channel in self.channels:
                if msg.nick in self.ircstates[irc].channels[channel].users:
                    m = ircmsgs.privmsg(channel, s)
                    self._sendToOthers(irc, m)

    def outFilter(self, irc, msg):
        if not self.started:
            return msg
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        if msg.command == 'PRIVMSG':
            abbreviations = self.abbreviations.values()
            rPrivmsg = re.compile(r'<[^@]+@(?:%s)>' % '|'.join(abbreviations))
            rAction = re.compile(r'\* [^/]+@(?:%s) ' % '|'.join(abbreviations))
            text = ircutils.unColor(msg.args[1])
            if not (rPrivmsg.match(text) or \
                    rAction.match(text) or \
                    'has left on ' in text or \
                    'has joined on ' in text or \
                    'has quit' in text or \
                    'was kicked by' in text or \
                    text.startswith('mode change') or \
                    text.startswith('nick change') or \
                    text.startswith('topic change')):
                channel = msg.args[0]
                if channel in self.channels:
                    abbreviation = self.abbreviations[irc]
                    s = self._formatPrivmsg(irc.nick, abbreviation, msg)
                    for otherIrc in self.ircs.itervalues():
                        if otherIrc != irc:
                            if channel in otherIrc.state.channels:
                                otherIrc.queueMsg(ircmsgs.privmsg(channel, s))
        elif msg.command == 'TOPIC' and len(msg.args) > 1:
            (channel, topic) = msg.args
            if channel in self.channels:
                for otherIrc in self.ircs.itervalues():
                    if otherIrc != irc:
                        if otherIrc.state.getTopic(channel) != topic:
                            otherIrc.queueMsg(ircmsgs.topic(channel, topic))

        return msg

Class = Relay

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
