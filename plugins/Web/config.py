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
_ = PluginInternationalization('Web')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    Web = conf.registerPlugin('Web', True)
    if yn("""This plugin also offers a snarfer that will try to fetch the
             title of URLs that it sees in the channel.  Would like you this
             snarfer to be enabled?""", default=False):
        Web.titleSnarfer.setValue(True)


Web = conf.registerPlugin('Web')
conf.registerChannelValue(Web, 'titleSnarfer',
    registry.Boolean(False, _("""Determines whether the bot will output the
    HTML title of URLs it sees in the channel.""")))
conf.registerChannelValue(Web, 'nonSnarfingRegexp',
    registry.Regexp(None, _("""Determines what URLs matching the given regexp
    will not be snarfed.  Give the empty string if you have no URLs that you'd
    like to exclude from being snarfed.""")))

conf.registerGroup(Web, 'fetch')
conf.registerGlobalValue(Web.fetch, 'maximum',
    registry.NonNegativeInteger(0, _("""Determines the maximum number of
    bytes the bot will download via the 'fetch' command in this plugin.""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
