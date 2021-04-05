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

Commands
--------
aol <text>
  Returns <text> as if an AOL user had said it.

binary <text>
  Returns the binary representation of <text>.

caps <text>
  EVERYONE LOVES CAPS LOCK.

capwords <text>
  Capitalises the first letter of each word.

colorize <text>
  Returns <text> with each character randomly colorized.

gnu <text>
  Returns <text> as GNU/RMS would say it.

hebrew <text>
  Removes all the vowels from <text>. (If you're curious why this is named 'hebrew' it's because I (jemfinch) thought of it in Hebrew class, and printed Hebrew often elides the vowels.)

hexlify <text>
  Returns a hexstring from the given string; a hexstring is a string composed of the hexadecimal value of each character in the string

jeffk <text>
  Returns <text> as if JeffK had said it himself.

leet <text>
  Returns the l33tspeak version of <text>

morse <text>
  Gives the Morse code equivalent of a given string.

outfilter [<channel>] [<command>]
  Sets the outFilter of this plugin to be <command>. If no command is given, unsets the outFilter. <channel> is only necessary if the message isn't sent in the channel itself.

rainbow <text>
  Returns <text> colorized like a rainbow.

reverse <text>
  Reverses <text>.

rot13 <text>
  Rotates <text> 13 characters to the right in the alphabet. Rot13 is commonly used for text that simply needs to be hidden from inadvertent reading by roaming eyes, since it's easily reversible.

scramble <text>
  Replies with a string where each word is scrambled; i.e., each internal letter (that is, all letters but the first and last) are shuffled.

shrink <text>
  Returns <text> with each word longer than supybot.plugins.Filter.shrink.minimum being shrunken (i.e., like "internationalization" becomes "i18n").

spellit <text>
  Returns <text>, phonetically spelled out.

squish <text>
  Removes all the spaces from <text>.

stripcolor <text>
  Returns <text> stripped of all color codes.

supa1337 <text>
  Replies with an especially k-rad translation of <text>.

unbinary <text>
  Returns the character representation of binary <text>. Assumes ASCII, 8 digits per character.

undup <text>
  Returns <text>, with all consecutive duplicated letters removed.

unhexlify <hexstring>
  Returns the string corresponding to <hexstring>. Obviously, <hexstring> must be a string of hexadecimal digits.

uniud <text>
  Returns <text> rotated 180 degrees. Only really works for ASCII printable characters.

unmorse <Morse code text>
  Does the reverse of the morse command.

uwu <text>
  Returns <text> in uwu-speak.

vowelrot <text>
  Returns <text> with vowels rotated

Configuration
-------------
supybot.plugins.Filter.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

