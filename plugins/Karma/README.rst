.. _plugin-Karma:

Documentation for the Karma plugin for Supybot
==============================================

Purpose
-------
Plugin for keeping track of Karma for users and things in a channel.

Usage
-----
Provides a simple tracker for setting Karma (thing++, thing--).
If ``config plugins.karma.allowUnaddressedKarma`` is set to ``True``
(default since 2014.05.07), saying `boats++` will give 1 karma
to ``boats``, and ``ships--`` will subtract 1 karma from ``ships``.

However, if you use this in a sentence, like
``That deserves a ++. Kevin++``, 1 karma will be added to
``That deserves a ++. Kevin``, so you should only add or subtract karma
in a line that doesn't have anything else in it.
Alternatively, you can restrict karma tracking to nicks in the current
channel by setting `config plugins.Karma.onlyNicks` to ``True``.

If ``config plugins.karma.allowUnaddressedKarma` is set to `False``,
you must address the bot with nick or prefix to add or subtract karma.

.. _commands-Karma:

Commands
--------
.. _command-Karma-clear:

clear [<channel>] [<name>]
  Resets the karma of <name> to 0. If <name> is not given, resets everything.

.. _command-Karma-dump:

dump [<channel>] <filename>
  Dumps the Karma database for <channel> to <filename> in the bot's data directory. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Karma-karma:

karma [<channel>] [<thing> ...]
  Returns the karma of <thing>. If <thing> is not given, returns the top N karmas, where N is determined by the config variable supybot.plugins.Karma.rankingDisplay. If one <thing> is given, returns the details of its karma; if more than one <thing> is given, returns the total karma of each of the things. <channel> is only necessary if the message isn't sent on the channel itself.

.. _command-Karma-load:

load [<channel>] <filename>
  Loads the Karma database for <channel> from <filename> in the bot's data directory. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Karma-most:

most [<channel>] {increased,decreased,active}
  Returns the most increased, the most decreased, or the most active (the sum of increased and decreased) karma things. <channel> is only necessary if the message isn't sent in the channel itself.

Configuration
-------------
supybot.plugins.Karma.allowSelfRating
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether users can adjust the karma of their nick.

supybot.plugins.Karma.allowUnaddressedKarma
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will increase/decrease karma without being addressed.

supybot.plugins.Karma.decrementChars
  This config variable defaults to "--", is network-specific, and is  channel-specific.

  A space separated list of characters to decrease karma.

supybot.plugins.Karma.incrementChars
  This config variable defaults to "++", is network-specific, and is  channel-specific.

  A space separated list of characters to increase karma.

supybot.plugins.Karma.mostDisplay
  This config variable defaults to "25", is network-specific, and is  channel-specific.

  Determines how many karma things are shown when the most command is called.

supybot.plugins.Karma.onlyNicks
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will only increase/decrease karma for nicks in the current channel.

supybot.plugins.Karma.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

supybot.plugins.Karma.rankingDisplay
  This config variable defaults to "3", is network-specific, and is  channel-specific.

  Determines how many highest/lowest karma things are shown when karma is called with no arguments.

supybot.plugins.Karma.response
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will reply with a success message when something's karma is increased or decreased.

supybot.plugins.Karma.simpleOutput
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will output shorter versions of the karma output when requesting a single thing's karma.

