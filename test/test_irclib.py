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

import pickle

import conf
import debug
import irclib
import ircmsgs

class IrcMsgQueueTestCase(unittest.TestCase):
    mode = ircmsgs.op('#foo', 'jemfinch')
    msg = ircmsgs.privmsg('#foo', 'hey, you')
    msgs = [ircmsgs.privmsg('#foo', str(i)) for i in range(10)]
    kick = ircmsgs.kick('#foo', 'PeterB')
    pong = ircmsgs.pong('123')
    ping = ircmsgs.ping('123')
    notice = ircmsgs.notice('jemfinch', 'supybot here')

    def testEmpty(self):
        q = irclib.IrcMsgQueue()
        self.failIf(q)

    def testEnqueueDequeue(self):
        q = irclib.IrcMsgQueue()
        q.enqueue(self.msg)
        self.failUnless(q)
        self.assertEqual(self.msg, q.dequeue())
        self.failIf(q)
        q.enqueue(self.msg)
        q.enqueue(self.notice)
        self.assertEqual(self.msg, q.dequeue())
        self.assertEqual(self.notice, q.dequeue())
        for msg in self.msgs:
            q.enqueue(msg)
        for msg in self.msgs:
            self.assertEqual(msg, q.dequeue())

    def testPrioritizing(self):
        q = irclib.IrcMsgQueue()
        q.enqueue(self.msg)
        q.enqueue(self.mode)
        self.assertEqual(self.mode, q.dequeue())
        self.assertEqual(self.msg, q.dequeue())
        q.enqueue(self.msg)
        q.enqueue(self.kick)
        self.assertEqual(self.kick, q.dequeue())
        q.enqueue(self.ping)
        q.enqueue(self.msg)
        self.assertEqual(self.msg, q.dequeue())
        self.assertEqual(self.ping, q.dequeue())
        q.enqueue(self.ping)
        q.enqueue(self.msgs[0])
        q.enqueue(self.kick)
        q.enqueue(self.msgs[1])
        q.enqueue(self.mode)
        self.assertEqual(self.kick, q.dequeue())
        self.assertEqual(self.mode, q.dequeue())
        self.assertEqual(self.msgs[0], q.dequeue())
        self.assertEqual(self.msgs[1], q.dequeue())
        self.assertEqual(self.ping, q.dequeue())

    def testNoIdenticals(self):
        q = irclib.IrcMsgQueue()
        q.enqueue(self.msg)
        q.enqueue(self.msg)
        self.assertEqual(self.msg, q.dequeue())
        self.failIf(q)


class ChannelTestCase(unittest.TestCase):
    def testPickleCopy(self):
        c = irclib.Channel()
        for name in c.__slots__:
        c1 = pickle.loads(pickle.dumps(c))
        for name in c1.__slots__:
        self.assertEqual(pickle.loads(pickle.dumps(c)), c)

    def testAddUser(self):
        c = irclib.Channel()
        c.addUser('foo')
        self.failUnless('foo' in c.users)
        self.failIf('foo' in c.ops)
        self.failIf('foo' in c.voices)
        self.failIf('foo' in c.halfops)
        c.addUser('+bar')
        self.failUnless('bar' in c.users)
        self.failUnless('bar' in c.voices)
        self.failIf('bar' in c.ops)
        self.failIf('bar' in c.halfops)
        c.addUser('%baz')
        self.failUnless('baz' in c.users)
        self.failUnless('baz' in c.halfops)
        self.failIf('baz' in c.voices)
        self.failIf('baz' in c.ops)
        c.addUser('@quuz')
        self.failUnless('quuz' in c.users)
        self.failUnless('quuz' in c.ops)
        self.failIf('quuz' in c.halfops)
        self.failIf('quuz' in c.voices)


class IrcStateTestCase(unittest.TestCase):
    class FakeIrc:
        nick = 'nick'
    irc = FakeIrc()
    def testHistory(self):
        oldconfmaxhistory = conf.maxHistory
        conf.maxHistory = 10
        state = irclib.IrcState()
        for msg in msgs:
            try:
                state.addMsg(self.irc, msg)
            except Exception:
                pass
            self.failIf(len(state.history) > conf.maxHistory)
        self.assertEqual(len(state.history), conf.maxHistory)
        self.assertEqual(list(state.history), msgs[len(msgs)-conf.maxHistory:])
        conf.maxHistory = oldconfmaxhistory

    def testPickleCopy(self):
        state = irclib.IrcState()
        self.assertEqual(state, pickle.loads(pickle.dumps(state)))
        for msg in msgs:
            try:
                state.addMsg(self.irc, msg)
            except Exception:
                pass
        self.assertEqual(state, pickle.loads(pickle.dumps(state)))

    def testEq(self):
        state1 = irclib.IrcState()
        state2 = irclib.IrcState()
        self.assertEqual(state1, state2)
        for msg in msgs:
            try:
                state1.addMsg(self.irc, msg)
                state2.addMsg(self.irc, msg)
                self.assertEqual(state1, state2)
            except Exception:
                pass


    """
    def testChannels(self):
        channel =
        state = irclib.IrcState()
        state.addMsg(self.irc, ircmsgs.join('#foo'))
    """

class IrcTestCase(unittest.TestCase):
    irc = irclib.Irc('nick')
    def testPingResponse(self):
        self.irc.feedMsg(ircmsgs.ping('123'))
        self.assertEqual(ircmsgs.pong('123'), self.irc.takeMsg())

    def test433Response(self):
        self.irc.feedMsg(ircmsgs.IrcMsg('433 * %s :Nickname already in use.' %\
                                        self.irc.nick))
        msg = self.irc.takeMsg()
        self.failUnless(msg.command == 'NICK' and msg.args[0] != self.irc.nick)

    def testReset(self):
        for msg in msgs:
            try:
                self.irc.feedMsg(msg)
            except:
                pass
        self.irc.reset()
        self.failIf(self.irc.fastqueue)
        self.failIf(self.irc.state.history)
        self.failIf(self.irc.state.channels)
        self.failIf(self.irc.outstandingPing)
        self.assertEqual(self.irc._nickmods, conf.nickmods)

    def testHistory(self):
        self.irc.reset()
        msg1 = ircmsgs.IrcMsg('PRIVMSG #linux :foo bar baz!')
        self.irc.feedMsg(msg1)
        self.assertEqual(self.irc.state.history[0], msg1)
        msg2 = ircmsgs.IrcMsg('JOIN #sourcereview')
        self.irc.feedMsg(msg2)
        self.assertEqual(list(self.irc.state.history), [msg1, msg2])


class IrcCallbackTestCase(unittest.TestCase):
    class FakeIrc:
        pass
    irc = FakeIrc()
    def testName(self):
        class UnnamedIrcCallback(irclib.IrcCallback):
            pass
        unnamed = UnnamedIrcCallback()

        class NamedIrcCallback(irclib.IrcCallback):
            myName = 'foobar'
            def name(self):
                return self.myName
        named = NamedIrcCallback()
        self.assertEqual(unnamed.name(), unnamed.__class__.__name__)
        self.assertEqual(named.name(), named.myName)

    def testDoCommand(self):
        def makeCommand(msg):
            return 'do' + msg.command.capitalize()
        class DoCommandCatcher(irclib.IrcCallback):
            def __init__(self):
                self.L = []
            def __getattr__(self, attr):
                self.L.append(attr)
                return lambda *args: None
        doCommandCatcher = DoCommandCatcher()
        for msg in msgs:
            doCommandCatcher(self.irc, msg)
        commands = map(makeCommand, msgs)
        self.assertEqual(doCommandCatcher.L, commands)

    def testFirstCommands(self):
        oldconfthrottle = conf.throttleTime
        conf.throttleTime = 0
        nick = 'nick'
        user = 'user any user'
        password = 'password'
        expected = [ircmsgs.nick(nick), ircmsgs.user(nick, user)]
        irc = irclib.Irc(nick, user)
        msgs = [irc.takeMsg()]
        while msgs[-1] != None:
            msgs.append(irc.takeMsg())
        msgs.pop()
        self.assertEqual(msgs, expected)
        irc = irclib.Irc(nick, user, password=password)
        msgs = [irc.takeMsg()]
        while msgs[-1] != None:
            msgs.append(irc.takeMsg())
        msgs.pop()
        expected.insert(0, ircmsgs.password(password))
        self.assertEqual(msgs, expected)
        conf.throttleTime = oldconfthrottle

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

