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

import io
from unittest.mock import patch, Mock

from supybot import conf
from supybot.test import *

from . import plugin

timestamp_re = '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}  '


patch_open = patch.object(plugin, 'open', create=True)

class ChannelLoggerTestCase(ChannelPluginTestCase):
    plugins = ('ChannelLogger',)
    config = {
        'supybot.plugins.ChannelLogger.flushImmediately': True,
        'supybot.plugins.ChannelLogger.enable.:test.#foo': True,
    }

    def testLogName(self):
        self.assertEqual(
            self.irc.getCallback('ChannelLogger').getLogName('test', '#foo'),
            '#foo.log'
        )
        self.assertEqual(
            self.irc.getCallback('ChannelLogger').getLogName('test', '#f/../oo'),
            '#f..oo.log'
        )

    def testLogDir(self):
        self.assertEqual(
            self.irc.getCallback('ChannelLogger').getLogDir(self.irc, '#foo'),
            conf.supybot.directories.log.dirize('ChannelLogger/test/#foo')
        )
        self.assertEqual(
            self.irc.getCallback('ChannelLogger').getLogDir(self.irc, '#f/../oo'),
            conf.supybot.directories.log.dirize('ChannelLogger/test/#f..oo')
        )

    @patch_open
    def testLog(self, mock_open):
        mock_open.return_value = Mock()
        self.assertIs(
            self.irc.getCallback('ChannelLogger').getLog(self.irc, '#foo'),
            mock_open.return_value
        )
        mock_open.assert_called_once_with(
            conf.supybot.directories.log.dirize('ChannelLogger/test/#foo/#foo.log'),
            encoding='utf-8',
            mode='a'
        )

        # the log file should be cached
        mock_open.reset_mock()
        self.assertIs(
            self.irc.getCallback('ChannelLogger').getLog(self.irc, '#foo'),
            mock_open.return_value
        )
        mock_open.assert_not_called()

    @patch_open
    def testLogPrivmsg(self, mock_open):
        log_file = io.StringIO()
        mock_open.return_value = log_file

        self.irc.feedMsg(
            ircmsgs.privmsg('#foo', 'test message', prefix='foo!bar@baz')
        )

        self.assertRegex(
            log_file.getvalue(),
            timestamp_re + '<foo> test message\n'
        )

    @patch_open
    def _testLogRewriteRelayedEmulatedEcho(self, mock_open, relayed):
        with conf.supybot.plugins.ChannelLogger.rewriteRelayed.context(True):
            log_file = io.StringIO()
            mock_open.return_value = log_file

            msg = ircmsgs.privmsg(
                '#foo', '<someone> test message', prefix='foo!bar@baz'
            )
            if relayed:
                msg.tag('relayedMsg')
            self.irc.getCallback('ChannelLogger').outFilter(self.irc, msg)
            self.irc.feedMsg(msg)

            if relayed:
                content = '<someone> test message\n'
            else:
                content = '<foo> <someone> test message\n'
            self.assertRegex(log_file.getvalue(), timestamp_re + content)

    def testLogRewriteRelayedEmulatedEcho(self):
        self._testLogRewriteRelayedEmulatedEcho(relayed=True)

    def testLogRewriteRelayedEmulatedEchoNotRelayed(self):
        self._testLogRewriteRelayedEmulatedEcho(relayed=False)

    @patch_open
    def _testLogRewriteRelayedRealEcho(self, mock_open, relayed):
        with conf.supybot.plugins.ChannelLogger.rewriteRelayed.context(True):
            log_file = io.StringIO()
            mock_open.return_value = log_file

            original_caps = self.irc.state.capabilities_ack
            self.irc.state.capabilities_ack |= {
                'echo-message', 'labeled-response'
            }

            try:
                out_msg = ircmsgs.privmsg('#foo', '<someone> test message')
                if relayed:
                    out_msg.tag('relayedMsg')
                self.irc.getCallback('ChannelLogger').outFilter(self.irc, out_msg)
            finally:
                self.irc.state.capabilities_ack = original_caps

            msg = ircmsgs.privmsg(
                '#foo', '<someone> test message', prefix='foo!bar@baz'
            )
            msg.server_tags['label'] = out_msg.server_tags['label']
            self.irc.feedMsg(msg)

            if relayed:
                content = '<someone> test message\n'
            else:
                content = '<foo> <someone> test message\n'
            self.assertRegex(log_file.getvalue(), timestamp_re + content)

    def testLogRewriteRelayedRealEcho(self):
        self._testLogRewriteRelayedRealEcho(relayed=True)

    def testLogRewriteRelayedRealEchoNotRelayed(self):
        self._testLogRewriteRelayedRealEcho(relayed=False)

    @patch_open
    def testLogNotice(self, mock_open):
        log_file = io.StringIO()
        mock_open.return_value = log_file

        self.irc.feedMsg(
            ircmsgs.notice('#foo', 'test message', prefix='foo!bar@baz')
        )

        self.assertRegex(
            log_file.getvalue(),
            timestamp_re + '-foo- test message\n'
        )


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
