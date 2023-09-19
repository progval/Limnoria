###
# Copyright (c) 2015, Michael Daniel Telatynski <postmaster@webdevguru.co.uk>
# Copyright (c) 2015-2019, James Lu <james@overdrivenetworks.com>
# Copyright (c) 2020-2021, Valentin Lorentz
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
    _ = PluginInternationalization('SedRegex')
except:
    _ = lambda x: x

def configure(advanced):
    from supybot.questions import expect, anything, something, yn, output
    conf.registerPlugin('SedRegex', True)
    if advanced:
        output("""The SedRegex plugin allows you to make Perl/sed-style regex
               replacements to your chat history.""")

SedRegex = conf.registerPlugin('SedRegex')

conf.registerChannelValue(SedRegex, 'displayErrors',
    registry.Boolean(True, _("""Should errors be displayed?""")))
conf.registerChannelValue(SedRegex, 'boldReplacementText',
    registry.Boolean(True, _("""Should the replacement text be bolded?""")))
conf.registerChannelValue(SedRegex, 'enable',
    registry.Boolean(False, _("""Should Perl/sed-style regex replacing
                     work in this channel?""")))
conf.registerChannelValue(SedRegex, 'ignoreRegex',
    registry.Boolean(True, _("""Should Perl/sed regex replacing
                     ignore messages which look like valid regex?""")))
conf.registerChannelValue(SedRegex, 'format',
    registry.String(_('$nick meant to say: $replacement'), _("""Sets the format
                                    string for a message edited by the original
                                    author. Required fields: $nick (nick of the
                                    author), $replacement (edited message)""")))
conf.registerChannelValue(SedRegex.format, 'other',
    registry.String(_('$otherNick thinks $nick meant to say: $replacement'), _("""
                                    Sets the format string for a message edited by
                                    another author. Required fields: $nick (nick
                                    of the original author), $otherNick (nick of
                                    the editor), $replacement (edited message)""")))
conf.registerGlobalValue(SedRegex, 'processTimeout',
    registry.PositiveFloat(0.5,  _("""Sets the timeout when processing a single
                                   regexp. The default should be adequate unless
                                   you have a busy or low-powered system that
                                   cannot process regexps quickly enough. However,
                                   you will not want to set this value too high
                                   as that would make your bot vulnerable to ReDoS
                                   attacks.""")))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
