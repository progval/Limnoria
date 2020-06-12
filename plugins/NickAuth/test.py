###
# Copyright (c) 2012, Valentin Lorentz
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

import supybot.ircdb as ircdb
import supybot.ircutils as ircutils
from supybot.test import *

class NickAuthTestCase(PluginTestCase):
    plugins = ('NickAuth', 'User')

    prefix1 = 'something!user@host.tld'

    def _register(self):
        self.assertNotError('register foobar 123')
        self.assertResponse('user list', 'foobar')
        self.assertNotError('hostmask remove foobar %s' % self.prefix)
        self.assertNotError('identify foobar 123')
        self.assertNotError('nick add foobar baz')
        self.assertNotError('unidentify')

    def _procedure(self, nickserv_reply):
        self._register()
        self.prefix = self.prefix1
        self.assertError('nick add foobar qux')
        self.nick = self.prefix.split('!')[0]

        self.assertError('hostmask list')
        self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                         'auth',
                                         prefix=self.prefix))
        self.assertEqual(self.irc.takeMsg().command, 'WHOIS')
        self.assertError('hostmask list')

        self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                         'auth',
                                         prefix=self.prefix))
        self.assertEqual(self.irc.takeMsg().command, 'WHOIS')
        if nickserv_reply:
            self.irc.feedMsg(ircmsgs.IrcMsg(':leguin.freenode.net 330 pgjrgrg '
                    '%s baz :is logged in as' % self.nick))
            msg = self.irc.takeMsg()
            self.assertNotEqual(msg, None)
            self.assertEqual(msg.args[1], 'You are now authenticated as foobar.')
            self.assertResponse('hostmask list',
                    'foobar has no registered hostmasks.')
        else:
            msg = self.irc.takeMsg()
            self.assertEqual(msg, None)
            self.assertError('hostmask list')

    def testAuth(self):
        self._procedure(True)
    def testNoAuth(self):
        self._procedure(False)

    def testUserJoin(self):
        self.irc.feedMsg(ircmsgs.IrcMsg('CAP * NEW extended-join'))
        m = self.irc.takeMsg()
        self.assertEqual(m.command, 'CAP')
        self.assertEqual(m.args, ('REQ', 'extended-join'))

        self.irc.feedMsg(ircmsgs.IrcMsg('CAP * ACK extended-join'))
        m = self.irc.takeMsg()
        self.assertEqual(m.command, 'CAP')
        self.assertEqual(m.args, ('END',))
        self.assertEqual(self.irc.takeMsg(), None)

        channel = '#test'
        self.irc.feedMsg(ircmsgs.join(channel, prefix=self.prefix))
        self.assertEqual(self.irc.takeMsg().command, 'MODE')
        self.assertEqual(self.irc.takeMsg().command, 'MODE')
        self.assertEqual(self.irc.takeMsg().command, 'WHO')
        self.assertEqual(self.irc.takeMsg(), None)

        self._register()
        self.assertRegexp(
            'whoami', "I don't recognize you", frm=self.prefix1)
        self.irc.feedMsg(ircmsgs.IrcMsg(
            ':%s JOIN %s baz :Real name' % (self.prefix1, channel)))
        self.assertResponse('ping', 'pong')
        self.assertResponse('whoami', 'foobar', frm=self.prefix1)

    def testBotJoin(self):
        channel = '#test'
        self.irc.feedMsg(ircmsgs.join(channel, prefix=self.prefix))
        self.assertEqual(self.irc.takeMsg().command, 'MODE')
        self.assertEqual(self.irc.takeMsg().command, 'MODE')
        self.assertEqual(self.irc.takeMsg().command, 'WHO')
        self.assertEqual(self.irc.takeMsg(), None)

        self._register()
        self.assertRegexp(
            'whoami', "I don't recognize you", frm=self.prefix1)
        (nick, ident, host) = ircutils.splitHostmask(self.prefix1)
        self.irc.feedMsg(ircmsgs.IrcMsg(
            ':card.freenode.net 354 pgjrgrg 1 %(ident)s 255.255.255.255 '
            '%(host)s %(nick)s H baz :gecos'
            % dict(nick=nick, ident=ident, host=host)))
        self.assertResponse('ping', 'pong')
        self.assertResponse('whoami', 'foobar', frm=self.prefix1)

    def testList(self):
        self.assertNotError('register foobar 123')
        self.assertRegexp('nick list', 'You have no recognized nick')
        self.assertNotError('nick add foo')
        self.assertRegexp('nick list', 'foo')
        self.assertNotError('nick add %s bar' % self.nick)
        self.assertRegexp('nick list', 'foo and bar')
        self.assertNotError('nick add %s %s baz' % (self.irc.network, self.nick))
        self.assertRegexp('nick list', 'foo, bar, and baz')
        self.assertRegexp('nick list %s' % self.irc.network, 'foo, bar, and baz')
        self.assertRegexp('nick list %s foobar' % self.irc.network,
                'foo, bar, and baz')


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
