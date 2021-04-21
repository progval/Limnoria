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
.. _command-status-cmd:

cmd takes no arguments
  Returns some interesting command-related statistics.

.. _command-status-commands:

commands takes no arguments
  Returns a list of the commands offered by the bot.

.. _command-status-cpu:

cpu takes no arguments
  Returns some interesting CPU-related statistics on the bot.

.. _command-status-net:

net takes no arguments
  Returns some interesting network-related statistics.

.. _command-status-network:

network takes no arguments
  Returns the network the bot is on.

.. _command-status-processes:

processes takes no arguments
  Returns the number of processes that have been spawned, and list of ones that are still active.

.. _command-status-server:

server takes no arguments
  Returns the server the bot is on.

.. _command-status-status:

status takes no arguments
  Returns the status of the bot.

.. _command-status-threads:

threads takes no arguments
  Returns the current threads that are active.

.. _command-status-uptime:

uptime takes no arguments
  Returns the amount of time the bot has been running.

.. _conf-Status:

Configuration
-------------

.. _conf-supybot.plugins.Status.cpu:


supybot.plugins.Status.cpu
  This is a group of:

  .. _conf-supybot.plugins.Status.cpu.children:


  supybot.plugins.Status.cpu.children
    This config variable defaults to "True", is network-specific, and is  channel-specific.

    Determines whether the cpu command will list the time taken by children as well as the bot's process.

  .. _conf-supybot.plugins.Status.cpu.memory:


  supybot.plugins.Status.cpu.memory
    This config variable defaults to "True", is network-specific, and is  channel-specific.

    Determines whether the cpu command will report the amount of memory being used by the bot.

  .. _conf-supybot.plugins.Status.cpu.threads:


  supybot.plugins.Status.cpu.threads
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether the cpu command will provide the number of threads spawned and active.

.. _conf-supybot.plugins.Status.public:


supybot.plugins.Status.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

