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

from supybot.test import *

url = 'http://www.advogato.org/rss/articles.xml'
class RSSTestCase(ChannelPluginTestCase):
    plugins = ('RSS','Plugin')
    def testRssAddBadName(self):
        self.assertError('rss add "foo bar" %s' % url)

    def testCantAddFeedNamedRss(self):
        self.assertError('rss add rss %s' % url)

    def testCantRemoveMethodThatIsntFeed(self):
        self.assertError('rss remove rss')

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

        def testAnnounce(self):
            self.assertNotError('rss add advogato %s' % url)
            self.assertNotError('rss announce add advogato')
            self.assertNotRegexp('rss announce', r'ValueError')
            self.assertNotError('rss announce remove advogato')
            self.assertNotError('rss remove advogato')

        def testRss(self):
            self.assertNotError('rss %s' % url)
            m = self.assertNotError('rss %s 2' % url)
            self.failUnless(m.args[1].count('||') == 1)

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
