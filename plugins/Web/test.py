###
# Copyright (c) 2005, Jeremiah Fincher
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

class WebTestCase(ChannelPluginTestCase):
    plugins = ('Web',)
    timeout = 10
    if network:
        def testHeaders(self):
            self.assertError('headers ftp://ftp.cdrom.com/pub/linux')
            self.assertNotError('headers http://www.slashdot.org/')

        def testDoctype(self):
            self.assertError('doctype ftp://ftp.cdrom.com/pub/linux')
            self.assertNotError('doctype http://www.slashdot.org/')
            m = self.getMsg('doctype http://moobot.sf.net/')
            self.failUnless(m.args[1].endswith('>'))

        def testSize(self):
            self.assertError('size ftp://ftp.cdrom.com/pub/linux')
            self.assertNotError('size http://supybot.sf.net/')
            self.assertNotError('size http://www.slashdot.org/')

        def testTitle(self):
            self.assertResponse('title http://www.slashdot.org/',
                                'Slashdot - News for nerds, stuff that matters')
            # Amazon add a bunch of scripting stuff to the top of their page,
            # so we need to allow for a larger peekSize
# Actually, screw Amazon. Even bumping this up to 10k doesn't give us enough
# info.
#            try:
#                orig = conf.supybot.protocols.http.peekSize()
#                conf.supybot.protocols.http.peekSize.setValue(8192)
#                self.assertNotRegexp('title '
#                             'http://www.amazon.com/exec/obidos/tg/detail/-/'
#                             '1884822312/qid=1063140754/sr=8-1/ref=sr_8_1/'
#                             '002-9802970-2308826?v=glance&s=books&n=507846',
#                             'no HTML title')
#            finally:
#                conf.supybot.protocols.http.peekSize.setValue(orig)
            # Checks the non-greediness of the regexp
            self.assertResponse('title '
                                'http://www.space.com/scienceastronomy/'
                                'jupiter_dark_spot_031023.html',
                                'SPACE.com -- Mystery Spot on Jupiter Baffles '
                                'Astronomers')
            # Checks for @title not-working correctly
            self.assertResponse('title '
                'http://www.catb.org/~esr/jargon/html/F/foo.html',
                'foo')
            # Checks for only grabbing the real title tags instead of title
            # tags inside, for example, script tags. Bug #1190350
            self.assertNotRegexp('title '
                'http://www.irinnews.org/report.asp?ReportID=45910&'
                'SelectRegion=West_Africa&SelectCountry=CHAD',
                r'document\.write\(')
            # Checks that title parser grabs the full title instead of just
            # part of it.
            self.assertRegexp('title http://www.n-e-r-d.com/', 'N.*E.*R.*D')
            # Checks that the parser doesn't hang on invalid tags
            print
            print "If we have not fixed a bug with the parser, the following",
            print "test will hang the test-suite."
            self.assertNotError(
                        'title http://www.youtube.com/watch?v=x4BtiqPN4u8')

        def testNetcraft(self):
            self.assertNotError('netcraft slashdot.org')

        def testTitleSnarfer(self):
            try:
                conf.supybot.plugins.Web.titleSnarfer.setValue(True)
                self.assertSnarfResponse('http://microsoft.com/',
                                         'Title: Microsoft Corporation'
                                         ' (at microsoft.com)')
            finally:
                conf.supybot.plugins.Web.titleSnarfer.setValue(False)

        def testNonSnarfing(self):
            snarf = conf.supybot.plugins.Web.nonSnarfingRegexp()
            title = conf.supybot.plugins.Web.titleSnarfer()
            try:
                conf.supybot.plugins.Web.nonSnarfingRegexp.set('m/sf/')
                try:
                    conf.supybot.plugins.Web.titleSnarfer.setValue(True)
                    self.assertSnarfNoResponse('http://sf.net/', 2)
                    self.assertSnarfRegexp('http://www.sourceforge.net/',
                                           r'Sourceforge\.net')
                finally:
                    conf.supybot.plugins.Web.titleSnarfer.setValue(title)
            finally:
                conf.supybot.plugins.Web.nonSnarfingRegexp.setValue(snarf)

    def testNonSnarfingRegexpConfigurable(self):
        self.assertSnarfNoResponse('http://foo.bar.baz/', 2)
        try:
            conf.supybot.plugins.Web.nonSnarfingRegexp.set('m/biff/')
            self.assertSnarfNoResponse('http://biff.bar.baz/', 2)
        finally:
            conf.supybot.plugins.Web.nonSnarfingRegexp.set('')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
