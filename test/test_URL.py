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

urls = """
http://www.ureg.ohio-state.edu/courses/book3.asp
http://wwwsearch.sourceforge.net/ClientForm/
http://slashdot.org/comments.pl?sid=75443&cid=6747654
http://baseball-almanac.com/rb_menu.shtml
http://www.linuxquestions.org/questions/showthread.php?postid=442905#post442905
http://games.slashdot.org/comments.pl?sid=76027&cid=6785588'
http://games.slashdot.org/comments.pl?sid=76027&cid=6785588
http://www.census.gov/ftp/pub/tiger/tms/gazetteer/zcta5.zip
http://slashdot.org/~Strike
http://lambda.weblogs.com/xml/rss.xml'
http://lambda.weblogs.com/xml/rss.xml
http://www.sourcereview.net/forum/index.php?showforum=8
http://www.sourcereview.net/forum/index.php?showtopic=291
http://www.sourcereview.net/forum/index.php?showtopic=291&st=0&#entry1778
http://dhcp065-024-059-168.columbus.rr.com:81/~jfincher/old-supybot.tar.gz
http://www.sourcereview.net/forum/index.php?
http://www.joelonsoftware.com/articles/BuildingCommunitieswithSo.html
http://gameknot.com/stats.pl?ddipaolo
http://slashdot.org/slashdot.rss
http://slashdot.org/slashdot.rss
http://gameknot.com/chess.pl?bd=1038943
http://gameknot.com/chess.pl?bd=1038943
http://gameknot.com/chess.pl?bd=1038943
http://codecentral.sleepwalkers.org/
http://gameknot.com/chess.pl?bd=1037471&r=327
http://gameknot.com/chess.pl?bd=1037471&r=327
http://gameknot.com/chess.pl?bd=1037471&r=327
http://gameknot.com/chess.pl?bd=1037471&r=327
http://dhcp065-024-059-168.columbus.rr.com:81/~jfincher/angryman.py
https://sourceforge.net/projects/pyrelaychecker/
http://gameknot.com/tsignup.pl
http://lambda.weblogs.com/xml/rss.xml
""".strip().splitlines()
    
try:
    import sqlite
except ImportError:
    sqlite = None

if sqlite is not None:
    class URLTestCase(ChannelPluginTestCase, PluginDocumentation):
        plugins = ('URL',)
        def test(self):
            self.assertNotError('config tinyurlsnarfer off')
            counter = 0
            self.assertNotError('url random')
            for url in urls:
                self.assertRegexp('url num', str(counter))
                self.feedMsg(url)
                counter += 1
            self.assertRegexp('url num', str(counter))
            self.assertRegexp('url last', re.escape(urls[-1]))
            self.assertRegexp('url last --proto https', re.escape(urls[-3]))
            self.assertRegexp('url last --at gameknot.com',re.escape(urls[-2]))
            self.assertRegexp('url last --with dhcp', re.escape(urls[-4]))
            self.assertRegexp('url last --from alsdkjf', '^No')
            self.assertNotError('url random')

        def testDefaultNotFancy(self):
            self.assertNotError('url config tinyurlsnarfer off')
            self.feedMsg(urls[0])
            self.assertResponse('url last', urls[0])

        def testAction(self):
            self.assertNotError('url config tinyurlsnarfer off')
            self.irc.feedMsg(ircmsgs.action(self.channel, urls[1]))
            self.assertNotRegexp('url last', '\\x01')

        def testTinyurl(self):
            self.assertNotError('url config tinyurlsnarfer off')
            self.assertRegexp('url tiny http://sourceforge.net/tracker/?'
                              'func=add&group_id=58965&atid=489447',
                              r'http://tinyurl.com/rqac')
            self.assertNotError('url config tinyurlsnarfer on')
            self.assertRegexp('url tiny http://sourceforge.net/tracker/?'
                              'func=add&group_id=58965&atid=489447',
                              r'http://tinyurl.com/rqac')

        def testTinysnarf(self):
            self.assertNotError('url config tinyurlsnarfer on')
            self.assertRegexp('http://www.urbandictionary.com/define.php?'
                              'term=all+your+base+are+belong+to+us',
                              r'http://tinyurl.com/u479.* \(was')
            self.assertRegexp('http://sourceforge.net/tracker/?'
                              'func=add&group_id=58965&atid=489447',
                              r'http://tinyurl.com/rqac.* \(was')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

