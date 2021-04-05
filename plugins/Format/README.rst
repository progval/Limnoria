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

.. _commands-Format:

Commands
--------
.. _command-Format-bold:

bold <text>
  Returns <text> bolded.

.. _command-Format-capitalize:

capitalize <text>
  Returns <text> capitalized.

.. _command-Format-color:

color <foreground> [<background>] <text>
  Returns <text> with foreground color <foreground> and background color <background> (if given)

.. _command-Format-concat:

concat <string 1> <string 2>
  Concatenates two strings. Do keep in mind that this is *not* the same thing as join "", since if <string 2> contains spaces, they won't be removed by concat.

.. _command-Format-cut:

cut <size> <text>
  Cuts <text> down to <size> by chopping off the rightmost characters in excess of <size>. If <size> is a negative number, it chops that many characters off the end of <text>.

.. _command-Format-field:

field <number> <text>
  Returns the <number>th space-separated field of <text>. I.e., if text is "foo bar baz" and <number> is 2, "bar" is returned.

.. _command-Format-format:

format <format string> [<arg> ...]
  Expands a Python-style format string using the remaining args. Just be sure always to use %s, not %d or %f or whatever, because all the args are strings.

.. _command-Format-join:

join <separator> <string 1> [<string> ...]
  Joins all the arguments together with <separator>.

.. _command-Format-lower:

lower <text>
  Returns <text> lowercased.

.. _command-Format-replace:

replace <substring to translate> <substring to replace it with> <text>
  Replaces all non-overlapping occurrences of <substring to translate> with <substring to replace it with> in <text>.

.. _command-Format-repr:

repr <text>
  Returns <text> surrounded by double quotes.

.. _command-Format-reverse:

reverse <text>
  Returns <text> in reverse-video.

.. _command-Format-stripformatting:

stripformatting <text>
  Strips bold, underline, and colors from <text>.

.. _command-Format-title:

title <text>
  Returns <text> titlecased.

.. _command-Format-translate:

translate <chars to translate> <chars to replace those with> <text>
  Replaces <chars to translate> with <chars to replace those with> in <text>. The first and second arguments must necessarily be the same length.

.. _command-Format-underline:

underline <text>
  Returns <text> underlined.

.. _command-Format-upper:

upper <text>
  Returns <text> uppercased.

Configuration
-------------
supybot.plugins.Format.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

