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

Alias = loadPlugin('Alias')


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
        self.assertEqual(Alias.findBiggestDollar(''), None)
        self.assertEqual(Alias.findBiggestDollar('foo'), None)
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


class AliasTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('Alias', 'FunCommands', 'Utilities', 'MiscCommands')
    def testAliasHelp(self):
        self.assertNotError('alias slashdot foo')
        self.assertNotRegexp('help slashdot', 'None')
        self.assertResponse('morehelp slashdot', "Alias for 'foo'")
        
    def testSimpleAlias(self):
        pi = '3.1456926535897932384626433832795028841971693'
        self.assertNotError('alias pi %s' % pi)
        self.assertReponse('pi', pi)

    def testSimpleAlias(self):
        s = 'foobar'
        self.assertNotError('alias foo "rot13 %s"' % s)
        self.assertResponse('foo', s.encode('rot13'))

    def testDollars(self):
        self.assertNotError('alias rot26 "rot13 [rot13 $1]"')
        self.assertResponse('rot26 foobar', 'foobar')

    def testMoreDollars(self):
        self.assertNotError('alias rev "echo $3 $2 $1"')
        self.assertResponse('rev foo bar baz', 'baz bar foo')

    def testNoRecursion(self):
        self.assertError('alias rotinfinity "rot13 [rotinfinity $1]"')

    def testNonCanonicalName(self):
        self.assertError('alias FOO foo')

    def testNotCannotNestRaised(self):
        self.assertNotError('alias mytell "tell $channel $1"')
        self.assertNotError('mytell #foo bugs')
        self.assertNoResponse('blah blah blah', 2)

    def testAddAlias(self):
        cb = self.irc.getCallback('Alias')
        cb.addAlias(self.irc, 'foobar', 'rot13 foobar')
        self.assertResponse('foobar', 'sbbone')
        


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
