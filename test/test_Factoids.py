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

class FactoidsTestCase(ChannelPluginTestCase):
    plugins = ('Factoids',)
    def testRandomfactoid(self):
        self.assertError('randomfactoid')
        self.assertNotError('learn jemfinch as my primary author')
        self.assertRegexp('randomfactoid', 'primary author')

    def testLearn(self):
        self.assertNotError('learn jemfinch as my primary author')
        self.assertNotError('factoidinfo jemfinch')
        self.assertRegexp('whatis jemfinch', 'my primary author')
        self.assertRegexp('whatis JEMFINCH', 'my primary author')
        self.assertNotError('learn jemfinch as a crappy assembly programmer')
        self.assertRegexp('whatis jemfinch', r'.*primary author.*assembly')
        self.assertError('unlearn jemfinch')
        self.assertError('unlearn jemfinch 2')
        self.assertNotError('unlearn jemfinch 1')
        self.assertNotError('unlearn jemfinch 0')
        self.assertError('whatis jemfinch')
        self.assertError('factoidinfo jemfinch')

        self.assertNotError('learn foo bar as baz')
        self.assertNotError('factoidinfo foo bar')
        self.assertRegexp('whatis foo bar', 'baz')
        self.assertNotError('learn foo bar as quux')
        self.assertRegexp('whatis foo bar', '.*baz.*quux')
        self.assertError('unlearn foo bar')
        self.assertNotError('unlearn foo bar 1')
        self.assertNotError('unlearn foo bar 0')
        self.assertError('whatis foo bar')
        self.assertError('factoidinfo foo bar')
        
        self.assertRegexp('learn foo bar baz', '^learn') # No 'as'
        self.assertRegexp('learn foo bar', '^learn') # No 'as'

    def testSearchFactoids(self):
        self.assertNotError('learn jemfinch as my primary author')
        self.assertNotError('learn strike as another cool guy working on me')
        self.assertNotError('learn inkedmn as another of my developers')
        self.assertNotError('learn jamessan as a developer of much python')
        self.assertNotError('learn bwp as the author of my weather command')
        self.assertRegexp('searchfactoids /.w./', 'bwp')
        self.assertRegexp('searchfactoids /^.+i/', 'jemfinch.*strike')
        self.assertNotRegexp('searchfactoids /^.+i/', 'inkedmn')
        self.assertRegexp('searchfactoids /^j/', 'jemfinch.*jamessan')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

