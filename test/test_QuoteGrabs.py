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

import sets

from testsupport import *

try:
    import sqlite
except ImportError:
    sqlite = None


if sqlite:
    class QuoteGrabsTestCase(ChannelPluginTestCase, PluginDocumentation):
        plugins = ('QuoteGrabs',)
        def testQuoteGrab(self):
            testPrefix = 'foo!bar@baz'
            self.assertError('grab foo')    
            # Test join/part/notice (shouldn't grab)
            self.irc.feedMsg(ircmsgs.join(self.channel, prefix=testPrefix))
            self.assertError('grab foo')
            self.irc.feedMsg(ircmsgs.part(self.channel, prefix=testPrefix))
            self.assertError('grab foo')
            # Test privmsgs
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'something',
                                             prefix=testPrefix))
            self.assertNotError('grab foo')    
            self.assertResponse('quote foo', '<foo> something')
            # Test actions
            self.irc.feedMsg(ircmsgs.action(self.channel, 'moos',
                                            prefix=testPrefix))
            self.assertNotError('grab foo')
            self.assertResponse('quote foo', '* foo moos')

        def testList(self):
            testPrefix = 'foo!bar@baz'
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                             prefix=testPrefix))
            self.assertNotError('grab foo')
            self.assertResponse('quotegrabs list foo', '#1: test')
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'a' * 80,
                                             prefix=testPrefix))
            self.assertNotError('grab foo')
            self.assertResponse('quotegrabs list foo',
                                '#1: test and #2: %s...' %\
                                ('a'*43)) # 50 - length of "#2: ..."

        def testDuplicateGrabs(self):
            testPrefix = 'foo!bar@baz'
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                             prefix=testPrefix))
            self.assertNotError('grab foo') 
            self.assertNotError('grab foo') # note:NOTanerror,stillwon'tdupe
            self.assertResponse('quotegrabs list foo', '#1: test')

        def testCaseInsensitivity(self):
            testPrefix = 'foo!bar@baz'
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                             prefix=testPrefix))
            self.assertNotError('grab FOO')
            self.assertNotError('quote foo')
            self.assertNotError('quote FoO')
            self.assertNotError('quote Foo')

        def testGet(self):
            testPrefix= 'foo!bar@baz'
            self.assertError('quotegrabs get asdf')
            self.assertError('quotegrabs get 1')
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'test',
                                             prefix=testPrefix))
            self.assertNotError('grab foo')
            self.assertRegexp('quotegrabs get 1',
                              '<foo> test \(Said by: foo!bar@baz on .*?\)')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

