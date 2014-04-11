###
# Copyright (c) 2004, Daniel DiPaolo
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
_ = PluginInternationalization('QuoteGrabs')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('QuoteGrabs', True)


QuoteGrabs = conf.registerPlugin('QuoteGrabs')
# This is where your configuration variables (if any) should go.  For example:
# conf.registerGlobalValue(QuoteGrabs, 'someConfigVariableName',
#     registry.Boolean(False, _("""Help for someConfigVariableName.""")))
conf.registerChannelValue(conf.supybot.plugins.QuoteGrabs, 'randomGrabber',
    registry.Boolean(False, _("""Determines whether the bot will randomly grab
    possibly-suitable quotes on occasion.  The suitability of a given message
    is determined by ...""")))
conf.registerChannelValue(conf.supybot.plugins.QuoteGrabs.randomGrabber,
    'averageTimeBetweenGrabs',
    registry.PositiveInteger(864000, _("""Determines about how many seconds, on
    average, should elapse between random grabs.  This is only an average
    value; grabs can happen from any time after half this time until never,
    although that's unlikely to occur.""")))
conf.registerChannelValue(conf.supybot.plugins.QuoteGrabs.randomGrabber,
    'minimumWords', registry.PositiveInteger(3, _("""Determines the minimum
    number of words in a message for it to be considered for random
    grabbing.""")))
conf.registerChannelValue(conf.supybot.plugins.QuoteGrabs.randomGrabber,
    'minimumCharacters', registry.PositiveInteger(8, _("""Determines the
    minimum number of characters in a message for it to be considered for
    random grabbing.""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
