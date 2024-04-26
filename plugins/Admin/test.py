###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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
    plugins = ('Admin', 'Utilities')
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
        self.assertNotRegexp('config networks.test.channels', '.*#foo.*')

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
        self.assertIn('bar', u.capabilities)
        ircdb.users.delUser(u.id)

    def testCapabilityRemove(self):
        self.assertError('capability remove foo bar')
        u = ircdb.users.newUser()
        u.name = 'foo'
        ircdb.users.setUser(u)
        self.assertNotError('capability add foo bar')
        self.assertIn('bar', u.capabilities)
        self.assertError('removecapability foo bar')
        self.assertNotError('capability remove foo bar')
        self.assertNotIn('bar', u.capabilities)
        ircdb.users.delUser(u.id)

    def testJoin(self):
        try:
            m = self.getMsg('join #foo')
            self.assertEqual(m.command, 'JOIN')
            self.assertEqual(m.args[0], '#foo')
            m = self.getMsg('join #foo key')
            self.assertEqual(m.command, 'JOIN')
            self.assertEqual(m.args[0], '#foo')
            self.assertEqual(m.args[1], 'key')
        finally:
            conf.supybot.networks.test.channels.setValue('')

    def testNick(self):
        try:
            m = self.getMsg('nick foobar')
            self.assertEqual(m.command, 'NICK')
            self.assertEqual(m.args[0], 'foobar')
        finally:
            conf.supybot.networks.test.nick.setValue('')

    def testAddCapabilityOwner(self):
        self.assertError('admin capability add %s owner' % self.nick)

    def testJoinOnOwnerInvite(self):
        try:
            self.irc.feedMsg(ircmsgs.invite(conf.supybot.nick(), '#foo', prefix=self.prefix))
            m = self.getMsg(' ')
            self.assertEqual(m.command, 'JOIN')
            self.assertEqual(m.args[0], '#foo')
        finally:
            conf.supybot.networks.test.channels.setValue('')

    def testNoJoinOnUnprivilegedInvite(self):
        try:
            world.testing = False
            for channel in '#foo', '#foo\u0009':
                self.irc.feedMsg(ircmsgs.invite(conf.supybot.nick(), channel, prefix='foo!bar@baz'))
                self.assertResponse('somecommand',
                    'Error: "somecommand" is not a valid command.')
        finally:
            world.testing = True
            self.assertNotRegexp('config networks.test.channels', '.*#foo.*')

    def testAcmd(self):
        self.irc.feedMsg(ircmsgs.join('#foo', prefix=self.prefix))
        self.irc.feedMsg(ircmsgs.join('#bar', prefix=self.prefix))
        while self.irc.takeMsg():
            pass
        msgs = []
        msg = self.getMsg('acmd echo hi $channel')
        while msg:
            msgs.append(msg)
            msg = self.irc.takeMsg()
        self.assertCountEqual(
            [(msg.command,) + msg.args for msg in msgs],
            [("PRIVMSG", "#foo", "hi #foo"), ("PRIVMSG", "#bar", "hi #bar")])

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

