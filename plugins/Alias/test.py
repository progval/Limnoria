# -*- coding: utf8 -*-
###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

from supybot.test import *

import supybot.conf as conf
import supybot.plugin as plugin
import supybot.registry as registry
from supybot.utils.minisix import u

from . import plugin as Alias

class FunctionsTest(SupyTestCase):
    def testFindBiggestDollar(self):
        self.assertEqual(Alias.findBiggestDollar(''), 0)
        self.assertEqual(Alias.findBiggestDollar('foo'), 0)
        self.assertEqual(Alias.findBiggestDollar('$0'), 0)
        self.assertEqual(Alias.findBiggestDollar('$1'), 1)
        self.assertEqual(Alias.findBiggestDollar('$2'), 2)
        self.assertEqual(Alias.findBiggestDollar('$2 $10'), 10)
        self.assertEqual(Alias.findBiggestDollar('$3'), 3)
        self.assertEqual(Alias.findBiggestDollar('$3 $2 $1'), 3)
        self.assertEqual(Alias.findBiggestDollar('foo bar $1'), 1)
        self.assertEqual(Alias.findBiggestDollar('foo $2 $1'), 2)
        self.assertEqual(Alias.findBiggestDollar('foo $0 $1'), 1)
        self.assertEqual(Alias.findBiggestDollar('foo $1 $3'), 3)
        self.assertEqual(Alias.findBiggestDollar('$10 bar $1'), 10)


class AliasTestCase(ChannelPluginTestCase):
    plugins = ('Alias', 'Filter', 'Utilities', 'Format', 'Reply')
    def testNoAliasWithNestedCommandName(self):
        self.assertError('alias add foo "[bar] baz"')

    def testDoesNotOverwriteCommands(self):
        # We don't have dispatcher commands anymore
        #self.assertError('alias add alias "echo foo bar baz"')
        self.assertError('alias add add "echo foo bar baz"')
        self.assertError('alias add remove "echo foo bar baz"')
        self.assertError('alias add lock "echo foo bar baz"')
        self.assertError('alias add unlock "echo foo bar baz"')

    def testAliasHelp(self):
        self.assertNotError('alias add slashdot foo')
        self.assertRegexp('help slashdot', "Alias for .*foo")
        self.assertNotError('alias add nonascii echo éé')
        self.assertRegexp('help nonascii', "Alias for .*echo éé")

    def testRemove(self):
        self.assertNotError('alias add foo echo bar')
        self.assertResponse('foo', 'bar')
        self.assertNotError('alias remove foo')
        self.assertError('foo')

    def testDollars(self):
        self.assertNotError('alias add rot26 "rot13 [rot13 $1]"')
        self.assertResponse('rot26 foobar', 'foobar')

    def testMoreDollars(self):
        self.assertNotError('alias add rev "echo $3 $2 $1"')
        self.assertResponse('rev foo bar baz', 'baz bar foo')

    def testAllArgs(self):
        self.assertNotError('alias add swap "echo $2 $1 $*"')
        self.assertResponse('swap 1 2 3 4 5', '2 1 3 4 5')
        self.assertError('alias add foo "echo $1 @1 $*"')
        self.assertNotError('alias add moo echo $1 $*')
        self.assertError('moo')
        self.assertResponse('moo foo', 'foo')
        self.assertResponse('moo foo bar', 'foo bar')
    
    def testChannel(self):
        self.assertNotError('alias add channel echo $channel')
        self.assertResponse('alias channel', self.channel)

    def testNick(self):
        self.assertNotError('alias add sendingnick "rot13 [rot13 $nick]"')
        self.assertResponse('sendingnick', self.nick)

    def testAddRemoveAlias(self):
        cb = self.irc.getCallback('Alias')
        cb.addAlias(self.irc, 'foobar', 'echo sbbone', lock=True)
        self.assertResponse('foobar', 'sbbone')
        self.assertRaises(Alias.AliasError, cb.removeAlias, 'foobar')
        cb.removeAlias('foobar', evenIfLocked=True)
        self.assertNotIn('foobar', cb.aliases)
        self.assertError('foobar')

        self.assertRegexp('alias add abc\x07 ignore', 'Error.*Invalid')

    def testOptionalArgs(self):
        self.assertNotError('alias add myrepr "repr @1"')
        self.assertResponse('myrepr foo', '"foo"')
        self.assertResponse('myrepr ""', '""')

    def testNoExtraSpaces(self):
        self.assertNotError('alias add foo "action takes $1\'s money"')
        self.assertResponse('foo bar', '\x01ACTION takes bar\'s money\x01')

    def testNoExtraQuotes(self):
        self.assertNotError('alias add myre "echo s/$1/$2/g"')
        self.assertResponse('myre foo bar', 's/foo/bar/g')

    def testUnicode(self):
        self.assertNotError(u('alias add \u200b echo foo'))
        self.assertResponse(u('\u200b'), 'foo')

        self.assertNotError('alias add café echo bar')
        self.assertResponse('café', 'bar')

    def testSimpleAliasWithoutArgsImpliesDollarStar(self):
        self.assertNotError('alias add exo echo')
        self.assertResponse('exo foo bar baz', 'foo bar baz')

class EscapedAliasTestCase(ChannelPluginTestCase):
    plugins = ('Alias', 'Utilities')
    def setUp(self):
        registry._cache.update(
            {'supybot.plugins.Alias.escapedaliases.a1a3dfoobar': 'echo baz',
            'supybot.plugins.Alias.escapedaliases.a1a3dfoobar.locked': 'False'})
        super(EscapedAliasTestCase, self).setUp()

    def testReadDatabase(self):
        self.assertResponse('foo.bar', 'baz')

    def testAdd(self):
        self.assertNotError('alias add spam.egg echo hi')
        self.assertResponse('spam.egg', 'hi')

        self.assertNotError('alias add spam|egg echo hey')
        self.assertResponse('spam|egg', 'hey')

        self.assertNotError('alias remove spam.egg')
        self.assertError('spam.egg')
        self.assertNotError('spam|egg')
        self.assertNotError('alias remove spam|egg')
        self.assertError('spam.egg')
        self.assertError('spam|egg')

    def testWriteDatabase(self):
        self.assertNotError('alias add fooo.spam echo egg')
        self.assertResponse('fooo.spam', 'egg')
        self.assertTrue(hasattr(conf.supybot.plugins.Alias.escapedaliases,
            'a1a4dfooospam'))
        self.assertEqual(conf.supybot.plugins.Alias.escapedaliases.a1a4dfooospam(),
                'echo egg')

        self.assertNotError('alias add foo.spam.egg echo supybot')
        self.assertResponse('foo.spam.egg', 'supybot')
        self.assertTrue(hasattr(conf.supybot.plugins.Alias.escapedaliases,
            'a2a3d8dfoospamegg'))
        self.assertEqual(conf.supybot.plugins.Alias.escapedaliases.a2a3d8dfoospamegg(),
                'echo supybot')
        self.assertEqual(Alias.unescapeAlias('a2a3d8dfoospamegg'),
            'foo.spam.egg')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
