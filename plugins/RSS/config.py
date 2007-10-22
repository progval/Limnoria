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
import supybot.callbacks as callbacks

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('RSS', True)


class FeedNames(registry.SpaceSeparatedListOfStrings):
    List = callbacks.CanonicalNameSet

RSS = conf.registerPlugin('RSS')
conf.registerChannelValue(RSS, 'bold', registry.Boolean(
    True, """Determines whether the bot will bold the title of the feed when it
    announces new news."""))
conf.registerChannelValue(RSS, 'headlineSeparator',
    registry.StringSurroundedBySpaces(' || ', """Determines what string is used
    to separate headlines in new feeds."""))
conf.registerChannelValue(RSS, 'announcementPrefix',
    registry.StringWithSpaceOnRight('New news from ', """Determines what prefix
    is prepended (if any) to the new news item announcements made in the
    channel."""))
conf.registerChannelValue(RSS, 'announce',
    registry.SpaceSeparatedSetOfStrings([], """Determines which RSS feeds
    should be announced in the channel; valid input is a list of strings
    (either registered RSS feeds or RSS feed URLs) separated by spaces."""))
conf.registerGlobalValue(RSS, 'waitPeriod',
    registry.PositiveInteger(1800, """Indicates how many seconds the bot will
    wait between retrieving RSS feeds; requests made within this period will
    return cached results."""))
conf.registerGlobalValue(RSS, 'feeds',
    FeedNames([], """Determines what feeds should be accessible as
    commands."""))
conf.registerChannelValue(RSS, 'showLinks',
    registry.Boolean(False, """Determines whether the bot will list the link
    along with the title of the feed when the rss command is called.
    supybot.plugins.RSS.announce.showLinks affects whether links will be
    listed when a feed is automatically announced."""))

conf.registerGroup(RSS, 'announce')
conf.registerChannelValue(RSS.announce, 'showLinks',
    registry.Boolean(False, """Determines whether the bot will list the link
    along with the title of the feed when a feed is automatically
    announced."""))



# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
