###
# Copyright (c) 2019, James Lu <james@overdrivenetworks.com>
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

import supybot
from supybot.test import *

class MiscTestCase(SupyTestCase):

    def testAuthorExpand(self):
        # The standard 3 pair: name, nick, email
        self.assertEqual(str(supybot.authors.progval),
                         'Valentin Lorentz (ProgVal) <progval@gmail.com>')
        # All 3 provided, but name == nick
        self.assertEqual(str(supybot.Author('foobar', 'foobar', 'foobar@example.net')),
                         'foobar <foobar@example.net>')
        # Only name provided
        self.assertEqual(str(supybot.Author('somedev')), 'somedev')
        # Only nick provided
        self.assertEqual(str(supybot.Author(nick='somedev')), 'somedev')
        # Only name and nick provided
        self.assertEqual(str(supybot.Author('James Lu', 'tacocat')), 'James Lu (tacocat)')
        # Only name and nick provided, but name == nick
        self.assertEqual(str(supybot.Author('tacocat', 'tacocat')), 'tacocat')
        # Only name and email
        self.assertEqual(str(supybot.authors.jlu), 'James Lu <james@overdrivenetworks.com>')
        # Only nick and email
        self.assertEqual(str(supybot.Author(nick='abcdef', email='abcdef@example.org')), 'abcdef <abcdef@example.org>')
        # Only email?
        self.assertEqual(str(supybot.Author(email='xyzzy@localhost.localdomain')), 'Unknown author <xyzzy@localhost.localdomain>')

    def testAuthorExpandShort(self):
        self.assertEqual(supybot.authors.progval.format(short=True),
                         'Valentin Lorentz (ProgVal)')
        self.assertEqual(supybot.authors.jlu.format(short=True),
                         'James Lu')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
