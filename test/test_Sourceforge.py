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

class SourceforgeTest(PluginTestCase, PluginDocumentation):
    plugins = ('Sourceforge',)
    def testBugs(self):
        self.assertNotError('bugs')
        self.assertResponse('bugs alkjfi83fa8', 'Can\'t find the "Bugs" link.')
        self.assertNotError('bugs gaim')
        m = self.getMsg('bugs gaim')
        n = re.search('#(\d+)', m.args[1]).group(1)
        self.assertNotError('bugs gaim %s' % n)

    def testRfes(self):
        self.assertNotError('rfes')
        self.assertResponse('rfes alkjfi83hfa8', 'Can\'t find the "RFE" link.')
        self.assertNotError('rfes gaim')
        m = self.getMsg('rfes gaim')
        n = re.search('#(\d+)', m.args[1]).group(1)
        self.assertNotError('rfes gaim %s' % n)

    def testSnarfer(self):
        s = r';.*Status.*: \w+;'
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=589953&group_id=58965&atid=489447', s)
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=712761&group_id=58965&atid=489450', s)
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=540223&group_id=235&atid=300235', s)
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=561547&group_id=235&atid=200235', s)
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=400942&group_id=235&atid=390395', s)

        # test that it works without index.php
        self.assertNotError('http://sourceforge.net/tracker/?'\
            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works with www
        self.assertNotError('http://www.sourceforge.net/tracker/index.php?'\
            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works with www and without index.php
        self.assertNotError('http://www.sourceforge.net/tracker/?'\
            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works with sf.net
        self.assertNotError('http://sf.net/tracker/?'\
            'func=detail&aid=540223&group_id=235&atid=300235')

    def testHttpsSnarfer(self):
        s = r';.*Status.*: \w+;'
        self.assertRegexp('https://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=589953&group_id=58965&atid=489447', s)
        self.assertRegexp('https://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=712761&group_id=58965&atid=489450', s)
        self.assertRegexp('https://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=540223&group_id=235&atid=300235', s)
        self.assertRegexp('https://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=561547&group_id=235&atid=200235', s)
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=400942&group_id=235&atid=390395', s)

        # test that it works without index.php
        self.assertNotError('https://sourceforge.net/tracker/?'\
            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works with www
        self.assertNotError('https://www.sourceforge.net/tracker/?'\
            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works with www and without index.php
        self.assertNotError('https://www.sourceforge.net/tracker/index.php?'\
            'func=detail&aid=540223&group_id=235&atid=300235')
        # test that it works with www and without index.php
        self.assertNotError('https://sf.net/tracker/index.php?'\
            'func=detail&aid=540223&group_id=235&atid=300235')

    def testDisablesfsnarfer(self):
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=540223&group_id=235&atid=300235', 
            r';.*Status.*: \w+;')
        self.assertNotError('togglesnarfer')
        self.assertNoResponse('http://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=540223&group_id=235&atid=300235')
        self.assertNotError('togglesnarfer')
        self.assertRegexp('http://sourceforge.net/tracker/index.php?'\
            'func=detail&aid=540223&group_id=235&atid=300235', 
            r';.*Status.*: \w+;')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

