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

import utils

if network:
    class GameknotTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('Gameknot',)
        def testGkstats(self):
            self.assertNotRegexp('gkstats jemfinch', 'Old GK rating')
            self.assertError('gkstats %s' % utils.mktemp())
            self.assertNotError('gkstats Strike')

        def testUrlSnarfer(self):
            conf.supybot.plugins.Gameknot.gameSnarfer.setValue(True)
            self.assertNotError('http://gameknot.com/chess.pl?bd=1019508')
            self.assertNotError('here\'s a link: '
                                'http://gameknot.com/chess.pl?bd=1077350&r=394 '
                                'and here\'s another one: '
                                'http://gameknot.com/chess.pl?bd=1116828&r=250')
            self.assertNotError(' ') # The next snarfed response.
            self.assertNotRegexp('http://gameknot.com/chess.pl?bd=1019508',
                                 self.nick)

        def testStatsUrlSnarfer(self):
            conf.supybot.plugins.Gameknot.statSnarfer.setValue(True)
            self.assertNotError('http://gameknot.com/stats.pl?ironchefchess')
            self.assertRegexp('http://gameknot.com/stats.pl?ddipaolo&1',
                              r'^[^&]+$')

        def testConfig(self):
            conf.supybot.plugins.Gameknot.gameSnarfer.setValue(False)
            conf.supybot.plugins.Gameknot.statSnarfer.setValue(False)
            self.assertNoResponse('http://gameknot.com/stats.pl?ironchefchess')
            self.assertNoResponse('http://gameknot.com/chess.pl?bd=907498')
            conf.supybot.plugins.Gameknot.gameSnarfer.setValue(True)
            conf.supybot.plugins.Gameknot.statSnarfer.setValue(True)
            self.assertNotError('http://gameknot.com/stats.pl?ironchefchess')
            self.assertNotError('http://gameknot.com/chess.pl?bd=907498')
        

        def testSnarfer(self):
            conf.supybot.plugins.Gameknot.gameSnarfer.setValue(True)
            # This game expired.
##             self.assertRegexp('http://gameknot.com/chess.pl?bd=907498',
##                               '\x02ddipaolo\x0f won')
            # As did this :(
##             self.assertRegexp('http://gameknot.com/chess.pl?bd=907498',
##                               '\x02chroniqueur\x0f resigned')
            self.assertRegexp('http://gameknot.com/chess.pl?bd=955432',
                              '\x02ddipaolo\x0f lost')
            self.assertRegexp('http://gameknot.com/chess.pl?bd=1077345&r=365',
                              'draw')



# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

