.. _plugin-Google:

Documentation for the Google plugin for Supybot
===============================================

Purpose
-------

Accesses Google for various things.

Usage
-----

This plugin provides access to Google services:

1. translate

   Translates a string
   ``!translate en ar test``

Check: `Supported language codes`_

.. _Supported language codes: <https://cloud.google.com/translate/v2/using_rest#language-params>`

.. _commands-Google:

Commands
--------

.. _command-google-translate:

``translate <source language> [to] <target language> <text>``
  Returns <text> translated from <source language> into <target language>. <source language> and <target language> take language codes (not language names), which are listed here: https://cloud.google.com/translate/docs/languages

.. _conf-Google:

Configuration
-------------

.. _conf-supybot.plugins.Google.public:


supybot.plugins.Google.public
  This config variable defaults to "True", is not network-specific, and is not channel-specific.

  Determines whether this plugin is publicly visible.

