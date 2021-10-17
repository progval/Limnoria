###
# Copyright (c) 2004, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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

import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Protector')

class Protector(callbacks.Plugin):
    """Prevents users from doing things they are not supposed to do on a channel,
    even if they have +o or +h."""
    def isImmune(self, irc, msg):
        if not ircutils.isUserHostmask(msg.prefix):
            self.log.debug('%q is immune, it\'s a server.', msg)
            return True # It's a server prefix.
        if ircutils.strEqual(msg.nick, irc.nick):
            self.log.debug('%q is immune, it\'s me.', msg)
            return True # It's the bot itself.
        if msg.nick in self.registryValue('immune', msg.channel, irc.network):
            self.log.debug('%q is immune, it\'s configured to be immune.', msg)
            return True
        return False

    def isOp(self, irc, channel, hostmask):
        cap = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(hostmask, cap):
            self.log.debug('%s is an op on %s, it has %s.',
                           hostmask, channel, cap)
            return True
        if ircutils.strEqual(hostmask, irc.prefix):
            return True
        return False

    def isProtected(self, irc, channel, hostmask):
        cap = ircdb.makeChannelCapability(channel, 'protected')
        if ircdb.checkCapability(hostmask, cap):
            self.log.debug('%s is protected on %s, it has %s.',
                           hostmask, channel, cap)
            return True
        if ircutils.strEqual(hostmask, irc.prefix):
            return True
        return False

    def demote(self, irc, channel, nick):
        irc.queueMsg(ircmsgs.deop(channel, nick))

    def __call__(self, irc, msg):
        def ignore(reason):
            self.log.debug('Ignoring %q, %s.', msg, reason)
        if not msg.args:
            ignore('no msg.args')
        elif not msg.channel:
            ignore('not on a channel')
        elif not self.registryValue('enable', msg.channel, irc.network):
            ignore('supybot.plugins.Protector.enable is False.')
        elif msg.channel not in irc.state.channels:
            # One has to wonder how this would happen, but just in case...
            ignore('bot isn\'t in channel')
        elif irc.nick not in irc.state.channels[msg.channel].ops:
            ignore('bot is not opped')
        elif msg.nick not in irc.state.channels[msg.channel].users:
            ignore('sender is not in channel (ChanServ, maybe?)')
        elif msg.nick not in irc.state.channels[msg.channel].ops:
            ignore('sender is not an op in channel (IRCOP, maybe?)')
        elif self.isImmune(irc, msg):
            ignore('sender is immune')
        else:
            super(Protector, self).__call__(irc, msg)

    def doMode(self, irc, msg):
        channel = msg.channel
        chanOp = ircdb.makeChannelCapability(channel, 'op')
        chanVoice = ircdb.makeChannelCapability(channel, 'voice')
        chanHalfOp = ircdb.makeChannelCapability(channel, 'halfop')
        if not ircdb.checkCapability(msg.prefix, chanOp):
            irc.sendMsg(ircmsgs.deop(channel, msg.nick))
        for (mode, value) in ircutils.separateModes(msg.args[1:]):
            if not value:
                continue
            if ircutils.strEqual(value, msg.nick):
                # We allow someone to mode themselves to oblivion.
                continue
            if irc.isNick(value):
                hostmask = irc.state.nickToHostmask(value)
                if mode == '+o':
                    if not self.isOp(irc, channel, hostmask):
                        irc.queueMsg(ircmsgs.deop(channel, value))
                elif mode == '+h':
                    if not ircdb.checkCapability(hostmask, chanHalfOp):
                         irc.queueMsg(ircmsgs.dehalfop(channel, value))
                elif mode == '+v':
                    if not ircdb.checkCapability(hostmask, chanVoice):
                        irc.queueMsg(ircmsgs.devoice(channel, value))
                elif mode == '-o':
                    if ircdb.checkCapability(hostmask, chanOp):
                        irc.queueMsg(ircmsgs.op(channel, value))
                elif mode == '-h':
                    if ircdb.checkCapability(hostmask, chanOp):
                        irc.queueMsg(ircmsgs.halfop(channel, value))
                elif mode == '-v':
                    if ircdb.checkCapability(hostmask, chanOp):
                        irc.queueMsg(ircmsgs.voice(channel, value))
            else:
                assert ircutils.isUserHostmask(value)
                # Handle bans.

    def doKick(self, irc, msg):
        channel = msg.channel
        kicked = msg.args[1].split(',')
        protected = []
        for nick in kicked:
            if ircutils.strEqual(nick, irc.nick):
                return # Channel will handle the rejoin.
        for nick in kicked:
            hostmask = irc.state.nickToHostmask(nick)
            if self.isProtected(irc, channel, hostmask):
                self.log.info('%s was kicked from %s and is protected; '
                              'inviting back.', hostmask, channel)
                hostmask = '%s!%s' % (nick, irc.state.nickToHostmask(nick))
                protected.append(nick)
                bans = []
                for banmask in irc.state.channels[channel].bans:
                    if ircutils.hostmaskPatternEqual(banmask, hostmask):
                        bans.append(banmask)
                irc.queueMsg(ircmsgs.unbans(channel, bans))
                irc.queueMsg(ircmsgs.invite(nick, channel))
        if not self.isOp(irc, channel, msg.prefix):
            self.demote(irc, channel, msg.nick)


Class = Protector

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
