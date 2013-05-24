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
from cStringIO import StringIO

import supybot.gpg as gpg
from supybot.test import PluginTestCase, network

import supybot.conf as conf
import supybot.world as world
import supybot.ircdb as ircdb
import supybot.utils as utils

PRIVATE_KEY = """
-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1.4.12 (GNU/Linux)

lQHYBFD7GxQBBACeu7bj/wgnnv5NkfHImZJVJLaq2cwKYc3rErv7pqLXpxXZbDOI
jP+5eSmTLhPUK67aRD6gG0wQ9iAhYR03weOmyjDGh0eF7kLYhu/4Il56Y/YbB8ll
Imz/pep/Hi72ShcW8AtifDup/KeHjaWa1yF2WThHbX/0N2ghSxbJnatpBwARAQAB
AAP6Arf7le7FD3ZhGZvIBkPr25qca6i0Qxb5XpOinV7jLcoycZriJ9Xofmhda9UO
xhNVppMvs/ofI/m0umnR4GLKtRKnJSc8Edxi4YKyqLehfBTF20R/kBYPZ772FkNW
Kzo5yCpP1jpOc0+QqBuU7OmrG4QhQzTLXIUgw4XheORncEECAMGkvR47PslJqzbY
VRIzWEv297r1Jxqy6qgcuCJn3RWYJbEZ/qdTYy+MgHGmaNFQ7yhfIzkBueq0RWZp
Z4PfJn8CANHZGj6AJZcvb+VclNtc5VNfnKjYD+qQOh2IS8NhE/0umGMKz3frH1TH
yCbh2LlPR89cqNcd4QvbHKA/UmzISXkB/37MbUnxXTpS9Y4HNpQCh/6SYlB0lucV
QN0cgjfhd6nBrb6uO6+u40nBzgynWcEpPMNfN0AtQeA4Dx+WrnK6kZqfd7QMU3Vw
eWJvdCB0ZXN0iLgEEwECACIFAlD7GxQCGwMGCwkIBwMCBhUIAgkKCwQWAgMBAh4B
AheAAAoJEMnTMjwgrwErV3AD/0kRq8UWPlkc6nyiIR6qiT3EoBNHKIi4cz68Wa1u
F2M6einrRR0HolrxonynTGsdr1u2f3egOS4fNfGhTNAowSefYR9q5kIYiYE2DL5G
YnjJKNfmnRxZM9YqmEnN50rgu2cifSRehp61fXdTtmOAR3js+9wb73dwbYzr3kIc
3WH1
=UBcd
-----END PGP PRIVATE KEY BLOCK-----
"""

WRONG_TOKEN_SIGNATURE = """
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA1

{a95dc112-780e-47f7-a83a-c6f3820d7dc3}
-----BEGIN PGP SIGNATURE-----
Version: GnuPG v1.4.12 (GNU/Linux)

iJwEAQECAAYFAlD7Jb0ACgkQydMyPCCvASv9HgQAhQf/oFMWcKwGncH0hjXC3QYz
7ck3chgL3S1pPAvS69viz6i2bwYZYD8fhzHNJ/qtw/rx6thO6PwT4SpdhKerap+I
kdem3LjM4fAGHRunHZYP39obNKMn1xv+f26mEAAWxdv/W/BLAFqxi3RijJywRkXm
zo5GUl844kpnV+uk0Xk=
=z2Cz
-----END PGP SIGNATURE-----
"""

FINGERPRINT = '2CF3E41500218D30F0B654F5C9D3323C20AF012B'

class UserTestCase(PluginTestCase):
    plugins = ('User', 'Admin', 'Config')
    prefix1 = 'somethingElse!user@host.tld'
    prefix2 = 'EvensomethingElse!user@host.tld'

    def setUp(self):
        super(UserTestCase, self).setUp()
        gpg.loadKeyring()

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


    def testHostmask(self):
        self.assertResponse('hostmask', self.prefix)
        self.assertError('@hostmask asdf')
        m = self.irc.takeMsg()
        self.failIf(m is not None, m)

    def testRegisterUnregister(self):
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        self.assertError('register foo baz')
        self.failUnless(ircdb.users.getUserId('foo'))
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
            self.failIf(m is not None, m)
            self.failUnless(ircdb.users.getUserId('foo'))
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

    if gpg.available and network:
        def testGpgAddRemove(self):
            self.assertNotError('register foo bar')
            self.assertError('user gpg add 51E516F0B0C5CE6A pgp.mit.edu')
            self.assertResponse('user gpg add EB17F1E0CEB63930 pgp.mit.edu',
                    '1 key imported, 0 unchanged, 0 not imported.')
            self.assertNotError(
                    'user gpg remove F88ECDE235846FA8652DAF5FEB17F1E0CEB63930')
            self.assertResponse('user gpg add EB17F1E0CEB63930 pgp.mit.edu',
                    '1 key imported, 0 unchanged, 0 not imported.')
            self.assertResponse('user gpg add EB17F1E0CEB63930 pgp.mit.edu',
                    'Error: This key is already associated with your account.')

    if gpg.available:
        def testGpgAuth(self):
            self.assertNotError('register spam egg')
            gpg.keyring.import_keys(PRIVATE_KEY).__dict__
            (id, user) = ircdb.users.items()[0]
            user.gpgkeys.append(FINGERPRINT)
            msg = self.getMsg('gpg gettoken').args[-1]
            match = re.search('is: ({.*}).', msg)
            assert match, repr(msg)
            token = match.group(1)

            def fakeGetUrlFd(*args, **kwargs):
                return fd
            (utils.web.getUrlFd, realGetUrlFd) = (fakeGetUrlFd, utils.web.getUrlFd)

            fd = StringIO()
            fd.write('foo')
            fd.seek(0)
            self.assertResponse('gpg auth http://foo.bar/baz.gpg',
                    'Error: Signature or token not found.')

            fd = StringIO()
            fd.write(token)
            fd.seek(0)
            self.assertResponse('gpg auth http://foo.bar/baz.gpg',
                    'Error: Signature or token not found.')

            fd = StringIO()
            fd.write(WRONG_TOKEN_SIGNATURE)
            fd.seek(0)
            self.assertRegexp('gpg auth http://foo.bar/baz.gpg',
                    'Error: Unknown token.*')

            fd = StringIO()
            fd.write(str(gpg.keyring.sign(token)))
            fd.seek(0)
            self.assertResponse('gpg auth http://foo.bar/baz.gpg',
                    'You are now authenticated as spam.')

            utils.web.getUrlFd = realGetUrlFd

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

