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

class UtilitiesTestCase(PluginTestCase):
    plugins = ('Utilities', 'Status')
    def testIgnore(self):
        self.assertNoResponse('utilities ignore foo bar baz', 1)
        self.assertError('utilities ignore [re m/foo bar]')

    def testSuccess(self):
        self.assertNotError('success 1')
        self.assertError('success [re m/foo bar]')

    def testLast(self):
        self.assertResponse('utilities last foo bar baz', 'baz')

    def testStrlen(self):
        self.assertResponse('strlen %s' % ('s'*10), '10')
        self.assertResponse('strlen a b', '3')

    def testEcho(self):
        self.assertHelp('echo')
        self.assertResponse('echo foo', 'foo')
        m = self.getMsg('status cpu')
        self.assertResponse('echo "%s"' % m.args[1], m.args[1])

    def testEchoStandardSubstitute(self):
        self.assertNotRegexp('echo $nick', r'\$')

    def testRe(self):
        self.assertResponse('re "m/system time/" [status cpu]', 'system time')
        self.assertResponse('re s/user/luser/g user user', 'luser luser')
        self.assertResponse('re s/user/luser/ user user', 'luser user')
        self.assertNotRegexp('re m/foo/ bar', 'has no attribute')
        self.assertResponse('re m/a\S+y/ "the bot angryman is hairy"','angry')

    def testReNotEmptyString(self):
        self.assertError('re s//foo/g blah')

    def testReWorksWithJustCaret(self):
        self.assertResponse('re s/^/foo/ bar', 'foobar')

    def testReNoEscapingUnpackListOfWrongSize(self):
        self.assertNotRegexp('re foo bar baz', 'unpack list of wrong size')

    def testReBug850931(self):
        self.assertResponse('re s/\b(\w+)\b/\1./g foo bar baz',
                            'foo. bar. baz.')

    def testNotOverlongRe(self):
        self.assertError('re [strjoin "" s/./ [eval \'xxx\'*400]] blah blah')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
