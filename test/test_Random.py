#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

import sets

iters = 100
class RandomTestCase(PluginTestCase):
    plugins = ('Random',)
    def testNoErrors(self):
        self.assertNotError('random')

    def testRange(self):
        for x in range(iters):
            self.assertRegexp('range 1 2', '^(1|2)$')
        
    def testDiceroll(self):
        for x in range(iters):
            self.assertActionRegexp('diceroll', '^rolls a (1|2|3|4|5|6)$')
    
    def testSample(self):
        for x in range(iters):
            self.assertRegexp('sample 1 a b c', '^(a|b|c)$')
        for x in range(iters):
            self.assertRegexp('sample 2 a b c', '^(a and b|a and c|b and c)$')
        self.assertResponse('sample 3 a b c', 'a, b, and c')

    def testSeed(self):
        self.assertNotError('seed 12')
        m1 = self.assertNotError('random')
        self.assertNotError('seed 13')
        m2 = self.assertNotError('random')
        self.assertNotError('seed 12')
        m3 = self.assertNotError('random')
        self.assertEqual(m1, m3)
        self.assertNotEqual(m1, m2)


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

