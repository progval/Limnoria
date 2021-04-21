.. _plugin-NickCapture:

Documentation for the NickCapture plugin for Supybot
====================================================

Purpose
-------
This module attempts to capture the bot's nick, watching for an opportunity to
switch to that nick.

Usage
-----
This plugin constantly tries to take whatever nick is configured as
supybot.nick.  Just make sure that's set appropriately, and thus plugin
will do the rest.

.. _conf-NickCapture:

Configuration
-------------

.. _conf-supybot.plugins.NickCapture.ison:


supybot.plugins.NickCapture.ison
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether the bot will check occasionally if its preferred nick is in use via the ISON command.

  .. _conf-supybot.plugins.NickCapture.ison.period:


  supybot.plugins.NickCapture.ison.period
    This config variable defaults to "600", is not network-specific, and is  not channel-specific.

    Determines how often (in seconds) the bot will check whether its nick ISON.

.. _conf-supybot.plugins.NickCapture.public:


supybot.plugins.NickCapture.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

