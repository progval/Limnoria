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
JOINs, etc. to make sure they match the channel's config.  Also handles
auto-opping, auto-halfopping, or auto-voicing, as well as cycling an otherwise
empty channel in order to get ops.
"""

__revision__ = "$Id$"

import plugins

import conf
import ircdb
import ircmsgs
import plugins
import ircutils
import privmsgs
import registry
import callbacks

def configure(advanced):
    from questions import output, expect, anything, something, yn
    conf.registerPlugin('Enforcer', True)
    chanserv = anything("""What\'s the name of ChanServ on your network?  If
                           there is no ChanServ on your network, just press
                           enter without entering anything.""")
    revenge = yn('Do you want the bot to take revenge on rule breakers?')
    conf.supybot.plugins.Enforcer.ChanServ.set(chanserv)
    conf.supybot.plugins.Enforcer.takeRevenge.setValue(revenge)

class ValidNickOrEmptyString(registry.String):
    def setValue(self, v):
        if v and not ircutils.isNick(v):
            raise registry.InvalidRegistryValue, \
                  'Value must be a valid nick or the empty string.'
        self.value = v
            
conf.registerPlugin('Enforcer')
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'autoOp',
    registry.Boolean(False, """Determines whether the bot will automatically op
    people with the <channel>,op capability when they join the channel."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'autoHalfop',
    registry.Boolean(False, """Determines whether the bot will automatically
    halfop people with the <channel>,halfop capability when they join the
    channel."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'autoVoice',
    registry.Boolean(False, """Determines whether the bot will automatically
    voice people with the <channel>,voice capability when they join the
    channel."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'takeRevenge',
    registry.Boolean(False, """Determines whether the bot will take revenge on
    people who do things it doesn't like (somewhat like 'bitch mode' in other
    IRC bots)."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'takeRevengeOnOps',
    registry.Boolean(False, """Determines whether the bot will even take
    revenge on ops (people with the #channel,op capability) who violate the
    channel configuration."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'cycleToGetOps',
    registry.Boolean(True, """Determines whether the bot will cycle the channel
    if it doesn't have ops and there's no one else in the channel."""))
# This is a network value, not a channel value.
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'ChanServ',
    ValidNickOrEmptyString('', """Determines what nick the bot will consider to
    be the ChanServ on the network.  ChanServ (on networks that support it) is
    obviously beyond our abilities to enforce, and so we would ignore all
    messages from it."""))

_chanCap = ircdb.makeChannelCapability
class Enforcer(callbacks.Privmsg):
    """Manages various things concerning channel security.  Check out the
    supybot.plugins.Enforcer.autoOp, supybot.plugins.Enforcer.autoHalfop,
    supybot.plugins.Enforcer.autoVoice, supybot.plugins.Enforcer.takeRevenge,
    supybot.plugins.Enforcer.cycleToGetOps, and
    supybot.plugins.Enforcer.ChanServ to configure the behavior of this plugin.
    """
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.topics = ircutils.IrcDict()
        
    def doJoin(self, irc, msg):
        channel = msg.args[0]
        c = ircdb.channels.getChannel(channel)
        if c.checkBan(msg.prefix):
            irc.queueMsg(ircmsgs.ban(channel, ircutils.banmask(msg.prefix)))
            irc.queueMsg(ircmsgs.kick(channel, msg.nick))
        elif ircdb.checkCapability(msg.prefix, _chanCap(channel, 'op')):
            if self.registryValue('autoOp', channel):
                irc.queueMsg(ircmsgs.op(channel, msg.nick))
        elif ircdb.checkCapability(msg.prefix, _chanCap(channel, 'halfop')):
            if self.registryValue('autoHalfop', channel):
                irc.queueMsg(ircmsgs.halfop(channel, msg.nick))
        elif ircdb.checkCapability(msg.prefix, _chanCap(channel, 'voice')):
            if self.registryValue('autoVoice', channel):
                irc.queueMsg(ircmsgs.voice(channel, msg.nick))

    def doTopic(self, irc, msg):
        channel = msg.args[0]
        topic = msg.args[1]
        if msg.nick != irc.nick and channel in self.topics and \
           not ircdb.checkCapabilities(msg.prefix,
                                       (_chanCap(channel, 'op'),
                                        _chanCap(channel, 'topic'))):
            irc.queueMsg(ircmsgs.topic(channel, self.topics[channel]))
            if self.registryValue('takeRevenge', channel):
                irc.queueMsg(ircmsgs.kick(channel, msg.nick,
                                          conf.supybot.replies.noCapability() %
                                          _chanCap(channel, 'topic')))
        else:
            self.topics[channel] = msg.args[1]

    def do332(self, irc, msg):
        # This command gets sent right after joining a channel.
        (channel, topic) = msg.args[1:]
        self.topics[channel] = topic

    def _isProtected(self, channel, hostmask):
        capabilities = [_chanCap(channel, 'op'),_chanCap(channel, 'protected')]
        return ircdb.checkCapabilities(hostmask, capabilities)

    def _isPowerful(self, irc, msg):
        if msg.nick == irc.nick:
            return True # It's me.
        if not ircutils.isUserHostmask(msg.prefix):
            return True # It's a server.
        chanserv = self.registryValue('ChanServ')
        if ircutils.nickEqual(msg.nick, chanserv):
            return True # It's ChanServ.
        capability = _chanCap(msg.args[0], 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            return True # It's a chanop.
        return False    # Default.

    def _revenge(self, irc, channel, hostmask):
        irc.queueMsg(ircmsgs.ban(channel, ircutils.banmask(hostmask)))
        irc.queueMsg(ircmsgs.kick(channel,ircutils.nickFromHostmask(hostmask)))

    def doKick(self, irc, msg):
        channel = msg.args[0]
        kicked = msg.args[1].split(',')
        deop = False
        if not self._isPowerful(irc, msg) or \
           self.registryValue('takeRevengeOnOps', channel):
            for nick in kicked:
                hostmask = irc.state.nickToHostmask(nick)
                if nick == irc.nick:
                    # Must be a sendMsg so he joins the channel before MODEing.
                    irc.sendMsg(ircmsgs.join(channel))
                    deop = True
                if self._isProtected(channel, hostmask):
                    deop = True
                    irc.queueMsg(ircmsgs.invite(msg.args[1], channel))
            if deop:
                deop = False
                if self.registryValue('takeRevenge', channel):
                    self._revenge(irc, channel, msg.prefix)
                else:
                    irc.queueMsg(ircmsgs.deop(channel, msg.nick))

    def doMode(self, irc, msg):
        channel = msg.args[0]
        chanserv = self.registryValue('ChanServ', channel)
        if not ircutils.isChannel(channel) or \
           (self._isPowerful(irc, msg) and
            not self.registryValue('takeRevengeOnOps', channel)):
            return
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
                    if self.registryValue('takeRevenge', channel):
                        self._revenge(irc, channel, msg.prefix)
                    else:
                        irc.queueMsg(ircmsgs.deop(channel, msg.nick))
            elif mode == '-h':
                hostmask = irc.state.nickToHostmask(value)
                if self._isProtected(channel, hostmask):
                    irc.queueMsg(ircmsgs.halfop(channel, value))
                    if self.registryValue('takeRevenge', channel):
                        self._revenge(irc, channel, msg.prefix)
                    else:
                        irc.queueMsg(ircmsgs.deop(channel, msg.nick))
            elif mode == '-v':
                hostmask = irc.state.nickToHostmask(value)
                if self._isProtected(channel, hostmask):
                    irc.queueMsg(ircmsgs.voice(channel, value))
                    if self.registryValue('takeRevenge', channel):
                        self._revenge(irc, channel, msg.prefix)
                    else:
                        irc.queueMsg(ircmsgs.deop(channel, msg.nick))
            elif mode == '+b':
                irc.queueMsg(ircmsgs.unban(channel, value))
                if self.registryValue('takeRevenge', channel):
                    self._revenge(irc, channel, msg.prefix)
                else:
                    irc.queueMsg(ircmsgs.deop(channel, msg.nick))

    def _cycle(self, irc, channel):
        if self.registryValue('cycleToGetOps', channel):
            if 'i' not in irc.state.channels[channel].modes:
                # What about keywords?
                self.log.info('Cycling %s: I\'m the only one left.', channel)
                irc.queueMsg(ircmsgs.part(channel))
                irc.queueMsg(ircmsgs.join(channel))
            else:
                self.log.warning('Not cycling %s: it\'s +i', channel)
            
    def doPart(self, irc, msg):
        if msg.prefix != irc.prefix:
            channel = msg.args[0]
            c = irc.state.channels[channel]
            if len(c.users) == 1:
                if irc.nick not in c.ops:
                    self._cycle(irc, channel)

    def doQuit(self, irc, msg):
        for (channel, c) in irc.state.channels.iteritems():
            if len(c.users) == 1:
                self._cycle(irc, channel)

    def __call__(self, irc, msg):
        chanserv = self.registryValue('ChanServ', irc.network)
        if chanserv:
            if ircutils.isUserHostmask(msg.prefix):
                if msg.nick != chanserv:
                    callbacks.Privmsg.__call__(self, irc, msg)
        else:
            callbacks.Privmsg.__call__(self, irc, msg)


Class = Enforcer
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
