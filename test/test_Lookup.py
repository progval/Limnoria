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

import os

try:
    import sqlite
except ImportError:
    sqlite = None

import conf

if sqlite:
    class LookupTestCase(PluginTestCase, PluginDocumentation):
        plugins = ('Lookup',)
        d = {
            'foo': 'bar',
            'bar': 'baz',
            'your mom': 'my mom',
            'foo\\:bar': 'baz',
        }
        def setUp(self):
            PluginTestCase.setUp(self)
            fd = file(os.path.join(conf.dataDir, 'foo.supyfact'), 'w')
            for k, v in self.d.iteritems():
                fd.write('%s:%s\n' % (k, v))
            fd.close()

        def test(self):
            self.assertNotError('lookup add test foo.supyfact')
            self.assertRegexp('test', r"(foo|bar|your mom): (bar|baz|my mom)")
            self.assertResponse('test foo', 'bar')
            self.assertResponse('test bar', 'baz')
            self.assertResponse('test your mom', 'my mom')
            self.assertError('test something not in there')
            self.assertResponse('test foo:bar', 'baz')
            self.assertNotError('lookup remove test')
            try:
                original = conf.replyWhenNotCommand
                conf.replyWhenNotCommand = True
                self.assertError('test foo')
            finally:
                conf.replyWhenNotCommand = original

        def testNotEscapingIOError(self):
            self.assertNotRegexp('lookup add foo asdlfkjsdalfkj', 'IOError')

        def testEmptyLines(self):
            fd = file(os.path.join(conf.dataDir, 'foo.supyfact'), 'a')
            fd.write('\n')
            fd.close()
            self.assertNotError('lookup add test foo.supyfact')
        


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

