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

class QuotesTestCase(PluginTestCase):
    plugins = ('Quotes',)
    def test(self):
        self.assertRegexp('numquotes #foo', '0')
        self.assertNotError('addquote #foo foo')
        self.assertRegexp('numquotes #foo', '1')
        self.assertResponse('quote #foo --id 1', '#1: foo')
        self.assertResponse('quote #foo 1', '#1: foo')
        self.assertNotError('addquote #foo bar')
        self.assertResponse('quote #foo 2', '#2: bar')
        self.assertResponse('quote #foo --id 2', '#2: bar')
        self.assertNotError('addquote #foo baz')
        self.assertRegexp('numquotes #foo', '3')
        self.assertResponse('quote #foo 3', '#3: baz')
        self.assertRegexp('quote #foo --regexp m/ba/', 'bar.*baz')
        self.assertRegexp('quote #foo --regexp ba', 'bar.*baz')
        self.assertNotError('quoteinfo #foo 1')
        self.assertNotError('randomquote #foo')
        self.assertError('removequote #foo 4')
        self.assertError('quoteinfo #foo 4')
        self.assertNotError('removequote #foo 3')
        self.assertRegexp('numquotes #foo', '2')
        self.assertNotError('removequote #foo 1')
        self.assertError('quoteinfo #foo 3')
        self.assertError('quoteinfo #foo 1')
        self.assertRegexp('randomquote #foo', '#2')
        self.assertError('removequote #foo 3')
        self.assertNotError('removequote #foo 2')
        self.assertRegexp('numquotes #foo', '0')
        self.assertError('randomquote #foo')

    

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

