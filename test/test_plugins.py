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

import sets

import irclib
import plugins

class holder:
    users = sets.Set(map(str, range(1000)))

class FunctionsTestCase(SupyTestCase):
    class irc:
        class state:
            channels = {'#foo': holder()}
        nick = 'foobar'
    def testStandardSubstitute(self):
        msg = ircmsgs.privmsg('#foo', 'filler', prefix='biff!quux@xyzzy')
        s = plugins.standardSubstitute(self.irc, msg, '$rand')
        try:
            int(s)
        except ValueError:
            self.fail('$rand wasn\'t an int.')
        s = plugins.standardSubstitute(self.irc, msg, '$randomInt')
        try:
            int(s)
        except ValueError:
            self.fail('$randomint wasn\'t an int.')
        self.assertEqual(plugins.standardSubstitute(self.irc, msg, '$botnick'),
                         self.irc.nick)
        self.assertEqual(plugins.standardSubstitute(self.irc, msg, '$who'),
                         msg.nick)
        self.assertEqual(plugins.standardSubstitute(self.irc, msg, '$nick'),
                         msg.nick)
        self.assert_(plugins.standardSubstitute(self.irc, msg, '$randomdate'))
        q = plugins.standardSubstitute(self.irc,msg,'$randomdate\t$randomdate')
        dl = q.split('\t')
        if dl[0] == dl[1]:
            self.fail ('Two $randomdates in the same string were the same')
        q = plugins.standardSubstitute(self.irc, msg, '$randomint\t$randomint')
        dl = q.split('\t')
        if dl[0] == dl[1]:
            self.fail ('Two $randomints in the same string were the same')
        self.assert_(plugins.standardSubstitute(self.irc, msg, '$today'))
        self.assert_(plugins.standardSubstitute(self.irc, msg, '$now'))
        n = plugins.standardSubstitute(self.irc, msg, '$randnick')
        self.failUnless(n in self.irc.state.channels['#foo'].users)
        n = plugins.standardSubstitute(self.irc, msg, '$randomnick')
        self.failUnless(n in self.irc.state.channels['#foo'].users)
        n = plugins.standardSubstitute(self.irc, msg, '$randomnick '*100)
        L = n.split()
        self.failIf(all(L[0].__eq__, L), 'all $randomnicks were the same')
        c = plugins.standardSubstitute(self.irc, msg, '$channel')
        self.assertEqual(c, msg.args[0])









