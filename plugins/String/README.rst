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

.. _conf-supybot.plugins.String.levenshtein:


supybot.plugins.String.levenshtein
  This is a group of:

  .. _conf-supybot.plugins.String.levenshtein.max:


  supybot.plugins.String.levenshtein.max
    This config variable defaults to "256", is not network-specific, and is  not channel-specific.

    Determines the maximum size of a string given to the levenshtein command. The levenshtein command uses an O(m*n) algorithm, which means that with strings of length 256, it can take 1.5 seconds to finish; with strings of length 384, though, it can take 4 seconds to finish, and with strings of much larger lengths, it takes more and more time. Using nested commands, strings can get quite large, hence this variable, to limit the size of arguments passed to the levenshtein command.

.. _conf-supybot.plugins.String.public:


supybot.plugins.String.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.String.re:


supybot.plugins.String.re
  This is a group of:

  .. _conf-supybot.plugins.String.re.timeout:


  supybot.plugins.String.re.timeout
    This config variable defaults to "0.1", is not network-specific, and is  not channel-specific.

    Determines the maximum time, in seconds, that a regular expression is given to execute before being terminated. Since there is a possibility that user input for the re command can cause it to eat up large amounts of ram or cpu time, it's a good idea to keep this low. Most normal regexps should not take very long at all.

