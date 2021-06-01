###
# Copyright (c) 2003-2005, Daniel DiPaolo
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
import supybot.ircutils as ircutils
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Dunno')

class Dunno(plugins.ChannelIdDatabasePlugin):
    """This plugin was written initially to work with MoobotFactoids, the two
    of them to provide a similar-to-moobot-and-blootbot interface for factoids.
    Basically, it replaces the standard 'Error: <x> is not a valid command.'
    messages with messages kept in a database, able to give more personable
    responses.

    ``$command`` in the message will be replaced by the command's name."""

    callAfter = ['MoobotFactoids', 'Factoids', 'Infobot']
    def invalidCommand(self, irc, msg, tokens):
        if msg.channel:
            dunno = self.db.random(msg.channel)
            if dunno is not None:
                dunno = dunno.text
                prefixNick = self.registryValue('prefixNick',
                                                msg.channel, irc.network)
                env = {'command': tokens[0]}
                self.log.info('Issuing "dunno" answer, %s is not a command.',
                        tokens[0])
                dunno = ircutils.standardSubstitute(irc, msg, dunno, env=env)
                irc.reply(dunno, prefixNick=prefixNick)
Dunno = internationalizeDocstring(Dunno)

Class = Dunno


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
