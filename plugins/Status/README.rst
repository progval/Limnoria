.. _plugin-Status:

Documentation for the Status plugin for Supybot
===============================================

Purpose
-------
A simple module to handle various informational commands querying the bot's
current status and statistics, like its uptime.

Usage
-----
This plugin allows you to view different bot statistics, for example,
uptime.

Commands
--------
cmd takes no arguments
  Returns some interesting command-related statistics.

commands takes no arguments
  Returns a list of the commands offered by the bot.

cpu takes no arguments
  Returns some interesting CPU-related statistics on the bot.

net takes no arguments
  Returns some interesting network-related statistics.

network takes no arguments
  Returns the network the bot is on.

processes takes no arguments
  Returns the number of processes that have been spawned, and list of ones that are still active.

server takes no arguments
  Returns the server the bot is on.

status takes no arguments
  Returns the status of the bot.

threads takes no arguments
  Returns the current threads that are active.

uptime takes no arguments
  Returns the amount of time the bot has been running.

Configuration
-------------
supybot.plugins.Status.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

