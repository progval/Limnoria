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
This plugin handles channel limits (MODE +l).
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch
__contributors__ = {}


import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Limiter', True)

conf.registerPlugin('Limiter')
conf.registerChannelValue(conf.supybot.plugins.Limiter, 'enable',
    registry.Boolean(False, """Determines whether the bot will maintain the
    channel limit to be slightly above the current number of people in the
    channel, in order to make clone/drone attacks harder."""))
conf.registerChannelValue(conf.supybot.plugins.Limiter, 'minimumExcess',
    registry.PositiveInteger(5, """Determines the minimum number of free
    spots that will be saved when limits are being enforced.  This should
    always be smaller than supybot.plugins.Limiter.limit.maximumExcess."""))
conf.registerChannelValue(conf.supybot.plugins.Limiter, 'maximumExcess',
    registry.PositiveInteger(10, """Determines the maximum number of free spots
    that will be saved when limits are being enforced.  This should always be
    larger than supybot.plugins.Limiter.limit.minimumExcess."""))

class Limiter(callbacks.Privmsg):
    def _enforce(self, irc, limit):
        irc.queueMsg(limit)
        irc.noReply()

    def _enforceLimit(self, irc, channel):
        if self.registryValue('enable', channel):
            maximum = self.registryValue('maximumExcess', channel)
            minimum = self.registryValue('minimumExcess', channel)
            assert maximum > minimum
            currentUsers = len(irc.state.channels[channel].users)
            currentLimit = irc.state.channels[channel].modes.get('l', 0)
            if currentLimit - currentUsers < minimum:
                self._enforce(irc, ircmsgs.limit(channel,currentUsers+maximum))
            elif currentLimit - currentUsers > maximum:
                self._enforce(irc, ircmsgs.limit(channel,currentUsers-minimum))

    def doJoin(self, irc, msg):
        if not ircutils.strEqual(msg.nick, irc.nick):
            self._enforceLimit(irc, msg.args[0])
    doPart = doJoin
    doKick = doJoin

    def doQuit(self, irc, msg):
        for channel in irc.state.channels:
            self._enforceLimit(irc, channel)


Class = Limiter

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
