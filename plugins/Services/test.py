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

from supybot.test import *
import supybot.conf as conf
from supybot.ircmsgs import IrcMsg

class ServicesTestCase(PluginTestCase):
    plugins = ('Services', 'Config')
    config = {
        'plugins.Services.NickServ': 'NickServ',
        'plugins.Services.ChanServ': 'ChanServ',
        }

    def testPasswordAndIdentify(self):
        self.assertNotError('services password foo bar')
        self.assertError('services identify') # Don't have a password.
        self.assertNotError('services password %s baz' % self.nick)
        m = self.assertNotError('services identify')
        self.assertTrue(m.args[0] == 'NickServ')
        self.assertTrue(m.args[1].lower() == 'identify baz')
        self.assertNotError('services password %s biff' % self.nick)
        m = self.assertNotError('services identify')
        self.assertTrue(m.args[0] == 'NickServ')
        self.assertTrue(m.args[1].lower() == 'identify biff')

    def testPasswordConfg(self):
        self.assertNotError('config plugins.Services.nicks ""')
        self.assertNotError('config network plugins.Services.nicks ""')

        self.assertNotError('services password %s bar' % self.nick)

        self.assertResponse(
            'config plugins.Services.nicks',
            'Global:  ; test: %s' % self.nick)
        self.assertResponse(
            'config plugins.Services.nickserv.password.%s' % self.nick,
            'Global: bar; test: bar')

        self.assertNotError(
            'config network plugins.Services.nickserv.password.%s bar2'
            % self.nick)
        self.assertResponse(
            'config plugins.Services.nickserv.password.%s' % self.nick,
            'Global: bar; test: bar2')
        self.assertResponse(
            'config plugins.Services.nickserv.password.%s' % self.nick,
            'Global: bar; test: bar2')

        m = self.assertNotError('services identify')
        self.assertTrue(m.args[0] == 'NickServ')
        self.assertTrue(m.args[1].lower() == 'identify bar2')

    def testRegisterNoExperimentalExtensions(self):
        self.assertRegexp(
            "register p4ssw0rd", "error: Experimental IRC extensions")

        self.irc.feedMsg(IrcMsg(
            command="FAIL", args=["REGISTER", "BLAH", "message"]))
        self.assertIsNone(self.irc.takeMsg())

        self.irc.feedMsg(IrcMsg(
            command="REGISTER", args=["SUCCESS", "account", "msg"]))
        self.assertIsNone(self.irc.takeMsg())

        self.irc.feedMsg(IrcMsg(
            command="REGISTER",
            args=["VERIFICATION_REQUIRED", "account", "msg"]))
        self.assertIsNone(self.irc.takeMsg())


class ExperimentalServicesTestCase(PluginTestCase):
    plugins = ["Services"]
    timeout = 0.1

    def setUp(self):
        super().setUp()
        conf.supybot.protocols.irc.experimentalExtensions.setValue(True)
        self._initialCaps = self.irc.state.capabilities_ls.copy()
        self.irc.state.capabilities_ls["draft/register"] = None
        self.irc.state.capabilities_ls["labeled-response"] = None

    def tearDown(self):
        self.irc.state.capabilities_ls = self._initialCaps
        conf.supybot.protocols.irc.experimentalExtensions.setValue(False)
        super().tearDown()

    def testRegisterSupportError(self):
        old_caps = self.irc.state.capabilities_ls.copy()
        try:
            del self.irc.state.capabilities_ls["labeled-response"]
            self.assertRegexp(
                "register p4ssw0rd",
                "error: This network does not support labeled-response.")

            del self.irc.state.capabilities_ls["draft/register"]
            self.assertRegexp(
                "register p4ssw0rd",
                "error: This network does not support draft/register.")
        finally:
            self.irc.state.capabilities_ls = old_caps

    def testRegisterRequireEmail(self):
        old_caps = self.irc.state.capabilities_ls.copy()
        try:
            self.irc.state.capabilities_ls["draft/register"] = "email-required"
            self.assertRegexp(
                "register p4ssw0rd",
                "error: This network requires an email address to register.")
        finally:
            self.irc.state.capabilities_ls = old_caps

    def testRegisterSuccess(self):
        m = self.getMsg("register p4ssw0rd")
        label = m.server_tags.pop("label")
        self.assertEqual(m, IrcMsg(command="REGISTER", args=["*", "p4ssw0rd"]))
        self.irc.feedMsg(IrcMsg(
            server_tags={"label": label},
            command="REGISTER",
            args=["SUCCESS", "accountname", "welcome!"]
        ))
        self.assertResponse(
            "",
            "Registration of account accountname on test succeeded: welcome!")

    def testRegisterSuccessBatch(self):
        # oragono replies with a batch
        m = self.getMsg("register p4ssw0rd")
        label = m.server_tags.pop("label")
        self.assertEqual(m, IrcMsg(command="REGISTER", args=["*", "p4ssw0rd"]))

        batch_name = "Services_testRegisterSuccessBatch"
        self.irc.feedMsg(IrcMsg(
            server_tags={"label": label},
            command="BATCH",
            args=["+" + batch_name, "labeled-response"]
        ))
        self.irc.feedMsg(IrcMsg(
            server_tags={"batch": batch_name},
            command="REGISTER",
            args=["SUCCESS", "accountname", "welcome!"]
        ))
        self.irc.feedMsg(IrcMsg(
            server_tags={"batch": batch_name},
            command="NOTICE",
            args=[self.irc.nick, "Registration succeeded blah blah blah"]
        ))
        self.irc.feedMsg(IrcMsg(
            command="BATCH",
            args=["-" + batch_name],
        ))

        self.assertResponse(
            "",
            "Registration of account accountname on test succeeded: welcome!")

    def testRegisterSuccessEmail(self):
        m = self.getMsg("register p4ssw0rd foo@example.org")
        label = m.server_tags.pop("label")
        self.assertEqual(m, IrcMsg(
            command="REGISTER", args=["foo@example.org", "p4ssw0rd"]))
        self.irc.feedMsg(IrcMsg(
            server_tags={"label": label},
            command="REGISTER",
            args=["SUCCESS", "accountname", "welcome!"]
        ))
        self.assertResponse(
            "",
            "Registration of account accountname on test succeeded: welcome!")

    def testRegisterVerify(self):
        m = self.getMsg("register p4ssw0rd")
        label = m.server_tags.pop("label")
        self.assertEqual(m, IrcMsg(command="REGISTER", args=["*", "p4ssw0rd"]))
        self.irc.feedMsg(IrcMsg(
            server_tags={"label": label},
            command="REGISTER",
            args=["VERIFICATION_REQUIRED", "accountname", "check your emails"]
        ))
        self.assertResponse(
            "",
            "Registration of accountname on test requires verification "
            "to complete: check your emails")

        m = self.getMsg("verify accountname c0de")
        label = m.server_tags.pop("label")
        self.assertEqual(m, IrcMsg(
            command="VERIFY", args=["accountname", "c0de"]))
        self.irc.feedMsg(IrcMsg(
            server_tags={"label": label},
            command="VERIFY",
            args=["SUCCESS", "accountname", "welcome!"]
        ))
        self.assertResponse(
            "",
            "Verification of account accountname on test succeeded: welcome!")

    def testRegisterVerifyBatch(self):
        m = self.getMsg("register p4ssw0rd")
        label = m.server_tags.pop("label")
        self.assertEqual(m, IrcMsg(command="REGISTER", args=["*", "p4ssw0rd"]))
        self.irc.feedMsg(IrcMsg(
            server_tags={"label": label},
            command="REGISTER",
            args=["VERIFICATION_REQUIRED", "accountname", "check your emails"]
        ))
        self.assertResponse(
            "",
            "Registration of accountname on test requires verification "
            "to complete: check your emails")

        m = self.getMsg("verify accountname c0de")
        label = m.server_tags.pop("label")
        self.assertEqual(m, IrcMsg(
            command="VERIFY", args=["accountname", "c0de"]))

        batch_name = "Services_testVerifySuccessBatch"
        self.irc.feedMsg(IrcMsg(
            server_tags={"label": label},
            command="BATCH",
            args=["+" + batch_name, "labeled-response"]
        ))
        self.irc.feedMsg(IrcMsg(
            server_tags={"batch": batch_name},
            command="VERIFY",
            args=["SUCCESS", "accountname", "welcome!"]
        ))
        self.irc.feedMsg(IrcMsg(
            server_tags={"batch": batch_name},
            command="NOTICE",
            args=[self.irc.nick, "Verification succeeded blah blah blah"]
        ))
        self.irc.feedMsg(IrcMsg(
            command="BATCH",
            args=["-" + batch_name],
        ))

        self.assertResponse(
            "",
            "Verification of account accountname on test succeeded: welcome!")


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

