###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2009, James Vega
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

class GoogleTestCase(ChannelPluginTestCase):
    plugins = ('Google', 'Config')
    if network:
        def testCalcHandlesMultiplicationSymbol(self):
            self.assertNotRegexp('google calc seconds in a century', r'215')

        def testCalc(self):
            self.assertNotRegexp('google calc e^(i*pi)+1', r'didn\'t')
            self.assertNotRegexp('google calc 1 usd in gbp', r'didn\'t')

        def testHtmlHandled(self):
            self.assertNotRegexp('google calc '
                                 'the speed of light '
                                 'in microns / fortnight', '<sup>')
            self.assertNotRegexp('google calc '
                                 'the speed of light '
                                 'in microns / fortnight', '&times;')

        def testSearch(self):
            self.assertNotError('google foo')
            self.assertRegexp('google dupa', r'dupa')
            # Unicode check
            self.assertNotError('google ae')

        def testUrlDecode(self):
            self.assertRegexp(
                    'google site:http://www.urbandictionary.com carajo land',
                    '\x02carajo land - Urban Dictionary\x02: '
                    r'https?://www.urbandictionary.com/define.php\?term=carajo%20land')

        def testLucky(self):
            self.assertResponse('lucky Hacker News',
                    'https://news.ycombinator.com/')

        def testSearchFormat(self):
            self.assertRegexp('google foo', '<https?://.*>')
            self.assertNotError('config reply.format.url %s')
            self.assertRegexp('google foo', 'https?://.*')
            self.assertNotRegexp('google foo', '<https?://.*>')

        def testSearchOneToOne(self):
            self.assertRegexp('google dupa', ';')
            self.assertNotError('config plugins.Google.oneToOne True')
            self.assertNotRegexp('google dupa', ';')

        def testFight(self):
            self.assertRegexp('fight supybot moobot', r'.*supybot.*: \d+')
            self.assertNotError('fight ... !')

        def testTranslate(self):
            self.assertRegexp('translate en es hello world', 'Hola mundo')

        def testCalcDoesNotHaveExtraSpaces(self):
            self.assertNotRegexp('google calc 1000^2', r'\s+,\s+')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
