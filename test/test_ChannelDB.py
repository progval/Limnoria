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

import ircdb

try:
    import sqlite
except ImportError:
    sqlite = None

if sqlite is not None:
    class ChannelDBTestCase(ChannelPluginTestCase, PluginDocumentation):
        plugins = ('ChannelDB', 'Misc', 'User')
        def setUp(self):
            ChannelPluginTestCase.setUp(self)
            self.prefix = 'foo!bar@baz'
            self.nick = 'foo'
            self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                             'register foo bar',
                                             prefix=self.prefix))
            _ = self.irc.takeMsg()
            
        def test(self):
            self.assertNotError('channelstats')
            self.assertNotError('channelstats')
            self.assertNotError('channelstats')

        def testStats(self):
            self.assertError('channeldb stats %s' % self.nick)
            self.assertNotError('channeldb stats %s' % self.nick)
            self.assertNotError('channeldb stats %s' % self.nick.upper())
            self.assertNotError('channeldb stats')
            self.assertRegexp('channeldb stats', self.nick)

        def testSelfStats(self):
            self.assertError('channeldb stats %s' % self.irc.nick)
            self.assertNotError('channeldb stats %s' % self.irc.nick)
            self.assertNotError('channeldb stats %s' % self.irc.nick)
            id = ircdb.users.getUserId(self.prefix)
            u = ircdb.users.getUser(id)
            u.addCapability(ircdb.makeChannelCapability(self.channel, 'op'))
            ircdb.users.setUser(id, u)
            self.assertNotError('channeldb toggle selfstats off')
            m1 = self.getMsg('channeldb stats %s' % self.irc.nick)
            m2 = self.getMsg('channeldb stats %s' % self.irc.nick)
            self.assertEqual(m1.args[1], m2.args[1])
            
        def testNoKeyErrorEscapeFromSeen(self):
            self.assertRegexp('seen asldfkjasdlfkj', 'I have not seen')
            self.assertNotRegexp('seen asldfkjasdlfkj', 'KeyError')

        def testNoKeyErrorStats(self):
            self.assertNotRegexp('stats sweede', 'KeyError')

        def testSeen(self):
            self.assertNotError('list')
            self.assertNotError('seen %s' % self.nick)
            self.assertNotError('seen %s' % self.nick.upper())

        def testWordStatsNoArgs(self):
            self.assertResponse('wordstats', 'I am not currently keeping any '
                                             'word stats.')
            self.assertNotError('addword lol')
            self.assertResponse('wordstats', 'Currently keeping stats for: '
                                             '\'lol\'')

        def testWordStatsUser(self):
            self.assertNotError('addword lol')
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol',
                                             prefix=self.prefix))
            self.assertResponse('wordstats foo', '\'lol\': 2')
            self.assertNotError('addword moo')
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
            self.assertNotError('addword lol')
            self.assertResponse('wordstats lol', 'Top 1 \'lol\'er: foo: 1')
            for i in range(5):
                self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol',
                                                 prefix=userPrefix1))
            self.assertResponse('wordstats lol', 'Top 2 \'lol\'ers: %s: 5 '
                                                 'and foo: 2' % userNick1)
            for i in range(10):
                self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'lol',
                                                 prefix=userPrefix2))
            self.assertResponse('wordstats lol', 'Top 3 \'lol\'ers: %s: 10, '
                                                 '%s: 5, and foo: 3' % (\
                                                 userNick2, userNick1))

        def testWordStatsUserWord(self):
            self.assertNotError('addword lol')
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
            self.assertNotError('addword heh')
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
            self.assertError('addword lol!')
            self.assertNotError('addword lolz0r')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

