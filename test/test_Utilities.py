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

class UtilitiesTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('Utilities', 'Status')
    def testIgnore(self):
        self.assertNoResponse('ignore foo bar baz', 1)

    def testStrjoin(self):
        self.assertResponse('strjoin + foo bar baz', 'foo+bar+baz')

    def testStrtranslate(self):
        self.assertResponse('strtranslate 123 456 1234567890', '4564567890')

    def testStrupper(self):
        self.assertResponse('strupper foo', 'FOO')
        self.assertResponse('strupper FOO', 'FOO')

    def testStrlower(self):
        self.assertResponse('strlower foo', 'foo')
        self.assertResponse('strlower FOO', 'foo')

    def testStrlen(self):
        self.assertResponse('strlen %s' % ('s'*10), '10')
        self.assertResponse('strlen a b', '3')

    def testRepr(self):
        self.assertResponse('repr foo bar baz', '"foo bar baz"')

    def testStrconcat(self):
        self.assertResponse('strconcat foo bar baz', 'foobar baz')

    def testEcho(self):
        self.assertResponse('echo foo', 'foo')
        m = self.getMsg('cpustats')
        self.assertResponse('echo "%s"' % m.args[1], m.args[1])

    def testRe(self):
        self.assertResponse('re "m/My children/" [cpustats]', 'My children')
        self.assertResponse('re s/user/luser/g user user', 'luser luser')
        self.assertResponse('re s/user/luser/ user user', 'luser user')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

