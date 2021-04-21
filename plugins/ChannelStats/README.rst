.. _plugin-ChannelStats:

Documentation for the ChannelStats plugin for Supybot
=====================================================

Purpose
-------
Silently listens to every message received on a channel and keeps statistics
concerning joins, parts, and various other commands in addition to tracking
statistics about smileys, actions, characters, and words.

Usage
-----
This plugin keeps stats of the channel and returns them with
the command 'channelstats'.

.. _commands-ChannelStats:

Commands
--------
.. _command-channelstats-channelstats:

channelstats [<channel>]
  Returns the statistics for <channel>. <channel> is only necessary if the message isn't sent on the channel itself.

.. _command-channelstats-rank:

rank [<channel>] <stat expression>
  Returns the ranking of users according to the given stat expression. Valid variables in the stat expression include 'msgs', 'chars', 'words', 'smileys', 'frowns', 'actions', 'joins', 'parts', 'quits', 'kicks', 'kicked', 'topics', and 'modes'. Any simple mathematical expression involving those variables is permitted.

.. _command-channelstats-stats:

stats [<channel>] [<name>]
  Returns the statistics for <name> on <channel>. <channel> is only necessary if the message isn't sent on the channel itself. If <name> isn't given, it defaults to the user sending the command.

.. _conf-ChannelStats:

Configuration
-------------

.. _conf-supybot.plugins.ChannelStats.frowns:


supybot.plugins.ChannelStats.frowns
  This config variable defaults to ":| :-/ :-\\ :\\ :/ :( :-( :'(", is network-specific, and is  channel-specific.

  Determines what words (i.e., pieces of text with no spaces in them) are considered 'frowns' for the purposes of stats-keeping.

.. _conf-supybot.plugins.ChannelStats.public:


supybot.plugins.ChannelStats.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.ChannelStats.selfStats:


supybot.plugins.ChannelStats.selfStats
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will keep channel statistics on itself, possibly skewing the channel stats (especially in cases where the bot is relaying between channels on a network).

.. _conf-supybot.plugins.ChannelStats.smileys:


supybot.plugins.ChannelStats.smileys
  This config variable defaults to ":) ;) ;] :-) :-D :D :P :p (= =)", is network-specific, and is  channel-specific.

  Determines what words (i.e., pieces of text with no spaces in them) are considered 'smileys' for the purposes of stats-keeping.

