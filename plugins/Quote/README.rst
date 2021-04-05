.. _plugin-Quote:

Documentation for the Quote plugin for Supybot
==============================================

Purpose
-------
Maintains a Quotes database for each channel.

Usage
-----
This plugin allows you to add quotes to the database for a channel.

.. _commands-Quote:

Commands
--------
.. _command-Quote-add:

add [<channel>] <text>
  Adds <text> to the quote database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Quote-change:

change [<channel>] <id> <regexp>
  Changes the quote with id <id> according to the regular expression <regexp>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Quote-get:

get [<channel>] <id>
  Gets the quote with id <id> from the quote database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Quote-random:

random [<channel>]
  Returns a random quote from <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Quote-remove:

remove [<channel>] <id>
  Removes the quote with id <id> from the quote database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Quote-replace:

replace [<channel>] <id> <text>
  Replace quote <id> with <text>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Quote-search:

search [<channel>] [--{regexp,by} <value>] [<glob>]
  Searches for quotes matching the criteria given.

.. _command-Quote-stats:

stats [<channel>]
  Returns the number of quotes in the database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

Configuration
-------------
supybot.plugins.Quote.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

