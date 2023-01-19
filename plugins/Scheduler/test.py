###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008, James McCoy
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

import supybot.schedule as schedule

class SchedulerTestCase(ChannelPluginTestCase):
    plugins = ('Scheduler', 'Utilities')
    def tearDown(self):
        schedule.schedule.reset()
        ChannelPluginTestCase.tearDown(self)

    def testAddRemove(self):
        self.assertRegexp('scheduler list', 'no.*commands')
        m = self.assertNotError('scheduler add 5 echo testAddRemove')
        self.assertResponse(
            'scheduler list',
            '1 (in 4 seconds): "echo testAddRemove"')
        timeFastForward(2)
        self.assertNoResponse(' ', timeout=1)
        timeFastForward(2)
        self.assertResponse(' ', 'testAddRemove')
        m = self.assertNotError('scheduler add 5 echo testAddRemove2')
        # Get id.
        id = None
        for s in m.args[1].split():
            s = s.lstrip('#')
            if s.isdigit():
                id = s
                break
        self.assertTrue(id, 'Couldn\'t find id in reply.')
        self.assertNotError('scheduler remove %s' % id)
        timeFastForward(5)
        self.assertNoResponse(' ', timeout=1)

    # Need this test to run first so it has id 0 for its event
    def test00RemoveZero(self):
        id = None
        m = self.assertNotError('scheduler add 5 echo testRemoveZero')
        for s in m.args[1].split():
            s = s.lstrip('#')
            if s.isdigit():
                id = s
                break
        self.assertNotError('scheduler remove %s' % id)
        timeFastForward(5)
        self.assertNoResponse(' ', timeout=1)

    def testRemind(self):
        self.assertNotError('scheduler remind 5 testRemind')
        self.assertResponse(
            'scheduler list',
            '3 (in 4 seconds): "testRemind"')
        timeFastForward(3)
        self.assertNoResponse(' ', timeout=1)
        timeFastForward(3)
        self.assertResponse(' ', 'Reminder: testRemind')
        timeFastForward(5)
        self.assertNoResponse(' ', timeout=1)
        self.assertResponse(
            'scheduler list', 'There are currently no scheduled commands.')

    def testRepeat(self):
        self.assertRegexp('scheduler repeat repeater 5 echo testRepeat',
            'testRepeat')
        timeFastForward(5)
        self.assertResponse(' ', 'testRepeat')
        self.assertResponse(
            'scheduler list',
            'repeater (every 5 seconds, next run in 4 seconds): '
            '"echo testRepeat"')
        timeFastForward(3)
        self.assertNoResponse(' ', timeout=1)
        timeFastForward(2)
        self.assertResponse(' ', 'testRepeat')
        self.assertNotError('scheduler remove repeater')
        self.assertRegexp('scheduler list', 'no.*commands')
        timeFastForward(5)
        self.assertNoResponse(' ', timeout=1)

    def testRepeatDelay(self):
        self.assertNoResponse(
            'scheduler repeat --delay 5 repeater 20 echo testRepeat',
            timeout=1)
        timeFastForward(5)
        self.assertResponse(' ', 'testRepeat', timeout=1)
        timeFastForward(17)
        self.assertNoResponse(' ', timeout=1)
        timeFastForward(5)
        self.assertResponse(' ', 'testRepeat', timeout=1)

    def testRepeatWorksWithNestedCommands(self):
        self.assertRegexp('scheduler repeat foo 5 "echo foo [echo nested]"',
            'foo nested')
        timeFastForward(5)
        self.assertResponse(' ', 'foo nested')
        timeFastForward(3)
        self.assertNoResponse(' ', timeout=1)
        timeFastForward(2)
        self.assertResponse(' ', 'foo nested')
        self.assertNotError('scheduler remove foo')
        timeFastForward(5)
        self.assertNoResponse(' ', timeout=1)

    def testRepeatWorksWithNestedCommandsWithNoReply(self):
        # the 'trylater' command uses ircmsgs.privmsg + irc.noReply(),
        # similar to how the Anonymous plugin implements sending messages
        # to channels/users without .reply() (as it is technically not a
        # reply to the origin message)
        count = 0
        class TryLater(callbacks.Plugin):
            def trylater(self, irc, msg, args):
                nonlocal count
                msg = ircmsgs.privmsg(msg.nick, "%d %s" % (count, args))
                irc.queueMsg(msg)
                irc.noReply()
                count += 1

        cb = TryLater(self.irc)
        self.irc.addCallback(cb)
        try:
            self.assertResponse('scheduler repeat foo 5 "trylater [echo foo]"',
                "0 ['foo']")
            timeFastForward(5)
            self.assertResponse(' ', "1 ['foo']")
            timeFastForward(5)
            self.assertResponse(' ', "2 ['foo']")
        finally:
            self.irc.removeCallback('TryLater')

    def testRepeatDisallowsIntegerNames(self):
        self.assertError('scheduler repeat 1234 1234 "echo NoIntegerNames"')

    def testRepeatDisallowsDuplicateNames(self):
        self.assertNotError('scheduler repeat foo 5 "echo foo"')
        self.assertError('scheduler repeat foo 5 "echo another foo fails"')

    def testSinglePersistence(self):
        self.assertRegexp(
            'scheduler add 10 echo testSingle',
            '^The operation succeeded')

        self.assertNotError('unload Scheduler')
        schedule.schedule.reset()
        timeFastForward(20)
        self.assertNoResponse(' ', timeout=1)

        self.assertNotError('load Scheduler')
        self.assertResponse(' ', 'testSingle')

    def testRepeatPersistence(self):
        self.assertRegexp(
            'scheduler repeat repeater 20 echo testRepeat',
            'testRepeat')

        self.assertNotError('unload Scheduler')
        schedule.schedule.reset()
        timeFastForward(30)
        self.assertNoResponse(' ', timeout=1)

        self.assertNotError('load Scheduler')
        self.assertNoResponse(' ', timeout=1) # T+30 to T+31
        timeFastForward(5)
        self.assertNoResponse(' ', timeout=1) # T+36 to T+37
        timeFastForward(5)
        self.assertResponse(' ', 'testRepeat', timeout=1) # T+42

        timeFastForward(15)
        self.assertNoResponse(' ', timeout=1) # T+57 to T+58
        timeFastForward(5)
        self.assertResponse(' ', 'testRepeat', timeout=1) # T+64

        self.assertNotError('unload Scheduler')
        schedule.schedule.reset()
        timeFastForward(20)
        self.assertNoResponse(' ', timeout=1)

        self.assertNotError('load Scheduler')
        self.assertNoResponse(' ', timeout=1) # T+85 to T+86
        timeFastForward(10)
        self.assertNoResponse(' ', timeout=1) # T+95 to T+96
        timeFastForward(10)
        self.assertResponse(' ', 'testRepeat', timeout=1) # T+106


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

