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

import ircdb

class UserTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('User',)
    prefix1 = 'somethingElse!user@host.tld'
    prefix2 = 'EvensomethingElse!user@host.tld'
    def testRegisterUnregister(self):
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        self.assertError('register foo baz')
        self.failUnless(ircdb.users.getUserId('foo'))
        self.assertNotError('unregister foo bar')
        self.assertRaises(KeyError, ircdb.users.getUserId, 'foo')
        
    def testChangeUsername(self):
        self.prefix = self.prefix1
        self.assertNotError('register foo bar')
        self.prefix = self.prefix2
        self.assertNotError('register bar baz')
        self.prefix = self.prefix1
        self.assertError('changeusername foo bar')
        self.assertNotError('changeusername foo baz')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

