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

import re

import utils

class FunCommandsTest(PluginTestCase):
    plugins = ('FunCommands',)
    def testNoErrors(self):
        self.assertNotError('netstats')
        self.assertNotError('cpustats')
        self.assertNotError('uptime')
        self.assertNotError('leet foobar')
        self.assertNotError('lithp meghan sweeney')
        self.assertNotError('objects')
        self.assertNotError('levenshtein Python Perl')
        self.assertNotError('soundex jemfinch')

    def testBinary(self):
        self.assertResponse('binary A', '01000001')

    def testRot13(self):
        for s in nicks[:10]: # 10 is probably enough.
            self.assertResponse('rot13 [rot13 %s]' % s, s)

    def testCalc(self):
        self.assertResponse('calc 5*0.06', str(5*0.06))

    def testChr(self):
        for i in range(256):
            c = chr(i)
            regexp = r'%s|%s' % (re.escape(c), re.escape(repr(c)))
            self.assertRegexp('chr %s' % i, regexp)

    def testHexlifyUnhexlify(self):
        for s in nicks[:10]: # 10, again, is probably enough.
            self.assertResponse('unhexlify [hexlify %s]' % s, s)

    def testXor(self):
        for s0, s1, s2, s3, s4, s5, s6, s7, s8, s9 in group(nicks, 10):
            data = '%s%s%s%s%s%s%s%s%s' % (s0, s1, s2, s3, s4, s5, s6, s7, s8)
            self.assertResponse('xor %s [xor %s %s]' % (s9, s9, data), data)

    def testUrlquoteUrlunquote(self):
        self.assertResponse('urlunquote [urlquote ~jfincher]', '~jfincher')

    def testPydoc(self):
        self.assertNotError('pydoc str')
        self.assertError('pydoc foobar')
        self.assertError('pydoc assert')

    def testOrd(self):
        for c in map(chr, range(256)):
            i = ord(c)
            self.assertResponse('ord %s' % utils.dqrepr(c), str(i))

    def testTell(self):
        m = self.getMsg('tell foo [rot13 foobar]')
        self.failUnless(m.args[0] == 'foo')
        self.failUnless('sbbone' in m.args[1])
        m = self.getMsg('tell #foo [rot13 foobar]')
        self.failUnless(m.args[0] == '#foo')
        self.failUnless('sbbone' in m.args[1])

    def testZen(self):
        self.assertNotError('zen')
        
    def testDns(self):
        self.assertNotError('dns slashdot.org')

    def testWhois(self):
        self.assertNotError('whois ohio-state.edu')
        self.assertError('whois slashdot.org')

    def testDict(self):
        self.assertNotError('dict slash')
        self.assertNotRegexp('dict web1913 slash', 'foldoc')

    def testDictionaries(self):
        self.assertNotError('dictionaries')

    

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
