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

class MiscCommandsTestCase(PluginTestCase):
    plugins = ('MiscCommands',)
    def testHelp(self):
        self.assertNotError('help list')
        self.assertNotError('help help')

    def testMorehelp(self):
        self.assertNotError('morehelp list')
        self.assertNotError('morehelp morehelp')

    def testList(self):
        self.assertNotError('list MiscCommands')
        self.assertNotError('list misccommands')

    def testBug(self):
        self.assertNotError('bug')

    def testVersion(self):
        self.assertNotError('version')

    def testSource(self):
        self.assertNotError('source')

    def testLogfilesize(self):
        self.assertNotError('logfilesize')

    def testGetprefixchar(self):
        self.assertNotError('getprefixchar')

    def testModuleof(self):
        self.assertResponse('moduleof moduleof', 'MiscCommands')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

