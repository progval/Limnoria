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
Warns people when they join a channel if their ident is root.
"""

__revision__ = "$Id$"

import plugins

import conf
import ircmsgs
import ircutils
import registry
import callbacks


conf.registerPlugin('RootWarner')
conf.registerChannelValue(conf.supybot.plugins.RootWarner, 'warn',
    registry.Boolean(True, """Determines whether the bot will warn people who
    join the channel with an ident of 'root' or '~root'."""))
conf.registerChannelValue(conf.supybot.plugins.RootWarner, 'warning',
    registry.NormalizedString("""Don't IRC as root -- it's very possible that
    there's a security flaw latent in your IRC client (remember the BitchX
    format string vulnerabilities of days past?) and if you're IRCing as root,
    your entire box could be compromised.""", """Determines the message that is
    to be sent to users joining the channel with an ident of 'root' or '~root'.
    """))
conf.registerChannelValue(conf.supybot.plugins.RootWarner, 'kick',
    registry.Boolean(False, """Determines whether the bot will kick people who
    join the channel with an ident of 'root' or '~root'."""))

class RootWarner(callbacks.Privmsg):
    def doJoin(self, irc, msg):
        user = ircutils.userFromHostmask(msg.prefix)
        if user == 'root' or user == '~root':
            channel = msg.args[0]
            s = self.registryValue('warning', channel)
            if self.registryValue('warn', channel):
                irc.queueMsg(ircmsgs.notice(msg.nick, s))
            if self.registryValue('kick', channel):
                irc.queueMsg(ircmsgs.kick(channel, msg.nick, s))

Class = RootWarner
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
