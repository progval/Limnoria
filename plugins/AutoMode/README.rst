.. _plugin-AutoMode:

Documentation for the AutoMode plugin for Supybot
=================================================

Purpose
-------
Automatically ops, voices, or halfops, or bans people when they join a channel,
according to their capabilities.  If you want your bot automatically op users
when they join your channel, this is the plugin to load.

Usage
-----
This plugin, when configured, allows the bot to automatically set modes
on users when they join.

* if ``plugins.automode.op`` is set to ``True``, users with the
  ``#channel,op`` capability are opped when they join.
* if ``plugins.automode.halfop`` is set to ``True``, users with the
  ``#channel,halfop`` are halfopped when they join.
* if ``plugins.automode.voice`` is set to ``True``, users with the
  ``#channel,voice`` are voiced when they join.

This plugin also kbans people on ``@channel ban list``
(``config plugins.automode.ban``) when they join and if moding users with
lower capability is enabled, that is also applied to users with higher
capability (``config plugins.automode.fallthrough``).

Configuration
-------------
supybot.plugins.AutoMode.alternativeCapabilities
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will check for 'alternative capabilities' (ie. autoop, autohalfop, autovoice) in addition to/instead of classic ones.

supybot.plugins.AutoMode.ban
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will automatically ban people who join the channel and are on the banlist.

  supybot.plugins.AutoMode.ban.period
    This config variable defaults to "86400", is network-specific, and is  channel-specific.

    Determines how many seconds the bot will automatically ban a person when banning.

supybot.plugins.AutoMode.delay
  This config variable defaults to "0", is network-specific, and is  channel-specific.

  Determines how many seconds the bot will wait before applying a mode. Has no effect on bans.

supybot.plugins.AutoMode.enable
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether this plugin is enabled.

supybot.plugins.AutoMode.extra
  This config variable defaults to " ", is network-specific, and is  channel-specific.

  Extra modes that will be applied to a user. Example syntax: user1+o-v user2+v user3-v

supybot.plugins.AutoMode.fallthrough
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will "fall through" to halfop/voicing when auto-opping is turned off but auto-halfopping/voicing are turned on.

supybot.plugins.AutoMode.halfop
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will automatically halfop people with the <channel>,halfop capability when they join the channel.

supybot.plugins.AutoMode.op
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will automatically op people with the <channel>,op capability when they join the channel.

supybot.plugins.AutoMode.owner
  This config variable defaults to "False", is not network-specific, and is  not channel-specific.

  Determines whether this plugin will automode owners even if they don't have op/halfop/voice/whatever capability.

supybot.plugins.AutoMode.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

supybot.plugins.AutoMode.voice
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will automatically voice people with the <channel>,voice capability when they join the channel.

