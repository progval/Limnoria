###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import os

from supybot.test import *

if os.name == 'posix':
    class UnixTestCase(PluginTestCase):
        plugins = ('Unix',)
        if utils.findBinaryInPath('aspell') is not None or \
           utils.findBinaryInPath('ispell') is not None:
            def testSpell(self):
                self.assertRegexp('spell Strike',
                                  '(correctly|Possible spellings)')
                # ispell won't find any results.  aspell will make some
                # suggestions.
                self.assertRegexp('spell z0opadfnaf83nflafl230kasdf023hflasdf',
                                  'not find|Possible spellings')
                self.assertNotError('spell Strizzike')
                self.assertError('spell foo bar baz')
                self.assertError('spell -')
                self.assertError('spell .')
                self.assertError('spell ?')
                self.assertNotError('spell whereever')
                self.assertNotRegexp('spell foo', 'whatever')

        def testErrno(self):
            self.assertRegexp('errno 12', '^ENOMEM')
            self.assertRegexp('errno ENOMEM', '#12')

        def testProgstats(self):
            self.assertNotError('progstats')

        def testCrypt(self):
            self.assertNotError('crypt jemfinch')

        if utils.findBinaryInPath('fortune') is not None:
            def testFortune(self):
                self.assertNotError('fortune')

        if utils.findBinaryInPath('ping') is not None:
            def testPing(self):
                self.assertNotError('unix ping 127.0.0.1')
                self.assertError('unix ping')
                self.assertError('unix ping -localhost')
                self.assertError('unix ping local%host')
            def testPingCount(self):
                self.assertNotError('unix ping --c 1 127.0.0.1')
                self.assertError('unix ping --c a 127.0.0.1')
                self.assertRegexp('unix ping --c 11 127.0.0.1','10 packets')
                self.assertRegexp('unix ping 127.0.0.1','5 packets')
            def testPingInterval(self):
                self.assertNotError('unix ping --i 1 --c 1 127.0.0.1')
                self.assertError('unix ping --i a --c 1 127.0.0.1')
                # Super-user privileged interval setting
                self.assertError('unix ping --i 0.1 --c 1 127.0.0.1') 
            def testPingTtl(self):
                self.assertNotError('unix ping --t 64 --c 1 127.0.0.1')
                self.assertError('unix ping --t a --c 1 127.0.0.1')
            def testPingWait(self):
                self.assertNotError('unix ping --W 1 --c 1 127.0.0.1')
                self.assertError('unix ping --W a --c 1 127.0.0.1')

        def testCall(self):
            self.assertNotError('unix call /bin/ping -c 1 localhost')
            self.assertRegexp('unix call /bin/ping -c 1 localhost', 'ping statistics')
            self.assertError('unix call /usr/bin/nosuchcommandaoeuaoeu')
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
