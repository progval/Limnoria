.. _plugin-Hashes:

Documentation for the Hashes plugin for Supybot
===============================================

Purpose
-------
Provides various hash- and encryption-related commands.

Usage
-----
Provides hash or encryption related commands

Commands
--------
algorithms <takes no arguments>
  Returns the list of available algorithms.

md5 <text>
  Returns the md5 hash of a given string.

mkhash <algorithm> <text>
  Returns TEXT after it has been hashed with ALGORITHM. See the 'algorithms' command in this plugin to return the algorithms available on this system.

sha <text>
  Returns the SHA1 hash of a given string.

sha256 <text>
  Returns a SHA256 hash of the given string.

sha512 <text>
  Returns a SHA512 hash of the given string.

Configuration
-------------
supybot.plugins.Hashes.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

