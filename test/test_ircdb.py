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

import os
import unittest

import conf
import debug
import ircdb
import ircutils

class FunctionsTestCase(unittest.TestCase):
    def testIsAntiCapability(self):
        self.failIf(ircdb.isAntiCapability('foo'))
        self.failIf(ircdb.isAntiCapability('#foo.bar'))
        self.failUnless(ircdb.isAntiCapability('!foo'))
        self.failUnless(ircdb.isAntiCapability('#foo.!bar'))
        self.failUnless(ircdb.isAntiCapability('#foo.bar.!baz'))

    def testIsChannelCapability(self):
        self.failIf(ircdb.isChannelCapability('foo'))
        self.failUnless(ircdb.isChannelCapability('#foo.bar'))
        self.failUnless(ircdb.isChannelCapability('#foo.bar.baz'))

    def testMakeAntiCapability(self):
        self.assertEqual(ircdb.makeAntiCapability('foo'), '!foo')
        self.assertEqual(ircdb.makeAntiCapability('#foo.bar'), '#foo.!bar')

    def testMakeChannelCapability(self):
        self.assertEqual(ircdb.makeChannelCapability('#f', 'b'), '#f.b')
        self.assertEqual(ircdb.makeChannelCapability('#f', '!b'), '#f.!b')

    def testFromChannelCapability(self):
        self.assertEqual(ircdb.fromChannelCapability('#foo.bar'),
                         ['#foo', 'bar'])
        self.assertEqual(ircdb.fromChannelCapability('#foo.bar.baz'),
                         ['#foo.bar', 'baz'])

    def testUnAntiCapability(self):
        self.assertEqual(ircdb.unAntiCapability('!bar'), 'bar')
        self.assertEqual(ircdb.unAntiCapability('#foo.!bar'), '#foo.bar')
        self.assertEqual(ircdb.unAntiCapability('#foo.bar.!baz'),
                         '#foo.bar.baz')

    def testInvertCapability(self):
        self.assertEqual(ircdb.invertCapability('bar'), '!bar')
        self.assertEqual(ircdb.invertCapability('!bar'), 'bar')
        self.assertEqual(ircdb.invertCapability('#foo.bar'), '#foo.!bar')
        self.assertEqual(ircdb.invertCapability('#foo.!bar'), '#foo.bar')


class CapabilitySetTestCase(unittest.TestCase):
    def test(self):
        d = ircdb.CapabilitySet()
        self.assertRaises(KeyError, d.check, 'foo')
        d = ircdb.CapabilitySet(('foo',))
        self.failUnless(d.check('foo'))
        self.failIf(d.check('!foo'))
        d.add('bar')
        self.failUnless(d.check('bar'))
        self.failIf(d.check('!bar'))
        d.add('!baz')
        self.failIf(d.check('baz'))
        self.failUnless(d.check('!baz'))
        d.add('!bar')
        self.failIf(d.check('bar'))
        self.failUnless(d.check('!bar'))
        d.remove('!bar')
        self.assertRaises(KeyError, d.check, '!bar')
        self.assertRaises(KeyError, d.check, 'bar')


class UserCapabilitySetTestCase(unittest.TestCase):
    def testOwnerHasAll(self):
        d = ircdb.UserCapabilitySet(('owner',))
        self.failIf(d.check('!foo'))
        self.failUnless(d.check('foo'))

    def testOwnerIsAlwaysPresent(self):
        d = ircdb.UserCapabilitySet()
        self.failUnless('owner' in d)
        self.failUnless('!owner' in d)
        self.failIf(d.check('owner'))
        d.add('owner')
        self.failUnless(d.check('owner'))



class CapabilitySetTestCase(unittest.TestCase):
    def testContains(self):
        s = ircdb.CapabilitySet()
        self.failIf('foo' in s)
        self.failIf('!foo' in s)
        s.add('foo')
        self.failUnless('foo' in s)
        self.failUnless('!foo' in s)
        s.remove('foo')
        self.failIf('foo' in s)
        self.failIf('!foo' in s)
        s.add('!foo')
        self.failUnless('foo' in s)
        self.failUnless('!foo' in s)

    def testCheck(self):
        s = ircdb.CapabilitySet()
        self.assertRaises(KeyError, s.check, 'foo')
        self.assertRaises(KeyError, s.check, '!foo')
        s.add('foo')
        self.failUnless(s.check('foo'))
        self.failIf(s.check('!foo'))
        s.remove('foo')
        self.assertRaises(KeyError, s.check, 'foo')
        self.assertRaises(KeyError, s.check, '!foo')
        s.add('!foo')
        self.failIf(s.check('foo'))
        self.failUnless(s.check('!foo'))
        s.remove('!foo')
        self.assertRaises(KeyError, s.check, 'foo')
        self.assertRaises(KeyError, s.check, '!foo')

    def testAdd(self):
        s = ircdb.CapabilitySet()
        s.add('foo')
        s.add('!foo')
        self.failIf(s.check('foo'))
        self.failUnless(s.check('!foo'))
        s.add('foo')
        self.failUnless(s.check('foo'))
        self.failIf(s.check('!foo'))


class UserCapabilitySetTestCase(unittest.TestCase):
    def testOwner(self):
        s = ircdb.UserCapabilitySet()
        s.add('owner')
        self.failUnless('foo' in s)
        self.failUnless('!foo' in s)
        self.failUnless(s.check('owner'))
        self.failIf(s.check('!owner'))
        self.failIf(s.check('!foo'))
        self.failUnless(s.check('foo'))


class IrcUserTestCase(unittest.TestCase):
    def testCapabilities(self):
        u = ircdb.IrcUser()
        u.addCapability('foo')
        self.failUnless(u.checkCapability('foo'))
        self.failIf(u.checkCapability('!foo'))
        u.addCapability('!bar')
        self.failUnless(u.checkCapability('!bar'))
        self.failIf(u.checkCapability('bar'))
        u.removeCapability('foo')
        u.removeCapability('!bar')
        self.assertRaises(KeyError, u.checkCapability, 'foo')
        self.assertRaises(KeyError, u.checkCapability, '!bar')

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

class UsersDBTestCase(unittest.TestCase):
    filename = 'UsersDBTestCase.conf'
    def setUp(self):
        try:
            os.remove(self.filename)
        except:
            pass
        self.users = ircdb.UsersDB(self.filename)

    def testGetSetDelUser(self):
        self.assertRaises(KeyError, self.users.getUser, 'foo')
        self.assertRaises(KeyError, self.users.getUser, 'foo!bar@baz')
        (id, u) = self.users.newUser()
        hostmask = 'foo!bar@baz'
        banmask = ircutils.banmask(hostmask)
        u.addHostmask(banmask)
        u.name = 'foo'
        self.users.setUser(id, u)
        self.assertEqual(self.users.getUser('foo'), u)
        self.assertEqual(self.users.getUser('FOO'), u)
        self.assertEqual(self.users.getUser(hostmask), u)
        self.assertEqual(self.users.getUser(banmask), u)
        # The UsersDB shouldn't allow users to be added whose hostmasks
        # match another user's already in the database.
        (id, u2) = self.users.newUser()
        u2.addHostmask('*!*@*')
        self.assertRaises(ValueError, self.users.setUser, id, u2)


class CheckCapabilityTestCase(unittest.TestCase):
    filename = 'CheckCapabilityTestCase.conf'
    owner = 'owner!owner@owner'
    nothing = 'nothing!nothing@nothing'
    justfoo = 'justfoo!justfoo@justfoo'
    antifoo = 'antifoo!antifoo@antifoo'
    justchanfoo = 'justchanfoo!justchanfoo@justchanfoo'
    antichanfoo = 'antichanfoo!antichanfoo@antichanfoo'
    channel = '#channel'
    cap = 'foo'
    anticap = ircdb.makeAntiCapability(cap)
    chancap = ircdb.makeChannelCapability(channel, cap)
    antichancap = ircdb.makeAntiCapability(chancap)
    chanop = ircdb.makeChannelCapability(channel, 'op')
    channelnothing = ircdb.IrcChannel()
    channelcap = ircdb.IrcChannel()
    channelcap.addCapability(cap)
    channelanticap = ircdb.IrcChannel()
    channelanticap.addCapability(anticap)
    def setUp(self):
        try:
            os.remove(self.filename)
        except:
            pass
        self.users = ircdb.UsersDB(self.filename)
        self.channels = ircdb.ChannelsDictionary(self.filename)
        (id, owner) = self.users.newUser()
        owner.name = 'owner'
        owner.addCapability('owner')
        owner.addHostmask(self.owner)
        self.users.setUser(id, owner)
        (id, nothing) = self.users.newUser()
        nothing.name = 'nothing'
        nothing.addHostmask(self.nothing)
        self.users.setUser(id, nothing)
        (id, justfoo) = self.users.newUser()
        justfoo.name = 'justfoo'
        justfoo.addCapability(self.cap)
        justfoo.addHostmask(self.justfoo)
        self.users.setUser(id, justfoo)
        (id, antifoo) = self.users.newUser()
        antifoo.name = 'antifoo'
        antifoo.addCapability(self.anticap)
        antifoo.addHostmask(self.antifoo)
        self.users.setUser(id, antifoo)
        (id, justchanfoo) = self.users.newUser()
        justchanfoo.name = 'justchanfoo'
        justchanfoo.addCapability(self.chancap)
        justchanfoo.addHostmask(self.justchanfoo)
        self.users.setUser(id, justchanfoo)
        (id, antichanfoo) = self.users.newUser()
        antichanfoo.name = 'antichanfoo'
        antichanfoo.addCapability(self.antichancap)
        antichanfoo.addHostmask(self.antichanfoo)
        self.users.setUser(id, antichanfoo)
        channel = ircdb.IrcChannel()
        self.channels.setChannel(self.channel, channel)

    def checkCapability(self, hostmask, capability):
        return ircdb.checkCapability(hostmask, capability,
                                     self.users, self.channels)

    def testOwner(self):
        self.failUnless(self.checkCapability(self.owner, self.cap))
        self.failIf(self.checkCapability(self.owner, self.anticap))
        self.failUnless(self.checkCapability(self.owner, self.chancap))
        self.failIf(self.checkCapability(self.owner, self.antichancap))
        self.channels.setChannel(self.channel, self.channelanticap)
        self.failUnless(self.checkCapability(self.owner, self.cap))
        self.failIf(self.checkCapability(self.owner, self.anticap))

    def testNothingAgainstChannel(self):
        self.channels.setChannel(self.channel, self.channelnothing)
        self.assertEqual(self.checkCapability(self.nothing, self.chancap),
                         self.channelnothing.defaultAllow)
        self.channelnothing.defaultAllow = not self.channelnothing.defaultAllow
        self.channels.setChannel(self.channel, self.channelnothing)
        self.assertEqual(self.checkCapability(self.nothing, self.chancap),
                         self.channelnothing.defaultAllow)
        self.channels.setChannel(self.channel, self.channelcap)
        self.failUnless(self.checkCapability(self.nothing, self.chancap))
        self.failIf(self.checkCapability(self.nothing, self.antichancap))
        self.channels.setChannel(self.channel, self.channelanticap)
        self.failIf(self.checkCapability(self.nothing, self.chancap))
        self.failUnless(self.checkCapability(self.nothing, self.antichancap))

    def testNothing(self):
        self.assertEqual(self.checkCapability(self.nothing, self.cap),
                         conf.defaultAllow)
        self.assertEqual(self.checkCapability(self.nothing, self.anticap),
                         not conf.defaultAllow)

    def testJustFoo(self):
        self.failUnless(self.checkCapability(self.justfoo, self.cap))
        self.failIf(self.checkCapability(self.justfoo, self.anticap))

    def testAntiFoo(self):
        self.failUnless(self.checkCapability(self.antifoo, self.anticap))
        self.failIf(self.checkCapability(self.antifoo, self.cap))

    def testJustChanFoo(self):
        self.channels.setChannel(self.channel, self.channelnothing)
        self.failUnless(self.checkCapability(self.justchanfoo, self.chancap))
        self.failIf(self.checkCapability(self.justchanfoo, self.antichancap))
        self.channelnothing.defaultAllow = not self.channelnothing.defaultAllow
        self.failUnless(self.checkCapability(self.justchanfoo, self.chancap))
        self.failIf(self.checkCapability(self.justchanfoo, self.antichancap))
        self.channels.setChannel(self.channel, self.channelanticap)
        self.failUnless(self.checkCapability(self.justchanfoo, self.chancap))
        self.failIf(self.checkCapability(self.justchanfoo, self.antichancap))

    def testChanOpCountsAsEverything(self):
        self.channels.setChannel(self.channel, self.channelanticap)
        id = self.users.getUserId('nothing')
        u = self.users.getUser(id)
        u.addCapability(self.chanop)
        self.users.setUser(id, u)
        self.failUnless(self.checkCapability(self.nothing, self.chancap))
        self.channels.setChannel(self.channel, self.channelnothing)
        self.failUnless(self.checkCapability(self.nothing, self.chancap))
        self.channelnothing.defaultAllow = not self.channelnothing.defaultAllow
        self.failUnless(self.checkCapability(self.nothing, self.chancap))

    def testAntiChanFoo(self):
        self.channels.setChannel(self.channel, self.channelnothing)
        self.failIf(self.checkCapability(self.antichanfoo, self.chancap))
        self.failUnless(self.checkCapability(self.antichanfoo,
                                             self.antichancap))


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

