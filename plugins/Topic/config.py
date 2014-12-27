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

import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Topic')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Topic', True)


class TopicFormat(registry.TemplatedString):
    "Value must include $topic, otherwise the actual topic would be left out."
    requiredTemplates = ['topic']

Topic = conf.registerPlugin('Topic')
conf.registerChannelValue(Topic, 'separator',
    registry.StringSurroundedBySpaces('|', _("""Determines what separator is
    used between individually added topics in the channel topic.""")))
conf.registerChannelValue(Topic, 'format',
    TopicFormat('$topic', _("""Determines what format is used to add
    topics in the topic.  All the standard substitutes apply, in addition to
    "$topic" for the topic itself.""")))
conf.registerChannelValue(Topic, 'recognizeTopiclen',
    registry.Boolean(True, _("""Determines whether the bot will recognize the
    TOPICLEN value sent to it by the server and thus refuse to send TOPICs
    longer than the TOPICLEN.  These topics are likely to be truncated by the
    server anyway, so this defaults to True.""")))
conf.registerChannelValue(Topic, 'default',
    registry.String('', _("""Determines what the default topic for the channel
    is.  This is used by the default command to set this topic.""")))
conf.registerChannelValue(Topic, 'setOnJoin',
    registry.Boolean(True, _("""Determines whether the bot will automatically
    set the topic on join if it is empty.""")))
conf.registerChannelValue(Topic, 'alwaysSetOnJoin',
    registry.Boolean(False, _("""Determines whether the bot will set the topic
    every time it joins, or only if the topic is empty. Requires 'config
    plugins.topic.setOnJoin' to be set to True.""")))
conf.registerGroup(Topic, 'undo')
conf.registerChannelValue(Topic.undo, 'max',
    registry.NonNegativeInteger(10, _("""Determines the number of previous
    topics to keep around in case the undo command is called.""")))
conf.registerChannelValue(Topic, 'requireManageCapability',
    registry.String('channel,op; channel,halfop', _("""Determines the
    capabilities required (if any) to make any topic changes,
    (everything except for read-only operations). Use 'channel,capab' for
    channel-level capabilities.
    Note that absence of an explicit anticapability means user has
    capability.""")))
conf.registerChannelValue(Topic, 'allowSeparatorinTopics',
    registry.Boolean(True, _("""Determines whether the bot will allow
    topics containing the defined separator to be used. You may want
    to disable this if you are signing all topics by nick (see the 'format'
    option for ways to adjust this).""")))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
