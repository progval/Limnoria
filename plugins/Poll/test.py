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

from supybot.test import *


class PollTestCase(ChannelPluginTestCase):
    plugins = ("Poll",)

    def testBasics(self):
        self.assertResponse(
            'poll add "Is this a test?" "Yes" "No" "Maybe"',
            "The operation succeeded.  Poll # 1 created.",
        )

        self.assertNotError("vote 1 Yes", frm="voter1!foo@bar")
        self.assertNotError("vote 1 No", frm="voter2!foo@bar")
        self.assertNotError("vote 1 No", frm="voter3!foo@bar")

        self.assertResponse(
            "results 1",
            "2 votes for No, 1 vote for Yes, and 0 votes for Maybe",
        )

    def testDoubleVoting(self):
        self.assertResponse(
            'poll add "Is this a test?" "Yes" "No" "Maybe"',
            "The operation succeeded.  Poll # 1 created.",
        )

        self.assertNotError("vote 1 Yes", frm="voter1!foo@bar")
        self.assertNotError("vote 1 No", frm="voter2!foo@bar")
        self.assertResponse(
            "vote 1 Yes",
            "voter1: Error: You already voted on this poll.",
            frm="voter1!foo@bar",
        )

        self.assertRegexp(
            "results 1",
            "1 vote for (Yes|No), 1 vote for (Yes|No), and 0 votes for Maybe",
        )

    def testClosed(self):
        self.assertResponse(
            'poll add "Is this a test?" "Yes" "No" "Maybe"',
            "The operation succeeded.  Poll # 1 created.",
        )

        self.assertNotError("vote 1 Yes", frm="voter1!foo@bar")
        self.assertNotError("vote 1 No", frm="voter2!foo@bar")
        self.assertNotError("close 1")
        self.assertResponse(
            "vote 1 Yes",
            "voter3: Error: This poll is closed.",
            frm="voter3!foo@bar",
        )
        self.assertRegexp("close 1", "already closed")

        self.assertRegexp(
            "results 1",
            "1 vote for (Yes|No), 1 vote for (Yes|No), and 0 votes for Maybe",
        )

    def testNonExisting(self):
        self.assertResponse(
            'poll add "Is this a test?" "Yes" "No" "Maybe"',
            "The operation succeeded.  Poll # 1 created.",
        )

        self.assertRegexp("vote 2 Yes", "does not exist")

    def testLongAnswers(self):
        self.assertResponse(
            'poll add "Is this a test?" "Yes totally" "No no no" "Maybe"',
            "The operation succeeded.  Poll # 1 created.",
        )

        self.assertNotError("vote 1 Yes", frm="voter1!foo@bar")
        self.assertNotError("vote 1 No", frm="voter2!foo@bar")
        self.assertNotError("vote 1 No", frm="voter3!foo@bar")

        self.assertResponse(
            "results 1",
            "2 votes for No, 1 vote for Yes, and 0 votes for Maybe",
        )

    def testDuplicateId(self):
        self.assertResponse(
            'poll add "Is this a test?" "Yes" "Yes" "Maybe"',
            "Error: Duplicate answer identifier(s): Yes",
        )

        self.assertResponse(
            'poll add "Is this a test?" "Yes totally" "Yes and no" "Maybe"',
            "Error: Duplicate answer identifier(s): Yes",
        )
