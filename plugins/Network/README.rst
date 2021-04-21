.. _plugin-Network:

Documentation for the Network plugin for Supybot
================================================

Purpose
-------
Includes commands for connecting, disconnecting, and reconnecting to multiple
networks, as well as several other utility functions related to IRC networks
like showing the latency.

Usage
-----
Provides network-related commands, such as connecting to multiple networks
and checking latency to the server.

.. _commands-Network:

Commands
--------
.. _command-network-capabilities:

capabilities [<network>]
  Returns the list of IRCv3 capabilities available on the network.

.. _command-network-cmdall:

cmdall <command> [<arg> ...]
  Perform <command> (with its associated <arg>s) on all networks.

.. _command-network-command:

command <network> <command> [<arg> ...]
  Gives the bot <command> (with its associated <arg>s) on <network>.

.. _command-network-connect:

connect [--nossl] <network> [<host[:port]>] [<password>]
  Connects to another network (which will be represented by the name provided in <network>) at <host:port>. If port is not provided, it defaults to 6697, the default port for IRC with SSL. If password is provided, it will be sent to the server in a PASS command. If --nossl is provided, an SSL connection will not be attempted, and the port will default to 6667.

.. _command-network-disconnect:

disconnect <network> [<quit message>]
  Disconnects from the network represented by the network <network>. If <quit message> is given, quits the network with the given quit message.

.. _command-network-driver:

driver [<network>]
  Returns the current network driver for <network>. <network> is only necessary if the message isn't sent on the network to which this command is to apply.

.. _command-network-latency:

latency [<network>]
  Returns the current latency to <network>. <network> is only necessary if the message isn't sent on the network to which this command is to apply.

.. _command-network-networks:

networks [--all]
  Returns the networks to which the bot is currently connected. If --all is given, also includes networks known by the bot, but not connected to.

.. _command-network-reconnect:

reconnect [<network>] [<quit message>]
  Disconnects and then reconnects to <network>. If no network is given, disconnects and then reconnects to the network the command was given on. If no quit message is given, uses the configured one (supybot.plugins.Owner.quitMsg) or the nick of the person giving the command.

.. _command-network-uptime:

uptime [<network>]
  Returns the time duration since the connection was established.

.. _command-network-whois:

whois [<network>] <nick>
  Returns the WHOIS response <network> gives for <nick>. <network> is only necessary if the network is different than the network the command is sent on.

.. _command-network-whowas:

whowas [<network>] <nick>
  Returns the WHOIS response <network> gives for <nick>. <network> is only necessary if the network is different than the network the command is sent on.

.. _conf-Network:

Configuration
-------------

.. _conf-supybot.plugins.Network.public:


supybot.plugins.Network.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

