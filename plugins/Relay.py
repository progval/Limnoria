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

Commands include:
  startrelay
  relayconnect
  relaydisconnect
  relayjoin
  relaypart
"""

from baseplugin import *

import re
import copy

import ircdb
import debug
import irclib
import ircmsgs
import ircutils
import privmsgs
import callbacks
import asyncoreDrivers

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
    

class Relay(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.ircs = {}
        self.started = False
        self.ircstates = {}
        self.lastmsg = ircmsgs.ping('this is just a fake message')
        self.channels = set()
        self.abbreviations = {}
        
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
    
    def startrelay(self, irc, msg, args):
        """<network abbreviation for current server>

        This command is necessary to start the Relay plugin; the
        <network abbreviation> is the abbreviation that the network the
        bot is currently connected to should be shown as to other networks.
        For instance, if the network abbreviation is 'oftc', then when
        relaying messages from that network to other networks, the users
        will show up as 'user@oftc'.
        """
        realIrc = irc.getRealIrc()
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
        if ':' in server:
            (server, port) = server.split(':')
            port = int(port)
        else:
            port = 6667
        newIrc = irclib.Irc(irc.nick, callbacks=irc.callbacks)
        driver = asyncoreDrivers.AsyncoreDriver((server, port), newIrc)
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
        otherIrc.driver.die()
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

    def relaynames(self, irc, msg, args):
        """[<channel>] (only if not sent in the channel itself.)

        The <channel> argument is only necessary if the message isn't sent on
        the channel itself.  Returns the nicks of the people in the channel on
        the various networks the bot is connected to.
        """
        if not isinstance(irc, irclib.Irc):
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
                users.append('\x02%s\x02: %s' % (abbreviation, usersS))
        irc.reply(msg, '; '.join(users))
        
    def _formatPrivmsg(self, nick, abbreviation, msg):
        if ircmsgs.isAction(msg):
            return '* %s/%s %s' % (nick, abbreviation, ircmsgs.unAction(msg))
        else:
            return '<%s@%s> %s' % (nick, abbreviation, msg.args[1])

    def doPrivmsg(self, irc, msg):
        callbacks.Privmsg.doPrivmsg(self, irc, msg)
        if not isinstance(irc, irclib.Irc):
            irc = irc.getRealIrc()
        if self.started and ircutils.isChannel(msg.args[0]):
            channel = msg.args[0]
            if channel not in self.channels:
                return
            #debug.printf('self.abbreviations = %s' % self.abbreviations)
            #debug.printf('self.ircs = %s' % self.ircs)
            #debug.printf('irc = %s' % irc)
            abbreviation = self.abbreviations[irc]
            s = self._formatPrivmsg(msg.nick, abbreviation, msg)
            for otherIrc in self.ircs.itervalues():
                #debug.printf('otherIrc = %s' % otherIrc)
                if otherIrc != irc:
                    #debug.printf('otherIrc != irc')
                    #debug.printf('id(irc) = %s, id(otherIrc) = %s' % \
                    #             (id(irc), id(otherIrc)))
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
            s = '%s has joined on %s' % (msg.nick, abbreviation)
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
            s = '%s has left on %s' % (msg.nick, abbreviation)
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
                s = 'mode change by %s on %s/%s %s' % \
                    (msg.nick, channel, abbreviation, ' '.join(msg.args[1:]))
                for otherIrc in self.ircs.itervalues():
                    if otherIrc != irc:
                        otherIrc.queueMsg(ircmsgs.privmsg(channel, s))
                    
    def doNick(self, irc, msg):
        if self.started:
            if not isinstance(irc, irclib.Irc):
                irc = irc.getRealIrc()
            newNick = msg.args[0]
            s = 'nick change by %s to %s' % (msg.nick, newNick)
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
            if len(msg.args) > 0:
                s = '%s/%s has quit (%s)' % (msg.nick, network, msg.args[0])
            else:
                s = '%s/%s has quit.' % (msg.nick, network)
            for channel in self.channels:
                debug.printf(self.ircstates[irc])
                debug.printf(self.ircstates[irc].channels[channel].users)
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
            rAction = re.compile(r'\* [^/]+/(?:%s) ' % '|'.join(abbreviations))
            if not (rPrivmsg.match(msg.args[1]) or \
                    rAction.match(msg.args[1]) or \
                    msg.args[1].find('has left on ') != -1 or \
                    msg.args[1].find('has joined on ') != -1 or \
                    msg.args[1].find('has quit') != -1 or \
                    msg.args[1].startswith('mode change') or \
                    msg.args[1].startswith('nick change')):
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
