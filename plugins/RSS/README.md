This plugin allows you to poll and periodically announce new items from
RSS feeds.

In order to use this plugin you must have the following modules
installed:
* feedparser: http://feedparser.org/

If you are experiencing TypeError issues with Python 3, please apply this
patch: http://code.google.com/p/feedparser/issues/detail?id=403

Basic usage
-----------

Adding a feed
`@rss add supybot http://sourceforge.net/export/rss2_projfiles.php?group_id=58965`

Add announcements for a feed
`@rss announce add supybot`

Stop announcements for a feed
`@rss announce remove supybot`

News on their own lines
-----------------------

If you want the feed topics to be on their own lines instead of being separated by 
the separator which you have configured you can set `reply.onetoone` to False.

Please first read the help for that configuration variable

`@config help reply.onetoone`

and understand what it says and then you can do

`@config reply.onetoone False`
