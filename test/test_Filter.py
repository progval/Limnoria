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

from testsupport import *

import re

import utils

class FilterTest(ChannelPluginTestCase, PluginDocumentation):
    plugins = ('Filter',)
    def testNoErrors(self):
        self.assertNotError('leet foobar')
        self.assertNotError('lithp meghan sweeney')

    def testJeffk(self):
        for i in range(100):
            self.assertNotError('jeffk the quick brown fox is ghetto')

    def testSquish(self):
        self.assertResponse('squish foo bar baz', 'foobarbaz')
        self.assertResponse('squish "foo bar baz"', 'foobarbaz')

    def testLithp(self):
        self.assertResponse('lithp jamessan', 'jamethan')

    def testMorse(self):
        self.assertResponse('unmorse [morse jemfinch]', 'JEMFINCH')

    def testReverse(self):
        for nick in nicks[:10]:
            self.assertResponse('reverse %s' % nick, nick[::-1])

    def testBinary(self):
        self.assertResponse('binary A', '01000001')

    def testRot13(self):
        for s in nicks[:10]: # 10 is probably enough.
            self.assertResponse('rot13 [rot13 %s]' % s, s)

    def testHexlifyUnhexlify(self):
        for s in nicks[:10]: # 10, again, is probably enough.
            self.assertResponse('unhexlify [hexlify %s]' % s, s)

    def testScramble(self):
        s = 'the recalcitrant jamessan tests his scramble function'
        self.assertNotRegexp('scramble %s' % s, s)
        s = 'the recalc1trant jam3ssan tests his scramble fun><tion'
        self.assertNotRegexp('scramble %s' % s, s)

    def testColorize(self):
        self.assertNotRegexp('colorize foobar', r'\s+')
        self.assertRegexp('colorize foobar', r'\x03')

    def testOutfilter(self):
        s = self.nick.encode('rot13')
        self.assertNotError('outfilter rot13')
        self.assertResponse('rot13 foobar', '%s: foobar' % s)
        self.assertNotError('outfilter rot13')
        self.assertResponse('rot13 foobar', 'sbbone')
        self.assertNotError('outfilter')
        self.assertResponse('rot13 foobar', 'sbbone')
        self.assertNotError('outfilter ROT13')
        self.assertResponse('rot13 foobar', '%s: foobar' % s)
        self.assertNotError('outfilter')
        self.assertResponse('rot13 foobar', 'sbbone')

    def testOutfilterAction(self):
        s = self.nick.encode('rot13')
        self.assertNotError('outfilter rot13')
        self.assertResponse('rot13 foobar', '%s: foobar' % s)
        m = self.getMsg('action foobar')
        self.failUnless(ircmsgs.isAction(m))
        s = ircmsgs.unAction(m)
        self.assertEqual(s, 'sbbone')
        
        

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
