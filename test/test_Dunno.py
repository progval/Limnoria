#!/usr/bin/env python

###
# Copyright (c) 2003, Daniel DiPaolo
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

try:
    import sqlite
except ImportError:
    sqlite = None

if sqlite is not None:
    class DunnoTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('Dunno', 'User')
        def setUp(self):
            PluginTestCase.setUp(self)
            self.prefix = 'foo!bar@baz'
            self.assertNotError('register tester moo')

        def testDunnoAdd(self):
            self.assertNotError('dunno add moo')
            self.assertResponse('asdfagagfosdfk', 'moo')

        def testDunnoRemove(self):
            self.assertNotError('dunno add moo')
            self.assertNotError('dunno remove 1')

        def testDunnoSearch(self):
            self.assertNotError('dunno add foo')
            self.assertError('dunno search moo')
            self.assertNotError('dunno add moo')
            self.assertResponse('dunno search moo', 'Dunno search for \'moo\' '
                                '(1 found): 2.')
            self.assertResponse('dunno search m', 'Dunno search for \'m\' '
                                '(1 found): 2.')
            # Test multiple adds
            for i in range(5):
                self.assertNotError('dunno add moo%s' % i)
            self.assertResponse('dunno search moo',
                                'Dunno search for \'moo\' (6 found): '
                                '2, 3, 4, 5, 6, and 7.')

        def testDunnoGet(self):
            self.assertNotError('dunno add moo')
            self.assertResponse('dunno get 1', 'Dunno #1: \'moo\'.')
            self.assertNotError('dunno add $who')
            self.assertResponse('dunno get 2', 'Dunno #2: \'$who\'.')
            self.assertError('dunno get 3')
            self.assertError('dunno get a')

        def testDunnoChange(self):
            self.assertNotError('dunno add moo')
            self.assertNotError('dunno change 1 s/moo/bar/')
            self.assertRegexp('dunno get 1', '.*?: \'bar\'')
