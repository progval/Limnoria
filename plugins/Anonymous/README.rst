.. _plugin-Anonymous:

Documentation for the Anonymous plugin for Supybot
==================================================

Purpose
-------
Allows folks to talk through the bot anonymously.

Usage
-----
This plugin allows users to act through the bot anonymously.  The 'do'
command has the bot perform an anonymous action in a given channel, and
the 'say' command allows other people to speak through the bot.  Since
this can be fairly well abused, you might want to set
supybot.plugins.Anonymous.requireCapability so only users with that
capability can use this plugin.  For extra security, you can require that
the user be *in* the channel they are trying to address anonymously with
supybot.plugins.Anonymous.requirePresenceInChannel, or you can require
that the user be registered by setting
supybot.plugins.Anonymous.requireRegistration.

Example: Proving that you are the owner
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you ask for cloak/vhost for your bot, the network operators will
often ask you to prove that you own the bot. You can do this for example
with the following method::

    @load Anonymous
    @config plugins.anonymous.requirecapability owner
    @config plugins.anonymous.allowprivatetarget True
    @anonymous say <operator nick> Hi, my owner is <your nick> :)

This
* Loads the plugin.
* Makes the plugin require that you are the owner

  * If anyone could send private messages as the bot, they could also
    access network services.

* Allows sending private messages
* Sends message ``Hi, my owner is <your nick> :)`` to ``operator nick``.

  * Note that you won't see the messages that are sent to the bot.

.. _commands-Anonymous:

Commands
--------
.. _command-anonymous-do:

do <channel> <action>
  Performs <action> in <channel>.

.. _command-anonymous-react:

react <channel> <reaction> <nick>
  Sends the <reaction> to <nick>'s last message. <reaction> is typically a smiley or an emoji. This may not be supported on the current network, as this command depends on IRCv3 features. This is also not supported if supybot.protocols.irc.experimentalExtensions disabled (don't enable it unless you know what you are doing).

.. _command-anonymous-say:

say <channel> <text>
  Sends <text> to <channel>.

.. _command-anonymous-tell:

tell <nick> <text>
  Sends <text> to <nick>. Can only be used if supybot.plugins.Anonymous.allowPrivateTarget is True.

.. _conf-Anonymous:

Configuration
-------------

.. _conf-supybot.plugins.Anonymous.allowPrivateTarget:


supybot.plugins.Anonymous.allowPrivateTarget
  This config variable defaults to "False", is not network-specific, and is  not channel-specific.

  Determines whether the bot will allow the "tell" command to be used. If true, the bot will allow the "tell" command to send private messages to other users.

.. _conf-supybot.plugins.Anonymous.public:


supybot.plugins.Anonymous.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Anonymous.requireCapability:


supybot.plugins.Anonymous.requireCapability
  This config variable defaults to "", is network-specific, and is  channel-specific.

  Determines what capability (if any) the bot should require people trying to use this plugin to have.

.. _conf-supybot.plugins.Anonymous.requirePresenceInChannel:


supybot.plugins.Anonymous.requirePresenceInChannel
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot should require people trying to use this plugin to be in the channel they wish to anonymously send to.

.. _conf-supybot.plugins.Anonymous.requireRegistration:


supybot.plugins.Anonymous.requireRegistration
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot should require people trying to use this plugin to be registered.

