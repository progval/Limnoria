###
# Copyright (c) 2004, Jeremiah Fincher
# Copyright (c) 2009, James Vega
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
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.schedule as schedule
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('AutoMode')

class Continue(Exception):
    pass # Used below, look in the "do" function nested in doJoin.

class AutoMode(callbacks.Plugin):
    def doJoin(self, irc, msg):
        channel = msg.args[0]
        if ircutils.strEqual(irc.nick, msg.nick):
            return
        if not self.registryValue('enable', channel):
            return
        fallthrough = self.registryValue('fallthrough', channel)
        def do(type):
            cap = ircdb.makeChannelCapability(channel, type)
            if ircdb.checkCapability(msg.prefix, cap,
                    ignoreOwner=not self.registryValue('owner')):
                if self.registryValue(type, channel):
                    self.log.info('Scheduling auto-%s of %s in %s.',
                                  type, msg.prefix, channel)
                    msgmaker = getattr(ircmsgs, type)
                    schedule_msg(msgmaker(channel, msg.nick))
                    raise Continue # Even if fallthrough, let's only do one.
                elif not fallthrough:
                    self.log.debug('%s has %s, but supybot.plugins.AutoMode.%s'
                                   ' is not enabled in %s, refusing to fall '
                                   'through.', msg.prefix, cap, type, channel)
                    raise Continue
        def schedule_msg(msg):
            def f():
                irc.queueMsg(msg)
            delay = self.registryValue('delay', channel)
            if delay:
                schedule.addEvent(f, time.time() + delay)
            else:
                f()
        try:
            do('op')
            if 'h' in irc.state.supported['prefix']:
                do('halfop')
            do('voice')
        except Continue:
            return
        c = ircdb.channels.getChannel(channel)
        if c.checkBan(msg.prefix) and self.registryValue('ban', channel):
            period = self.registryValue('ban.period', channel)
            if period:
                def unban():
                    try:
                        if msg.prefix in irc.state.channels[channel].bans:
                            irc.queueMsg(ircmsgs.unban(channel, msg.prefix))
                    except KeyError:
                        # We're not in the channel anymore.
                        pass
                schedule.addEvent(unban, time.time()+period)
            banmask =conf.supybot.protocols.irc.banmask.makeBanmask(msg.prefix)
            irc.queueMsg(ircmsgs.ban(channel, banmask))
            irc.queueMsg(ircmsgs.kick(channel, msg.nick))


Class = AutoMode

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
