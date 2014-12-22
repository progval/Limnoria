###
# Copyright (c) 2005, Daniel DiPaolo
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

from supybot.commands import *
import supybot.plugins as plugins
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Quote')

class Quote(plugins.ChannelIdDatabasePlugin):
    """This plugin allows you to add quotes to the database for a channel."""
    @internationalizeDocstring
    def random(self, irc, msg, args, channel):
        """[<channel>]

        Returns a random quote from <channel>.  <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        quote = self.db.random(channel)
        if quote:
            irc.reply(self.showRecord(quote))
        else:
            irc.error(_('I have no quotes in my database for %s.') % channel)
    random = wrap(random, ['channeldb'])

    def replace(self, irc, msg, args, user, channel, id, text):
        """[<channel>] <id> <text>
        Replace quote <id> with <text>. <channel> is only necessary if
        the message isn't sent in the channel itself.
        """
        try:
            record = self.db.get(channel, id)
            self.checkChangeAllowed(irc, msg, channel, user, record)
            record.text = text
            self.db.set(channel, id, record)
            irc.replySuccess()
        except KeyError:
            self.noSuchRecord(irc, channel, id)
    replace = wrap(replace, ['user', 'channeldb', 'id', 'text'])

Class = Quote

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
