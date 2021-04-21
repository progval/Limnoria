.. _plugin-Seen:

Documentation for the Seen plugin for Supybot
=============================================

Purpose
-------
Keeps track of the last time a user was seen on a channel
and what they last said.
It also allows you to see what you missed since you parted the channel.

Usage
-----
This plugin allows you to see when and what someone last said and
what you missed since you left a channel.

.. _commands-Seen:

Commands
--------
.. _command-seen-any:

any [<channel>] [--user <name>] [<nick>]
  Returns the last time <nick> was seen and what <nick> was last seen doing. This includes any form of activity, instead of just PRIVMSGs. If <nick> isn't specified, returns the last activity seen in <channel>. If --user is specified, looks up name in the user database and returns the last time user was active in <channel>. <channel> is only necessary if the message isn't sent on the channel itself.

.. _command-seen-last:

last [<channel>]
  Returns the last thing said in <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-seen-seen:

seen [<channel>] <nick>
  Returns the last time <nick> was seen and what <nick> was last seen saying. <channel> is only necessary if the message isn't sent on the channel itself. <nick> may contain * as a wildcard.

.. _command-seen-since:

since [<channel>] [<nick>]
  Returns the messages since <nick> last left the channel. If <nick> is not given, it defaults to the nickname of the person calling the command.

.. _command-seen-user:

user [<channel>] <name>
  Returns the last time <name> was seen and what <name> was last seen saying. This looks up <name> in the user seen database, which means that it could be any nick recognized as user <name> that was seen. <channel> is only necessary if the message isn't sent in the channel itself.

.. _conf-Seen:

Configuration
-------------

.. _conf-supybot.plugins.Seen.minimumNonWildcard:


supybot.plugins.Seen.minimumNonWildcard
  This config variable defaults to "2", is network-specific, and is  channel-specific.

  The minimum non-wildcard characters required to perform a 'seen' request. Of course, it only applies if there is a wildcard in the request.

.. _conf-supybot.plugins.Seen.public:


supybot.plugins.Seen.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Seen.showLastMessage:


supybot.plugins.Seen.showLastMessage
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the last message will be displayed with @seen. Useful for keeping messages from a channel private.

