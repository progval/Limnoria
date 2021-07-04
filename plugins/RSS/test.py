###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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

import functools
from unittest.mock import patch
import sys

import feedparser

from supybot.test import *
import supybot.conf as conf
import supybot.utils.minisix as minisix

xkcd_old = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>xkcd.com</title><link>http://xkcd.com/</link><description>xkcd.com: A webcomic of romance and math humor.</description><language>en</language><item><title>Snake Facts</title><link>http://xkcd.com/1398/</link><description>&lt;img src="http://imgs.xkcd.com/comics/snake_facts.png" title="Biologically speaking, what we call a 'snake' is actually a human digestive tract which has escaped from its host." alt="Biologically speaking, what we call a 'snake' is actually a human digestive tract which has escaped from its host." /&gt;</description><pubDate>Wed, 23 Jul 2014 04:00:00 -0000</pubDate><guid>http://xkcd.com/1398/</guid></item></channel></rss>
"""

xkcd_new = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>xkcd.com</title><link>http://xkcd.com/</link><description>xkcd.com: A webcomic of romance and math humor.</description><language>en</language><item><title>Telescopes: Refractor vs Reflector</title><link>http://xkcd.com/1791/</link><description>&lt;img src="http://imgs.xkcd.com/comics/telescopes_refractor_vs_reflector.png" title="On the other hand, the refractor's limited light-gathering means it's unable to make out shadow people or the dark god Chernabog." alt="On the other hand, the refractor's limited light-gathering means it's unable to make out shadow people or the dark god Chernabog." /&gt;</description><pubDate>Fri, 27 Jan 2017 05:00:00 -0000</pubDate><guid>http://xkcd.com/1791/</guid></item><item><title>Chaos</title><link>http://xkcd.com/1399/</link><description>&lt;img src="http://imgs.xkcd.com/comics/chaos.png" title="Although the oral exam for the doctorate was just 'can you do that weird laugh?'" alt="Although the oral exam for the doctorate was just 'can you do that weird laugh?'" /&gt;</description><pubDate>Fri, 25 Jul 2014 04:00:00 -0000</pubDate><guid>http://xkcd.com/1399/</guid></item><item><title>Snake Facts</title><link>http://xkcd.com/1398/</link><description>&lt;img src="http://imgs.xkcd.com/comics/snake_facts.png" title="Biologically speaking, what we call a 'snake' is actually a human digestive tract which has escaped from its host." alt="Biologically speaking, what we call a 'snake' is actually a human digestive tract which has escaped from its host." /&gt;</description><pubDate>Wed, 23 Jul 2014 04:00:00 -0000</pubDate><guid>http://xkcd.com/1398/</guid></item></channel></rss>
"""

not_well_formed = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
<channel>
	<title>this is missing a close tag
	<link>http://example.com/</link>
	<description>this dummy feed has no elements</description>
	<language>en</language>
</channel>
</rss>
"""


class MockResponse:
    headers = {}
    url = ''
    def read(self):
        return self._data.encode()

    def close(self):
        pass

def mock_urllib(f):
    mock = MockResponse()

    @functools.wraps(f)
    def newf(self):
        with patch("urllib.request.OpenerDirector.open", return_value=mock):
            f(self, mock)

    return newf


url = 'http://www.advogato.org/rss/articles.xml'
class RSSTestCase(ChannelPluginTestCase):
    plugins = ('RSS','Plugin')

    timeout = 1

    def testRssAddBadName(self):
        self.assertError('rss add "foo bar" %s' % url)

    def testCantAddFeedNamedRss(self):
        self.assertError('rss add rss %s' % url)

    def testCantRemoveMethodThatIsntFeed(self):
        self.assertError('rss remove rss')

    def testCantAddDuplicatedFeed(self):
        self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
        try:
            self.assertError('rss add xkcddup http://xkcd.com/rss.xml')
        finally:
            self.assertNotError('rss remove xkcd')

    @mock_urllib
    def testRemoveAliasedFeed(self, mock):
        mock._data = xkcd_new
        try:
            self.assertNotError('rss announce add http://xkcd.com/rss.xml')
            self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
        finally:
            self.assertNotError('rss announce remove http://xkcd.com/rss.xml')
            self.assertNotError('rss remove xkcd')
        self.assertEqual(self.irc.getCallback('RSS').feed_names, {})

    @mock_urllib
    def testInitialAnnounceNewest(self, mock):
        mock._data = xkcd_new
        timeFastForward(1.1)
        try:
            with conf.supybot.plugins.RSS.sortFeedItems.context('newestFirst'):
                with conf.supybot.plugins.RSS.initialAnnounceHeadlines.context(1):
                    self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
                    self.assertNotError('rss announce add xkcd')
                    self.assertRegexp(' ', 'Telescopes')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')

    @mock_urllib
    def testInitialAnnounceOldest(self, mock):
        mock._data = xkcd_new
        timeFastForward(1.1)
        try:
            with conf.supybot.plugins.RSS.initialAnnounceHeadlines.context(1):
                with conf.supybot.plugins.RSS.sortFeedItems.context('oldestFirst'):
                    self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
                    self.assertNotError('rss announce add xkcd')
                    self.assertRegexp(' ', 'Telescopes')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')

    @mock_urllib
    def testNoInitialAnnounce(self, mock):
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            with conf.supybot.plugins.RSS.initialAnnounceHeadlines.context(0):
                self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
                self.assertNotError('rss announce add xkcd')
                self.assertNoResponse(' ', timeout=0.1)
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')

    @mock_urllib
    def testAnnounce(self, mock):
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            self.assertError('rss announce add xkcd')
            self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
            self.assertNotError('rss announce add xkcd')
            self.assertNotError(' ')
            with conf.supybot.plugins.RSS.sortFeedItems.context('oldestFirst'):
                with conf.supybot.plugins.RSS.waitPeriod.context(1):
                    timeFastForward(1.1)
                    self.assertNoResponse(' ', timeout=0.1)
                    mock._data = xkcd_new
                    self.assertNoResponse(' ', timeout=0.1)
                    timeFastForward(1.1)
                    self.assertRegexp(' ', 'Chaos')
                    self.assertRegexp(' ', 'Telescopes')
                    self.assertNoResponse(' ')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')

    @mock_urllib
    def testMaxAnnounces(self, mock):
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            self.assertError('rss announce add xkcd')
            self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
            self.assertNotError('rss announce add xkcd')
            self.assertNotError(' ')
            with conf.supybot.plugins.RSS.sortFeedItems.context('oldestFirst'):
                with conf.supybot.plugins.RSS.waitPeriod.context(1):
                    with conf.supybot.plugins.RSS.maximumAnnounceHeadlines.context(1):
                        timeFastForward(1.1)
                        self.assertNoResponse(' ', timeout=0.1)
                        mock._data = xkcd_new
                        log.debug('set return value to: %r', xkcd_new)
                        self.assertNoResponse(' ', timeout=0.1)
                        timeFastForward(1.1)
                        self.assertRegexp(' ', 'Telescopes')
                        self.assertNoResponse(' ')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')

    @mock_urllib
    def testAnnounceAnonymous(self, mock):
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            self.assertNotError('rss announce add http://xkcd.com/rss.xml')
            self.assertNotError(' ')
            with conf.supybot.plugins.RSS.waitPeriod.context(1):
                timeFastForward(1.1)
                self.assertNoResponse(' ', timeout=0.1)
                mock._data = xkcd_new
                self.assertNoResponse(' ', timeout=0.1)
                timeFastForward(1.1)
                self.assertRegexp(' ', 'Telescopes')
                self.assertRegexp(' ', 'Chaos')
                self.assertNoResponse(' ', timeout=0.1)
            self.assertResponse('announce list', 'http://xkcd.com/rss.xml')
        finally:
            self._feedMsg('rss announce remove http://xkcd.com/rss.xml')
            self._feedMsg('rss remove http://xkcd.com/rss.xml')

    @mock_urllib
    def testAnnounceReload(self, mock):
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            with conf.supybot.plugins.RSS.waitPeriod.context(1):
                self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
                self.assertNotError('rss announce add xkcd')
                self.assertNotError(' ', timeout=0.1)
                self.assertNotError('reload RSS')
                self.assertNoResponse(' ', timeout=0.1)
                timeFastForward(1.1)
                self.assertNoResponse(' ', timeout=0.1)
            self.assertResponse('announce list', 'xkcd')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')

    @mock_urllib
    def testReload(self, mock):
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            with conf.supybot.plugins.RSS.waitPeriod.context(1):
                self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
                self.assertNotError('rss announce add xkcd')
                self.assertRegexp(' ', 'Snake Facts')
                mock._data = xkcd_new
                self.assertNotError('reload RSS')
                self.assertRegexp(' ', 'Telescopes')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')

    @mock_urllib
    def testReloadNoDelay(self, mock):
        # https://github.com/ProgVal/Limnoria/issues/922
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            with conf.supybot.plugins.RSS.waitPeriod.context(1):
                self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
                self.assertRegexp('xkcd', 'Snake Facts')
                self.assertNotError('reload RSS')
                self.assertRegexp('xkcd', 'Snake Facts')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')

    @mock_urllib
    def testReannounce(self, mock):
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            self.assertError('rss announce add xkcd')
            self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
            self.assertNotError('rss announce add xkcd')
            self.assertRegexp(' ', 'Snake Facts')
            with conf.supybot.plugins.RSS.waitPeriod.context(1):
                with conf.supybot.plugins.RSS.initialAnnounceHeadlines.context(1):
                    with conf.supybot.plugins.RSS.sortFeedItems.context('oldestFirst'):
                        timeFastForward(1.1)
                        self.assertNoResponse(' ', timeout=0.1)
                        self._feedMsg('rss announce remove xkcd')
                        mock._data = xkcd_new
                        timeFastForward(1.1)
                        self.assertNoResponse(' ', timeout=0.1)
                        self.assertNotError('rss announce add xkcd')
                        timeFastForward(1.1)
                        self.assertRegexp(' ', 'Chaos')
                        self.assertRegexp(' ', 'Telescopes')
                        self.assertNoResponse(' ')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')

    @mock_urllib
    def testFeedSpecificFormat(self, mock):
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
            self.assertNotError('rss add xkcdsec https://xkcd.com/rss.xml')
            self.assertNotError('config plugins.RSS.feeds.xkcd.format foo')
            self.assertRegexp('config plugins.RSS.feeds.xkcd.format', 'foo')
            self.assertRegexp('xkcd', 'foo')
            self.assertNotRegexp('xkcdsec', 'foo')
        finally:
            self._feedMsg('rss remove xkcd')
            self._feedMsg('rss remove xkcdsec')

    @mock_urllib
    def testFeedSpecificWaitPeriod(self, mock):
        mock._data = xkcd_old
        timeFastForward(1.1)
        try:
            self.assertNotError('rss add xkcd1 http://xkcd.com/rss.xml')
            self.assertNotError('rss announce add xkcd1')
            self.assertNotError('rss add xkcd2 http://xkcd.com/rss.xml&foo')
            self.assertNotError('rss announce add xkcd2')
            self.assertNotError(' ')
            self.assertNotError(' ')
            with conf.supybot.plugins.RSS.sortFeedItems.context('oldestFirst'):
                with conf.supybot.plugins.RSS.feeds.xkcd1.waitPeriod.context(1):
                    timeFastForward(1.1)
                    self.assertNoResponse(' ', timeout=0.1)
                    mock._data = xkcd_new
                    self.assertNoResponse(' ', timeout=0.1)
                    timeFastForward(1.1)
                    self.assertRegexp(' ', 'xkcd1.*Chaos')
                    self.assertRegexp(' ', 'xkcd1.*Telescopes')
                    self.assertNoResponse(' ')
                    timeFastForward(1.1)
                    self.assertNoResponse(' ', timeout=0.1)
        finally:
            self._feedMsg('rss announce remove xkcd1')
            self._feedMsg('rss remove xkcd1')
            self._feedMsg('rss announce remove xkcd2')
            self._feedMsg('rss remove xkcd2')

    @mock_urllib
    def testDescription(self, mock):
        timeFastForward(1.1)
        with conf.supybot.plugins.RSS.format.context('$description'):
            mock._data = xkcd_new
            self.assertRegexp('rss http://xkcd.com/rss.xml',
                    'On the other hand, the refractor\'s')

    @mock_urllib
    def testBadlyFormedFeedWithNoItems(self, mock):
        # This combination will cause the RSS command to show the last parser
        # error.
        timeFastForward(1.1)
        mock._data = not_well_formed
        self.assertRegexp('rss http://example.com/',
                          'Parser error')

    if network:
        timeout = 5  # Note this applies also to the above tests

        def testRssinfo(self):
            timeFastForward(1.1)
            self.assertNotError('rss info %s' % url)
            self.assertNotError('rss add advogato %s' % url)
            self.assertNotError('rss info advogato')
            self.assertNotError('rss info AdVogATo')
            self.assertNotError('rss remove advogato')

        def testRssinfoDoesTimeProperly(self):
            timeFastForward(1.1)
            self.assertNotRegexp('rss info http://slashdot.org/slashdot.rss',
                                 '-1 years')

        def testAnnounceAdd(self):
            timeFastForward(1.1)
            self.assertNotError('rss add advogato %s' % url)
            self.assertNotError('rss announce add advogato')
            self.assertRegexp('rss announce channels advogato', 'advogato is announced to.*%s%s' % (self.irc.network, self.channel))

            self.assertNotRegexp('rss announce', r'ValueError')

            self.assertNotError('rss announce remove advogato')
            self.assertRegexp('rss announce channels advogato', 'advogato is not announced to any channels')

            self.assertNotError('rss remove advogato')
            self.assertRegexp('rss announce channels advogato', 'Unknown feed')

        def testRss(self):
            timeFastForward(1.1)
            self.assertNotError('rss %s' % url)
            m = self.assertNotError('rss %s 2' % url)
            self.assertTrue(m.args[1].count(' | ') == 1)

        def testRssAdd(self):
            timeFastForward(1.1)
            self.assertNotError('rss add advogato %s' % url)
            self.assertNotError('advogato')
            self.assertNotError('rss advogato')
            self.assertNotError('rss remove advogato')
            self.assertNotRegexp('list RSS', 'advogato')
            self.assertError('advogato')
            self.assertError('rss advogato')

        def testNonAsciiFeeds(self):
            timeFastForward(1.1)
            self.assertNotError('rss http://www.heise.de/newsticker/heise.rdf')
            self.assertNotError('rss info http://br-linux.org/main/index.xml')



# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
