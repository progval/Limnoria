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

from baseplugin import *

import re
import sets
import time

import conf
import debug
import utils
import ircdb
import irclib
import drivers
import ircmsgs
import ircutils
import privmsgs
import callbacks

example = utils.wrapLines("""
<jemfinch> @load Relay
<supybot> jemfinch: The operation succeeded.
<jemfinch> @startrelay freenode
<supybot> jemfinch: The operation succeeded.
<jemfinch> @relayconnect oftc irc.oftc.net
<supybot> jemfinch: The operation succeeded.
<jemfinch> @relayjoin #sourcereview
<supybot> jemfinch: The operation succeeded.
<supybot> supybot (supybot!~supybot@65.24.59.168) has joined on oftc
<jemfinch> howdy, folks :)
<supybot> jemfinch (jemfinch!~jfincher@dhcp065-024-059-168.columbus.rr.com) has joined on oftc
<jemfinch> @list Relay
<supybot> jemfinch: relaycolor, relayconnect, relaydisconnect, relayjoin, relaynames, relaypart, relaysay, relaywhois, startrelay
<jemfinch> @relaynames
<supybot> jemfinch: oftc: supybot, jemfinch, sweede, Strike, GnuVince
<jemfinch> @relaycolor 0
<supybot> jemfinch: The operation succeeded.
<jemfinch> @relaycolor 1
<supybot> jemfinch: The operation succeeded.
<jemfinch> @relaycolor 2
<supybot> jemfinch: The operation succeeded.
<jemfinch> @relaycolor 3
<supybot> jemfinch: relaycolor <0,1,2>
<jemfinch> @relaywhois GnuVince
<supybot> jemfinch: Vincent Foley (~vince@modemcable216.89-202-24.mtl.mc.videotron.ca) has been online since 08:37 PM, August 24, 2003 (idle for 1 day, 10 hours, 21 minutes, and 3 seconds) and is on #sourcereview and @#hackcanada
""")

def configure(onStart, afterConnect, advanced):
    import socket
    from questions import expect, anything, something, yn
    onStart.append('load Relay')
    startNetwork = anything('What is the name of the network you\'re ' \
                            'connecting to first?')
    onStart.append('startrelay %s' % startNetwork)
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
        onStart.append('relayconnect %s %s' % (network, server))
    channel = anything('What channel would you like to relay between?')
    afterConnect.append('relayjoin %s' % channel)
    while yn('Would like to relay between any more channels?') == 'y':
        channel = anything('What channel?')
        afterConnect.append('relayjoin %s' % channel)
    if yn('Would you like to use color to distinguish between nicks?') == 'y':
        afterConnect.append('relaycolor 2')


class Relay(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.color = 0
        self.ircs = {}
        self.whois = {}
        self.started = False
        self.ircstates = {}
        self.lastmsg = ircmsgs.ping('this is just a fake message')
        self.channels = ircutils.IrcSet()
        self.abbreviations = {}
        self.originalIrc = None

    def inFilter(self, irc, msg):
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        try:
            self.ircstates[irc].addMsg(irc, self.lastmsg)
        except KeyError:
            self.ircstates[irc] = irclib.IrcState()
            self.ircstates[irc].addMsg(irc, self.lastmsg)
        self.lastmsg = msg
        return msg

    def die(self):
        for irc in self.abbreviations:
            if irc != self.originalIrc:
                irc.callbacks[:] = []
                irc.die()

    def do376(self, irc, msg):
        if self.channels:
            irc.queueMsg(ircmsgs.joins(self.channels))

    def startrelay(self, irc, msg, args):
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
        self.started = True
        irc.reply(msg, conf.replySuccess)
    startrelay = privmsgs.checkCapability(startrelay, 'owner')

    def relayconnect(self, irc, msg, args):
        """<network abbreviation> <domain:port> (port defaults to 6667)

        Connects to another network at <domain:port>.  The network
        abbreviation <network abbreviation> is used when relaying messages from
        that network to other networks.
        """
        abbreviation, server = privmsgs.getArgs(args, needed=2)
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
        irc.reply(msg, conf.replySuccess)
    relayconnect = privmsgs.checkCapability(relayconnect, 'owner')

    def relaydisconnect(self, irc, msg, args):
        """<network>

        Disconnects and ceases to relay to and from the network represented by
        the network abbreviation <network>.
        """
        network = privmsgs.getArgs(args)
        otherIrc = self.ircs[network]
        otherIrc.die()
        del self.ircs[network]
        world.ircs.remove(otherIrc)
        del self.abbreviations[otherIrc]
        irc.reply(msg, conf.replySuccess)
    relaydisconnect = privmsgs.checkCapability(relaydisconnect, 'owner')

    def relayjoin(self, irc, msg, args):
        """<channel>

        Starts relaying between the channel <channel> on all networks.  If on a
        network the bot isn't in <channel>, he'll join.  This commands is
        required even if the bot is in the channel on both networks; he won't
        relay between those channels unless he's told to relayjoin both
        channels.
        """
        channel = privmsgs.getArgs(args)
        self.channels.add(ircutils.toLower(channel))
        for otherIrc in self.ircs.itervalues():
            if channel not in otherIrc.state.channels:
                otherIrc.queueMsg(ircmsgs.join(channel))
        irc.reply(msg, conf.replySuccess)
    relayjoin = privmsgs.checkCapability(relayjoin, 'owner')

    def relaypart(self, irc, msg, args):
        """<channel>

        Ceases relaying between the channel <channel> on all networks.  The bot
        will part from the channel on all networks in which it is on the
        channel.
        """
        channel = privmsgs.getArgs(args)
        self.channels.remove(ircutils.toLower(channel))
        for otherIrc in self.ircs.itervalues():
            if channel in otherIrc.state.channels:
                otherIrc.queueMsg(ircmsgs.part(channel))
        irc.reply(msg, conf.replySuccess)
    relaypart = privmsgs.checkCapability(relaypart, 'owner')

    def relaysay(self, irc, msg, args):
        """<network> [<channel>] <text>

        Says <text> on <channel> (using the current channel if unspecified)
        on <network>.
        """
        if not args:
            raise callbacks.ArgumentError, 'relaysay'
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
    relaysay = privmsgs.checkCapability(relaysay, 'admin')

    def relaynames(self, irc, msg, args):
        """[<channel>] (only if not sent in the channel itself.)

        The <channel> argument is only necessary if the message isn't sent on
        the channel itself.  Returns the nicks of the people in the channel on
        the various networks the bot is connected to.
        """
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
            if abbreviation != self.abbreviations[realIrc]:
                Channel = otherIrc.state.channels[channel]
                usersS = ', '.join([s for s in Channel.users if s.strip()!=''])
                users.append('%s: %s' % (ircutils.bold(abbreviation), usersS))
        irc.reply(msg, '; '.join(users))

    def relaywhois(self, irc, msg, args):
        """<nick>@<network>

        Returns the WHOIS response <network> gives for <nick>.
        """
        nickAtNetwork = privmsgs.getArgs(args)
        if isinstance(irc, irclib.Irc):
            realIrc = irc
        else:
            realIrc = irc.getRealIrc()
        try:
            (nick, network) = nickAtNetwork.split('@', 1)
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
        self.whois[(otherIrc, nick)] = (irc, msg, {})

    def relaycolor(self, irc, msg, args):
        """<0,1,2>

        0 turns coloring of nicks/angle brackets off entirely.  1 colors the
        nicks, but not the angle brackets.  2 colors both.
        """
        try:
            color = int(privmsgs.getArgs(args))
            if color != 0 and color != 1 and color != 2:
                raise callbacks.ArgumentError
            self.color = color
        except ValueError:
            raise callbacks.ArgumentError
        irc.reply(msg, conf.replySuccess)
    relaycolor = privmsgs.checkCapability(relaycolor, 'admin')

    def do311(self, irc, msg):
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        nick = ircutils.toLower(msg.args[1])
        if (irc, nick) not in self.whois:
            return
        else:
            self.whois[(irc, nick)][-1][msg.command] = msg

    do312 = do311
    do317 = do311
    do319 = do311

    def do318(self, irc, msg):
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        nick = ircutils.toLower(msg.args[1])
        if (irc, nick) not in self.whois:
            return
        (replyIrc, replyMsg, d) = self.whois[(irc, nick)]
        hostmask = '@'.join(d['311'].args[2:4])
        user = d['311'].args[-1]
        if '319' in d:
            channels = d['319'].args[-1].split()
            channels[0] = 'is on ' + channels[0]
        else:
            channels = ['isn\'t on any channels.']
        for (i, channel) in enumerate(channels):
            if channel[0] == '@':
                channels[i] = 'is an op on %s' % channel[1:]
            elif channel[0] == '+':
                channels[i] = 'is voiced on %s' % channel[1:]
            elif channel[0] == '%':
                channels[i] = 'is a half-op on %s' % channel[1:]
        channels = utils.commaAndify(channels)
        if '317' in d:
            idle = utils.timeElapsed(d['317'].args[2])
            signon = time.strftime(conf.humanTimestampFormat,
                                   time.localtime(float(d['317'].args[3])))
        else:
            idle = '<unknown>'
            signon = '<unknown>'
        s = '%s (%s) has been online since %s (idle for %s) and %s.' % \
            (user, hostmask, signon, idle, channels)
        replyIrc.reply(replyMsg, s)
        del self.whois[(irc, nick)]

    def do402(self, irc, msg):
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        nick = ircutils.toLower(msg.args[1])
        if (irc, nick) not in self.whois:
            return
        (replyIrc, replyMsg, d) = self.whois[(irc, nick)]
        s = 'There is no %s on %s.' % (nick, self.abbreviations[irc])
        replyIrc.reply(replyMsg, s)

    do401 = do402

    def _formatPrivmsg(self, nick, network, msg):
        # colorize nicks
        if self.color >= 1:
            nick = ircutils.mircColor(nick, *ircutils.canonicalColor(nick))
        if self.color >= 2:
            colors = ircutils.canonicalColor(nick, shift=4)
        if ircmsgs.isAction(msg):
            if self.color >= 2:
                t = ircutils.mircColor('*', *colors)
            else:
                t = '*'
            s = '%s %s@%s %s' % (t, nick, network, ircmsgs.unAction(msg))
        else:
            if self.color >= 2:
                lt = ircutils.mircColor('<', *colors)
                gt = ircutils.mircColor('>', *colors)
            else:
                lt = '<'
                gt = '>'
            s = '%s%s@%s%s %s' % (lt, nick, network, gt, msg.args[1])
        return s

    def doPrivmsg(self, irc, msg):
        callbacks.Privmsg.doPrivmsg(self, irc, msg)
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        if self.started and ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
            if channel not in self.channels:
                return
            abbreviation = self.abbreviations[irc]
            s = self._formatPrivmsg(msg.nick, abbreviation, msg)
            for otherIrc in self.ircs.itervalues():
                if otherIrc != irc:
                    if channel in otherIrc.state.channels:
                         otherIrc.queueMsg(ircmsgs.privmsg(channel, s))

    def doJoin(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            channel = msg.args[0]
            if channel not in self.channels:
                return
            abbreviation = self.abbreviations[irc]
            s = '%s (%s) has joined on %s' % (msg.nick,msg.prefix,abbreviation)
            for otherIrc in self.ircs.itervalues():
                if otherIrc != irc:
                    if channel in otherIrc.state.channels:
                        otherIrc.queueMsg(ircmsgs.privmsg(channel, s))

    def doPart(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            channel = msg.args[0]
            if channel not in self.channels:
                return
            abbreviation = self.abbreviations[irc]
            s = '%s (%s) has left on %s' % (msg.nick, msg.prefix, abbreviation)
            for otherIrc in self.ircs.itervalues():
                if otherIrc != irc:
                    if channel in otherIrc.state.channels:
                        otherIrc.queueMsg(ircmsgs.privmsg(channel, s))

    def doMode(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            channel = msg.args[0]
            if channel in self.channels:
                abbreviation = self.abbreviations[irc]
                s = 'mode change by %s on %s: %s' % \
                    (msg.nick, abbreviation, ' '.join(msg.args[1:]))
                for otherIrc in self.ircs.itervalues():
                    if otherIrc != irc:
                        otherIrc.queueMsg(ircmsgs.privmsg(channel, s))

    def doKick(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            channel = msg.args[0]
            if channel in self.channels:
                abbrev = self.abbreviations[irc]
                if len(msg.args) == 3:
                    s = '%s@%s was kicked by %s@%s (%s)' % \
                        (msg.args[1], abbrev, msg.nick, abbrev, msg.args[2])
                else:
                    s = '%s@%s was kicked by %s@%s' % \
                        (msg.args[1], abbrev, msg.nick, abbrev)
                for otherIrc in self.ircs.itervalues():
                    if otherIrc != irc:
                        otherIrc.queueMsg(ircmsgs.privmsg(channel, s))

    def doNick(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            newNick = msg.args[0]
            network = self.abbreviations[irc]
            s = 'nick change by %s to %s on %s' % (msg.nick, newNick, network)
            for channel in self.channels:
                if newNick in irc.state.channels[channel].users:
                    for otherIrc in self.ircs.itervalues():
                        if otherIrc != irc:
                            otherIrc.queueMsg(ircmsgs.privmsg(channel, s))

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
                    for otherIrc in self.ircs.itervalues():
                        if otherIrc != irc:
                            otherIrc.queueMsg(ircmsgs.privmsg(channel, s))

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
                    text.startswith('mode change') or \
                    text.startswith('nick change')):
                channel = msg.args[0]
                if channel in self.channels:
                    abbreviation = self.abbreviations[irc]
                    s = self._formatPrivmsg(irc.nick, abbreviation, msg)
                    for otherIrc in self.ircs.itervalues():
                        if otherIrc != irc:
                            if channel in otherIrc.state.channels:
                                otherIrc.queueMsg(ircmsgs.privmsg(channel, s))
        elif msg.command == 'TOPIC':
            (channel, topic) = msg.args
            if channel in self.channels:
                for otherIrc in self.ircs.itervalues():
                    if otherIrc != irc:
                        if otherIrc.state.getTopic(channel) != topic:
                            otherIrc.queueMsg(ircmsgs.topic(channel, topic))

        return msg

Class = Relay

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
