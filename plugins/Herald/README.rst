.. _plugin-Herald:

Documentation for the Herald plugin for Supybot
===============================================

Purpose
-------
Greets users who join the channel with a recognized hostmask with a nice
little greeting.

Usage
-----
This plugin allows you to set welcome messages (heralds) to people who
are recognized by the bot when they join a channel.

.. _commands-Herald:

Commands
--------
.. _command-Herald-add:

add [<channel>] <user|nick> <msg>
  Sets the herald message for <user> (or the user <nick|hostmask> is currently identified or recognized as) to <msg>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Herald-change:

change [<channel>] [<user|nick>] <regexp>
  Changes the herald message for <user>, or the user <nick|hostmask> is currently identified or recognized as, according to <regexp>. If <user> is not given, defaults to the calling user. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Herald-default:

default [<channel>] [--remove|<msg>]
  If <msg> is given, sets the default herald to <msg>. A <msg> of "" will remove the default herald. If <msg> is not given, returns the current default herald. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Herald-get:

get [<channel>] [<user|nick>]
  Returns the current herald message for <user> (or the user <nick|hostmask> is currently identified or recognized as). If <user> is not given, defaults to the user giving the command. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Herald-remove:

remove [<channel>] [<user|nick>]
  Removes the herald message set for <user>, or the user <nick|hostmask> is currently identified or recognized as. If <user> is not given, defaults to the user giving the command. <channel> is only necessary if the message isn't sent in the channel itself.

Configuration
-------------
supybot.plugins.Herald.default
  This config variable defaults to "", is network-specific, and is  channel-specific.

  Sets the default herald to use. If a user has a personal herald specified, that will be used instead. If set to the empty string, the default herald will be disabled.

  supybot.plugins.Herald.default.notice
    This config variable defaults to "True", is network-specific, and is  channel-specific.

    Determines whether the default herald will be sent as a NOTICE instead of a PRIVMSG.

  supybot.plugins.Herald.default.public
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether the default herald will be sent publicly.

supybot.plugins.Herald.heralding
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether messages will be sent to the channel when a recognized user joins; basically enables or disables the plugin.

supybot.plugins.Herald.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

supybot.plugins.Herald.requireCapability
  This config variable defaults to "", is not network-specific, and is  not channel-specific.

  Determines what capability (if any) is required to add/change/remove the herald of another user.

supybot.plugins.Herald.throttle
  This config variable defaults to "600", is network-specific, and is  channel-specific.

  Determines the minimum number of seconds between heralds.

  supybot.plugins.Herald.throttle.afterPart
    This config variable defaults to "0", is network-specific, and is  channel-specific.

    Determines the minimum number of seconds after parting that the bot will not herald the person when they rejoin.

  supybot.plugins.Herald.throttle.afterSplit
    This config variable defaults to "60", is network-specific, and is  channel-specific.

    Determines the minimum number of seconds after a netsplit that the bot will not herald the users that split.

