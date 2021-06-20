##
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import copy
import pickle
import textwrap
import unittest.mock

from supybot.test import *

import supybot.conf as conf
import supybot.irclib as irclib
import supybot.drivers as drivers
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils

# The test framework used to provide these, but not it doesn't.  We'll add
# messages to as we find bugs (if indeed we find bugs).
msgs = []
rawmsgs = []


class CapNegMixin:
    """Utilities for handling the capability negotiation."""

    def startCapNegociation(self, caps='sasl'):
        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertTrue(m.args == ('LS', '302'), 'Expected CAP LS 302, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'NICK', 'Expected NICK, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'USER', 'Expected USER, got %r.' % m)

        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', caps)))

        if caps:
            m = self.irc.takeMsg()
            self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
            self.assertEqual(m.args[0], 'REQ', m)
            self.assertEqual(m.args[1], 'sasl')

            self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
                args=('*', 'ACK', 'sasl')))

    def endCapNegociation(self):
        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args, ('END',), m)


class IrcCommandDispatcherTestCase(SupyTestCase):
    class DispatchedClass(irclib.IrcCommandDispatcher):
        def doPrivmsg():
            pass
        def doCap():
            pass
        def doFail():
            pass

    class DispatchedClassSub(irclib.IrcCommandDispatcher):
        def doPrivmsg():
            pass
        def doPrivmsgFoo():
            pass
        def doCapLs():
            pass
        def doFailFoo():
            pass

    def testCommandDispatch(self):
        dispatcher = self.DispatchedClass()
        self.assertEqual(
            dispatcher.dispatchCommand('privmsg', ['foo']),
            dispatcher.doPrivmsg)
        self.assertEqual(
            dispatcher.dispatchCommand('cap', ['*', 'ls']),
            dispatcher.doCap)
        self.assertEqual(
            dispatcher.dispatchCommand('fail', ['foo', 'bar']),
            dispatcher.doFail)
        self.assertEqual(
            dispatcher.dispatchCommand('foobar', ['*', 'ls']),
            None)

    def testSubCommandDispatch(self):
        dispatcher = self.DispatchedClassSub()
        self.assertEqual(
            dispatcher.dispatchCommand('privmsg', ['foo']),
            dispatcher.doPrivmsg)
        self.assertEqual(
            dispatcher.dispatchCommand('cap', ['*', 'ls']),
            dispatcher.doCapLs)
        self.assertEqual(
            dispatcher.dispatchCommand('fail', ['foo', 'bar']),
            dispatcher.doFailFoo)
        self.assertEqual(
            dispatcher.dispatchCommand('foobar', ['*', 'ls']),
            None)

    def testCommandDispatchMissingArgs(self):
        dispatcher = self.DispatchedClass()
        self.assertEqual(
            dispatcher.dispatchCommand('privmsg', ['foo']),
            dispatcher.doPrivmsg)
        self.assertEqual(
            dispatcher.dispatchCommand('cap', ['*']),
            dispatcher.doCap)
        self.assertEqual(
            dispatcher.dispatchCommand('fail', []),
            dispatcher.doFail)
        self.assertEqual(
            dispatcher.dispatchCommand('foobar', ['*']),
            None)

    def testCommandDispatchLegacy(self):
        """Tests the legacy parameters of dispatchCommand, without the "args"
        argument."""
        dispatcher = self.DispatchedClass()
        with self.assertWarnsRegex(DeprecationWarning, "'args'"):
            self.assertEqual(
                dispatcher.dispatchCommand('privmsg'),
                dispatcher.doPrivmsg)
        with self.assertWarnsRegex(DeprecationWarning, "'args'"):
            self.assertEqual(
                dispatcher.dispatchCommand('cap'),
                dispatcher.doCap)
        with self.assertWarnsRegex(DeprecationWarning, "'args'"):
            self.assertEqual(
                dispatcher.dispatchCommand('fail'),
                dispatcher.doFail)
        with self.assertWarnsRegex(DeprecationWarning, "'args'"):
            self.assertEqual(
                dispatcher.dispatchCommand('foobar'),
                None)

class IrcMsgQueueTestCase(SupyTestCase):
    mode = ircmsgs.op('#foo', 'jemfinch')
    msg = ircmsgs.privmsg('#foo', 'hey, you')
    msgs = [ircmsgs.privmsg('#foo', str(i)) for i in range(10)]
    kick = ircmsgs.kick('#foo', 'PeterB')
    pong = ircmsgs.pong('123')
    ping = ircmsgs.ping('123')
    topic = ircmsgs.topic('#foo')
    notice = ircmsgs.notice('jemfinch', 'supybot here')
    join = ircmsgs.join('#foo')
    who = ircmsgs.who('#foo')

    def testInit(self):
        q = irclib.IrcMsgQueue([self.msg, self.topic, self.ping])
        self.assertEqual(len(q), 3)

    def testLen(self):
        q = irclib.IrcMsgQueue()
        q.enqueue(self.msg)
        self.assertEqual(len(q), 1)
        q.enqueue(self.mode)
        self.assertEqual(len(q), 2)
        q.enqueue(self.kick)
        self.assertEqual(len(q), 3)
        q.enqueue(self.topic)
        self.assertEqual(len(q), 4)
        q.dequeue()
        self.assertEqual(len(q), 3)
        q.dequeue()
        self.assertEqual(len(q), 2)
        q.dequeue()
        self.assertEqual(len(q), 1)
        q.dequeue()
        self.assertEqual(len(q), 0)

    def testContains(self):
        q = irclib.IrcMsgQueue()
        q.enqueue(self.msg)
        q.enqueue(self.msg)
        q.enqueue(self.msg)
        self.assertTrue(self.msg in q)
        q.dequeue()
        self.assertTrue(self.msg in q)
        q.dequeue()
        self.assertTrue(self.msg in q)
        q.dequeue()
        self.assertFalse(self.msg in q)

    def testRepr(self):
        q = irclib.IrcMsgQueue()
        self.assertEqual(repr(q), 'IrcMsgQueue([])')
        q.enqueue(self.msg)
        try:
            repr(q)
        except Exception as e:
            self.fail('repr(q) raised an exception: %s' %
                      utils.exnToString(e))

    def testEmpty(self):
        q = irclib.IrcMsgQueue()
        self.assertFalse(q)

    def testEnqueueDequeue(self):
        q = irclib.IrcMsgQueue()
        q.enqueue(self.msg)
        self.assertTrue(q)
        self.assertEqual(self.msg, q.dequeue())
        self.assertFalse(q)
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
        self.assertEqual(self.msg, q.dequeue())
        q.enqueue(self.ping)
        q.enqueue(self.msgs[0])
        q.enqueue(self.kick)
        q.enqueue(self.msgs[1])
        q.enqueue(self.mode)
        self.assertEqual(self.kick, q.dequeue())
        self.assertEqual(self.mode, q.dequeue())
        self.assertEqual(self.ping, q.dequeue())
        self.assertEqual(self.msgs[0], q.dequeue())
        self.assertEqual(self.msgs[1], q.dequeue())

    def testNoIdenticals(self):
        configVar = conf.supybot.protocols.irc.queuing.duplicates
        original = configVar()
        try:
            configVar.setValue(True)
            q = irclib.IrcMsgQueue()
            q.enqueue(self.msg)
            q.enqueue(self.msg)
            self.assertEqual(self.msg, q.dequeue())
            self.assertFalse(q)
        finally:
            configVar.setValue(original)

    def testJoinBeforeWho(self):
        q = irclib.IrcMsgQueue()
        q.enqueue(self.join)
        q.enqueue(self.who)
        self.assertEqual(self.join, q.dequeue())
        self.assertEqual(self.who, q.dequeue())
##         q.enqueue(self.who)
##         q.enqueue(self.join)
##         self.assertEqual(self.join, q.dequeue())
##         self.assertEqual(self.who, q.dequeue())

    def testTopicBeforePrivmsg(self):
        q = irclib.IrcMsgQueue()
        q.enqueue(self.msg)
        q.enqueue(self.topic)
        self.assertEqual(self.topic, q.dequeue())
        self.assertEqual(self.msg, q.dequeue())

    def testModeBeforePrivmsg(self):
        q = irclib.IrcMsgQueue()
        q.enqueue(self.msg)
        q.enqueue(self.mode)
        self.assertEqual(self.mode, q.dequeue())
        self.assertEqual(self.msg, q.dequeue())
        q.enqueue(self.mode)
        q.enqueue(self.msg)
        self.assertEqual(self.mode, q.dequeue())
        self.assertEqual(self.msg, q.dequeue())


class ChannelStateTestCase(SupyTestCase):
    def testPickleCopy(self):
        c = irclib.ChannelState()
        self.assertEqual(pickle.loads(pickle.dumps(c)), c)
        c.addUser('jemfinch')
        c1 = pickle.loads(pickle.dumps(c))
        self.assertEqual(c, c1)
        c.removeUser('jemfinch')
        self.assertFalse('jemfinch' in c.users)
        self.assertTrue('jemfinch' in c1.users)

    def testCopy(self):
        c = irclib.ChannelState()
        c.addUser('jemfinch')
        c1 = copy.deepcopy(c)
        c.removeUser('jemfinch')
        self.assertFalse('jemfinch' in c.users)
        self.assertTrue('jemfinch' in c1.users)

    def testAddUser(self):
        c = irclib.ChannelState()
        c.addUser('foo')
        self.assertTrue('foo' in c.users)
        self.assertFalse('foo' in c.ops)
        self.assertFalse('foo' in c.voices)
        self.assertFalse('foo' in c.halfops)
        c.addUser('+bar')
        self.assertTrue('bar' in c.users)
        self.assertTrue('bar' in c.voices)
        self.assertFalse('bar' in c.ops)
        self.assertFalse('bar' in c.halfops)
        c.addUser('%baz')
        self.assertTrue('baz' in c.users)
        self.assertTrue('baz' in c.halfops)
        self.assertFalse('baz' in c.voices)
        self.assertFalse('baz' in c.ops)
        c.addUser('@quuz')
        self.assertTrue('quuz' in c.users)
        self.assertTrue('quuz' in c.ops)
        self.assertFalse('quuz' in c.halfops)
        self.assertFalse('quuz' in c.voices)


class IrcStateTestCase(SupyTestCase):
    class FakeIrc:
        nick = 'nick'
        prefix = 'nick!user@host'

        def isChannel(self, s):
            return ircutils.isChannel(s)

    irc = FakeIrc()
    def testKickRemovesChannel(self):
        st = irclib.IrcState()
        st.channels['#foo'] = irclib.ChannelState()
        m = ircmsgs.kick('#foo', self.irc.nick, prefix=self.irc.prefix)
        st.addMsg(self.irc, m)
        self.assertFalse('#foo' in st.channels)

    def testAddMsgRemovesOpsProperly(self):
        st = irclib.IrcState()
        st.channels['#foo'] = irclib.ChannelState()
        st.channels['#foo'].ops.add('bar')
        m = ircmsgs.mode('#foo', ('-o', 'bar'))
        st.addMsg(self.irc, m)
        self.assertFalse('bar' in st.channels['#foo'].ops)

    def testNickChangesChangeChannelUsers(self):
        st = irclib.IrcState()
        st.channels['#foo'] = irclib.ChannelState()
        st.channels['#foo'].addUser('@bar')
        self.assertTrue('bar' in st.channels['#foo'].users)
        self.assertTrue(st.channels['#foo'].isOp('bar'))
        st.addMsg(self.irc, ircmsgs.IrcMsg(':bar!asfd@asdf.com NICK baz'))
        self.assertFalse('bar' in st.channels['#foo'].users)
        self.assertFalse(st.channels['#foo'].isOp('bar'))
        self.assertTrue('baz' in st.channels['#foo'].users)
        self.assertTrue(st.channels['#foo'].isOp('baz'))

    def testHistory(self):
        if len(msgs) < 10:
            return
        maxHistoryLength = conf.supybot.protocols.irc.maxHistoryLength
        with maxHistoryLength.context(10):
            state = irclib.IrcState()
            for msg in msgs:
                try:
                    state.addMsg(self.irc, msg)
                except Exception:
                    pass
                self.assertFalse(len(state.history) > maxHistoryLength())
            self.assertEqual(len(state.history), maxHistoryLength())
            self.assertEqual(list(state.history),
                             msgs[len(msgs) - maxHistoryLength():])

    def testWasteland005(self):
        state = irclib.IrcState()
        # Here we're testing if PREFIX works without the (ov) there.
        state.addMsg(self.irc, ircmsgs.IrcMsg(':desolate.wasteland.org 005 jemfinch NOQUIT WATCH=128 SAFELIST MODES=6 MAXCHANNELS=10 MAXBANS=100 NICKLEN=30 TOPICLEN=307 KICKLEN=307 CHANTYPES=&# PREFIX=@+ NETWORK=DALnet SILENCE=10 :are available on this server'))
        self.assertEqual(state.supported['prefix']['o'], '@')
        self.assertEqual(state.supported['prefix']['v'], '+')

    def testIRCNet005(self):
        state = irclib.IrcState()
        # Testing IRCNet's misuse of MAXBANS
        state.addMsg(self.irc, ircmsgs.IrcMsg(':irc.inet.tele.dk 005 adkwbot WALLCHOPS KNOCK EXCEPTS INVEX MODES=4 MAXCHANNELS=20 MAXBANS=beI:100 MAXTARGETS=4 NICKLEN=9 TOPICLEN=120 KICKLEN=90 :are supported by this server'))
        self.assertEqual(state.supported['maxbans'], 100)

    def testSupportedUmodes(self):
        state = irclib.IrcState()
        state.addMsg(self.irc, ircmsgs.IrcMsg(':coulomb.oftc.net 004 testnick coulomb.oftc.net hybrid-7.2.2+oftc1.6.8 CDGPRSabcdfgiklnorsuwxyz biklmnopstveI bkloveI'))
        self.assertEqual(state.supported['umodes'],
                frozenset('CDGPRSabcdfgiklnorsuwxyz'))
        self.assertEqual(state.supported['chanmodes'],
                         frozenset('biklmnopstveI'))

    def testClientTagDenied(self):
        state = irclib.IrcState()

        # By default, every tag is assumed allowed
        self.assertEqual(state.getClientTagDenied('foo'), False)
        self.assertEqual(state.getClientTagDenied('bar'), False)

        # Blacklist
        state.addMsg(self.irc, ircmsgs.IrcMsg(
            ':example.org 005 mybot CLIENTTAGDENY=foo :are supported by this server'))
        self.assertEqual(state.getClientTagDenied('foo'), True)
        self.assertEqual(state.getClientTagDenied('bar'), False)
        self.assertEqual(state.getClientTagDenied('+foo'), True)
        self.assertEqual(state.getClientTagDenied('+bar'), False)

        # Whitelist
        state.addMsg(self.irc, ircmsgs.IrcMsg(
            ':example.org 005 mybot CLIENTTAGDENY=*,-foo :are supported by this server'))
        self.assertEqual(state.getClientTagDenied('foo'), False)
        self.assertEqual(state.getClientTagDenied('bar'), True)
        self.assertEqual(state.getClientTagDenied('+foo'), False)
        self.assertEqual(state.getClientTagDenied('+bar'), True)

    def testShort004(self):
        state = irclib.IrcState()
        state.addMsg(self.irc, ircmsgs.IrcMsg(':coulomb.oftc.net 004 testnick coulomb.oftc.net hybrid-7.2.2+oftc1.6.8'))
        self.assertNotIn('umodes', state.supported)
        self.assertNotIn('chanmodes', state.supported)

    def testEmptyTopic(self):
        state = irclib.IrcState()
        state.addMsg(self.irc, ircmsgs.topic('#foo'))

    def testPickleCopy(self):
        state = irclib.IrcState()
        self.assertEqual(state, pickle.loads(pickle.dumps(state)))
        for msg in msgs:
            try:
                state.addMsg(self.irc, msg)
            except Exception:
                pass
        self.assertEqual(state, pickle.loads(pickle.dumps(state)))

    def testCopy(self):
        state = irclib.IrcState()
        self.assertEqual(state, state.copy())
        for msg in msgs:
            try:
                state.addMsg(self.irc, msg)
            except Exception:
                pass
        self.assertEqual(state, state.copy())

    def testCopyCopiesChannels(self):
        state = irclib.IrcState()
        stateCopy = state.copy()
        state.channels['#foo'] = None
        self.assertFalse('#foo' in stateCopy.channels)

    def testJoin(self):
        st = irclib.IrcState()
        st.addMsg(self.irc, ircmsgs.join('#foo', prefix=self.irc.prefix))
        self.assertTrue('#foo' in st.channels)
        self.assertTrue(self.irc.nick in st.channels['#foo'].users)
        st.addMsg(self.irc, ircmsgs.join('#foo', prefix='foo!bar@baz'))
        self.assertTrue('foo' in st.channels['#foo'].users)
        st2 = st.copy()
        st.addMsg(self.irc, ircmsgs.quit(prefix='foo!bar@baz'))
        self.assertFalse('foo' in st.channels['#foo'].users)
        self.assertTrue('foo' in st2.channels['#foo'].users)


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

    def testHandlesModes(self):
        st = irclib.IrcState()
        st.addMsg(self.irc, ircmsgs.join('#foo', prefix=self.irc.prefix))
        self.assertFalse('bar' in st.channels['#foo'].ops)
        st.addMsg(self.irc, ircmsgs.op('#foo', 'bar'))
        self.assertTrue('bar' in st.channels['#foo'].ops)
        st.addMsg(self.irc, ircmsgs.deop('#foo', 'bar'))
        self.assertFalse('bar' in st.channels['#foo'].ops)

        self.assertFalse('bar' in st.channels['#foo'].voices)
        st.addMsg(self.irc, ircmsgs.voice('#foo', 'bar'))
        self.assertTrue('bar' in st.channels['#foo'].voices)
        st.addMsg(self.irc, ircmsgs.devoice('#foo', 'bar'))
        self.assertFalse('bar' in st.channels['#foo'].voices)

        self.assertFalse('bar' in st.channels['#foo'].halfops)
        st.addMsg(self.irc, ircmsgs.halfop('#foo', 'bar'))
        self.assertTrue('bar' in st.channels['#foo'].halfops)
        st.addMsg(self.irc, ircmsgs.dehalfop('#foo', 'bar'))
        self.assertFalse('bar' in st.channels['#foo'].halfops)

    def testDoModeOnlyChannels(self):
        st = irclib.IrcState()
        self.assert_(st.addMsg(self.irc, ircmsgs.IrcMsg('MODE foo +i')) or 1)


class IrcCapsTestCase(SupyTestCase, CapNegMixin):
    def testReqLineLength(self):
        self.irc = irclib.Irc('test')

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertTrue(m.args == ('LS', '302'), 'Expected CAP LS 302, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'NICK', 'Expected NICK, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'USER', 'Expected USER, got %r.' % m)

        self.irc.REQUEST_CAPABILITIES = set(['a'*400, 'b'*400])
        caps = ' '.join(self.irc.REQUEST_CAPABILITIES)
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', '*', 'a'*400)))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', 'b'*400)))

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args[0], 'REQ', m)
        self.assertEqual(m.args[1], 'a'*400)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args[0], 'REQ', m)
        self.assertEqual(m.args[1], 'b'*400)

    def testNoEchomessageWithoutLabeledresponse(self):
        self.irc = irclib.Irc('test')

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertTrue(m.args == ('LS', '302'), 'Expected CAP LS 302, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'NICK', 'Expected NICK, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'USER', 'Expected USER, got %r.' % m)

        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', 'account-notify echo-message')))

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args[0], 'REQ', m)
        self.assertEqual(m.args[1], 'account-notify')

        m = self.irc.takeMsg()
        self.assertIsNone(m)

        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'ACK', 'account-notify')))

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args, ('END',), m)

    def testEchomessageLabeledresponseGrouped(self):
        self.irc = irclib.Irc('test')

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertTrue(m.args == ('LS', '302'), 'Expected CAP LS 302, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'NICK', 'Expected NICK, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'USER', 'Expected USER, got %r.' % m)

        self.irc.REQUEST_CAPABILITIES = set([
            'account-notify', 'a'*490, 'echo-message', 'labeled-response'])
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP', args=(
            '*', 'LS',
            'account-notify ' + 'a'*490 + ' echo-message labeled-response')))

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args[0], 'REQ', m)
        self.assertEqual(m.args[1], 'echo-message labeled-response')

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args[0], 'REQ', m)
        self.assertEqual(m.args[1], 'a'*490)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args[0], 'REQ', m)
        self.assertEqual(m.args[1], 'account-notify')

        m = self.irc.takeMsg()
        self.assertIsNone(m)

    def testCapNew(self):
        self.irc = irclib.Irc('test')

        self.assertEqual(self.irc.sasl_current_mechanism, None)
        self.assertEqual(self.irc.sasl_next_mechanisms, [])

        self.startCapNegociation(caps='')

        self.endCapNegociation()

        while self.irc.takeMsg():
            pass

        self.irc.feedMsg(ircmsgs.IrcMsg(command='422')) # ERR_NOMOTD

        m = self.irc.takeMsg()
        self.assertIsNone(m)

        self.irc.feedMsg(ircmsgs.IrcMsg(
            command='CAP', args=['*', 'NEW', 'account-notify']))

        m = self.irc.takeMsg()
        self.assertEqual(m,
            ircmsgs.IrcMsg(command='CAP', args=['REQ', 'account-notify']))

        self.irc.feedMsg(ircmsgs.IrcMsg(
            command='CAP', args=['*', 'ACK', 'account-notify']))

        self.assertIn('account-notify', self.irc.state.capabilities_ack)

    def testCapNewEchomessageLabeledResponse(self):
        self.irc = irclib.Irc('test')

        self.assertEqual(self.irc.sasl_current_mechanism, None)
        self.assertEqual(self.irc.sasl_next_mechanisms, [])

        self.startCapNegociation(caps='')

        self.endCapNegociation()

        while self.irc.takeMsg():
            pass

        self.irc.feedMsg(ircmsgs.IrcMsg(command='422')) # ERR_NOMOTD

        m = self.irc.takeMsg()
        self.assertIsNone(m)

        self.irc.feedMsg(ircmsgs.IrcMsg(
            command='CAP', args=['*', 'NEW', 'echo-message']))

        m = self.irc.takeMsg()
        self.assertIsNone(m)

        self.irc.feedMsg(ircmsgs.IrcMsg(
            command='CAP', args=['*', 'NEW', 'labeled-response']))

        m = self.irc.takeMsg()
        self.assertEqual(m,
            ircmsgs.IrcMsg(
                command='CAP', args=['REQ', 'echo-message labeled-response']))

        self.irc.feedMsg(ircmsgs.IrcMsg(
            command='CAP', args=['*', 'ACK', 'echo-message labeled-response']))

        self.assertIn('echo-message', self.irc.state.capabilities_ack)
        self.assertIn('labeled-response', self.irc.state.capabilities_ack)


class StsTestCase(SupyTestCase):
    def setUp(self):
        self.irc = irclib.Irc('test')

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.failUnless(m.args == ('LS', '302'), 'Expected CAP LS 302, got %r.' % m)

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'NICK', 'Expected NICK, got %r.' % m)

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'USER', 'Expected USER, got %r.' % m)

        self.irc.driver = unittest.mock.Mock()

    def tearDown(self):
        ircdb.networks.networks = {}

    def testStsInSecureConnection(self):
        self.irc.driver.anyCertValidationEnabled.return_value = True
        self.irc.driver.ssl = True
        self.irc.driver.currentServer = drivers.Server('irc.test', 6697, None, False)
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', 'sts=duration=42,port=6697')))

        self.assertEqual(ircdb.networks.getNetwork('test').stsPolicies, {
            'irc.test': 'duration=42,port=6697'})
        self.irc.driver.reconnect.assert_not_called()

    def testStsInInsecureTlsConnection(self):
        self.irc.driver.anyCertValidationEnabled.return_value = False
        self.irc.driver.ssl = True
        self.irc.driver.currentServer = drivers.Server('irc.test', 6697, None, False)
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', 'sts=duration=42,port=6697')))

        self.assertEqual(ircdb.networks.getNetwork('test').stsPolicies, {})
        self.irc.driver.reconnect.assert_called_once_with(
            server=drivers.Server('irc.test', 6697, None, True),
            wait=True)

    def testStsInCleartextConnection(self):
        self.irc.driver.anyCertValidationEnabled.return_value = False
        self.irc.driver.ssl = True
        self.irc.driver.currentServer = drivers.Server('irc.test', 6667, None, False)
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', 'sts=duration=42,port=6697')))

        self.assertEqual(ircdb.networks.getNetwork('test').stsPolicies, {})
        self.irc.driver.reconnect.assert_called_once_with(
            server=drivers.Server('irc.test', 6697, None, True),
            wait=True)

    def testStsInCleartextConnectionInvalidDuration(self):
        # "Servers MAY send this key to all clients, but insecurely
        # connected clients MUST ignore it."
        self.irc.driver.anyCertValidationEnabled.return_value = False
        self.irc.driver.ssl = True
        self.irc.driver.currentServer = drivers.Server('irc.test', 6667, None, False)
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', 'sts=duration=foo,port=6697')))

        self.assertEqual(ircdb.networks.getNetwork('test').stsPolicies, {})
        self.irc.driver.reconnect.assert_called_once_with(
            server=drivers.Server('irc.test', 6697, None, True),
            wait=True)

    def testStsInCleartextConnectionNoDuration(self):
        # "Servers MAY send this key to all clients, but insecurely
        # connected clients MUST ignore it."
        self.irc.driver.anyCertValidationEnabled.return_value = False
        self.irc.driver.ssl = True
        self.irc.driver.currentServer = drivers.Server('irc.test', 6667, None, False)
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', 'sts=port=6697')))

        self.assertEqual(ircdb.networks.getNetwork('test').stsPolicies, {})
        self.irc.driver.reconnect.assert_called_once_with(
            server=drivers.Server('irc.test', 6697, None, True),
            wait=True)

class IrcTestCase(SupyTestCase):
    def setUp(self):
        self.irc = irclib.Irc('test')

        #m = self.irc.takeMsg()
        #self.assertTrue(m.command == 'PASS', 'Expected PASS, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertTrue(m.args == ('LS', '302'), 'Expected CAP LS 302, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'NICK', 'Expected NICK, got %r.' % m)

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'USER', 'Expected USER, got %r.' % m)

        # TODO
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', '*', 'account-tag multi-prefix')))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', 'extended-join')))

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args[0], 'REQ', m)
        # NOTE: Capabilities are requested in alphabetic order, because
        # sets are unordered, and their "order" is nondeterministic.
        self.assertEqual(m.args[1], 'account-tag extended-join multi-prefix')

        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'ACK', 'account-tag multi-prefix extended-join')))

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args, ('END',), m)

        m = self.irc.takeMsg()
        self.assertTrue(m is None, m)

    def testPingResponse(self):
        self.irc.feedMsg(ircmsgs.ping('123'))
        self.assertEqual(ircmsgs.pong('123'), self.irc.takeMsg())

    def test433Response(self):
        # This is necessary; it won't change nick if irc.originalName==irc.nick
        self.irc.nick = 'somethingElse'
        self.irc.feedMsg(ircmsgs.IrcMsg('433 * %s :Nickname already in use.' %\
                                        self.irc.nick))
        msg = self.irc.takeMsg()
        self.assertTrue(msg.command == 'NICK' and msg.args[0] != self.irc.nick)
        self.irc.feedMsg(ircmsgs.IrcMsg('433 * %s :Nickname already in use.' %\
                                        self.irc.nick))
        msg = self.irc.takeMsg()
        self.assertTrue(msg.command == 'NICK' and msg.args[0] != self.irc.nick)

    def testSendBeforeQueue(self):
        while self.irc.takeMsg() is not None:
            self.irc.takeMsg()
        self.irc.queueMsg(ircmsgs.IrcMsg('NOTICE #foo bar'))
        self.irc.sendMsg(ircmsgs.IrcMsg('PRIVMSG #foo yeah!'))
        msg = self.irc.takeMsg()
        self.assertTrue(msg.command == 'PRIVMSG')
        msg = self.irc.takeMsg()
        self.assertTrue(msg.command == 'NOTICE')

    def testNoMsgLongerThan512(self):
        self.irc.queueMsg(ircmsgs.privmsg('whocares', 'x'*1000))
        msg = self.irc.takeMsg()
        self.assertEqual(
            len(msg), 512, 'len(msg) was %s (msg=%r)' % (len(msg), msg))

        # Server tags don't influence the size limit of the rest of the
        # message.
        self.irc.queueMsg(ircmsgs.IrcMsg(
            command='PRIVMSG', args=['whocares', 'x'*1000],
            server_tags={'y': 'z'*500}))
        msg2 = self.irc.takeMsg()
        self.assertEqual(
            len(msg2), 512+504, 'len(msg2) was %s (msg2=%r)' % (len(msg2), msg2))
        self.assertEqual(msg.args, msg2.args)

    def testReset(self):
        for msg in msgs:
            try:
                self.irc.feedMsg(msg)
            except:
                pass
        self.irc.reset()
        self.assertFalse(self.irc.state.history)
        self.assertFalse(self.irc.state.channels)
        self.assertFalse(self.irc.outstandingPing)

    def testHistory(self):
        self.irc.reset()
        msg1 = ircmsgs.IrcMsg('PRIVMSG #linux :foo bar baz!')
        self.irc.feedMsg(msg1)
        self.assertEqual(self.irc.state.history[0], msg1)
        msg2 = ircmsgs.IrcMsg('JOIN #sourcereview')
        self.irc.feedMsg(msg2)
        self.assertEqual(list(self.irc.state.history), [msg1, msg2])

    def testMultipleMotd(self):
        self.irc.reset()

        self.irc.feedMsg(ircmsgs.IrcMsg(command='422'))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='422'))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='375', args=['nick']))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='372', args=['nick', 'some message']))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='376', args=['nick']))

    def testSetUmodes(self):
        def assertSentModes(modes):
            self.assertEqual(
                self.irc.takeMsg(),
                ircmsgs.IrcMsg(command='MODE', args=['test', modes]),
            )

        self.irc.reset()
        while self.irc.takeMsg():
            pass

        self.irc.state.supported["BOT"] = "" # invalid
        self.irc._setUmodes()
        self.assertIsNone(self.irc.takeMsg())

        self.irc.state.supported["BOT"] = "bB" # invalid too
        self.irc._setUmodes()
        self.assertIsNone(self.irc.takeMsg())

        del self.irc.state.supported["BOT"]
        self.irc._setUmodes()
        self.assertIsNone(self.irc.takeMsg())

        self.irc.state.supported["BOT"] = "B"
        self.irc._setUmodes()
        assertSentModes("+B")

        self.irc.state.supported["BOT"] = "b"
        self.irc._setUmodes()
        assertSentModes("+b")

        # merge with configured umodes
        with conf.supybot.protocols.irc.umodes.context("+B"):
            self.irc._setUmodes()
            assertSentModes("+B+b")

        # no duplicate if char is the same
        with conf.supybot.protocols.irc.umodes.context("+b"):
            self.irc._setUmodes()
            assertSentModes("+b")

        # no duplicate if explicitly disabled
        with conf.supybot.protocols.irc.umodes.context("-b"):
            self.irc._setUmodes()
            assertSentModes("-b")

    def testMsgChannel(self):
        self.irc.reset()

        self.irc.state.supported['statusmsg'] = '@'
        self.irc.feedMsg(ircmsgs.IrcMsg('PRIVMSG #linux :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, '#linux')
        self.irc.feedMsg(ircmsgs.IrcMsg('PRIVMSG @#linux2 :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, '#linux2')
        self.irc.feedMsg(ircmsgs.IrcMsg('PRIVMSG +#linux3 :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, None)

        self.irc.state.supported['statusmsg'] = '+@'
        self.irc.feedMsg(ircmsgs.IrcMsg('PRIVMSG #linux :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, '#linux')
        self.irc.feedMsg(ircmsgs.IrcMsg('PRIVMSG @#linux2 :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, '#linux2')
        self.irc.feedMsg(ircmsgs.IrcMsg('PRIVMSG +#linux3 :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, '#linux3')

        del self.irc.state.supported['statusmsg']
        self.irc.feedMsg(ircmsgs.IrcMsg('PRIVMSG #linux :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, '#linux')
        self.irc.feedMsg(ircmsgs.IrcMsg('PRIVMSG @#linux2 :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, None)
        self.irc.feedMsg(ircmsgs.IrcMsg('PRIVMSG +#linux3 :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, None)

        # Test msg.channel is set only for PRIVMSG and NOTICE
        self.irc.state.supported['statusmsg'] = '+@'
        self.irc.feedMsg(ircmsgs.IrcMsg('NOTICE @#linux :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, '#linux')
        self.irc.feedMsg(ircmsgs.IrcMsg('NOTICE @#linux2 :foo bar baz!'))
        self.assertEqual(self.irc.state.history[-1].channel, '#linux2')
        self.irc.feedMsg(ircmsgs.IrcMsg('MODE @#linux3 +v foo'))
        self.assertEqual(self.irc.state.history[-1].channel, None)

    def testQuit(self):
        self.irc.reset()
        self.irc.feedMsg(ircmsgs.IrcMsg(':someuser JOIN #foo'))
        self.irc.feedMsg(ircmsgs.IrcMsg(':someuser JOIN #bar'))
        self.irc.feedMsg(ircmsgs.IrcMsg(':someuser2 JOIN #bar2'))
        class Callback(irclib.IrcCallback):
            channels_set = None
            def name(self):
                return 'testcallback'
            def doQuit(self2, irc, msg):
                self2.channels_set = msg.tagged('channels')
        c = Callback()
        self.irc.addCallback(c)
        try:
            self.irc.feedMsg(ircmsgs.IrcMsg(':someuser QUIT'))
        finally:
            self.irc.removeCallback(c.name())
        self.assertEqual(c.channels_set, ircutils.IrcSet(['#foo', '#bar']))

    def testNick(self):
        self.irc.reset()
        self.irc.feedMsg(ircmsgs.IrcMsg(':someuser JOIN #foo'))
        self.irc.feedMsg(ircmsgs.IrcMsg(':someuser JOIN #bar'))
        self.irc.feedMsg(ircmsgs.IrcMsg(':someuser2 JOIN #bar2'))
        class Callback(irclib.IrcCallback):
            channels_set = None
            def name(self):
                return 'testcallback'
            def doNick(self2, irc, msg):
                self2.channels_set = msg.tagged('channels')
        c = Callback()
        self.irc.addCallback(c)
        try:
            self.irc.feedMsg(ircmsgs.IrcMsg(':someuser NICK newuser'))
        finally:
            self.irc.removeCallback(c.name())
        self.assertEqual(c.channels_set, ircutils.IrcSet(['#foo', '#bar']))

    def testBatch(self):
        self.irc.reset()
        self.irc.feedMsg(ircmsgs.IrcMsg(':someuser1 JOIN #foo'))
        m1 = ircmsgs.IrcMsg(':host BATCH +name netjoin')
        self.irc.feedMsg(m1)
        m2 = ircmsgs.IrcMsg('@batch=name :someuser2 JOIN #foo')
        self.irc.feedMsg(m2)
        self.irc.feedMsg(ircmsgs.IrcMsg(':someuser3 JOIN #foo'))
        m3 = ircmsgs.IrcMsg('@batch=name :someuser4 JOIN #foo')
        self.irc.feedMsg(m3)
        class Callback(irclib.IrcCallback):
            batch = None
            def name(self):
                return 'testcallback'
            def doBatch(self2, irc, msg):
                self2.batch = msg.tagged('batch')
        c = Callback()
        self.irc.addCallback(c)
        try:
            m4 = ircmsgs.IrcMsg(':host BATCH -name')
            self.irc.feedMsg(m4)
        finally:
            self.irc.removeCallback(c.name())
        self.assertEqual(
            c.batch,
            irclib.Batch('name', 'netjoin', (), [m1, m2, m3, m4], None),
            repr(c.batch)
        )

    def testBatchNested(self):
        self.irc.reset()
        logs = textwrap.dedent('''
            :irc.host BATCH +outer example.com/foo
            @batch=outer :irc.host BATCH +inner example.com/bar
            @batch=inner :nick!user@host PRIVMSG #channel :Hi
            @batch=outer :irc.host BATCH -inner
            :irc.host BATCH -outer
        ''')
        msgs = [ircmsgs.IrcMsg(s) for s in logs.split('\n') if s]

        # Feed 'BATCH +outer', it should be added in state
        self.irc.feedMsg(msgs[0])
        outer = irclib.Batch('outer', 'example.com/foo', (), msgs[0:1], None)
        self.assertEqual(self.irc.state.batches, {'outer': outer})
        msg1 = self.irc.state.history[-1]
        self.assertEqual(msg1.tagged('batch'), outer)
        self.assertEqual(self.irc.state.getParentBatches(msg1), [outer])

        # Feed 'BATCH +inner', it should be added in state
        self.irc.feedMsg(msgs[1])
        outer = irclib.Batch('outer', 'example.com/foo', (), msgs[0:2], None)
        inner = irclib.Batch('inner', 'example.com/bar', (), msgs[1:2], outer)
        self.assertIs(self.irc.state.batches['inner'].parent_batch,
                      self.irc.state.batches['outer'])
        self.assertEqual(dict(self.irc.state.batches),
                         {'outer': outer, 'inner': inner})
        msg2 = self.irc.state.history[-1]
        self.assertEqual(msg2.tagged('batch'), inner)
        self.assertEqual(self.irc.state.getParentBatches(msg2), [inner, outer])

        # Feed 'PRIVMSG'
        self.irc.feedMsg(msgs[2])
        outer = irclib.Batch('outer', 'example.com/foo', (), msgs[0:3], None)
        inner = irclib.Batch('inner', 'example.com/bar', (), msgs[1:3], outer)
        self.assertIs(self.irc.state.batches['inner'].parent_batch,
                      self.irc.state.batches['outer'])
        self.assertEqual(self.irc.state.batches,
                         {'outer': outer, 'inner': inner})
        msg3 = self.irc.state.history[-1]
        self.assertEqual(msg3.tagged('batch'), None)
        self.assertEqual(self.irc.state.getParentBatches(msg3), [inner, outer])

        # Feed 'BATCH -inner', it should be remove from state
        self.irc.feedMsg(msgs[3])
        outer = irclib.Batch('outer', 'example.com/foo', (), msgs[0:4], None)
        inner = irclib.Batch('inner', 'example.com/bar', (), msgs[1:4], outer)
        self.assertEqual(self.irc.state.batches, {'outer': outer})
        self.assertIs(self.irc.state.history[-1].tagged('batch').parent_batch,
                      self.irc.state.batches['outer'])
        msg4 = self.irc.state.history[-1]
        self.assertEqual(msg4.tagged('batch'), inner)
        self.assertEqual(self.irc.state.getParentBatches(msg4), [inner, outer])

        # Feed 'BATCH -outer', it should be remove from state
        self.irc.feedMsg(msgs[4])
        outer = irclib.Batch('outer', 'example.com/foo', (), msgs[0:5], None)
        inner = irclib.Batch('inner', 'example.com/bar', (), msgs[1:4], outer)
        self.assertEqual(self.irc.state.batches, {})
        msg5 = self.irc.state.history[-1]
        self.assertEqual(msg5.tagged('batch'), outer)
        self.assertEqual(self.irc.state.getParentBatches(msg5), [outer])

    def testBatchError(self):
        # Checks getting an ERROR message in a batch does not cause issues
        # due to deinitializing the connection at the same time.
        self.irc.reset()
        m1 = ircmsgs.IrcMsg(':host BATCH +name batchtype')
        self.irc.feedMsg(m1)
        m2 = ircmsgs.IrcMsg('@batch=name :someuser2 NOTICE * :oh no')
        self.irc.feedMsg(m2)
        m3 = ircmsgs.IrcMsg('@batch=name ERROR :bye')
        self.irc.feedMsg(m3)
        class Callback(irclib.IrcCallback):
            batch = None
            def __call__(self, *args, **kwargs):
                return super().__call__(*args, **kwargs)
            def name(self):
                return 'testcallback'
            def doBatch(self2, irc, msg):
                self2.batch = msg.tagged('batch')

        # would usually be called by the driver upon reconnect() trigged
        # by the ERROR:
        self.irc.reset()

        c = Callback()
        self.irc.addCallback(c)
        try:
            m4 = ircmsgs.IrcMsg(':host BATCH -name')
            self.irc.feedMsg(m4)
        finally:
            self.irc.removeCallback(c.name())
        self.assertEqual(
            c.batch,
            irclib.Batch('name', 'batchtype', (), [m1, m2, m3, m4], None),
            repr(c.batch)
        )

    def testTruncate(self):
        self.irc = irclib.Irc('test')

        while self.irc.takeMsg():
            pass

        # over 512 bytes
        msg = ircmsgs.IrcMsg(command='PRIVMSG', args=('#test2', 'é'*256))
        self.irc.sendMsg(msg)
        m = self.irc.takeMsg()
        remaining_payload = 'é' * ((512 - len('PRIVMSG #test2 :\r\n'))//2)
        self.assertEqual(
                str(m), 'PRIVMSG #test2 :%s\r\n' % remaining_payload)

        # over 512 bytes, make sure it doesn't truncate in the middle of
        # a character
        msg = ircmsgs.IrcMsg(command='PRIVMSG', args=('#test', 'é'*256))
        self.irc.sendMsg(msg)
        m = self.irc.takeMsg()
        remaining_payload = 'é' * ((512 - len('PRIVMSG #test :\r\n'))//2)
        self.assertEqual(
                str(m), 'PRIVMSG #test :%s\r\n' % remaining_payload)


class BatchTestCase(SupyTestCase):
    def setUp(self):
        self.irc = irclib.Irc('test')
        conf.supybot.protocols.irc.experimentalExtensions.setValue(True)
        while self.irc.takeMsg() is not None:
            self.irc.takeMsg()

    def tearDown(self):
        conf.supybot.protocols.irc.experimentalExtensions.setValue(False)

    def testQueueBatch(self):
        """Basic operation of queueBatch"""
        msgs = [
            ircmsgs.IrcMsg('BATCH +label batchtype'),
            ircmsgs.IrcMsg('@batch=label PRIVMSG #channel :hello'),
            ircmsgs.IrcMsg('@batch=label PRIVMSG #channel :there'),
            ircmsgs.IrcMsg('BATCH -label'),
        ]

        self.irc.queueBatch(copy.deepcopy(msgs))
        for msg in msgs:
            self.assertEqual(msg, self.irc.takeMsg())

    def testQueueBatchStartMinus(self):
        msgs = [
            ircmsgs.IrcMsg('BATCH -label batchtype'),
            ircmsgs.IrcMsg('@batch=label PRIVMSG #channel :hello'),
            ircmsgs.IrcMsg('BATCH -label'),
        ]

        with self.assertRaises(ValueError):
            self.irc.queueBatch(msgs)
        self.assertIsNone(self.irc.takeMsg())

    def testQueueBatchEndPlus(self):
        msgs = [
            ircmsgs.IrcMsg('BATCH +label batchtype'),
            ircmsgs.IrcMsg('@batch=label PRIVMSG #channel :hello'),
            ircmsgs.IrcMsg('BATCH +label'),
        ]

        with self.assertRaises(ValueError):
            self.irc.queueBatch(msgs)
        self.assertIsNone(self.irc.takeMsg())

    def testQueueBatchMismatchStartEnd(self):
        msgs = [
            ircmsgs.IrcMsg('BATCH +label batchtype'),
            ircmsgs.IrcMsg('@batch=label PRIVMSG #channel :hello'),
            ircmsgs.IrcMsg('BATCH -label2'),
        ]

        with self.assertRaises(ValueError):
            self.irc.queueBatch(msgs)
        self.assertIsNone(self.irc.takeMsg())

    def testQueueBatchMismatchInner(self):
        msgs = [
            ircmsgs.IrcMsg('BATCH +label batchtype'),
            ircmsgs.IrcMsg('@batch=label2 PRIVMSG #channel :hello'),
            ircmsgs.IrcMsg('BATCH -label'),
        ]

        with self.assertRaises(ValueError):
            self.irc.queueBatch(msgs)
        self.assertIsNone(self.irc.takeMsg())

    def testQueueBatchTwice(self):
        """Basic operation of queueBatch"""
        all_msgs = []
        for label in ('label1', 'label2'):
            msgs = [
                ircmsgs.IrcMsg('BATCH +%s batchtype' % label),
                ircmsgs.IrcMsg('@batch=%s PRIVMSG #channel :hello' % label),
                ircmsgs.IrcMsg('@batch=%s PRIVMSG #channel :there' % label),
                ircmsgs.IrcMsg('BATCH -%s' % label),
            ]
            all_msgs.extend(msgs)
            self.irc.queueBatch(copy.deepcopy(msgs))

        for msg in all_msgs:
            self.assertEqual(msg, self.irc.takeMsg())

    def testQueueBatchDuplicate(self):
        msgs = [
            ircmsgs.IrcMsg('BATCH +label batchtype'),
            ircmsgs.IrcMsg('@batch=label PRIVMSG #channel :hello'),
            ircmsgs.IrcMsg('BATCH -label'),
        ]

        self.irc.queueBatch(copy.deepcopy(msgs))

        with self.assertRaises(ValueError):
            self.irc.queueBatch(copy.deepcopy(msgs))

        for msg in msgs:
            self.assertEqual(msg, self.irc.takeMsg())
        self.assertIsNone(self.irc.takeMsg())

    def testQueueBatchReuse(self):
        """We can reuse the same label after the batch is closed."""
        msgs = [
            ircmsgs.IrcMsg('BATCH +label batchtype'),
            ircmsgs.IrcMsg('@batch=label PRIVMSG #channel :hello'),
            ircmsgs.IrcMsg('BATCH -label'),
        ]

        self.irc.queueBatch(copy.deepcopy(msgs))
        for msg in msgs:
            self.assertEqual(msg, self.irc.takeMsg())

        self.irc.queueBatch(copy.deepcopy(msgs))
        for msg in msgs:
            self.assertEqual(msg, self.irc.takeMsg())

    def testBatchInterleaved(self):
        """Make sure it's not possible for an unrelated message to be sent
        while a batch is open"""
        msgs = [
            ircmsgs.IrcMsg('BATCH +label batchtype'),
            ircmsgs.IrcMsg('@batch=label PRIVMSG #channel :hello'),
            ircmsgs.IrcMsg('BATCH -label'),
        ]
        msg = ircmsgs.IrcMsg('PRIVMSG #channel :unrelated message')

        with self.subTest('sendMsg called before "BATCH +" is dequeued'):
            self.irc.queueBatch(copy.deepcopy(msgs))
            self.irc.sendMsg(msg)

            self.assertEqual(msg, self.irc.takeMsg())
            self.assertEqual(msgs[0], self.irc.takeMsg())
            self.assertEqual(msgs[1], self.irc.takeMsg())
            self.assertEqual(msgs[2], self.irc.takeMsg())
            self.assertIsNone(self.irc.takeMsg())

        with self.subTest('sendMsg called after "BATCH +" is dequeued'):
            self.irc.queueBatch(copy.deepcopy(msgs))
            self.assertEqual(msgs[0], self.irc.takeMsg())

            self.irc.sendMsg(msg)

            self.assertEqual(msgs[1], self.irc.takeMsg())
            self.assertEqual(msgs[2], self.irc.takeMsg())
            self.assertEqual(msg, self.irc.takeMsg())
            self.assertIsNone(self.irc.takeMsg())


class SaslTestCase(SupyTestCase, CapNegMixin):
    def setUp(self):
        pass

    def testPlain(self):
        try:
            conf.supybot.networks.test.sasl.username.setValue('jilles')
            conf.supybot.networks.test.sasl.password.setValue('sesame')
            self.irc = irclib.Irc('test')
        finally:
            conf.supybot.networks.test.sasl.username.setValue('')
            conf.supybot.networks.test.sasl.password.setValue('')
        self.assertEqual(self.irc.sasl_current_mechanism, None)
        self.assertEqual(self.irc.sasl_next_mechanisms, ['plain'])

        self.startCapNegociation()

        m = self.irc.takeMsg()
        self.assertEqual(m, ircmsgs.IrcMsg(command='AUTHENTICATE',
            args=('PLAIN',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='AUTHENTICATE', args=('+',)))

        m = self.irc.takeMsg()
        self.assertEqual(m, ircmsgs.IrcMsg(command='AUTHENTICATE',
            args=('amlsbGVzAGppbGxlcwBzZXNhbWU=',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='900', args=('jilles',)))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='903', args=('jilles',)))

        self.endCapNegociation()

    def testExternalFallbackToPlain(self):
        try:
            conf.supybot.networks.test.sasl.username.setValue('jilles')
            conf.supybot.networks.test.sasl.password.setValue('sesame')
            conf.supybot.networks.test.certfile.setValue('foo')
            self.irc = irclib.Irc('test')
        finally:
            conf.supybot.networks.test.sasl.username.setValue('')
            conf.supybot.networks.test.sasl.password.setValue('')
            conf.supybot.networks.test.certfile.setValue('')
        self.assertEqual(self.irc.sasl_current_mechanism, None)
        self.assertEqual(self.irc.sasl_next_mechanisms,
                ['external', 'plain'])

        self.startCapNegociation()

        m = self.irc.takeMsg()
        self.assertEqual(m, ircmsgs.IrcMsg(command='AUTHENTICATE',
            args=('EXTERNAL',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='904',
            args=('mechanism not available',)))

        m = self.irc.takeMsg()
        self.assertEqual(m, ircmsgs.IrcMsg(command='AUTHENTICATE',
            args=('PLAIN',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='AUTHENTICATE', args=('+',)))

        m = self.irc.takeMsg()
        self.assertEqual(m, ircmsgs.IrcMsg(command='AUTHENTICATE',
            args=('amlsbGVzAGppbGxlcwBzZXNhbWU=',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='900', args=('jilles',)))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='903', args=('jilles',)))

        self.endCapNegociation()

    def testFilter(self):
        try:
            conf.supybot.networks.test.sasl.username.setValue('jilles')
            conf.supybot.networks.test.sasl.password.setValue('sesame')
            conf.supybot.networks.test.certfile.setValue('foo')
            self.irc = irclib.Irc('test')
        finally:
            conf.supybot.networks.test.sasl.username.setValue('')
            conf.supybot.networks.test.sasl.password.setValue('')
            conf.supybot.networks.test.certfile.setValue('')
        self.assertEqual(self.irc.sasl_current_mechanism, None)
        self.assertEqual(self.irc.sasl_next_mechanisms,
                ['external', 'plain'])

        self.startCapNegociation(caps='sasl=foo,plain,bar')

        m = self.irc.takeMsg()
        self.assertEqual(m, ircmsgs.IrcMsg(command='AUTHENTICATE',
            args=('PLAIN',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='AUTHENTICATE', args=('+',)))

        m = self.irc.takeMsg()
        self.assertEqual(m, ircmsgs.IrcMsg(command='AUTHENTICATE',
            args=('amlsbGVzAGppbGxlcwBzZXNhbWU=',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='900', args=('jilles',)))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='903', args=('jilles',)))

        self.endCapNegociation()

    def testReauthenticate(self):
        try:
            conf.supybot.networks.test.sasl.username.setValue('jilles')
            conf.supybot.networks.test.sasl.password.setValue('sesame')
            self.irc = irclib.Irc('test')
        finally:
            conf.supybot.networks.test.sasl.username.setValue('')
            conf.supybot.networks.test.sasl.password.setValue('')
        self.assertEqual(self.irc.sasl_current_mechanism, None)
        self.assertEqual(self.irc.sasl_next_mechanisms, ['plain'])

        self.startCapNegociation(caps='')

        self.endCapNegociation()

        while self.irc.takeMsg():
            pass

        self.irc.feedMsg(ircmsgs.IrcMsg(command='422')) # ERR_NOMOTD

        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
                args=('*', 'NEW', 'sasl=EXTERNAL')))

        self.irc.takeMsg() # None. But even if it was CAP REQ sasl, it would be ok
        self.assertEqual(self.irc.takeMsg(), None)

        try:
            conf.supybot.networks.test.sasl.username.setValue('jilles')
            conf.supybot.networks.test.sasl.password.setValue('sesame')
            self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
                    args=('*', 'DEL', 'sasl')))
            self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
                    args=('*', 'NEW', 'sasl=PLAIN')))
        finally:
            conf.supybot.networks.test.sasl.username.setValue('')
            conf.supybot.networks.test.sasl.password.setValue('')

        m = self.irc.takeMsg()
        self.assertTrue(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args[0], 'REQ', m)
        self.assertEqual(m.args[1], 'sasl')
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'ACK', 'sasl')))

        m = self.irc.takeMsg()
        self.assertEqual(m, ircmsgs.IrcMsg(command='AUTHENTICATE',
            args=('PLAIN',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='AUTHENTICATE', args=('+',)))

        m = self.irc.takeMsg()
        self.assertEqual(m, ircmsgs.IrcMsg(command='AUTHENTICATE',
            args=('amlsbGVzAGppbGxlcwBzZXNhbWU=',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(command='900', args=('jilles',)))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='903', args=('jilles',)))



class IrcCallbackTestCase(SupyTestCase):
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
        commands = list(map(makeCommand, msgs))
        self.assertEqual(doCommandCatcher.L, commands)

    def testFirstCommands(self):
        try:
            originalNick = conf.supybot.nick()
            originalUser = conf.supybot.user()
            originalPassword = conf.supybot.networks.test.password()
            nick = 'nick'
            conf.supybot.nick.setValue(nick)
            user = 'user any user'
            conf.supybot.user.setValue(user)
            expected = [
                ircmsgs.IrcMsg(command='CAP', args=('LS', '302')),
                ircmsgs.nick(nick),
                ircmsgs.user('limnoria', user),
            ]
            irc = irclib.Irc('test')
            msgs = [irc.takeMsg()]
            while msgs[-1] is not None:
                msgs.append(irc.takeMsg())
            msgs.pop()
            self.assertEqual(msgs, expected)
            password = 'password'
            conf.supybot.networks.test.password.setValue(password)
            irc = irclib.Irc('test')
            msgs = [irc.takeMsg()]
            while msgs[-1] is not None:
                msgs.append(irc.takeMsg())
            msgs.pop()
            expected.insert(1, ircmsgs.password(password))
            self.assertEqual(msgs, expected)
        finally:
            conf.supybot.nick.setValue(originalNick)
            conf.supybot.user.setValue(originalUser)
            conf.supybot.networks.test.password.setValue(originalPassword)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

