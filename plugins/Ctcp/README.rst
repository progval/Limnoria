.. _plugin-Ctcp:

Documentation for the Ctcp plugin for Supybot
=============================================

Purpose
-------
Handles standard CTCP responses to PING, TIME, SOURCE, VERSION, USERINFO,
and FINGER.

Usage
-----
Provides replies to common CTCPs (version, time, etc.), and a command
to fetch version responses from channels.

Please note that the command `ctcp version` cannot receive any responses if the channel is
mode +C or similar which prevents CTCP requests to channel.

.. _commands-Ctcp:

Commands
--------
.. _command-ctcp-version:

version [<channel>] [--nicks]
  Sends a CTCP VERSION to <channel>, returning the various version strings returned. It waits for 10 seconds before returning the versions received at that point. If --nicks is given, nicks are associated with the version strings; otherwise, only the version strings are given.

.. _conf-Ctcp:

Configuration
-------------

.. _conf-supybot.plugins.Ctcp.public:


supybot.plugins.Ctcp.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Ctcp.userinfo:


supybot.plugins.Ctcp.userinfo
  This config variable defaults to "", is not network-specific, and is  not channel-specific.

  Determines what will be sent when a USERINFO query is received.

.. _conf-supybot.plugins.Ctcp.versionWait:


supybot.plugins.Ctcp.versionWait
  This config variable defaults to "10", is not network-specific, and is  not channel-specific.

  Determines how many seconds the bot will wait after getting a version command (not a CTCP VERSION, but an actual call of the command in this plugin named "version") before replying with the results it has collected.

