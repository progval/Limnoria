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

from testsupport import *

try:
    import sqlite
except ImportError:
    sqlite = None

if sqlite is not None:
    class QuotesTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('Quotes',)
        def test(self):
            self.assertRegexp('stats #foo', '0')
            self.assertRegexp('add #foo foo', 'Quote #1 added')
            self.assertRegexp('stats #foo', '1')
            self.assertResponse('get #foo --id 1', '#1: foo')
            self.assertResponse('get #foo 1', '#1: foo')
            self.assertRegexp('add #foo bar','Quote #2 added')
            self.assertResponse('get #foo 2', '#2: bar')
            self.assertResponse('get #foo --id 2', '#2: bar')
            self.assertRegexp('add #foo baz','Quote #3 added')
            self.assertRegexp('stats #foo', '3')
            self.assertResponse('get #foo 3', '#3: baz')
            self.assertRegexp('get #foo --regexp m/ba/', 'bar.*baz')
            self.assertRegexp('get #foo --regexp ba', 'bar.*baz')
            self.assertRegexp('get #foo --with bar', '#2: bar')
            self.assertRegexp('get #foo bar', '#2: bar')
            self.assertNotError('info #foo 1')
            self.assertNotError('random #foo')
            self.assertError('remove #foo 4')
            self.assertError('info #foo 4')
            self.assertNotError('get #foo 3')
            self.assertNotError('remove #foo 3')
            self.assertRegexp('stats #foo', '2')
            self.assertNotError('remove #foo 1')
            self.assertError('info #foo 3')
            self.assertError('info #foo 1')
            self.assertRegexp('random #foo', '#2')
            self.assertError('remove #foo 3')
            self.assertNotError('remove #foo 2')
            self.assertRegexp('stats #foo', '0')
            self.assertError('random #foo')



# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

