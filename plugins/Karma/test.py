###
# Copyright (c) 2005, Jeremiah Fincher
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

class KarmaTestCase(ChannelPluginTestCase):
    plugins = ('Karma',)
    def testKarma(self):
        self.assertError('karma')
        self.assertRegexp('karma foobar', 'neutral karma')
        try:
            conf.replyWhenNotCommand = True
            self.assertNoResponse('foobar++', 2)
        finally:
            conf.replyWhenNotCommand = False
        self.assertRegexp('karma foobar', 'increased 1.*total.*1')
        self.assertRegexp('karma FOOBAR', 'increased 1.*total.*1')
        self.assertNoResponse('foobar--', 2)
        self.assertRegexp('karma foobar', 'decreased 1.*total.*0')
        self.assertRegexp('karma FOOBAR', 'decreased 1.*total.*0')
        self.assertNoResponse('FOO++', 2)
        self.assertNoResponse('BAR--', 2)
        self.assertRegexp('karma foo bar foobar', '.*foo.*foobar.*bar.*')
        self.assertRegexp('karma FOO BAR FOOBAR', '.*foo.*foobar.*bar.*')
        self.assertRegexp('karma FOO BAR FOOBAR',
                          '.*FOO.*foobar.*BAR.*', flags=0)
        self.assertRegexp('karma foo bar foobar asdfjkl', 'asdfjkl')
        # Test case-insensitive
        self.assertNoResponse('MOO++', 2)
        self.assertRegexp('karma moo',
                          'Karma for [\'"]moo[\'"].*increased 1.*total.*1')
        self.assertRegexp('karma MoO',
                          'Karma for [\'"]MoO[\'"].*increased 1.*total.*1')

    def testKarmaRankingDisplayConfigurable(self):
        try:
            orig = conf.supybot.plugins.Karma.response()
            conf.supybot.plugins.Karma.response.setValue(True)
            original = conf.supybot.plugins.Karma.rankingDisplay()
            self.assertNotError('foo++')
            self.assertNotError('foo++')
            self.assertNotError('foo++')
            self.assertNotError('foo++')
            self.assertNotError('bar++')
            self.assertNotError('bar++')
            self.assertNotError('bar++')
            self.assertNotError('baz++')
            self.assertNotError('baz++')
            self.assertNotError('quux++')
            self.assertNotError('xuuq--')
            self.assertNotError('zab--')
            self.assertNotError('zab--')
            self.assertNotError('rab--')
            self.assertNotError('rab--')
            self.assertNotError('rab--')
            self.assertNotError('oof--')
            self.assertNotError('oof--')
            self.assertNotError('oof--')
            self.assertNotError('oof--')
            self.assertRegexp('karma', 'foo.*bar.*baz.*oof.*rab.*zab')
            conf.supybot.plugins.Karma.rankingDisplay.setValue(4)
            self.assertRegexp('karma', 'foo.*bar.*baz.*quux')
        finally:
            conf.supybot.plugins.Karma.response.setValue(orig)
            conf.supybot.plugins.Karma.rankingDisplay.setValue(original)

    def testMost(self):
        self.assertError('most increased')
        self.assertError('most decreased')
        self.assertError('most active')
        self.assertHelp('most aldsfkj')
        self.assertNoResponse('foo++', 1)
        self.assertNoResponse('foo++', 1)
        self.assertNoResponse('bar++', 1)
        self.assertNoResponse('bar--', 1)
        self.assertNoResponse('bar--', 1)
        self.assertRegexp('karma most active', 'bar.*foo')
        self.assertRegexp('karma most increased', 'foo.*bar')
        self.assertRegexp('karma most decreased', 'bar.*foo')
        self.assertNoResponse('foo--', 1)
        self.assertNoResponse('foo--', 1)
        self.assertNoResponse('foo--', 1)
        self.assertNoResponse('foo--', 1)
        self.assertRegexp('karma most active', 'foo.*bar')
        self.assertRegexp('karma most increased', 'foo.*bar')
        self.assertRegexp('karma most decreased', 'foo.*bar')

    def testSimpleOutput(self):
        try:
            orig = conf.supybot.plugins.Karma.simpleOutput()
            conf.supybot.plugins.Karma.simpleOutput.setValue(True)
            self.assertNoResponse('foo++', 2)
            self.assertResponse('karma foo', 'foo: 1')
            self.assertNoResponse('bar--', 2)
            self.assertResponse('karma bar', 'bar: -1')
        finally:
            conf.supybot.plugins.Karma.simpleOutput.setValue(orig)

    def testSelfRating(self):
        nick = self.nick
        try:
            orig = conf.supybot.plugins.Karma.allowSelfRating()
            conf.supybot.plugins.Karma.allowSelfRating.setValue(False)
            self.assertError('%s++' % nick)
            self.assertResponse('karma %s' % nick,
                                '%s has neutral karma.' % nick)
            conf.supybot.plugins.Karma.allowSelfRating.setValue(True)
            self.assertNoResponse('%s++' % nick, 2)
            self.assertRegexp('karma %s' % nick,
                  'Karma for [\'"]%s[\'"].*increased 1.*total.*1' % nick)
        finally:
            conf.supybot.plugins.Karma.allowSelfRating.setValue(orig)

    def testKarmaOutputConfigurable(self):
        self.assertNoResponse('foo++', 2)
        try:
            orig = conf.supybot.plugins.Karma.response()
            conf.supybot.plugins.Karma.response.setValue(True)
            self.assertNotError('foo++')
        finally:
            conf.supybot.plugins.Karma.response.setValue(orig)

    def testKarmaMostDisplayConfigurable(self):
        self.assertNoResponse('foo++', 1)
        self.assertNoResponse('foo++', 1)
        self.assertNoResponse('bar++', 1)
        self.assertNoResponse('bar--', 1)
        self.assertNoResponse('bar--', 1)
        self.assertNoResponse('foo--', 1)
        self.assertNoResponse('foo--', 1)
        self.assertNoResponse('foo--', 1)
        self.assertNoResponse('foo--', 1)
        try:
            orig = conf.supybot.plugins.Karma.mostDisplay()
            conf.supybot.plugins.Karma.mostDisplay.setValue(1)
            self.assertRegexp('karma most active', '(?!bar)')
            conf.supybot.plugins.Karma.mostDisplay.setValue(25)
            self.assertRegexp('karma most active', 'bar')
        finally:
            conf.supybot.plugins.Karma.mostDisplay.setValue(orig)


    def testIncreaseKarmaWithNickNotCallingInvalidCommand(self):
        self.assertSnarfNoResponse('%s: foo++' % self.irc.nick, 3)

    def testClear(self):
        self.assertNoResponse('foo++', 1)
        self.assertRegexp('karma foo', '1')
        self.assertNotError('karma clear foo')
        self.assertRegexp('karma foo', 'neutral')
        self.assertNotRegexp('karma foo', '1')

#        def testNoKarmaDunno(self):
#            self.assertNotError('load Infobot')
#            self.assertNoResponse('foo++')

    def testMultiWordKarma(self):
        self.assertNoResponse('(foo bar)++', 1)
        self.assertRegexp('karma "foo bar"', '1')

    def testUnaddressedKarma(self):
        karma = conf.supybot.plugins.Karma
        resp = karma.response()
        unaddressed = karma.allowUnaddressedKarma()
        try:
            karma.response.setValue(True)
            karma.allowUnaddressedKarma.setValue(True)
            for m in ('++', '--'):
                self.assertRegexp('foo%s' % m, 'is now')
                self.assertSnarfRegexp('foo%s' % m, 'is now')
                #self.assertNoResponse('foo bar%s' % m)
                #self.assertSnarfNoResponse('foo bar%s' % m)
                self.assertRegexp('(foo bar)%s' % m, 'is now')
                self.assertSnarfRegexp('(foo bar)%s' % m, 'is now')
        finally:
            karma.response.setValue(resp)
            karma.allowUnaddressedKarma.setValue(unaddressed)

    def testOnlyNicks(self):
        # We use this to join a dummy user to test upon
        msg = ircmsgs.join(self.channel, prefix='hello!foo@bar')
        self.irc.feedMsg(msg)
        karma = conf.supybot.plugins.Karma
        resp = karma.response()
        onlynicks = karma.onlyNicks()
        try:
            karma.onlynicks.setValue(True)
            karma.response.setValue(True)
            self.assertSnarfNoResponse('abcd++')
            self.assertSnarfRegexp('hello--', 'is now')
            self.assertSnarfNoResponse('abcd--')
            self.assertSnarfRegexp('hello++', 'is now')
        finally:
            karma.onlynicks.setValue(onlynicks)
            karma.response.setValue(resp)
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
