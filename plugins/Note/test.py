###
# Copyright (c) 2003, Brett Kelly
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

class NoteTestCase(PluginTestCase):
    plugins = ('Note', 'Misc', 'User')
    config = {'supybot.reply.whenNotCommand': False}
    def setUp(self):
        PluginTestCase.setUp(self)
        # setup a user
        self.prefix = 'foo!bar@baz'
        self.assertNotError('register inkedmn bar')
        self.assertNotError('hostmask add inkedmn test2!bar@baz')

    def testSendnote(self):
        self.assertRegexp('note send inkedmn test', '#1')
        # have to getMsg(' ') after each Note.send to absorb supybot's
        # automatic "You have an unread note" message
        _ = self.getMsg(' ')
        self.assertError('note send alsdkjfasldk foo')
        self.assertNotError('note send inkedmn test2')
        _ = self.getMsg(' ')
        # verify that sending a note to a user via their nick instead of their
        # ircdb user name works
        self.prefix = 'test2!bar@baz'
        self.assertNotError('note send test2 foo')
        _ = self.getMsg(' ')

    def testNote(self):
        self.assertNotError('note send inkedmn test')
        _ = self.getMsg(' ')
        self.assertRegexp('note 1', 'test')
        self.assertError('note blah')

    def testList(self):
        self.assertResponse('note list', 'You have no unread notes.')
        self.assertNotError('note send inkedmn testing')
        _ = self.getMsg(' ')
        self.assertNotError('note send inkedmn 1,2,3')
        _ = self.getMsg(' ')
        self.assertRegexp('note list --sent', r'#2.*#1')
        self.assertRegexp('note list --sent --to inkedmn', r'#2.*#1')
        self.assertRegexp('note list', r'#1.*#2')
        self.assertRegexp('note 1', 'testing')
        self.assertRegexp('note list --old', '#1 from inkedmn')
        self.assertRegexp('note list --old --from inkedmn','#1 from inkedmn')

    def testSearch(self):
        self.assertNotError('note send inkedmn testing')
        _ = self.getMsg(' ')
        self.assertNotError('note send inkedmn 1,2,3')
        _ = self.getMsg(' ')
        self.assertRegexp('note search test', r'#1')
        self.assertRegexp('note search --regexp m/1,2/', r'#2')
        self.assertRegexp('note search --sent test', r'#1')

    def testNext(self):
        self.assertNotError('note send inkedmn testing')
        _ = self.getMsg(' ')
        self.assertRegexp('note next', 'testing')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
