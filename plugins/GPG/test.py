###
# Copyright (c) 2015, Valentin Lorentz
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
import supybot.utils.minisix as minisix

import supybot.gpg as gpg

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


class GPGTestCase(PluginTestCase):
    plugins = ('GPG', 'User')

    def setUp(self):
        super(GPGTestCase, self).setUp()
        gpg.loadKeyring()

    if gpg.available and network:
        def testGpgAddRemove(self):
            self.assertNotError('register foo bar')
            self.assertError('gpg key add 51E516F0B0C5CE6A pgp.mit.edu')
            self.assertResponse('gpg key add EB17F1E0CEB63930 pgp.mit.edu',
                    '1 key imported, 0 unchanged, 0 not imported.')
            self.assertNotError(
                    'gpg key remove F88ECDE235846FA8652DAF5FEB17F1E0CEB63930')
            self.assertResponse('gpg key add EB17F1E0CEB63930 pgp.mit.edu',
                    '1 key imported, 0 unchanged, 0 not imported.')
            self.assertResponse('gpg key add EB17F1E0CEB63930 pgp.mit.edu',
                    'Error: This key is already associated with your account.')

    if gpg.available:
        def testGpgAuth(self):
            self.assertNotError('register spam egg')
            gpg.keyring.import_keys(PRIVATE_KEY).__dict__
            (id, user) = list(ircdb.users.items())[0]
            user.gpgkeys.append(FINGERPRINT)
            msg = self.getMsg('gpg signing gettoken').args[-1]
            match = re.search('is: ({.*}).', msg)
            assert match, repr(msg)
            token = match.group(1)

            def fakeGetUrlFd(*args, **kwargs):
                fd.geturl = lambda :None
                return fd
            (utils.web.getUrlFd, realGetUrlFd) = (fakeGetUrlFd, utils.web.getUrlFd)

            fd = minisix.io.StringIO()
            fd.write('foo')
            fd.seek(0)
            self.assertResponse('gpg signing auth http://foo.bar/baz.gpg',
                    'Error: Signature or token not found.')

            fd = minisix.io.StringIO()
            fd.write(token)
            fd.seek(0)
            self.assertResponse('gpg signing auth http://foo.bar/baz.gpg',
                    'Error: Signature or token not found.')

            fd = minisix.io.StringIO()
            fd.write(WRONG_TOKEN_SIGNATURE)
            fd.seek(0)
            self.assertRegexp('gpg signing auth http://foo.bar/baz.gpg',
                    'Error: Unknown token.*')

            fd = minisix.io.StringIO()
            fd.write(str(gpg.keyring.sign(token)))
            fd.seek(0)
            self.assertResponse('gpg signing auth http://foo.bar/baz.gpg',
                    'You are now authenticated as spam.')

            utils.web.getUrlFd = realGetUrlFd


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
