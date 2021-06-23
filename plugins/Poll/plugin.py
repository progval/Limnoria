###
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

import collections
import re

from supybot import utils, plugins, ircdb, ircutils, callbacks
from supybot.commands import *

try:
    from supybot.i18n import PluginInternationalization

    _ = PluginInternationalization("Poll")
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


Poll = collections.namedtuple("Poll", "question answers votes open")


class Poll_(callbacks.Plugin):
    """Provides a simple way to vote on answers to a question

    For example, this creates a poll::

       <admin> @poll add "Is this a test?" "Yes" "No" "Maybe"
       <bot> The operation succeeded.  Poll # 42 created.

    Creates a poll that can be voted on in this way::

       <citizen1> @vote 42 Yes
       <citizen2> @vote 42 No
       <citizen3> @vote 42 No

    And results::

        <admin> @poll results
        <bot> 2 votes for No, 1 vote for Yes, and 0 votes for Maybe

    Longer answers are possible, and voters only need to use the first
    word of each answer to vote. For example, this creates a poll that
    can be voted on in the same way::

       <admin> @poll add "Is this a test?" "Yes totally" "No no no" "Maybe"
       <bot> The operation succeeded.  Poll # 43 created.

    You can also add a number or letter at the beginning of each question to
    make it easier::

       <admin> @poll add "Who is the best captain?" "1 James T Kirk" "2 Jean-Luc Picard" "3 Benjamin Sisko" "4 Kathryn Janeway"
       <bot> The operation succeeded.  Poll # 44 created.

       <trekkie1> @vote 42 1
       <trekkie2> @vote 42 4
       <trekkie3> @vote 42 4
    """

    def __init__(self, irc):
        super().__init__(irc)

        # {(network, channel): {id: Poll}}
        self._polls = collections.defaultdict(dict)

    def name(self):
        return "Poll"

    def _checkManageCapability(self, irc, msg, channel):
        # Copy-pasted from Topic
        capabilities = self.registryValue(
            "requireManageCapability", channel, irc.network
        )
        for capability in re.split(r"\s*;\s*", capabilities):
            if capability.startswith("channel,"):
                capability = ircdb.makeChannelCapability(
                    channel, capability[8:]
                )
            if capability and ircdb.checkCapability(msg.prefix, capability):
                return
        irc.errorNoCapability(capabilities, Raise=True)

    def _getPoll(self, irc, channel, poll_id):
        poll = self._polls[(irc.network, channel)].get(poll_id)
        if poll is None:
            irc.error(
                _("A poll with this ID does not exist in this channel."),
                Raise=True,
            )
        return poll

    @wrap(["channel", "something", many("something")])
    def add(self, irc, msg, args, channel, question, answers):
        """[<channel>] <question> <answer1> [<answer2> [<answer3> [...]]]

        Creates a new poll with the specified <question> and answers
        on the <channel>.
        The first word of each answer is used as its id to vote,
        so each answer should start with a different word.

        <channel> is only necessary if this command is run in private,
        and defaults to the current channel otherwise."""
        self._checkManageCapability(irc, msg, channel)

        poll_id = max(self._polls[(irc.network, channel)], default=0) + 1

        answers = [(answer.split()[0], answer) for answer in answers]

        answer_id_counts = collections.Counter(id_ for (id_, _) in answers).items()
        duplicate_answer_ids = [
            answer_id for (answer_id, count) in answer_id_counts if count > 1
        ]
        if duplicate_answer_ids:
            irc.error(
                format(
                    _("Duplicate answer identifier(s): %L"), duplicate_answer_ids
                ),
                Raise=True,
            )

        self._polls[(irc.network, channel)][poll_id] = Poll(
            question=question, answers=dict(answers), votes={}, open=True
        )

        irc.replySuccess(_("Poll # %d created.") % poll_id)

    @wrap(["channel", "positiveInt"])
    def close(self, irc, msg, args, channel, poll_id):
        """[<channel>] <poll_id>

        Closes the specified poll."""
        self._checkManageCapability(irc, msg, channel)

        poll = self._getPoll(irc, channel, poll_id)

        if not poll.open:
            irc.error(_("This poll was already closed."), Raise=True)

        poll = Poll(
            question=poll.question,
            answers=poll.answers,
            votes=poll.votes,
            open=False,
        )
        self._polls[(irc.network, channel)][poll_id] = poll
        irc.replySuccess()

    @wrap(["channel", "positiveInt", "somethingWithoutSpaces"])
    def vote(self, irc, msg, args, channel, poll_id, answer_id):
        """[<channel>] <poll_id> <answer_id>

        Registers your vote on the poll <poll_id> as being the answer
        identified by <answer_id> (which is the first word of each possible
        answer)."""

        poll = self._getPoll(irc, channel, poll_id)

        if not poll.open:
            irc.error(_("This poll is closed."), Raise=True)

        if msg.nick in poll.votes:
            irc.error(_("You already voted on this poll."), Raise=True)

        if answer_id not in poll.answers:
            irc.error(
                format(
                    _("Invalid answer ID. Valid answers are: %L"),
                    poll.answers,
                ),
                Raise=True,
            )

        poll.votes[msg.nick] = answer_id

        irc.replySuccess()

    @wrap(["channel", "positiveInt"])
    def results(self, irc, msg, args, channel, poll_id):
        """[<channel>] <poll_id>

        Returns the results of the specified poll."""

        poll = self._getPoll(irc, channel, poll_id)

        counts = collections.Counter(poll.votes.values())

        # Add answers with 0 votes
        counts.update({answer_id: 0 for answer_id in poll.answers})

        results = [
            format(_("%n for %s"), (v, "vote"), k)
            for (k, v) in counts.most_common()
        ]

        irc.replies(results)


Class = Poll_
