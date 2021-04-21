.. _plugin-Plugin:

Documentation for the Plugin plugin for Supybot
===============================================

Purpose
-------
This plugin handles various plugin-related things, such as getting help for
a plugin or retrieving author info.

Usage
-----
This plugin exists to help users manage their plugins.  Use 'plugin
list' to list the loaded plugins; use 'plugin help' to get the description
of a plugin; use the 'plugin' command itself to determine what plugin a
command exists in.

.. _commands-Plugin:

Commands
--------
.. _command-plugin-author:

author <plugin>
  Returns the author of <plugin>. This is the person you should talk to if you have ideas, suggestions, or other comments about a given plugin.

.. _command-plugin-contributors:

contributors <plugin> [<name>]
  Replies with a list of people who made contributions to a given plugin. If <name> is specified, that person's specific contributions will be listed. You can specify a person's name by their full name or their nick, which is shown inside brackets if available.

.. _command-plugin-help:

help <plugin>
  Returns a useful description of how to use <plugin>, if the plugin has one.

.. _command-plugin-plugin:

plugin <command>
  Returns the name of the plugin that would be used to call <command>. If it is not uniquely determined, returns list of all plugins that contain <command>.

.. _command-plugin-plugins:

plugins <command>
  Returns the names of all plugins that contain <command>.

.. _conf-Plugin:

Configuration
-------------

.. _conf-supybot.plugins.Plugin.public:


supybot.plugins.Plugin.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

