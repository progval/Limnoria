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

from test import *

try:
    import sqlite
except ImportError:
    sqlite = None

if sqlite is not None:
    class FactoidsTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('MiscCommands', 'MoobotFactoids', 'UserCommands')
        def setUp(self):
            PluginTestCase.setUp(self)
            # Create a valid user to use
            self.prefix = 'foo!bar@baz'
            self.assertNotError('register tester moo')

        def testLiteral(self):
            self.assertError('literal moo') # no factoids yet
            self.assertNotError('moo is <reply>foo')
            self.assertResponse('literal moo', '<reply>foo')
            self.assertNotError('moo2 is moo!')
            self.assertResponse('literal moo2', 'moo!')
            self.assertNotError('moo3 is <action>foo')
            self.assertResponse('literal moo3', '<action>foo')

        def testGetFactoid(self):
            self.assertNotError('moo is <reply>foo')
            self.assertResponse('moo', 'foo')
            self.assertNotError('moo2 is moo!')
            self.assertResponse('moo2', 'moo2 is moo!')
            self.assertNotError('moo3 is <action>foo')
            self.assertAction('moo3', 'foo')
            # Test and make sure it's parsing
            self.assertNotError('moo4 is <reply>(1|2|3)')
            self.assertRegexp('moo4', '^(1|2|3)$')

        def testFactinfo(self):
            self.assertNotError('moo is <reply>foo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on.*$')
            self.assertNotError('moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Last requested by foo!bar@baz on .*?, '
                              'requested 1 time.$')
            self.assertNotError('moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Last requested by foo!bar@baz on .*?, '
                              'requested 2 times.$')
            self.assertNotError('moo =~ s/foo/bar/')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Last modified by tester on .*?\. '
                              'Last requested by foo!bar@baz on .*?, '
                              'requested 2 times.$')
            self.assertNotError('lock moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Last modified by tester on .*?\. '
                              'Last requested by foo!bar@baz on .*?, '
                              'requested 2 times. Locked on .*\.$')
            self.assertNotError('unlock moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Last modified by tester on .*?\. '
                              'Last requested by foo!bar@baz on .*?, '
                              'requested 2 times.$')

        def testLockUnlock(self):
            self.assertNotError('moo is <reply>moo')
            self.assertNotError('lock moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Locked on .*?\.')
            # switch user
            self.prefix = 'moo!moo@moo'
            self.assertNotError('register nottester moo')
            self.assertError('unlock moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Locked on .*?\.')
            # switch back
            self.prefix = 'foo!bar@baz'
            self.assertNotError('identify tester moo')
            self.assertNotError('unlock moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\.')
                              
        def testChangeFactoid(self):
            self.assertNotError('moo is <reply>moo')
            self.assertNotError('moo =~ s/moo/moos/')
            self.assertResponse('moo', 'moos')
            self.assertNotError('moo =~ s/reply/action/')
            self.assertAction('moo', 'moos')
            self.assertNotError('moo =~ s/moos/(moos|woofs)/')
            self.assertActionRegexp('moo', '^(moos|woofs)$')
            self.assertError('moo =~ s/moo/')

        def testListkeys(self):
            self.assertResponse('listkeys *', 'No keys found matching \'*\'.')
            self.assertNotError('moo is <reply>moo')
            self.assertResponse('listkeys moo', 'Key search for \'moo\' '
                              '(1 found): moo')
            self.assertResponse('listkeys foo', 'No keys found matching '
                                '\'foo\'.')
            # Throw in a bunch more
            for i in range(10):
                self.assertNotError('moo%s is <reply>moo' % i)
            self.assertRegexp('listkeys moo', '^Key search for \'moo\' '
                              '(11 found): (moo\d*, )+ and moo9$')
            self.assertRegexp('listkeys *', '^Key search for \'*\' '
                              '(12 found): foo, (moo\d*, )+ and moo9$')

        def testListvalues(self):
            self.assertNotError('moo is <reply>moo')
            self.assertResponse('listvalues moo', 'Value search for \'moo\' '
                                '(1 found): moo')

        def testListauth(self):
            self.assertNotError('moo is <reply>moo')
            self.assertResponse('listauth tester', 'Author search for tester '
                                '(1 found): moo')

    class DunnoTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('MiscCommands', 'MoobotFactoids', 'UserCommands')
        def testDunno(self):
            self.assertNotError('apfasdfjoia') # Should say a dunno, no error

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
