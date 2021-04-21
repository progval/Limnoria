.. _plugin-Note:

Documentation for the Note plugin for Supybot
=============================================

Purpose
-------
A complete messaging system that allows users to leave 'notes' for other
users that can be retrieved later.

Usage
-----
Allows you to send notes to other users.

.. _commands-Note:

Commands
--------
.. _command-note-list:

list [--{old,sent}] [--{from,to} <user>]
  Retrieves the ids of all your unread notes. If --old is given, list read notes. If --sent is given, list notes that you have sent. If --from is specified, only lists notes sent to you from <user>. If --to is specified, only lists notes sent by you to <user>.

.. _command-note-next:

next takes no arguments
  Retrieves your next unread note, if any.

.. _command-note-note:

note <id>
  Retrieves a single note by its unique note id. Use the 'note list' command to see what unread notes you have.

.. _command-note-reply:

reply <id> <text>
  Sends a note in reply to <id>.

.. _command-note-search:

search [--{regexp} <value>] [--sent] [<glob>]
  Searches your received notes for ones matching <glob>. If --regexp is given, its associated value is taken as a regexp and matched against the notes. If --sent is specified, only search sent notes.

.. _command-note-send:

send <recipient>,[<recipient>,[...]] <text>
  Sends a new note to the user specified. Multiple recipients may be specified by separating their names by commas.

.. _command-note-unsend:

unsend <id>
  Unsends the note with the id given. You must be the author of the note, and it must be unread.

.. _conf-Note:

Configuration
-------------

.. _conf-supybot.plugins.Note.notify:


supybot.plugins.Note.notify
  This is a group of:

  .. _conf-supybot.plugins.Note.notify.autoSend:


  supybot.plugins.Note.notify.autoSend
    This config variable defaults to "0", is not network-specific, and is  not channel-specific.

    Determines the upper limit for automatically sending messages instead of notifications. I.e., if this value is 2 and there are 2 new messages to notify a user about, instead of sending a notification message, the bot will simply send those new messages. If there are 3 new messages, however, the bot will send a notification message.

  .. _conf-supybot.plugins.Note.notify.onJoin:


  supybot.plugins.Note.notify.onJoin
    This config variable defaults to "False", is not network-specific, and is  not channel-specific.

    Determines whether the bot will notify people of their new messages when they join the channel. Normally it will notify them when they send a message to the channel, since oftentimes joins are the result of netsplits and not the actual presence of the user.

    .. _conf-supybot.plugins.Note.notify.onJoin.repeatedly:


    supybot.plugins.Note.notify.onJoin.repeatedly
      This config variable defaults to "False", is not network-specific, and is  not channel-specific.

      Determines whether the bot will repeatedly notify people of their new messages when they join the channel. That means when they join the channel, the bot will tell them they have unread messages, even if it's told them before.

.. _conf-supybot.plugins.Note.public:


supybot.plugins.Note.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

