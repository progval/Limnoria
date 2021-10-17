###
# Copyright (c) 2003-2005, Daniel DiPaolo
# Copyright (c) 2010-2021, Valentin Lorentz
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

from __future__ import print_function

import time

from supybot.test import *

class NewsTestCase(ChannelPluginTestCase):
    plugins = ('News','User')
    def setUp(self):
        ChannelPluginTestCase.setUp(self)
        # Create a valid user to use
        self.prefix = 'news!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.nick, 'register tester moo',
                                         prefix=self.prefix))
        m = self.irc.takeMsg() # Response to register.

    def testAddnews(self):
        self.assertNotError('add 0 subject: foo')
        self.assertRegexp('news', 'subject')
        self.assertNotError('add 0 subject2: foo2')
        self.assertRegexp('news', 'subject.*subject2')
        self.assertNotError('add 5 subject3: foo3')
        self.assertRegexp('news', 'subject3')
        timeFastForward(6)
        self.assertNotRegexp('news', 'subject3')

    def testNews(self):
        # These should both fail first, as they will have nothing in the DB
        self.assertRegexp('news', 'no news')
        self.assertRegexp('news #channel', 'no news')
        # Now we'll add news and make sure listnews doesn't fail
        self.assertNotError('add #channel 0 subject: foo')
        self.assertNotError('news #channel')
        self.assertNotError('add 0 subject: foo')
        self.assertRegexp('news', '#1')
        self.assertNotError('news 1')

    def testChangenews(self):
        self.assertNotError('add 0 Foo: bar')
        self.assertNotError('change 1 s/bar/baz/')
        self.assertNotRegexp('news 1', 'bar')
        self.assertRegexp('news 1', 'baz')

    def testOldnews(self):
        self.assertRegexp('old', 'No old news')
        self.assertNotError('add 0 a: b')
        self.assertRegexp('old', 'No old news')
        self.assertNotError('add 5 foo: bar')
        self.assertRegexp('old', 'No old news')
        timeFastForward(6)
        self.assertNotError('old')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
