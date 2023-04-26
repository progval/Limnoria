# -*- encoding: utf-8 -*-
###
# Copyright (c) 2003-2005, Daniel DiPaolo
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

import time

from supybot.test import *
#import supybot.plugin as plugin
import supybot.ircutils as ircutils
from supybot.utils.minisix import u

# import sqlite3, so it's in sys.modules and conf.supybot.databases includes
# sqlite3.
try:
    import sqlite3
except ImportError:
    sqlite3 = None

from . import plugin
MFconf = conf.supybot.plugins.MoobotFactoids

class OptionListTestCase(SupyTestCase):
    maxIterations = 267
    def _testOptions(self, s, L):
        max = self.maxIterations
        original = L[:]
        while max and L:
            max -= 1
            option = plugin.pickOptions(s)
            self.assertIn(
                option,
                original,
                'Option %s not in %s' % (option, original)
            )
            if option in L:
                L.remove(option)
        self.assertFalse(L, 'Some options never seen: %s' % L)

    def testPickOptions(self):
        self._testOptions('(a|b)', ['a', 'b'])
        self._testOptions('a', ['a'])
        self._testOptions('(a|b (c|d))', ['a', 'b c', 'b d'])
        self._testOptions('(a|(b|)c)', ['a', 'bc', 'c'])
        self._testOptions('(a(b|)|(c|)d)', ['a', 'ab', 'cd', 'd'])
        self._testOptions('(a|)', ['a', ''])
        self._testOptions('(|a)', ['a', ''])
        self._testOptions('((a)|(b))', ['(a)', '(b)'])
        self._testOptions('^\\%(\\%(foo\\)\\@<!.\\)*$',
                          ['^\\%(\\%(foo\\)\\@<!.\\)*$'])


class NonChannelFactoidsTestCase(ChannelPluginTestCase):
    plugins = ('MoobotFactoids', 'User')
    config = {'reply.whenNotCommand': False}

    def setUp(self):
        ChannelPluginTestCase.setUp(self)
        # Create a valid user to use
        self.prefix = 'mf!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.nick, 'register tester moo',
                                         prefix=self.prefix))
        m = self.irc.takeMsg() # Response to register.
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
        self.assertResponse('who', ircutils.nickFromHostmask(self.prefix))
        # Check that actions ("\x01ACTION...") don't match
        m = ircmsgs.action(self.channel, 'is doing something')
        self.irc.feedMsg(m)
        self.assertNoResponse(' ', 1)

class FactoidsTestCase(ChannelPluginTestCase):
    plugins = ('MoobotFactoids', 'User', 'String', 'Utilities', 'Web')
    config = {'reply.whenNotCommand': False}
    def setUp(self):
        ChannelPluginTestCase.setUp(self)
        # Create a valid user to use
        self.prefix = 'mf!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.nick, 'register tester moo',
                                         prefix=self.prefix))
        m = self.irc.takeMsg() # Response to register.

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
        self.assertResponse('who', ircutils.nickFromHostmask(self.prefix))
        # Check that actions ("\x01ACTION...") don't match
        m = ircmsgs.action(self.channel, 'is doing something')
        self.irc.feedMsg(m)
        self.assertNoResponse(' ', 1)

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
        self.assertRegexp('moo4', r'^(1|2|3)$')
        # Check case-insensitivity
        self.assertResponse('MOO', 'foo')
        self.assertResponse('mOo', 'foo')
        self.assertResponse('MoO', 'foo')
        # Check the "_is_" ability
        self.assertNotError('remove moo')
        self.assertNotError('moo _is_ <reply>foo')
        self.assertResponse('moo', 'foo')
        self.assertNotError('foo is bar _is_ baz')
        self.assertResponse('foo is bar', 'foo is bar is baz')

    def testFactinfo(self):
        self.assertNotError('moo is <reply>foo')
        self.assertRegexp('factinfo moo', r'^moo: Created by tester on.*$')
        self.assertNotError('moo')
        self.assertRegexp('factinfo moo', self.prefix + r'.*1 time')
        self.assertNotError('moo')
        self.assertRegexp('factinfo moo', self.prefix + r'.*2 times')
        self.assertNotError('moo =~ s/foo/bar/')
        self.assertRegexp('factinfo moo',
                          r'^moo: Created by tester on'
                          r'.*?\. Last modified by tester on .*?\. '
                          r'Last requested by %s on .*?, '
                          r'requested 2 times.$' % self.prefix)
        self.assertNotError('lock moo')
        self.assertRegexp('factinfo moo',
                          r'^moo: Created by tester on'
                          r'.*?\. Last modified by tester on .*?\. '
                          r'Last requested by %s on .*?, '
                          r'requested 2 times. '
                          r'Locked by tester on .*\.$' % self.prefix)
        self.assertNotError('unlock moo')
        self.assertRegexp('factinfo moo',
                          r'^moo: Created by tester on'
                          r'.*?\. Last modified by tester on .*?\. '
                          r'Last requested by %s on .*?, '
                          r'requested 2 times.$' % self.prefix)
        # Make sure I solved this bug
        # Check and make sure all the other stuff is reset
        self.assertNotError('foo is bar')
        self.assertNotError('foo =~ s/bar/blah/')
        self.assertNotError('foo')
        self.assertNotError('no foo is baz')
        self.assertRegexp('factinfo foo',
                          r'^foo: Created by tester on'
                          r'(?!(request|modif)).*?\.$')

    def testLockUnlock(self):
        # disable world.testing since we want new users to not
        # magically be endowed with the admin capability
        try:
            world.testing = False
            self.assertNotError('moo is <reply>moo')
            self.assertNotError('lock moo')
            self.assertRegexp('factinfo moo',
                              r'^moo: Created by tester on'
                              r'.*?\. Locked by tester on .*?\.')
            # switch user
            original = self.prefix
            self.prefix = 'moo!moo@moo'
            self.assertNotError('register nottester moo', private=True)
            self.assertError('unlock moo')
            self.assertRegexp('factinfo moo',
                              r'^moo: Created by tester on'
                              r'.*?\. Locked by tester on .*?\.')
            # switch back
            self.prefix = original
            self.assertNotError('identify tester moo', private=True)
            self.assertNotError('unlock moo')
            self.assertRegexp('factinfo moo',
                              r'^moo: Created by tester on.*?\.')
        finally:
            world.testing = True

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
        userPrefix1 = 'moo!bar@baz'; userNick1 = 'moo'
        userPrefix2 = 'boo!bar@baz'; userNick2 = 'boo'
        self.assertNotError('register %s bar' % userNick1,
                            frm=userPrefix1, private=True)
        self.assertNotError('register %s bar' % userNick2,
                            frm=userPrefix2, private=True)
        # Check an empty database
        self.assertError('most popular')
        self.assertError('most authored')
        self.assertError('most recent')
        # Check singularity response
        self.prefix = userPrefix1
        self.assertNotError('moogle is <reply>moo')
        self.assertError('most popular')
        self.assertResponse('most authored',
                            'Most prolific author: moo (1)')
        self.assertRegexp('most recent', r"1 latest factoid:.*moogle")
        self.assertResponse('moogle', 'moo')
        self.assertRegexp('most popular',
                          r"Top 1 requested factoid:.*moogle.*(1)")
        # Check plural response
        time.sleep(1)
        self.prefix = userPrefix2
        self.assertNotError('mogle is <reply>mo')
        self.assertRegexp('most authored',
                          (r'Most prolific authors: .*'
                           r'(moo.*\(1\).*boo.*\(1\)'
                           r'|boo.*\(1\).*moo.*\(1\))'))
        self.assertRegexp('most recent',
                          r"2 latest factoids:.*mogle.*moogle.*")
        self.assertResponse('moogle', 'moo')
        self.assertRegexp('most popular',
                          r"Top 1 requested factoid:.*moogle.*(2)")
        self.assertResponse('mogle', 'mo')
        self.assertRegexp('most popular',
                          r"Top 2 requested factoids:.*"
                          r"moogle.*(2).*mogle.*(1)")
        # Check most author ordering
        self.assertNotError('moo is <reply>oom')
        self.assertRegexp('most authored',
                          r'Most prolific authors:.*boo.*(2).*moo.*(1)')

    def testListkeys(self):
        self.assertResponse('listkeys %', 'No keys matching "%" found.')
        self.assertNotError('moo is <reply>moo')
        # With this set, if only one key matches, it should respond with
        # the factoid
        orig = MFconf.showFactoidIfOnlyOneMatch()
        try:
            MFconf.showFactoidIfOnlyOneMatch.setValue(True)
            self.assertResponse('listkeys moo', 'moo')
            self.assertResponse('listkeys foo', 'No keys matching "foo" '
                                'found.')
            # Throw in a bunch more
            for i in range(10):
                self.assertNotError('moo%s is <reply>moo' % i)
            self.assertRegexp('listkeys moo',
                              r'^Key search for "moo" '
                              r'\(11 found\): ("moo\d*", )+and "moo9"$')
            self.assertNotError('foo is bar')
            self.assertRegexp('listkeys %',
                              r'^Key search for "\%" '
                              r'\(12 found\): "foo", ("moo\d*", )+and '
                              r'"moo9"$')
            # Check quoting
            self.assertNotError('foo\' is bar')
            self.assertResponse('listkeys foo',
                                'Key search for "foo" '
                                '(2 found): "foo" and "foo\'"')
            # Check unicode stuff
            self.assertResponse(u('listkeys Б'),
                    'No keys matching "Б" found.')
            self.assertNotError(u('АБВГДЕЖ is foo'))
            self.assertNotError(u('АБВГДЕЖЗИ is foo'))
            self.assertResponse(u('listkeys Б'),
                                'Key search for "Б" '
                                '(2 found): "АБВГДЕЖ" and "АБВГДЕЖЗИ"')
        finally:
            MFconf.showFactoidIfOnlyOneMatch.setValue(orig)

    def testListvalues(self):
        self.assertNotError('moo is moo')
        self.assertResponse('listvalues moo',
                            'Value search for "moo" (1 found): "moo"')

    def testListauth(self):
        self.assertNotError('moo is <reply>moo')
        self.assertRegexp('listauth tester', r'tester.*\(1 found\):.*moo')
        self.assertError('listauth moo')

    def testRemove(self):
        self.assertNotError('moo is <reply>moo')
        self.assertNotError('lock moo')
        self.assertError('remove moo')
        self.assertNotError('unlock moo')
        self.assertNotError('remove moo')

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
        self.assertFalse(m)

    def testAddFactoidNotCalledWithBadNestingSyntax(self):
        self.assertError('re s/Error:.*/foo/ ]')
        self.assertNoResponse(' ', 3)

    def testConfigShowFactoidIfOnlyOneMatch(self):
        # these are long
        MFconf = conf.supybot.plugins.MoobotFactoids
        self.assertNotError('foo is bar')
        # Default to saying the factoid value
        self.assertResponse('listkeys foo', 'foo is bar')
        # Check the False setting
        MFconf.showFactoidIfOnlyOneMatch.setValue(False)
        self.assertResponse('listkeys foo', 'Key search for "foo" '
                                            '(1 found): "foo"')

    def testRandom(self):
        self.assertNotError('foo is <reply>bar')
        self.assertNotError('bar is <reply>baz')
        self.assertRegexp('random', r'bar|baz')


# vim:set shiftwidth=4 softtabstop=8 expandtab textwidth=78:
