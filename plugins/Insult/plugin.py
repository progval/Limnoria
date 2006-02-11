###
# Copyright (c) 2004-2005, Mike Taylor
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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class Insult(callbacks.Plugin):
    def _buildInsult(self):
        """
        Insults are formed by making combinations of:
        You are nothing but a(n) {adj} {amt} of {adj} {noun}
        """
        if self.registryValue('allowFoul'):
            _nouns = self.registryValue('nouns') + \
                     self.registryValue('foulNouns')
            _amounts = self.registryValue('amounts') + \
                       self.registryValue('foulAmounts')
            _adjectives = self.registryValue('adjectives') + \
                          self.registryValue('foulAdjectives')
        else:
            _nouns = self.registryValue('nouns')
            _amounts = self.registryValue('amounts')
            _adjectives = self.registryValue('adjectives')
        adj1 = utils.iter.choice(_adjectives)
        adj2 = utils.iter.choice(_adjectives)
        noun = utils.iter.choice(_nouns)
        amount = utils.iter.choice(_amounts)
        if adj1 == adj2:
            adj2 = utils.iter.choice(_adjectives)
        if not adj1[0] in 'aeiou':
            an = 'a'
        else:
            an = 'an'
        return format('You are nothing but %s %s %s of %s %s.',
                      an, adj1, amount, adj2, noun)

    def insult(self, irc, msg, args, victim):
        """[<target>]

        Reply optionally directed at a random string, person,
        object, etc.
        """
        tempinsult = self._buildInsult()
        if not victim:
            irc.reply(tempinsult, prefixNick=False)
        else:
            irc.reply(format('%s - %s ', victim, tempinsult),
                      prefixNick=False)
    insult = wrap(insult, [additional('text')])


Class = Insult


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
