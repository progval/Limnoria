###
# Copyright (c) 2004-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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

from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Limiter')

class Limiter(callbacks.Plugin):
    """In order to use this plugin, its config values need to be properly
    setup.  supybot.plugins.Limiter.enable needs to be set to True and
    supybot.plugins.Limiter.{maximumExcess,minimumExcess} should be set to
    values appropriate to your channel (if the defaults aren't satisfactory).
    Once these are set, and someone enters/leaves the channel, Supybot will
    start setting the proper +l modes.
    """
    def _enforce(self, irc, limit):
        irc.queueMsg(limit)
        irc.noReply()

    def _enforceLimit(self, irc, channel):
        if self.registryValue('enable', channel, irc.network):
            maximum = self.registryValue('maximumExcess', channel, irc.network)
            minimum = self.registryValue('minimumExcess', channel, irc.network)
            assert maximum > minimum
            currentUsers = len(irc.state.channels[channel].users)
            currentLimit = irc.state.channels[channel].modes.get('l', 0)
            if currentLimit - currentUsers < minimum:
                self._enforce(irc, ircmsgs.limit(channel,currentUsers+maximum))
            elif currentLimit - currentUsers > maximum:
                self._enforce(irc, ircmsgs.limit(channel,currentUsers+minimum))

    def doJoin(self, irc, msg):
        if not ircutils.strEqual(msg.nick, irc.nick):
            irc = callbacks.SimpleProxy(irc, msg)
            self._enforceLimit(irc, msg.channel)
    doPart = doJoin
    doKick = doJoin

    def doQuit(self, irc, msg):
        for channel in msg.tagged('channels'):
            self._enforceLimit(irc, channel)
Limiter = internationalizeDocstring(Limiter)

Class = Limiter


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
