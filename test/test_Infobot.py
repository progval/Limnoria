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
    class InfobotTestCase(PluginTestCase):
        plugins = ('Infobot',)
        def testIsSnarf(self):
            self.assertNoResponse('foo is at http://bar.com/', 2)
            self.assertRegexp('foo?', r'foo.*is.*http://bar.com/')
            self.assertNoResponse('foo is at http://baz.com/', 2)
            self.assertNotRegexp('foo?', 'baz')

        def testAreSnarf(self):
            self.assertNoResponse('bars are dirty', 2)
            self.assertRegexp('bars?', 'bars.*are.*dirty')
            self.assertNoResponse('bars are not dirty', 2)
            self.assertNotRegexp('bars?', 'not')

        def testIsResponses(self):
            self.assertNoResponse('foo is bar', 2)
            self.assertRegexp('foo?', 'foo.*is.*bar')
            self.assertNoResponse('when is foo?', 2)
            self.assertNoResponse('why is foo?', 2)
            self.assertNoResponse('why foo?', 2)
            self.assertNoResponse('when is foo?', 2)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
