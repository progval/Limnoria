.. _plugin-Games:

Documentation for the Games plugin for Supybot
==============================================

Purpose
-------
This plugin provides some fun games like (Russian) roulette, 8ball, monologue
which tells you how many lines you have spoken without anyone interrupting
you, coin and dice.

Usage
-----
This plugin provides some small games like (Russian) roulette,
eightball, monologue, coin and dice.

.. _commands-Games:

Commands
--------
.. _command-Games-coin:

coin takes no arguments
  Flips a coin and returns the result.

.. _command-Games-dice:

dice <dice>d<sides>
  Rolls a die with <sides> number of sides <dice> times. For example, 2d6 will roll 2 six-sided dice; 10d10 will roll 10 ten-sided dice.

.. _command-Games-eightball:

eightball [<question>]
  Ask a question and the answer shall be provided.

.. _command-Games-monologue:

monologue [<channel>]
  Returns the number of consecutive lines you've sent in <channel> without being interrupted by someone else (i.e. how long your current 'monologue' is). <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Games-roulette:

roulette [spin]
  Fires the revolver. If the bullet was in the chamber, you're dead. Tell me to spin the chambers and I will.

Configuration
-------------
supybot.plugins.Games.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

