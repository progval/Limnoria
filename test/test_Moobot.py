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

import base64

class MoobotTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('Moobot',)
    def testCool(self):
        for nick in nicks[:10]:
            self.assertResponse('cool %s' % nick, ':cool: %s :cool:' % nick)

    def testMime(self):
        for nick in nicks[:10]:
            self.assertResponse('unmime [mime %s]' % nick, nick)

    def testStack(self):
        self.assertError('stack pop')
        self.assertError('stack xray 1')
        self.assertNotError('stack push foo')
        self.assertNotError('stack push bar')
        self.assertNotError('stack push baz')
        self.assertResponse('stack pop', 'baz')
        self.assertResponse('stack pop', 'bar')
        self.assertResponse('stack pop', 'foo')

    def testGive(self):
        m = self.getMsg('give foo a bicycle')
        self.failUnless(ircmsgs.isAction(m))
        self.failUnless('bicycle' in m.args[1])
        self.assertRegexp('give yourself a beer', 'himself')
        self.assertRegexp('give me a beef', self.nick)


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

