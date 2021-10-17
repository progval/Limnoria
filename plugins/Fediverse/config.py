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

from supybot import conf, registry

try:
    from supybot.i18n import PluginInternationalization

    _ = PluginInternationalization("Fediverse")
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn

    conf.registerPlugin("Fediverse", True)


Fediverse = conf.registerPlugin("Fediverse")
conf.registerGroup(Fediverse, "snarfers")
conf.registerChannelValue(
    Fediverse.snarfers,
    "username",
    registry.Boolean(
        False,
        _(
            """Determines whether the bot will output the profile of
            @username@hostname accounts it sees in channel messages."""
        ),
    ),
)
conf.registerChannelValue(
    Fediverse.snarfers,
    "profile",
    registry.Boolean(
        False,
        _(
            """Determines whether the bot will output the profile of
            URLs to Fediverse accounts it sees in channel messages."""
        ),
    ),
)
conf.registerChannelValue(
    Fediverse.snarfers,
    "status",
    registry.Boolean(
        False,
        _(
            """Determines whether the bot will output the content of
            statuses whose URLs it sees in channel messages."""
        ),
    ),
)

conf.registerGroup(Fediverse, "format")
conf.registerGroup(Fediverse.format, "statuses")

conf.registerChannelValue(
    Fediverse.format.statuses,
    "showContentWithCW",
    registry.Boolean(
        True,
        _(
            """Determines whether the content of a status will be shown
            when the status has a Content Warning."""
        ),
    ),
)


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
