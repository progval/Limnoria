###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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
import supybot.conf as conf
import time

class LaterTestCase(ChannelPluginTestCase):
    plugins = ('Later',)
    def testLaterWorksTwice(self):
        self.assertNotError('later tell foo bar')
        self.assertNotError('later tell foo baz')

    def testLaterRemove(self):
        self.assertNotError('later tell foo 1')
        self.assertNotError('later tell bar 1')
        self.assertRegexp('later notes', 'bar.*foo')
        self.assertNotError('later remove bar')
        self.assertNotRegexp('later notes', 'bar.*foo')
        self.assertRegexp('later notes', 'foo')

    def testLaterUndo(self):
        self.assertNotError('later tell foo 1')
        self.assertNotError('later tell bar 1')
        self.assertRegexp('later notes', 'bar.*foo')
        self.assertNotError('later undo foo')
        self.assertNotRegexp('later notes', 'bar.*foo')
        self.assertRegexp('later notes', 'bar')

    def testNickValidation(self):
        origconf = conf.supybot.protocols.irc.strictRfc()
        conf.supybot.protocols.irc.strictRfc.setValue('True')
        self.assertError('later tell 1foo bar')
        self.assertError('later tell foo$moo zoob')
        conf.supybot.protocols.irc.strictRfc.setValue(origconf)

    def testWildcard(self):
        self.assertNotError('later tell foo* stuff')
        self.assertNotError('later tell bar,baz more stuff')
        self.assertRegexp('later notes', 'bar.*foo')
        testPrefix = 'foo!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'something',
                                         prefix=testPrefix))
        m = self.getMsg(' ')
        self.assertEqual(str(m).strip(),
                'PRIVMSG #test :foo: Sent just now: <test> stuff')

    def testHostmask(self):
        self.assertNotError('later tell foo*!*@baz stuff')
        self.assertNotError('later tell bar,baz more stuff')
        self.assertRegexp('later notes', 'bar.*foo')

        testPrefix = 'foo!bar@baz2'
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'something',
                                         prefix=testPrefix))
        m = self.getMsg(' ')
        self.assertEqual(m, None)

        testPrefix = 'foo!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'something',
                                         prefix=testPrefix))
        m = self.getMsg(' ')
        self.assertEqual(str(m).strip(),
                'PRIVMSG #test :foo: Sent just now: <test> stuff')

    def testNoteExpiry(self):
        cb = self.irc.getCallback('Later')
        # add a note 40 days in the past
        cb._addNote('foo', 'test', 'some stuff', at=(time.time() - 3456000))
        self.assertRegexp('later notes', 'foo')
        self.assertNotError('later tell moo stuff')
        self.assertNotRegexp('later notes', 'foo')
        self.assertRegexp('later notes', 'moo')

    def testNoteSend(self):
        self.assertNotError('later tell foo stuff')
        self.assertNotError('later tell bar,baz more stuff')
        self.assertRegexp('later notes', 'bar.*foo')
        testPrefix = 'foo!bar@baz'
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'something',
                                         prefix=testPrefix))
        m = self.getMsg(' ')
        self.assertEqual(str(m).strip(),
                'PRIVMSG #test :foo: Sent just now: <test> stuff')
        self.assertNotRegexp('later notes', 'foo')
        self.assertRegexp('later notes', 'bar')

        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'something',
                                         prefix='baz!baz@qux'))
        m = self.getMsg(' ')
        self.assertEqual(str(m).strip(),
                'PRIVMSG #test :baz: Sent just now: <test> more stuff')

        real_time = time.time
        def fake_time():
            return real_time() + 62
        time.time = fake_time
        self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'something',
                                         prefix='bar!baz@qux'))
        m = self.getMsg(' ')
        self.assertEqual(str(m).strip(),
                'PRIVMSG #test :bar: Sent 1 minute ago: <test> more stuff')
        time.time = real_time

    def testSenderHostname(self):
        self.assertNotError('later tell foo stuff')
        testPrefix = 'foo!bar@baz'
        with conf.supybot.plugins.Later.format.senderHostname.context(True):
            self.irc.feedMsg(ircmsgs.privmsg(self.channel, 'something',
                                             prefix=testPrefix))
            m = self.getMsg(' ')
        self.assertEqual(str(m).strip(),
                'PRIVMSG #test :foo: Sent just now: <%s> stuff' % self.prefix)
 
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

