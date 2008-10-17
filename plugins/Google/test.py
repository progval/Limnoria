###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008, James Vega
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
    plugins = ('Google',)
    if network:
        def testCalcHandlesMultiplicationSymbol(self):
            self.assertNotRegexp('google calc seconds in a century', r'215')

        def testCalc(self):
            self.assertNotRegexp('google calc e^(i*pi)+1', r'didn\'t')

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

        def testFight(self):
            self.assertRegexp('fight supybot moobot', r'.*supybot.*: \d+')

        def testTranslate(self):
            self.assertRegexp('translate en es hello world', 'mundo')

        def testCalcDoesNotHaveExtraSpaces(self):
            self.assertNotRegexp('google calc 1000^2', r'\s+,\s+')

        def testGroupsSnarfer(self):
            orig = conf.supybot.plugins.Google.groupsSnarfer()
            try:
                conf.supybot.plugins.Google.groupsSnarfer.setValue(True)
                # This should work, and does work in practice, but is failing
                # in the tests.
                #self.assertSnarfRegexp(
                #    'http://groups.google.com/groups?dq=&hl=en&lr=lang_en&'
                #    'ie=UTF-8&oe=UTF-8&selm=698f09f8.0310132012.738e22fc'
                #    '%40posting.google.com',
                #    r'comp\.lang\.python.*question: usage of __slots__')
                self.assertSnarfRegexp(
                    'http://groups.google.com/groups?selm=ExDm.8bj.23'
                    '%40gated-at.bofh.it&oe=UTF-8&output=gplain',
                    r'linux\.kernel.*NFS client freezes')
                self.assertSnarfRegexp(
                    'http://groups.google.com/groups?q=kernel+hot-pants&'
                    'hl=en&lr=&ie=UTF-8&oe=UTF-8&selm=1.5.4.32.199703131'
                    '70853.00674d60%40adan.kingston.net&rnum=1',
                    r'Madrid Bluegrass Ramble')
                self.assertSnarfRegexp(
                    'http://groups.google.com/groups?selm=1.5.4.32.19970'
                    '313170853.00674d60%40adan.kingston.net&oe=UTF-8&'
                    'output=gplain',
                    r'Madrid Bluegrass Ramble')
                self.assertSnarfRegexp(
                    'http://groups.google.com/groups?dq=&hl=en&lr=&'
                    'ie=UTF-8&threadm=mailman.1010.1069645289.702.'
                    'python-list%40python.org&prev=/groups%3Fhl%3Den'
                    '%26lr%3D%26ie%3DUTF-8%26group%3Dcomp.lang.python',
                    r'comp\.lang\.python.*What exactly are bound')
                # Test for Bug #1002547
                self.assertSnarfRegexp(
                    'http://groups.google.com/groups?q=supybot+is+the&'
                    'hl=en&lr=&ie=UTF-8&c2coff=1&selm=1028329672'
                    '%40freshmeat.net&rnum=9',
                    r'fm\.announce.*SupyBot')
            finally:
                conf.supybot.plugins.Google.groupsSnarfer.setValue(orig)

        def testConfig(self):
            orig = conf.supybot.plugins.Google.groupsSnarfer()
            try:
                conf.supybot.plugins.Google.groupsSnarfer.setValue(False)
                self.assertSnarfNoResponse(
                        'http://groups.google.com/groups?dq=&hl=en&lr=lang_en&'
                        'ie=UTF-8&oe=UTF-8&selm=698f09f8.0310132012.738e22fc'
                        '%40posting.google.com')
                conf.supybot.plugins.Google.groupsSnarfer.setValue(True)
                self.assertSnarfNotError(
                        'http://groups.google.com/groups?dq=&hl=en&lr=lang_en&'
                        'ie=UTF-8&oe=UTF-8&selm=698f09f8.0310132012.738e22fc'
                        '%40posting.google.com')
            finally:
                conf.supybot.plugins.Google.groupsSnarfer.setValue(orig)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
