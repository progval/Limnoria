#!/usr/bin/env python

###
# Copyright (c) 2004, Kevin Murphy
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

class GeekQuoteTestCase(ChannelPluginTestCase, PluginDocumentation):
    plugins = ('Geekquote',)
    def setUp(self):
        ChannelPluginTestCase.setUp(self)
        conf.supybot.plugins.Geekquote.geekSnarfer.setValue(False)

    def testGeekquote(self):
        self.assertNotError('geekquote')
        self.assertNotError('geekquote 4848')
        # It's not an error, it just truncates at the first non-number
        #self.assertError('geekquote 48a8')
        self.assertError('geekquote asdf')

    def testQdb(self):
        self.assertNotError('qdb')
        self.assertNotError('qdb 13600')
        self.assertError('qdb qwerty')

    if network:

        def testSnarfer(self):
            try:
                orig = conf.supybot.plugins.Geekquote.geekSnarfer()
                conf.supybot.plugins.Geekquote.geekSnarfer.setValue(True)
                self.assertRegexp('http://www.bash.org/?1033',
                                  r'\<Guilty\>')
                self.assertRegexp('http://bash.org/?2820',
                                  r'\[Duckarse\]')
                self.assertRegexp('http://www.qdb.us/?33080',
                                  r'\<@Noggie\>')
                self.assertRegexp('http://qdb.us/?22280',
                                  r'\<MegamanX2K\>')
            finally:
                conf.supybot.plugins.Geekquote.geekSnarfer.setValue(orig)
            self.assertNoResponse('http://www.bash.org/?4848')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

