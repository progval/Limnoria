.. _plugin-GPG:

Documentation for the GPG plugin for Supybot
============================================

Purpose
-------
GPG: Provides authentication based on GPG keys.

Usage
-----
Provides authentication based on GPG keys.

Commands
--------
key add <key id> <key server>
  Add a GPG key to your account.

key list takes no arguments
  List your GPG keys.

key remove <fingerprint>
  Remove a GPG key from your account.

signing auth <url>
  Check the GPG signature at the <url> and authenticates you if the key used is associated to a user.

signing gettoken takes no arguments
  Send you a token that you'll have to sign with your key.

Configuration
-------------
supybot.plugins.GPG.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

