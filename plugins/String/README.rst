.. _plugin-String:

Documentation for the String plugin for Supybot
===============================================

Purpose
-------
Provides various commands to manipulate characters and strings.

Usage
-----
Provides useful commands for manipulating characters and strings.

.. _commands-String:

Commands
--------
.. _command-String-chr:

chr <number>
  Returns the unicode character associated with codepoint <number>

.. _command-String-decode:

decode <encoding> <text>
  Returns an un-encoded form of the given text; the valid encodings are available in the documentation of the Python codecs module: <http://docs.python.org/library/codecs.html#standard-encodings>.

.. _command-String-encode:

encode <encoding> <text>
  Returns an encoded form of the given text; the valid encodings are available in the documentation of the Python codecs module: <http://docs.python.org/library/codecs.html#standard-encodings>.

.. _command-String-len:

len <text>
  Returns the length of <text>.

.. _command-String-levenshtein:

levenshtein <string1> <string2>
  Returns the levenshtein distance (also known as the "edit distance" between <string1> and <string2>)

.. _command-String-md5:

md5 <text>
  Returns the md5 hash of a given string.

.. _command-String-ord:

ord <letter>
  Returns the unicode codepoint of <letter>.

.. _command-String-re:

re <regexp> <text>
  If <regexp> is of the form m/regexp/flags, returns the portion of <text> that matches the regexp. If <regexp> is of the form s/regexp/replacement/flags, returns the result of applying such a regexp to <text>.

.. _command-String-sha:

sha <text>
  Returns the SHA1 hash of a given string.

.. _command-String-soundex:

soundex <string> [<length>]
  Returns the Soundex hash to a given length. The length defaults to 4, since that's the standard length for a soundex hash. For unlimited length, use 0. Maximum length 1024.

.. _command-String-unicodename:

unicodename <character>
  Returns the name of the given unicode <character>.

.. _command-String-unicodesearch:

unicodesearch <name>
  Searches for a unicode character from its <name>.

.. _command-String-xor:

xor <password> <text>
  Returns <text> XOR-encrypted with <password>.

Configuration
-------------
supybot.plugins.String.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

