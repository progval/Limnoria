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

"""
Add the module docstring here.  This will be used by the setup.py script.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.unknown
__contributors__ = {}

import re

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Praise', True)


Praise = conf.registerPlugin('Praise')
conf.registerChannelValue(Praise, 'showIds',
    registry.Boolean(False, """Determines whether the bot will show the ids of
    a praise when the praise is given."""))

class Praise(plugins.ChannelIdDatabasePlugin):
    _meRe = re.compile(r'\bme\b', re.I)
    _myRe = re.compile(r'\bmy\b', re.I)
    def _replaceFirstPerson(self, s, nick):
        s = self._meRe.sub(nick, s)
        s = self._myRe.sub('%s\'s' % nick, s)
        return s

    def addValidator(self, irc, text):
        if '$who' not in text:
            irc.error('Praises must contain $who.', Raise=True)

    def praise(self, irc, msg, args, channel, id, text):
        """[<channel>] [<id>] <who|what> [for <reason>]

        Praises <who|what> (for <reason>, if given).  If <id> is given, uses
        that specific praise.  <channel> is only necessary if the message isn't
        sent in the channel itself.
        """
        if ' for ' in text:
            (target, reason) = map(str.strip, text.split(' for ', 1))
        else:
            (target, reason) = (text, '')
        if ircutils.strEqual(target, irc.nick):
            target = 'itself'
        if id is not None:
            try:
                praise = self.db.get(channel, id)
            except KeyError:
                irc.error('There is no praise with id #%s.' % id)
                return
        else:
            praise = self.db.random(channel)
            if not praise:
                irc.error('There are no praise in my database for %s.' %channel)
                return
        text = self._replaceFirstPerson(praise.text, msg.nick)
        reason = self._replaceFirstPerson(reason, msg.nick)
        if target.endswith('.'):
            target = target.rstrip('.')
        target = self._replaceFirstPerson(target, msg.nick)
        text = text.replace('$who', target)
        if reason:
            text += ' for ' + reason
        if self.registryValue('showIds', channel):
            text += ' (#%s)' % praise.id
        irc.reply(text, action=True)
    praise = wrap(praise, ['channeldb', optional('id'), 'text'])

Class = Praise

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
