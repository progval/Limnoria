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

import unittest

import ircdb
import ircutils

class IrcUserTestCase(unittest.TestCase):
    def testCapabilities(self):
        u = ircdb.IrcUser()
        u.addCapability('foo')
        u.addCapability('!bar')
        self.failIf(u.checkCapability('bar'))
        self.failUnless(u.checkCapability('!bar'))
        self.failUnless(u.checkCapability('foo'))
        self.failIf(u.checkCapability('!foo'))
        u.removeCapability('foo')
        u.removeCapability('!bar')
        self.failIf(u.checkCapability('!bar'))
        self.failIf(u.checkCapability('foo'))

    def testOwner(self):
        u = ircdb.IrcUser()
        u.addCapability('owner')
        self.failUnless(u.checkCapability('foo'))
        self.failIf(u.checkCapability('!foo'))
        
    def testInitCapabilities(self):
        u = ircdb.IrcUser(capabilities=['foo'])
        self.failUnless(u.checkCapability('foo'))

    def testPassword(self):
        u = ircdb.IrcUser()
        u.setPassword('foobar')
        self.failUnless(u.checkPassword('foobar'))
        self.failIf(u.checkPassword('somethingelse'))

    def testHostmasks(self):
        prefix = 'foo!bar@baz'
        hostmasks = ['*!bar@baz', 'foo!*@*']
        u = ircdb.IrcUser()
        self.failIf(u.checkHostmask(prefix))
        for hostmask in hostmasks:
            u.addHostmask(hostmask)
        self.failUnless(u.checkHostmask(prefix))

    def testAuth(self):
        prefix = 'foo!bar@baz'
        u = ircdb.IrcUser()
        u.setAuth(prefix)
        self.failUnless(u.checkAuth(prefix))
        u.unsetAuth()
        self.failIf(u.checkAuth(prefix))

    def testIgnore(self):
        u = ircdb.IrcUser(ignore=True)
        self.failIf(u.checkCapability('foo'))
        self.failUnless(u.checkCapability('!foo'))
        

class IrcChannelTestCase(unittest.TestCase):
    def testInit(self):
        c = ircdb.IrcChannel()
        self.failIf(c.checkCapability('op'))
        self.failIf(c.checkCapability('voice'))
        self.failIf(c.checkCapability('halfop'))
        self.failIf(c.checkCapability('protected'))

    def testCapabilities(self):
        c = ircdb.IrcChannel(defaultAllow=False)
        self.failIf(c.checkCapability('foo'))
        c.addCapability('foo')
        self.failUnless(c.checkCapability('foo'))
        c.removeCapability('foo')
        self.failIf(c.checkCapability('foo'))

    def testDefaultCapability(self):
        c = ircdb.IrcChannel()
        c.setDefaultCapability(False)
        self.failIf(c.checkCapability('foo'))
        self.failUnless(c.checkCapability('!foo'))
        c.setDefaultCapability(True)
        self.failUnless(c.checkCapability('foo'))
        self.failIf(c.checkCapability('!foo'))

    def testLobotomized(self):
        c = ircdb.IrcChannel(lobotomized=True)
        self.failUnless(c.checkIgnored(''))
        
    def testIgnored(self):
        prefix = 'foo!bar@baz'
        banmask = ircutils.banmask(prefix)
        c = ircdb.IrcChannel()
        self.failIf(c.checkIgnored(prefix))
        c.addIgnore(banmask)
        self.failUnless(c.checkIgnored(prefix))
        c.removeIgnore(banmask)
        self.failIf(c.checkIgnored(prefix))
        c.addBan(banmask)
        self.failUnless(c.checkIgnored(prefix))
        c.removeBan(banmask)
        self.failIf(c.checkIgnored(prefix))


class FunctionsTestCase(unittest.TestCase):
    def testIsAntiCapability(self):
        self.failIf(ircdb.isAntiCapability('foo'))
        self.failIf(ircdb.isAntiCapability('#foo.bar'))
        self.failUnless(ircdb.isAntiCapability('!foo'))
        self.failUnless(ircdb.isAntiCapability('#foo.!bar'))

    def testIsChannelCapability(self):
        self.failIf(ircdb.isChannelCapability('foo'))
        self.failUnless(ircdb.isChannelCapability('#foo.bar'))

    def testMakeAntiCapability(self):
        self.assertEqual(ircdb.makeAntiCapability('foo'), '!foo')
        self.assertEqual(ircdb.makeAntiCapability('#foo.bar'), '#foo.!bar')
