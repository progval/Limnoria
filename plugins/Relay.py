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

import ircdb
import debug
import irclib
import ircmsgs
import ircutils
import privmsgs
import callbacks
import asyncoreDrivers

class Relay(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.ircs = {}
        self.started = False
        self.channels = set()
        self.abbreviations = {}
        
    def startrelay(self, irc, msg, args):
        "<network abbreviation for current server>"
        realIrc = irc.getRealIrc()
        abbreviation = privmsgs.getArgs(args)
        self.ircs[abbreviation] = realIrc
        self.abbreviations[realIrc] = abbreviation
        self.started = True
        irc.reply(msg, conf.replySuccess)
    startrelay = privmsgs.checkCapability(startrelay, 'owner')

    def relayconnect(self, irc, msg, args):
        "<network abbreviation> <domain:port> (port defaults to 6667)"
        abbreviation, server = privmsgs.getArgs(args, needed=2)
        if ':' in server:
            (server, port) = server.split(':')
            port = int(port)
        else:
            port = 6667
        newIrc = irclib.Irc(irc.nick, callbacks=irc.callbacks)
        driver = asyncoreDrivers.AsyncoreDriver((server, port))
        driver.irc = newIrc
        newIrc.driver = driver
        self.ircs[abbreviation] = newIrc
        self.abbreviations[newIrc] = abbreviation
        irc.reply(msg, conf.replySuccess)
    relayconnect = privmsgs.checkCapability(relayconnect, 'owner')

    def relaydisconnect(self, irc, msg, args):
        "<network>"
        network = privmsgs.getArgs(args)
        otherIrc = self.ircs[network]
        otherIrc.driver.die()
        del self.ircs[network]
        world.ircs.remove(otherIrc)
        del self.abbreviations[otherIrc]
        irc.reply(msg, conf.replySuccess)
    relaydisconnect = privmsgs.checkCapability(relaydisconnect, 'owner')

    def relayjoin(self, irc, msg, args):
        "<channel>"
        channel = privmsgs.getArgs(args)
        self.channels.add(channel)
        for otherIrc in self.ircs.itervalues():
            if channel not in otherIrc.state.channels:
                otherIrc.queueMsg(ircmsgs.join(channel))
        irc.reply(msg, conf.replySuccess)
    relayjoin = privmsgs.checkCapability(relayjoin, 'owner')

    def relaypart(self, irc, msg, args):
        "<channel>"
        channel = privmsgs.getArgs(args)
        self.channels.remove(channel)
        for otherIrc in self.ircs.itervalues():
            if channel in otherIrc.state.channels:
                otherIrc.queueMsg(ircmsgs.part(channel))
        irc.reply(msg, conf.replySuccess)
    relaypart = privmsgs.checkCapability(relaypart, 'owner')

    def relaynames(self, irc, msg, args):
        "[<channel>] (only if not sent in the channel itself.)"
        if not isinstance(irc, irclib.Irc):
            realIrc = irc.getRealIrc()
        channel = privmsgs.getChannel(msg, args)
        if channel not in self.channels:
            irc.error(msg, 'I\'m not relaying that channel.')
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
                s = 'mode change on %s/%s %s' % \
                    (channel, abbreviation, ' '.join(msg.args[1:]))
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
