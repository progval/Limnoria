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
Enforces capabilities on a channel, watching MODEs, KICKs,
JOINs, etc. to make sure they match the channel's config.  Also handles
auto-opping, auto-halfopping, or auto-voicing, as well as cycling an otherwise
empty channel in order to get ops.
"""

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import supybot.plugins as plugins

import time

import supybot.log as log
import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.schedule as schedule
import supybot.callbacks as callbacks

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
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
# XXX We should look into making *all* plugin values ChannelValues and allowing
#     all channels to disable any plugin in their channel.
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'enforce',
    registry.Boolean(True, """Determines whether the bot will enforce
    capabilities on this channel.  Basically, if False, it 'turns off' the
    plugin for this channel."""))
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
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'autoBan',
    registry.Boolean(True, """Determines whether the bot will automatically ban
    people who join the channel and are on the banlist."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'banPeriod',
    registry.PositiveInteger(86400, """Determines how many seconds the bot will
    automatically ban a person for when banning."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'takeRevenge',
    registry.Boolean(True, """Determines whether the bot will take revenge on
    people who do things it doesn't like (somewhat like 'bitch mode' in other
    IRC bots)."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer.takeRevenge, 'onOps',
    registry.Boolean(False, """Determines whether the bot will even take
    revenge on ops (people with the #channel,op capability) who violate the
    channel configuration."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'cycleToGetOps',
    registry.Boolean(False, """Determines whether the bot will cycle the channel
    if it doesn't have ops and there's no one else in the channel."""))
# This is a network value, not a channel value.
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'ChanServ',
    ValidNickOrEmptyString('', """Determines what nick the bot will consider to
    be the ChanServ on the network.  ChanServ (on networks that support it) is
    obviously beyond our abilities to enforce, and so we would ignore all
    messages from it."""))

# Limit stuff
conf.registerChannelValue(conf.supybot.plugins.Enforcer, 'limit',
    registry.Boolean(False, """Determines whether the bot will maintain the
    channel limit to be slightly above the current number of people in the
    channel, in order to make clone/drone attacks harder."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer.limit, 'minimumExcess',
    registry.PositiveInteger(5, """Determines the minimum number of free
    spots that will be saved when limits are being enforced.  This should
    always be smaller than supybot.plugins.Enforcer.limit.maximumExcess."""))
conf.registerChannelValue(conf.supybot.plugins.Enforcer.limit, 'maximumExcess',
    registry.PositiveInteger(10, """Determines the maximum number of free spots
    that will be saved when limits are being enforced.  This should always be
    larger than supybot.plugins.Enforcer.limit.minimumExcess."""))

_chanCap = ircdb.makeChannelCapability
class Enforcer(callbacks.Privmsg):
    """Manages various things concerning channel security.  Check out the
    Enforcer.autoOp, supybot.plugins.Enforcer.autoHalfop,
    supybot.plugins.Enforcer.autoVoice, supybot.plugins.Enforcer.takeRevenge,
    supybot.plugins.Enforcer.cycleToGetOps, and
    supybot.plugins.Enforcer.ChanServ to configure the behavior of this plugin.
    """
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.topics = ircutils.IrcDict()
        self.unbans = {}

    def _enforceLimit(self, irc, channel):
        if self.registryValue('limit', channel):
            maximum = self.registryValue('limit.maximumExcess', channel)
            minimum = self.registryValue('limit.minimumExcess', channel)
            assert maximum > minimum
            currentUsers = len(irc.state.channels[channel].users)
            currentLimit = irc.state.channels[channel].modes.get('l', 0)
            if currentLimit - currentUsers < minimum:
                irc.queueMsg(ircmsgs.limit(channel, currentUsers + maximum))
            elif currentLimit - currentUsers > maximum:
                irc.queueMsg(ircmsgs.limit(channel, currentUsers + minimum))

    def _doBan(self, irc, channel, hostmask):
        nick = ircutils.nickFromHostmask(hostmask)
        banmask = ircutils.banmask(hostmask)
        irc.sendMsg(ircmsgs.ban(channel, banmask))
        irc.sendMsg(ircmsgs.kick(channel, nick))
        period = self.registryValue('banPeriod', channel)
        when = time.time() + period
        if banmask in self.unbans:
            self.log.info('Rescheduling unban of %s for %s.',
                          banmask, log.timestamp(when))
            schedule.rescheduleEvent(self.unbans[banmask], when)
        else:
            def unban():
                irc.queueMsg(ircmsgs.unban(channel, banmask))
                del self.unbans[banmask]
            eventId = schedule.addEvent(unban, when)
            self.unbans[banmask] = eventId
                
    def doJoin(self, irc, msg):
        if ircutils.strEqual(msg.nick, irc.nick):
            return
        channel = msg.args[0]
        c = ircdb.channels.getChannel(channel)
        if c.checkBan(msg.prefix) and self.registryValue('autoBan', channel):
            self._doBan(irc, channel, msg.prefix)
        elif ircdb.checkCapability(msg.prefix, _chanCap(channel, 'op')):
            if self.registryValue('autoOp', channel):
                irc.queueMsg(ircmsgs.op(channel, msg.nick))
        elif ircdb.checkCapability(msg.prefix, _chanCap(channel, 'halfop')):
            if self.registryValue('autoHalfop', channel):
                irc.queueMsg(ircmsgs.halfop(channel, msg.nick))
        elif ircdb.checkCapability(msg.prefix, _chanCap(channel, 'voice')):
            if self.registryValue('autoVoice', channel):
                irc.queueMsg(ircmsgs.voice(channel, msg.nick))
        self._enforceLimit(irc, channel)

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

    def _isPowerful(self, irc, channel, hostmask):
        if not ircutils.isUserHostmask(hostmask):
            return True # It's a server.
        nick = ircutils.nickFromHostmask(hostmask)
        if ircutils.strEqual(nick, irc.nick):
            return True # It's me.
        chanserv = self.registryValue('ChanServ')
        if ircutils.strEqual(nick, chanserv):
            return True # It's ChanServ.
        capability = _chanCap(channel, 'op')
        if ircdb.checkCapability(hostmask, capability):
            return True # It's a chanop.
        return False    # Default.

    def _revenge(self, irc, channel, hostmask):
        nick = ircutils.nickFromHostmask(hostmask)
        if self.registryValue('takeRevenge', channel):
            if self._isPowerful(irc, channel, hostmask) and \
               not self.registryValue('takeRevenge.onOps', channel):
                return
            if irc.nick != nick:
                self._doBan(irc, channel, hostmask)
            else:
                # This can happen if takeRevenge.onOps is True.
                self.log.warning('Tried to take revenge on myself.  '
                                 'Are you sure you want takeRevenge.onOps '
                                 'to be True?')
        elif nick in irc.state.channels[channel].ops:
            irc.sendMsg(ircmsgs.deop(channel, nick))

    def doKick(self, irc, msg):
        channel = msg.args[0]
        kicked = msg.args[1].split(',')
        deop = False
        for nick in kicked:
            hostmask = irc.state.nickToHostmask(nick)
            if ircutils.strEqual(nick, irc.nick):
                # Must be a sendMsg so he joins the channel before MODEing.
                irc.sendMsg(ircmsgs.join(channel))
            if self._isProtected(channel, hostmask):
                irc.queueMsg(ircmsgs.invite(nick, channel))
        self._revenge(irc, channel, msg.prefix)
        self._enforceLimit(irc, channel)

    def doMode(self, irc, msg):
        channel = msg.args[0]
        chanserv = self.registryValue('ChanServ', channel)
        if not ircutils.isChannel(channel):
            return
        if self._isPowerful(irc, channel, msg.prefix):
            if not self.registryValue('takeRevenge.onOps', channel):
                return
        for (mode, value) in ircutils.separateModes(msg.args[1:]):
            if ircutils.strEqual(value, msg.nick):
                continue
            elif mode == '+o':
                hostmask = irc.state.nickToHostmask(value)
                if ircdb.checkCapability(channel,
                                       ircdb.makeAntiCapability('op')):
                    irc.sendMsg(ircmsgs.deop(channel, value))
            elif mode == '+h':
                hostmask = irc.state.nickToHostmask(value)
                if ircdb.checkCapability(channel,
                                       ircdb.makeAntiCapability('halfop')):
                    irc.sendMsg(ircmsgs.dehalfop(channel, value))
            elif mode == '+v':
                hostmask = irc.state.nickToHostmask(value)
                if ircdb.checkCapability(channel,
                                       ircdb.makeAntiCapability('voice')):
                    irc.queueMsg(ircmsgs.devoice(channel, value))
            elif mode == '-o':
                hostmask = irc.state.nickToHostmask(value)
                if self._isProtected(channel, hostmask):
                    self._revenge(irc, channel, msg.prefix)
                    irc.sendMsg(ircmsgs.op(channel, value))
            elif mode == '-h':
                hostmask = irc.state.nickToHostmask(value)
                if self._isProtected(channel, hostmask):
                    self._revenge(irc, channel, msg.prefix)
                    irc.queueMsg(ircmsgs.halfop(channel, value))
            elif mode == '-v':
                hostmask = irc.state.nickToHostmask(value)
                if self._isProtected(channel, hostmask):
                    self._revenge(irc, channel, msg.prefix)
                    irc.queueMsg(ircmsgs.voice(channel, value))
            elif mode == '+b':
                self._revenge(irc, channel, msg.prefix)
                irc.sendMsg(ircmsgs.unban(channel, value))

    def _cycle(self, irc, channel):
        if self.registryValue('cycleToGetOps', channel):
            if 'i' not in irc.state.channels[channel].modes and \
               'k' not in irc.state.channels[channel].modes:
                # XXX We should pull these keywords from the registry.
                self.log.info('Cycling %s: I\'m the only one left.', channel)
                irc.queueMsg(ircmsgs.part(channel))
                irc.queueMsg(ircmsgs.join(channel))
            else:
                self.log.info('Not cycling %s: it\'s +i or +k.', channel)

    def doPart(self, irc, msg):
        if msg.prefix != irc.prefix:
            channel = msg.args[0]
            c = irc.state.channels[channel]
            if len(c.users) == 1:
                if irc.nick not in c.ops:
                    self._cycle(irc, channel)
                    return
            self._enforceLimit(irc, channel)

    def doQuit(self, irc, msg):
        for (channel, c) in irc.state.channels.iteritems():
            if len(c.users) == 1:
                if irc.nick not in c.ops:
                    self._cycle(irc, channel)
                    continue
            self._enforceLimit(irc, channel)

    def __call__(self, irc, msg):
        channel = msg.args[0]
        if ircutils.isChannel(channel) and \
           self.registryValue('enforce', channel):
            chanserv = self.registryValue('ChanServ', irc.network)
            if chanserv:
                if ircutils.isUserHostmask(msg.prefix):
                    if msg.nick != chanserv:
                        callbacks.Privmsg.__call__(self, irc, msg)
            else:
                callbacks.Privmsg.__call__(self, irc, msg)


Class = Enforcer
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
