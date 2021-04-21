.. _plugin-NickAuth:

Documentation for the NickAuth plugin for Supybot
=================================================

Purpose
-------
Support authentication based on nicks and network services.

Usage
-----
This plugin allows users to use their network services account to
authenticate to the bot.

They first have to use ``@nickauth nick add <the nick>`` while being
identified to the bot and then use ``@auth`` when they want to
identify to the bot.

.. _commands-NickAuth:

Commands
--------
.. _command-nickauth-auth:

auth takes no argument
  Tries to authenticate you using network services. If you get no reply, it means you are not authenticated to the network services.

.. _command-nickauth-nick.add:

nick add [<network>] <user> <nick>
  Add <nick> to the list of nicks owned by the <user> on the <network>. You have to register this nick to the network services to be authenticated. <network> defaults to the current network.

.. _command-nickauth-nick.list:

nick list [<network>] [<user>]
  Lists nicks of the <user> on the network. <network> defaults to the current network.

.. _command-nickauth-nick.remove:

nick remove [<network>] <user> <nick>
  Remove <nick> from the list of nicks owned by the <user> on the <network>. <network> defaults to the current network.

.. _conf-NickAuth:

Configuration
-------------

.. _conf-supybot.plugins.NickAuth.public:


supybot.plugins.NickAuth.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

