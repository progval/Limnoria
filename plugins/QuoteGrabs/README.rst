.. _plugin-QuoteGrabs:

Documentation for the QuoteGrabs plugin for Supybot
===================================================

Purpose
-------
Quotegrabs are like IRC sound bites.  When someone says something funny,
incriminating, stupid, outrageous, ... anything that might be worth
remembering, you can grab that quote for that person.  With this plugin, you
can store many quotes per person and display their most recent quote, as well
as see who "grabbed" the quote in the first place.

Usage
-----
Stores and displays quotes from channels. Quotes are stored randomly
and/or on user request.

.. _commands-QuoteGrabs:

Commands
--------
.. _command-quotegrabs-get:

get [<channel>] <id>
  Return the quotegrab with the given <id>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quotegrabs-grab:

grab [<channel>] <nick>
  Grabs a quote from <channel> by <nick> for the quotegrabs table. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quotegrabs-list:

list [<channel>] <nick>
  Returns a list of shortened quotes that have been grabbed for <nick> as well as the id of each quote. These ids can be used to get the full quote. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quotegrabs-quote:

quote [<channel>] <nick>
  Returns <nick>'s latest quote grab in <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quotegrabs-random:

random [<channel>] [<nick>]
  Returns a randomly grabbed quote, optionally choosing only from those quotes grabbed for <nick>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quotegrabs-say:

say [<channel>] <id>
  Return the quotegrab with the given <id>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quotegrabs-search:

search [<channel>] <text>
  Searches for <text> in a quote. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-quotegrabs-ungrab:

ungrab [<channel>] <number>
  Removes the grab <number> (the last by default) on <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _conf-QuoteGrabs:

Configuration
-------------

.. _conf-supybot.plugins.QuoteGrabs.public:


supybot.plugins.QuoteGrabs.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.QuoteGrabs.randomGrabber:


supybot.plugins.QuoteGrabs.randomGrabber
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will randomly grab possibly-suitable quotes on occasion. The suitability of a given message is determined by ...

  .. _conf-supybot.plugins.QuoteGrabs.randomGrabber.averageTimeBetweenGrabs:


  supybot.plugins.QuoteGrabs.randomGrabber.averageTimeBetweenGrabs
    This config variable defaults to "864000", is network-specific, and is  channel-specific.

    Determines about how many seconds, on average, should elapse between random grabs. This is only an average value; grabs can happen from any time after half this time until never, although that's unlikely to occur.

  .. _conf-supybot.plugins.QuoteGrabs.randomGrabber.minimumCharacters:


  supybot.plugins.QuoteGrabs.randomGrabber.minimumCharacters
    This config variable defaults to "8", is network-specific, and is  channel-specific.

    Determines the minimum number of characters in a message for it to be considered for random grabbing.

  .. _conf-supybot.plugins.QuoteGrabs.randomGrabber.minimumWords:


  supybot.plugins.QuoteGrabs.randomGrabber.minimumWords
    This config variable defaults to "3", is network-specific, and is  channel-specific.

    Determines the minimum number of words in a message for it to be considered for random grabbing.

