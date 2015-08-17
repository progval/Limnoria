###
# Copyright (c) 2002-2005, Jeremiah Fincher
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
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Factoids')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Factoids', True)

class FactoidFormat(registry.TemplatedString):
    """Value must include $value, otherwise the factoid's value would be left
    out."""
    requiredTemplates = ['value']

Factoids = conf.registerPlugin('Factoids')
conf.registerGroup(Factoids, 'web')
conf.registerGlobalValue(Factoids.web, 'enable',
    registry.Boolean(False, _("""Determines whether the Factoids plugins will
    be browsable on the HTTP server.""")))
conf.registerChannelValue(Factoids.web, 'channel',
    registry.Boolean(False, _("""Determines whether factoids can be displayed
    via the web server.""")))

conf.registerChannelValue(Factoids, 'requireVoice',
    registry.Boolean(False, _("""Only allows a user with voice or above on a
    channel to use the 'learn' and 'forget' commands.""")))
conf.registerChannelValue(Factoids, 'learnSeparator',
    registry.String('is', _("""Determines what separator must be used in 
    the learn command.  Defaults to 'is' -- learn <key> is <value>.  
    Users might want to change this to something else, so it's
    configurable.""")))
conf.registerChannelValue(Factoids, 'showFactoidIfOnlyOneMatch',
    registry.Boolean(True, _("""Determines whether the bot will reply with the
    single matching factoid if only one factoid matches when using the search
    command.""")))
conf.registerChannelValue(Factoids, 'replyWhenInvalidCommand',
    registry.Boolean(True,  _("""Determines whether the bot will reply to invalid
    commands by searching for a factoid; basically making the whatis
    unnecessary when you want all factoids for a given key.""")))
conf.registerChannelValue(Factoids, 'replyApproximateSearchKeys',
    registry.Boolean(True,  _("""If you try to look up a nonexistent factoid,
    this setting make the bot try to find some possible matching keys through
    several approximate matching algorithms and return a list of matching keys,
    before giving up.""")))
conf.registerChannelValue(Factoids, 'format',
    FactoidFormat(_('$value'), _("""Determines the format of
    the response given when a factoid's value is requested.  All the standard
    substitutes apply, in addition to "$key" for the factoid's key and "$value"
    for the factoid's value.""")))
conf.registerChannelValue(Factoids, 'keepRankInfo',
    registry.Boolean(True, """Determines whether we keep updating the usage
    count for each factoid, for popularity ranking."""))
conf.registerChannelValue(Factoids, 'rankListLength',
    registry.Integer(20, """Determines the number of factoid keys returned
    by the factrank command."""))
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
