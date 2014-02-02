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
            self.assertRegexp('title http://www.slashdot.org/',
                              'News for nerds, stuff that matters')
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
            print()
            print("If we have not fixed a bug with the parser, the following")
            print("test will hang the test-suite.")
            self.assertNotError(
                        'title http://www.youtube.com/watch?v=x4BtiqPN4u8')

        def testTitleSnarfer(self):
            try:
                conf.supybot.plugins.Web.titleSnarfer.setValue(True)
                self.assertSnarfRegexp('http://microsoft.com/',
                                         'Microsoft')
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

        def testWhitelist(self):
            fm = conf.supybot.plugins.Web.fetch.maximum()
            uw = conf.supybot.plugins.Web.urlWhitelist()
            try:
                conf.supybot.plugins.Web.fetch.maximum.set(1024)
                self.assertNotError('web fetch http://fsf.org')
                conf.supybot.plugins.Web.urlWhitelist.set('http://slashdot.org')
                self.assertError('web fetch http://fsf.org')
                self.assertError('wef title http://fsf.org')
                self.assertError('web fetch http://slashdot.org.evildomain.com')
                self.assertNotError('web fetch http://slashdot.org')
                self.assertNotError('web fetch http://slashdot.org/recent')
                conf.supybot.plugins.Web.urlWhitelist.set('http://slashdot.org http://fsf.org')
                self.assertNotError('doctype http://fsf.org')
            finally:
                conf.supybot.plugins.Web.urlWhitelist.set('')
                conf.supybot.plugins.Web.fetch.maximum.set(fm)

    def testNonSnarfingRegexpConfigurable(self):
        self.assertSnarfNoResponse('http://foo.bar.baz/', 2)
        try:
            conf.supybot.plugins.Web.nonSnarfingRegexp.set('m/biff/')
            self.assertSnarfNoResponse('http://biff.bar.baz/', 2)
        finally:
            conf.supybot.plugins.Web.nonSnarfingRegexp.set('')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
