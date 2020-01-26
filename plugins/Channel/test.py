###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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

from supybot.test import *

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs

class ChannelTestCase(ChannelPluginTestCase):
    plugins = ('Channel', 'User')

    def setUp(self):
        super(ChannelTestCase, self).setUp()
        self.irc.state.channels[self.channel].addUser('foo')
        self.irc.state.channels[self.channel].addUser('bar')

    def testLobotomies(self):
        self.assertRegexp('lobotomy list', 'not.*any')

##     def testCapabilities(self):
##         self.prefix = 'foo!bar@baz'
##         self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick, 'register foo bar',
##                                          prefix=self.prefix))
##         u = ircdb.users.getUser(0)
##         u.addCapability('%s.op' % self.channel)
##         ircdb.users.setUser(u)
##         self.assertNotError(' ')
##         self.assertResponse('user capabilities foo', '[]')
##         self.assertNotError('channel addcapability foo op')
##         self.assertRegexp('channel capabilities foo', 'op')
##         self.assertNotError('channel removecapability foo op')
##         self.assertResponse('user capabilities foo', '[]')

    def testCapabilities(self):
        self.assertNotError('channel capability list')
        self.assertNotError('channel capability set -foo')
        self.assertNotError('channel capability unset -foo')
        self.assertError('channel capability unset -foo')
        self.assertNotError('channel capability set -foo bar baz')
        self.assertRegexp('channel capability list', 'baz')
        self.assertNotError('channel capability unset -foo baz')
        self.assertError('channel capability unset baz')

    def testEnableDisable(self):
        self.assertNotRegexp('channel capability list', '-Channel')
        self.assertError('channel enable channel')
        self.assertNotError('channel disable channel')
        self.assertRegexp('channel capability list', '-Channel')
        self.assertNotError('channel enable channel')
        self.assertNotRegexp('channel capability list', '-Channel')
        self.assertNotError('channel disable channel nicks')
        self.assertRegexp('channel capability list', '-Channel.nicks')
        self.assertNotError('channel enable channel nicks')
        self.assertNotRegexp('channel capability list', '-Channel.nicks')
        self.assertNotRegexp('channel capability list', 'nicks')
        self.assertNotError('channel disable nicks')
        self.assertRegexp('channel capability list', 'nicks')
        self.assertNotError('channel enable nicks')
        self.assertError('channel disable invalidPlugin')
        self.assertError('channel disable channel invalidCommand')

    def testUnban(self):
        self.assertError('unban foo!bar@baz')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        m = self.getMsg('unban foo!bar@baz')
        self.assertEqual(m.command, 'MODE')
        self.assertEqual(m.args, (self.channel, '-b', 'foo!bar@baz'))
        self.assertNoResponse(' ', 2)

    def testErrorsWithoutOps(self):
        for s in 'op deop halfop dehalfop voice devoice kick invite'.split():
            self.assertError('%s foo' % s)
            self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
            self.assertNotError('%s foo' % s)
            self.irc.feedMsg(ircmsgs.deop(self.channel, self.nick))

    def testWontDeItself(self):
        for s in 'deop dehalfop'.split():
            self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
            self.assertError('%s %s' % (s, self.nick))
            
    def testCanDevoiceSelf(self):
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('devoice %s' % self.nick)

    def testOp(self):
        self.assertError('op')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('op')
        m = self.getMsg('op foo')
        self.assertTrue(m.command == 'MODE' and
                        m.args == (self.channel, '+o', 'foo'))
        m = self.getMsg('op foo bar')
        self.assertTrue(m.command == 'MODE' and
                        m.args == (self.channel, '+o', 'foo'))
        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'MODE' and
                        m.args == (self.channel, '+o', 'bar'))
        self.irc.state.supported['MODES'] = 2
        m = self.getMsg('op foo bar')
        try:
            self.assertTrue(m.command == 'MODE' and
                            m.args == (self.channel, '+oo', 'foo', 'bar'))
        finally:
            self.irc.state.supported['MODES'] = 1

    def testHalfOp(self):
        self.assertError('halfop')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('halfop')
        m = self.getMsg('halfop foo')
        self.assertTrue(m.command == 'MODE' and
                        m.args == (self.channel, '+h', 'foo'))
        m = self.getMsg('halfop foo bar')
        self.assertTrue(m.command == 'MODE' and
                        m.args == (self.channel, '+h', 'foo'))
        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'MODE' and
                        m.args == (self.channel, '+h', 'bar'))

    def testVoice(self):
        self.assertError('voice')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('voice')
        m = self.getMsg('voice foo')
        self.assertTrue(m.command == 'MODE' and
                        m.args == (self.channel, '+v', 'foo'))
        m = self.getMsg('voice foo bar')
        self.assertTrue(m.command == 'MODE' and
                        m.args == (self.channel, '+v', 'foo'))
        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'MODE' and
                        m.args == (self.channel, '+v', 'bar'))

    def assertKban(self, query, hostmask, **kwargs):
        m = self.getMsg(query, **kwargs)
        self.assertEqual(m, ircmsgs.ban(self.channel, hostmask))
        m = self.getMsg(' ')
        self.assertEqual(m.command, 'KICK')
    def assertBan(self, query, hostmask, **kwargs):
        m = self.getMsg(query, **kwargs)
        self.assertEqual(m, ircmsgs.ban(self.channel, hostmask))

    def testIban(self):
        self.irc.feedMsg(ircmsgs.join(self.channel,
                                      prefix='foobar!user@host.domain.tld'))
        self.assertError('iban foo!bar@baz')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.irc.nick))
        self.assertBan('iban foo!bar@baz', 'foo!bar@baz')
        self.assertBan('iban foobar', 'foobar!user@host.domain.tld')

        conf.supybot.protocols.irc.strictRfc.setValue(True)
        self.assertError('iban $a:nyuszika7h')
        self.assertError('unban $a:nyuszika7h')
        conf.supybot.protocols.irc.strictRfc.setValue(False)
        self.assertBan('iban $a:nyuszika7h', '$a:nyuszika7h')
        self.assertNotError('unban $a:nyuszika7h')

##    def testKban(self):
##        self.irc.prefix = 'something!else@somehwere.else'
##        self.irc.nick = 'something'
##        self.irc.feedMsg(ircmsgs.join(self.channel,
##                                      prefix='foobar!user@host.domain.tld'))
##        self.assertError('kban foobar')
##        self.irc.feedMsg(ircmsgs.op(self.channel, self.irc.nick))
##        self.assertError('kban foobar -1')
##        self.assertKban('kban foobar', '*!*@*.domain.tld')
##        self.assertKban('kban --exact foobar', 'foobar!user@host.domain.tld')
##        self.assertKban('kban --host foobar', '*!*@host.domain.tld')
##        self.assertKban('kban --user foobar', '*!user@*')
##        self.assertKban('kban --nick foobar', 'foobar!*@*')
##        self.assertKban('kban --nick --user foobar', 'foobar!user@*')
##        self.assertKban('kban --nick --host foobar',
##                       'foobar!*@host.domain.tld')
##        self.assertKban('kban --user --host foobar', '*!user@host.domain.tld')
##        self.assertKban('kban --nick --user --host foobar',
##                       'foobar!user@host.domain.tld')
##        self.assertNotRegexp('kban adlkfajsdlfkjsd', 'KeyError')
##        self.assertNotRegexp('kban foobar time', 'ValueError')
##        self.assertError('kban %s' % self.irc.nick)

    def testBan(self):
        with conf.supybot.protocols.irc.banmask.context(['exact']):
            self.assertNotError('ban add foo!bar@baz')
            self.assertNotError('ban remove foo!bar@baz')
            orig = conf.supybot.protocols.irc.strictRfc()
            with conf.supybot.protocols.irc.strictRfc.context(True):
                # something wonky is going on here. irc.error (src/Channel.py|449)
                # is being called but the assert is failing
                self.assertError('ban add not!a.hostmask')
                self.assertNotRegexp('ban add not!a.hostmask', 'KeyError')
                self.assertError('ban add $a:nyuszika7h')
                self.assertError('ban remove $a:nyuszika7h')
                conf.supybot.protocols.irc.strictRfc.setValue(False)
                self.assertNotError('ban add $a:nyuszika7h')
                self.assertNotError('ban remove $a:nyuszika7h')

    def testBanList(self):
        self.assertNotError('ban add foo!bar@baz')
        self.assertNotError('ban add foobar!*@baz')
        self.assertNotError('ban add foobar!qux@baz')
        self.assertRegexp('ban list', r'.*foo!bar@baz.*')
        self.assertRegexp('ban list', r'.*foobar!\*@baz.*')
        self.assertRegexp('ban list', r'.*foobar!qux@baz.*')
        self.assertNotRegexp('ban list foobar!*@baz', r'.*foo!bar@baz.*')
        self.assertRegexp('ban list foobar!*@baz', r'.*foobar!\*@baz.*')
        self.assertRegexp('ban list foobar!*@baz', r'.*foobar!qux@baz.*')
        self.assertResponse('ban list foobar!\\*@baz',
                            '"foobar!*@baz" (never expires)')

    def testIgnore(self):
        orig = conf.supybot.protocols.irc.banmask()
        def ignore(given, expect=None):
            if expect is None:
                expect = given
            self.assertNotError('channel ignore add %s' % given)
            self.assertResponse('channel ignore list', "'%s'" % expect)
            self.assertNotError('channel ignore remove %s' % expect)
            self.assertRegexp('channel ignore list', 'not currently')
        ignore('foo!bar@baz', '*!*@baz')
        ignore('foo!*@*')
        with conf.supybot.protocols.irc.banmask.context(['exact']):
            ignore('foo!bar@baz')
            ignore('foo!*@*')
            self.assertError('ban add not!a.hostmask')

    def testNicks(self):
        self.assertResponse('channel nicks', 'bar, foo, and test')
        self.assertResponse('channel nicks --count', '3')

    def testPart(self):
        def getAfterJoinMessages():
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'MODE')
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'MODE')
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'WHO')
        self.assertError('part #foo')
        self.assertRegexp('part #foo', 'not in')
        self.irc.feedMsg(ircmsgs.join('#foo', prefix=self.prefix))
        getAfterJoinMessages()
        m = self.getMsg('part #foo')
        self.assertEqual(m.command, 'PART')
        self.irc.feedMsg(ircmsgs.join('#foo', prefix=self.prefix))
        getAfterJoinMessages()
        m = self.getMsg('part #foo reason')
        self.assertEqual(m.command, 'PART')
        self.assertEqual(m.args[0], '#foo')
        self.assertEqual(m.args[1], 'reason')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

