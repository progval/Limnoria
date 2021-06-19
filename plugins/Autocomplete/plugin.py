###
# Copyright (c) 2020, Valentin Lorentz
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

from supybot import conf, ircutils, ircmsgs, callbacks
from supybot.i18n import PluginInternationalization

_ = PluginInternationalization("Autocomplete")


REQUEST_TAG = "+draft/autocomplete-request"
RESPONSE_TAG = "+draft/autocomplete-response"


def _commonPrefix(L):
    """Takes a list of lists, and returns their longest common prefix."""
    assert L
    if len(L) == 1:
        return L[0]

    for n in range(1, max(map(len, L)) + 1):
        prefix = L[0][:n]
        for item in L[1:]:
            if prefix != item[:n]:
                return prefix[0:-1]

    assert False


def _getAutocompleteResponse(irc, msg, payload):
    """Returns the value of the +draft/autocomplete-response tag for the given
    +draft/autocomplete-request payload."""
    tokens = callbacks.tokenize(
        payload, channel=msg.channel, network=irc.network
    )
    normalized_payload = " ".join(tokens)

    candidate_commands = _getCandidates(irc, normalized_payload)

    if len(candidate_commands) == 0:
        # No result
        return None
    elif len(candidate_commands) == 1:
        # One result, return it directly
        commands = candidate_commands
    else:
        # Multiple results, return only the longest common prefix + one word

        tokenized_candidates = [
            callbacks.tokenize(c, channel=msg.channel, network=irc.network)
            for c in candidate_commands
        ]

        common_prefix = _commonPrefix(tokenized_candidates)

        words_after_prefix = {
            candidate[len(common_prefix)] for candidate in tokenized_candidates
        }

        commands = [
            " ".join(common_prefix + [word]) for word in words_after_prefix
        ]

    # strip what the user already typed
    assert all(command.startswith(normalized_payload) for command in commands)
    normalized_payload_length = len(normalized_payload)
    response_items = [
        command[normalized_payload_length:] for command in commands
    ]

    return "\t".join(sorted(response_items))


def _getCandidates(irc, normalized_payload):
    """Returns a list of commands starting with the normalized_payload."""
    candidates = set()
    for cb in irc.callbacks:
        cb_commands = cb.listCommands()

        # copy them with the plugin name (optional when calling a command)
        # at the beginning
        plugin_name = cb.canonicalName()
        cb_commands += [plugin_name + " " + command for command in cb_commands]

        candidates |= {
            command
            for command in cb_commands
            if command.startswith(normalized_payload)
        }

    return candidates


class Autocomplete(callbacks.Plugin):
    """Provides command completion for IRC clients that support it."""

    def _enabled(self, irc, msg):
        return (
            conf.supybot.protocols.irc.experimentalExtensions()
            and self.registryValue("enabled", msg.channel, irc.network)
        )

    def doTagmsg(self, irc, msg):
        if REQUEST_TAG not in msg.server_tags:
            return
        if "msgid" not in msg.server_tags:
            return
        if not self._enabled(irc, msg):
            return

        msgid = msg.server_tags["msgid"]

        text = msg.server_tags[REQUEST_TAG]

        # using callbacks._addressed instead of callbacks.addressed, as
        # callbacks.addressed would tag the m
        payload = callbacks._addressed(irc, msg, payload=text)

        if not payload:
            # not addressed
            return

        # marks used by '_addressed' are usually prefixes (char, string,
        # nick), but may also be suffixes (with
        # supybot.reply.whenAddressedBy.nick.atEnd); but there is no way to
        # have it in the middle of the message AFAIK.
        assert payload in text

        if not text.endswith(payload):
            # If there is a suffix, it means the end of the text is used to
            # address the bot, so it can't be a method to be completed.
            return

        autocomplete_response = _getAutocompleteResponse(irc, msg, payload)
        if not autocomplete_response:
            return

        target = msg.channel or ircutils.nickFromHostmask(msg.prefix)
        irc.queueMsg(
            ircmsgs.IrcMsg(
                server_tags={
                    "+draft/reply": msgid,
                    RESPONSE_TAG: autocomplete_response,
                },
                command="TAGMSG",
                args=[target],
            )
        )


Class = Autocomplete


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
