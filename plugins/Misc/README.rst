.. _plugin-Misc:

Documentation for the Misc plugin for Supybot
=============================================

Purpose
-------
Miscellaneous commands.

Usage
-----
Miscellaneous commands to access Supybot core. This is a core
Supybot plugin that should not be removed!

.. _commands-Misc:

Commands
--------
.. _command-misc-apropos:

apropos <string>
  Searches for <string> in the commands currently offered by the bot, returning a list of the commands containing that string.

.. _command-misc-clearmores:

clearmores takes no arguments
  Clears all mores for the current network.

.. _command-misc-completenick:

completenick [<channel>] <beginning> [--match-case]
  Returns the nick of someone on the channel whose nick begins with the given <beginning>. <channel> defaults to the current channel.

.. _command-misc-help:

help [<plugin>] [<command>]
  This command gives a useful description of what <command> does. <plugin> is only necessary if the command is in more than one plugin. You may also want to use the 'list' command to list all available plugins and commands.

.. _command-misc-last:

last [--{from,in,on,with,without,regexp} <value>] [--nolimit]
  Returns the last message matching the given criteria. --from requires a nick from whom the message came; --in requires a channel the message was sent to; --on requires a network the message was sent on; --with requires some string that had to be in the message; --regexp requires a regular expression the message must match; --nolimit returns all the messages that can be found. By default, the channel this command is given in is searched.

.. _command-misc-list:

list [--private] [--unloaded] [<plugin>]
  Lists the commands available in the given plugin. If no plugin is given, lists the public plugins available. If --private is given, lists the private plugins. If --unloaded is given, it will list available plugins that are not loaded.

.. _command-misc-more:

more [<nick>]
  If the last command was truncated due to IRC message length limitations, returns the next chunk of the result of the last command. If <nick> is given, it takes the continuation of the last command from <nick> instead of the person sending this message.

.. _command-misc-noticetell:

noticetell <nick> <text>
  Tells the <nick> whatever <text> is, in a notice. Use nested commands to your benefit here.

.. _command-misc-ping:

ping takes no arguments
  Checks to see if the bot is alive.

.. _command-misc-source:

source takes no arguments
  Returns a URL saying where to get Limnoria.

.. _command-misc-tell:

tell <nick> <text>
  Tells the <nick> whatever <text> is. Use nested commands to your benefit here.

.. _command-misc-version:

version takes no arguments
  Returns the version of the current bot.

.. _conf-Misc:

Configuration
-------------

.. _conf-supybot.plugins.Misc.customHelpString:


supybot.plugins.Misc.customHelpString
  This config variable defaults to "", is not network-specific, and is  not channel-specific.

  Sets a custom help string, displayed when the 'help' command is called without arguments.

.. _conf-supybot.plugins.Misc.last:


supybot.plugins.Misc.last
  This is a group of:

  .. _conf-supybot.plugins.Misc.last.nested:


  supybot.plugins.Misc.last.nested
    This is a group of:

    .. _conf-supybot.plugins.Misc.last.nested.includeNick:


    supybot.plugins.Misc.last.nested.includeNick
      This config variable defaults to "False", is network-specific, and is  channel-specific.

      Determines whether or not the nick will be included in the output of last when it is part of a nested command

    .. _conf-supybot.plugins.Misc.last.nested.includeTimestamp:


    supybot.plugins.Misc.last.nested.includeTimestamp
      This config variable defaults to "False", is network-specific, and is  channel-specific.

      Determines whether or not the timestamp will be included in the output of last when it is part of a nested command

.. _conf-supybot.plugins.Misc.listPrivatePlugins:


supybot.plugins.Misc.listPrivatePlugins
  This config variable defaults to "False", is not network-specific, and is  not channel-specific.

  Determines whether the bot will list private plugins with the list command if given the --private switch. If this is disabled, non-owner users should be unable to see what private plugins are loaded.

.. _conf-supybot.plugins.Misc.listUnloadedPlugins:


supybot.plugins.Misc.listUnloadedPlugins
  This config variable defaults to "False", is not network-specific, and is  not channel-specific.

  Determines whether the bot will list unloaded plugins with the list command if given the --unloaded switch. If this is disabled, non-owner users should be unable to see what unloaded plugins are available.

.. _conf-supybot.plugins.Misc.mores:


supybot.plugins.Misc.mores
  This config variable defaults to "1", is network-specific, and is  channel-specific.

  Determines how many messages the bot will issue when using the 'more' command.

.. _conf-supybot.plugins.Misc.public:


supybot.plugins.Misc.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Misc.timestampFormat:


supybot.plugins.Misc.timestampFormat
  This config variable defaults to "[%H:%M:%S]", is not network-specific, and is  not channel-specific.

  Determines the format string for timestamps in the Misc.last command. Refer to the Python documentation for the time module to see what formats are accepted. If you set this variable to the empty string, the timestamp will not be shown.

