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
        self.assertNotError('netstats')

    def testCpustats(self):
        try:
            original = world.startedAt
            world.startedAt = time.time()
            self.assertError('cpustats')
            world.startedAt = 0
            self.assertNotError('cpustats')
            for s in ['linux', 'freebsd', 'openbsd', 'netbsd']:
                if sys.platform.startswith(s):
                    self.assertRegexp('cpustats', 'kB')
        finally:
            world.startedAt = original
    def testUptime(self):
        self.assertNotError('uptime')

    def testCmdstats(self):
        self.assertNotError('cmdstats')

    def testCommands(self):
        self.assertNotError('commands')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

