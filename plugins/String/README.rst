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
.. _command-string-chr:

chr <number>
  Returns the unicode character associated with codepoint <number>

.. _command-string-decode:

decode <encoding> <text>
  Returns an un-encoded form of the given text; the valid encodings are available in the documentation of the Python codecs module: <http://docs.python.org/library/codecs.html#standard-encodings>.

.. _command-string-encode:

encode <encoding> <text>
  Returns an encoded form of the given text; the valid encodings are available in the documentation of the Python codecs module: <http://docs.python.org/library/codecs.html#standard-encodings>.

.. _command-string-len:

len <text>
  Returns the length of <text>.

.. _command-string-levenshtein:

levenshtein <string1> <string2>
  Returns the levenshtein distance (also known as the "edit distance" between <string1> and <string2>)

.. _command-string-md5:

md5 <text>
  Returns the md5 hash of a given string.

.. _command-string-ord:

ord <letter>
  Returns the unicode codepoint of <letter>.

.. _command-string-re:

re <regexp> <text>
  If <regexp> is of the form m/regexp/flags, returns the portion of <text> that matches the regexp. If <regexp> is of the form s/regexp/replacement/flags, returns the result of applying such a regexp to <text>.

.. _command-string-sha:

sha <text>
  Returns the SHA1 hash of a given string.

.. _command-string-soundex:

soundex <string> [<length>]
  Returns the Soundex hash to a given length. The length defaults to 4, since that's the standard length for a soundex hash. For unlimited length, use 0. Maximum length 1024.

.. _command-string-unicodename:

unicodename <character>
  Returns the name of the given unicode <character>.

.. _command-string-unicodesearch:

unicodesearch <name>
  Searches for a unicode character from its <name>.

.. _command-string-xor:

xor <password> <text>
  Returns <text> XOR-encrypted with <password>.

.. _conf-String:

Configuration
-------------

.. _conf-supybot.plugins.String.public:

supybot.plugins.String.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

