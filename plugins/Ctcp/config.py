###
# Copyright (c) 2005, Jeremiah Fincher
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
_ = PluginInternationalization('Ctcp')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Ctcp', True)


###
# Ctcp plugin configuration variables.
###
Ctcp = conf.registerPlugin('Ctcp')
conf.registerGlobalValue(Ctcp, 'versionWait',
    registry.PositiveInteger(10, """Determines how many seconds the bot will
    wait after getting a version command (not a CTCP VERSION, but an actual
    call of the command in this plugin named "version") before replying with
    the results it has collected."""))
conf.registerGlobalValue(Ctcp, 'userinfo',
    registry.String('', """Determines what will be sent when a
    USERINFO query is received."""))

###
# supybot.abuse configuration variables.
###
conf.registerGlobalValue(conf.supybot.abuse.flood, 'ctcp',
    registry.Boolean(True, """Determines whether the bot will defend itself
    against CTCP flooding."""))
conf.registerGlobalValue(conf.supybot.abuse.flood.ctcp, 'maximum',
    registry.PositiveInteger(5, """Determines how many CTCP messages (not
    including actions) the bot will reply to from a given user in a minute.
    If a user sends more than this many CTCP messages in a 60 second period,
    the bot will ignore CTCP messages from this user for
    supybot.abuse.flood.ctcp.punishment seconds."""))
conf.registerGlobalValue(conf.supybot.abuse.flood.ctcp, 'punishment',
    registry.PositiveInteger(300, """Determines how many seconds the bot will
    ignore CTCP messages from users who flood it with CTCP messages."""))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
