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

import sys

import world

class StatusTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('Status',)
    def testBestuptime(self):
        self.assertNotRegexp('bestuptime', '33 years')
        self.assertNotError('unload Status')
        self.assertNotError('load Status')
        self.assertNotError('bestuptime')

    def testNetstats(self):
        self.assertNotError('net')

    def testCpustats(self):
        m = self.assertNotError('status cpu')
        self.failIf('None' in m.args[1], 'None in cpu output: %r.' % m)
        for s in ['linux', 'freebsd', 'openbsd', 'netbsd', 'darwin']:
            if sys.platform.startswith(s):
                self.failUnless('kB' in m.args[1],
                                'No memory string on supported platform.')

    def testUptime(self):
        self.assertNotError('uptime')

    def testCmdstats(self):
        self.assertNotError('cmd')

    def testCommands(self):
        self.assertNotError('commands')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

