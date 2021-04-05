.. _plugin-RSS:

Documentation for the RSS plugin for Supybot
============================================

Purpose
-------
Provides basic functionality for handling RSS/RDF feeds, and allows announcing
them periodically to channels.
In order to use this plugin you must have the following modules
installed:
* feedparser: http://feedparser.org/

Usage
-----
This plugin is useful both for announcing updates to RSS feeds in a
channel, and for retrieving the headlines of RSS feeds via command.  Use
the "add" command to add feeds to this plugin, and use the "announce"
command to determine what feeds should be announced in a given channel.

Basic usage
^^^^^^^^^^^

1. Add a feed using
   ``@rss add limnoria https://github.com/ProgVal/Limnoria/tags.atom``.

   * This is RSS feed of Limnoria's stable releases.
   * You can now check the latest news from the feed with ``@limnoria``.

2. To have new news automatically announced on the channel, use
   ``@rss announce add Limnoria``.

To add another feed, simply replace limnoria and the address using name
of the feed and address of the feed. For example, YLE News:

1. ``@rss add yle http://yle.fi/uutiset/rss/uutiset.rss?osasto=news``
2. ``@rss announce add yle``

News on their own lines
^^^^^^^^^^^^^^^^^^^^^^^

If you want the feed topics to be on their own lines instead of being separated by
the separator which you have configured you can set `reply.onetoone` to False.

Please first read the help for that configuration variable

``@config help reply.onetoone``

and understand what it says and then you can do

``@config reply.onetoone False``

Commands
--------
add <name> <url>
  Adds a command to this plugin that will look up the RSS feed at the given URL.

announce add [<channel>] <name|url> [<name|url> ...]
  Adds the list of feeds to the current list of announced feeds in <channel>. Valid feeds include the names of registered feeds as well as URLs for RSS feeds. <channel> is only necessary if the message isn't sent in the channel itself.

announce channels <name|url>
  Returns a list of channels that the given feed name or URL is being announced to.

announce list [<channel>]
  Returns the list of feeds announced in <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

announce remove [<channel>] <name|url> [<name|url> ...]
  Removes the list of feeds from the current list of announced feeds in <channel>. Valid feeds include the names of registered feeds as well as URLs for RSS feeds. <channel> is only necessary if the message isn't sent in the channel itself.

info <url|feed>
  Returns information from the given RSS feed, namely the title, URL, description, and last update date, if available.

remove <name>
  Removes the command for looking up RSS feeds at <name> from this plugin.

rss <name|url> [<number of headlines>]
  Gets the title components of the given RSS feed. If <number of headlines> is given, return only that many headlines.

Configuration
-------------
supybot.plugins.RSS.announce
  This config variable defaults to " ", is network-specific, and is  channel-specific.

  Determines which RSS feeds should be announced in the channel; valid input is a list of strings (either registered RSS feeds or RSS feed URLs) separated by spaces.

supybot.plugins.RSS.announceFormat
  This config variable defaults to "News from $feed_name: $title <$link>", is network-specific, and is  channel-specific.

  The format the bot will use for displaying headlines of a RSS feed that is announced. See supybot.plugins.RSS.format for the available variables.

supybot.plugins.RSS.defaultNumberOfHeadlines
  This config variable defaults to "1", is network-specific, and is  channel-specific.

  Indicates how many headlines an rss feed will output by default, if no number is provided.

supybot.plugins.RSS.feeds
  This config variable defaults to " ", is not network-specific, and is  not channel-specific.

  Determines what feeds should be accessible as commands.

supybot.plugins.RSS.format
  This config variable defaults to "$date: $title <$link>", is network-specific, and is  channel-specific.

  The format the bot will use for displaying headlines of a RSS feed that is triggered manually. In addition to fields defined by feedparser ($published (the entry date), $title, $link, $description, $id, etc.), the following variables can be used: $feed_name, $date (parsed date, as defined in supybot.reply.format.time)

supybot.plugins.RSS.headlineSeparator
  This config variable defaults to " | ", is network-specific, and is  channel-specific.

  Determines what string is used to separate headlines in new feeds.

supybot.plugins.RSS.initialAnnounceHeadlines
  This config variable defaults to "5", is network-specific, and is  channel-specific.

  Indicates how many headlines an rss feed will output when it is first added to announce for a channel.

supybot.plugins.RSS.keywordBlacklist
  This config variable defaults to " ", is network-specific, and is  channel-specific.

  Space separated list of strings, lets you filter headlines to those not containing any items in this blacklist.

supybot.plugins.RSS.keywordWhitelist
  This config variable defaults to " ", is network-specific, and is  channel-specific.

  Space separated list of strings, lets you filter headlines to those containing one or more items in this whitelist.

supybot.plugins.RSS.maximumAnnounceHeadlines
  This config variable defaults to "5", is network-specific, and is  channel-specific.

  Indicates how many new news entries may be sent at the same time. Extra entries will be discarded.

supybot.plugins.RSS.notice
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether announces will be sent as notices instead of privmsgs.

supybot.plugins.RSS.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

supybot.plugins.RSS.sortFeedItems
  This config variable defaults to "asInFeed", is not network-specific, and is  not channel-specific.

  Determines whether feed items should be sorted by their publication/update timestamp or kept in the same order as they appear in a feed.  Valid strings: asInFeed, oldestFirst, newestFirst, outdatedFirst, and updatedFirst.

supybot.plugins.RSS.waitPeriod
  This config variable defaults to "1800", is not network-specific, and is  not channel-specific.

  Indicates how many seconds the bot will wait between retrieving RSS feeds; requests made within this period will return cached results.

