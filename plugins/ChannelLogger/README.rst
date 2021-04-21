.. _plugin-ChannelLogger:

Documentation for the ChannelLogger plugin for Supybot
======================================================

Purpose
-------
Logs each channel to its own individual logfile.

Usage
-----
This plugin allows the bot to log channel conversations to disk.

.. _conf-ChannelLogger:

Configuration
-------------

.. _conf-supybot.plugins.ChannelLogger.directories:


supybot.plugins.ChannelLogger.directories
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether the bot will partition its channel logs into separate directories based on different criteria.

  .. _conf-supybot.plugins.ChannelLogger.directories.channel:


  supybot.plugins.ChannelLogger.directories.channel
    This config variable defaults to "True", is not network-specific, and is  not channel-specific.

    Determines whether the bot will use a channel directory if using directories.

  .. _conf-supybot.plugins.ChannelLogger.directories.network:


  supybot.plugins.ChannelLogger.directories.network
    This config variable defaults to "True", is not network-specific, and is  not channel-specific.

    Determines whether the bot will use a network directory if using directories.

  .. _conf-supybot.plugins.ChannelLogger.directories.timestamp:


  supybot.plugins.ChannelLogger.directories.timestamp
    This config variable defaults to "False", is not network-specific, and is  not channel-specific.

    Determines whether the bot will use a timestamp (determined by supybot.plugins.ChannelLogger.directories.timestamp.format) if using directories.

    .. _conf-supybot.plugins.ChannelLogger.directories.timestamp.format:


    supybot.plugins.ChannelLogger.directories.timestamp.format
      This config variable defaults to "%B", is not network-specific, and is  not channel-specific.

      Determines what timestamp format will be used in the directory structure for channel logs if supybot.plugins.ChannelLogger.directories.timestamp is True.

.. _conf-supybot.plugins.ChannelLogger.enable:


supybot.plugins.ChannelLogger.enable
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether logging is enabled.

.. _conf-supybot.plugins.ChannelLogger.filenameTimestamp:


supybot.plugins.ChannelLogger.filenameTimestamp
  This config variable defaults to "%Y-%m-%d", is network-specific, and is  channel-specific.

  Determines how to represent the timestamp used for the filename in rotated logs. When this timestamp changes, the old logfiles will be closed and a new one started. The format characters for the timestamp are in the time.strftime docs at python.org. In order for your logs to be rotated, you'll also have to enable supybot.plugins.ChannelLogger.rotateLogs.

.. _conf-supybot.plugins.ChannelLogger.flushImmediately:


supybot.plugins.ChannelLogger.flushImmediately
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether channel logfiles will be flushed anytime they're written to, rather than being buffered by the operating system.

.. _conf-supybot.plugins.ChannelLogger.noLogPrefix:


supybot.plugins.ChannelLogger.noLogPrefix
  This config variable defaults to "[nolog]", is network-specific, and is  channel-specific.

  Determines what string a message should be prefixed with in order not to be logged. If you don't want any such prefix, just set it to the empty string.

.. _conf-supybot.plugins.ChannelLogger.public:


supybot.plugins.ChannelLogger.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.ChannelLogger.rewriteRelayed:


supybot.plugins.ChannelLogger.rewriteRelayed
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will rewrite outgoing relayed messages (eg. from the Relay plugin) to use the original nick instead of the bot's nick.

.. _conf-supybot.plugins.ChannelLogger.rotateLogs:


supybot.plugins.ChannelLogger.rotateLogs
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will automatically rotate the logs for this channel. The bot will rotate logs when the timestamp for the log changes. The timestamp is set according to the 'filenameTimestamp' configuration variable.

.. _conf-supybot.plugins.ChannelLogger.showJoinParts:


supybot.plugins.ChannelLogger.showJoinParts
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines wether joins and parts are logged

.. _conf-supybot.plugins.ChannelLogger.stripFormatting:


supybot.plugins.ChannelLogger.stripFormatting
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether formatting characters (such as bolding, color, etc.) are removed when writing the logs to disk.

.. _conf-supybot.plugins.ChannelLogger.timestamp:


supybot.plugins.ChannelLogger.timestamp
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the logs for this channel are timestamped with the timestamp in supybot.log.timestampFormat.

