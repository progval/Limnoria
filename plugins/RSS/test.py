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

import sys
import feedparser
from supybot.test import *
import supybot.conf as conf
if sys.version_info[0] >= 3:
    from io import BytesIO
else:
    from cStringIO import StringIO as BytesIO

xkcd_old = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>xkcd.com</title><link>http://xkcd.com/</link><description>xkcd.com: A webcomic of romance and math humor.</description><language>en</language><item><title>Snake Facts</title><link>http://xkcd.com/1398/</link><description>&lt;img src="http://imgs.xkcd.com/comics/snake_facts.png" title="Biologically speaking, what we call a 'snake' is actually a human digestive tract which has escaped from its host." alt="Biologically speaking, what we call a 'snake' is actually a human digestive tract which has escaped from its host." /&gt;</description><pubDate>Wed, 23 Jul 2014 04:00:00 -0000</pubDate><guid>http://xkcd.com/1398/</guid></item></channel></rss>
"""

xkcd_new = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>xkcd.com</title><link>http://xkcd.com/</link><description>xkcd.com: A webcomic of romance and math humor.</description><language>en</language><item><title>Chaos</title><link>http://xkcd.com/1399/</link><description>&lt;img src="http://imgs.xkcd.com/comics/chaos.png" title="Although the oral exam for the doctorate was just 'can you do that weird laugh?'" alt="Although the oral exam for the doctorate was just 'can you do that weird laugh?'" /&gt;</description><pubDate>Fri, 25 Jul 2014 04:00:00 -0000</pubDate><guid>http://xkcd.com/1399/</guid></item><item><title>Snake Facts</title><link>http://xkcd.com/1398/</link><description>&lt;img src="http://imgs.xkcd.com/comics/snake_facts.png" title="Biologically speaking, what we call a 'snake' is actually a human digestive tract which has escaped from its host." alt="Biologically speaking, what we call a 'snake' is actually a human digestive tract which has escaped from its host." /&gt;</description><pubDate>Wed, 23 Jul 2014 04:00:00 -0000</pubDate><guid>http://xkcd.com/1398/</guid></item></channel></rss>
"""


def constant(content):
    if sys.version_info[0] >= 3:
        content = content.encode()
    def f(*args, **kwargs):
        return BytesIO(content)
    return f

url = 'http://www.advogato.org/rss/articles.xml'
class RSSTestCase(ChannelPluginTestCase):
    plugins = ('RSS','Plugin')
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

    def testInitialAnnounce(self):
        old_open = feedparser._open_resource
        feedparser._open_resource = constant(xkcd_old)
        try:
            with conf.supybot.plugins.RSS.initialAnnounceHeadlines.context(0):
                self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
                self.assertNotError('rss announce add xkcd')
                self.assertNoResponse(' ')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')
            feedparser._open_resource = old_open

    def testAnnounce(self):
        old_open = feedparser._open_resource
        feedparser._open_resource = constant(xkcd_old)
        try:
            self.assertError('rss announce add xkcd')
            self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
            self.assertNotError('rss announce add xkcd')
            self.assertNotError(' ')
            if network:
                with conf.supybot.plugins.RSS.waitPeriod.context(1):
                    time.sleep(1.1)
                    self.assertNoResponse(' ')
                    feedparser._open_resource = constant(xkcd_new)
                    self.assertNoResponse(' ')
                    time.sleep(1.1)
                    self.assertRegexp(' ', 'Chaos')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')
            feedparser._open_resource = old_open

    def testAnnounceReload(self):
        old_open = feedparser._open_resource
        feedparser._open_resource = constant(xkcd_old)
        try:
            with conf.supybot.plugins.RSS.waitPeriod.context(1):
                self.assertNotError('rss add xkcd http://xkcd.com/rss.xml')
                self.assertNotError('rss announce add xkcd')
                self.assertNotError(' ')
                self.assertNotError('reload RSS')
                self.assertNoResponse(' ')
                time.sleep(1.1)
                self.assertNoResponse(' ')
        finally:
            self._feedMsg('rss announce remove xkcd')
            self._feedMsg('rss remove xkcd')
            feedparser._open_resource = old_open

    def testFeedSpecificFormat(self):
        old_open = feedparser._open_resource
        feedparser._open_resource = constant(xkcd_old)
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
            feedparser._open_resource = old_open

    if network:
        def testRssinfo(self):
            self.assertNotError('rss info %s' % url)
            self.assertNotError('rss add advogato %s' % url)
            self.assertNotError('rss info advogato')
            self.assertNotError('rss info AdVogATo')
            self.assertNotError('rss remove advogato')

        def testRssinfoDoesTimeProperly(self):
            self.assertNotRegexp('rss info http://slashdot.org/slashdot.rss',
                                 '-1 years')

        def testAnnounceAdd(self):
            self.assertNotError('rss add advogato %s' % url)
            self.assertNotError('rss announce add advogato')
            self.assertNotRegexp('rss announce', r'ValueError')
            self.assertNotError('rss announce remove advogato')
            self.assertNotError('rss remove advogato')

        def testRss(self):
            self.assertNotError('rss %s' % url)
            m = self.assertNotError('rss %s 2' % url)
            self.failUnless(m.args[1].count(' | ') == 1)

        def testRssAdd(self):
            self.assertNotError('rss add advogato %s' % url)
            self.assertNotError('advogato')
            self.assertNotError('rss advogato')
            self.assertNotError('rss remove advogato')
            self.assertNotRegexp('list RSS', 'advogato')
            self.assertError('advogato')
            self.assertError('rss advogato')

        def testNonAsciiFeeds(self):
            self.assertNotError('rss http://www.heise.de/newsticker/heise.rdf')
            self.assertNotError('rss info http://br-linux.org/main/index.xml')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
