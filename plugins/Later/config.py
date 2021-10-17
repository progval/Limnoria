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
_ = PluginInternationalization('Later')

def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Later', True)

Later = conf.registerPlugin('Later')
conf.registerGlobalValue(Later, 'maximum',
    registry.NonNegativeInteger(0, _("""Determines the maximum number of
    messages to be queued for a user.  If this value is 0, there is no maximum.
    """)))
conf.registerGlobalValue(Later, 'private',
    registry.Boolean(False, _("""Determines whether users will be notified in
    the first place in which they're seen, or in private.""")))
conf.registerGlobalValue(Later, 'tellOnJoin',
    registry.Boolean(False, _("""Determines whether users will be notified upon
    joining any channel the bot is in, or only upon sending a message.""")))
conf.registerGlobalValue(Later, 'messageExpiry',
    registry.NonNegativeInteger(30, _("""Determines the maximum number of
    days that a message will remain queued for a user. After this time elapses,
    the message will be deleted. If this value is 0, there is no maximum.""")))

conf.registerGroup(Later, 'format')
conf.registerGlobalValue(Later.format, 'senderHostname',
    registry.Boolean(False, _("""Determines whether senders' hostname will be
    shown in messages (instead of just the nick).""")))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
