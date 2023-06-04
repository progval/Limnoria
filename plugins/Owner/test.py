###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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

import sys
from unittest import skip

from supybot.test import *

import supybot.conf as conf
import supybot.plugin as plugin

class OwnerTestCase(PluginTestCase):
    plugins = ('Owner', 'Config', 'Misc', 'Admin')
    def testHelpLog(self):
        self.assertHelp('help logmark')

    def testSrcAmbiguity(self):
        self.assertError('capability add foo bar')

    def testIrcquote(self):
        self.assertResponse('ircquote PRIVMSG %s :foo' % self.irc.nick, 'foo')

        self.feedMsg('ircquote PING foo')
        self.assertEqual(self.irc.takeMsg(), ircmsgs.IrcMsg(
            command='PING', args=('foo',)))

    def testIrcquoteLabeledResponse(self):
        self.irc.state.capabilities_ack.update({'labeled-response', 'batch'})
        self.feedMsg('ircquote @label=abc PING foo')
        self.assertEqual(self.irc.takeMsg(), ircmsgs.IrcMsg(
            server_tags={'label': 'abc'}, command='PING', args=('foo',)))
        self.irc.feedMsg(ircmsgs.IrcMsg(
            server_tags={'label': 'abc'}, prefix='server.',
            command='PONG', args=('foo',)))
        self.assertResponse(' ', '@label=abc :server. PONG :foo')

    def testIrcquoteLabeledResponseBatch(self):
        self.irc.state.capabilities_ack.update({'labeled-response', 'batch'})
        self.feedMsg('ircquote @label=abc WHO val')
        self.assertEqual(self.irc.takeMsg(), ircmsgs.IrcMsg(
            server_tags={'label': 'abc'}, command='WHO', args=('val',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(
            server_tags={'label': 'abc'}, prefix='server.',
            command='BATCH', args=('+4', 'labeled-response')))
        self.irc.feedMsg(ircmsgs.IrcMsg(
            server_tags={'batch': '4'}, prefix='server.',
            command='311', args=('test', 'val', '~u', 'host', '*', 'Val L')))
        self.irc.feedMsg(ircmsgs.IrcMsg(
            server_tags={'batch': '4'}, prefix='server.',
            command='311', args=('test', 'val', '#limnoria-bots')))

        # Batch not complete yet -> no response
        self.assertIsNone(self.irc.takeMsg())

        # end of batch
        self.irc.feedMsg(ircmsgs.IrcMsg(
            prefix='server.', command='BATCH', args=('-4',)))

        self.assertResponse(
            ' ', '@label=abc :server. BATCH +4 :labeled-response')
        self.assertResponse(
            ' ', '@batch=4 :server. 311 test val ~u host * :Val L')
        self.assertResponse(
            ' ', '@batch=4 :server. 311 test val :#limnoria-bots')
        self.assertResponse(
            ' ', ':server. BATCH :-4')


    def testFlush(self):
        self.assertNotError('flush')

    def testUpkeep(self):
        self.assertNotError('upkeep')

    def testLoad(self):
        self.assertError('load Owner')
        self.assertError('load owner')
        self.assertNotError('load Channel')
        self.assertNotError('list Owner')

    def testReload(self):
        self.assertError('reload Channel')
        self.assertNotError('load Channel')
        self.assertNotError('reload Channel')
        self.assertNotError('reload Channel')

    def testUnload(self):
        self.assertError('unload Foobar')
        self.assertNotError('load Channel')
        self.assertNotError('unload Channel')
        self.assertError('unload Channel')
        self.assertNotError('load Channel')
        self.assertNotError('unload CHANNEL')

    def testDisable(self):
        self.assertError('disable enable')
        self.assertError('disable identify')

    def testEnable(self):
        self.assertError('enable enable')

    def testEnableIsCaseInsensitive(self):
        self.assertNotError('disable Foo')
        self.assertNotError('enable foo')

    def testRename(self):
        self.assertError('rename Admin join JOIN')
        self.assertError('rename Admin join jo-in')
        self.assertNotError('rename Admin join testcommand')
        self.assertRegexp('list Admin', 'testcommand')
        self.assertNotRegexp('list Admin', 'join')
        self.assertError('help join')
        self.assertRegexp('help testcommand', 'Tell the bot to join')
        self.assertRegexp('join', 'not a valid command')
        self.assertHelp('testcommand')
        self.assertNotError('unrename Admin')
        self.assertNotRegexp('list Admin', 'testcommand')

    @skip('Nested commands cannot be renamed yet.')
    def testRenameNested(self):
        self.assertNotError('rename Admin "capability remove" rmcap')
        self.assertNotRegexp('list Admin', 'capability remove')
        self.assertRegexp('list Admin', 'rmcap')
        self.assertNotError('reload Admin')
        self.assertNotRegexp('list Admin', 'capability remove')
        self.assertRegexp('list Admin', 'rmcap')
        self.assertNotError('unrename Admin')
        self.assertRegexp('list Admin', 'capability remove')
        self.assertNotRegexp('list Admin', 'rmcap')

    def testDefaultPluginErrorsWhenCommandNotInPlugin(self):
        self.assertError('defaultplugin foobar owner')


class CommandsTestCase(PluginTestCase):
    plugins = ('Owner', 'Utilities')

    def testSimpleCommand(self):
        self.irc.feedMsg(
            ircmsgs.privmsg(self.irc.nick, 'echo foo $nick!$user@$host', self.prefix))
        response = self.irc.takeMsg()
        self.assertEqual(response.args, (self.nick, 'foo ' + self.prefix))

    def testMultilineCommandDisabled(self):
        self._sendBatch()

        # response to 'echo '
        self.assertRegexp('', '(echo <text>)')

        # response to 'foo '
        self.assertResponse('', 'Error: "foo" is not a valid command.')

        # response to '$prefix'
        self.assertResponse(
            '', 'Error: "$nick!$user@$host" is not a valid command.')

        # response to 'echo nope'
        self.assertResponse('', 'nope')

    def testMultilineCommand(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            self._sendBatch()
            response = self.irc.takeMsg()
            self.assertEqual(response.args, (self.nick, 'foo ' + self.prefix))

            response = self.irc.takeMsg()
            self.assertIsNone(response, 'Should not respond to second line')

    def _sendBatch(self):
        self.irc.feedMsg(ircmsgs.IrcMsg(
            command='BATCH',
            args=('+123', 'draft/multiline', self.irc.nick)))

        # one line
        self.irc.feedMsg(ircmsgs.IrcMsg(
            server_tags={'batch': '123'},
            prefix=self.prefix,
            command='PRIVMSG',
            args=(self.irc.nick, 'echo ')))
        self.irc.feedMsg(ircmsgs.IrcMsg(
            server_tags={'batch': '123', 'draft/multiline-concat': None},
            prefix=self.prefix,
            command='PRIVMSG',
            args=(self.irc.nick, 'foo ')))
        self.irc.feedMsg(ircmsgs.IrcMsg(
            server_tags={'batch': '123', 'draft/multiline-concat': None},
            prefix=self.prefix,
            command='PRIVMSG',
            args=(self.irc.nick, '$nick!$user@$host')))

        # an other line
        self.irc.feedMsg(ircmsgs.IrcMsg(
            server_tags={'batch': '123'},
            prefix=self.prefix,
            command='PRIVMSG',
            args=(self.irc.nick, 'echo nope')))

        self.irc.feedMsg(ircmsgs.IrcMsg(
            command='BATCH',
            args=('-123',)))

    def testIgnoreChathistory(self):
        self.irc.feedMsg(ircmsgs.IrcMsg(
            command='BATCH',
            args=('+123', 'chathistory', self.irc.nick)))

        self.irc.feedMsg(ircmsgs.IrcMsg(
            server_tags={'batch': '123'},
            prefix=self.prefix,
            command='PRIVMSG',
            args=(self.irc.nick, 'echo foo')))

        self.irc.feedMsg(ircmsgs.IrcMsg(
            command='BATCH',
            args=('-123',)))

        self.irc.feedMsg(ircmsgs.IrcMsg(
            prefix=self.prefix,
            command='PRIVMSG',
            args=(self.irc.nick, 'echo bar')))

        self.assertResponse('', 'bar')



# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
