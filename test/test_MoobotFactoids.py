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
    class FactoidsTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('MiscCommands', 'MoobotFactoids', 'UserCommands')
        def setUp(self):
            PluginTestCase.setUp(self)
            # Create a valid user to use
            self.prefix = 'foo!bar@baz'
            self.assertNotError('register tester moo')
            
        def testLiteral(self):
            self.assertError('literal moo') # no factoids yet
            self.assertNotError('moo is <reply>foo')
            self.assertRegexp('literal moo', '<reply>foo')
            self.assertNotError('moo2 is moo!')
            self.assertRegexp('literal moo2', 'moo!')
            self.assertNotError('moo3 is <action>foo')
            self.assertRegexp('literal moo3', '<action>foo')

        def testGetFactoid(self):
            self.assertNotError('moo is <reply>foo')
            self.assertRegexp('moo', 'foo')
            self.assertNotError('moo2 is moo!')
            self.assertRegexp('moo2', 'moo2 is moo!')
            self.assertNotError('moo3 is <action>foo')
            self.assertAction('moo3', 'foo')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

