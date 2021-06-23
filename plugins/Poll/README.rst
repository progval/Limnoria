.. _plugin-Poll:

Documentation for the Poll plugin for Supybot
=============================================

Purpose
-------
Poll: Provides a simple way to vote on answers to a question

Usage
-----
Provides a simple way to vote on answers to a question

For example, this creates a poll::

   <admin> @poll add "Is this a test?" "Yes" "No" "Maybe"
   <bot> The operation succeeded.  Poll # 42 created.

Creates a poll that can be voted on in this way::

   <citizen1> @vote 42 Yes
   <citizen2> @vote 42 No
   <citizen3> @vote 42 No

And results::

    <admin> @poll results
    <bot> 2 votes for No, 1 vote for Yes, and 0 votes for Maybe

Longer answers are possible, and voters only need to use the first
word of each answer to vote. For example, this creates a poll that
can be voted on in the same way::

   <admin> @poll add "Is this a test?" "Yes totally" "No no no" "Maybe"
   <bot> The operation succeeded.  Poll # 43 created.

You can also add a number or letter at the beginning of each question to
make it easier::

   <admin> @poll add "Who is the best captain?" "1 James T Kirk" "2 Jean-Luc Picard" "3 Benjamin Sisko" "4 Kathryn Janeway"
   <bot> The operation succeeded.  Poll # 44 created.

   <trekkie1> @vote 42 1
   <trekkie2> @vote 42 4
   <trekkie3> @vote 42 4

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

