###
# Copyright (c) 2005, Daniel DiPaolo
# Copyright (c) 2010-2021, Valentin Lorentz
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
_ = PluginInternationalization('Anonymous')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Anonymous', True)


Anonymous = conf.registerPlugin('Anonymous')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(Anonymous, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))
conf.registerChannelValue(conf.supybot.plugins.Anonymous,
    'requirePresenceInChannel', registry.Boolean(True, _("""Determines whether
    the bot should require people trying to use this plugin to be in the
    channel they wish to anonymously send to.""")))
conf.registerChannelValue(conf.supybot.plugins.Anonymous, 'requireRegistration',
    registry.Boolean(True, _("""Determines whether the bot should require
    people trying to use this plugin to be registered.""")))
conf.registerChannelValue(conf.supybot.plugins.Anonymous, 'requireCapability',
    registry.String('', _("""Determines what capability (if any) the bot should
    require people trying to use this plugin to have.""")))
conf.registerGlobalValue(conf.supybot.plugins.Anonymous, 'allowPrivateTarget',
    registry.Boolean(False, _("""Determines whether the bot will allow the
    "tell" command to be used. If true, the bot will allow the "tell"
    command to send private messages to other users.""")))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
