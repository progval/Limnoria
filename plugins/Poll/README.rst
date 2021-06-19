.. _plugin-Poll:

Documentation for the Poll plugin for Supybot
=============================================

Purpose
-------
Poll: Provides a simple way to vote on answers to a question

Usage
-----
Provides a simple way to vote on answers to a question

.. _commands-Poll:

Commands
--------
.. _command-poll-add:

add [<channel>] <question> <answer1> [<answer2> [<answer3> [...]]]
  Creates a new poll with the specified <question> and answers on the <channel>. The first word of each answer is used as its id to vote, so each answer should start with a different word. <channel> is only necessary if this command is run in private, and defaults to the current channel otherwise.

.. _command-poll-close:

close [<channel>] <poll_id>
  Closes the specified poll.

.. _command-poll-results:

results [<channel>] <poll_id>
  Returns the results of the specified poll.

.. _command-poll-vote:

vote [<channel>] <poll_id> <answer_id>
  Registers your vote on the poll <poll_id> as being the answer identified by <answer_id> (which is the first word of each possible answer).

.. _conf-Poll:

Configuration
-------------

.. _conf-supybot.plugins.Poll.public:


supybot.plugins.Poll.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Poll.requireManageCapability:


supybot.plugins.Poll.requireManageCapability
  This config variable defaults to "channel,op; channel,halfop", is network-specific, and is  channel-specific.

  Determines the capabilities required (if any) to open and close polls. Use 'channel,capab' for channel-level capabilities. Note that absence of an explicit anticapability means user has capability.

