.. _plugin-News:

Documentation for the News plugin for Supybot
=============================================

Purpose
-------
A module to allow each channel to have "news".  News items may have expiration
dates.
It was partially inspired by the news system used on #debian's bot.

Usage
-----
This plugin provides a means of maintaining News for a channel.

.. _commands-News:

Commands
--------
.. _command-news-add:

add [<channel>] <expires> <subject>: <text>
  Adds a given news item of <text> to a channel with the given <subject>. If <expires> isn't 0, that news item will expire <expires> seconds from now. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-news-change:

change [<channel>] <id> <regexp>
  Changes the news item with <id> from <channel> according to the regular expression <regexp>. <regexp> should be of the form s/text/replacement/flags. <channel> is only necessary if the message isn't sent on the channel itself.

.. _command-news-news:

news [<channel>] [<id>]
  Display the news items for <channel> in the format of '(#id) subject'. If <id> is given, retrieve only that news item; otherwise retrieve all news items. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-news-old:

old [<channel>] [<id>]
  Returns the old news item for <channel> with <id>. If no number is given, returns all the old news items in reverse order. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-news-remove:

remove [<channel>] <id>
  Removes the news item with <id> from <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _conf-News:

Configuration
-------------

.. _conf-supybot.plugins.News.public:


supybot.plugins.News.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

