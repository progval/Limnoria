.. _plugin-Limiter:

Documentation for the Limiter plugin for Supybot
================================================

Purpose
-------
This plugin sets channel limits (MODE +l) based on
``plugins.Limiter.MaximumExcess`` plus the current number of users
in the channel. This is useful to prevent flood attacks.

Usage
-----
In order to use this plugin, its config values need to be properly
setup.  supybot.plugins.Limiter.enable needs to be set to True and
supybot.plugins.Limiter.{maximumExcess,minimumExcess} should be set to
values appropriate to your channel (if the defaults aren't satisfactory).
Once these are set, and someone enters/leaves the channel, Supybot will
start setting the proper +l modes.

.. _conf-Limiter:

Configuration
-------------

.. _conf-supybot.plugins.Limiter.enable:


supybot.plugins.Limiter.enable
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will maintain the channel limit to be slightly above the current number of people in the channel, in order to make clone/drone attacks harder.

.. _conf-supybot.plugins.Limiter.maximumExcess:


supybot.plugins.Limiter.maximumExcess
  This config variable defaults to "10", is network-specific, and is  channel-specific.

  Determines the maximum number of free spots that will be saved when limits are being enforced. This should always be larger than supybot.plugins.Limiter.limit.minimumExcess.

.. _conf-supybot.plugins.Limiter.minimumExcess:


supybot.plugins.Limiter.minimumExcess
  This config variable defaults to "5", is network-specific, and is  channel-specific.

  Determines the minimum number of free spots that will be saved when limits are being enforced. This should always be smaller than supybot.plugins.Limiter.limit.maximumExcess.

.. _conf-supybot.plugins.Limiter.public:


supybot.plugins.Limiter.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

