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
Handles standard CTCP responses to PING, TIME, SOURCE, VERSION, USERINFO,
and FINGER.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import os
import sys
import time

sys.path.append(os.pardir)

import supybot.conf as conf
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks

conf.registerPlugin('Ctcp')
conf.registerGlobalValue(conf.supybot.abuse.flood, 'ctcp',
    registry.Boolean(True, """Determines whether the bot will defend itself
    against CTCP flooding."""))
conf.registerGlobalValue(conf.supybot.abuse.flood.ctcp, 'maximum',
    registry.PositiveInteger(5, """Determines how many CTCP messages (not
    including actions) the bot will reply to from a given user in a minute.
    If a user sends more than this many CTCP messages in a 60 second period,
    the bot will ignore CTCP messages from this user for
    supybot.abuse.flood.ctcp.punishment seconds."""))
conf.registerGlobalValue(conf.supybot.abuse.flood.ctcp, 'punishment',
    registry.PositiveInteger(300, """Determines how many seconds the bot will
    ignore CTCP messages from users who flood it with CTCP messages."""))

class Ctcp(callbacks.PrivmsgRegexp):
    public = False
    def __init__(self):
        self.__parent = super(Ctcp, self)
        self.__parent.__init__()
        self.ignores = ircutils.IrcDict()
        self.floods = ircutils.FloodQueue(60)

    def callCommand(self, name, irc, msg, *L, **kwargs):
        if conf.supybot.abuse.flood.ctcp():
            now = time.time()
            for (ignore, expiration) in self.ignores.items():
                if expiration < now:
                    del self.ignores[ignore]
                elif ircutils.hostmaskPatternEqual(ignore, msg.prefix):
                        return
            self.floods.enqueue(msg)
            max = conf.supybot.abuse.flood.ctcp.maximum()
            if self.floods.len(msg) > max:
                expires = conf.supybot.abuse.flood.ctcp.punishment()
                self.log.warning('Apparent CTCP flood from %s, '
                                 'ignoring CTCP messages for %s seconds.',
                                 msg.prefix, expires)
                ignoreMask = '*!%s@%s' % (msg.user, msg.host)
                self.ignores[ignoreMask] = now + expires
                return
        self.__parent.callCommand(name, irc, msg, *L, **kwargs)
        
    def _reply(self, irc, msg, s):
        s = '\x01%s\x01' % s
        irc.reply(s, notice=True, private=True, to=msg.nick)

    def ping(self, irc, msg, match):
        "\x01PING (.*)\x01"
        self.log.info('Received CTCP PING from %s', msg.prefix)
        self._reply(irc, msg, 'PING %s' % match.group(1))

    def version(self, irc, msg, match):
        "\x01VERSION\x01"
        self.log.info('Received CTCP VERSION from %s', msg.prefix)
        self._reply(irc, msg, 'VERSION Supybot %s' % conf.version)

    def userinfo(self, irc, msg, match):
        "\x01USERINFO\x01"
        self.log.info('Received CTCP USERINFO from %s', msg.prefix)
        self._reply(irc, msg, 'USERINFO')

    def time(self, irc, msg, match):
        "\x01TIME\x01"
        self.log.info('Received CTCP TIME from %s' % msg.prefix)
        self._reply(irc, msg, time.ctime())

    def finger(self, irc, msg, match):
        "\x01FINGER\x01"
        self.log.info('Received CTCP FINGER from %s' % msg.prefix)
        self._reply(irc, msg, 'Supybot, the best Python IRC bot in existence!')

    def source(self, irc, msg, match):
        "\x01SOURCE\x01"
        self.log.info('Received CTCP SOURCE from %s' % msg.prefix)
        self._reply(irc, msg, 'http://www.sourceforge.net/projects/supybot/')

Class = Ctcp
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
