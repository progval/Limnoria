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

class FriendlyTestCase(PluginTestCase):
    plugins = ('Friendly',)
    def testExclaim(self):
        s = '%s!' % self.irc.nick
        self.assertResponse(s, s)

    def testGreet(self):
        self.assertNotError('heya, %s' % self.irc.nick)
        self.assertNotError('howdy %s' % self.irc.nick)
        self.assertNotError('hi, %s!' % self.irc.nick)
        self.assertNotRegexp('hi, %s' % self.irc.nick,
                             '^%s: ' % self.irc.nick)

    def testGoodbye(self):
        self.assertNotError('seeya %s!' % self.irc.nick)
        self.assertNotError('bye, %s.' % self.irc.nick)
        self.assertNotRegexp('bye, %s' % self.irc.nick,
                             '^%s: ' % self.irc.nick)

    def testBeGracious(self):
        self.assertNotError('thanks, %s' % self.irc.nick)
        self.assertNotError('thank you, %s' % self.irc.nick)
        self.assertNotError('thx %s' % self.irc.nick)
        self.assertNotError('%s: thx!' % self.irc.nick)
        self.assertNotRegexp('thanks, %s' % self.irc.nick,
                             '^%s: ' % self.irc.nick)



# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

