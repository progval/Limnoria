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

.. _commands-Status:

Commands
--------
.. _command-Status-cmd:

cmd takes no arguments
  Returns some interesting command-related statistics.

.. _command-Status-commands:

commands takes no arguments
  Returns a list of the commands offered by the bot.

.. _command-Status-cpu:

cpu takes no arguments
  Returns some interesting CPU-related statistics on the bot.

.. _command-Status-net:

net takes no arguments
  Returns some interesting network-related statistics.

.. _command-Status-network:

network takes no arguments
  Returns the network the bot is on.

.. _command-Status-processes:

processes takes no arguments
  Returns the number of processes that have been spawned, and list of ones that are still active.

.. _command-Status-server:

server takes no arguments
  Returns the server the bot is on.

.. _command-Status-status:

status takes no arguments
  Returns the status of the bot.

.. _command-Status-threads:

threads takes no arguments
  Returns the current threads that are active.

.. _command-Status-uptime:

uptime takes no arguments
  Returns the amount of time the bot has been running.

Configuration
-------------
supybot.plugins.Status.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

