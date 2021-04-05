.. _plugin-Praise:

Documentation for the Praise plugin for Supybot
===============================================

Purpose
-------
Hand out praise to IRC denizens with this plugin.

Usage
-----
Praise is a plugin for ... well, praising things.  Feel free to add
your own flavor to it by customizing what praises it gives.  Use "praise
add <text>" to add new ones, making sure to include "$who" in <text> where
you want to insert the thing being praised.

Example:

* If you add ``hugs $who``
* Someone says ``@praise ChanServ``.
* ``* bot hugs ChanServ``

Commands
--------
add [<channel>] <text>
  Adds <text> to the praise database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

change [<channel>] <id> <regexp>
  Changes the praise with id <id> according to the regular expression <regexp>. <channel> is only necessary if the message isn't sent in the channel itself.

get [<channel>] <id>
  Gets the praise with id <id> from the praise database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

praise [<channel>] [<id>] <who|what> [for <reason>]
  Praises <who|what> (for <reason>, if given). If <id> is given, uses that specific praise. <channel> is only necessary if the message isn't sent in the channel itself.

remove [<channel>] <id>
  Removes the praise with id <id> from the praise database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

search [<channel>] [--{regexp,by} <value>] [<glob>]
  Searches for praises matching the criteria given.

stats [<channel>]
  Returns the number of praises in the database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

Configuration
-------------
supybot.plugins.Praise.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

supybot.plugins.Praise.showIds
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will show the ids of a praise when the praise is given.

