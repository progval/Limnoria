.. _plugin-Relay:

Documentation for the Relay plugin for Supybot
==============================================

Purpose
-------
Handles relaying between networks.

Usage
-----
This plugin allows you to setup a relay between networks.

Note that you must tell the bot to join the channel you wish to relay on
all networks with the ``join`` command or
``network command <network> join <channel>``
or to join the channel on all networks ``network cmdall join <channel>``.

There are several advanced alternatives to this plugin, available as
third-party plugins. You can check them out at
https://limnoria.net/plugins.xhtml#messaging

.. _commands-Relay:

Commands
--------
.. _command-relay-join:

join [<channel>]
  Starts relaying between the channel <channel> on all networks. If on a network the bot isn't in <channel>, it'll join. This commands is required even if the bot is in the channel on both networks; it won't relay between those channels unless it's told to join both channels. If <channel> is not given, starts relaying on the channel the message was sent in.

.. _command-relay-nicks:

nicks [<channel>]
  Returns the nicks of the people in the channel on the various networks the bot is connected to. <channel> is only necessary if the message isn't sent on the channel itself.

.. _command-relay-part:

part <channel>
  Ceases relaying between the channel <channel> on all networks. The bot will part from the channel on all networks in which it is on the channel.

.. _conf-Relay:

Configuration
-------------

.. _conf-supybot.plugins.Relay.channels:


supybot.plugins.Relay.channels
  This config variable defaults to " ", is not network-specific, and is  not channel-specific.

  Determines which channels the bot will relay in.

  .. _conf-supybot.plugins.Relay.channels.joinOnAllNetworks:


  supybot.plugins.Relay.channels.joinOnAllNetworks
    This config variable defaults to "False", is network-specific, and is  channel-specific.

    Determines whether the bot will always join the channel(s) it relays when connecting to any network.

.. _conf-supybot.plugins.Relay.color:


supybot.plugins.Relay.color
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will color relayed PRIVMSGs so as to make the messages easier to read.

.. _conf-supybot.plugins.Relay.hostmasks:


supybot.plugins.Relay.hostmasks
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will relay the hostmask of the person joining or parting the channel when they join or part.

.. _conf-supybot.plugins.Relay.ignores:


supybot.plugins.Relay.ignores
  This config variable defaults to " ", is network-specific, and is  channel-specific.

  Determines what hostmasks will not be relayed on a channel.

.. _conf-supybot.plugins.Relay.includeNetwork:


supybot.plugins.Relay.includeNetwork
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will include the network in relayed PRIVMSGs; if you're only relaying between two networks, it's somewhat redundant, and you may wish to save the space.

.. _conf-supybot.plugins.Relay.noticeNonPrivmsgs:


supybot.plugins.Relay.noticeNonPrivmsgs
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will used NOTICEs rather than PRIVMSGs for non-PRIVMSG relay messages (i.e., joins, parts, nicks, quits, modes, etc.)

.. _conf-supybot.plugins.Relay.public:


supybot.plugins.Relay.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Relay.punishOtherRelayBots:


supybot.plugins.Relay.punishOtherRelayBots
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will detect other bots relaying and respond by kickbanning them.

.. _conf-supybot.plugins.Relay.topicSync:


supybot.plugins.Relay.topicSync
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will synchronize topics between networks in the channels it relays.

