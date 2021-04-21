.. _plugin-MessageParser:

Documentation for the MessageParser plugin for Supybot
======================================================

Purpose
-------
The MessageParser plugin allows you to set custom regexp triggers,
which will trigger the bot to respond if they match anywhere in the message.
This is useful for those cases when you want a bot response even when the bot
was not explicitly addressed by name or prefix character.

An updated page of this plugin's documentation is located here:
https://sourceforge.net/p/gribble/wiki/MessageParser_Plugin/

Usage
-----
This plugin can set regexp triggers to activate the bot.
Use 'add' command to add regexp trigger, 'remove' to remove.

.. _commands-MessageParser:

Commands
--------
.. _command-messageparser-add:

add [<channel>|global] <regexp> <action>
  Associates <regexp> with <action>. <channel> is only necessary if the message isn't sent on the channel itself. Action is echoed upon regexp match, with variables $1, $2, etc. being interpolated from the regexp match groups.

.. _command-messageparser-info:

info [<channel>|global] [--id] <regexp>
  Display information about <regexp> in the triggers database. <channel> is only necessary if the message isn't sent in the channel itself. If option --id specified, will retrieve by regexp id, not content.

.. _command-messageparser-list:

list [<channel>|global]
  Lists regexps present in the triggers database. <channel> is only necessary if the message isn't sent in the channel itself. Regexp ID listed in parentheses.

.. _command-messageparser-lock:

lock [<channel>|global] <regexp>
  Locks the <regexp> so that it cannot be removed or overwritten to. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-messageparser-rank:

rank [<channel>|global]
  Returns a list of top-ranked regexps, sorted by usage count (rank). The number of regexps returned is set by the rankListLength registry value. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-messageparser-remove:

remove [<channel>|global] [--id] <regexp>]
  Removes the trigger for <regexp> from the triggers database. <channel> is only necessary if the message isn't sent in the channel itself. If option --id specified, will retrieve by regexp id, not content.

.. _command-messageparser-show:

show [<channel>|global] [--id] <regexp>
  Looks up the value of <regexp> in the triggers database. <channel> is only necessary if the message isn't sent in the channel itself. If option --id specified, will retrieve by regexp id, not content.

.. _command-messageparser-unlock:

unlock [<channel>|global] <regexp>
  Unlocks the entry associated with <regexp> so that it can be removed or overwritten. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-messageparser-vacuum:

vacuum [<channel>|global]
  Vacuums the database for <channel>. See SQLite vacuum doc here: http://www.sqlite.org/lang_vacuum.html <channel> is only necessary if the message isn't sent in the channel itself. First check if user has the required capability specified in plugin config requireVacuumCapability.

.. _conf-MessageParser:

Configuration
-------------

.. _conf-supybot.plugins.MessageParser.enable:


supybot.plugins.MessageParser.enable
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the message parser is enabled. If enabled, will trigger on regexps added to the regexp db.

.. _conf-supybot.plugins.MessageParser.enableForNotices:


supybot.plugins.MessageParser.enableForNotices
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the message parser is enabled for NOTICE messages too.

.. _conf-supybot.plugins.MessageParser.keepRankInfo:


supybot.plugins.MessageParser.keepRankInfo
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether we keep updating the usage count for each regexp, for popularity ranking.

.. _conf-supybot.plugins.MessageParser.listSeparator:


supybot.plugins.MessageParser.listSeparator
  This config variable defaults to ", ", is network-specific, and is  channel-specific.

  Determines the separator used between regexps when shown by the list command.

.. _conf-supybot.plugins.MessageParser.maxTriggers:


supybot.plugins.MessageParser.maxTriggers
  This config variable defaults to "0", is network-specific, and is  channel-specific.

  Determines the maximum number of triggers in one message. Set this to 0 to allow an infinite number of triggers.

.. _conf-supybot.plugins.MessageParser.public:


supybot.plugins.MessageParser.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.MessageParser.rankListLength:


supybot.plugins.MessageParser.rankListLength
  This config variable defaults to "20", is network-specific, and is  channel-specific.

  Determines the number of regexps returned by the triggerrank command.

.. _conf-supybot.plugins.MessageParser.requireManageCapability:


supybot.plugins.MessageParser.requireManageCapability
  This config variable defaults to "admin; channel,op", is network-specific, and is  channel-specific.

  Determines the capabilities required (if any) to manage the regexp database, including add, remove, lock, unlock. Use 'channel,capab' for channel-level capabilities. Note that absence of an explicit anticapability means user has capability.

.. _conf-supybot.plugins.MessageParser.requireVacuumCapability:


supybot.plugins.MessageParser.requireVacuumCapability
  This config variable defaults to "admin", is network-specific, and is  channel-specific.

  Determines the capability required (if any) to vacuum the database.

