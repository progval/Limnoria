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

import conf
import utils
import ircmsgs
import callbacks

tokenize = callbacks.tokenize


class TokenizerTestCase(unittest.TestCase):
    def testEmpty(self):
        self.assertEqual(tokenize(''), [])

    def testNullCharacter(self):
        self.assertEqual(tokenize(utils.dqrepr('\0')), ['\0'])

    def testSingleDQInDQString(self):
        self.assertEqual(tokenize('"\\""'), ['"'])

    def testDQsWithBackslash(self):
        self.assertEqual(tokenize('"\\\\"'), ["\\"])

    def testSingleWord(self):
        self.assertEqual(tokenize('foo'), ['foo'])

    def testMultipleSimpleWords(self):
        words = 'one two three four five six seven eight'.split()
        for i in range(len(words)):
            self.assertEqual(tokenize(' '.join(words[:i])), words[:i])

    def testSingleQuotesNotQuotes(self):
        self.assertEqual(tokenize("it's"), ["it's"])

    def testQuotedWords(self):
        self.assertEqual(tokenize('"foo bar"'), ['foo bar'])
        self.assertEqual(tokenize('""'), [''])
        self.assertEqual(tokenize('foo "" bar'), ['foo', '', 'bar'])
        self.assertEqual(tokenize('foo "bar baz" quux'),
                         ['foo', 'bar baz', 'quux'])

    def testNesting(self):
        self.assertEqual(tokenize('[]'), [[]])
        self.assertEqual(tokenize('[foo]'), [['foo']])
        self.assertEqual(tokenize('foo [bar]'), ['foo', ['bar']])
        self.assertEqual(tokenize('foo bar [baz quux]'),
                         ['foo', 'bar', ['baz', 'quux']])

    def testError(self):
        self.assertRaises(SyntaxError, tokenize, '[foo') #]
        self.assertRaises(SyntaxError, tokenize, '"foo') #"

    def testPipe(self):
        try:
            conf.enablePipeSyntax = True
            self.assertRaises(SyntaxError, tokenize, '| foo')
            self.assertRaises(SyntaxError, tokenize, 'foo ||bar')
            self.assertRaises(SyntaxError, tokenize, 'bar |')
            self.assertEqual(tokenize('foo | bar'), ['bar', ['foo']])
            self.assertEqual(tokenize('foo | bar | baz'),
                             ['baz', ['bar',['foo']]])
            self.assertEqual(tokenize('foo bar | baz'),
                             ['baz', ['foo', 'bar']])
            self.assertEqual(tokenize('foo | bar baz'),
                             ['bar', 'baz', ['foo']])
            self.assertEqual(tokenize('foo bar | baz quux'),
                             ['baz', 'quux', ['foo', 'bar']])
        finally:
            conf.enablePipeSyntax = False
        


class FunctionsTestCase(unittest.TestCase):
    def testCanonicalName(self):
        self.assertEqual('foo', callbacks.canonicalName('foo'))
        self.assertEqual('foobar', callbacks.canonicalName('foo-bar'))
        self.assertEqual('foobar', callbacks.canonicalName('foo_bar'))
        self.assertEqual('foobar', callbacks.canonicalName('FOO-bar'))
        self.assertEqual('foobar', callbacks.canonicalName('FOOBAR'))
        self.assertEqual('foobar', callbacks.canonicalName('foo___bar'))
        self.assertEqual('foobar', callbacks.canonicalName('_f_o_o-b_a_r_'))

    def testAddressed(self):
        oldprefixchars = conf.prefixChars
        nick = 'supybot'
        conf.prefixChars = '~!@'
        inChannel = ['~foo', '@foo', '!foo',
                     '%s: foo' % nick, '%s foo' % nick]
        inChannel = [ircmsgs.privmsg('#foo', s) for s in inChannel]
        badmsg = ircmsgs.privmsg('#foo', '%s:foo' % nick)
        self.failIf(callbacks.addressed(nick, badmsg))
        for msg in inChannel:
            self.assertEqual('foo', callbacks.addressed(nick, msg), msg)
        msg = ircmsgs.privmsg(nick, 'foo')
        self.assertEqual('foo', callbacks.addressed(nick, msg))
        conf.prefixChars = oldprefixchars

    def testReply(self):
        prefix = 'foo!bar@baz'
        channelMsg = ircmsgs.privmsg('#foo', 'bar baz', prefix=prefix)
        nonChannelMsg = ircmsgs.privmsg('supybot', 'bar baz', prefix=prefix)
        self.assertEqual(ircmsgs.privmsg(nonChannelMsg.nick, 'foo'),
                         callbacks.reply(nonChannelMsg, 'foo'))
        self.assertEqual(ircmsgs.privmsg(channelMsg.args[0],
                                         '%s: foo' % channelMsg.nick),
                         callbacks.reply(channelMsg, 'foo'))

    def testGetCommands(self):
        self.assertEqual(callbacks.getCommands(['foo']), ['foo'])
        self.assertEqual(callbacks.getCommands(['foo', 'bar']), ['foo'])
        self.assertEqual(callbacks.getCommands(['foo', ['bar', 'baz']]),
                         ['foo', 'bar'])
        self.assertEqual(callbacks.getCommands(['foo', 'bar', ['baz']]),
                         ['foo', 'baz'])
        self.assertEqual(callbacks.getCommands(['foo', ['bar'], ['baz']]),
                         ['foo', 'bar', 'baz'])
        

class PrivmsgTestCase(PluginTestCase):
    plugins = ('Utilities',)
    def testEmptySquareBrackets(self):
        self.assertResponse('echo []', '[]')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
