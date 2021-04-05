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
.. _command-Filter-aol:

aol <text>
  Returns <text> as if an AOL user had said it.

.. _command-Filter-binary:

binary <text>
  Returns the binary representation of <text>.

.. _command-Filter-caps:

caps <text>
  EVERYONE LOVES CAPS LOCK.

.. _command-Filter-capwords:

capwords <text>
  Capitalises the first letter of each word.

.. _command-Filter-colorize:

colorize <text>
  Returns <text> with each character randomly colorized.

.. _command-Filter-gnu:

gnu <text>
  Returns <text> as GNU/RMS would say it.

.. _command-Filter-hebrew:

hebrew <text>
  Removes all the vowels from <text>. (If you're curious why this is named 'hebrew' it's because I (jemfinch) thought of it in Hebrew class, and printed Hebrew often elides the vowels.)

.. _command-Filter-hexlify:

hexlify <text>
  Returns a hexstring from the given string; a hexstring is a string composed of the hexadecimal value of each character in the string

.. _command-Filter-jeffk:

jeffk <text>
  Returns <text> as if JeffK had said it himself.

.. _command-Filter-leet:

leet <text>
  Returns the l33tspeak version of <text>

.. _command-Filter-morse:

morse <text>
  Gives the Morse code equivalent of a given string.

.. _command-Filter-outfilter:

outfilter [<channel>] [<command>]
  Sets the outFilter of this plugin to be <command>. If no command is given, unsets the outFilter. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-Filter-rainbow:

rainbow <text>
  Returns <text> colorized like a rainbow.

.. _command-Filter-reverse:

reverse <text>
  Reverses <text>.

.. _command-Filter-rot13:

rot13 <text>
  Rotates <text> 13 characters to the right in the alphabet. Rot13 is commonly used for text that simply needs to be hidden from inadvertent reading by roaming eyes, since it's easily reversible.

.. _command-Filter-scramble:

scramble <text>
  Replies with a string where each word is scrambled; i.e., each internal letter (that is, all letters but the first and last) are shuffled.

.. _command-Filter-shrink:

shrink <text>
  Returns <text> with each word longer than supybot.plugins.Filter.shrink.minimum being shrunken (i.e., like "internationalization" becomes "i18n").

.. _command-Filter-spellit:

spellit <text>
  Returns <text>, phonetically spelled out.

.. _command-Filter-squish:

squish <text>
  Removes all the spaces from <text>.

.. _command-Filter-stripcolor:

stripcolor <text>
  Returns <text> stripped of all color codes.

.. _command-Filter-supa1337:

supa1337 <text>
  Replies with an especially k-rad translation of <text>.

.. _command-Filter-unbinary:

unbinary <text>
  Returns the character representation of binary <text>. Assumes ASCII, 8 digits per character.

.. _command-Filter-undup:

undup <text>
  Returns <text>, with all consecutive duplicated letters removed.

.. _command-Filter-unhexlify:

unhexlify <hexstring>
  Returns the string corresponding to <hexstring>. Obviously, <hexstring> must be a string of hexadecimal digits.

.. _command-Filter-uniud:

uniud <text>
  Returns <text> rotated 180 degrees. Only really works for ASCII printable characters.

.. _command-Filter-unmorse:

unmorse <Morse code text>
  Does the reverse of the morse command.

.. _command-Filter-uwu:

uwu <text>
  Returns <text> in uwu-speak.

.. _command-Filter-vowelrot:

vowelrot <text>
  Returns <text> with vowels rotated

Configuration
-------------
supybot.plugins.Filter.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

