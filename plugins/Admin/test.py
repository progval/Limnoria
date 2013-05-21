###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

class AdminTestCase(PluginTestCase):
    plugins = ('Admin',)
    def testChannels(self):
        def getAfterJoinMessages():
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'MODE')
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

    def testIgnoreAddRemove(self):
        self.assertNotError('admin ignore add foo!bar@baz')
        self.assertError('admin ignore add alsdkfjlasd')
        self.assertNotError('admin ignore remove foo!bar@baz')
        self.assertError('admin ignore remove foo!bar@baz')

    def testIgnoreList(self):
        self.assertNotError('admin ignore list')
        self.assertNotError('admin ignore add foo!bar@baz')
        self.assertNotError('admin ignore list')
        self.assertNotError('admin ignore add foo!bar@baz')
        self.assertRegexp('admin ignore list', 'foo')

    def testCapabilityAdd(self):
        self.assertError('capability add foo bar')
        u = ircdb.users.newUser()
        u.name = 'foo'
        ircdb.users.setUser(u)
        self.assertNotError('capability add foo bar')
        self.assertError('addcapability foo baz')
        self.assert_('bar' in u.capabilities)
        ircdb.users.delUser(u.id)

    def testCapabilityRemove(self):
        self.assertError('capability remove foo bar')
        u = ircdb.users.newUser()
        u.name = 'foo'
        ircdb.users.setUser(u)
        self.assertNotError('capability add foo bar')
        self.assert_('bar' in u.capabilities)
        self.assertError('removecapability foo bar')
        self.assertNotError('capability remove foo bar')
        self.assert_(not 'bar' in u.capabilities)
        ircdb.users.delUser(u.id)

    def testJoin(self):
        m = self.getMsg('join #foo')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo')
        m = self.getMsg('join #foo key')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo')
        self.assertEqual(m.args[1], 'key')

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

    def testNick(self):
        original = conf.supybot.nick()
        try:
            m = self.getMsg('nick foobar')
            self.assertEqual(m.command, 'NICK')
            self.assertEqual(m.args[0], 'foobar')
        finally:
            conf.supybot.networks.test.nick.setValue('')

    def testAddCapabilityOwner(self):
        self.assertError('admin capability add %s owner' % self.nick)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

