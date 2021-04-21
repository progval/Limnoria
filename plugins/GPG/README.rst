.. _plugin-GPG:

Documentation for the GPG plugin for Supybot
============================================

Purpose
-------
GPG: Provides authentication based on GPG keys.

Usage
-----
Provides authentication based on GPG keys.

.. _commands-GPG:

Commands
--------
.. _command-gpg-key.add:

key add <key id> <key server>
  Add a GPG key to your account.

.. _command-gpg-key.list:

key list takes no arguments
  List your GPG keys.

.. _command-gpg-key.remove:

key remove <fingerprint>
  Remove a GPG key from your account.

.. _command-gpg-signing.auth:

signing auth <url>
  Check the GPG signature at the <url> and authenticates you if the key used is associated to a user.

.. _command-gpg-signing.gettoken:

signing gettoken takes no arguments
  Send you a token that you'll have to sign with your key.

.. _conf-GPG:

Configuration
-------------

.. _conf-supybot.plugins.GPG.auth:


supybot.plugins.GPG.auth
  This is a group of:

  .. _conf-supybot.plugins.GPG.auth.sign:


  supybot.plugins.GPG.auth.sign
    This is a group of:

    .. _conf-supybot.plugins.GPG.auth.sign.TokenTimeout:


    supybot.plugins.GPG.auth.sign.TokenTimeout
      This config variable defaults to "600", is not network-specific, and is  not channel-specific.

      Determines the lifetime of a GPG signature authentication token (in seconds).

    .. _conf-supybot.plugins.GPG.auth.sign.enable:


    supybot.plugins.GPG.auth.sign.enable
      This config variable defaults to "True", is not network-specific, and is  not channel-specific.

      Determines whether or not users are allowed to use GPG signing for authentication.

.. _conf-supybot.plugins.GPG.public:


supybot.plugins.GPG.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

