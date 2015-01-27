This plugin allows you to poll and periodically announce new items from
RSS feeds.

In order to use this plugin you must have the following modules
installed:
* feedparser: http://feedparser.org/

If you are experiencing TypeError issues with Python 3, please apply this
patch: http://code.google.com/p/feedparser/issues/detail?id=403

Basic usage
-----------

1. Add a feed using
`@rss add limnoria https://github.com/ProgVal/Limnoria/tags.atom`.
    * This is RSS feed of Limnoria's stable releases.
    * You can now check the latest news from the feed with `@limnoria`.
2. To have new news automatically announced on the channel, use
`@rss announce add Limnoria`.

To add another feed, simply replace limnoria and the address using name
of the feed and address of the feed. For example, YLE News:

1. `@rss add yle http://yle.fi/uutiset/rss/uutiset.rss?osasto=news`
2. `@rss announce add yle`

News on their own lines
-----------------------

If you want the feed topics to be on their own lines instead of being separated by 
the separator which you have configured you can set `reply.onetoone` to False.

Please first read the help for that configuration variable

`@config help reply.onetoone`

and understand what it says and then you can do

`@config reply.onetoone False`
