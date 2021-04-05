.. _plugin-Admin:

Documentation for the Admin plugin for Supybot
==============================================

Purpose
-------
These are commands useful for administrating the bot; they all require their
caller to have the 'admin' capability.  This plugin is loaded by default.

Usage
-----
This plugin provides access to administrative commands, such as
adding capabilities, managing ignore lists, and joining channels.
This is a core Supybot plugin that should not be removed!

Commands
--------
acmd <command> [<arg> ...]
  Perform <command> (with associated <arg>s on all channels on current network.

capability add <name|hostmask> <capability>
  Gives the user specified by <name> (or the user to whom <hostmask> currently maps) the specified capability <capability>

capability remove <name|hostmask> <capability>
  Takes from the user specified by <name> (or the user to whom <hostmask> currently maps) the specified capability <capability>

channels takes no arguments
  Returns the channels the bot is on.

clearq takes no arguments
  Clears the current send queue for this network.

ignore add <hostmask|nick> [<expires>]
  This will set a persistent ignore on <hostmask> or the hostmask currently associated with <nick>. <expires> is an optional argument specifying when (in "seconds from now") the ignore will expire; if it isn't given, the ignore will never automatically expire.

ignore list takes no arguments
  Lists the hostmasks that the bot is ignoring.

ignore remove <hostmask|nick>
  This will remove the persistent ignore on <hostmask> or the hostmask currently associated with <nick>.

join <channel> [<key>]
  Tell the bot to join the given channel. If <key> is given, it is used when attempting to join the channel.

nick [<nick>] [<network>]
  Changes the bot's nick to <nick>. If no nick is given, returns the bot's current nick.

Configuration
-------------
supybot.plugins.Admin.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

