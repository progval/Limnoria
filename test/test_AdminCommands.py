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

class AdminCommandsTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('AdminCommands', 'MiscCommands')
    def testSetprefixchar(self):
        self.assertNotError('setprefixchar $')
        self.assertResponse('getprefixchar', "'$'")

    def testAddcapability(self):
        self.assertError('addcapability sdlkfj foo')
        (id, u) = ircdb.users.newUser()
        u.name = 'foo'
        ircdb.users.setUser(id, u)
        self.assertError('removecapability foo bar')
        self.assertNotRegexp('removecapability foo bar', 'find')

    def testRemoveCapability(self):
        self.assertError('removecapability alsdfkjasd foo')

    def testDisable(self):
        self.assertError('disable enable')
        self.assertError('disable identify')

    def testEnable(self):
        self.assertError('enable enable')

    def testJoin(self):
        m = self.getMsg('join #foo')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo')
        m = self.getMsg('join #foo #bar')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo,#bar')
        m = self.getMsg('join #foo,key')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo')
        self.assertEqual(m.args[1], 'key')
        m = self.getMsg('join #bar #foo,key')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo,#bar')
        self.assertEqual(m.args[1], 'key')
        m = self.getMsg('join #bar,key1 #foo,key2')
        self.assertEqual(m.command, 'JOIN')
        self.assertEqual(m.args[0], '#foo,#bar')
        self.assertEqual(m.args[1], 'key2,key1')

    def testPart(self):
        self.assertError('part #foo')
        _ = self.getMsg('join #foo') # get the JOIN.
        _ = self.getMsg(' ') # get the WHO.
        self.assertError('part #foo #bar')
        m = self.getMsg('part #foo')
        self.assertEqual(m.command, 'PART')
        self.assertEqual(m.args[0], '#foo')
        _ = self.getMsg('join #foo #bar') # get the JOIN.
        _ = self.getMsg(' ') # get the WHO.
        # vvv(won't send this because there was no server response.)
        # _ = self.getMsg(' ') # get the WH0.
        m = self.getMsg('part #foo #bar')
        self.assertEqual(m.command, 'PART')
        self.assertEqual(m.args[0], '#foo,#bar')

    def testNick(self):
        m = self.getMsg('nick foobar')
        self.assertEqual(m.command, 'NICK')
        self.assertEqual(m.args[0], 'foobar')
        


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

