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
    plugins = ('Web', 'Admin',)
    timeout = 10
    if network:
        def testHeaders(self):
            self.assertError('headers ftp://ftp.cdrom.com/pub/linux')
            self.assertNotError('headers http://www.slashdot.org/')

        def testLocation(self):
            self.assertError('location ftp://ftp.cdrom.com/pub/linux')
            self.assertResponse(
                'location http://limnoria.net/', 'https://limnoria.net/')
            self.assertResponse(
                'location https://www.limnoria.net/', 'https://limnoria.net/')

        def testDoctype(self):
            self.assertError('doctype ftp://ftp.cdrom.com/pub/linux')
            self.assertNotError('doctype http://www.slashdot.org/')
            m = self.getMsg('doctype http://moobot.sf.net/')
            self.assertTrue(m.args[1].endswith('>'))

        def testSize(self):
            self.assertError('size ftp://ftp.cdrom.com/pub/linux')
            self.assertNotError('size http://supybot.sf.net/')
            self.assertNotError('size http://www.slashdot.org/')

        def testTitle(self):
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
            self.assertNotError(
                        'title http://www.youtube.com/watch?v=x4BtiqPN4u8')
            self.assertResponse(
                    'title http://www.thefreedictionary.com/don%27t',
                    "Don't - definition of don't by The Free Dictionary")
            self.assertRegexp(
                    'title '
                    'https://twitter.com/rlbarnes/status/656554266744586240',
                    '"PSA: In Firefox 44 Nightly, "http:" pages with '
                    '<input type="password"> are now marked insecure. '
                    'https://t.co/qS9LxuRPdm"$')

        def testTitleSnarfer(self):
            try:
                conf.supybot.plugins.Web.titleSnarfer.setValue(True)
                self.assertSnarfRegexp('http://microsoft.com/',
                                         'Microsoft')
            finally:
                conf.supybot.plugins.Web.titleSnarfer.setValue(False)

        def testMultipleTitleSnarfer(self):
            try:
                conf.supybot.plugins.Web.titleSnarfer.setValue(True)
                conf.supybot.plugins.Web.snarfMultipleUrls.setValue(True)
                self.feedMsg(
                        'https://microsoft.com/ https://google.com/')
                m1 = self.getMsg(' ')
                m2 = self.getMsg(' ')
                self.assertTrue(('Microsoft' in m1.args[1]) ^
                        ('Microsoft' in m2.args[1]))
                self.assertTrue(('Google' in m1.args[1]) ^
                        ('Google' in m2.args[1]))
            finally:
                conf.supybot.plugins.Web.titleSnarfer.setValue(False)
                conf.supybot.plugins.Web.snarfMultipleUrls.setValue(False)

        def testNonSnarfing(self):
            snarf = conf.supybot.plugins.Web.nonSnarfingRegexp()
            title = conf.supybot.plugins.Web.titleSnarfer()
            try:
                conf.supybot.plugins.Web.nonSnarfingRegexp.set('m/fr/')
                try:
                    conf.supybot.plugins.Web.titleSnarfer.setValue(True)
                    self.assertSnarfNoResponse('https://www.google.fr/', 2)
                    self.assertSnarfRegexp('https://www.google.com/',
                                           r'Google')
                finally:
                    conf.supybot.plugins.Web.titleSnarfer.setValue(title)
            finally:
                conf.supybot.plugins.Web.nonSnarfingRegexp.setValue(snarf)

        def testSnarferIgnore(self):
            conf.supybot.plugins.Web.titleSnarfer.setValue(True)
            (oldprefix, self.prefix) = (self.prefix, 'foo!bar@baz')
            try:
                self.assertSnarfRegexp('http://google.com/', 'Google')
                self.assertNotError('admin ignore add %s' % self.prefix)
                self.assertSnarfNoResponse('http://google.com/')
                self.assertNoResponse('title http://www.google.com/')
            finally:
                conf.supybot.plugins.Web.titleSnarfer.setValue(False)
                (self.prefix, oldprefix) = (oldprefix, self.prefix)
                self.assertNotError('admin ignore remove %s' % oldprefix)

        def testSnarferNotIgnore(self):
            conf.supybot.plugins.Web.titleSnarfer.setValue(True)
            conf.supybot.plugins.Web.checkIgnored.setValue(False)
            (oldprefix, self.prefix) = (self.prefix, 'foo!bar@baz')
            try:
                self.assertSnarfRegexp('https://google.it/', 'Google')
                self.assertNotError('admin ignore add %s' % self.prefix)
                self.assertSnarfRegexp('https://www.google.it/', 'Google')
                self.assertNoResponse('title http://www.google.it/')
            finally:
                conf.supybot.plugins.Web.titleSnarfer.setValue(False)
                conf.supybot.plugins.Web.checkIgnored.setValue(True)
                (self.prefix, oldprefix) = (oldprefix, self.prefix)
                self.assertNotError('admin ignore remove %s' % oldprefix)

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
