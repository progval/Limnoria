.. _plugin-Lart:

Documentation for the Lart plugin for Supybot
=============================================

Purpose
-------
This plugin keeps a database of larts (Luser Attitude Readjustment Tool),
and larts with it.

Usage
-----
Provides an implementation of the Luser Attitude Readjustment Tool
for users.

Example:

* If you add ``slaps $who``.
* And Someone says ``@lart ChanServ``.
* ``* bot slaps ChanServ``.

.. _commands-Lart:

Commands
--------
.. _command-lart-add:

add [<channel>] <text>
  Adds <text> to the lart database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-lart-change:

change [<channel>] <id> <regexp>
  Changes the lart with id <id> according to the regular expression <regexp>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-lart-get:

get [<channel>] <id>
  Gets the lart with id <id> from the lart database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-lart-lart:

lart [<channel>] [<id>] <who|what> [for <reason>]
  Uses the Luser Attitude Readjustment Tool on <who|what> (for <reason>, if given). If <id> is given, uses that specific lart. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-lart-remove:

remove [<channel>] <id>
  Removes the lart with id <id> from the lart database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-lart-search:

search [<channel>] [--{regexp,by} <value>] [<glob>]
  Searches for larts matching the criteria given.

.. _command-lart-stats:

stats [<channel>]
  Returns the number of larts in the database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _conf-Lart:

Configuration
-------------

.. _conf-supybot.plugins.Lart.public:


supybot.plugins.Lart.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Lart.showIds:


supybot.plugins.Lart.showIds
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will show the ids of a lart when the lart is given.

