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

import re
import time

import supybot.log as log
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
            try:
                if ircdb.checkCapability(msg.prefix, cap,
                        ignoreOwner=not self.registryValue('owner')):
                    if self.registryValue(type, channel):
                        self.log.info('Scheduling auto-%s of %s in %s.',
                                      type, msg.prefix, channel)
                        def dismiss():
                            """Determines whether or not a mode has already
                            been applied."""
                            l = getattr(irc.state.channels[channel], type+'s')
                            return (msg.nick in l)
                        msgmaker = getattr(ircmsgs, type)
                        schedule_msg(msgmaker(channel, msg.nick),
                                dismiss)
                        raise Continue # Even if fallthrough, let's only do one.
                    elif not fallthrough:
                        self.log.debug('%s has %s, but supybot.plugins.AutoMode.%s'
                                       ' is not enabled in %s, refusing to fall '
                                       'through.', msg.prefix, cap, type, channel)
                        raise Continue
            except KeyError:
                pass
        def schedule_msg(msg, dismiss):
            def f():
                if not dismiss():
                    irc.queueMsg(msg)
                else:
                    self.log.info('Dismissing auto-mode for %s.' % msg.nick)
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
        finally:
            user = ircdb.users.getUser(ircdb.users.getUserId(msg.prefix))
            pattern = re.compile('-|\+')
            for item in self.registryValue('extra', channel):
                try:
                    username, modes = pattern.split(item, maxsplit=1)
                    modes = item[len(username)] + modes
                except ValueError: # No - or + in item
                    log.error(('%r is not a valid item for '
                            'supybot.plugins.AutoMode.extra') % item)
                    continue
                if username != user.name:
                    continue
                else:
                    self.log.info('Scheduling auto-modes %s of %s in %s.',
                                  modes, msg.prefix, channel)
                    modes = [modes] + \
                            ([msg.nick]*len(pattern.sub('', modes)))
                    schedule_msg(ircmsgs.mode(channel, modes), lambda :False)
                    break
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
