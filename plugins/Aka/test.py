# -*- coding: utf8 -*-
###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

import supybot.conf as conf
import supybot.plugin as plugin
import supybot.registry as registry

import plugin as Aka

class FunctionsTest(SupyTestCase):
    def testFindBiggestDollar(self):
        self.assertEqual(Aka.findBiggestDollar(''), 0)
        self.assertEqual(Aka.findBiggestDollar('foo'), 0)
        self.assertEqual(Aka.findBiggestDollar('$0'), 0)
        self.assertEqual(Aka.findBiggestDollar('$1'), 1)
        self.assertEqual(Aka.findBiggestDollar('$2'), 2)
        self.assertEqual(Aka.findBiggestDollar('$2 $10'), 10)
        self.assertEqual(Aka.findBiggestDollar('$3'), 3)
        self.assertEqual(Aka.findBiggestDollar('$3 $2 $1'), 3)
        self.assertEqual(Aka.findBiggestDollar('foo bar $1'), 1)
        self.assertEqual(Aka.findBiggestDollar('foo $2 $1'), 2)
        self.assertEqual(Aka.findBiggestDollar('foo $0 $1'), 1)
        self.assertEqual(Aka.findBiggestDollar('foo $1 $3'), 3)
        self.assertEqual(Aka.findBiggestDollar('$10 bar $1'), 10)

class AkaChannelTestCase(ChannelPluginTestCase):
    plugins = ('Aka', 'Conditional', 'Filter', 'Math', 'Utilities',
            'Format', 'Reply')

    def testDoesNotOverwriteCommands(self):
        # We don't have dispatcher commands anymore
        #self.assertError('aka add aka "echo foo bar baz"')
        self.assertError('aka add add "echo foo bar baz"')
        self.assertError('aka add remove "echo foo bar baz"')
        self.assertError('aka add lock "echo foo bar baz"')
        self.assertError('aka add unlock "echo foo bar baz"')

    def testAkaHelp(self):
        self.assertNotError('aka add slashdot foo')
        self.assertRegexp('help slashdot', "Alias for .*foo")
        self.assertNotError('aka add nonascii echo éé')
        self.assertRegexp('help nonascii', "Alias for .*echo éé")

    def testRemove(self):
        self.assertNotError('aka add foo echo bar')
        self.assertResponse('foo', 'bar')
        self.assertNotError('aka remove foo')
        self.assertError('foo')

    def testDollars(self):
        self.assertNotError('aka add rot26 "rot13 [rot13 $1]"')
        self.assertResponse('rot26 foobar', 'foobar')

    def testMoreDollars(self):
        self.assertNotError('aka add rev "echo $3 $2 $1"')
        self.assertResponse('rev foo bar baz', 'baz bar foo')

    def testAllArgs(self):
        self.assertNotError('aka add swap "echo $2 $1 $*"')
        self.assertResponse('swap 1 2 3 4 5', '2 1 3 4 5')
        self.assertError('aka add foo "echo $1 @1 $*"')
        self.assertNotError('aka add moo echo $1 $*')
        self.assertError('moo')
        self.assertResponse('moo foo', 'foo')
        self.assertResponse('moo foo bar', 'foo bar')

        self.assertNotError('aka add spam "echo [echo $*]"')
        self.assertResponse('spam egg', 'egg')
        self.assertResponse('spam egg bacon', 'egg bacon')
    
    def testChannel(self):
        self.assertNotError('aka add channel echo $channel')
        self.assertResponse('aka channel', self.channel)

    def testAddRemoveAka(self):
        cb = self.irc.getCallback('Aka')
        cb._add_aka('global', 'foobar', 'echo sbbone')
        cb._db.lock_aka('global', 'foobar', 'evil_admin')
        self.assertResponse('foobar', 'sbbone')
        self.assertRegexp('list Aka', 'foobar')
        self.assertRaises(Aka.AkaError, cb._remove_aka, 'global', 'foobar')
        cb._remove_aka('global', 'foobar', evenIfLocked=True)
        self.assertNotRegexp('list Aka', 'foobar')
        self.assertError('foobar')

    def testOptionalArgs(self):
        self.assertNotError('aka add myrepr "repr @1"')
        self.assertResponse('myrepr foo', '"foo"')
        self.assertResponse('myrepr ""', '""')

    def testNoExtraSpaces(self):
        self.assertNotError('aka add foo "action takes $1\'s money"')
        self.assertResponse('foo bar', '\x01ACTION takes bar\'s money\x01')

    def testNoExtraQuotes(self):
        self.assertNotError('aka add myre "echo s/$1/$2/g"')
        self.assertResponse('myre foo bar', 's/foo/bar/g')

    def testSimpleAkaWithoutArgsImpliesDollarStar(self):
        self.assertNotError('aka add exo echo')
        self.assertResponse('exo foo bar baz', 'foo bar baz')

    def testChannelPriority(self):
        self.assertNotError('aka add spam "echo foo"')
        self.assertNotError('aka add --channel %s spam "echo bar"' %
                self.channel)
        self.assertResponse('spam', 'bar')

        self.assertNotError('aka add --channel %s egg "echo baz"' %
                self.channel)
        self.assertNotError('aka add egg "echo qux"')
        self.assertResponse('egg', 'baz')

    def testComplicatedNames(self):
        self.assertNotError(u'aka add café "echo coffee"')
        self.assertResponse(u'café', 'coffee')

        self.assertNotError('aka add "foo bar" "echo spam"')
        self.assertResponse('foo bar', 'spam')
        self.assertNotError('aka add "foo" "echo egg"')
        self.assertResponse('foo', 'egg')
        # You could expect 'spam' here, but in fact, this is dangerous.
        # Just imagine this session:
        # <evil_user> aka add "echo foo" quit
        # <bot> The operation succeeded.
        # ...
        # <owner> echo foo
        # * bot has quit
        self.assertResponse('foo bar', 'egg')

    def testNoOverride(self):
        self.assertNotError('aka add "echo foo" "echo bar"')
        self.assertResponse('echo foo', 'foo')
        self.assertNotError('aka add foo "echo baz"')
        self.assertNotError('aka add "foo bar" "echo qux"')
        self.assertResponse('foo bar', 'baz')

    def testRecursivity(self):
        self.assertNotError('aka add fact '
                r'"cif [nceq $1 0] \"echo 1\" '
                r'\"calc $1 * [fact [calc $1 - 1]]\""')
        self.assertResponse('fact 4', '24')
        self.assertRegexp('fact 50', 'more nesting')

    def testDollarStarNesting(self):
        self.assertNotError('aka add alias aka $*')
        self.assertNotError('alias add a+ aka add $*')

class AkaTestCase(PluginTestCase):
    plugins = ('Aka', 'Alias', 'User', 'Utilities')

    def testMaximumLength(self):
        self.assertNotError('aka add "foo bar baz qux quux" "echo test"')
        self.assertError('aka add "foo bar baz qux quux corge" "echo test"')

    def testAkaLockedHelp(self):
        self.assertNotError('register evil_admin foo')

        self.assertNotError('aka add slashdot foo')
        self.assertRegexp('help aka slashdot', "Alias for .*foo")
        self.assertNotRegexp('help aka slashdot', 'Locked by')
        self.assertNotError('aka lock slashdot')
        self.assertRegexp('help aka slashdot', 'Locked by evil_admin')
        self.assertNotError('aka unlock slashdot')
        self.assertNotRegexp('help aka slashdot', 'Locked by')

    def testAliasImport(self):
        self.assertNotError('alias add foo "echo bar"')
        self.assertNotError(u'alias add baz "echo café"')
        self.assertNotError('aka add qux "echo quux"')
        self.assertResponse('alias foo', 'bar')
        self.assertResponse('alias baz', 'café')
        self.assertRegexp('aka foo', 'there is no command named')
        self.assertResponse('aka qux', 'quux')

        self.assertNotError('aka importaliasdatabase')

        self.assertRegexp('alias foo', 'there is no command named')
        self.assertResponse('aka foo', 'bar')
        self.assertResponse('aka baz', 'café')
        self.assertResponse('aka qux', 'quux')

        self.assertNotError('alias add foo "echo test"')
        self.assertNotError('alias add spam "echo egg"')
        self.assertNotError('alias lock spam')

        self.assertRegexp('aka importaliasdatabase',
            r'the 1 following command: foo \(This Aka already exists.\)$')
        self.assertResponse('aka foo', 'bar')
        self.assertResponse('alias foo', 'test')
        self.assertRegexp('alias spam', 'there is no command named')
        self.assertResponse('aka spam', 'egg')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
