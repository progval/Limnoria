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

class HttpTest(PluginTestCase, PluginDocumentation):
    plugins = ('Http',)
    def testStockquote(self):
        self.assertNotError('stockquote MSFT')

    def testFreshmeat(self):
        self.assertNotError('freshmeat supybot')
        self.assertNotRegexp('freshmeat supybot', 'DOM Element')

    def testTitle(self):
        self.assertResponse('title slashdot.org',
                            'Slashdot: News for nerds, stuff that matters')
        self.assertResponse('title http://www.slashdot.org/',
                            'Slashdot: News for nerds, stuff that matters')
        self.assertNotRegexp('title '
                             'http://www.amazon.com/exec/obidos/tg/detail/-/'
                             '1884822312/qid=1063140754/sr=8-1/ref=sr_8_1/'
                             '002-9802970-2308826?v=glance&s=books&n=507846',
                             'no HTML title')
        # Checks the non-greediness of the regexp
        self.assertResponse('title '
                            'http://www.space.com/scienceastronomy/'
                            'jupiter_dark_spot_031023.html',
                            'Mystery Spot on Jupiter Baffles Astronomers')
        # Checks for @title not-working correctly
        self.assertResponse('title '\
            'http://www.catb.org/~esr/jargon/html/F/foo.html',
            'foo')

    def testGeekquote(self):
        self.assertNotError('geekquote')
        self.assertNotError('geekquote --id=4848')
        self.assertError('geekquote --id=48a')

    def testAcronym(self):
        self.assertRegexp('acronym ASAP', 'as soon as possible')
        self.assertNotRegexp('acronym asap', 'Definition')
        self.assertNotRegexp('acronym UNIX', 'not an acronym')

    def testNetcraft(self):
        self.assertNotError('netcraft slashdot.org')

    def testWeather(self):
        self.assertNotError('weather Columbus, OH')
        self.assertNotError('weather 43221')
        self.assertNotRegexp('weather Paris, FR', 'Virginia')
        self.assertError('weather alsdkfjasdl, asdlfkjsadlfkj')
        self.assertNotError('weather London, uk')
        self.assertNotError('weather London, UK')
        self.assertNotError('weather Munich, de')
        self.assertNotError('weather Tucson, AZ')
	self.assertError('weather hell')

    def testKernel(self):
        self.assertNotError('kernel')

    def testPgpkey(self):
        self.assertNotError('pgpkey jeremiah fincher')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

