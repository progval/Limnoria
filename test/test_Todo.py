#!/usr/bin/env python

###
# Copyright (c) 2003, Daniel DiPaolo
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

try:
    import sqlite
except ImportError:
    sqlite = None

if sqlite is not None:
    class TodoTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('Todo', 'UserCommands')
        def setUp(self):
            PluginTestCase.setUp(self)
            # Create a valid user to use
            self.prefix = 'foo!bar@baz'
            self.assertNotError('register tester moo')

        def testTodo(self):
            # Should not error, but no tasks yet.
            self.assertNotError('todo')
            self.assertRegexp('todo', 'You have no tasks in your todo list.')
            # Add a task
            self.assertNotError('addtodo wash my car')
            self.assertRegexp('todo', '#1: wash my car')
            # Check that task
            self.assertNotError('todo 1')

        def testAddtodo(self):
            self.assertNotError('addtodo code a new plugin')
            self.assertNotError('addtodo --priority=1000 fix all bugs')

        def testRemovetodo(self):
            self.assertNotError('addtodo do something else')
            self.assertNotError('removetodo 1')

        def testSearchtodo(self):
            self.assertNotError('addtodo task number one')
            self.assertRegexp('searchtodo task*', '#1: task number one')
            self.assertNotError('addtodo task number two is much longer than'
                                ' task number one')
            self.assertRegexp('searchtodo task*', '#1: task number one and #2:'
                              ' task number two is much longer than task '
                              'number...')
            self.assertRegexp('searchtodo --exact "task number one"',
                              '#1: task number one')
            self.assertError('searchtodo --regexp s/bustedregex')
            self.assertRegexp('searchtodo --regexp m/task/', '#1: task number'
                              ' one and #2: task number two is much longer '
                              'than task number...')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

