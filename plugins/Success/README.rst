.. _plugin-Success:

Documentation for the Success plugin for Supybot
================================================

Purpose
-------
The Success plugin spices up success replies by allowing custom messages
instead of the default 'The operation succeeded.' message;
like Dunno does for "no such command" replies.

Usage
-----
This plugin was written initially to work with MoobotFactoids, the two
of them to provide a similar-to-moobot-and-blootbot interface for factoids.
Basically, it replaces the standard 'The operation succeeded.' messages
with messages kept in a database, able to give more personable
responses.

Commands
--------
add [<channel>] <text>
  Adds <text> to the success database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

change [<channel>] <id> <regexp>
  Changes the success with id <id> according to the regular expression <regexp>. <channel> is only necessary if the message isn't sent in the channel itself.

get [<channel>] <id>
  Gets the success with id <id> from the success database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

remove [<channel>] <id>
  Removes the success with id <id> from the success database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

search [<channel>] [--{regexp,by} <value>] [<glob>]
  Searches for successes matching the criteria given.

stats [<channel>]
  Returns the number of successes in the database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

Configuration
-------------
supybot.plugins.Success.prefixNick
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will prefix the nick of the user giving an invalid command to the success response.

supybot.plugins.Success.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

