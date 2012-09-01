###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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

try:
    import sqlite
except ImportError:
    sqlite = None

if sqlite:
    class FactoidsTestCase(ChannelPluginTestCase):
        plugins = ('Factoids',)
        def testRandomfactoid(self):
            self.assertError('random')
            self.assertNotError('learn jemfinch as my primary author')
            self.assertRegexp('random', 'primary author')

        def testLearn(self):
            self.assertError('learn as my primary author')
            self.assertError('learn jemfinch as')
            self.assertNotError('learn jemfinch as my primary author')
            self.assertNotError('info jemfinch')
            self.assertRegexp('whatis jemfinch', 'my primary author')
            self.assertRegexp('whatis JEMFINCH', 'my primary author')
            self.assertRegexp('whatis JEMFINCH 1', 'my primary author')
            self.assertNotError('learn jemfinch as a bad assembly programmer')
            self.assertRegexp('whatis jemfinch 2', 'bad assembly')
            self.assertNotRegexp('whatis jemfinch 2', 'primary author')
            self.assertRegexp('whatis jemfinch', r'.*primary author.*assembly')
            self.assertError('forget jemfinch')
            self.assertError('forget jemfinch 3')
            self.assertError('forget jemfinch 0')
            self.assertNotError('forget jemfinch 2')
            self.assertNotError('forget jemfinch 1')
            self.assertError('whatis jemfinch')
            self.assertError('info jemfinch')

            self.assertNotError('learn foo bar as baz')
            self.assertNotError('info foo bar')
            self.assertRegexp('whatis foo bar', 'baz')
            self.assertNotError('learn foo bar as quux')
            self.assertRegexp('whatis foo bar', '.*baz.*quux')
            self.assertError('forget foo bar')
            self.assertNotError('forget foo bar 2')
            self.assertNotError('forget foo bar 1')
            self.assertError('whatis foo bar')
            self.assertError('info foo bar')

            self.assertError('learn foo bar baz') # No 'as'
            self.assertError('learn foo bar') # No 'as'

        def testChangeFactoid(self):
            self.assertNotError('learn foo as bar')
            self.assertNotError('change foo 1 s/bar/baz/')
            self.assertRegexp('whatis foo', 'baz')
            self.assertError('change foo 2 s/bar/baz/')
            self.assertError('change foo 0 s/bar/baz/')

        def testSearchFactoids(self):
            self.assertNotError('learn jemfinch as my primary author')
            self.assertNotError('learn strike as a cool guy working on me')
            self.assertNotError('learn inkedmn as another of my developers')
            self.assertNotError('learn jamessan as a developer of much python')
            self.assertNotError('learn bwp as author of my weather command')
            self.assertRegexp('factoids search --regexp /.w./', 'bwp')
            self.assertRegexp('factoids search --regexp /^.+i/',
                              'jemfinch.*strike')
            self.assertNotRegexp('factoids search --regexp /^.+i/', 'inkedmn')
            self.assertRegexp('factoids search --regexp m/j/ --regexp m/ss/',
                              'jamessan')
            self.assertRegexp('factoids search --regexp m/^j/ *ss*',
                              'jamessan')
            self.assertRegexp('factoids search --regexp /^j/',
                              'jemfinch.*jamessan')
            self.assertRegexp('factoids search j*', 'jemfinch.*jamessan')
            self.assertRegexp('factoids search *ke*',
                              'inkedmn.*strike|strike.*inkedmn')
            self.assertRegexp('factoids search ke',
                              'inkedmn.*strike|strike.*inkedmn')
            self.assertRegexp('factoids search jemfinch',
                              'my primary author')
            self.assertRegexp('factoids search --values primary author',
                              'my primary author')

        def testWhatisOnNumbers(self):
            self.assertNotError('learn 911 as emergency number')
            self.assertRegexp('whatis 911', 'emergency number')

        def testNotZeroIndexed(self):
            self.assertNotError('learn foo as bar')
            self.assertNotRegexp('info foo', '#0')
            self.assertNotRegexp('whatis foo', '#0')
            self.assertNotError('learn foo as baz')
            self.assertNotRegexp('info foo', '#0')
            self.assertNotRegexp('whatis foo', '#0')

        def testInfoReturnsRightNumber(self):
            self.assertNotError('learn foo as bar')
            self.assertNotRegexp('info foo', '2 factoids')

        def testLearnSeparator(self):
            self.assertError('learn foo is bar')
            self.assertNotError('learn foo as bar')
            self.assertRegexp('whatis foo', 'bar')
            orig = conf.supybot.plugins.Factoids.learnSeparator()
            try:
                conf.supybot.plugins.Factoids.learnSeparator.setValue('is')
                self.assertError('learn bar as baz')
                self.assertNotError('learn bar is baz')
                self.assertRegexp('whatis bar', 'baz')
            finally:
                conf.supybot.plugins.Factoids.learnSeparator.setValue(orig)

        def testShowFactoidIfOnlyOneMatch(self):
            m1 = self.assertNotError('factoids search m/foo|bar/')
            orig = conf.supybot.plugins.Factoids.showFactoidIfOnlyOneMatch()
            try:
                conf.supybot.plugins.Factoids. \
                    showFactoidIfOnlyOneMatch.setValue(False)
                m2 = self.assertNotError('factoids search m/foo/')
                self.failUnless(m1.args[1].startswith(m2.args[1]))
            finally:
                conf.supybot.plugins.Factoids. \
                    showFactoidIfOnlyOneMatch.setValue(orig)

        def testInvalidCommand(self):
            orig = conf.supybot.plugins.Factoids.replyWhenInvalidCommand()
            try:
                conf.supybot.plugins.Factoids.\
                    replyWhenInvalidCommand.setValue(True)
                self.assertNotError('learn foo as bar')
                self.assertRegexp('foo', 'bar')
            finally:
                conf.supybot.plugins.Factoids.\
                    replyWhenInvalidCommand.setValue(orig)

    def testQuoteHandling(self):
        self.assertNotError('learn foo as "\\"bar\\""')
        self.assertRegexp('whatis foo', r'"bar"')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
