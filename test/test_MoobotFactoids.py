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
        plugins = ('MoobotFactoids', 'User', 'Utilities')
        def setUp(self):
            PluginTestCase.setUp(self)
            # Create a valid user to use
            self.prefix = 'foo!bar@baz'
            self.assertNotError('register tester moo')

        def testAddFactoid(self):
            self.assertNotError('moo is foo')
            # Check stripping punctuation
            self.assertError('moo!?    is foo') # 'moo' already exists
            self.assertNotError('foo!?    is foo') 
            self.assertResponse('foo', 'foo is foo')
            self.assertNotError('bar is <reply>moo is moo')
            self.assertResponse('bar', 'moo is moo')
            # Check substitution
            self.assertNotError('who is <reply>$who')
            self.assertResponse('who', 'foo')

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
            # Check case-insensitivity
            self.assertResponse('MOO', 'foo')
            self.assertResponse('mOo', 'foo')
            self.assertResponse('MoO', 'foo')
            # Check the "_is_" ability
            self.assertNotError('delete moo')
            self.assertNotError('moo _is_ <reply>foo')
            self.assertResponse('moo', 'foo')
            self.assertNotError('foo is bar _is_ baz')
            self.assertResponse('foo is bar', 'foo is bar is baz')

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
                              'requested 2 times. '
                              'Locked by tester on .*\.$')
            self.assertNotError('unlock moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Last modified by tester on .*?\. '
                              'Last requested by foo!bar@baz on .*?, '
                              'requested 2 times.$')
            # Make sure I solved this bug
            # Check and make sure all the other stuff is reset 
            self.assertNotError('foo is bar')
            self.assertNotError('foo =~ s/bar/blah/')
            self.assertNotError('foo')
            self.assertNotError('no foo is baz')
            self.assertRegexp('factinfo foo', '^foo: Created by tester on'
                              '(?!(request|modif)).*?\.$')

        def testLockUnlock(self):
            self.assertNotError('moo is <reply>moo')
            self.assertNotError('lock moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Locked by tester on .*?\.')
            # switch user
            self.prefix = 'moo!moo@moo'
            self.assertNotError('register nottester moo')
            self.assertError('unlock moo')
            self.assertRegexp('factinfo moo', '^moo: Created by tester on'
                              '.*?\. Locked by tester on .*?\.')
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

        def testMost(self):
            # Check an empty database
            self.assertResponse('most popular', 'I can\'t find any factoids.')
            self.assertResponse('most authored', 'I can\'t find any factoids.')
            self.assertResponse('most recent', 'I can\'t find any factoids.')
            # Check singularity response
            self.assertNotError('moogle is <reply>moo')
            self.assertResponse('most popular', 'I can\'t find any factoids.')
            self.assertResponse('most authored', 'Top 1 author: tester (1)') 
            self.assertResponse('most recent', '1 latest factoid: moogle') 
            self.assertResponse('moogle', 'moo')
            self.assertResponse('most popular', 'Top 1 factoid: moogle (1)')
            # Check plural response
            self.assertNotError('mogle is <reply>mo')
            self.assertResponse('most authored', 'Top 1 author: tester (2)') 
            self.assertResponse('most recent', '2 latest factoids: mogle and '\
                'moogle') 
            self.assertResponse('moogle', 'moo')
            self.assertResponse('most popular', 'Top 1 factoid: moogle (2)')
            self.assertResponse('mogle', 'mo')
            self.assertResponse('most popular', 'Top 2 factoids: moogle (2) '\
                'and mogle (1)')

        def testListkeys(self):
            self.assertResponse('listkeys %', 'No keys matching \'%\' found.')
            self.assertNotError('moo is <reply>moo')
            self.assertResponse('listkeys moo', 'Key search for \'moo\' '
                              '(1 found): \'moo\'')
            self.assertResponse('listkeys foo', 'No keys matching \'foo\' '
                                'found.')
            # Throw in a bunch more
            for i in range(10):
                self.assertNotError('moo%s is <reply>moo' % i)
            self.assertRegexp('listkeys moo', '^Key search for \'moo\' '
                              '\(11 found\): (\'moo\d*\', )+and \'moo9\'$')
            self.assertNotError('foo is bar')
            self.assertRegexp('listkeys %', '^Key search for \'\%\' '
                              '\(12 found\): \'foo\', (\'moo\d*\', )+and '
                              '\'moo9\'$')
            # Check quoting
            self.assertNotError('foo\' is bar')
            self.assertResponse('listkeys foo', 'Key search for \'foo\' '
                                '(2 found): \'foo\' and "foo\'"')

        def testListvalues(self):
            self.assertNotError('moo is moo')
            self.assertResponse('listvalues moo', 'Value search for \'moo\' '
                                '(1 found): \'moo\'')

        def testListauth(self):
            self.assertNotError('moo is <reply>moo')
            self.assertRegexp('listauth tester', 'tester.*\(1 found\):.*moo')
            self.assertError('listauth moo')

        def testDelete(self):
            self.assertNotError('moo is <reply>moo')
            self.assertNotError('lock moo')
            self.assertError('delete moo')
            self.assertNotError('unlock moo')
            self.assertNotError('delete moo')

        def testAugmentFactoid(self):
            self.assertNotError('moo is foo')
            self.assertNotError('moo is also bar')
            self.assertResponse('moo', 'moo is foo, or bar')
            self.assertNotError('moo is bar _is_ foo')
            self.assertNotError('moo is bar is also foo')
            self.assertResponse('moo is bar', 'moo is bar is foo, or foo')

        def testReplaceFactoid(self):
            self.assertNotError('moo is foo')
            self.assertNotError('no moo is bar')
            self.assertResponse('moo', 'moo is bar')
            self.assertNotError('no, moo is baz')
            self.assertResponse('moo', 'moo is baz')
            self.assertNotError('lock moo')
            self.assertError('no moo is qux')
            self.assertNotError('foo is bar _is_ foo')
            self.assertNotError('no foo is bar _is_ baz')
            self.assertResponse('foo is bar', 'foo is bar is baz')

        def testRegexpNotCalledIfAlreadyHandled(self):
            self.assertResponse('echo foo is bar', 'foo is bar')
            self.assertNoResponse(' ', 3)

        def testNoResponseToCtcp(self):
            self.assertNotError('foo is bar')
            self.assertResponse('foo', 'foo is bar')
            self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick, '\x01VERSION\x01'))
            m = self.irc.takeMsg()
            self.failIf(m)
                


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
