###
# Copyright (c) 2020-2021, Valentin Lorentz
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

from supybot import conf, ircmsgs
from supybot.test import *


class AutocompleteTestCase(PluginTestCase):
    plugins = ("Autocomplete", "Later", "Misc")
    # Later and Misc both have a 'tell' command, this allows checking
    # deduplication.

    def _sendRequest(self, request):
        self.irc.feedMsg(
            ircmsgs.IrcMsg(
                prefix="foo!bar@baz",
                server_tags={
                    "msgid": "1234",
                    "+draft/autocomplete-request": request,
                },
                command="TAGMSG",
                args=[self.nick],
            )
        )

    def _assertAutocompleteResponse(self, request, expectedResponse):
        self._sendRequest(request)
        m = self.irc.takeMsg()
        self.assertEqual(
            m.server_tags["+draft/autocomplete-response"], expectedResponse
        )
        self.assertEqual(
            m,
            ircmsgs.IrcMsg(
                server_tags={
                    "+draft/reply": "1234",
                    "+draft/autocomplete-response": expectedResponse,
                },
                command="TAGMSG",
                args=["foo"],
            ),
        )

    def testResponse(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with conf.supybot.plugins.Autocomplete.enabled.context(True):
                self._assertAutocompleteResponse("apro", "pos")

    def testSingleCommandName(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with conf.supybot.plugins.Autocomplete.enabled.context(True):
                self._assertAutocompleteResponse("apro", "pos")
                self._assertAutocompleteResponse("apr", "opos")
                self._assertAutocompleteResponse("tel", "l")

    def testTwoResults(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with conf.supybot.plugins.Autocomplete.enabled.context(True):
                self._assertAutocompleteResponse("te", "ll\tstplugin")

    def testCommandNameAndPluginName(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with conf.supybot.plugins.Autocomplete.enabled.context(True):
                self._assertAutocompleteResponse("misc t", "ell")
                self._assertAutocompleteResponse(
                    "misc c", "learmores\tompletenick"
                )

    def testSinglePluginName(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with conf.supybot.plugins.Autocomplete.enabled.context(True):
                self._assertAutocompleteResponse(
                    "lat", "er notes\ter remove\ter tell\ter undo"
                )

    def testNextWord(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with conf.supybot.plugins.Autocomplete.enabled.context(True):
                self._assertAutocompleteResponse(
                    "later", " notes\t remove\t tell\t undo"
                )

    def testNoResponse(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            self._sendRequest("apro")
            self.assertIsNone(self.irc.takeMsg())

        with conf.supybot.plugins.Autocomplete.enabled.context(True):
            self._sendRequest("apro")
            self.assertIsNone(self.irc.takeMsg())


class AutocompleteChannelTestCase(ChannelPluginTestCase):
    plugins = ("Autocomplete", "Later", "Misc")

    def _sendRequest(self, request):
        self.irc.feedMsg(
            ircmsgs.IrcMsg(
                prefix="foo!bar@baz",
                server_tags={
                    "msgid": "1234",
                    "+draft/autocomplete-request": request,
                },
                command="TAGMSG",
                args=[self.channel],
            )
        )

    def _assertAutocompleteResponse(self, request, expectedResponse):
        self._sendRequest(request)
        m = self.irc.takeMsg()
        self.assertEqual(
            m,
            ircmsgs.IrcMsg(
                server_tags={
                    "+draft/reply": "1234",
                    "+draft/autocomplete-response": expectedResponse,
                },
                command="TAGMSG",
                args=[self.channel],
            ),
        )

    def testResponse(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            with conf.supybot.plugins.Autocomplete.enabled.context(True):
                self._assertAutocompleteResponse("@apro", "pos")

    def testNoResponse(self):
        with conf.supybot.protocols.irc.experimentalExtensions.context(True):
            self._sendRequest("@apro")
            self.assertIsNone(self.irc.takeMsg())

        with conf.supybot.plugins.Autocomplete.enabled.context(True):
            self._sendRequest("@apro")
            self.assertIsNone(self.irc.takeMsg())


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
