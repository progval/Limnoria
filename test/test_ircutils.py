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

import ircmsgs
import ircutils

class FunctionsTestCase(unittest.TestCase):
    hostmask = 'foo!bar@baz'
    def testIsUserHostmask(self):
        self.failUnless(ircutils.isUserHostmask(self.hostmask))
        self.failUnless(ircutils.isUserHostmask('a!b@c'))
        self.failIf(ircutils.isUserHostmask('!bar@baz'))
        self.failIf(ircutils.isUserHostmask('!@baz'))
        self.failIf(ircutils.isUserHostmask('!bar@'))
        self.failIf(ircutils.isUserHostmask('!@'))
        self.failIf(ircutils.isUserHostmask('foo!@baz'))
        self.failIf(ircutils.isUserHostmask('foo!bar@'))
        self.failIf(ircutils.isUserHostmask(''))
        self.failIf(ircutils.isUserHostmask('!'))
        self.failIf(ircutils.isUserHostmask('@'))
        self.failIf(ircutils.isUserHostmask('!bar@baz'))

    def testIsChannel(self):
        self.failUnless(ircutils.isChannel('#'))
        self.failUnless(ircutils.isChannel('&'))
        self.failUnless(ircutils.isChannel('+'))
        self.failUnless(ircutils.isChannel('!'))
        self.failUnless(ircutils.isChannel('#foo'))
        self.failUnless(ircutils.isChannel('&foo'))
        self.failUnless(ircutils.isChannel('+foo'))
        self.failUnless(ircutils.isChannel('!foo'))
        self.failIf(ircutils.isChannel('#foo bar'))
        self.failIf(ircutils.isChannel('#foo,bar'))
        self.failIf(ircutils.isChannel('#foobar\x07'))
        self.failIf(ircutils.isChannel('foo'))
        self.failIf(ircutils.isChannel(''))

    def testBold(self):
        s = ircutils.bold('foo')
        self.assertEqual(s[0], '\x02')
        self.assertEqual(s[-1], '\x02')

    def testMircColor(self):
        # No colors provided should return the same string
        s = 'foo'
        self.assertEqual(s, ircutils.mircColor(s))
        # Test positional args
        self.assertEqual('\x030foo\x03', ircutils.mircColor(s, 'white'))
        self.assertEqual('\x031,2foo\x03',ircutils.mircColor(s,'black','blue'))
        self.assertEqual('\x03,3foo\x03', ircutils.mircColor(s, None, 'green'))
        # Test keyword args
        self.assertEqual('\x034foo\x03', ircutils.mircColor(s, fg='red'))
        self.assertEqual('\x03,5foo\x03', ircutils.mircColor(s, bg='brown'))
        self.assertEqual('\x036,7foo\x03',
                         ircutils.mircColor(s, bg='orange', fg='purple'))
        
    def testMircColors(self):
        # Make sure all (k, v) pairs are also (v, k) pairs.
        for (k, v) in ircutils.mircColors.items():
            if k:
                self.assertEqual(ircutils.mircColors[v], k)
        
        
    def testSafeArgument(self):
        s = 'I have been running for 9 seconds'
        bolds = ircutils.bold(s)
        self.assertEqual(s, ircutils.safeArgument(s))
        self.assertEqual(bolds, ircutils.safeArgument(bolds))

    def testIsIP(self):
        self.failIf(ircutils.isIP('a.b.c'))
        self.failIf(ircutils.isIP('256.0.0.0'))
        self.failUnless(ircutils.isIP('127.1'))
        self.failUnless(ircutils.isIP('0.0.0.0'))
        self.failUnless(ircutils.isIP('100.100.100.100'))
        self.failUnless(ircutils.isIP('255.255.255.255'))

    def testIsNick(self):
        self.failUnless(ircutils.isNick('jemfinch'))
        self.failUnless(ircutils.isNick('jemfinch0'))
        self.failUnless(ircutils.isNick('[0]'))
        self.failUnless(ircutils.isNick('{jemfinch}'))
        self.failUnless(ircutils.isNick('[jemfinch]'))
        self.failUnless(ircutils.isNick('jem|finch'))
        self.failUnless(ircutils.isNick('\\```'))
        self.failIf(ircutils.isNick(''))
        self.failIf(ircutils.isNick('8foo'))
        self.failIf(ircutils.isNick('10'))

    def banmask(self):
        for msg in msgs:
            if ircutils.isUserHostmask(msg.prefix):
                self.failUnless(ircutils.hostmaskPatternEqual
                                (ircutils.banmask(msg.prefix),
                                 msg.prefix))

    def testSeparateModes(self):
        self.assertEqual(ircutils.separateModes(['+ooo', 'x', 'y', 'z']),
                         [('+o', 'x'), ('+o', 'y'), ('+o', 'z')])
        self.assertEqual(ircutils.separateModes(['+o-o', 'x', 'y']),
                         [('+o', 'x'), ('-o', 'y')])
        self.assertEqual(ircutils.separateModes(['+s-o', 'x']),
                         [('+s', None), ('-o', 'x')])
        self.assertEqual(ircutils.separateModes(['+sntl', '100']),
                        [('+s', None),('+n', None),('+t', None),('+l', '100')])

    def testToLower(self):
        self.assertEqual('jemfinch', ircutils.toLower('jemfinch'))
        self.assertEqual('{}|^', ircutils.toLower('[]\\~'))

    def testNick(self):
        nicks = ['jemfinch', 'jemfinch\\[]~']
        for nick in nicks:
            self.assertEqual(str(ircutils.nick(nick)), str(nick))
            self.assertEqual(ircutils.nick(nick), nick)
            self.assertEqual(ircutils.nick(nick), ircutils.toLower(nick))

    def testReplyTo(self):
        prefix = 'foo!bar@baz'
        channel = ircmsgs.privmsg('#foo', 'bar baz', prefix=prefix)
        private = ircmsgs.privmsg('jemfinch', 'bar baz', prefix=prefix)
        self.assertEqual(ircutils.replyTo(channel), channel.args[0])
        self.assertEqual(ircutils.replyTo(private), private.nick)

    def testJoinModes(self):
        plusE = ('+e', '*!*@*ohio-state.edu')
        plusB = ('+b', '*!*@*umich.edu')
        minusL = ('-l', None)
        modes = [plusB, plusE, minusL]
        self.assertEqual(ircutils.joinModes(modes),
                         ['+be-l', plusB[1], plusE[1]])


class IrcDictTestCase(unittest.TestCase):
    def test(self):
        d = ircutils.IrcDict()
        d['#FOO'] = 'bar'
        self.assertEqual(d['#FOO'], 'bar')
        self.assertEqual(d['#Foo'], 'bar')
        self.assertEqual(d['#foo'], 'bar')
        del d['#fOO']
        d['jemfinch{}'] = 'bar'
        self.assertEqual(d['jemfinch{}'], 'bar')
        self.assertEqual(d['jemfinch[]'], 'bar')
        self.assertEqual(d['JEMFINCH[]'], 'bar')

    def testContains(self):
        d = ircutils.IrcDict()
        d['#FOO'] = None
        self.failUnless('#foo' in d)
        d['#fOOBAR[]'] = None
        self.failUnless('#foobar{}' in d)

    def testGetSetItem(self):
        d = ircutils.IrcDict()
        d['#FOO'] = 12
        self.assertEqual(12, d['#foo'])
        d['#fOOBAR[]'] = 'blah'
        self.assertEqual('blah', d['#foobar{}'])
