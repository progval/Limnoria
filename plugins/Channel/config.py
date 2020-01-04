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


import supybot.conf as conf
import supybot.utils as utils
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Channel')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Channel', True)

Channel = conf.registerPlugin('Channel')
conf.registerChannelValue(Channel, 'alwaysRejoin',
    registry.Boolean(True, _("""Determines whether the bot will always try to
    rejoin a channel whenever it's kicked from the channel.""")))
conf.registerChannelValue(Channel, 'nicksInPrivate',
    registry.Boolean(True, _("""Determines whether the output of 'nicks' will
    be sent in private. This prevents mass-highlights of a channel's users,
    accidental or on purpose.""")))
conf.registerChannelValue(Channel, 'rejoinDelay',
    registry.NonNegativeInteger(0, _("""Determines how many seconds the bot will wait
    before rejoining a channel if kicked and
    supybot.plugins.Channel.alwaysRejoin is on.""")))
conf.registerChannelValue(Channel, 'partMsg',
    registry.String('Limnoria $version', _("""Determines what part message should be
        used by default. If the part command is called without a part message,
        this will be used. If this value is empty, then no part message will
        be used (they are optional in the IRC protocol). The standard
        substitutions ($version, $nick, etc.) are all handled appropriately.""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
