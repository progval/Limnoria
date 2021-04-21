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
.. _command-quote-add:

add [<channel>] <text>
  Adds <text> to the quote database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quote-change:

change [<channel>] <id> <regexp>
  Changes the quote with id <id> according to the regular expression <regexp>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quote-get:

get [<channel>] <id>
  Gets the quote with id <id> from the quote database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quote-random:

random [<channel>]
  Returns a random quote from <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quote-remove:

remove [<channel>] <id>
  Removes the quote with id <id> from the quote database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quote-replace:

replace [<channel>] <id> <text>
  Replace quote <id> with <text>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quote-search:

search [<channel>] [--{regexp,by} <value>] [<glob>]
  Searches for quotes matching the criteria given.

.. _command-quote-stats:

stats [<channel>]
  Returns the number of quotes in the database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _conf-Quote:

Configuration
-------------

.. _conf-supybot.plugins.Quote.public:


supybot.plugins.Quote.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

