#!/usr/bin/env python

###
# Copyright (c) 2003, James Vega
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

import re

from test import *

class SourceforgeTest(ChannelPluginTestCase, PluginDocumentation):
    plugins = ('Sourceforge',)
    def testBug(self):
        self.assertHelp('bug')
        m = self.getMsg('bugs gaim')
        n = re.search('#(\d+)', m.args[1]).group(1)
        self.assertNotError('bug gaim %s' % n)
        self.assertError('bug gaim')
        self.assertRegexp('bug lkadf 9', 'find the Bugs')

    def testBugs(self):
        self.assertHelp('bugs')
        self.assertNotError('config defaultproject supybot')
        self.assertNotError('bugs')
        self.assertRegexp('bugs alkjfi83fa8', 'find the Bugs')
        self.assertNotError('bugs gaim')
        self.assertNotError('config defaultproject')
        self.assertRegexp('bugs 83423', 'Use the bug command')

    def testRfe(self):
        m = self.getMsg('rfes gaim')
        n = re.search('#(\d+)', m.args[1]).group(1)
        self.assertNotError('rfe gaim %s' % n)
        self.assertError('rfe gaim')
        self.assertRegexp('rfe lakdf 9', 'find the RFEs')

    def testRfes(self):
        self.assertHelp('rfes')
        self.assertNotError('config defaultproject gaim')
        self.assertNotError('rfes')
        self.assertRegexp('rfes alkjfi83hfa8', 'find the RFEs')
        self.assertNotError('rfes gaim')
        self.assertNotError('config defaultproject')
        self.assertRegexp('rfes 83423', 'Use the rfe command')

    def testDefaultproject(self):
        self.assertHelp('bugs')
        self.assertNotError('config defaultproject supybot')
        self.assertNotError('bugs')
        m = self.getMsg('bugs')
        n = re.search('#(\d+)', m.args[1]).group(1)
        self.assertNotError('bug supybot %s' % n)
        # This should have the same effect as calling 'bug supybot %s'
        self.assertNotError('bug %s' % n)
        self.assertNotError('config defaultproject ""')

    def testSnarfer(self):
        s = r'.*Status.*: \w+'
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'
                          'func=detail&aid=589953&group_id=58965&atid=489447',
                          s)
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'
                          'func=detail&aid=712761&group_id=58965&atid=489450',
                          s)
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'
                          'func=detail&aid=540223&group_id=235&atid=300235', s)
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'
                          'func=detail&aid=561547&group_id=235&atid=200235', s)
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'
                          'func=detail&aid=400942&group_id=235&atid=390395', s)

        # test that it works without index.php
        self.assertNotError('http://sourceforge.net/tracker/?'
                            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works with www
        self.assertNotError('http://www.sourceforge.net/tracker/index.php?'
                            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works with www and without index.php
        self.assertNotError('http://www.sourceforge.net/tracker/?'
                            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works with sf.net
        self.assertNotError('http://sf.net/tracker/?'
                            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works
        self.assertNotError('https://sourceforge.net/tracker/?'
                            'func=detail&atid=105470&aid=827260&group_id=5470')
        self.assertNoResponse('https://sourceforge.net/tracker/?'
                              'group_id=58965&atid=489447')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

