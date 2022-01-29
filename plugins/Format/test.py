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

class FormatTestCase(PluginTestCase):
    plugins = ('Format',)
    def testBold(self):
        self.assertResponse('bold foobar', '\x02foobar\x02')

    def testUnderline(self):
        self.assertResponse('underline foobar', '\x1ffoobar\x1f')

    def testReverse(self):
        self.assertResponse('reverse foobar', '\x16foobar\x16')


    def testFormat(self):
        self.assertResponse('format %s foo', 'foo')
        self.assertResponse('format %s%s foo bar', 'foobar')
        self.assertResponse('format "%sbaz%s" "foo bar" 1', 'foo barbaz1')
        self.assertError('format %s foo bar')
        self.assertError('format %s%s foo')
        
    def testJoin(self):
        self.assertResponse('join + foo bar baz', 'foo+bar+baz')
        self.assertResponse('join "" foo bar baz', 'foobarbaz')

    def testTranslate(self):
        self.assertResponse('translate 123 456 1234567890', '4564567890')
        self.assertError('translate 123 1234 123125151')

    def testReplace(self):
        self.assertResponse('replace # %23 bla#foo', 'bla%23foo')
        self.assertResponse('replace "/" "" t/e/s/t', 'test')
        self.assertResponse('replace "" :) hello', ':)h:)e:)l:)l:)o:)')
        self.assertResponse('replace de "d e" a b c de f ', 'a b c d e f')

    def testUpper(self):
        self.assertResponse('upper foo', 'FOO')
        self.assertResponse('upper FOO', 'FOO')

    def testLower(self):
        self.assertResponse('lower foo', 'foo')
        self.assertResponse('lower FOO', 'foo')

    def testCapitalize(self):
        self.assertResponse('capitalize foo', 'Foo')
        self.assertResponse('capitalize foo bar', 'Foo bar')

    def testTitle(self):
        self.assertResponse('title foo', 'Foo')
        self.assertResponse('title foo bar', 'Foo Bar')
        self.assertResponse('title foo\'s bar', 'Foo\'s Bar')

    def testRepr(self):
        self.assertResponse('repr foo bar baz', '"foo bar baz"')

    def testConcat(self):
        self.assertResponse('concat foo bar baz', 'foobar baz')

    def testCut(self):
        self.assertResponse('cut 5 abcdefgh', 'abcde')
        self.assertResponse('cut 5 abcd', 'abcd')
        self.assertResponse('cut -1 abcde', 'abcd')

    def testField(self):
        self.assertResponse('field 2 foo bar baz', 'bar')
        self.assertResponse('field -1 foo bar baz', 'baz')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
