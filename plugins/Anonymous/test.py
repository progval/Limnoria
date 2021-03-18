###
# Copyright (c) 2005, Daniel DiPaolo
# Copyright (c) 2014, James McCoy
# Copyright (c) 2021, Valentin Lorentz
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

import supybot.conf as conf
from supybot.test import *

class AnonymousTestCase(ChannelPluginTestCase):
    plugins = ('Anonymous',)
    def testSay(self):
        self.assertError('anonymous say %s I love you!' % self.channel)

        with conf.supybot.plugins.Anonymous.requireRegistration.context(False):
            m = self.assertNotError('anonymous say %s foo!' % self.channel)
            self.assertTrue(m.args[1] == 'foo!')

    def testTell(self):
        self.assertError('anonymous tell %s I love you!' % self.nick)

        with conf.supybot.plugins.Anonymous.requireRegistration.context(False):
            self.assertError('anonymous tell %s foo!' % self.channel)
            with conf.supybot.plugins.Anonymous.allowPrivateTarget.context(True):
                m = self.assertNotError('anonymous tell %s foo!' % self.nick)
                self.assertTrue(m.args[1] == 'foo!')

    def testAction(self):
        m = self.assertError('anonymous do %s loves you!' % self.channel)

        with conf.supybot.plugins.Anonymous.requireRegistration.context(False):
            m = self.assertNotError('anonymous do %s loves you!'%self.channel)
            self.assertEqual(m.args, ircmsgs.action(self.channel,
                                                    'loves you!').args)

    def testReact(self):
        with self.subTest('nick not in channel'):
            self.assertRegexp('anonymous react :) blah',
                              'blah is not in %s' % self.channel)

        self.irc.feedMsg(ircmsgs.IrcMsg(
            ':blah!foo@example JOIN %s' % self.channel))

        with self.subTest('require registration'):
            self.assertRegexp('anonymous react :) blah',
                              'must be registered')
            self.assertIsNone(self.irc.takeMsg())

        with conf.supybot.plugins.Anonymous.requireRegistration.context(False):
            with self.subTest('experimental extensions disabled'):
                self.assertRegexp('anonymous react :) blah',
                                  'protocols.irc.experimentalExtensions is disabled')
                self.assertIsNone(self.irc.takeMsg())

        with conf.supybot.plugins.Anonymous.requireRegistration.context(False), \
                conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with self.subTest('server support missing'):
                self.assertRegexp('anonymous react :) blah',
                                  'network does not support message-tags')
                self.assertIsNone(self.irc.takeMsg())

            self.irc.state.capabilities_ack.add('message-tags')

            with self.subTest('no message from the target'):
                self.assertRegexp('anonymous react :) blah',
                                  'couldn\'t find a message')
                self.assertIsNone(self.irc.takeMsg())

            self.irc.feedMsg(ircmsgs.IrcMsg(
                ':blah!foo@example PRIVMSG %s :hello' % self.channel))

            with self.subTest('original message not tagged with msgid'):
                self.assertRegexp('anonymous react :) blah',
                                  'not have a message id')
                self.assertIsNone(self.irc.takeMsg())

            self.irc.feedMsg(ircmsgs.IrcMsg(
                '@msgid=123 :blah!foo@example PRIVMSG %s :hello'
                % self.channel))

            # Works
            with self.subTest('canonical working case'):
                m = self.getMsg('anonymous react :) blah')
                self.assertEqual(m, ircmsgs.IrcMsg(
                    '@+draft/reply=123;+draft/react=:) TAGMSG %s'
                    % self.channel))


    def testReactClienttagdeny(self):
        self.irc.feedMsg(ircmsgs.IrcMsg(
            ':blah!foo@example JOIN %s' % self.channel))

        self.irc.feedMsg(ircmsgs.IrcMsg(
            '@msgid=123 :blah!foo@example PRIVMSG %s :hello'
            % self.channel))
        self.irc.state.capabilities_ack.add('message-tags')

        with conf.supybot.plugins.Anonymous.requireRegistration.context(False), \
                conf.supybot.protocols.irc.experimentalExtensions.context(True):

            # Works
            self.irc.state.supported['CLIENTTAGDENY'] = 'foo,bar'

            for value in ('draft/reply', 'draft/react', '*,-draft/reply',
                          '*,draft/react'):
                self.irc.state.supported['CLIENTTAGDENY'] = value
                with self.subTest('denied by CLIENTTAGDENY=%s' % value):
                    self.assertRegexp('anonymous react :) blah',
                                      'draft/reply and/or draft/react')
                    self.assertIsNone(self.irc.takeMsg())

            # Works
            for value in ('foo,bar', '*,-draft/reply,-draft/react'):
                self.irc.state.supported['CLIENTTAGDENY'] = value
                with self.subTest('allowed by CLIENTTAGDENY=%s' % value):
                    m = self.getMsg('anonymous react :) blah')
                    self.assertEqual(m, ircmsgs.IrcMsg(
                        '@+draft/reply=123;+draft/react=:) TAGMSG %s'
                        % self.channel))



# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
