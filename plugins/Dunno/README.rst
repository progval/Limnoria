.. _plugin-Dunno:

Documentation for the Dunno plugin for Supybot
==============================================

Purpose
-------
The Dunno module is used to spice up the reply when given an invalid command
with random 'I dunno'-like responses.  If you want something spicier than
'<x> is not a valid command'-like responses, use this plugin.
Like Success does for the  'The operation succeeded.' reply.

Usage
-----
This plugin was written initially to work with MoobotFactoids, the two
of them to provide a similar-to-moobot-and-blootbot interface for factoids.
Basically, it replaces the standard 'Error: <x> is not a valid command.'
messages with messages kept in a database, able to give more personable
responses.

Commands
--------
add [<channel>] <text>
  Adds <text> to the dunno database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

change [<channel>] <id> <regexp>
  Changes the dunno with id <id> according to the regular expression <regexp>. <channel> is only necessary if the message isn't sent in the channel itself.

get [<channel>] <id>
  Gets the dunno with id <id> from the dunno database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

remove [<channel>] <id>
  Removes the dunno with id <id> from the dunno database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

search [<channel>] [--{regexp,by} <value>] [<glob>]
  Searches for dunnos matching the criteria given.

stats [<channel>]
  Returns the number of dunnos in the database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

Configuration
-------------
supybot.plugins.Dunno.prefixNick
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will prefix the nick of the user giving an invalid command to the "dunno" response.

supybot.plugins.Dunno.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

