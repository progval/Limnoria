#!/usr/bin/env python
# -*- coding:utf-8 -*-

###
# Copyright (c) 2003, Stéphan Kochen
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

import utils
import ircdb

try:
    import sqlite
except ImportError:
    sqlite = None

if sqlite is not None:
    class PollTestCase(ChannelPluginTestCase, PluginDocumentation):
        plugins = ('Poll', 'User')
        def setUp(self):
            ChannelPluginTestCase.setUp(self)
            self.prefix = 'foo!bar@baz'
            self.nick = 'foo'
            self.irc.feedMsg(ircmsgs.privmsg(self.irc.nick,
                                             'register foo bar',
                                             prefix=self.prefix))
            _ = self.irc.takeMsg()

        def testOpen(self):
            self.assertRegexp('poll open Foo?', '(poll #1)')

        def testClose(self):
            self.assertRegexp('poll open Foo?', '(poll #1)')
            self.assertNotError('poll close 1')
            self.assertError('poll close blah')
            self.assertError('poll close 2')

        def testAdd(self):
            self.assertNotError('poll open Foo?')
            self.assertNotError('poll add 1 moo')
            self.assertError('poll add 2 moo')

        def testVote(self):
            self.assertNotError('poll open Foo?')
            self.assertNotError('poll add 1 moo')
            self.assertNotError('poll vote 1 1')
            self.assertError('poll vote 1 2')
            self.assertError('poll vote blah Yes')
            self.assertError('poll vote 2 blah')

        def testResults(self):
            self.assertNotError('poll open Foo?')
            self.assertNotError('poll add 1 moo')
            self.assertNotError('poll vote 1 1')
            self.assertError('poll results blah')
            self.assertRegexp('poll results 1', 'moo: 1')

        def testList(self):
            self.assertNotError('poll open Foo?')
            self.assertRegexp('poll list', '#1: \'Foo\?\'')
            self.assertNotError('poll open Foo 2?')
            self.assertRegexp('poll list', '#1: \'Foo\?\'.*#2: \'Foo 2\?\'')

        def testOptions(self):
            self.assertNotError('poll open Foo?')
            self.assertNotError('poll add 1 moo')
            self.assertNotError('poll add 1 bar')
            self.assertNotError('poll add 1 baz')
            self.assertRegexp('poll options 1', 'moo.*bar.*baz')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
