###
# Copyright (c) 2003-2005, Daniel DiPaolo
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

class DunnoTestCase(ChannelPluginTestCase):
    plugins = ('Dunno', 'User')
    def setUp(self):
        PluginTestCase.setUp(self)
        self.prefix = 'foo!bar@baz'
        self.assertNotError('register tester moo', private=True)

    def testDunnoAdd(self):
        self.assertNotError('dunno add moo')
        self.assertResponse('asdfagagfosdfk', 'moo')

    def testDunnoRemove(self):
        self.assertNotError('dunno add moo')
        self.assertNotError('dunno remove 1')

    def testDunnoSearch(self):
        self.assertNotError('dunno add foo')
        self.assertRegexp('dunno search moo', 'No.*dunnos.*found')
        # Test searching using just the getopts
        self.assertRegexp('dunno search --regexp m/foo/', r'1 found')
        self.assertNotError('dunno add moo')
        self.assertRegexp('dunno search moo', r'1 found')
        self.assertRegexp('dunno search m', r'1 found')
        # Test multiple adds
        for i in range(5):
            self.assertNotError('dunno add moo%s' % i)
        self.assertRegexp('dunno search moo', r'6 found')

    def testDunnoGet(self):
        self.assertNotError('dunno add moo')
        self.assertRegexp('dunno get 1', r'#1.*moo')
        self.assertNotError('dunno add $who')
        self.assertRegexp('dunno get 2', r'#2.*\$who')
        self.assertError('dunno get 3')
        self.assertError('dunno get a')

    def testDunnoChange(self):
        self.assertNotError('dunno add moo')
        self.assertNotError('dunno change 1 s/moo/bar/')
        self.assertRegexp('dunno get 1', '.*?: [\'"]bar[\'"]')

    def testDollarCommand(self):
        self.assertNotError("dunno add I can't $command.")
        self.assertResponse('asdf', "I can't asdf.")


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
