###
# Copyright (c) 2004-2005, Jeremiah Fincher
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
_ = PluginInternationalization('Misc')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Misc', True)

Misc = conf.registerPlugin('Misc')
conf.registerChannelValue(Misc, 'mores',
    registry.PositiveInteger(1, _("""Determines how many messages the bot
    will issue when using the 'more' command.""")))
conf.registerGlobalValue(Misc, 'listPrivatePlugins',
    registry.Boolean(False, _("""Determines whether the bot will list private
    plugins with the list command if given the --private switch.  If this is
    disabled, non-owner users should be unable to see what private plugins
    are loaded.""")))
conf.registerGlobalValue(Misc, 'customHelpString',
    registry.String('', _("""Sets a custom help string, displayed when the 'help'
    command is called without arguments.""")))
conf.registerGlobalValue(Misc, 'listUnloadedPlugins',
    registry.Boolean(False, _("""Determines whether the bot will list unloaded
    plugins with the list command if given the --unloaded switch.  If this is
    disabled, non-owner users should be unable to see what unloaded plugins
    are available.""")))
conf.registerGlobalValue(Misc, 'timestampFormat',
    registry.String('[%H:%M:%S]', _("""Determines the format string for
    timestamps in the Misc.last command.  Refer to the Python documentation
    for the time module to see what formats are accepted. If you set this
    variable to the empty string, the timestamp will not be shown.""")))
conf.registerGroup(Misc, 'last')
conf.registerGroup(Misc.last, 'nested')
conf.registerChannelValue(Misc.last.nested,
    'includeTimestamp', registry.Boolean(False, _("""Determines whether or not
    the timestamp will be included in the output of last when it is part of a
    nested command""")))
conf.registerChannelValue(Misc.last.nested,
    'includeNick', registry.Boolean(False, _("""Determines whether or not the
    nick will be included in the output of last when it is part of a nested
    command""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
