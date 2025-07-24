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

They first have to use ``@nickauth nick add <services account name>`` while
identified to the bot, and then use ``@auth`` when they want to
identify to the bot.

.. _commands-NickAuth:

Commands
--------

.. _command-nickauth-auth:

``auth takes no argument``
  Tries to authenticate you using network services. If you get no reply, it means you are not authenticated to network services.

.. _command-nickauth-nick.add:

``nick add [<network>] [<bot username>] <account>``
  Add <account> to the list of network services accounts owned by <bot username> on <network>. <bot username> is only required if you are not already logged in to Limnoria. <network> defaults to the current network.

.. _command-nickauth-nick.list:

``nick list [<network>] [<bot username>]``
  Lists services accounts registered to <bot username> on the network, or your own bot account if no username is given. <network> defaults to the current network.

.. _command-nickauth-nick.remove:

``nick remove [<network>] [<bot username>] <account>``
  Remove <account> from the list of network services accounts owned by <bot username> on <network>. <bot username> is only required if you are not already logged in to Limnoria. <network> defaults to the current network.

.. _conf-NickAuth:

Configuration
-------------

.. _conf-supybot.plugins.NickAuth.public:


supybot.plugins.NickAuth.public
  This config variable defaults to "True", is not network-specific, and is not channel-specific.

  Determines whether this plugin is publicly visible.

