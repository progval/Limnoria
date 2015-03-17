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
_ = PluginInternationalization('Dict')

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Dict', True)
    output(_('The default dictd server is dict.org.'))
    if yn(_('Would you like to specify a different dictd server?')):
        server = something('What server?')
        conf.supybot.plugins.Dict.server.set(server)

Dict = conf.registerPlugin('Dict')
conf.registerGlobalValue(Dict, 'server',
    registry.String('dict.org', _("""Determines what server the bot will
    retrieve definitions from.""")))
conf.registerChannelValue(Dict, 'default',
    registry.String('*', _("""Determines the default dictionary the bot
    will ask for definitions in.  If this value is '*' (without the quotes)
    the bot will use all dictionaries to define words.""")))
conf.registerChannelValue(Dict, 'showDictName',
    registry.Boolean(True, _("""Determines whether the bot will show which
    dictionaries responded to a query, if the selected dictionary is '*'.
    """)))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
