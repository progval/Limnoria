.. _plugin-Conditional:

Documentation for the Conditional plugin for Supybot
====================================================

Purpose
-------
Contains numerous conditional commands (such as 'if', 'and', and 'or'),
which can be used on their own or with another plugin.
Also provides logic operators for writing conditions.

Useful for bot scripting / nested commands.

Usage
-----
This plugin provides logic operators and other commands that
enable you to run commands only if a condition is true. Useful for nested
commands and scripting.

.. _commands-Conditional:

Commands
--------
.. _command-Conditional-cand:

cand <cond1> [<cond2> ... <condN>]
  Returns true if all conditions supplied evaluate to true.

.. _command-Conditional-ceq:

ceq <item1> <item2>
  Does a string comparison on <item1> and <item2>. Returns true if they are equal.

.. _command-Conditional-cerror:

cerror <testcommand>
  Runs <testcommand> and returns true if it raises an error; false otherwise.

.. _command-Conditional-cif:

cif <condition> <ifcommand> <elsecommand>
  Runs <ifcommand> if <condition> evaluates to true, runs <elsecommand> if it evaluates to false. Use other logical operators defined in this plugin and command nesting to your advantage here.

.. _command-Conditional-cor:

cor <cond1> [<cond2> ... <condN>]
  Returns true if any one of conditions supplied evaluates to true.

.. _command-Conditional-cxor:

cxor <cond1> [<cond2> ... <condN>]
  Returns true if only one of conditions supplied evaluates to true.

.. _command-Conditional-ge:

ge <item1> <item2>
  Does a string comparison on <item1> and <item2>. Returns true if <item1> is greater than or equal to <item2>.

.. _command-Conditional-gt:

gt <item1> <item2>
  Does a string comparison on <item1> and <item2>. Returns true if <item1> is greater than <item2>.

.. _command-Conditional-le:

le <item1> <item2>
  Does a string comparison on <item1> and <item2>. Returns true if <item1> is less than or equal to <item2>.

.. _command-Conditional-lt:

lt <item1> <item2>
  Does a string comparison on <item1> and <item2>. Returns true if <item1> is less than <item2>.

.. _command-Conditional-match:

match [--case-insensitive] <item1> <item2>
  Determines if <item1> is a substring of <item2>. Returns true if <item1> is contained in <item2>. Will only match case if --case-insensitive is not given.

.. _command-Conditional-nceq:

nceq <item1> <item2>
  Does a numeric comparison on <item1> and <item2>. Returns true if they are equal.

.. _command-Conditional-ne:

ne <item1> <item2>
  Does a string comparison on <item1> and <item2>. Returns true if they are not equal.

.. _command-Conditional-nge:

nge <item1> <item2>
  Does a numeric comparison on <item1> and <item2>. Returns true if <item1> is greater than or equal to <item2>.

.. _command-Conditional-ngt:

ngt <item1> <item2>
  Does a numeric comparison on <item1> and <item2>. Returns true if <item1> is greater than <item2>.

.. _command-Conditional-nle:

nle <item1> <item2>
  Does a numeric comparison on <item1> and <item2>. Returns true if <item1> is less than or equal to <item2>.

.. _command-Conditional-nlt:

nlt <item1> <item2>
  Does a numeric comparison on <item1> and <item2>. Returns true if <item1> is less than <item2>.

.. _command-Conditional-nne:

nne <item1> <item2>
  Does a numeric comparison on <item1> and <item2>. Returns true if they are not equal.

Configuration
-------------
supybot.plugins.Conditional.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

