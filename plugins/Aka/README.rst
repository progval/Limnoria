.. _plugin-Aka:

Documentation for the Aka plugin for Supybot
============================================

Purpose
-------
This plugin allows the user to create various aliases (known as "Akas", since
Alias is the name of another plugin Aka is based on) to other commands or
combinations of other commands (via nested commands).

Usage
-----
This plugin allows users to define aliases to commands and combinations
of commands (via nesting).

Importing from Alias
^^^^^^^^^^^^^^^^^^^^

Add an aka, Alias, which eases the transitioning to Aka from Alias.

First we will load Alias and Aka::

    <jamessan> @load Alias
    <bot> jamessan: The operation succeeded.
    <jamessan> @load Aka
    <bot> jamessan: The operation succeeded.

Then we import the Alias database to Aka in case it exists and unload
Alias::

    <jamessan> @importaliasdatabase
    <bot> jamessan: The operation succeeded.
    <jamessan> @unload Alias
    <bot> jamessan: The operation succeeded.

And now we will finally add the Aka ``alias`` itself::

    <jamessan> @aka add "alias" "aka $1 $*"
    <bot> jamessan: The operation succeeded.

Now you can use Aka as you used Alias before.

Trout
^^^^^

Add an aka, trout, which expects a word as an argument::

    <jamessan> @aka add trout "reply action slaps $1 with a large trout"
    <bot> jamessan: The operation succeeded.
    <jamessan> @trout me
    * bot slaps me with a large trout

This ``trout`` aka requires the plugin ``Reply`` to be loaded since it
provides the ``action`` command.

LastFM
^^^^^^

Add an aka, ``lastfm``, which expects a last.fm username and replies with
their most recently played item::

    @aka add lastfm "rss [format concat http://ws.audioscrobbler.com/1.0/user/ [format concat [web urlquote $1] /recenttracks.rss]]"

This ``lastfm`` aka requires the following plugins to be loaded: ``RSS``,
``Format`` and ``Web``.

``RSS`` provides ``rss``, ``Format`` provides ``concat`` and ``Web`` provides
``urlquote``.

Note that if the nested commands being aliased hadn't been quoted, then
those commands would have been run immediately, and ``@lastfm`` would always
reply with the same information, the result of those commands.

.. _commands-Aka:

Commands
--------
.. _command-aka-add:

add [--channel <#channel>] <name> <command>
  Defines an alias <name> that executes <command>. The <command> should be in the standard "command argument [nestedcommand argument]" arguments to the alias; they'll be filled with the first, second, etc. arguments. $1, $2, etc. can be used for required arguments. @1, @2, etc. can be used for optional arguments. $* simply means "all arguments that have not replaced $1, $2, etc.", ie. it will also include optional arguments.

.. _command-aka-remove:

remove [--channel <#channel>] <name>
  Removes the given alias, if unlocked.

.. _command-aka-lock:

lock [--channel <#channel>] <alias>
  Locks an alias so that no one else can change it.

.. _command-aka-unlock:

unlock [--channel <#channel>] <alias>
  Unlocks an alias so that people can define new aliases over it.

.. _command-aka-importaliasdatabase:

importaliasdatabase takes no arguments
  Imports the Alias database into Aka's, and clean the former.

.. _command-aka-show:

show [--channel <#channel>] <alias>
  This command shows the content of an Aka.

.. _command-aka-list:

list [--channel <#channel>] [--keys] [--unlocked|--locked]
  Lists all Akas defined for <channel>. If <channel> is not specified, lists all global Akas. If --keys is given, lists only the Aka names and not their commands.

.. _command-aka-set:

set [--channel <#channel>] <name> <command>
  Overwrites an existing alias <name> to execute <command> instead. The <command> should be in the standard "command argument [nestedcommand argument]" arguments to the alias; they'll be filled with the first, second, etc. arguments. $1, $2, etc. can be used for required arguments. @1, @2, etc. can be used for optional arguments. $* simply means "all arguments that have not replaced $1, $2, etc.", ie. it will also include optional arguments.

.. _command-aka-search:

search [--channel <#channel>] <query>
  Searches Akas defined for <channel>. If <channel> is not specified, searches all global Akas.

.. _conf-Aka:

Configuration
-------------

.. _conf-supybot.plugins.Aka.maximumWordsInName:


supybot.plugins.Aka.maximumWordsInName
  This config variable defaults to "5", is not network-specific, and is  not channel-specific.

  The maximum number of words allowed in a command name. Setting this to an high value may slow down your bot on long commands.

.. _conf-supybot.plugins.Aka.public:


supybot.plugins.Aka.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Aka.web:


supybot.plugins.Aka.web
  This is a group of:

  .. _conf-supybot.plugins.Aka.web.enable:


  supybot.plugins.Aka.web.enable
    This config variable defaults to "False", is not network-specific, and is  not channel-specific.

    Determines whether the Akas will be browsable through the HTTP server.

