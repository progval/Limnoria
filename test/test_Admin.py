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

class AdminTestCase(PluginTestCase):
    plugins = ('Admin',)
    def testChannels(self):
        def getAfterJoinMessages():
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'MODE')
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'WHO')
        self.assertRegexp('channels', 'not.*in any')
        self.irc.feedMsg(ircmsgs.join('#foo', prefix=self.prefix))
        getAfterJoinMessages()
        self.assertRegexp('channels', '#foo')
        self.irc.feedMsg(ircmsgs.join('#bar', prefix=self.prefix))
        getAfterJoinMessages()
        self.assertRegexp('channels', '#bar and #foo')
        self.irc.feedMsg(ircmsgs.join('#Baz', prefix=self.prefix))
        getAfterJoinMessages()
        self.assertRegexp('channels', '#bar, #Baz, and #foo')

    def testIgnoreUnignore(self):
        self.assertNotError('admin ignore foo!bar@baz')
        self.assertError('admin ignore alsdkfjlasd')
        self.assertNotError('admin unignore foo!bar@baz')
        self.assertError('admin unignore foo!bar@baz')

    def testIgnores(self):
        self.assertNotError('admin ignores')
        self.assertNotError('admin ignore foo!bar@baz')
        self.assertNotError('admin ignores')
        self.assertNotError('admin ignore foo!bar@baz')
        self.assertNotError('admin ignores')

    def testAddcapability(self):
        self.assertError('addcapability sdlkfj foo')
        (id, u) = ircdb.users.newUser()
        u.name = 'foo'
        ircdb.users.setUser(id, u)
        self.assertError('removecapability foo bar')
        self.assertNotRegexp('removecapability foo bar', 'find')

    def testRemoveCapability(self):
        self.assertError('removecapability alsdfkjasd foo')

    def testJoin(self):
        m = self.getMsg('join #foo')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo')
        m = self.getMsg('join #foo #bar')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo,#bar')
        m = self.getMsg('join #foo,key')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo')
        self.assertEqual(m.args[1], 'key')
        m = self.getMsg('join #bar #foo,key')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo,#bar')
        self.assertEqual(m.args[1], 'key')
        m = self.getMsg('join #bar,key1 #foo,key2')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo,#bar')
        self.assertEqual(m.args[1], 'key2,key1')

    def testPart(self):
        def getAfterJoinMessages():
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'MODE')
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'WHO')
        self.assertError('part #foo')
        self.assertRegexp('part #foo', 'currently')
        self.irc.feedMsg(ircmsgs.join('#foo', prefix=self.prefix))
        getAfterJoinMessages()
        self.assertError('part #foo #bar')
        m = self.getMsg('part #foo')
        self.assertEqual(m.command, 'PART')
        self.assertEqual(m.args[0], '#foo')
        self.irc.feedMsg(ircmsgs.join('#foo', prefix=self.prefix))
        getAfterJoinMessages()
        self.irc.feedMsg(ircmsgs.join('#bar', prefix=self.prefix))
        getAfterJoinMessages()
        m = self.getMsg('part #foo #bar')
        self.assertEqual(m.command, 'PART')
        self.assertEqual(m.args[0], '#foo,#bar')

    def testNick(self):
        original = conf.supybot.nick()
        try:
            m = self.getMsg('nick foobar')
            self.assertEqual(m.command, 'NICK')
            self.assertEqual(m.args[0], 'foobar')
        finally:
            conf.supybot.nick.setValue(original)

    def testAddCapabilityOwner(self):
        self.assertError('admin addcapability %s owner' % self.nick)



# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

