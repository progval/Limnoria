.. _plugin-MoobotFactoids:

Documentation for the MoobotFactoids plugin for Supybot
=======================================================

Purpose
-------
Moobot factoid compatibility module.  Moobot's factoids were originally
designed to emulate Blootbot's factoids, so in either case, you should find
this plugin comfortable.

Usage
-----
An alternative to the Factoids plugin, this plugin keeps factoids in
your bot.

To add factoid say
``@something is something`` And when you call ``@something`` the bot says
``something is something``.

If you want factoid to be in different format say (for example):
``@Hi is <reply> Hello`` And when you call ``@hi`` the bot says ``Hello.``

If you want the bot to use /mes with Factoids, that is possible too.
``@test is <action> tests.`` and everytime when someone calls for
``test`` the bot answers ``* bot tests.``

.. _commands-MoobotFactoids:

Commands
--------
.. _command-moobotfactoids-factinfo:

factinfo [<channel>] <factoid key>
  Returns the various bits of info on the factoid for the given key. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-moobotfactoids-listauth:

listauth [<channel>] <author name>
  Lists the keys of the factoids with the given author. Note that if an author has an integer name, you'll have to use that author's id to use this function (so don't use integer usernames!). <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-moobotfactoids-listkeys:

listkeys [<channel>] <text>
  Lists the keys of the factoids whose key contains the provided text. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-moobotfactoids-listvalues:

listvalues [<channel>] <text>
  Lists the keys of the factoids whose value contains the provided text. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-moobotfactoids-literal:

literal [<channel>] <factoid key>
  Returns the literal factoid for the given factoid key. No parsing of the factoid value is done as it is with normal retrieval. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-moobotfactoids-lock:

lock [<channel>] <factoid key>
  Locks the factoid with the given factoid key. Requires that the user be registered and have created the factoid originally. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-moobotfactoids-most:

most [<channel>] {popular|authored|recent}
  Lists the most {popular|authored|recent} factoids. "popular" lists the most frequently requested factoids. "authored" lists the author with the most factoids. "recent" lists the most recently created factoids. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-moobotfactoids-random:

random [<channel>]
  Displays a random factoid (along with its key) from the database. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-moobotfactoids-remove:

remove [<channel>] <factoid key>
  Deletes the factoid with the given key. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-moobotfactoids-unlock:

unlock [<channel>] <factoid key>
  Unlocks the factoid with the given factoid key. Requires that the user be registered and have locked the factoid. <channel> is only necessary if the message isn't sent in the channel itself.

.. _conf-MoobotFactoids:

Configuration
-------------

.. _conf-supybot.plugins.MoobotFactoids.mostCount:


supybot.plugins.MoobotFactoids.mostCount
  This config variable defaults to "10", is network-specific, and is  channel-specific.

  Determines how many items are shown when the 'most' command is called.

.. _conf-supybot.plugins.MoobotFactoids.public:


supybot.plugins.MoobotFactoids.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.MoobotFactoids.showFactoidIfOnlyOneMatch:


supybot.plugins.MoobotFactoids.showFactoidIfOnlyOneMatch
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether or not the factoid value will be shown when a listkeys search returns only one factoid key.

