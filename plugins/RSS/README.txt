This plugin allows you to poll and periodically announce new items from
RSS feeds.

In order to use this plugin you must have the following modules
installed:
- feedparser: http://feedparser.org/

Basic usage
-----------

Adding a feed
@rss add supybot https://github.com/Supybot/Supybot/commits/master.atom

Add announcements for a feed
@rss announce add supybot

Stop announcements for a feed
@rss announce remove supybot
