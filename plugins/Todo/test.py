###
# Copyright (c) 2003-2005, Daniel DiPaolo
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

class TodoTestCase(PluginTestCase):
    plugins = ('Todo', 'User', 'Config')
    _user1 = 'foo!bar@baz'
    _user2 = 'bar!foo@baz'
    def setUp(self):
        PluginTestCase.setUp(self)
        # Create a valid user to use
        self.prefix = self._user2
        self.assertNotError('register testy oom')
        self.prefix = self._user1
        self.assertNotError('register tester moo')

    def testTodo(self):
        # Should not error, but no tasks yet.
        self.assertNotError('todo')
        self.assertRegexp('todo', 'You have no tasks')
        # Add a task
        self.assertNotError('todo add wash my car')
        self.assertRegexp('todo', '#1: wash my car')
        # Check that task
        self.assertRegexp('todo 1',
                          r'Todo for tester: wash my car \(Added .*?\)')
        # Check that it lists all my tasks when given my name
        self.assertResponse('todo tester',
                            'Todo for tester: #1: wash my car')
        # Check pluralization
        self.assertNotError('todo add moo')
        self.assertRegexp('todo tester',
                          'Todos for tester: #1: wash my car and #2: moo')
        # Check error
        self.assertError('todo asfas')
        self.assertRegexp('todo asfas',
                          'Error: \'asfas\' is not a valid task')
        # Check priority sorting
        self.assertNotError('todo setpriority 1 100')
        self.assertNotError('todo setpriority 2 10')
        self.assertRegexp('todo', '#2: moo and #1: wash my car')
        # Check permissions
        self.prefix = self._user2
        self.assertError('todo tester')
        self.assertNotRegexp('todo tester', 'task id')
        self.prefix = self._user1
        self.assertNotError('todo tester')
        self.assertNotError('config plugins.Todo.allowThirdpartyReader True')
        self.prefix = self._user2
        self.assertNotError('todo tester')
        self.prefix = self._user1
        self.assertNotError('todo tester')

    def testAddtodo(self):
        self.assertNotError('todo add code a new plugin')
        self.assertNotError('todo add --priority=1000 fix all bugs')

    def testRemovetodo(self):
        self.nick = 'testy'
        self.prefix = self._user2
        self.assertNotError('todo add do something')
        self.assertNotError('todo add do something else')
        self.assertNotError('todo add do something again')
        self.assertNotError('todo remove 1')
        self.assertNotError('todo 1')
        self.nick = 'tester'
        self.prefix = self._user1
        self.assertNotError('todo add make something')
        self.assertNotError('todo add make something else')
        self.assertNotError('todo add make something again')
        self.assertNotError('todo remove 1 3')
        self.assertRegexp('todo 1', r'Inactive')
        self.assertRegexp('todo 3', r'Inactive')
        self.assertNotError('todo')

    def testSearchtodo(self):
        self.assertNotError('todo add task number one')
        self.assertRegexp('todo search task*', '#1: task number one')
        self.assertRegexp('todo search number', '#1: task number one')
        self.assertNotError('todo add task number two is much longer than'
                            ' task number one')
        self.assertRegexp('todo search task*',
                          '#1: task number one and #2: task number two is '
                          'much longer than task number...')
        self.assertError('todo search --regexp s/bustedregex')
        self.assertRegexp('todo search --regexp m/task/',
                          '#1: task number one and #2: task number two is '
                          'much longer than task number...')

    def testSetPriority(self):
        self.assertNotError('todo add --priority=1 moo')
        self.assertRegexp('todo 1',
                          r'moo, priority: 1 \(Added at .*?\)')
        self.assertNotError('setpriority 1 50')
        self.assertRegexp('todo 1',
                          r'moo, priority: 50 \(Added at .*?\)')
        self.assertNotError('setpriority 1 0')
        self.assertRegexp('todo 1', r'moo \(Added at .*?\)')

    def testChangeTodo(self):
        self.assertNotError('todo add moo')
        self.assertError('todo change 1 asdfas')
        self.assertError('todo change 1 m/asdfaf//')
        self.assertNotError('todo change 1 s/moo/foo/')
        self.assertRegexp('todo 1', r'Todo for tester: foo \(Added .*?\)')

    def testActiveInactiveTodo(self):
        self.assertNotError('todo add foo')
        self.assertNotError('todo add bar')
        self.assertRegexp('todo 1', 'Active')
        self.assertRegexp('todo 2', 'Active')
        self.assertNotError('todo remove 1')
        self.assertRegexp('todo 1', 'Inactive')
        self.assertRegexp('todo 2', 'Active')
        self.assertNotError('todo remove 2')
        self.assertRegexp('todo 2', 'Inactive')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
