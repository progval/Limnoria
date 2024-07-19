###
# Copyright (c) 2005, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('RSS')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified themself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('RSS', True)


class FeedNames(registry.SpaceSeparatedSetOfStrings):
    List = callbacks.CanonicalNameSet

class FeedItemSortOrder(registry.OnlySomeStrings):
    """Valid values include 'asInFeed', 'oldestFirst', 'newestFirst'."""
    validStrings = ('asInFeed', 'oldestFirst', 'newestFirst', 'outdatedFirst',
            'updatedFirst')

RSS = conf.registerPlugin('RSS')

conf.registerGlobalValue(RSS, 'feeds',
    FeedNames([], _("""Determines what feeds should be accessible as
    commands.""")))

########
# Format

conf.registerChannelValue(RSS, 'headlineSeparator',
    registry.StringSurroundedBySpaces('|', _("""Determines what string is
    used to separate headlines in new feeds.""")))
conf.registerChannelValue(RSS, 'format',
    registry.String(_('$date: $title <$link>'), _("""The format the bot
    will use for displaying headlines of a RSS feed that is triggered
    manually. In addition to fields defined by feedparser ($published
    (the entry date), $title, $link, $description, $id, etc.), the following
    variables can be used: $feed_name (the configured name)
    $feed_title/$feed_subtitle/$feed_author/$feed_language/$feed_link,
    $date (parsed date, as defined in
    supybot.reply.format.time)""")))
conf.registerChannelValue(RSS, 'announceFormat',
    registry.String(_('News from $feed_name: $title <$link>'),
    _("""The format the bot will use for displaying headlines of a RSS feed
    that is announced. See supybot.plugins.RSS.format for the available
    variables.""")))

###########
# Announces

conf.registerChannelValue(RSS, 'announce',
    registry.SpaceSeparatedSetOfStrings([], _("""Determines which RSS feeds
    should be announced in the channel; valid input is a list of strings
    (either registered RSS feeds or RSS feed URLs) separated by spaces.""")))
conf.registerGlobalValue(RSS, 'waitPeriod',
    registry.PositiveInteger(1800, _("""Indicates how many seconds the bot will
    wait between retrieving RSS feeds; requests made within this period will
    return cached results.""")))
conf.registerGlobalValue(RSS, 'sortFeedItems',
    FeedItemSortOrder('asInFeed', _("""Determines whether feed items should be
    sorted by their publication/update timestamp or kept in the same order as
    they appear in a feed.""")))
conf.registerChannelValue(RSS, 'notice',
    registry.Boolean(False, _("""Determines whether announces will be sent
    as notices instead of privmsgs.""")))
conf.registerChannelValue(RSS, 'maximumAnnounceHeadlines',
    registry.PositiveInteger(5, _("""Indicates how many new news entries may
    be sent at the same time. Extra entries will be discarded.""")))

####################
# Headlines filtering
conf.registerChannelValue(RSS, 'defaultNumberOfHeadlines',
    registry.PositiveInteger(1, _("""Indicates how many headlines an rss feed
    will output by default, if no number is provided.""")))
conf.registerChannelValue(RSS, 'initialAnnounceHeadlines',
    registry.Integer(5, _("""Indicates how many headlines an rss feed
    will output when it is first added to announce for a channel.""")))
conf.registerChannelValue(RSS, 'keywordWhitelist',
    registry.SpaceSeparatedSetOfStrings([], _("""Space separated list of 
    strings, lets you filter headlines to those containing one or more items
    in this whitelist.""")))
conf.registerChannelValue(RSS, 'keywordBlacklist',
    registry.SpaceSeparatedSetOfStrings([], _("""Space separated list of 
    strings, lets you filter headlines to those not containing any items
    in this blacklist.""")))


def register_feed_config(name, url=''):
    RSS.feeds().add(name)
    conf.registerGlobalValue(RSS.feeds, name,
        registry.String(url, _("""The URL for the feed %s. Note that because
        announced lines are cached, you may need to reload this plugin after
        changing this option.""" % name)))
    feed_group = conf.registerGroup(RSS.feeds, name)
    conf.registerChannelValue(feed_group, 'format',
            registry.String('', _("""Feed-specific format. Defaults to
            supybot.plugins.RSS.format if empty.""")))
    conf.registerChannelValue(feed_group, 'announceFormat',
            registry.String('', _("""Feed-specific announce format.
            Defaults to supybot.plugins.RSS.announceFormat if empty.""")))
    conf.registerGlobalValue(feed_group, 'waitPeriod',
            registry.NonNegativeInteger(0, _("""If set to a non-zero
            value, overrides supybot.plugins.RSS.waitPeriod for this
            particular feed.""")))

for name in RSS.feeds():
    register_feed_config(name)



# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
