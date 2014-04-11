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
_ = PluginInternationalization('Note')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Note', True)


Note = conf.registerPlugin('Note')
conf.registerGroup(Note, 'notify')
conf.registerGlobalValue(Note.notify, 'onJoin',
    registry.Boolean(False, """Determines whether the bot will notify people of
    their new messages when they join the channel.  Normally it will notify
    them when they send a message to the channel, since oftentimes joins are
    the result of netsplits and not the actual presence of the user."""))
conf.registerGlobalValue(Note.notify.onJoin, 'repeatedly',
    registry.Boolean(False, """Determines whether the bot will repeatedly
    notify people of their new messages when they join the channel.  That means
    when they join the channel, the bot will tell them they have unread
    messages, even if it's told them before."""))
conf.registerGlobalValue(Note.notify, 'autoSend',
    registry.NonNegativeInteger(0, """Determines the upper limit for
    automatically sending messages instead of notifications.  I.e., if this
    value is 2 and there are 2 new messages to notify a user about, instead of
    sending a notification message, the bot will simply send those new
    messages. If there are 3 new messages, however, the bot will send a
    notification message."""))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
