###
# Copyright (c) 2010, Daniel Folkinshteyn
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

try:
    from supybot.i18n import PluginInternationalization
    from supybot.i18n import internationalizeDocstring
    _ = PluginInternationalization('MessageParser')
except:
    # This are useless functions that's allow to run the plugin on a bot
    # without the i18n plugin
    _ = lambda x:x
    internationalizeDocstring = lambda x:x

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('MessageParser', True)

MessageParser = conf.registerPlugin('MessageParser')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(MessageParser, 'someConfigVariableName',
#     registry.Boolean(False, """Help for someConfigVariableName."""))
conf.registerChannelValue(MessageParser, 'enable',
    registry.Boolean(True, _("""Determines whether the
    message parser is enabled.  If enabled, will trigger on regexps
    added to the regexp db.""")))
conf.registerChannelValue(MessageParser, 'enableForNotices',
    registry.Boolean(False, _("""Determines whether the message parser
    is enabled for NOTICE messages too.""")))
conf.registerChannelValue(MessageParser, 'keepRankInfo',
    registry.Boolean(True, _("""Determines whether we keep updating the usage
    count for each regexp, for popularity ranking.""")))
conf.registerChannelValue(MessageParser, 'rankListLength',
    registry.Integer(20, _("""Determines the number of regexps returned
    by the triggerrank command.""")))
conf.registerChannelValue(MessageParser, 'requireVacuumCapability',
    registry.String('admin', _("""Determines the capability required (if any) to
    vacuum the database.""")))
conf.registerChannelValue(MessageParser, 'requireManageCapability',
    registry.String('admin; channel,op', _("""Determines the
    capabilities required (if any) to manage the regexp database,
    including add, remove, lock, unlock. Use 'channel,capab' for
    channel-level capabilities.
    Note that absence of an explicit anticapability means user has
    capability.""")))
conf.registerChannelValue(MessageParser, 'listSeparator',
    registry.String(', ', _("""Determines the separator used between regexps when
    shown by the list command.""")))
conf.registerChannelValue(MessageParser, 'maxTriggers',
    registry.Integer(0, _("""Determines the maximum number of triggers in
    one message. Set this to 0 to allow an infinite number of triggers.""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
