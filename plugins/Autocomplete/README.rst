.. _plugin-Autocomplete:

Documentation for the Autocomplete plugin for Supybot
=====================================================

Purpose
-------
Autocomplete: Provides command autocompletion for IRC clients that support it.

This plugin implements an early draft of the IRCv3 autocompletion client tags.
As this is not yet a released specification, it does nothing unless
``supybot.protocols.irc.experimentalExtensions`` is set to True (keep it set to
False unless you know what you are doing).

If you are interested in this feature, please contribute to
`the discussion <https://github.com/ircv3/ircv3-specifications/pull/415>`_

Usage
-----
Provides command completion for IRC clients that support it.

.. _conf-Autocomplete:

Configuration
-------------

.. _conf-supybot.plugins.Autocomplete.enabled:


supybot.plugins.Autocomplete.enabled
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Whether the bot should reply to autocomplete requests from clients.

.. _conf-supybot.plugins.Autocomplete.public:


supybot.plugins.Autocomplete.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

