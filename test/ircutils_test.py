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

import ircutils

class FunctionsTestCase(unittest.TestCase):
    hostmask = 'foo!bar@baz'
    def testIsUserHostmask(self):
        self.failUnless(ircutils.isUserHostmask(self.hostmask))
        self.failIf(ircutils.isUserHostmask('!bar@baz'))
        self.failIf(ircutils.isUserHostmask('!@baz'))
        self.failIf(ircutils.isUserHostmask('!bar@'))
        self.failIf(ircutils.isUserHostmask('!@'))
        self.failIf(ircutils.isUserHostmask('foo!@baz'))
        self.failIf(ircutils.isUserHostmask('foo!bar@'))
        self.failIf(ircutils.isUserHostmask(''))
        self.failIf(ircutils.isUserHostmask('!'))
        self.failIf(ircutils.isUserHostmask('@'))
        self.failIf(ircutils.isUserHostmask('!bar@baz'))
        self.failIf(ircutils.isUserHostmask('a!b@c'))

    def testIsChannel(self):
        self.failUnless(ircutils.isChannel('#'))
        self.failUnless(ircutils.isChannel('&'))
        self.failUnless(ircutils.isChannel('+'))
        self.failUnless(ircutils.isChannel('!'))
        self.failUnless(ircutils.isChannel('#foo'))
        self.failUnless(ircutils.isChannel('&foo'))
        self.failUnless(ircutils.isChannel('+foo'))
        self.failUnless(ircutils.isChannel('!foo'))
        self.failIf(ircutils.isChannel('foo'))
        self.failIf(ircutils.isChannel(''))

    def testIsIP(self):
        self.failIf(ircutils.isIP('a.b.c'))
        self.failUnless(ircutils.isIP('100.100.100.100'))

    def banmask(self):
        self.failUnless(ircutils.hostmaskPatternEqual(\
            ircutils.banmask(self.hostmask), self.hostmask))
                   
