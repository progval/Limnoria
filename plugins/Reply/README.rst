.. _plugin-Reply:

Documentation for the Reply plugin for Supybot
==============================================

Purpose
-------
This plugin contains various commands which elicit certain types of responses
from the bot.

Usage
-----
This plugin contains a few commands that construct various types of
replies.  Some bot owners would be wise to not load this plugin because it
can be easily abused.

.. _commands-Reply:

Commands
--------
.. _command-Reply-action:

action <text>
  Replies with <text> as an action. Use nested commands to your benefit here.

.. _command-Reply-notice:

notice <text>
  Replies with <text> in a notice. Use nested commands to your benefit here. If you want a private notice, nest the private command.

.. _command-Reply-private:

private <text>
  Replies with <text> in private. Use nested commands to your benefit here.

.. _command-Reply-replies:

replies <str> [<str> ...]
  Replies with each of its arguments <str> in separate replies, depending the configuration of supybot.reply.oneToOne.

.. _command-Reply-reply:

reply <text>
  Replies with <text>. Equivalent to the alias, 'echo $nick: $1'.

Configuration
-------------
supybot.plugins.Reply.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

