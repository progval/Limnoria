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

import os

class PythonTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('Python',)
    def testPydoc(self):
        self.assertError('pydoc foobar')
        self.assertError('pydoc assert')
        self.assertNotError('pydoc str')
        self.assertNotError('pydoc list.reverse')
        if os.name == 'posix':
            self.assertNotRegexp('pydoc crypt.crypt', 'NameError')
            self.assertNotError('pydoc crypt.crypt')
            # .so modules don't have an __file__ in Windows.
            self.assertNotError('pydoc math.sin')
        self.assertNotError('pydoc string.translate')
        self.assertNotError('pydoc fnmatch.fnmatch')
        self.assertNotError('pydoc socket.socket')
        self.assertNotError('pydoc logging.Logger')
        self.assertNotRegexp('pydoc str.replace', r"^'")

    def testZen(self):
        self.assertNotError('zen')
        

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

