.. _plugin-Format:

Documentation for the Format plugin for Supybot
===============================================

Purpose
-------
Provides simple commands for formatting text on IRC (like bold),
and to change the output of the bot for a particular command.
See also the :ref:`Filter plugin <plugin-Filter>` to configure
the output format for all commands.

Usage
-----
Provides some commands for formatting text, such as making text bold or
capitalized.

Commands
--------
bold <text>
  Returns <text> bolded.

capitalize <text>
  Returns <text> capitalized.

color <foreground> [<background>] <text>
  Returns <text> with foreground color <foreground> and background color <background> (if given)

concat <string 1> <string 2>
  Concatenates two strings. Do keep in mind that this is *not* the same thing as join "", since if <string 2> contains spaces, they won't be removed by concat.

cut <size> <text>
  Cuts <text> down to <size> by chopping off the rightmost characters in excess of <size>. If <size> is a negative number, it chops that many characters off the end of <text>.

field <number> <text>
  Returns the <number>th space-separated field of <text>. I.e., if text is "foo bar baz" and <number> is 2, "bar" is returned.

format <format string> [<arg> ...]
  Expands a Python-style format string using the remaining args. Just be sure always to use %s, not %d or %f or whatever, because all the args are strings.

join <separator> <string 1> [<string> ...]
  Joins all the arguments together with <separator>.

lower <text>
  Returns <text> lowercased.

replace <substring to translate> <substring to replace it with> <text>
  Replaces all non-overlapping occurrences of <substring to translate> with <substring to replace it with> in <text>.

repr <text>
  Returns <text> surrounded by double quotes.

reverse <text>
  Returns <text> in reverse-video.

stripformatting <text>
  Strips bold, underline, and colors from <text>.

title <text>
  Returns <text> titlecased.

translate <chars to translate> <chars to replace those with> <text>
  Replaces <chars to translate> with <chars to replace those with> in <text>. The first and second arguments must necessarily be the same length.

underline <text>
  Returns <text> underlined.

upper <text>
  Returns <text> uppercased.

Configuration
-------------
supybot.plugins.Format.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

