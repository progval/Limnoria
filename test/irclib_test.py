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
        
        
