.. _plugin-Filter:

Documentation for the Filter plugin for Supybot
===============================================

Purpose
-------
Provides numerous filters, and a command (outfilter) to set them as filters on
the output of the bot.
For instance, you could make everything the bot says be
in leetspeak, or Morse code, or any number of other kinds of filters.
Not very useful, but definitely quite fun :)

See also the :ref:`Format plugin <plugin-Format>` for format manipulation
commands.

Usage
-----
This plugin offers several commands which transform text in some way.
It also provides the capability of using such commands to 'filter' the
output of the bot -- for instance, you could make everything the bot says
be in leetspeak, or Morse code, or any number of other kinds of filters.
Not very useful, but definitely quite fun :)

.. _commands-Filter:

Commands
--------
.. _command-filter-aol:

aol <text>
  Returns <text> as if an AOL user had said it.

.. _command-filter-binary:

binary <text>
  Returns the binary representation of <text>.

.. _command-filter-caps:

caps <text>
  EVERYONE LOVES CAPS LOCK.

.. _command-filter-capwords:

capwords <text>
  Capitalises the first letter of each word.

.. _command-filter-colorize:

colorize <text>
  Returns <text> with each character randomly colorized.

.. _command-filter-gnu:

gnu <text>
  Returns <text> as GNU/RMS would say it.

.. _command-filter-hebrew:

hebrew <text>
  Removes all the vowels from <text>. (If you're curious why this is named 'hebrew' it's because I (jemfinch) thought of it in Hebrew class, and printed Hebrew often elides the vowels.)

.. _command-filter-hexlify:

hexlify <text>
  Returns a hexstring from the given string; a hexstring is a string composed of the hexadecimal value of each character in the string

.. _command-filter-jeffk:

jeffk <text>
  Returns <text> as if JeffK had said it himself.

.. _command-filter-leet:

leet <text>
  Returns the l33tspeak version of <text>

.. _command-filter-morse:

morse <text>
  Gives the Morse code equivalent of a given string.

.. _command-filter-outfilter:

outfilter [<channel>] [<command>]
  Sets the outFilter of this plugin to be <command>. If no command is given, unsets the outFilter. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-filter-rainbow:

rainbow <text>
  Returns <text> colorized like a rainbow.

.. _command-filter-reverse:

reverse <text>
  Reverses <text>.

.. _command-filter-rot13:

rot13 <text>
  Rotates <text> 13 characters to the right in the alphabet. Rot13 is commonly used for text that simply needs to be hidden from inadvertent reading by roaming eyes, since it's easily reversible.

.. _command-filter-scramble:

scramble <text>
  Replies with a string where each word is scrambled; i.e., each internal letter (that is, all letters but the first and last) are shuffled.

.. _command-filter-shrink:

shrink <text>
  Returns <text> with each word longer than supybot.plugins.Filter.shrink.minimum being shrunken (i.e., like "internationalization" becomes "i18n").

.. _command-filter-spellit:

spellit <text>
  Returns <text>, phonetically spelled out.

.. _command-filter-squish:

squish <text>
  Removes all the spaces from <text>.

.. _command-filter-stripcolor:

stripcolor <text>
  Returns <text> stripped of all color codes.

.. _command-filter-supa1337:

supa1337 <text>
  Replies with an especially k-rad translation of <text>.

.. _command-filter-unbinary:

unbinary <text>
  Returns the character representation of binary <text>. Assumes ASCII, 8 digits per character.

.. _command-filter-undup:

undup <text>
  Returns <text>, with all consecutive duplicated letters removed.

.. _command-filter-unhexlify:

unhexlify <hexstring>
  Returns the string corresponding to <hexstring>. Obviously, <hexstring> must be a string of hexadecimal digits.

.. _command-filter-uniud:

uniud <text>
  Returns <text> rotated 180 degrees. Only really works for ASCII printable characters.

.. _command-filter-unmorse:

unmorse <Morse code text>
  Does the reverse of the morse command.

.. _command-filter-uwu:

uwu <text>
  Returns <text> in uwu-speak.

.. _command-filter-vowelrot:

vowelrot <text>
  Returns <text> with vowels rotated

.. _conf-Filter:

Configuration
-------------

.. _conf-supybot.plugins.Filter.public:


supybot.plugins.Filter.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Filter.shrink:


supybot.plugins.Filter.shrink
  This is a group of:

  .. _conf-supybot.plugins.Filter.shrink.minimum:


  supybot.plugins.Filter.shrink.minimum
    This config variable defaults to "4", is network-specific, and is  channel-specific.

    Determines the minimum number of a letters in a word before it will be shrunken by the shrink command/filter.

.. _conf-supybot.plugins.Filter.spellit:


supybot.plugins.Filter.spellit
  This is a group of:

  .. _conf-supybot.plugins.Filter.spellit.replaceLetters:


  supybot.plugins.Filter.spellit.replaceLetters
    This config variable defaults to "True", is not network-specific, and is  not channel-specific.

    Determines whether or not to replace letters in the output of spellit.

  .. _conf-supybot.plugins.Filter.spellit.replaceNumbers:


  supybot.plugins.Filter.spellit.replaceNumbers
    This config variable defaults to "True", is not network-specific, and is  not channel-specific.

    Determines whether or not to replace numbers in the output of spellit.

  .. _conf-supybot.plugins.Filter.spellit.replacePunctuation:


  supybot.plugins.Filter.spellit.replacePunctuation
    This config variable defaults to "True", is not network-specific, and is  not channel-specific.

    Determines whether or not to replace punctuation in the output of spellit.

