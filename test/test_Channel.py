#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

import conf
import ircdb
import ircmsgs

class ChannelTestCase(ChannelPluginTestCase, PluginDocumentation):
    plugins = ('Channel',)
    def testLobotomies(self):
        self.assertRegexp('lobotomies', 'not.*any')

    def testUnban(self):
        self.assertError('unban foo!bar@baz')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        m = self.getMsg('unban foo!bar@baz')
        self.assertEqual(m.command, 'MODE')
        self.assertEqual(m.args, (self.channel, '-b', 'foo!bar@baz'))
        self.assertNotError(' ')
        
    def testErrorsWithoutOps(self):
        for s in 'op deop halfop dehalfop voice devoice kick'.split():
            self.assertError('%s foo' % s)
            self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
            self.assertNotError('%s foo' % s)
            self.irc.feedMsg(ircmsgs.deop(self.channel, self.nick))

    def testOp(self):
        self.assertError('op')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('op')
        
    def testHalfOp(self):
        self.assertError('halfop')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('halfop')

    def testVoice(self):
        self.assertError('voice')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        self.assertNotError('voice')
        
    def testKban(self):
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix='foobar!user@host'))
        self.assertError('kban foobar')
        self.irc.feedMsg(ircmsgs.op(self.channel, self.nick))
        m = self.getMsg('kban foobar')
        self.assertEqual(m, ircmsgs.ban(self.channel, '*!*@host'))
        m = self.getMsg(' ')
        self.assertEqual(m, ircmsgs.kick(self.channel, 'foobar', self.nick))
        self.assertNotRegexp('kban adlkfajsdlfkjsd', 'KeyError')
        self.assertError('kban %s' % self.nick)

    def testLobotomizers(self):
        self.assertNotError('lobotomize')
        self.assertNotError('unlobotomize')

    def testPermban(self):
        self.assertNotError('permban foo!bar@baz')
        self.assertNotError('unpermban foo!bar@baz')
        self.assertError('permban not!a.hostmask')

    def testIgnore(self):
        self.assertNotError('Channel ignore foo!bar@baz')
        self.assertResponse('Channel ignores', "'foo!bar@baz'")
        self.assertNotError('Channel unignore foo!bar@baz')
        self.assertError('permban not!a.hostmask')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

