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

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Herald')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Herald', True)


Herald = conf.registerPlugin('Herald')
conf.registerChannelValue(Herald, 'heralding',
    registry.Boolean(True, _("""Determines whether messages will be sent to the
    channel when a recognized user joins; basically enables or disables the
    plugin.""")))
conf.registerGlobalValue(Herald, 'requireCapability',
    registry.String('', _("""Determines what capability (if any) is required to
    add/change/remove the herald of another user.""")))
conf.registerChannelValue(Herald, 'throttle',
    registry.PositiveInteger(600, _("""Determines the minimum number of seconds
    between heralds.""")))
conf.registerChannelValue(Herald.throttle, 'afterPart',
    registry.NonNegativeInteger(0, _("""Determines the minimum number of seconds
    after parting that the bot will not herald the person when they
    rejoin.""")))
conf.registerChannelValue(Herald.throttle, 'afterSplit',
    registry.NonNegativeInteger(60, _("""Determines the minimum number of seconds
    after a netsplit that the bot will not herald the users that split.""")))
conf.registerChannelValue(Herald, 'default',
    registry.String('', _("""Sets the default herald to use.  If a user has a
    personal herald specified, that will be used instead.  If set to the empty
    string, the default herald will be disabled.""")))
conf.registerChannelValue(Herald.default, 'notice',
    registry.Boolean(True, _("""Determines whether the default herald will be
    sent as a NOTICE instead of a PRIVMSG.""")))
conf.registerChannelValue(Herald.default, 'public',
    registry.Boolean(False, _("""Determines whether the default herald will be
    sent publicly.""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
