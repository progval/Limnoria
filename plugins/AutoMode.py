###
# Copyright (c) 2004, Jeremiah Fincher
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
Automatically ops, voices, or halfops, or bans people when they join a channel,
according to their capabilities.  If you want your bot automatically op users
when they join your channel, this is the plugin to load.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch
__contributors__ = {}

import time

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.schedule as schedule
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('AutoMode', True)

AutoMode = conf.registerPlugin('AutoMode')
conf.registerChannelValue(AutoMode, 'enable',
    registry.Boolean(True, """Determines whether this plugin is enabled."""))
conf.registerChannelValue(AutoMode, 'fallthrough',
    registry.Boolean(False, """Determines whether the bot will "fall through" to
    halfop/voicing when auto-opping is turned off but auto-halfopping/voicing
    are turned on."""))
conf.registerChannelValue(AutoMode, 'op',
    registry.Boolean(True, """Determines whether the bot will automatically op
    people with the <channel>,op capability when they join the channel."""))
conf.registerChannelValue(AutoMode, 'halfop',
    registry.Boolean(True, """Determines whether the bot will automatically
    halfop people with the <channel>,halfop capability when they join the
    channel."""))
conf.registerChannelValue(AutoMode, 'voice',
    registry.Boolean(True, """Determines whether the bot will automatically
    voice people with the <channel>,voice capability when they join the
    channel."""))
conf.registerChannelValue(AutoMode, 'ban',
    registry.Boolean(True, """Determines whether the bot will automatically ban
    people who join the channel and are on the banlist."""))
conf.registerChannelValue(AutoMode.ban, 'period',
    registry.PositiveInteger(86400, """Determines how many seconds the bot will
    automatically ban a person when banning."""))

class Continue(Exception):
    pass # Used below, look in the "do" function nested in doJoin.

class AutoMode(callbacks.Privmsg):
    def doJoin(self, irc, msg):
        channel = msg.args[0]
        if ircutils.strEqual(irc.nick, msg.nick):
            return
        if not self.registryValue('enable', channel):
            return
        fallthrough = self.registryValue('fallthrough', channel)
        def do(type):
            cap = ircdb.makeChannelCapability(channel, type)
            if ircdb.checkCapability(msg.prefix, cap):
                if self.registryValue(type, channel):
                    self.log.info('Sending auto-%s of %s in %s.',
                                  type, msg.prefix, channel)
                    msgmaker = getattr(ircmsgs, type)
                    irc.queueMsg(msgmaker(channel, msg.nick))
                    raise Continue # Even if fallthrough, let's only do one.
                elif not fallthrough:
                    self.log.debug('%s has %s, but supybot.plugins.AutoMode.%s'
                                   ' is not enabled in %s, refusing to fall '
                                   'through.', msg.prefix, cap, type, channel)
                    raise Continue
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
            irc.queueMsg(ircmsgs.ban(channel, msg.prefix))
            irc.queueMsg(ircmsgs.kick(channel, msg.nick))


Class = AutoMode

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
