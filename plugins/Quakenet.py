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
Plugin for handling Quakenet-specific stuff (like Q and L).
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch
__contributors__ = {}

import md5

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircmsgs as ircmsgs
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
    conf.registerPlugin('Quakenet', True)


class Password(registry.String):
    """Value must be a string of 10 or fewer characters."""
    def setValue(self, s):
        if len(s) > 10:
            self.error()
        else:
            registry.String.setValue(self, s)

Quakenet = conf.registerPlugin('Quakenet')
conf.registerGroup(Quakenet, 'Q')
conf.registerGlobalValue(Quakenet.Q, 'authname',
    registry.String('', """Determines what name the bot will identify with on
    Quakenet."""))
conf.registerGlobalValue(Quakenet.Q, 'password',
    Password('', """Determines what password the bot will identify with
    on Quakenet.""", private=True))

digests = ircutils.IrcDict({
    'MD5': lambda s: md5.md5(s).hexdigest()
})

toQ = 'Q@CServe.quakenet.org'
fromQ = 'Q!TheQBot@CServe.quakenet.org'

class Quakenet(privmsgs.CapabilityCheckingPrivmsg):
    capability = 'owner'
    def __init__(self):
        self.__parent = super(Quakenet, self)
        self.__parent.__init__()
        self.lastChallenge = None

    def _isQuakeNet(self, irc):
        return irc.state.supported.get('NETWORK') == 'QuakeNet'

    def outFilter(self, irc, msg):
        if self._isQuakeNet(irc):
            if msg.command == 'PRIVMSG':
                if msg.args[0] in ('NickServ', 'ChanServ'):
                    self.log.info('Filtering outgoing message to '
                                  'non-QuakeNet services.')
                    return None
        return msg

    def do376(self, irc, msg):
        if self._isQuakeNet(irc):
            self._doAuth(irc, msg)

    def _doAuth(self, irc, msg):
        name = self.registryValue('Q.authname')
        password = self.registryValue('Q.password')
        if name and password:
            self._sendToQ(irc, 'challenge')
            
    def doNotice(self, irc, msg):
        if self._isQuakeNet(irc):
            if msg.prefix == fromQ:
                self._doQ(irc, msg)

    def _handleChallenge(self, irc, digest, challenge):
        f = digests[digest]
        name = self.registryValue('Q.authname')
        password = self.registryValue('Q.password')
        response = f(password + ' ' + challenge)
        self._sendToQ(irc, 'challengeauth %s %s' % (name, response))

    def _doQ(self, irc, msg):
        self.log.debug('Received %r from Q.', msg)
        payload = msg.args[1]
        # Challenge/response.
        if 'already requested a challenge' in payload:
            self.log.debug('Received "already requested challenge" from Q.')
            assert self.lastChallenge
            self._handleChallenge(irc, *self.lastChallenge)
        elif 'successfully' in payload:
            # This needs to be before the next one since it also starts with
            # "CHALLENGE"
            self.log.info('Received %s from Q.', payload)
        elif payload.startswith('CHALLENGE'):
            self.log.info('Received CHALLENGE from Q.')
            (_, digest, challenge) = payload.split()
            self.lastChallenge = (digest, challenge)
            self._handleChallenge(irc, digest, challenge)
        elif payload.startswith('Remember:'):
            self.log.debug('Got a Remember: message from Q.')
        else:
            self.log.warning('Unexpected message from Q: %r', msg)

    def _sendToQ(self, irc, s):
        m = ircmsgs.privmsg(toQ, s)
        self.log.debug('Sending %r to Q.', m)
        irc.sendMsg(m)

    def q(self, irc, msg, args, text):
        """<text>

        Sends <text> to Q.
        """
        self._sendToQ(text)
        irc.noReply()
    q = wrap(q, ['text'])

    def auth(self, irc, msg, args):
        """takes no arguments

        Attempts to authenticate with Q.
        """
        self._sendToQ(irc, 'challenge')
        irc.noReply()
    auth = wrap(auth)


Class = Quakenet

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
