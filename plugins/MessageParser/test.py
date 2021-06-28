###
# Copyright (c) 2010, Daniel Folkinshteyn
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

import sqlite3


class MessageParserTestCase(ChannelPluginTestCase):
    plugins = ('MessageParser','Utilities','User')
    #utilities for the 'echo'
    #user for register for testVacuum

    def testAdd(self):
        self.assertError('messageparser add') #no args
        self.assertError('messageparser add "stuff"') #no action arg
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertRegexp('messageparser show "stuff"', '.*i saw some stuff.*')

        self.assertError('messageparser add "[a" "echo stuff"') #invalid regexp
        self.assertError('messageparser add "(a" "echo stuff"') #invalid regexp
        self.assertNotError('messageparser add "stuff" "echo i saw no stuff"') #overwrite existing regexp
        self.assertRegexp('messageparser show "stuff"', '.*i saw no stuff.*')


        try:
            world.testing = False
            origuser = self.prefix
            self.prefix = 'stuff!stuff@stuff'
            self.assertNotError('register nottester stuff', private=True)

            self.assertError('messageparser add "aoeu" "echo vowels are nice"')
            origconf = conf.supybot.plugins.MessageParser.requireManageCapability()
            conf.supybot.plugins.MessageParser.requireManageCapability.setValue('')
            self.assertNotError('messageparser add "aoeu" "echo vowels are nice"')
        finally:
            world.testing = True
            self.prefix = origuser
            conf.supybot.plugins.MessageParser.requireManageCapability.setValue(origconf)

    def testGroups(self):
        self.assertNotError('messageparser add "this (.+) a(.*)" "echo $1 $2"')
        self.feedMsg('this is a foo')
        self.assertResponse(' ', 'is foo')
        self.feedMsg('this is a')
        self.assertResponse(' ', 'is')
        self.assertNotError('messageparser remove "this (.+) a(.*)"')
        self.assertNotError('messageparser add "this (.+) a(.*)" "echo $1"')
        self.feedMsg('this is a foo')
        self.assertResponse(' ', 'is')
        self.feedMsg('this is a')
        self.assertResponse(' ', 'is')
        self.assertNotError('messageparser remove "this (.+) a(.*)"')
        self.assertNotError('messageparser add "this( .+)? a(.*)" "echo $1 $2"')
        self.feedMsg('this a foo')
        self.assertResponse(' ', '$1 foo')
        self.feedMsg('this a')
        self.assertResponse(' ', '$1')
        self.assertNotError('messageparser remove "this( .+)? a(.*)"')

    def testSyntaxError(self):
        self.assertNotError(r'messageparser add "test" "echo foo \" bar"')
        self.feedMsg('test')
        self.assertResponse(' ', 'Error: No closing quotation')

    def testShow(self):
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertRegexp('messageparser show "nostuff"', 'there is no such regexp trigger')
        self.assertRegexp('messageparser show "stuff"', '.*i saw some stuff.*')
        self.assertRegexp('messageparser show --id 1', '.*i saw some stuff.*')

    def testInfo(self):
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertRegexp('messageparser info "nostuff"', 'there is no such regexp trigger')
        self.assertRegexp('messageparser info "stuff"', '.*i saw some stuff.*')
        self.assertRegexp('messageparser info --id 1', '.*i saw some stuff.*')
        self.assertRegexp('messageparser info "stuff"', 'has been triggered 0 times')
        self.feedMsg('this message has some stuff in it')
        self.getMsg(' ')
        self.assertRegexp('messageparser info "stuff"', 'has been triggered 1 times')

    def testTrigger(self):
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.feedMsg('this message has some stuff in it')
        m = self.getMsg(' ')
        self.assertTrue(str(m).startswith('PRIVMSG #test :i saw some stuff'))

    def testMaxTriggers(self):
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertNotError('messageparser add "sbd" "echo i saw somebody"')
        self.feedMsg('this message issued by sbd has some stuff in it')
        m = self.getMsg(' ')
        self.assertTrue(str(m).startswith('PRIVMSG #test :i saw some'))
        m = self.getMsg(' ')
        self.assertTrue(str(m).startswith('PRIVMSG #test :i saw some'))

        with conf.supybot.plugins.messageparser.maxtriggers.context(1):
            self.feedMsg('this message issued by sbd has some stuff in it')
            m = self.getMsg(' ')
            self.assertTrue(str(m).startswith('PRIVMSG #test :i saw some'))
            m = self.getMsg(' ')
            self.assertFalse(m)

    def testLock(self):
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertNotError('messageparser lock "stuff"')
        self.assertError('messageparser add "stuff" "echo some other stuff"')
        self.assertError('messageparser remove "stuff"')
        self.assertRegexp('messageparser info "stuff"', 'is locked')

    def testUnlock(self):
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertNotError('messageparser lock "stuff"')
        self.assertError('messageparser remove "stuff"')
        self.assertNotError('messageparser unlock "stuff"')
        self.assertRegexp('messageparser info "stuff"', 'is not locked')
        self.assertNotError('messageparser remove "stuff"')

    def testRank(self):
        self.assertRegexp('messageparser rank',
                          r'There are no regexp triggers in the database\.')
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertRegexp('messageparser rank', r'#1 "stuff" \(0\)')
        self.assertNotError('messageparser add "aoeu" "echo vowels are nice!"')
        self.assertRegexp('messageparser rank', r'#1 "stuff" \(0\), #2 "aoeu" \(0\)')
        self.feedMsg('instead of asdf, dvorak has aoeu')
        self.getMsg(' ')
        self.assertRegexp('messageparser rank', r'#1 "aoeu" \(1\), #2 "stuff" \(0\)')

    def testList(self):
        self.assertRegexp('messageparser list',
                          r'There are no regexp triggers in the database\.')
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertRegexp('messageparser list', '\x02#1\x02: stuff')
        self.assertNotError('messageparser add "aoeu" "echo vowels are nice!"')
        self.assertRegexp('messageparser list', '\x02#1\x02: stuff, \x02#2\x02: aoeu')

    def testRemove(self):
        self.assertError('messageparser remove "stuff"')
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertNotError('messageparser lock "stuff"')
        self.assertError('messageparser remove "stuff"')
        self.assertNotError('messageparser unlock "stuff"')
        self.assertNotError('messageparser remove "stuff"')
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertNotError('messageparser remove --id 1')

    def testVacuum(self):
        self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
        self.assertNotError('messageparser remove "stuff"')
        self.assertNotError('messageparser vacuum')
        # disable world.testing since we want new users to not
        # magically be endowed with the admin capability
        try:
            world.testing = False
            original = self.prefix
            self.prefix = 'stuff!stuff@stuff'
            self.assertNotError('register nottester stuff', private=True)
            self.assertError('messageparser vacuum')

            orig = conf.supybot.plugins.MessageParser.requireVacuumCapability()
            conf.supybot.plugins.MessageParser.requireVacuumCapability.setValue('')
            self.assertNotError('messageparser vacuum')
        finally:
            world.testing = True
            self.prefix = original
            conf.supybot.plugins.MessageParser.requireVacuumCapability.setValue(orig)

    def testKeepRankInfo(self):
        orig = conf.supybot.plugins.MessageParser.keepRankInfo()

        try:
            conf.supybot.plugins.MessageParser.keepRankInfo.setValue(False)
            self.assertNotError('messageparser add "stuff" "echo i saw some stuff"')
            self.feedMsg('instead of asdf, dvorak has aoeu')
            self.getMsg(' ')
            self.assertRegexp('messageparser info "stuff"', 'has been triggered 0 times')
        finally:
            conf.supybot.plugins.MessageParser.keepRankInfo.setValue(orig)

        self.feedMsg('this message has some stuff in it')
        self.getMsg(' ')
        self.assertRegexp('messageparser info "stuff"', 'has been triggered 1 times')

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
