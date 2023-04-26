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

To add an alias, ``trout``, which expects a word as an argument::

    <jamessan> @alias add trout "action slaps $1 with a large trout"
    <bot> jamessan: The operation succeeded.
    <jamessan> @trout me
    * bot slaps me with a large trout

Add an alias, ``randpercent``, which returns a random percentage value::

    @alias add randpercent "squish [dice 1d100]%"

This requires the ``Filter`` and ``Games`` plugins to be loaded.

Note that nested commands in an alias should be quoted, or they will only
run once when you create the alias, and not each time the alias is
called. (In this case, not quoting the nested command would mean that
``@randpercent`` always responds with the same value!)

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
  This config variable defaults to "True", is not network-specific, and is not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Alias.validName:


supybot.plugins.Alias.validName
  This config variable defaults to "^[^\\x00-\\x20]+$", is not network-specific, and is not channel-specific.

  Regex which alias names must match in order to be valid

