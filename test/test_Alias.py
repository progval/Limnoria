#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

Alias = OwnerCommands.loadPluginModule('Alias')


class FunctionsTest(unittest.TestCase):
    def testFindAliasCommand(self):
        s = 'command'
        self.failIf(Alias.findAliasCommand(s, ''))
        self.failIf(Alias.findAliasCommand(s, 'foo'))
        self.failIf(Alias.findAliasCommand(s, 'foo bar [  baz]'))
        self.failIf(Alias.findAliasCommand(s, 'foo bar [baz]'))
        self.failUnless(Alias.findAliasCommand(s, s))
        self.failUnless(Alias.findAliasCommand(s, '  %s' % s))
        self.failUnless(Alias.findAliasCommand(s, '[%s]' % s))
        self.failUnless(Alias.findAliasCommand(s, '[ %s]' % s))
        self.failUnless(Alias.findAliasCommand(s, 'foo bar [%s]' % s))
        self.failUnless(Alias.findAliasCommand(s, 'foo bar [ %s]' % s))
        self.failUnless(Alias.findAliasCommand(s, 'foo | %s' % s))
        self.failUnless(Alias.findAliasCommand(s, 'foo |%s' % s))

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


class AliasTestCase(ChannelPluginTestCase, PluginDocumentation):
    plugins = ('Alias', 'FunCommands', 'Utilities', 'MiscCommands')
    def testAliasHelp(self):
        self.assertNotError('alias slashdot foo')
        self.assertNotRegexp('syntax slashdot', 'None')
        self.assertRegexp('help slashdot', "Alias for 'foo'")
        
    def testSimpleAlias(self):
        pi = '3.1456926535897932384626433832795028841971693'
        self.assertNotError('alias pi %s' % pi)
        self.assertResponse('pi', pi)

    def testDollars(self):
        self.assertNotError('alias rot26 "rot13 [rot13 $1]"')
        self.assertResponse('rot26 foobar', 'foobar')

    def testMoreDollars(self):
        self.assertNotError('alias rev "echo $3 $2 $1"')
        self.assertResponse('rev foo bar baz', 'baz bar foo')

    def testAllArgs(self):
        self.assertNotError('alias swap "echo $2 $1 $*"')
        self.assertResponse('swap 1 2 3 4 5', '2 1 3 4 5')
        self.assertError('alias foo "echo $1 @1 $*"')

    def testNoRecursion(self):
        self.assertError('alias rotinfinity "rot13 [rotinfinity $1]"')

    def testNonCanonicalName(self):
        self.assertError('alias FOO foo')
        self.assertError('alias [] foo')
        self.assertError('alias "foo bar" foo')
        try:
            conf.enablePipeSyntax = True
            self.assertError('alias "foo|bar" foo')
            conf.enablePipeSyntax = False
            self.assertNotError('alias "foo|bar" foo')
        finally:
            conf.enablePipeSyntax = False

    def testNotCannotNestRaised(self):
        self.assertNotError('alias mytell "tell $channel $1"')
        self.assertNotError('mytell #foo bugs')
        self.assertNoResponse('blah blah blah', 2)

    def testChannel(self):
        self.assertNotError('alias channel $channel')
        self.assertResponse('channel', self.channel)

    def testNick(self):
        self.assertNotError('alias sendingnick $nick')
        self.assertResponse('sendingnick', self.nick)

    def testAddRemoveAlias(self):
        cb = self.irc.getCallback('Alias')
        cb.addAlias(self.irc, 'foobar', 'sbbone', freeze=True)
        self.assertResponse('foobar', 'sbbone')
        self.assertRaises(Alias.AliasError, cb.removeAlias, 'foobar')
        cb.removeAlias('foobar', evenIfFrozen=True)
        self.failIf('foobar' in cb.frozen)
        self.assertNoResponse('foobar', 2)

    def testOptionalArgs(self):
        self.assertNotError('alias myrepr "repr @1"')
        self.assertResponse('myrepr foo', '"foo"')
        self.assertResponse('myrepr ""', '""')
        


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
