.. _plugin-Nickometer:

Documentation for the Nickometer plugin for Supybot
===================================================

Purpose
-------
A port of Infobot's nickometer command from Perl. This plugin
provides one command (called nickometer) which will tell you how 'lame'
an IRC nick is. It's an elitist hacker thing, but quite fun.

Usage
-----
Will tell you how lame a nick is by the command 'nickometer [nick]'.

.. _commands-Nickometer:

Commands
--------
.. _command-Nickometer-nickometer:

nickometer [<nick>]
  Tells you how lame said nick is. If <nick> is not given, uses the nick of the person giving the command.

Configuration
-------------
supybot.plugins.Nickometer.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

