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

from supybot.test import *

import copy
import pickle

import supybot.conf as conf
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs

# The test framework used to provide these, but not it doesn't.  We'll add
# messages to as we find bugs (if indeed we find bugs).
msgs = []
rawmsgs = []

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
        self.failUnless(self.msg in q)
        q.dequeue()
        self.failUnless(self.msg in q)
        q.dequeue()
        self.failUnless(self.msg in q)
        q.dequeue()
        self.failIf(self.msg in q)

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
            self.failIf(q)
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
        self.failIf('jemfinch' in c.users)
        self.failUnless('jemfinch' in c1.users)

    def testCopy(self):
        c = irclib.ChannelState()
        c.addUser('jemfinch')
        c1 = copy.deepcopy(c)
        c.removeUser('jemfinch')
        self.failIf('jemfinch' in c.users)
        self.failUnless('jemfinch' in c1.users)

    def testAddUser(self):
        c = irclib.ChannelState()
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


class IrcStateTestCase(SupyTestCase):
    class FakeIrc:
        nick = 'nick'
        prefix = 'nick!user@host'
    irc = FakeIrc()
    def testKickRemovesChannel(self):
        st = irclib.IrcState()
        st.channels['#foo'] = irclib.ChannelState()
        m = ircmsgs.kick('#foo', self.irc.nick, prefix=self.irc.prefix)
        st.addMsg(self.irc, m)
        self.failIf('#foo' in st.channels)

    def testAddMsgRemovesOpsProperly(self):
        st = irclib.IrcState()
        st.channels['#foo'] = irclib.ChannelState()
        st.channels['#foo'].ops.add('bar')
        m = ircmsgs.mode('#foo', ('-o', 'bar'))
        st.addMsg(self.irc, m)
        self.failIf('bar' in st.channels['#foo'].ops)

    def testNickChangesChangeChannelUsers(self):
        st = irclib.IrcState()
        st.channels['#foo'] = irclib.ChannelState()
        st.channels['#foo'].addUser('@bar')
        self.failUnless('bar' in st.channels['#foo'].users)
        self.failUnless(st.channels['#foo'].isOp('bar'))
        st.addMsg(self.irc, ircmsgs.IrcMsg(':bar!asfd@asdf.com NICK baz'))
        self.failIf('bar' in st.channels['#foo'].users)
        self.failIf(st.channels['#foo'].isOp('bar'))
        self.failUnless('baz' in st.channels['#foo'].users)
        self.failUnless(st.channels['#foo'].isOp('baz'))

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
                self.failIf(len(state.history) > maxHistoryLength())
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
        self.failIf('#foo' in stateCopy.channels)

    def testJoin(self):
        st = irclib.IrcState()
        st.addMsg(self.irc, ircmsgs.join('#foo', prefix=self.irc.prefix))
        self.failUnless('#foo' in st.channels)
        self.failUnless(self.irc.nick in st.channels['#foo'].users)
        st.addMsg(self.irc, ircmsgs.join('#foo', prefix='foo!bar@baz'))
        self.failUnless('foo' in st.channels['#foo'].users)
        st2 = st.copy()
        st.addMsg(self.irc, ircmsgs.quit(prefix='foo!bar@baz'))
        self.failIf('foo' in st.channels['#foo'].users)
        self.failUnless('foo' in st2.channels['#foo'].users)


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
        self.failIf('bar' in st.channels['#foo'].ops)
        st.addMsg(self.irc, ircmsgs.op('#foo', 'bar'))
        self.failUnless('bar' in st.channels['#foo'].ops)
        st.addMsg(self.irc, ircmsgs.deop('#foo', 'bar'))
        self.failIf('bar' in st.channels['#foo'].ops)

        self.failIf('bar' in st.channels['#foo'].voices)
        st.addMsg(self.irc, ircmsgs.voice('#foo', 'bar'))
        self.failUnless('bar' in st.channels['#foo'].voices)
        st.addMsg(self.irc, ircmsgs.devoice('#foo', 'bar'))
        self.failIf('bar' in st.channels['#foo'].voices)

        self.failIf('bar' in st.channels['#foo'].halfops)
        st.addMsg(self.irc, ircmsgs.halfop('#foo', 'bar'))
        self.failUnless('bar' in st.channels['#foo'].halfops)
        st.addMsg(self.irc, ircmsgs.dehalfop('#foo', 'bar'))
        self.failIf('bar' in st.channels['#foo'].halfops)

    def testDoModeOnlyChannels(self):
        st = irclib.IrcState()
        self.assert_(st.addMsg(self.irc, ircmsgs.IrcMsg('MODE foo +i')) or 1)


class IrcTestCase(SupyTestCase):
    def setUp(self):
        self.irc = irclib.Irc('test')

        #m = self.irc.takeMsg()
        #self.failUnless(m.command == 'PASS', 'Expected PASS, got %r.' % m)

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.failUnless(m.args == ('LS', '302'), 'Expected CAP LS 302, got %r.' % m)

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'NICK', 'Expected NICK, got %r.' % m)

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'USER', 'Expected USER, got %r.' % m)

        # TODO
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', '*', 'account-tag multi-prefix')))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', 'extended-join')))

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args[0], 'REQ', m)
        # NOTE: Capabilities are requested in alphabetic order, because
        # sets are unordered, and their "order" is nondeterministic.
        self.assertEqual(m.args[1], 'account-tag extended-join multi-prefix')

        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'ACK', 'account-tag multi-prefix extended-join')))

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args, ('END',), m)

        m = self.irc.takeMsg()
        self.failUnless(m is None, m)

    def testPingResponse(self):
        self.irc.feedMsg(ircmsgs.ping('123'))
        self.assertEqual(ircmsgs.pong('123'), self.irc.takeMsg())

    def test433Response(self):
        # This is necessary; it won't change nick if irc.originalName==irc.nick
        self.irc.nick = 'somethingElse'
        self.irc.feedMsg(ircmsgs.IrcMsg('433 * %s :Nickname already in use.' %\
                                        self.irc.nick))
        msg = self.irc.takeMsg()
        self.failUnless(msg.command == 'NICK' and msg.args[0] != self.irc.nick)
        self.irc.feedMsg(ircmsgs.IrcMsg('433 * %s :Nickname already in use.' %\
                                        self.irc.nick))
        msg = self.irc.takeMsg()
        self.failUnless(msg.command == 'NICK' and msg.args[0] != self.irc.nick)

    def testSendBeforeQueue(self):
        while self.irc.takeMsg() is not None:
            self.irc.takeMsg()
        self.irc.queueMsg(ircmsgs.IrcMsg('NOTICE #foo bar'))
        self.irc.sendMsg(ircmsgs.IrcMsg('PRIVMSG #foo yeah!'))
        msg = self.irc.takeMsg()
        self.failUnless(msg.command == 'PRIVMSG')
        msg = self.irc.takeMsg()
        self.failUnless(msg.command == 'NOTICE')

    def testNoMsgLongerThan512(self):
        self.irc.queueMsg(ircmsgs.privmsg('whocares', 'x'*1000))
        msg = self.irc.takeMsg()
        self.failUnless(len(msg) <= 512, 'len(msg) was %s' % len(msg))

    def testReset(self):
        for msg in msgs:
            try:
                self.irc.feedMsg(msg)
            except:
                pass
        self.irc.reset()
        self.failIf(self.irc.state.history)
        self.failIf(self.irc.state.channels)
        self.failIf(self.irc.outstandingPing)

    def testHistory(self):
        self.irc.reset()
        msg1 = ircmsgs.IrcMsg('PRIVMSG #linux :foo bar baz!')
        self.irc.feedMsg(msg1)
        self.assertEqual(self.irc.state.history[0], msg1)
        msg2 = ircmsgs.IrcMsg('JOIN #sourcereview')
        self.irc.feedMsg(msg2)
        self.assertEqual(list(self.irc.state.history), [msg1, msg2])

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
        self.irc.feedMsg(ircmsgs.IrcMsg(':host BATCH +name netjoin'))
        m1 = ircmsgs.IrcMsg('@batch=name :someuser2 JOIN #foo')
        self.irc.feedMsg(m1)
        self.irc.feedMsg(ircmsgs.IrcMsg(':someuser3 JOIN #foo'))
        m2 = ircmsgs.IrcMsg('@batch=name :someuser4 JOIN #foo')
        self.irc.feedMsg(m2)
        class Callback(irclib.IrcCallback):
            batch = None
            def name(self):
                return 'testcallback'
            def doBatch(self2, irc, msg):
                self2.batch = msg.tagged('batch')
        c = Callback()
        self.irc.addCallback(c)
        try:
            self.irc.feedMsg(ircmsgs.IrcMsg(':host BATCH -name'))
        finally:
            self.irc.removeCallback(c.name())
        self.assertEqual(c.batch, irclib.Batch('netjoin', (), [m1, m2]))

class SaslTestCase(SupyTestCase):
    def setUp(self):
        pass

    def startCapNegociation(self, caps='sasl'):
        m = self.irc.takeMsg()
        self.failUnless(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.failUnless(m.args == ('LS', '302'), 'Expected CAP LS 302, got %r.' % m)

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'NICK', 'Expected NICK, got %r.' % m)

        m = self.irc.takeMsg()
        self.failUnless(m.command == 'USER', 'Expected USER, got %r.' % m)

        self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
            args=('*', 'LS', caps)))

        if caps:
            m = self.irc.takeMsg()
            self.failUnless(m.command == 'CAP', 'Expected CAP, got %r.' % m)
            self.assertEqual(m.args[0], 'REQ', m)
            self.assertEqual(m.args[1], 'sasl')

            self.irc.feedMsg(ircmsgs.IrcMsg(command='CAP',
                args=('*', 'ACK', 'sasl')))

    def endCapNegociation(self):
        m = self.irc.takeMsg()
        self.failUnless(m.command == 'CAP', 'Expected CAP, got %r.' % m)
        self.assertEqual(m.args, ('END',), m)

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
        self.failUnless(m.command == 'CAP', 'Expected CAP, got %r.' % m)
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

