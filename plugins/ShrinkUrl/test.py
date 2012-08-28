###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009-2010, James Vega
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

class ShrinkUrlTestCase(ChannelPluginTestCase):
    plugins = ('ShrinkUrl',)
    config = {'supybot.snarfThrottle': 0}

    sfUrl ='http://sourceforge.net/tracker/?func=add&group_id=58965&atid=48947'
    udUrl = 'http://www.urbandictionary.com/define.php?' \
            'term=all+your+base+are+belong+to+us'
    tests = {'tiny': [(sfUrl, r'http://tinyurl.com/yg8r28z'),
                      (udUrl, r'http://tinyurl.com/u479')],
             'ln': [(sfUrl, r'http://ln-s.net/4LVF'),
                    (udUrl, r'http://ln-s.net/2\$K')],
             'xrl': [(sfUrl, r'http://xrl.us/bfq8ik'),
                     (udUrl, r'http://xrl.us/bfnyji')],
             'goo': [(sfUrl, r'http://goo.gl/3c59N'),
                     (udUrl, r'http://goo.gl/ocTga')],
             'ur1': [(sfUrl, r'http://ur1.ca/9xl25'),
                     (udUrl, r'http://ur1.ca/9xl9k')],
             'x0': [(sfUrl, r'http://x0.no/0l2j'),
                    (udUrl, r'http://x0.no/0l2k')]
            }
    if network:
        def testShrink(self):
            for (service, testdata) in self.tests.iteritems():
                for (url, shrunkurl) in testdata:
                    self.assertRegexp('shrinkurl %s %s' % (service, url),
                                      shrunkurl)

        def testShrinkCycle(self):
            cycle = conf.supybot.plugins.ShrinkUrl.serviceRotation
            snarfer = conf.supybot.plugins.ShrinkUrl.shrinkSnarfer
            origcycle = cycle()
            origsnarfer = snarfer()
            try:
                self.assertNotError(
                    'config plugins.ShrinkUrl.serviceRotation ln x0')
                self.assertError(
                    'config plugins.ShrinkUrl.serviceRotation ln x1')
                snarfer.setValue(True)
                self.assertSnarfRegexp(self.udUrl, r'%s.* \(at' %
                                       self.tests['ln'][1][1])
                self.assertSnarfRegexp(self.udUrl, r'%s.* \(at' %
                                       self.tests['x0'][1][1])
                self.assertSnarfRegexp(self.udUrl, r'%s.* \(at' %
                                       self.tests['ln'][1][1])
            finally:
                cycle.setValue(origcycle)
                snarfer.setValue(origsnarfer)

        def _snarf(self, service):
            shrink = conf.supybot.plugins.ShrinkUrl
            origService = shrink.default()
            origSnarf = shrink.shrinkSnarfer()
            shrink.default.setValue(service)
            shrink.shrinkSnarfer.setValue(True)
            try:
                for (url, shrunkurl) in self.tests[service]:
                    teststr = r'%s.* \(at' % shrunkurl
                    self.assertSnarfRegexp(url, teststr)
            finally:
                shrink.default.setValue(origService)
                shrink.shrinkSnarfer.setValue(origSnarf)

        def testTinysnarf(self):
            self._snarf('tiny')

        def testLnsnarf(self):
            self._snarf('ln')

        def testXrlsnarf(self):
            self._snarf('xrl')

        def testGoosnarf(self):
            self._snarf('goo')

        def testUr1snarf(self):
            self._snarf('ur1')

        def testX0snarf(self):
            self._snarf('x0')

        def testNonSnarfing(self):
            shrink = conf.supybot.plugins.ShrinkUrl
            origService = shrink.default()
            origSnarf = shrink.shrinkSnarfer()
            origLen = shrink.minimumLength()
            origRegexp = shrink.nonSnarfingRegexp()
            shrink.default.setValue('tiny')
            shrink.shrinkSnarfer.setValue(True)
            shrink.minimumLength.setValue(10)
            shrink.nonSnarfingRegexp.set('m/sf/')
            try:
                self.assertSnarfNoResponse('http://sf.net/', 5)
                self.assertSnarfRegexp('http://sourceforge.net/',
                                       r'http://tinyurl.com/7vm7.*\(at ')
            finally:
                shrink.default.setValue(origService)
                shrink.shrinkSnarfer.setValue(origSnarf)
                shrink.minimumLength.setValue(origLen)
                shrink.nonSnarfingRegexp.setValue(origRegexp)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
