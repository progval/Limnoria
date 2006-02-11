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
                self.assertRegexp('spell Strike', 'correctly')
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


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
