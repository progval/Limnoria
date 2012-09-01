###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008, James McCoy
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
        self.assertNotRegexp('scheduler list', 'no.*commands')
        self.assertNoResponse(' ', 3)
        self.assertResponse(' ', 'testAddRemove')
        m = self.assertNotError('scheduler add 5 echo testAddRemove2')
        # Get id.
        id = None
        for s in m.args[1].split():
            s = s.lstrip('#')
            if s.isdigit():
                id = s
                break
        self.failUnless(id, 'Couldn\'t find id in reply.')
        self.assertNotError('scheduler remove %s' % id)
        self.assertNoResponse(' ', 5)

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
        self.assertNoResponse(' ', 5)

    def testRepeat(self):
        self.assertNotError('scheduler repeat repeater 5 echo testRepeat')
        self.assertResponse(' ', 'testRepeat')
        self.assertResponse('scheduler list', 'repeater: "echo testRepeat"')
        self.assertNoResponse(' ', 3)
        self.assertResponse(' ', 'testRepeat')
        self.assertNotError('scheduler remove repeater')
        self.assertNotRegexp('scheduler list', 'repeater')
        self.assertNoResponse(' ', 5)

    def testRepeatWorksWithNestedCommands(self):
        self.assertNotError('scheduler repeat foo 5 "echo foo [echo nested]"')
        self.assertResponse(' ', 'foo nested')
        self.assertNoResponse(' ', 3)
        self.assertResponse(' ', 'foo nested')
        self.assertNotError('scheduler remove foo')
        self.assertNoResponse(' ', 5)

    def testRepeatDisallowsIntegerNames(self):
        self.assertError('scheduler repeat 1234 1234 "echo NoIntegerNames"')

    def testRepeatDisallowsDuplicateNames(self):
        self.assertNotError('scheduler repeat foo 5 "echo foo"')
        self.assertError('scheduler repeat foo 5 "echo another foo fails"')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

