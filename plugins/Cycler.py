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
Cycles the channel if no one is in it in an attempt to get ops.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch
__contributors__ = {}


import supybot.conf as conf
import supybot.utils as utils
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Cycler', True)

conf.registerPlugin('Cycler')
conf.registerChannelValue(conf.supybot.plugins.Cycler, 'enable',
    registry.Boolean(False, """Determines whether the bot will cycle the channel
    if it doesn't have ops and there's no one else in the channel."""))

class Cycler(callbacks.Privmsg):
    def _cycle(self, irc, channel):
        if self.registryValue('enable', channel) and \
           len(irc.state.channels[channel].users) == 1:
            if 'i' not in irc.state.channels[channel].modes and \
               'k' not in irc.state.channels[channel].modes:
                # XXX We should pull these keywords from the registry.
                self.log.info('Cycling %s: I\'m the only one left.', channel)
                irc.queueMsg(ircmsgs.part(channel))
                networkGroup = conf.supybot.networks.get(irc.network)
                irc.queueMsg(networkGroup.channels.join(channel))
            else:
                self.log.info('Not cycling %s: it\'s +i or +k.', channel)

    def doPart(self, irc, msg):
        if not ircutils.strEqual(msg.nick, irc.nick):
            self._cycle(irc, msg.args[0])
    doKick = doPart

    def doQuit(self, irc, msg):
        for (channel, c) in irc.state.channels.iteritems():
            self._cycle(irc, channel)


Class = Cycler

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
