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

import supybot.ircdb as ircdb

class WordStatsTestCase(ChannelPluginTestCase):
    plugins = ('WordStats', 'User', 'Utilities')
    def setUp(self):
        ChannelPluginTestCase.setUp(self)
        self.prefix = 'foo!bar@baz'
        self.nick = 'foo'
        self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                         'register foo bar',
                                         prefix=self.prefix))
        _ = self.irc.takeMsg()
        ircdb.users.getUser(self.nick).addCapability(self.channel + '.op')

    def testWordStatsNoArgs(self):
        self.assertResponse('wordstats', 'I am not currently keeping any '
                                         'word stats.')
        self.assertNotError('add lol')
        self.assertResponse('wordstats',
                            'I am currently keeping stats for lol.')

    def testWordStatsUser(self):
        self.assertNotError('add lol')
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol',
                                         prefix=self.prefix))
        self.assertResponse('wordstats foo', '\'lol\': 2')
        self.assertNotError('add moo')
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'moo',
                                         prefix=self.prefix))
        self.assertResponse('wordstats foo', '\'lol\': 2 and \'moo\': 2')

    def testWordStatsWord(self):
        userPrefix1 = 'moo!bar@baz'; userNick1 = 'moo'
        userPrefix2 = 'boo!bar@baz'; userNick2 = 'boo'
        self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                         'register %s bar' % userNick1,
                                         prefix=userPrefix1))
        self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                         'register %s bar' % userNick2,
                                         prefix=userPrefix2))
        _ = self.irc.takeMsg()
        _ = self.irc.takeMsg()
        self.assertNotError('add lol')
        self.assertRegexp('wordstats lol', 'foo: 1')
        for i in range(5):
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol',
                                             prefix=userPrefix1))
        self.assertRegexp('wordstats lol',
                          '2.*%s: 5.*foo: 2' % userNick1)
        for i in range(10):
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol',
                                             prefix=userPrefix2))
        self.assertRegexp('wordstats lol',
                          '3.*%s: 10.*%s: 5.*foo: 3' %
                          (userNick2, userNick1))
        # Check for the extra-swanky stuff too
        # (note: to do so we must make sure they don't appear in the list,
        # so we'll tweak the config)
        try:
            orig = conf.supybot.plugins.WordStats.rankingDisplay()
            conf.supybot.plugins.WordStats.rankingDisplay.setValue(2)
            self.assertRegexp('wordstats lol',
                              'total.*19 \'lol\'s.*%s: 10.*%s: 5.*'
                              'ranked 3 out of 3 \'lol\'ers' % \
                              (userNick2, userNick1))
        finally:
            conf.supybot.plugins.WordStats.rankingDisplay.setValue(orig)

    def testWordStatsUserWord(self):
        self.assertNotError('add lol')
        self.assertResponse('wordstats foo lol',
                            'foo has said \'lol\' 1 time.')
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol',
                                         prefix=self.prefix))
        self.assertResponse('wordstats foo lol',
                            'foo has said \'lol\' 3 times.')
        # Now check for case-insensitivity
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'LOL',
                                         prefix=self.prefix))
        self.assertResponse('wordstats foo lol',
                            'foo has said \'lol\' 5 times.')
        # Check and make sure actions get nabbed too
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol',
                                        prefix=self.prefix))
        self.assertResponse('wordstats foo lol',
                            'foo has said \'lol\' 7 times.')
        # Check and make sure it handles two words in one message
        self.assertNotError('add heh')
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol heh',
                                         prefix=self.prefix))
        self.assertResponse('wordstats foo lol',
                            'foo has said \'lol\' 9 times.')
        self.assertResponse('wordstats foo heh',
                            'foo has said \'heh\' 2 times.')
        # It should ignore punctuation around words
        self.irc.feedMsg(ircmsgs.privmsg(self.channel,'lol, I said "heh"',
                                         prefix=self.prefix))
        self.assertResponse('wordstats foo lol',
                            'foo has said \'lol\' 11 times.')
        self.assertResponse('wordstats foo heh',
                            'foo has said \'heh\' 4 times.')

    def testAddword(self):
        self.assertError('add lol!')
        self.assertNotError('add lolz0r')
        self.assertRegexp('wordstats lolz0r', r'1 \'lolz0r\' seen')

    def testRemoveword(self):
        self.assertError('wordstats remove foo')
        self.assertNotError('wordstats add foo')
        self.assertRegexp('wordstats foo', r'1 \'foo\' seen')
        self.assertRegexp('wordstats foo', r'2 \'foo\'s seen')
        self.assertNotError('wordstats remove foo')
        self.assertRegexp('wordstats foo', r'doesn\'t look like a word I')
        # Verify that we aren't keeping results from before
        self.assertNotError('add foo')
        self.assertRegexp('wordstats foo', r'1 \'foo\' seen')

    def testWordStatsRankingDisplay(self):
        self.assertNotError('add lol')
        try:
            orig = conf.supybot.plugins.WordStats.rankingDisplay()
            conf.supybot.plugins.WordStats.rankingDisplay.setValue(5)
            # Create 10 users and have them each send a different number of
            # 'lol's to the channel
            users = []
            for i in range(10):
                users.append(('foo%s!bar@baz' % i, 'foo%s' % i))
                self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                                 'register %s bar' % \
                                                 users[i][1],
                                                 prefix=users[i][0]))
                _ = self.irc.takeMsg()
            for i in range(10):
                for j in range(i):
                    self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol',
                                                     prefix=users[i][0]))
            # Make sure it shows the top 5
            self.assertRegexp('wordstats lol',
                              'Top 5 \'lol\'ers.*foo9: 9.*foo8: 8.*'
                              'foo7: 7.*foo6: 6.*foo5: 5')
        finally:
            conf.supybot.plugins.WordStats.rankingDisplay.setValue(orig)

    def testWordStatsIgnoreQueries(self):
        try:
            original = conf.supybot.plugins.WordStats.ignoreQueries()
            conf.supybot.plugins.WordStats.ignoreQueries.setValue(True)
            self.assertNotError('add lol')
            self.assertNotRegexp('wordstats lol', 'foo')
            self.assertNotRegexp('wordstats lol', 'foo')
            self.assertNotRegexp('wordstats lol', 'foo')
            self.assertNotError('echo lol')
            self.assertRegexp('wordstats lol', 'foo: 1')
            self.assertRegexp('wordstats lol', 'foo: 1')
            self.assertRegexp('wordstats lol', 'foo: 1')
        finally:
            conf.supybot.plugins.WordStats.ignoreQueries.setValue(original)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

