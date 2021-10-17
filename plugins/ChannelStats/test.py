###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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

from supybot.test import *

import supybot.ircdb as ircdb

class ChannelStatsTestCase(ChannelPluginTestCase):
    plugins = ('ChannelStats', 'User')
    def setUp(self):
        ChannelPluginTestCase.setUp(self)
        self.prefix = 'foo!bar@baz'
        self.nick = 'foo'
        self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                         'register foo bar',
                                         prefix=self.prefix))
        _ = self.irc.takeMsg()
        chanop = ircdb.makeChannelCapability(self.channel, 'op')
        ircdb.users.getUser(self.nick).addCapability(chanop)

    def test(self):
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        self.assertNotError('channelstats')
        self.assertNotError('channelstats')
        self.assertNotError('channelstats')

    def testStats(self):
        self.assertError('channelstats stats %s' % self.nick)
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        self.assertNotError('channelstats stats %s' % self.nick)
        self.assertNotError('channelstats stats %s' % self.nick.upper())
        self.assertNotError('channelstats stats')
        self.assertRegexp('channelstats stats', self.nick)

    def testSelfStats(self):
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        self.assertError('channelstats stats %s' % self.irc.nick)
        self.assertNotError('channelstats stats %s' % self.irc.nick)
        self.assertNotError('channelstats stats %s' % self.irc.nick)
        self.assertNotError('channelstats stats %s' % self.irc.nick.upper())
        self.assertRegexp('channelstats rank chars', self.irc.nick)
        u = ircdb.users.getUser(self.prefix)
        u.addCapability(ircdb.makeChannelCapability(self.channel, 'op'))
        ircdb.users.setUser(u)
        try:
            conf.supybot.plugins.ChannelStats.selfStats.setValue(False)
            m1 = self.getMsg('channelstats stats %s' % self.irc.nick)
            m2 = self.getMsg('channelstats stats %s' % self.irc.nick)
            self.assertEqual(m1.args[1], m2.args[1])
        finally:
            conf.supybot.plugins.ChannelStats.selfStats.setValue(True)

    def testNoKeyErrorStats(self):
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        self.assertNotRegexp('stats sweede', 'KeyError')

    def testRank(self):
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        self.assertError('channelstats stats %s' % self.irc.nick)
        self.assertNotError('channelstats stats %s' % self.irc.nick)
        self.assertNotError('channelstats stats %s' % self.irc.nick)
        self.assertNotError('channelstats stats %s' % self.irc.nick.upper())
        self.assertNotError('channelstats stats %s' % self.nick)
        self.assertNotError('channelstats stats %s' % self.nick.upper())
        self.assertNotError('channelstats stats')
        self.assertNotError('channelstats rank chars / msgs')
        self.assertNotError('channelstats rank kicks/kicked') # Tests inf
        self.assertNotError('channelstats rank log(msgs)')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

