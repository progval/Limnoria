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

class MiscTestCase(ChannelPluginTestCase, PluginDocumentation):
    plugins = ('Scheduler', 'Utilities')
    def testSeconds(self):
        self.assertResponse('seconds 1s', '1')
        self.assertResponse('seconds 10s', '10')
        self.assertResponse('seconds 1m', '60')
        self.assertResponse('seconds 1m 1s', '61')
        self.assertResponse('seconds 1h', '3600')
        self.assertResponse('seconds 1h 1s', '3601')
        self.assertResponse('seconds 1d', '86400')
        self.assertResponse('seconds 1d 1s', '86401')
        self.assertResponse('seconds 2s', '2')
        self.assertResponse('seconds 2m', '120')
        self.assertResponse('seconds 2d 2h 2m 2s', '180122')
        self.assertResponse('seconds 1s', '1')

    def testAddRemove(self):
        self.assertNotError('scheduler add [seconds 5s] echo foo bar baz')
        self.assertNoResponse(' ', 4)
        self.assertResponse(' ', 'foo bar baz')
        m = self.assertNotError('scheduler add 5 echo xyzzy')
        # Get id.
        id = None
        for s in m.args[1].split():
            s = s.lstrip('#')
            if s.isdigit():
                id = s
                break
        self.failUnless(id, 'Couldn\'t find id in reply.')
        self.assertNotError('scheduler remove %s' % id)
        self.assertNoResponse(' ', 5)

    def testRepeat(self):
        self.assertNotError('scheduler repeat repeater 5 echo foo bar baz')
        self.assertNotError(' ') # replySuccess
        self.assertNoResponse(' ', 4)
        self.assertResponse(' ', 'foo bar baz')
        self.assertNoResponse(' ', 4)
        self.assertResponse(' ', 'foo bar baz')
        self.assertNotError('scheduler remove repeater')
        self.assertNoResponse(' ', 5)


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

