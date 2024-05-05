###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import os
import socket

try:
    import crypt
except ImportError:
    crypt = None

from supybot.test import *

try:
    from unittest import skip, skipIf
except ImportError:
    def skipUnlessSpell(f):
        return None
    def skipUnlessFortune(f):
        return None
    def skipUnlessPing(f):
        return None
    def skipUnlessPing6(f):
        return None
else:
    skipUnlessSpell = skipIf(utils.findBinaryInPath('aspell') is None and \
            utils.findBinaryInPath('ispell') is None,
            'aspell/ispell not available.')
    skipUnlessFortune = skipIf(utils.findBinaryInPath('fortune') is None,
            'fortune not available.')

    if network:
        skipUnlessPing = skipIf(
                utils.findBinaryInPath('ping') is None or not setuid,
                'ping not available.')
        if socket.has_ipv6:
            skipUnlessPing6 = skipIf(
                    utils.findBinaryInPath('ping6') is None or not setuid,
                    'ping6 not available.')
        else:
            skipUnlessPing6 = skip(
                    'IPv6 not available.')
    else:
        skipUnlessPing = skip(
                'network not available.')
        skipUnlessPing6 = skip(
                'network not available.')

class UnixConfigTestCase(ChannelPluginTestCase):
    plugins = ('Unix',)
    def testFortuneFiles(self):
        self.assertNotError('config channel plugins.Unix.fortune.files '
                'foo bar')
        self.assertRegexp('config channel plugins.Unix.fortune.files '
                '"-foo bar"',
                'Error:.*dash.*not u?\'-foo\'') # The u is for Python 2
        self.assertNotError('config channel plugins.Unix.fortune.files ""')


if os.name == 'posix':
    class UnixTestCase(PluginTestCase):
        plugins = ('Unix',)

        @skipUnlessSpell
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

        if crypt is not None:  # Python < 3.13
            def testCrypt(self):
                self.assertNotError('crypt jemfinch')

        @skipUnlessFortune
        def testFortune(self):
            self.assertNotError('fortune')

        @skipUnlessPing
        def testPing(self):
            self.assertNotError('unix ping 127.0.0.1')
            self.assertError('unix ping')
            self.assertError('unix ping -localhost')
            self.assertError('unix ping local%host')
        @skipUnlessPing
        def testPingCount(self):
            self.assertNotError('unix ping --c 1 127.0.0.1')
            self.assertError('unix ping --c a 127.0.0.1')
            self.assertRegexp('unix ping --c 11 127.0.0.1','10 packets')
            self.assertRegexp('unix ping 127.0.0.1','5 packets')
        @skipUnlessPing
        def testPingInterval(self):
            self.assertNotError('unix ping --i 1 --c 1 127.0.0.1')
            self.assertError('unix ping --i a --c 1 127.0.0.1')
            # Super-user privileged interval setting
            self.assertError('unix ping --i 0.1 --c 1 127.0.0.1')
        @skipUnlessPing
        def testPingTtl(self):
            self.assertNotError('unix ping --t 64 --c 1 127.0.0.1')
            self.assertError('unix ping --t a --c 1 127.0.0.1')
        @skipUnlessPing
        def testPingWait(self):
            self.assertNotError('unix ping --W 1 --c 1 127.0.0.1')
            self.assertError('unix ping --W a --c 1 127.0.0.1')

        @skipUnlessPing6
        def testPing6(self):
            self.assertNotError('unix ping6 ::1')
            self.assertError('unix ping6')
            self.assertError('unix ping6 -localhost')
            self.assertError('unix ping6 local%host')
        @skipUnlessPing6
        def testPing6Count(self):
            self.assertNotError('unix ping6 --c 1 ::1')
            self.assertError('unix ping6 --c a ::1')
            self.assertRegexp('unix ping6 --c 11 ::1','10 packets',
                    timeout=12)
            self.assertRegexp('unix ping6 ::1','5 packets')
        @skipUnlessPing6
        def testPing6Interval(self):
            self.assertNotError('unix ping6 --i 1 --c 1 ::1')
            self.assertError('unix ping6 --i a --c 1 ::1')
            # Super-user privileged interval setting
            self.assertError('unix ping6 --i 0.1 --c 1 ::1')
        @skipUnlessPing6
        def testPing6Ttl(self):
            self.assertNotError('unix ping6 --t 64 --c 1 ::1')
            self.assertError('unix ping6 --t a --c 1 ::1')
        @skipUnlessPing6
        def testPing6Wait(self):
            self.assertNotError('unix ping6 --W 1 --c 1 ::1')
            self.assertError('unix ping6 --W a --c 1 ::1')

        def testCall(self):
            self.assertNotError('unix call /bin/ls /')
            self.assertRegexp('unix call /bin/ls /', 'boot, .*dev, ')
            self.assertError('unix call /usr/bin/nosuchcommandaoeuaoeu')

        def testShellForbidden(self):
            self.assertNotError('unix call /bin/ls /')
            with conf.supybot.commands.allowShell.context(False):
                self.assertRegexp('unix call /bin/ls /',
                        'Error:.*not available.*supybot.commands.allowShell')

        def testUptime(self):
            self.assertNotError('unix sysuptime')

        def testUname(self):
            self.assertNotError('unix sysuname')
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
