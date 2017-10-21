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


from supybot.utils.minisix import u
from supybot.test import *

class UtilitiesTestCase(PluginTestCase):
    plugins = ('Math', 'Utilities', 'String')
    def testIgnore(self):
        self.assertNoResponse('utilities ignore foo bar baz', 1)
        self.assertError('utilities ignore [re m/foo bar]')
        self.assertResponse('echo [utilities ignore foobar] qux', 'qux')

    def testSuccess(self):
        self.assertNotError('success 1')
        self.assertError('success [re m/foo bar]')

    def testLast(self):
        self.assertResponse('utilities last foo bar baz', 'baz')

    def testEcho(self):
        self.assertHelp('echo')
        self.assertResponse('echo foo', 'foo')
        self.assertResponse(u('echo 好'), '好')
        self.assertResponse(u('echo "好"'), '好')

    def testEchoDollarOneRepliesDollarOne(self):
        self.assertResponse('echo $1', '$1')

    def testEchoStandardSubstitute(self):
        self.assertNotRegexp('echo $nick', r'\$')

    def testEchoStripCtcp(self):
        self.assertResponse('echo \x01ACTION foo\x01', "ACTION foo")

    def testApply(self):
        self.assertResponse('apply "utilities last" a', 'a')
        self.assertResponse('apply "utilities last" a b', 'b')

    def testShuffle(self):
        self.assertResponse('shuffle a', 'a')

    def testSort(self):
        self.assertResponse('sort abc cab cba bca', 'abc bca cab cba')
        self.assertResponse('sort 2 12 42 7 2', '2 2 7 12 42')
        self.assertResponse('sort 2 8 12.2 12.11 42 7 2', '2 2 7 8 12.11 12.2 42')

    def testSample(self):
        self.assertResponse('sample 1 a', 'a')
        self.assertError('sample moo')
        self.assertError('sample 5 moo')
        self.assertRegexp('sample 2 a b c', '^[a-c] [a-c]$')

    def testCountargs(self):
        self.assertResponse('countargs a b c', '3')
        self.assertResponse('countargs a "b c"', '2')
        self.assertResponse('countargs', '0')

    def testLet(self):
        self.assertResponse('let x = 42 in echo foo $x bar', 'foo 42 bar')
        self.assertResponse(
                'let y = 21 in "'
                    'let x = [math calc 2*[echo $y]] in '
                        'echo foo $x bar"',
                'foo 42 bar')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
