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

        def testKarma(self):
            self.assertRegexp('karma foobar', 'no karma')
            try:
                conf.replyWhenNotCommand = True
                self.assertNoResponse('foobar++', 2)
            finally:
                conf.replyWhenNotCommand = False
            self.assertRegexp('karma foobar', 'increased 1.*total.*1')
            self.assertRegexp('karma FOOBAR', 'increased 1.*total.*1')
            self.assertNoResponse('foobar--', 2)
            self.assertRegexp('karma foobar', 'decreased 1.*total.*0')
            self.assertRegexp('karma FOOBAR', 'decreased 1.*total.*0')
            self.assertNoResponse('FOO++', 2)
            self.assertNoResponse('BAR--', 2)
            self.assertRegexp('karma foo bar foobar', '.*foo.*foobar.*bar.*')
            self.assertRegexp('karma FOO BAR FOOBAR', '.*foo.*foobar.*bar.*')
            self.assertRegexp('karma FOO BAR FOOBAR',
                              '.*FOO.*foobar.*BAR.*', flags=0)
            # Test case-insensitive
            self.assertNoResponse('MOO++', 2)
            self.assertRegexp('karma moo', 'Karma for \'moo\'.*increased 1'
                              '.*total.*1')
            self.assertRegexp('karma MoO', 'Karma for \'MoO\'.*increased 1'
                              '.*total.*1')



# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

