###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

from supybot.test import *

import sys

import supybot.world as world

class StatusTestCase(PluginTestCase):
    plugins = ('Status',)
    def testNet(self):
        self.assertNotError('net')

    def testCpu(self):
        m = self.assertNotError('status cpu')
        self.assertFalse('kB kB' in m.args[1])
        self.assertFalse('None' in m.args[1], 'None in cpu output: %r.' % m)
        for s in ['linux', 'freebsd', 'openbsd', 'netbsd', 'darwin']:
            if sys.platform.startswith(s):
                self.assertTrue('B' in m.args[1] or 'KB' in m.args[1] or
                                'MB' in m.args[1],
                                'No memory string on supported platform.')
        try:
            original = conf.supybot.plugins.Status.cpu.get('children')()
            conf.supybot.plugins.Status.cpu.get('children').setValue(False)
            self.assertNotRegexp('cpu', 'children')
        finally:
            conf.supybot.plugins.Status.cpu.get('children').setValue(original)
            

    def testUptime(self):
        self.assertNotError('uptime')

    def testCmd(self):
        self.assertNotError('cmd')

    def testCommands(self):
        self.assertNotError('commands')

    def testLogfilesize(self):
        self.feedMsg('list')
        self.feedMsg('list Status')
        self.assertNotError('upkeep')

    def testThreads(self):
        self.assertNotError('threads')

    def testProcesses(self):
        self.assertNotError('processes')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

