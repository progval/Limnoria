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

import re

from supybot.test import PluginTestCase, network

import supybot.conf as conf
import supybot.world as world
import supybot.ircdb as ircdb
import supybot.utils as utils

class UserTestCase(PluginTestCase):
    plugins = ('User', 'Admin', 'Config')
    prefix1 = 'somethingElse!user@host1.tld'
    prefix2 = 'EvensomethingElse!user@host2.tld'
    prefix3 = 'Completely!Different@host3.tld__no_testcap__'

    def testHostmaskList(self):
        self.assertError('hostmask list')
        original = self.prefix
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        self.prefix = original
        self.assertError('hostmask list foo')
        self.assertNotError('hostmask add foo [hostmask] bar')
        self.assertNotError('hostmask add foo')
        self.assertNotRegexp('hostmask add foo', 'IrcSet')

    def testHostmaskListHandlesEmptyListGracefully(self):
        self.assertError('hostmask list')
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        self.assertNotError('hostmask remove foo %s' % self.prefix1)
        self.assertNotError('identify foo bar')
        self.assertRegexp('hostmask list', 'no registered hostmasks')

    def testHostmaskOverlap(self):
        self.assertNotError('register foo passwd', frm=self.prefix1)
        self.assertNotError('register bar passwd', frm=self.prefix2)
        self.assertResponse('whoami', 'foo', frm=self.prefix1)
        self.assertResponse('whoami', 'bar', frm=self.prefix2)
        self.assertNotError('hostmask add foo *!*@foobar/b',
                frm=self.prefix1)

        self.assertResponse('hostmask add bar *!*@foobar/*',
                'Error: That hostmask is already registered to foo.',
                frm=self.prefix2)
        self.assertRegexp('hostmask list foo', r'\*!\*@foobar/b',
                frm=self.prefix1)
        self.assertNotRegexp('hostmask list bar', 'foobar',
                frm=self.prefix2)

    def testHostmaskOverlapPrivacy(self):
        self.assertNotError('register foo passwd', frm=self.prefix1)
        self.assertNotError('register bar passwd', frm=self.prefix3)
        self.assertResponse('whoami', 'foo', frm=self.prefix1)
        self.assertResponse('whoami', 'bar', frm=self.prefix3)
        self.assertNotError('hostmask add foo *!*@foobar/b',
                frm=self.prefix1)

        ircdb.users.getUser('bar').addCapability('owner')
        self.assertResponse('whoami', 'bar',
                frm=self.prefix3)
        self.assertResponse('capabilities', '[owner]',
                frm=self.prefix3)
        self.assertResponse('hostmask add *!*@foobar/*',
                'Error: That hostmask is already registered to foo.',
                frm=self.prefix3)
        ircdb.users.getUser('bar').removeCapability('owner')
        self.assertResponse('hostmask add *!*@foobar/*',
                'Error: That hostmask is already registered.',
                frm=self.prefix3)


    def testHostmask(self):
        self.assertResponse('hostmask', self.prefix)
        self.assertError('@hostmask asdf')
        m = self.irc.takeMsg()
        self.assertFalse(m is not None, m)

    def testRegisterPasswordLength(self):
        self.assertRegexp('register foo aa', 'at least 3 characters long.')

    def testRegisterNoPassword(self):
        self.assertNotError('register foo !')
        self.assertRegexp('identify foo bar', 'your password is wrong.')
        self.assertRegexp('identify foo !', 'your password is wrong.')

    def testRegisterUnregister(self):
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        self.assertError('register foo baz')
        self.assertTrue(ircdb.users.getUserId('foo'))
        self.assertError('unregister foo')
        self.assertNotError('unregister foo bar')
        self.assertRaises(KeyError, ircdb.users.getUserId, 'foo')

    def testDisallowedUnregistration(self):
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        orig = conf.supybot.databases.users.allowUnregistration()
        conf.supybot.databases.users.allowUnregistration.setValue(False)
        try:
            self.assertError('unregister foo')
            m = self.irc.takeMsg()
            self.assertFalse(m is not None, m)
            self.assertTrue(ircdb.users.getUserId('foo'))
        finally:
            conf.supybot.databases.users.allowUnregistration.setValue(orig)

    def testList(self):
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        self.assertResponse('user list', 'foo')
        self.prefix = self.prefix2
        self.assertNotError('register biff quux')
        self.assertResponse('user list', 'biff and foo')

        self.assertRegexp('user list --capability testcap', 'no matching')
        self.assertNotError('admin capability add biff testcap')
        self.assertResponse('user list --capability testcap', 'biff')
        self.assertNotError('config capabilities.private testcap')
        self.assertRegexp('user list --capability testcap', 'Error:.*private')
        self.assertNotError('admin capability add biff admin')
        self.assertResponse('user list --capability testcap', 'biff')
        self.assertNotError('admin capability remove biff admin')
        self.assertRegexp('user list --capability testcap', 'Error:.*private')
        self.assertNotError('config capabilities.private ""')
        self.assertResponse('user list --capability testcap', 'biff')
        self.assertNotError('admin capability remove biff testcap')
        self.assertRegexp('user list --capability testcap', 'no matching')

        self.assertResponse('user list f', 'biff and foo')
        self.assertResponse('user list f*', 'foo')
        self.assertResponse('user list *f', 'biff')
        self.assertNotError('unregister biff quux')
        self.assertResponse('user list', 'foo')
        self.assertNotError('unregister foo bar')
        self.assertRegexp('user list', 'no registered users')
        self.assertRegexp('user list asdlfkjasldkj', 'no matching registered')

    def testListHandlesCaps(self):
        self.prefix = self.prefix1
        self.assertNotError('register Foo bar')
        self.assertResponse('user list', 'Foo')
        self.assertResponse('user list f*', 'Foo')

    def testChangeUsername(self):
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        self.prefix = self.prefix2
        self.assertNotError('register bar baz')
        self.prefix = self.prefix1
        self.assertError('changename foo bar')
        self.assertNotError('changename foo baz')

    def testSetpassword(self):
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        password = ircdb.users.getUser(self.prefix).password
        self.assertNotEqual(password, 'bar')
        self.assertNotError('set password foo bar baz')
        self.assertNotEqual(ircdb.users.getUser(self.prefix).password,password)
        self.assertNotEqual(ircdb.users.getUser(self.prefix).password, 'baz')

    def testStats(self):
        self.assertNotError('user stats')
        self.assertNotError('load Lart')
        self.assertNotError('user stats')

    def testUserPluginAndUserList(self):
        self.prefix = self.prefix1
        self.assertNotError('register Foo bar')
        self.assertResponse('user list', 'Foo')
        self.assertNotError('load Seen')
        self.assertResponse('user list', 'Foo')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

