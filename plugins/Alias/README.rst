.. _plugin-Alias:

Documentation for the Alias plugin for Supybot
==============================================

Purpose
-------
Allows aliases for other commands. NOTE THAT IT'S RECOMMENDED TO USE Aka
PLUGIN INSTEAD!

Usage
-----
This plugin allows users to define aliases to commands and combinations
of commands (via nesting).
This plugin is only kept for backward compatibility, you should use the
built-in Aka plugin instead (you can migrate your existing aliases using
the 'importaliasdatabase' command.

To add an alias, `trout`, which expects a word as an argument::

    <jamessan> @alias add trout "action slaps $1 with a large trout"
    <bot> jamessan: The operation succeeded.
    <jamessan> @trout me
    * bot slaps me with a large trout

To add an alias, `lastfm`, which expects a last.fm user and replies with
their recently played items::

    @alias add lastfm "rss [format concat http://ws.audioscrobbler.com/1.0/user/ [format concat [urlquote $1] /recenttracks.rss]]"

Note that if the nested commands being aliased hadn't been quoted, then
those commands would have been run immediately, and `@lastfm` would always
reply with the same information, the result of those commands.

.. _commands-Alias:

Commands
--------
.. _command-alias-add:

add <name> <command>
  Defines an alias <name> that executes <command>. The <command> should be in the standard "command argument [nestedcommand argument]" arguments to the alias; they'll be filled with the first, second, etc. arguments. $1, $2, etc. can be used for required arguments. @1, @2, etc. can be used for optional arguments. $* simply means "all remaining arguments," and cannot be combined with optional arguments.

.. _command-alias-list:

list [--locked|--unlocked]
  Lists alias names of a particular type, defaults to all aliases if no --locked or --unlocked option is given.

.. _command-alias-lock:

lock <alias>
  Locks an alias so that no one else can change it.

.. _command-alias-remove:

remove <name>
  Removes the given alias, if unlocked.

.. _command-alias-unlock:

unlock <alias>
  Unlocks an alias so that people can define new aliases over it.

.. _conf-Alias:

Configuration
-------------

.. _conf-supybot.plugins.Alias.aliases:


supybot.plugins.Alias.aliases
  This is a group of:

.. _conf-supybot.plugins.Alias.escapedaliases:


supybot.plugins.Alias.escapedaliases
  This is a group of:

.. _conf-supybot.plugins.Alias.public:


supybot.plugins.Alias.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Alias.validName:


supybot.plugins.Alias.validName
  This config variable defaults to "^[^\\x00-\\x20]+$", is not network-specific, and is  not channel-specific.

  Regex which alias names must match in order to be valid

