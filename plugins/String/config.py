###
# Copyright (c) 2003-2005, Jeremiah Fincher
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
_ = PluginInternationalization('String')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('String', True)


String = conf.registerPlugin('String')
conf.registerGroup(String, 'levenshtein')
conf.registerGlobalValue(String.levenshtein, 'max',
    registry.PositiveInteger(256, _("""Determines the maximum size of a string
    given to the levenshtein command.  The levenshtein command uses an O(m*n)
    algorithm, which means that with strings of length 256, it can take 1.5
    seconds to finish; with strings of length 384, though, it can take 4
    seconds to finish, and with strings of much larger lengths, it takes more
    and more time.  Using nested commands, strings can get quite large, hence
    this variable, to limit the size of arguments passed to the levenshtein
    command.""")))

conf.registerGroup(String, 're')
conf.registerGlobalValue(String.re, 'timeout',
    registry.PositiveFloat(0.1, _("""Determines the maximum time, in seconds, that
    a regular expression is given to execute before being terminated. Since
    there is a possibility that user input for the re command can cause it to
    eat up large amounts of ram or cpu time, it's a good idea to keep this 
    low. Most normal regexps should not take very long at all.""")))
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
