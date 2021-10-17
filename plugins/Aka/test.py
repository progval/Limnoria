# -*- coding: utf8 -*-
###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2013-2021, Valentin Lorentz
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
import supybot.httpserver as httpserver
import supybot.plugin as plugin
import supybot.registry as registry
from supybot.utils.minisix import u

from . import plugin as Aka

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
            'Format', 'Reply', 'String')

    def testHistsearch(self):
        self.assertNotError(
                r'aka add histsearch "last --from [cif true '
                r'\"echo test\" \"echo test\"] '
                r'--regexp [concat \"m/$1/\" [re s/g// \"@2\"]]"')
        self.assertResponse('echo foo', 'foo')
        self.assertResponse('histsearch .*foo.*', '@echo foo')

    def testDoesNotOverwriteCommands(self):
        # We don't have dispatcher commands anymore
        #self.assertError('aka add aka "echo foo bar baz"')
        self.assertError('aka add add "echo foo bar baz"')
        self.assertError('aka add remove "echo foo bar baz"')
        self.assertError('aka add lock "echo foo bar baz"')
        self.assertError('aka add unlock "echo foo bar baz"')

    def testAkaHelp(self):
        self.assertNotError(r'aka add slashdot "foo \"bar\" baz"')
        self.assertRegexp('help slashdot', r'Alias for "foo \\"bar\\" baz".')
        self.assertNotError('aka add nonascii echo éé')
        self.assertRegexp('help nonascii', r'Alias for "echo éé".')

        self.assertNotError('aka remove slashdot')
        self.assertNotError('aka add --channel %s slashdot foo' % self.channel)
        self.assertRegexp('help aka slashdot', "an alias on %s.*Alias for .*foo"
                % self.channel)
        self.assertNotError('aka remove --channel %s slashdot' % self.channel)

    def testShow(self):
        self.assertNotError('aka add foo bar')
        self.assertResponse('show foo', 'bar $*')
        self.assertNotError('aka add "foo bar" baz')
        self.assertResponse('show "foo bar"', 'baz $*')

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

        self.assertNotError('aka add doublespam "echo [echo $* $*]"')
        self.assertResponse('doublespam egg', 'egg egg')
        self.assertResponse('doublespam egg bacon', 'egg bacon egg bacon')

    def testExpansionBomb(self):
        self.assertNotError('aka add bomb "bomb $* $* $* $* $*"')
        # if the mitigation doesn't work, this test will eat all memory on the
        # system.
        self.assertResponse('bomb foo', "Error: You've attempted more nesting "
                "than is currently allowed on this bot.")

    def testChannel(self):
        self.assertNotError('aka add channel echo $channel')
        self.assertResponse('aka channel', self.channel)

    def testAddRemoveAka(self):
        cb = self.irc.getCallback('Aka')
        cb._add_aka('global', 'foobar', 'echo sbbone')
        cb._db.lock_aka('global', 'foobar', 'evil_admin')
        self.assertResponse('foobar', 'sbbone')
        self.assertRegexp('aka list', 'foobar')
        self.assertRaises(Aka.AkaError, cb._remove_aka, 'global', 'foobar')
        cb._remove_aka('global', 'foobar', evenIfLocked=True)
        self.assertNotRegexp('aka list', 'foobar')
        self.assertError('foobar')

    def testOptionalArgs(self):
        self.assertNotError('aka add myrepr "repr @1"')
        self.assertResponse('myrepr foo', '"foo"')
        self.assertResponse('myrepr ""', '""')

    def testRequiredAndOptional(self):
        self.assertNotError('aka add reqopt "echo req=$1, opt=@1"')
        self.assertResponse('reqopt foo bar', 'req=foo, opt=bar')
        self.assertResponse('reqopt foo', 'req=foo, opt=')

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
        self.assertNotError(u('aka add café "echo coffee"'))
        self.assertResponse(u('café'), 'coffee')

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
        self.assertResponse('aka add alias aka $*', 'The operation succeeded.')
        self.assertResponse('alias add a+ aka add $*', 'The operation succeeded.')
        self.assertResponse('a+ spam echo egg', 'The operation succeeded.')
        self.assertResponse('spam', 'egg')

    def testIgnore(self):
        self.assertResponse('aka add test ignore', 'The operation succeeded.')
        self.assertNoResponse('test')


class AkaTestCase(PluginTestCase):
    plugins = ('Aka', 'Alias', 'User', 'Utilities')

    def testMaximumLength(self):
        self.assertNotError('aka add "foo bar baz qux quux" "echo test"')
        self.assertError('aka add "foo bar baz qux quux corge" "echo test"')

    def testAkaLockedHelp(self):
        self.assertNotError('register evil_admin foo')

        self.assertNotError('aka add slashdot foo')
        self.assertRegexp('help aka slashdot', "a global alias.*Alias for .*foo")
        self.assertNotRegexp('help aka slashdot', 'Locked by')
        self.assertNotError('aka lock slashdot')
        self.assertRegexp('help aka slashdot', 'Locked by evil_admin')
        self.assertNotError('aka unlock slashdot')
        self.assertNotRegexp('help aka slashdot', 'Locked by')

    def testAliasImport(self):
        self.assertNotError('alias add foo "echo bar"')
        self.assertNotError(u('alias add baz "echo café"'))
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

    def testList(self):
        self.assertNotError('aka add foo bar')
        self.assertRegexp('aka list', r'foo.*?bar \$\*')
        self.assertNotError('aka add "foo bar" baz')
        self.assertRegexp('aka list', r'foo.*?bar \$\*.*?foo bar.*?baz \$\*')

    def testListLockedUnlocked(self):
        self.assertNotError('register tacocat hunter2')

        self.assertNotError('aka add foo bar')
        self.assertNotError('aka add abcd echo hi')
        self.assertNotError('aka lock foo')
        self.assertRegexp('aka list --locked', 'foo')
        self.assertNotRegexp('aka list --locked', 'abcd')
        self.assertNotRegexp('aka list --unlocked', 'foo')
        self.assertRegexp('aka list --unlocked', 'abcd')
        # Can't look up both.
        self.assertError('aka list --locked --unlocked abcd')

    def testSearch(self):
        self.assertNotError('aka add foo bar')
        self.assertNotError('aka add "many words" "much command"')
        self.assertRegexp('aka search f', 'foo')
        self.assertError('aka search abcdefghijklmnop')
        self.assertRegexp('aka search many', 'many words')
        # This should be case insensitive too.
        self.assertRegexp('aka search MaNY', 'many words')

class AkaWebUITestCase(ChannelHTTPPluginTestCase):
    plugins = ('Aka',)
    config = {
        'servers.http.keepAlive': True,
        'plugins.Aka.web.enable': False,
    }

    def setUp(self):
        super(ChannelHTTPPluginTestCase, self).setUp()
        httpserver.startServer()

    def tearDown(self):
        httpserver.stopServer()
        super(ChannelHTTPPluginTestCase, self).tearDown()

    def testToggleWebEnable(self):
        self.assertHTTPResponse('/aka/', 404)
        self.assertNotError('config plugins.Aka.web.enable True')
        self.assertHTTPResponse('/aka/', 200)
        self.assertNotError('config plugins.Aka.web.enable False')
        self.assertHTTPResponse('/aka/', 404)

    def testGlobalPage(self):
        self.assertNotError('config plugins.Aka.web.enable True')

        self.assertNotError('aka add foo1 echo 1')
        self.assertNotError('aka add --channel #foo foo2 echo 2')
        self.assertNotError('aka add --channel #bar foo3 echo 3')

        (respCode, body) = self.request('/aka/list/global')
        self.assertEqual(respCode, 200)
        self.assertIn(b'foo1', body)
        self.assertNotIn(b'foo2', body)
        self.assertNotIn(b'foo3', body)

    def testChannelPage(self):
        self.assertNotError('config plugins.Aka.web.enable True')

        self.assertNotError('aka add foo1 echo 1')
        self.assertNotError('aka add --channel #foo foo2 echo 2')
        self.assertNotError('aka add --channel #bar foo3 echo 3')

        (respCode, body) = self.request('/aka/list/%23foo')
        self.assertEqual(respCode, 200)
        self.assertIn(b'foo1', body)
        self.assertIn(b'foo2', body)
        self.assertNotIn(b'foo3', body)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
