###
# Copyright (c) 2005, Jeremiah Fincher
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
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('AutoMode')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('AutoMode', True)


AutoMode = conf.registerPlugin('AutoMode')
conf.registerChannelValue(AutoMode, 'enable',
    registry.Boolean(True, _("""Determines whether this plugin is enabled.
    """)))
conf.registerGlobalValue(AutoMode, 'owner',
    registry.Boolean(False, _("""Determines whether this plugin will automode
    owners even if they don't have op/halfop/voice/whatever capability.""")))
conf.registerChannelValue(AutoMode, 'alternativeCapabilities',
    registry.Boolean(True, _("""Determines whether the bot will
    check for 'alternative capabilities' (ie. autoop, autohalfop,
    autovoice) in addition to/instead of classic ones.""")))
conf.registerChannelValue(AutoMode, 'fallthrough',
    registry.Boolean(True, _("""Determines whether the bot will "fall
    through" to halfop/voicing when auto-opping is turned off but
    auto-halfopping/voicing are turned on.""")))
conf.registerChannelValue(AutoMode, 'op',
    registry.Boolean(False, _("""Determines whether the bot will automatically
    op people with the <channel>,op capability when they join the channel.
    """)))
conf.registerChannelValue(AutoMode, 'halfop',
    registry.Boolean(False, _("""Determines whether the bot will automatically
    halfop people with the <channel>,halfop capability when they join the
    channel.""")))
conf.registerChannelValue(AutoMode, 'voice',
    registry.Boolean(False, _("""Determines whether the bot will automatically
    voice people with the <channel>,voice capability when they join the
    channel.""")))
conf.registerChannelValue(AutoMode, 'ban',
    registry.Boolean(True, _("""Determines whether the bot will automatically
    ban people who join the channel and are on the banlist.""")))
conf.registerChannelValue(AutoMode.ban, 'period',
    registry.PositiveInteger(86400, _("""Determines how many seconds the bot
    will automatically ban a person when banning.""")))

conf.registerChannelValue(AutoMode, 'delay',
    registry.Integer(0, _("""Determines how many seconds the bot will wait
    before applying a mode. Has no effect on bans.""")))

conf.registerChannelValue(AutoMode, 'extra',
    registry.SpaceSeparatedListOfStrings([], _("""Extra modes that will be
    applied to a user. Example syntax: user1+o-v user2+v user3-v""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
