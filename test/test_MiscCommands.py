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

class MiscCommandsTestCase(ChannelPluginTestCase, PluginDocumentation):
    plugins = ('MiscCommands', 'Utilities', 'ChannelDB', 'Ctcp')
    def testReplyWhenNotCommand(self):
        try:
            conf.replyWhenNotCommand = True
            self.prefix = 'somethingElse!user@host.domain.tld'
            self.assertRegexp('foo bar baz', 'not.*command')
            self.assertRegexp('foo | bar | baz', 'not.*commands')
            self.assertRegexp('baz [foo] [bar]', 'not.*commands')
        finally:
            conf.replyWhenNotCommand = False

    def testNotReplyWhenRegexpsMatch(self):
        try:
            conf.replyWhenNotCommand = True
            self.prefix = 'somethingElse!user@host.domain.tld'
            self.assertNoResponse('@coffee++', 2)
        finally:
            conf.replyWhenNotCommand = False

    def testNotReplyWhenNotCanonicalName(self):
        try:
            conf.replyWhenNotCommand = True
            self.prefix = 'somethingElse!user@host.domain.tld'
            self.assertNotRegexp('STrLeN foobar', 'command')
            self.assertResponse('StRlEn foobar', '6')
        finally:
            conf.repylWhenNotCommand = False
        
    def testHelp(self):
        self.assertNotError('help list')
        self.assertNotError('help help')

    def testMorehelp(self):
        self.assertNotError('morehelp list')
        self.assertNotError('morehelp morehelp')

    def testList(self):
        self.assertNotError('list MiscCommands')
        self.assertNotError('list misccommands')
        self.assertNotError('list')
        # If Ctcp changes to public, these tests will break.  So if
        # the next assert fails, change the plugin we test for public/private
        # to some other non-public plugin.
        name = 'Ctcp'
        self.failIf(self.irc.getCallback(name).public)
        self.assertNotRegexp('list', name)
        self.assertRegexp('list --private', name)

    def testBug(self):
        self.assertNotError('bug')

    def testVersion(self):
        self.assertNotError('version')

    def testSource(self):
        self.assertNotError('source')

    def testLogfilesize(self):
        self.assertNotError('logfilesize')

    def testGetprefixchar(self):
        self.assertNotError('getprefixchar')

    def testPlugin(self):
        self.assertResponse('plugin plugin', 'MiscCommands')

    def testTell(self):
        m = self.getMsg('tell foo [plugin tell]')
        self.failUnless(m.args[0] == 'foo')
        self.failUnless('MiscCommands' in m.args[1])
        m = self.getMsg('tell #foo [plugin tell]')
        self.failUnless(m.args[0] == '#foo')
        self.failUnless('MiscCommands' in m.args[1])

    def testLast(self):
        self.feedMsg('foo bar baz')
        self.assertResponse('last', 'foo bar baz')
        self.assertRegexp('last', 'last')
        self.assertResponse('last --with foo', 'foo bar baz')
        self.assertRegexp('last --regexp m/\s+/', 'last --with foo')
        self.assertResponse('last --regexp m/bar/', 'foo bar baz')

    def testMore(self):
        self.assertRegexp('echo %s' % ('abc'*300), 'more')
        self.assertRegexp('more', 'more')
        self.assertNotRegexp('more', 'more')
        


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

