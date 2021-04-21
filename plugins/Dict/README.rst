.. _plugin-Dict:

Documentation for the Dict plugin for Supybot
=============================================

Purpose
-------
Commands that use the dictd protocol to define words.

In order to use this plugin you must have the following modules
installed:

* dictclient: http://quux.org:70/devel/dictclient

Usage
-----
This plugin provides a function to look up words from different
dictionaries.

.. _commands-Dict:

Commands
--------
.. _command-dict-dict:

dict [<dictionary>] <word>
  Looks up the definition of <word> on the dictd server specified by the supybot.plugins.Dict.server config variable.

.. _command-dict-dictionaries:

dictionaries takes no arguments
  Returns the dictionaries valid for the dict command.

.. _command-dict-random:

random takes no arguments
  Returns a random valid dictionary.

.. _command-dict-synonym:

synonym <word> [<word> ...]
  Gets a random synonym from the Moby Thesaurus (moby-thesaurus) database. If given many words, gets a random synonym for each of them. Quote phrases to have them treated as one lookup word.

.. _conf-Dict:

Configuration
-------------

.. _conf-supybot.plugins.Dict.default:


supybot.plugins.Dict.default
  This config variable defaults to "*", is network-specific, and is  channel-specific.

  Determines the default dictionary the bot will ask for definitions in. If this value is '*' (without the quotes) the bot will use all dictionaries to define words.

.. _conf-supybot.plugins.Dict.public:


supybot.plugins.Dict.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Dict.server:


supybot.plugins.Dict.server
  This config variable defaults to "dict.org", is not network-specific, and is  not channel-specific.

  Determines what server the bot will retrieve definitions from.

.. _conf-supybot.plugins.Dict.showDictName:


supybot.plugins.Dict.showDictName
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will show which dictionaries responded to a query, if the selected dictionary is '*'.

