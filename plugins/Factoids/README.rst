.. _plugin-Factoids:

Documentation for the Factoids plugin for Supybot
=================================================

Purpose
-------
Handles 'factoids,' little tidbits of information held in a database and
available on demand via several commands.

Usage
-----
Provides the ability to show Factoids.

.. _commands-Factoids:

Commands
--------
.. _command-factoids-alias:

alias [<channel>] <oldkey> <newkey> [<number>]
  Adds a new key <newkey> for factoid associated with <oldkey>. <number> is only necessary if there's more than one factoid associated with <oldkey>. The same action can be accomplished by using the 'learn' function with a new key but an existing (verbatim) factoid content.

.. _command-factoids-change:

change [<channel>] <key> <number> <regexp>
  Changes the factoid #<number> associated with <key> according to <regexp>.

.. _command-factoids-forget:

forget [<channel>] <key> [<number>|*]
  Removes a key-fact relationship for key <key> from the factoids database. If there is more than one such relationship for this key, a number is necessary to determine which one should be removed. A * can be used to remove all relationships for <key>. If as a result, the key (factoid) remains without any relationships to a factoid (key), it shall be removed from the database. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-factoids-info:

info [<channel>] <key>
  Gives information about the factoid(s) associated with <key>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-factoids-learn:

learn [<channel>] <key> is <value>
  Associates <key> with <value>. <channel> is only necessary if the message isn't sent on the channel itself. The word 'is' is necessary to separate the key from the value. It can be changed to another word via the learnSeparator registry value.

.. _command-factoids-lock:

lock [<channel>] <key>
  Locks the factoid(s) associated with <key> so that they cannot be removed or added to. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-factoids-random:

random [<channel>]
  Returns random factoids from the database for <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-factoids-rank:

rank [<channel>] [--plain] [--alpha] [<number>]
  Returns a list of top-ranked factoid keys, sorted by usage count (rank). If <number> is not provided, the default number of factoid keys returned is set by the rankListLength registry value. If --plain option is given, rank numbers and usage counts are not included in output. If --alpha option is given in addition to --plain, keys are sorted alphabetically, instead of by rank. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-factoids-search:

search [<channel>] [--values] [--regexp <value>] [--author <username>] [<glob> ...]
  Searches the keyspace for keys matching <glob>. If --regexp is given, its associated value is taken as a regexp and matched against the keys. If --values is given, search the value space instead of the keyspace.

.. _command-factoids-unlock:

unlock [<channel>] <key>
  Unlocks the factoid(s) associated with <key> so that they can be removed or added to. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-factoids-whatis:

whatis [<channel>] [--raw] <key> [<number>]
  Looks up the value of <key> in the factoid database. If given a number, will return only that exact factoid. If '--raw' option is given, no variable substitution will take place on the factoid. <channel> is only necessary if the message isn't sent in the channel itself.

.. _conf-Factoids:

Configuration
-------------

.. _conf-supybot.plugins.Factoids.format:


supybot.plugins.Factoids.format
  This config variable defaults to "$value", is network-specific, and is  channel-specific.

  Determines the format of the response given when a factoid's value is requested. All the standard substitutes apply, in addition to "$key" for the factoid's key and "$value" for the factoid's value.

.. _conf-supybot.plugins.Factoids.keepRankInfo:


supybot.plugins.Factoids.keepRankInfo
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether we keep updating the usage count for each factoid, for popularity ranking.

.. _conf-supybot.plugins.Factoids.learnSeparator:


supybot.plugins.Factoids.learnSeparator
  This config variable defaults to "is", is network-specific, and is  channel-specific.

  Determines what separator must be used in the learn command. Defaults to 'is' -- learn <key> is <value>. Users might want to change this to something else, so it's configurable.

.. _conf-supybot.plugins.Factoids.public:


supybot.plugins.Factoids.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Factoids.rankListLength:


supybot.plugins.Factoids.rankListLength
  This config variable defaults to "20", is network-specific, and is  channel-specific.

  Determines the number of factoid keys returned by the factrank command.

.. _conf-supybot.plugins.Factoids.replyApproximateSearchKeys:


supybot.plugins.Factoids.replyApproximateSearchKeys
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  If you try to look up a nonexistent factoid, this setting make the bot try to find some possible matching keys through several approximate matching algorithms and return a list of matching keys, before giving up.

.. _conf-supybot.plugins.Factoids.replyWhenInvalidCommand:


supybot.plugins.Factoids.replyWhenInvalidCommand
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will reply to invalid commands by searching for a factoid; basically making the whatis unnecessary when you want all factoids for a given key.

.. _conf-supybot.plugins.Factoids.requireVoice:


supybot.plugins.Factoids.requireVoice
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Only allows a user with voice or above on a channel to use the 'learn' and 'forget' commands.

.. _conf-supybot.plugins.Factoids.showFactoidIfOnlyOneMatch:


supybot.plugins.Factoids.showFactoidIfOnlyOneMatch
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will reply with the single matching factoid if only one factoid matches when using the search command.

.. _conf-supybot.plugins.Factoids.web:


supybot.plugins.Factoids.web
  This is a group of:

  .. _conf-supybot.plugins.Factoids.web.channel:


  supybot.plugins.Factoids.web.channel
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether factoids can be displayed via the web server.

  .. _conf-supybot.plugins.Factoids.web.enable:


  supybot.plugins.Factoids.web.enable
    This config variable defaults to "False", is not network-specific, and is  not channel-specific.

    Determines whether the Factoids plugins will be browsable on the HTTP server.

