#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

from testsupport import *

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs

class ChannelTestCase(ChannelPluginTestCase, PluginDocumentation):
    plugins = ('Channel', 'User')
    def testLobotomies(self):
        self.assertRegexp('lobotomies', 'not.*any')

##     def testCapabilities(self):
##         self.prefix = 'foo!bar@baz'
##         self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick, 'register foo bar',
##                                          prefix=self.prefix))
##         u = ircdb.users.getUser(0)
##         u.addCapability('%s.op' % self.channel)
##         ircdb.users.setUser(0, u)
##         self.assertNotError(' ')
##         self.assertResponse('user capabilities foo', '[]')
##         self.assertNotError('channel addcapability foo op')
##         self.assertRegexp('channel capabilities foo', 'op')
##         self.assertNotError('channel removecapability foo op')
##         self.assertResponse('user capabilities foo', '[]')

    def testCapabilities(self):
        self.assertNotError('channel capabilities')
        self.assertNotError('channel setcapability -foo')
        self.assertNotError('channel unsetcapability -foo')
        self.assertError('channel unsetcapability -foo')

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
        for s in 'deop dehalfop devoice'.split():
            self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
            self.assertError('%s %s' % (s, self.nick))

    def testOp(self):
        self.assertError('op')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('op')
        m = self.getMsg('op foo')
        self.failUnless(m.command == 'MODE' and
                        m.args == (self.channel, '+o', 'foo'))
        m = self.getMsg('op foo bar')
        self.failUnless(m.command == 'MODE' and
                        m.args == (self.channel, '+oo', 'foo', 'bar'))

    def testHalfOp(self):
        self.assertError('halfop')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('halfop')
        m = self.getMsg('halfop foo')
        self.failUnless(m.command == 'MODE' and
                        m.args == (self.channel, '+h', 'foo'))
        m = self.getMsg('halfop foo bar')
        self.failUnless(m.command == 'MODE' and
                        m.args == (self.channel, '+hh', 'foo', 'bar'))

    def testVoice(self):
        self.assertError('voice')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('voice')
        m = self.getMsg('voice foo')
        self.failUnless(m.command == 'MODE' and
                        m.args == (self.channel, '+v', 'foo'))
        m = self.getMsg('voice foo bar')
        self.failUnless(m.command == 'MODE' and
                        m.args == (self.channel, '+vv', 'foo', 'bar'))

    def assertBan(self, query, hostmask, **kwargs):
        m = self.getMsg(query, **kwargs)
        self.assertEqual(m, ircmsgs.ban(self.channel, hostmask))
        m = self.getMsg(' ')
        self.assertEqual(m.command, 'KICK')

##    def testKban(self):
##        self.irc.prefix = 'something!else@somehwere.else'
##        self.irc.nick = 'something'
##        self.irc.feedMsg(ircmsgs.join(self.channel,
##                                      prefix='foobar!user@host.domain.tld'))
##        self.assertError('kban foobar')
##        self.irc.feedMsg(ircmsgs.op(self.channel, self.irc.nick))
##        self.assertError('kban foobar -1')
##        self.assertBan('kban foobar', '*!*@*.domain.tld')
##        self.assertBan('kban --exact foobar', 'foobar!user@host.domain.tld')
##        self.assertBan('kban --host foobar', '*!*@host.domain.tld')
##        self.assertBan('kban --user foobar', '*!user@*')
##        self.assertBan('kban --nick foobar', 'foobar!*@*')
##        self.assertBan('kban --nick --user foobar', 'foobar!user@*')
##        self.assertBan('kban --nick --host foobar', 'foobar!*@host.domain.tld')
##        self.assertBan('kban --user --host foobar', '*!user@host.domain.tld')
##        self.assertBan('kban --nick --user --host foobar',
##                       'foobar!user@host.domain.tld')
##        self.assertNotRegexp('kban adlkfajsdlfkjsd', 'KeyError')
##        self.assertNotRegexp('kban foobar time', 'ValueError')
##        self.assertError('kban %s' % self.irc.nick)

    def testPermban(self):
        self.assertNotError('permban foo!bar@baz')
        self.assertNotError('unpermban foo!bar@baz')
        orig = conf.supybot.protocols.irc.strictRfc()
        try:
            conf.supybot.protocols.irc.strictRfc.setValue(True)
            # something wonky is going on here. irc.error (src/Channel.py|449)
            # is being called but the assert is failing
            self.assertError('permban not!a.hostmask')
            self.assertNotRegexp('permban not!a.hostmask', 'KeyError')
        finally:
            conf.supybot.protocols.irc.strictRfc.setValue(orig)

    def testIgnore(self):
        self.assertNotError('Channel ignore foo!bar@baz')
        self.assertResponse('Channel ignores', "'foo!bar@baz'")
        self.assertNotError('Channel unignore foo!bar@baz')
        self.assertError('permban not!a.hostmask')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

