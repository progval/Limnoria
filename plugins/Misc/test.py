###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008, James McCoy
# Copyright (c) 2010-2021, Valentin Lorentz
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

from supybot.test import *


class MiscTestCase(PluginTestCase):
    plugins = ('Misc', 'Utilities')
    def testMore(self):
        newprefix = 'fooo!bar@baaaaaaaaaaaaaaz'

        # just for the sale of filling irc.state.nicksToHostmasks:
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CHGHOST', args=(self.nick, 'baz'),
            prefix=self.prefix))
        self.irc.feedMsg(ircmsgs.IrcMsg(command='CHGHOST', args=('foo', 'baz'),
            prefix='foo!bar@oldbaz'))

        self.assertResponse('echo %s' % ('abc '*400),
                            'abc '*112 + ' \x02(3 more messages)\x02',
                            frm=newprefix)
        m = self.assertResponse('more',
                            'abc '*112 + ' \x02(2 more messages)\x02',
                            frm=newprefix)
        self.assertResponse('more',
                            'abc '*112 + ' \x02(1 more message)\x02',
                            frm=newprefix)
        self.assertResponse('more',
                            ' '.join(['abc']*(400-112*3)),
                            frm=newprefix)
        self.assertResponse('more',
                            "Error: That's all, there is no more.",
                            frm=newprefix)


class MiscTestCase(ChannelPluginTestCase):
    plugins = ('Misc', 'Utilities', 'Anonymous', 'Plugin',
               'Channel', 'Dict', 'User', 'String')
    def testReplyWhenNotCommand(self):
        try:
            original = conf.supybot.reply.whenNotCommand()
            conf.supybot.reply.whenNotCommand.setValue(True)
            self.prefix = 'somethingElse!user@host.domain.tld'
            self.assertRegexp('foo', 'not.*command')
            self.assertRegexp('foo bar baz', 'not.*command')
        finally:
            conf.supybot.reply.whenNotCommand.setValue(original)

    def testReplyWhenNotCommandButFirstCommandIsPluginName(self):
        try:
            original = conf.supybot.reply.whenNotCommand()
            conf.supybot.reply.whenNotCommand.setValue(True)
            self.assertRegexp('misc foo', '"list Misc"')
        finally:
            conf.supybot.reply.whenNotCommand.setValue(original)

#    if network:
#        def testNotReplyWhenRegexpsMatch(self):
#            try:
#                orig = conf.supybot.reply.whenNotCommand()
#                gk = conf.supybot.plugins.Gameknot.gameSnarfer()
#                conf.supybot.reply.whenNotCommand.setValue(True)
#                conf.supybot.plugins.Gameknot.gameSnarfer.setValue(True)
#                self.prefix = 'somethingElse!user@host.domain.tld'
#                self.assertSnarfNotError(
#                        'http://gameknot.com/chess.pl?bd=1019508')
#            finally:
#                conf.supybot.reply.whenNotCommand.setValue(orig)
#                conf.supybot.plugins.Gameknot.gameSnarfer.setValue(gk)

    def testNotReplyWhenNotCanonicalName(self):
        try:
            original = str(conf.supybot.reply.whenNotCommand)
            conf.supybot.reply.whenNotCommand.set('True')
            self.prefix = 'somethingElse!user@host.domain.tld'
            self.assertNotRegexp('LeN foobar', 'command')
            self.assertResponse('lEn foobar', '6')
        finally:
            conf.supybot.reply.whenNotCommand.set(original)

    def testHelp(self):
        self.assertHelp('help list')
        self.assertRegexp('help help', r'^\(\x02help')
        #self.assertRegexp('help misc help', r'^\(\x02misc help')
        self.assertError('help nonExistentCommand')

    def testPluginHelp(self):
        self.assertResponse('help Misc',
            'Error: There is no command "misc". '
            "However, 'Misc' is the name of a loaded plugin, "
            "and you may be able to find its help using "
            "'plugin help Misc' and its provided "
            "commands using 'list Misc'.")
        self.assertNotError('unload Plugin')
        self.assertResponse('help Misc',
            'Error: There is no command "misc". '
            "However, 'Misc' is the name of a loaded plugin, "
            "and you may be able to find its provided commands using "
            "'list Misc'.")

    def testHelpIncludeFullCommandName(self):
        self.assertHelp('help channel capability add')
        m = self.getMsg('help channel capability add')
        self.assertIn('channel capability add', m.args[1])

    def testHelpDoesAmbiguityWithDefaultPlugins(self):
        m = self.getMsg('help list') # Misc.list and User.list.
        self.assertFalse(m.args[1].startswith('Error'))

    def testHelpIsCaseInsensitive(self):
        self.assertHelp('help LIST')

    def testList(self):
        self.assertNotError('list')
        self.assertNotError('list Misc')
        self.assertRegexp('list --unloaded', 'Ctcp')

    def testListIsCaseInsensitive(self):
        self.assertNotError('list misc')

    def testListPrivate(self):
        # If Anonymous changes to public, these tests will break.  So if
        # the next assert fails, change the plugin we test for public/private
        # to some other non-public plugin.
        name = 'Anonymous'
        conf.supybot.plugins.Anonymous.public.setValue(False)
        self.assertNotRegexp('list', name)
        self.assertRegexp('list --private', name)
        conf.supybot.plugins.Anonymous.public.setValue(True)
        self.assertRegexp('list', name)
        self.assertNotRegexp('list --private', name)

    def testListUnloaded(self):
        unloadedPlugin = 'Alias'
        loadedPlugin = 'Anonymous'
        self.assertRegexp('list --unloaded', 'Alias')
        self.assertNotRegexp('list --unloaded', 'Anonymous')

    def testListDoesNotIncludeNonCanonicalName(self):
        self.assertNotRegexp('list Owner', '_exec')

    def testListNoIncludeDispatcher(self):
        self.assertNotRegexp('list Misc', 'misc')

    def testListIncludesDispatcherIfThereIsAnOriginalCommand(self):
        self.assertRegexp('list Dict', r'\bdict\b')

    if network:
        def testVersion(self):
            print('*** This test should start passing when we have our '\
                  'threaded issues resolved.')
            self.assertNotError('version')

    def testSource(self):
        self.assertNotError('source')

    def testTell(self):
        # This test fails because the test is seeing us as owner and Misc.tell
        # allows the owner to send messages to people the bot hasn't seen.
        oldprefix, self.prefix = self.prefix, 'tester!foo@bar__no_testcap__baz'
        self.nick = 'tester'
        m = self.getMsg('tell aljsdkfh [plugin tell]')
        self.assertIn('let you do', m.args[1])
        m = self.getMsg('tell #foo [plugin tell]')
        self.assertIn('No need for', m.args[1])
        m = self.getMsg('tell me you love me')
        m = self.irc.takeMsg()
        self.assertEqual(m.args[0], self.nick)

    def testNoNestedTell(self):
        self.assertRegexp('echo [tell %s foo]' % self.nick, 'nested')

    def testTellDoesNotPropogateAction(self):
        m = self.getMsg('tell foo [action bar]')
        self.assertFalse(ircmsgs.isAction(m))

    def testLast(self):
        orig = conf.supybot.plugins.Misc.timestampFormat()
        try:
            conf.supybot.plugins.Misc.timestampFormat.setValue('')
            self.feedMsg('foo bar baz')
            self.assertResponse('last', '<%s> foo bar baz' % self.nick)
            self.assertRegexp('last', r'<%s> @last' % self.nick)
            self.assertResponse('last --with foo', '<%s> foo bar baz' % \
                                self.nick)
            self.assertResponse('last --without foo', '<%s> @last' % self.nick)
            self.assertRegexp(r'last --regexp m/\s+/', r'last --without foo')
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

    def testNestedLastTimestampConfig(self):
        tsConfig = conf.supybot.plugins.Misc.last.nested.includeTimestamp
        orig = tsConfig()
        try:
            tsConfig.setValue(True)
            self.getMsg('foo bar baz')
            chars = conf.supybot.reply.whenAddressedBy.chars()
            chars = re.escape(chars)
            self.assertRegexp('echo [last]', r'[%s]foo bar baz' % chars)
        finally:
            tsConfig.setValue(orig)

    def testNestedLastNickConfig(self):
        nickConfig = conf.supybot.plugins.Misc.last.nested.includeNick
        orig = nickConfig()
        try:
            nickConfig.setValue(True)
            self.getMsg('foo bar baz')
            chars = conf.supybot.reply.whenAddressedBy.chars()
            chars = re.escape(chars)
            self.assertRegexp('echo [last]',
                              '<%s> [%s]foo bar baz' % (self.nick, chars))
        finally:
            nickConfig.setValue(orig)

    def testMore(self):
        self.assertResponse('echo %s' % ('abc '*400),
                            'abc '*112 + ' \x02(3 more messages)\x02')
        self.assertResponse('more',
                            'abc '*112 + ' \x02(2 more messages)\x02')
        self.assertResponse('more',
                            'abc '*112 + ' \x02(1 more message)\x02')
        self.assertResponse('more',
                            ' '.join(['abc']*(400-112*3)))
        self.assertResponse('more',
                            "Error: That's all, there is no more.")

    def testMoreMores(self):
        with conf.supybot.plugins.Misc.mores.context(2):
            self.assertResponse('echo %s' % ('abc '*400),
                                'abc '*112 + ' \x02(3 more messages)\x02')
            self.assertResponse('more',
                                'abc '*112 + ' \x02(2 more messages)\x02')
            m = self.irc.takeMsg()
            self.assertIsNotNone(m)
            self.assertEqual(
                m.args[1],
                'abc '*112 + ' \x02(1 more message)\x02')
            self.assertResponse('more',
                                ' '.join(['abc']*(400-112*3)))
            self.assertResponse('more',
                                "Error: That's all, there is no more.")

    def testMoreBatch(self):
        self.irc.state.capabilities_ack.add('batch')
        self.irc.state.capabilities_ack.add('draft/multiline')
        self.irc.state.capabilities_ls['draft/multiline'] = 'max-bytes=4096'
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with conf.supybot.plugins.Misc.mores.context(2):
                self.assertResponse('echo %s' % ('abc '*400),
                                    'abc '*112 + ' \x02(3 more messages)\x02')
                self.irc.feedMsg(ircmsgs.privmsg(
                    self.channel, "@more", prefix=self.prefix))

            # First message opens the batch
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'BATCH', m)
            batch_name = m.args[0][1:]
            self.assertEqual(
                m, ircmsgs.IrcMsg(command='BATCH',
                    args=('+' + batch_name,
                        'draft/multiline', self.channel)))

            # Second message, first PRIVMSG
            m = self.irc.takeMsg()
            self.assertEqual(
                m, ircmsgs.IrcMsg(command='PRIVMSG',
                    args=(self.channel, "abc " * 112 + " \x02(2 more messages)\x02"),
                    server_tags={'batch': batch_name}))

            # Third message, last PRIVMSG
            m = self.irc.takeMsg()
            self.assertEqual(
                m, ircmsgs.IrcMsg(command='PRIVMSG',
                    args=(self.channel,
                        "abc " * 112 + " \x02(1 more message)\x02"),
                    server_tags={'batch': batch_name}))

            # Last message, closes the batch
            m = self.irc.takeMsg()
            self.assertEqual(
                m, ircmsgs.IrcMsg(command='BATCH', args=(
                    '-' + batch_name,)))

    def testMoreBatchMaxLines(self):
        self.irc.state.capabilities_ack.add('batch')
        self.irc.state.capabilities_ack.add('draft/multiline')
        self.irc.state.capabilities_ls['draft/multiline'] = \
            'max-bytes=4096,max-lines=2'
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with conf.supybot.plugins.Misc.mores.context(3):
                self.assertResponse('echo %s' % ('abc '*400),
                                    'abc '*112 + ' \x02(3 more messages)\x02')
                self.irc.feedMsg(ircmsgs.privmsg(
                    self.channel, "@more", prefix=self.prefix))

            # First message opens the batch
            m = self.irc.takeMsg()
            self.assertEqual(m.command, 'BATCH', m)
            batch_name = m.args[0][1:]
            self.assertEqual(
                m, ircmsgs.IrcMsg(command='BATCH',
                    args=('+' + batch_name,
                        'draft/multiline', self.channel)))

            # Second message, first PRIVMSG
            m = self.irc.takeMsg()
            self.assertEqual(
                m, ircmsgs.IrcMsg(command='PRIVMSG',
                    args=(self.channel, "abc " * 112 + " \x02(2 more messages)\x02"),
                    server_tags={'batch': batch_name}))

            # Third message, last PRIVMSG
            m = self.irc.takeMsg()
            self.assertEqual(
                m, ircmsgs.IrcMsg(command='PRIVMSG',
                    args=(self.channel,
                        "abc " * 112 + " \x02(1 more message)\x02"),
                    server_tags={'batch': batch_name}))

            # Last message, closes the batch
            m = self.irc.takeMsg()
            self.assertEqual(
                m, ircmsgs.IrcMsg(command='BATCH', args=(
                    '-' + batch_name,)))

    def testClearMores(self):
        self.assertRegexp('echo %s' % ('abc'*700), 'more')
        self.assertRegexp('more', 'more')
        self.assertNotError('clearmores')
        self.assertError('more')

    def testInvalidCommand(self):
        self.assertError('echo []')

    def testInvalidCommands(self):
        with conf.supybot.abuse.flood.command.invalid.maximum.context(3):
            self.assertNotRegexp('foo', 'given me', frm='f!f@__no_testcap__')
            self.assertNotRegexp('bar', 'given me', frm='f!f@__no_testcap__')
            self.assertNotRegexp('baz', 'given me', frm='f!f@__no_testcap__')
            self.assertRegexp('qux', 'given me', frm='f!f@__no_testcap__')

    def testMoreIsCaseInsensitive(self):
        self.assertNotError('echo %s' % ('abc'*2000))
        self.assertNotError('more')
        nick = ircutils.nickFromHostmask(self.prefix)
        self.assertNotError('more %s' % nick)
        self.assertNotError('more %s' % nick.upper())
        self.assertNotError('more %s' % nick.lower())

    def testApropos(self):
        self.assertNotError('apropos f')
        self.assertRegexp('apropos asldkfjasdlkfja', 'No appropriate commands')

    def testAproposIsNotCaseSensitive(self):
        self.assertNotRegexp('apropos LIST', 'No appropriate commands')

    def testAproposDoesntReturnNonCanonicalNames(self):
        self.assertNotRegexp('apropos exec', '_exec')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

