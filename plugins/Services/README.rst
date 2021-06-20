.. _plugin-Services:

Documentation for the Services plugin for Supybot
=================================================

Purpose
-------
Services: Handles management of nicks with NickServ, and ops with ChanServ;
to (re)gain access to its own nick and channels.

Usage
-----
This plugin handles dealing with Services on networks that provide them.
Basically, you should use the "password" command to tell the bot a nick to
identify with and what password to use to identify with that nick.  You can
use the password command multiple times if your bot has multiple nicks
registered.  Also, be sure to configure the NickServ and ChanServ
configuration variables to match the NickServ and ChanServ nicks on your
network.  Other commands such as identify, op, etc. should not be
necessary if the bot is properly configured.

.. _commands-Services:

Commands
--------
.. _command-services-chanserv:

chanserv <text>
  Sends the <text> to ChanServ. For example, to register a channel on Atheme, use: @chanserv REGISTER <#channel>.

.. _command-services-ghost:

ghost [<nick>]
  Ghosts the bot's given nick and takes it. If no nick is given, ghosts the bot's configured nick and takes it.

.. _command-services-identify:

identify takes no arguments
  Identifies with NickServ using the current nick.

.. _command-services-invite:

invite [<channel>]
  Attempts to get invited by ChanServ to <channel>. <channel> is only necessary if the message isn't sent in the channel itself, but chances are, if you need this command, you're not sending it in the channel itself.

.. _command-services-nicks:

nicks takes no arguments
  Returns the nicks that this plugin is configured to identify and ghost with.

.. _command-services-nickserv:

nickserv <text>
  Sends the <text> to NickServ. For example, to register to NickServ on Atheme, use: @nickserv REGISTER <password> <email-address>.

.. _command-services-op:

op [<channel>]
  Attempts to get opped by ChanServ in <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-services-password:

password <nick> [<password>]
  Sets the NickServ password for <nick> to <password>. If <password> is not given, removes <nick> from the configured nicks.

.. _command-services-register:

register [<network>] <password> [<email>]
  Uses the experimental REGISTER command to create an account for the bot on the <network>, using the <password> and the <email> if provided. Some networks may require the email. You may need to use the 'services verify' command afterward to confirm your email address.

.. _command-services-unban:

unban [<channel>]
  Attempts to get unbanned by ChanServ in <channel>. <channel> is only necessary if the message isn't sent in the channel itself, but chances are, if you need this command, you're not sending it in the channel itself.

.. _command-services-verify:

verify [<network>] <account> <code>
  If the <network> requires a verification code, you need to call this command with the code the server gave you to finish the registration.

.. _command-services-voice:

voice [<channel>]
  Attempts to get voiced by ChanServ in <channel>. <channel> is only necessary if the message isn't sent in the channel itself.

.. _conf-Services:

Configuration
-------------

.. _conf-supybot.plugins.Services.ChanServ:


supybot.plugins.Services.ChanServ
  This config variable defaults to "ChanServ", is network-specific, and is  not channel-specific.

  Determines what nick the 'ChanServ' service has.

  .. _conf-supybot.plugins.Services.ChanServ.halfop:


  supybot.plugins.Services.ChanServ.halfop
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether the bot will request to get half-opped by the ChanServ when it joins the channel.

  .. _conf-supybot.plugins.Services.ChanServ.op:


  supybot.plugins.Services.ChanServ.op
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether the bot will request to get opped by the ChanServ when it joins the channel.

  .. _conf-supybot.plugins.Services.ChanServ.password:


  supybot.plugins.Services.ChanServ.password
    This config variable defaults to "", is network-specific, and is  channel-specific.

    Determines what password the bot will use with ChanServ.

  .. _conf-supybot.plugins.Services.ChanServ.voice:


  supybot.plugins.Services.ChanServ.voice
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether the bot will request to get voiced by the ChanServ when it joins the channel.

.. _conf-supybot.plugins.Services.NickServ:


supybot.plugins.Services.NickServ
  This config variable defaults to "NickServ", is network-specific, and is  not channel-specific.

  Determines what nick the 'NickServ' service has.

  .. _conf-supybot.plugins.Services.NickServ.password:


  supybot.plugins.Services.NickServ.password
    This is a group of:

.. _conf-supybot.plugins.Services.disabledNetworks:


supybot.plugins.Services.disabledNetworks
  This config variable defaults to "QuakeNet", is not network-specific, and is  not channel-specific.

  Determines what networks this plugin will be disabled on.

.. _conf-supybot.plugins.Services.ghostDelay:


supybot.plugins.Services.ghostDelay
  This config variable defaults to "60", is network-specific, and is  not channel-specific.

  Determines how many seconds the bot will wait between successive GHOST attempts. Set this to 0 to disable GHOST.

.. _conf-supybot.plugins.Services.nicks:


supybot.plugins.Services.nicks
  This config variable defaults to " ", is network-specific, and is  not channel-specific.

  Determines what nicks the bot will use with services.

.. _conf-supybot.plugins.Services.noJoinsUntilIdentified:


supybot.plugins.Services.noJoinsUntilIdentified
  This config variable defaults to "False", is network-specific, and is  not channel-specific.

  Determines whether the bot will not join any channels until it is identified. This may be useful, for instances, if you have a vhost that isn't set until you're identified, or if you're joining +r channels that won't allow you to join unless you identify.

.. _conf-supybot.plugins.Services.public:


supybot.plugins.Services.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

