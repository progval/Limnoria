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

class MiscTestCase(ChannelPluginTestCase):
    plugins = ('Misc', 'Utilities', 'Gameknot', 'Anonymous', 'Dict', 'User')
    def testAction(self):
        self.assertAction('action moos', 'moos')

    def testActionDoesNotAllowEmptyString(self):
        self.assertHelp('action')
        self.assertHelp('action ""')

    def testReplyWhenNotCommand(self):
        try:
            original = str(conf.supybot.reply.whenNotCommand)
            conf.supybot.reply.whenNotCommand.set('True')
            self.prefix = 'somethingElse!user@host.domain.tld'
            self.assertRegexp('foo bar baz', 'not.*command')
        finally:
            conf.supybot.reply.whenNotCommand.set(original)

    if network:
        def testNotReplyWhenRegexpsMatch(self):
            try:
                orig = conf.supybot.reply.whenNotCommand()
                gk = conf.supybot.plugins.Gameknot.gameSnarfer()
                conf.supybot.reply.whenNotCommand.setValue(True)
                conf.supybot.plugins.Gameknot.gameSnarfer.setValue(True)
                self.prefix = 'somethingElse!user@host.domain.tld'
                self.assertSnarfNotError(
                        'http://gameknot.com/chess.pl?bd=1019508')
            finally:
                conf.supybot.reply.whenNotCommand.setValue(orig)
                conf.supybot.plugins.Gameknot.gameSnarfer.setValue(gk)

    def testNotReplyWhenNotCanonicalName(self):
        try:
            original = str(conf.supybot.reply.whenNotCommand)
            conf.supybot.reply.whenNotCommand.set('True')
            self.prefix = 'somethingElse!user@host.domain.tld'
            self.assertNotRegexp('STrLeN foobar', 'command')
            self.assertResponse('StRlEn foobar', '6')
        finally:
            conf.supybot.reply.whenNotCommand.set(original)

    def testHelp(self):
        self.assertHelp('help list')
        self.assertRegexp('help help', r'^\(\x02help')
        self.assertRegexp('help misc help', r'^\(\x02misc help')
        self.assertError('help nonExistentCommand')

    def testHelpDoesAmbiguityWithDefaultPlugins(self):
        m = self.getMsg('help list') # Misc.list and User.list.
        self.failIf(m.args[1].startswith('Error'))

    def testHelpIsCaseInsensitive(self):
        self.assertHelp('help LIST')

    def testList(self):
        self.assertNotError('list')
        self.assertNotError('list Misc')

    def testListIsCaseInsensitive(self):
        self.assertNotError('list misc')

    def testListPrivate(self):
        # If Ctcp changes to public, these tests will break.  So if
        # the next assert fails, change the plugin we test for public/private
        # to some other non-public plugin.
        name = 'Anonymous'
        conf.supybot.plugins.Anonymous.public.setValue(False)
        self.assertNotRegexp('list', name)
        self.assertRegexp('list --private', name)
        conf.supybot.plugins.Anonymous.public.setValue(True)
        self.assertRegexp('list', name)
        self.assertNotRegexp('list --private', name)

    def testListDoesNotIncludeNonCanonicalName(self):
        self.assertNotRegexp('list Owner', '_exec')

    def testListNoIncludeDispatcher(self):
        self.assertNotRegexp('list Misc', 'misc')

    def testListIncludesDispatcherIfThereIsAnOriginalCommand(self):
        self.assertRegexp('list Dict', r'\bdict\b')

    def testContributors(self):
        # Test ability to list contributors
        self.assertNotError('contributors Misc')
        # Test ability to list contributions
        # Verify that when a single command contribution has been made,
        # the word "command" is properly not pluralized.
        # Note: This will break if the listed person ever makes more than
        # one contribution to the Misc plugin
        self.assertRegexp('contributors Misc skorobeus', 'command')
        # Test handling of pluralization of "command" when person has
        # contributed more than one command to the plugin.
        # -- Need to create this case, check it with the regexp 'commands'
        # Test handling of invalid plugin
        self.assertRegexp('contributors InvalidPlugin', 
            'No such plugin')
        # Test handling of invalid person
        self.assertRegexp('contributors Misc noname', 
            'not a registered contributor')
        # Test handling of valid person with no contributions
        # Note: This will break if the listed person ever makes a contribution
        # to the Misc plugin
        self.assertRegexp('contributors Misc bwp',
            'listed as a contributor')
        
    def testContributorsIsCaseInsensitive(self):
        self.assertNotError('contributors Misc Skorobeus')
        self.assertNotError('contributors Misc sKoRoBeUs')

    if network:
        def testVersion(self):
            print '*** This test should start passing when we have our '\
                  'threaded issues resolved.'
            self.assertNotError('version')

    def testSource(self):
        self.assertNotError('source')

    def testPlugin(self):
        self.assertResponse('plugin plugin', 'Misc')

    def testTell(self):
        m = self.getMsg('tell foo [plugin tell]')
        self.failUnless('let you do' in m.args[1])
        m = self.getMsg('tell #foo [plugin tell]')
        self.failUnless('No need for' in m.args[1])
        m = self.getMsg('tell me you love me')
        self.failUnless(m.args[0] == self.nick)

    def testTellDoesNotPropogateAction(self):
        m = self.getMsg('tell foo [action bar]')
        self.failIf(ircmsgs.isAction(m))

    def testLast(self):
        orig = conf.supybot.plugins.Misc.timestampFormat()
        try:
            conf.supybot.plugins.Misc.timestampFormat.setValue('')
            self.feedMsg('foo bar baz')
            self.assertResponse('last', '<%s> foo bar baz' % self.nick)
            self.assertRegexp('last', '<%s> @last' % self.nick)
            self.assertResponse('last --with foo', '<%s> foo bar baz' % \
                                self.nick)
            self.assertResponse('last --without foo', '<%s> @last' % self.nick)
            self.assertRegexp('last --regexp m/\s+/', 'last --without foo')
            self.assertResponse('last --regexp m/bar/',
                                '<%s> foo bar baz' % self.nick)
            self.assertResponse('last --from %s' % self.nick.upper(),
                                '<%s> @last --regexp m/bar/' % self.nick)
            self.assertResponse('last --from %s*' % self.nick[0],
                                '<%s> @last --from %s' %
                                (self.nick, self.nick.upper()))
            conf.supybot.plugins.Misc.timestampFormat.setValue('foo')
            self.assertSnarfNoResponse('foo bar baz', 1)
            self.assertResponse('last', 'foo <%s> foo bar baz' % self.nick)
        finally:
            conf.supybot.plugins.Misc.timestampFormat.setValue(orig)

    def testMore(self):
        self.assertRegexp('echo %s' % ('abc'*300), 'more')
        self.assertRegexp('more', 'more')
        self.assertNotRegexp('more', 'more')

    def testInvalidCommand(self):
        self.assertError('echo []')

    def testMoreIsCaseInsensitive(self):
        self.assertNotError('echo %s' % ('abc'*2000))
        self.assertNotError('more')
        nick = ircutils.nickFromHostmask(self.prefix)
        self.assertNotError('more %s' % nick)
        self.assertNotError('more %s' % nick.upper())
        self.assertNotError('more %s' % nick.lower())

    def testPrivate(self):
        m = self.getMsg('private [list]')
        self.failIf(ircutils.isChannel(m.args[0]))

    def testNotice(self):
        m = self.getMsg('notice [list]')
        self.assertEqual(m.command, 'NOTICE')

    def testNoticePrivate(self):
        m = self.assertNotError('notice [private [list]]')
        self.assertEqual(m.command, 'NOTICE')
        self.assertEqual(m.args[0], self.nick)
        m = self.assertNotError('private [notice [list]]')
        self.assertEqual(m.command, 'NOTICE')
        self.assertEqual(m.args[0], self.nick)

    def testHostmask(self):
        self.assertResponse('hostmask', self.prefix)

    def testApropos(self):
        self.assertNotError('apropos f')
        self.assertRegexp('apropos asldkfjasdlkfja', 'No appropriate commands')

    def testAproposDoesntReturnNonCanonicalNames(self):
        self.assertNotRegexp('apropos exec', '_exec')

    def testRevision(self):
        self.assertNotError('revision Misc')
        self.assertNotError('revision Misc.py')
        self.assertNotError('revision')

    def testRevisionDoesNotLowerUnnecessarily(self):
        self.assertNotError('load Math')
        m1 = self.assertNotError('revision Math')
        m2 = self.assertNotError('revision math')
        self.assertEqual(m1, m2)

    def testRevisionIsCaseInsensitive(self):
        self.assertNotError('revision misc')

    def testSeconds(self):
        self.assertResponse('seconds 1s', '1')
        self.assertResponse('seconds 10s', '10')
        self.assertResponse('seconds 1m', '60')
        self.assertResponse('seconds 1m 1s', '61')
        self.assertResponse('seconds 1h', '3600')
        self.assertResponse('seconds 1h 1s', '3601')
        self.assertResponse('seconds 1d', '86400')
        self.assertResponse('seconds 1d 1s', '86401')
        self.assertResponse('seconds 2s', '2')
        self.assertResponse('seconds 2m', '120')
        self.assertResponse('seconds 2d 2h 2m 2s', '180122')
        self.assertResponse('seconds 1s', '1')
        self.assertResponse('seconds 1y 1s', '31536001')
        self.assertResponse('seconds 1w 1s', '604801')


class MiscNonChannelTestCase(PluginTestCase):
    plugins = ('Misc',)
    def testAction(self):
        self.prefix = 'something!else@somewhere.else'
        self.nick = 'something'
        m = self.assertAction('action foo', 'foo')
        self.failIf(m.args[0] == self.irc.nick)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

