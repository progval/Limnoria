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
    class PollTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('Poll', 'User')
        def testNew(self):
            #self.assertError('poll new Is this a question?')
            self.prefix = 'foo!bar@baz'
            self.assertNotError('register foo bar')
            self.assertRegexp('poll new Is this a question?', '(poll #1)')
            self.assertNotError('poll vote 1 Yes')
            self.assertError('poll vote 1 Yes')
            self.assertNotError('poll vote 1 No')
            self.assertError('poll vote 1 No')
            self.prefix = 'not!me@anymore'
            self.assertError('poll vote 1 Yes')
            self.prefix = 'foo!bar@baz'
            self.assertNotError('poll close 1')
            self.assertError('poll vote 1 Yes')
            self.assertNotError('poll open 1')
            self.assertNotError('poll vote 1 Yes')

        def testOpen(self):
            self.assertNotError('poll open 1')
            self.assertError('poll open blah')

        def testClose(self):
            self.assertNotError('poll close 1')
            self.assertError('poll close blah')

        def testVote(self):
            self.assertHelp('poll vote 1 blah')
            self.assertError('poll vote blah Yes')

        def testResults(self):
            self.assertError('poll results blah')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
