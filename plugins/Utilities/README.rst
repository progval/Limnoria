.. _plugin-Utilities:

Documentation for the Utilities plugin for Supybot
==================================================

Purpose
-------
Various utility commands, mostly useful for manipulating nested commands.

Usage
-----
Provides useful commands for bot scripting / command nesting.

.. _commands-Utilities:

Commands
--------
.. _command-utilities-apply:

apply <command> <text>
  Tokenizes <text> and calls <command> with the resulting arguments.

.. _command-utilities-countargs:

countargs <arg> [<arg> ...]
  Counts the arguments given.

.. _command-utilities-echo:

echo <text>
  Returns the arguments given it. Uses our standard substitute on the string(s) given to it; $nick (or $who), $randomNick, $randomInt, $botnick, $channel, $user, $host, $today, $now, and $randomDate are all handled appropriately.

.. _command-utilities-ignore:

ignore requires no arguments
  Does nothing. Useful sometimes for sequencing commands when you don't care about their non-error return values.

.. _command-utilities-last:

last <text> [<text> ...]
  Returns the last argument given. Useful when you'd like multiple nested commands to run, but only the output of the last one to be returned.

.. _command-utilities-let:

let <variable> = <value> in <command>
  Defines <variable> to be equal to <value> in the <command> and runs the <command>. '=' and 'in' can be omitted.

.. _command-utilities-sample:

sample <num> <arg> [<arg> ...]
  Randomly chooses <num> items out of the arguments given.

.. _command-utilities-shuffle:

shuffle <arg> [<arg> ...]
  Shuffles the arguments given.

.. _command-utilities-sort:

sort <arg> [<arg> ...]
  Sorts the arguments given.

.. _command-utilities-success:

success [<text>]
  Does nothing except to reply with a success message. This is useful when you want to run multiple commands as nested commands, and don't care about their output as long as they're successful. An error, of course, will break out of this command. <text>, if given, will be appended to the end of the success message.

.. _conf-Utilities:

Configuration
-------------

.. _conf-supybot.plugins.Utilities.public:


supybot.plugins.Utilities.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

