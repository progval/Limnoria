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

import conf
import Owner

class OwnerTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('Utilities', 'Relay', 'Network', 'Admin', 'Channel')
    def testDefaultPlugin(self):
        self.assertError('whois osu.edu')
        self.assertNotError('defaultplugin whois network')
        self.assertNotError('whois osu.edu')
        self.assertNotError('defaultplugin whois')
        self.assertError('whois osu.edu')
        self.assertError('defaultplugin asdlfkjasdflkjsad Owner')
        
    def testEval(self):
        try:
            originalConfAllowEval = conf.allowEval
            conf.allowEval = True
            self.assertNotError('eval 100')
            s = "[irc.__class__ for irc in " \
                "irc.getCallback('Relay').ircstates.keys()]" 
            self.assertNotRegexp('eval ' + s, '^SyntaxError')
            conf.allowEval = False
            self.assertError('eval 100')
        finally:
            conf.allowEval = originalConfAllowEval

    def testSrcAmbiguity(self):
        self.assertError('addcapability foo bar')

    def testExec(self):
        try:
            originalConfAllowEval = conf.allowEval
            conf.allowEval = True
            self.assertNotError('exec conf.foo = True')
            self.failUnless(conf.foo)
            del conf.foo
            conf.allowEval = False
            self.assertError('exec conf.foo = True')
        finally:
            conf.allowEval = originalConfAllowEval

    def testSettrace(self):
        self.assertNotError('settrace')
        self.assertNotError('unsettrace')

    def testIrcquote(self):
        self.assertResponse('ircquote PRIVMSG %s :foo' % self.irc.nick, 'foo')

    def testFlush(self):
        self.assertNotError('flush')

    def testUpkeep(self):
        self.assertNotError('upkeep')

    def testSetUnset(self):
        self.assertNotError('set foo bar')
        self.failUnless(world.tempvars['foo'] == 'bar')
        self.assertNotError('unset foo')
        self.failIf('foo' in world.tempvars)
        self.assertError('unset foo')

    def testLoad(self):
        self.assertError('load Owner')
        self.assertError('load owner')
        self.assertNotError('load Alias')
        self.assertNotError('list Owner')

    def testReload(self):
        self.assertError('reload Alias')
        self.assertNotError('load Alias')
        self.assertNotError('reload ALIAS')
        self.assertNotError('reload ALIAS')

    def testUnload(self):
        self.assertError('unload Foobar')
        self.assertNotError('load Alias')
        self.assertNotError('unload Alias')
        self.assertError('unload Alias')
        self.assertNotError('load ALIAS')
        self.assertNotError('unload ALIAS')

    def testSetconf(self):
        self.assertRegexp('setconf', 'confDir')
        self.assertNotRegexp('setconf', 'allowEval')
        self.assertResponse('setconf confDir',
                            'confDir is a string (%s).' % conf.confDir)
        self.assertError('setconf whackyConfOption')
        try:
            originalConfAllowEval = conf.allowEval
            conf.allowEval = False
            self.assertError('setconf alsdkfj 100')
            self.assertError('setconf poll "foo"')
            try:
                originalReplySuccess = conf.replySuccess
                self.assertResponse('setconf replySuccess foo', 'foo')
                self.assertResponse('setconf replySuccess "foo"', 'foo')
                self.assertResponse('setconf replySuccess \'foo\'', 'foo')
            finally:
                conf.replySuccess = originalReplySuccess
            try:
                originalReplyWhenNotCommand = conf.replyWhenNotCommand
                self.assertNotError('setconf replyWhenNotCommand True')
                self.failUnless(conf.replyWhenNotCommand)
                self.assertNotError('setconf replyWhenNotCommand False')
                self.failIf(conf.replyWhenNotCommand)
                self.assertNotError('setconf replyWhenNotCommand true')
                self.failUnless(conf.replyWhenNotCommand)
                self.assertNotError('setconf replyWhenNotCommand false')
                self.failIf(conf.replyWhenNotCommand)
                self.assertNotError('setconf replyWhenNotCommand 1')
                self.failUnless(conf.replyWhenNotCommand)
                self.assertNotError('setconf replyWhenNotCommand 0')
                self.failIf(conf.replyWhenNotCommand)
            finally:
                conf.replyWhenNotCommand = originalReplyWhenNotCommand
        finally:
            conf.allowEval = originalConfAllowEval


class FunctionsTestCase(unittest.TestCase):
    def testLoadPluginModule(self):
        self.assertRaises(ImportError, Owner.loadPluginModule, 'asldj')
        self.failUnless(Owner.loadPluginModule('Owner'))
        self.failUnless(Owner.loadPluginModule('owner'))


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

