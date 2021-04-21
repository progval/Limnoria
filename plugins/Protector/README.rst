.. _plugin-Protector:

Documentation for the Protector plugin for Supybot
==================================================

Purpose
-------
Defends a channel against actions by people who don't have the proper
capabilities, even if they have +o or +h.

Usage
-----
Prevents users from doing things they are not supposed to do on a channel,
even if they have +o or +h.

.. _conf-Protector:

Configuration
-------------

.. _conf-supybot.plugins.Protector.enable:


supybot.plugins.Protector.enable
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether this plugin is enabled in a given channel.

.. _conf-supybot.plugins.Protector.immune:


supybot.plugins.Protector.immune
  This config variable defaults to " ", is network-specific, and is  channel-specific.

  Determines what nicks the bot will consider to be immune from enforcement. These nicks will not even have their actions watched by this plugin. In general, only the ChanServ for this network will be in this list.

.. _conf-supybot.plugins.Protector.public:


supybot.plugins.Protector.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

