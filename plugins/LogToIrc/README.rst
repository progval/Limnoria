.. _plugin-LogToIrc:

Documentation for the LogToIrc plugin for Supybot
=================================================

Purpose
-------
Allows for sending the bot's logging output to channels or users.

.. _conf-LogToIrc:

Configuration
-------------

.. _conf-supybot.plugins.LogToIrc.channelModesRequired:


supybot.plugins.LogToIrc.channelModesRequired
  This config variable defaults to "s", is network-specific, and is  not channel-specific.

  Determines what channel modes a channel will be required to have for the bot to log to the channel. If this string is empty, no modes will be checked.

.. _conf-supybot.plugins.LogToIrc.color:


supybot.plugins.LogToIrc.color
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot's logs to IRC will be colorized with mIRC colors.

.. _conf-supybot.plugins.LogToIrc.level:


supybot.plugins.LogToIrc.level
  This config variable defaults to "WARNING", is network-specific, and is  channel-specific.

  Determines what the minimum priority level logged will be to IRC. See supybot.log.level for possible values. DEBUG is disabled due to the large quantity of output.

.. _conf-supybot.plugins.LogToIrc.networks:


supybot.plugins.LogToIrc.networks
  This config variable defaults to " ", is not network-specific, and is  not channel-specific.

  Determines what networks the bot should log to. If no networks are set, the bot will log on one network (whichever happens to be around at the time it feels like logging).

.. _conf-supybot.plugins.LogToIrc.notice:


supybot.plugins.LogToIrc.notice
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot's logs to IRC will be sent via NOTICE instead of PRIVMSG. Channels will always be PRIVMSGed, regardless of this variable; NOTICEs will only be used if this variable is True and the target is a nick, not a channel.

.. _conf-supybot.plugins.LogToIrc.public:


supybot.plugins.LogToIrc.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.LogToIrc.targets:


supybot.plugins.LogToIrc.targets
  This config variable defaults to " ", is network-specific, and is  not channel-specific.

  Determines which channels/nicks the bot should log to. If no channels/nicks are set, this plugin will effectively be turned off.

.. _conf-supybot.plugins.LogToIrc.userCapabilityRequired:


supybot.plugins.LogToIrc.userCapabilityRequired
  This config variable defaults to "owner", is not network-specific, and is  not channel-specific.

  Determines what capability is required for the bot to log to in private messages to the user. If this is empty, there will be no capability that's checked.

