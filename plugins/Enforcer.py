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
Enforcer: Enforces capabilities on a channel, watching MODEs, KICKs,
                 JOINs, etc. to make sure they match the channel's config.
"""

import plugins

import conf
import debug
import ircdb
import ircmsgs
import plugins
import privmsgs
import ircutils
import callbacks

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, something, yn
    onStart.append('load Enforcer')
    chanserv = something('What\'s the name of ChanServ on your network?')
    if yn('Do you want the bot to take revenge on rule breakers?') == 'y':
        revenge = True
    else:
        revenge = False
    onStart.append('enforcer start %s %s' % (chanserv, revenge))

###
# Enforcer: Enforces capabilities on JOIN, MODE, KICK, etc.
###
_chanCap = ircdb.makeChannelCapability
class Enforcer(callbacks.Privmsg, plugins.Configurable):
    configurables = plugins.ConfigurableDictionary(
        [('auto-op', plugins.ConfigurableBoolType, False,
          """Determines whether the bot will automatically op people with
          the <channel>.op capability when they join the channel."""),
         ('auto-voice', plugins.ConfigurableBoolType, False,
          """Determines whether the bot will automatically voice people with
          the <channel>.voice capability when they join the channel."""),
         ('auto-halfop', plugins.ConfigurableBoolType, False,
          """Determines whether the bot will automatically halfop people with
          the <channel>.halfop capability when they join the channel."""),
         ('revenge', plugins.ConfigurableBoolType, False,
          """Determines whether the bot will take revenge on people who do
          things it doesn't like (somewhat like 'bitch mode' in other IRC
          bots)."""),]
    )
    started = False
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        plugins.Configurable.__init__(self)

    def die(self):
        callbacks.Privmsg.die(self)
        plugins.Configurable.die(self)

    def start(self, irc, msg, args):
        """[<CHANSERV>]

        Starts the Enforcer plugin.  <chanserv> is the nick for the chanserv
        aspect of Services (it defaults to ChanServ).
        """
        self.topics = {}
        chanserv = privmsgs.getArgs(args, required=0, optional=2)
        self.chanserv = chanserv or 'ChanServ'
        self.started = True
        for channel in irc.state.channels:
            irc.queueMsg(ircmsgs.topic(channel))
        irc.reply(msg, conf.replySuccess)
    start = privmsgs.checkCapability(start, 'admin')

    def doJoin(self, irc, msg):
        if not self.started:
            debug.msg('Enforcer not started.', 'normal')
            return
        channel = msg.args[0]
        c = ircdb.channels.getChannel(channel)
        if c.checkBan(msg.prefix):
            irc.queueMsg(ircmsgs.ban(channel, ircutils.banmask(msg.prefix)))
            irc.queueMsg(ircmsgs.kick(channel, msg.nick))
        elif ircdb.checkCapability(msg.prefix, _chanCap(channel, 'op')):
            if self.configurables.get('auto-op', channel):
                irc.queueMsg(ircmsgs.op(channel, msg.nick))
        elif ircdb.checkCapability(msg.prefix, _chanCap(channel, 'halfop')):
            if self.configurables.get('auto-halfop', channel):
                irc.queueMsg(ircmsgs.halfop(channel, msg.nick))
        elif ircdb.checkCapability(msg.prefix, _chanCap(channel, 'voice')):
            if self.configurables.get('auto-voice', channel):
                irc.queueMsg(ircmsgs.voice(channel, msg.nick))

    def doTopic(self, irc, msg):
        if not self.started:
            debug.msg('Enforcer not started.', 'normal')
            return
        channel = msg.args[0]
        topic = msg.args[1]
        if msg.nick != irc.nick and \
           not ircdb.checkCapabilities(msg.prefix,
                                       (_chanCap(channel, 'op'),
                                        _chanCap(channel, 'topic'))):
            irc.queueMsg(ircmsgs.topic(channel, self.topics[channel]))
            if self.configurables.get('revenge', channel):
                irc.queueMsg(ircmsgs.kick(channel, msg.nick,
                                      conf.replyNoCapability % \
                                      _chanCap(channel, 'topic')))
        else:
            self.topics[channel] = msg.args[1]

    def do332(self, irc, msg):
        # This command gets sent right after joining a channel.
        if not self.started:
            debug.msg('Enforcer not started.', 'normal')
            return
        (channel, topic) = msg.args[1:]
        self.topics[channel] = topic

    def _isProtected(self, channel, hostmask):
        capabilities = [_chanCap(channel, 'op'),_chanCap(channel, 'protected')]
        return ircdb.checkCapabilities(hostmask, capabilities)

    def _revenge(self, irc, channel, hostmask):
        irc.queueMsg(ircmsgs.ban(channel, ircutils.banmask(hostmask)))
        irc.queueMsg(ircmsgs.kick(channel,ircutils.nickFromHostmask(hostmask)))

    def doKick(self, irc, msg):
        if not self.started:
            debug.msg('Enforcer not started.', 'normal')
            return
        channel = msg.args[0]
        kicked = msg.args[1].split(',')
        deop = False
        if msg.nick != irc.nick and\
           not ircdb.checkCapability(msg.prefix, _chanCap(channel, 'op')):
            for nick in kicked:
                hostmask = irc.state.nickToHostmask(nick)
                if nick == irc.nick:
                    # Must be a sendMsg so he joins the channel before MODEing.
                    irc.sendMsg(ircmsgs.join(channel))
                    deop = True
                if self._isProtected(channel, hostmask):
                    deop = True
                    irc.queueMsg(ircmsgs.invite(channel, msg.args[1]))
            if deop:
                deop = False
                if self.configurables.get('revenge', channel):
                    self._revenge(irc, channel, msg.prefix)
                else:
                    irc.queueMsg(ircmsgs.deop(channel, msg.nick))

    def doMode(self, irc, msg):
        if not self.started:
            debug.msg('Enforcer not started.', 'normal')
            return
        channel = msg.args[0]
        if not ircutils.isChannel(channel) or msg.nick == self.chanserv:
            return
        if msg.nick != irc.nick and\
           not ircdb.checkCapability(msg.prefix, _chanCap(channel, 'op')):
            for (mode, value) in ircutils.separateModes(msg.args[1:]):
                if value == msg.nick:
                    continue
                elif mode == '+o' and value != irc.nick:
                    hostmask = irc.state.nickToHostmask(value)
                    if ircdb.checkCapability(channel,
                                           ircdb.makeAntiCapability('op')):
                        irc.queueMsg(ircmsgs.deop(channel, value))
                elif mode == '+h' and value != irc.nick:
                    hostmask = irc.state.nickToHostmask(value)
                    if ircdb.checkCapability(channel,
                                           ircdb.makeAntiCapability('halfop')):
                        irc.queueMsg(ircmsgs.dehalfop(channel, value))
                elif mode == '+v' and value != irc.nick:
                    hostmask = irc.state.nickToHostmask(value)
                    if ircdb.checkCapability(channel,
                                           ircdb.makeAntiCapability('voice')):
                        irc.queueMsg(ircmsgs.devoice(channel, value))
                elif mode == '-o':
                    hostmask = irc.state.nickToHostmask(value)
                    if self._isProtected(channel, hostmask):
                        irc.queueMsg(ircmsgs.op(channel, value))
                        if self.configurables.get('revenge', channel):
                            self._revenge(irc, channel, msg.prefix)
                        else:
                            irc.queueMsg(ircmsgs.deop(channel, msg.nick))
                elif mode == '-h':
                    hostmask = irc.state.nickToHostmask(value)
                    if self._isProtected(channel, hostmask):
                        irc.queueMsg(ircmsgs.halfop(channel, value))
                        if self.configurables.get('revenge', channel):
                            self._revenge(irc, channel, msg.prefix)
                        else:
                            irc.queueMsg(ircmsgs.deop(channel, msg.nick))
                elif mode == '-v':
                    hostmask = irc.state.nickToHostmask(value)
                    if self._isProtected(channel, hostmask):
                        irc.queueMsg(ircmsgs.voice(channel, value))
                        if self.configurables.get('revenge', channel):
                            self._revenge(irc, channel, msg.prefix)
                        else:
                            irc.queueMsg(ircmsgs.deop(channel, msg.nick))
                elif mode == '+b':
                    # To be safe, only #channel.ops are allowed to ban.
                    if not ircdb.checkCapability(msg.prefix,
                                                 _chanCap(channel, 'op')):
                        irc.queueMsg(ircmsgs.unban(channel, value))
                        if self.configurables.get('revenge', channel):
                            self._revenge(irc, channel, msg.prefix)
                        else:
                            irc.queueMsg(ircmsgs.deop(channel, msg.nick))

    def __call__(self, irc, msg):
        if self.started:
            if ircutils.isUserHostmask(msg.prefix) and \
               not ircutils.nickEqual(msg.nick, self.chanserv):
                return callbacks.Privmsg.__call__(self, irc, msg)
        else:
            debug.msg('Enforcer plugin not started.  '
                      'Give the bot the start command.', 'normal')


Class = Enforcer
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
