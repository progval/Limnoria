#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

from testsupport import *

url = 'http://www.advogato.org/rss/articles.xml'
if network:
    class RSSTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('RSS',)
        def testRssinfo(self):
            self.assertNotError('rss info %s' % url)
            self.assertNotError('rss add advogato %s' % url)
            self.assertNotError('rss info advogato')
            self.assertNotError('rss info AdVogATo')

        def testRssinfoDoesTimeProperly(self):
            self.assertNotRegexp('rss info http://slashdot.org/slashdot.rss',
                                 '-1 years')

        def testRss(self):
            self.assertNotError('rss %s' % url)
            m = self.assertNotError('rss %s 2' % url)
            self.failUnless(m.args[1].count('||') == 1)

        def testRssAdd(self):
            try:
                orig = conf.supybot.reply.whenNotCommand()
                conf.supybot.reply.whenNotCommand.setValue(True)
                self.assertNotError('rss add advogato %s' % url)
                self.assertNotError('advogato')
                self.assertNotError('rss advogato')
                self.assertNotError('rss remove advogato')
                self.assertError('advogato')
                self.assertError('rss advogato')
            finally:
                conf.supybot.reply.whenNotCommand.setValue(orig)

        def testRssAddBadName(self):
            self.assertError('rss add "foo bar" %s' % url)

        def testCantAddFeedNamedRss(self):
            self.assertError('rss add rss %s' % url)

        def testCantRemoveMethodThatIsntFeed(self):
            self.assertError('rss remove rss')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

