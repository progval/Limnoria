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

from testsupport import *

import supybot.ircdb as ircdb

try:
    import sqlite
except ImportError:
    sqlite = None

if sqlite is not None:
    class TestFunDB(ChannelPluginTestCase, PluginDocumentation):
        plugins = ('FunDB','User','Utilities')
        def setUp(self):
            ChannelPluginTestCase.setUp(self)
            self.prefix = 't3st!bar@foo.com'
            self.nick = 't3st'
            self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                             'register t3st moo',
                                             prefix=self.prefix))
            _ = self.irc.takeMsg()
            #ircdb.users.getUser('t3st').addCapability('admin')
            ircdb.users.getUser('t3st').addCapability('#test.op')
            conf.supybot.plugins.FunDB.showIds.setValue(True)

        def testAdd(self):
            self.assertError('add l4rt foo')
            self.assertError('add lart foo')

        def testRemove(self):
            self.assertError('remove l4rt foo')
            self.assertError('remove lart foo')

        def testLart(self):
            self.assertNotError('add lart jabs $who')
            self.assertHelp('lart')
            self.assertResponse('lart jemfinch for being dumb',
                                '\x01ACTION jabs jemfinch for being dumb '
                                '(#1)\x01')
            self.assertResponse('lart jemfinch',
                                '\x01ACTION jabs jemfinch (#1)\x01')
            self.assertRegexp('stats lart', 'currently 1 lart')
            self.assertNotError('add lart shoots $who')
            self.assertHelp('lart 1')
            self.assertResponse('lart 1 jemfinch',
                                '\x01ACTION jabs jemfinch (#1)\x01')
            self.assertResponse('lart 2 jemfinch for being dumb',
                                '\x01ACTION shoots jemfinch for being dumb '
                                '(#2)\x01')
            self.assertNotRegexp('lart %s' % self.irc.nick, self.irc.nick)
            self.assertNotError('remove lart 1')
            self.assertRegexp('stats lart', 'currently 1 lart')
            self.assertResponse('lart jemfinch',
                                '\x01ACTION shoots jemfinch (#2)\x01')
            self.assertNotError('remove lart 2')
            self.assertRegexp('stats lart', 'currently 0')
            self.assertError('lart jemfinch')

        def testLartAndPraiseRemoveTrailingPeriods(self):
            for s in ['lart', 'praise']:
                self.assertNotError('add %s $who foo!' % s)
                self.assertAction('%s bar.' % s, 'bar foo! (#1)')

        def testMyMeReplacement(self):
            self.assertNotError('add lart jabs $who')
            self.assertNotError('add praise pets $who')
            self.assertNotError('add insult foo')
            self.assertAction('lart me', 'jabs t3st (#1)')
            self.assertAction('praise me', 'pets t3st (#1)')
            #self.assertResponse('insult me', 't3st: foo (#1)')
            self.assertAction('lart whamme', 'jabs whamme (#1)')
            self.assertAction('praise whamme', 'pets whamme (#1)')
            #self.assertResponse('insult whamme', 'whamme: foo (#1)')
            self.assertAction('lart my knee', 'jabs t3st\'s knee (#1)')
            self.assertAction('praise my knee', 'pets t3st\'s knee (#1)')
            #self.assertResponse('insult my knee', 't3st\'s knee: foo (#1)')
            self.assertAction('lart sammy the snake',
                              'jabs sammy the snake (#1)')
            self.assertAction('praise sammy the snake',
                              'pets sammy the snake (#1)')
            #self.assertResponse('insult sammy the snake',
            #                   'sammy the snake: foo (#1)')
            self.assertAction('lart me for my',
                              'jabs t3st for t3st\'s (#1)')
            self.assertAction('praise me for my',
                              'pets t3st for t3st\'s (#1)')
            self.assertAction('lart me and %s' % self.irc.nick,
                              'jabs t3st and %s (#1)' % self.irc.nick)
            self.assertAction('praise me and %s' % self.irc.nick,
                              'pets t3st and %s (#1)' % self.irc.nick)
            self.assertNotError('remove lart 1')
            self.assertNotError('remove praise 1')
            self.assertNotError('remove insult 1')

        def testExcuse(self):
            self.assertNotError('add excuse Power failure')
            self.assertResponse('excuse', 'Power failure (#1)')
            self.assertError('excuse a few random words')
            self.assertRegexp('stats excuse', r'currently 1 excuse')
            self.assertNotError('add excuse /pub/lunch')
            self.assertResponse('excuse 1', 'Power failure (#1)')
            self.assertNotError('remove excuse 1')
            self.assertRegexp('stats excuse', r'currently 1 excuse')
            self.assertResponse('excuse', '/pub/lunch (#2)')
            self.assertNotError('remove excuse 2')
            self.assertRegexp('stats excuse', r'currently 0')
            self.assertError('excuse')

        def testInsult(self):
            self.assertNotError('add insult Fatty McFatty')
            self.assertResponse('insult jemfinch',
                                'jemfinch: Fatty McFatty (#1)')
            self.assertRegexp('stats insult', r'currently 1')
            self.assertNotError('remove insult 1')
            self.assertRegexp('stats insult', 'currently 0')
            self.assertError('insult jemfinch')

        def testChannelReplies(self):
            self.assertNotError('add #tester praise pets $who')
            self.assertNotError('add praise pats $who')
            self.assertNotError('add #tester lart stabs $who')
            self.assertNotError('add lart stubs $who')
            self.assertNotError('add #tester insult nimrod')
            self.assertNotError('add insult nimwit')
            self.assertNotError('add #tester excuse He did it!')
            self.assertNotError('add excuse She did it!')
            self.assertResponse('praise jemfinch',
                                '\x01ACTION pats jemfinch (#1)\x01')
            self.assertResponse('praise #tester jemfinch',
                                '\x01ACTION pets jemfinch (#1)\x01')
            self.assertResponse('lart jemfinch',
                                '\x01ACTION stubs jemfinch (#1)\x01')
            self.assertResponse('lart #tester jemfinch',
                                '\x01ACTION stabs jemfinch (#1)\x01')
            self.assertResponse('insult jemfinch', 'jemfinch: nimwit (#1)')
            self.assertResponse('insult #tester jemfinch',
                                'jemfinch: nimrod (#1)')
            self.assertResponse('excuse', 'She did it! (#1)')
            self.assertResponse('excuse #tester', 'He did it! (#1)')

        def testPraise(self):
            self.assertNotError('add praise pets $who')
            self.assertHelp('praise')
            self.assertResponse('praise jemfinch for being him',
                                '\x01ACTION pets jemfinch for being him '
                                '(#1)\x01')
            self.assertResponse('praise jemfinch',
                                '\x01ACTION pets jemfinch (#1)\x01')
            self.assertRegexp('stats praise', r'currently 1')
            self.assertNotError('add praise gives $who a cookie')
            self.assertHelp('praise 1')
            self.assertResponse('praise 1 jemfinch',
                                '\x01ACTION pets jemfinch (#1)\x01')
            self.assertResponse('praise 2 jemfinch for being him',
                                '\x01ACTION gives jemfinch a cookie for being '
                                'him (#2)\x01')
            self.assertNotError('remove praise 1')
            self.assertRegexp('stats praise', r'currently 1')
            self.assertResponse('praise jemfinch',
                                '\x01ACTION gives jemfinch a cookie (#2)\x01')
            self.assertNotError('remove praise 2')
            self.assertRegexp('stats praise', r'currently 0')
            self.assertError('praise jemfinch')

        def testInfo(self):
            self.assertNotError('add praise $who')
            self.assertRegexp('info praise 1', r'Created by')
            self.assertNotError('remove praise 1')
            self.assertError('info fake 1')

        def testGet(self):
            self.assertError('fundb get fake 1')
            self.assertError('fundb get lart foo')
            self.assertNotError('add praise pets $who')
            self.assertResponse('fundb get praise 1', 'pets $who')
            self.assertNotError('remove praise 1')
            self.assertError('fundb get praise 1')

        def testStats(self):
            self.assertError('stats fake')
            self.assertError('stats 1')
            self.assertRegexp('stats praise', r'currently 0')
            self.assertRegexp('stats lart',   r'currently 0')
            self.assertRegexp('stats excuse', r'currently 0')
            self.assertRegexp('stats insult', r'currently 0')

        def testChange(self):
            self.assertNotError('add praise teaches $who perl')
            self.assertNotError('change praise 1 s/perl/python/')
            self.assertResponse('praise jemfinch',
                                '\x01ACTION teaches jemfinch python (#1)\x01')
            self.assertNotError('remove praise 1')

        def testConfig(self):
            self.assertNotError('add praise teaches $who perl')
            self.assertRegexp('praise jemfinch', r'\(#1\)')
            conf.supybot.plugins.FunDB.showIds.setValue(False)
            self.assertNotRegexp('praise jemfinch', r'\(#1\)')

        def testLartPraiseReasonPeriod(self):
            self.assertNotError('add lart kills $who')
            self.assertNotRegexp('lart foo for bar.', r'\.')
            self.assertNotError('add praise loves $who')
            self.assertNotRegexp('praise for for bar.', r'\.')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

