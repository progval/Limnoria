.. _plugin-Later:

Documentation for the Later plugin for Supybot
==============================================

Purpose
-------
Informal notes, mostly for compatibility with other bots.  Based entirely on
nicks, it's an easy way to tell users who refuse to register notes when they
arrive later.

Usage
-----
Used to do things later; currently, it only allows the sending of
nick-based notes.  Do note (haha!) that these notes are *not* private
and don't even pretend to be; if you want such features, consider using the
Note plugin.

Use the ``later tell`` command to leave a message to a user.
If you sent the message by accident or want to cancel it,
you can use the `later undo` command to remove the latest later,
which you have sent.

You can also see the people who have notes waiting for them by using
the `later notes` command. If you specify a nickname in ``later notes``
command, you will see the notes, which are waiting for the nickname.

Privacy
-------

As you probably noticed from above, this plugin isn't private.
Everyone can see notes sent by anyone and the laters are sent on channel
by default and as the "plugin help later" says::

    Used to do things later; currently, it only allows the sending of nick-based notes. Do note (haha!) that these notes are *not* private and don't even pretend to be; if you want such features, consider using the Note plugin.

The Note plugin identifies people by username instead of nickname
and allows only users to send notes.
The only people who are able to read notes are the sender, receiver,
and the owner.

.. _commands-Later:

Commands
--------
.. _command-later-notes:

notes [<nick>]
  If <nick> is given, replies with what notes are waiting on <nick>, otherwise, replies with the nicks that have notes waiting for them.

.. _command-later-remove:

remove <nick>
  Removes the notes waiting on <nick>.

.. _command-later-tell:

tell <nick1[,nick2[,...]]> <text>
  Tells each <nickX> <text> the next time <nickX> is seen. <nickX> can contain wildcard characters, and the first matching nick will be given the note.

.. _command-later-undo:

undo <nick>
  Removes the latest note you sent to <nick>.

.. _conf-Later:

Configuration
-------------

.. _conf-supybot.plugins.Later.format:


supybot.plugins.Later.format
  This is a group of:

  .. _conf-supybot.plugins.Later.format.senderHostname:


  supybot.plugins.Later.format.senderHostname
    This config variable defaults to "False", is not network-specific, and is  not channel-specific.

    Determines whether senders' hostname will be shown in messages (instead of just the nick).

.. _conf-supybot.plugins.Later.maximum:


supybot.plugins.Later.maximum
  This config variable defaults to "0", is not network-specific, and is  not channel-specific.

  Determines the maximum number of messages to be queued for a user. If this value is 0, there is no maximum.

.. _conf-supybot.plugins.Later.messageExpiry:


supybot.plugins.Later.messageExpiry
  This config variable defaults to "30", is not network-specific, and is  not channel-specific.

  Determines the maximum number of days that a message will remain queued for a user. After this time elapses, the message will be deleted. If this value is 0, there is no maximum.

.. _conf-supybot.plugins.Later.private:


supybot.plugins.Later.private
  This config variable defaults to "False", is not network-specific, and is  not channel-specific.

  Determines whether users will be notified in the first place in which they're seen, or in private.

.. _conf-supybot.plugins.Later.public:


supybot.plugins.Later.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Later.tellOnJoin:


supybot.plugins.Later.tellOnJoin
  This config variable defaults to "False", is not network-specific, and is  not channel-specific.

  Determines whether users will be notified upon joining any channel the bot is in, or only upon sending a message.

