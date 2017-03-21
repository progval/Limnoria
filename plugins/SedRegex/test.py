###
# Copyright (c) 2017, James Lu <james@overdrivenetworks.com>
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

from __future__ import print_function
from supybot.test import *

class SedRegexTestCase(ChannelPluginTestCase):
    other = "blah!blah@someone.else"
    other2 = "ghost!ghost@spooky"

    plugins = ('SedRegex', 'Utilities')
    config = {'plugins.sedregex.enable': True,
              'plugins.sedregex.boldReplacementText': False}

    # getMsg() stalls if no message is ever sent (i.e. if the plugin fails to respond to a request)
    # We should limit the timeout to prevent the tests from taking forever.
    timeout = 3

    def testSimpleReplace(self):
        self.feedMsg('Abcd abcdefgh')
        self.feedMsg('s/abcd/test/')
        # Run an empty command so that messages from the previous trigger are caught.
        m = self.getMsg(' ')
        self.assertIn('Abcd testefgh', str(m))

    def testCaseInsensitiveReplace(self):
        self.feedMsg('Aliens Are Invading, Help!')
        self.feedMsg('s/a/e/i')
        m = self.getMsg(' ')
        self.assertIn('eliens', str(m))

    def testGlobalReplace(self):
        self.feedMsg('AAaa aaAa a b')
        self.feedMsg('s/a/e/g')
        m = self.getMsg(' ')
        self.assertIn('AAee eeAe e b', str(m))

    def testGlobalCaseInsensitiveReplace(self):
        self.feedMsg('Abba')
        self.feedMsg('s/a/e/gi')
        m = self.getMsg(' ')
        self.assertIn('ebbe', str(m))

    def testOnlySelfReplace(self):
        self.feedMsg('evil machines')
        self.feedMsg('evil tacocats', frm=self.__class__.other)
        self.feedMsg('s/evil/kind/s')
        m = self.getMsg(' ')
        self.assertIn('kind machines', str(m))

    def testAllFlagsReplace(self):
        self.feedMsg('Terrible, terrible crimes')
        self.feedMsg('Terrible, terrible TV shows', frm=self.__class__.other)
        self.feedMsg('s/terr/horr/sgi')
        m = self.getMsg(' ')
        self.assertIn('horrible, horrible crimes', str(m))

    def testOtherPersonReplace(self):
        self.feedMsg('yeah, right', frm=self.__class__.other)
        self.feedMsg('s/right/left/', frm=self.__class__.other2)
        m = self.getMsg(' ')
        # Note: using the bot prefix for the s/right/left/ part causes the first nick in "X thinks Y"
        # to be empty? It works fine in runtime though...
        self.assertIn('%s thinks %s meant to say' % (ircutils.nickFromHostmask(self.__class__.other2),
                                                     ircutils.nickFromHostmask(self.__class__.other)), str(m))

    def testExplicitOtherReplace(self):
        self.feedMsg('ouch', frm=self.__class__.other2)
        self.feedMsg('poof', frm=self.__class__.other)
        self.feedMsg('wow!')
        self.feedMsg('%s: s/^/p/' % ircutils.nickFromHostmask(self.__class__.other2))
        m = self.getMsg(' ')
        self.assertIn('pouch', str(m))

    def testBoldReplacement(self):
        with conf.supybot.plugins.sedregex.boldReplacementText.context(True):
            self.feedMsg('hahahaha', frm=self.__class__.other)

            # One replacement
            self.feedMsg('s/h/H/', frm=self.__class__.other2)
            m = self.getMsg(' ')
            self.assertIn('\x02H\x02aha', str(m))

            # Replace all instances
            self.feedMsg('s/h/H/g', frm=self.__class__.other2)
            m = self.getMsg(' ')
            self.assertIn('\x02H\x02a\x02H\x02a', str(m))

            # One whole word
            self.feedMsg('sweet dreams are made of this', frm=self.__class__.other)
            self.feedMsg('s/this/cheese/', frm=self.__class__.other2)
            m = self.getMsg(' ')
            self.assertIn('of \x02cheese\x02', str(m))

    def testNonSlashSeparator(self):
        self.feedMsg('we are all decelopers on this blessed day')
        self.feedMsg('s.c.v.')
        m = self.getMsg(' ')
        self.assertIn('developers', str(m))

        self.feedMsg('4 / 2 = 8')
        self.feedMsg('s@/@*@')
        m = self.getMsg(' ')
        self.assertIn('4 * 2 = 8', str(m))

    def testWeirdSeparatorsFail(self):
        self.feedMsg("can't touch this", frm=self.__class__.other)
        # Only symbols are allowed as separators
        self.feedMsg('blah: s a b ')
        self.feedMsg('blah: sdadbd')

        m = self.getMsg('echo dummy message')
        # XXX: this is a total hack...
        for msg in self.irc.state.history:
            print("Message in history: %s" % msg, end='')
            self.assertNotIn("cbn't", str(msg))

    def testActionReplace(self):
        self.feedMsg("\x01ACTION sleeps\x01")
        self.feedMsg('s/sleeps/wakes/')

        m = self.getMsg(' ')
        self.assertIn('meant to say: * %s wakes' % self.nick, str(m))

    def testOtherPersonActionReplace(self):
        self.feedMsg("\x01ACTION sleeps\x01", frm=self.__class__.other)
        self.feedMsg('s/sleeps/wakes/')
        m = self.getMsg(' ')
        n = ircutils.nickFromHostmask(self.__class__.other)
        self.assertIn('thinks %s meant to say: * %s wakes' % (n, n), str(m))

    # TODO: test ignores

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
