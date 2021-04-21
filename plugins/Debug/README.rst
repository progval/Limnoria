.. _plugin-Debug:

Documentation for the Debug plugin for Supybot
==============================================

Purpose
-------
This is for developers debugging their plugins; it provides an eval command
as well as some other useful commands.
It should not be loaded with a default installation.

Usage
-----
This plugin provides debugging abilities for Supybot. It
should not be loaded with a default installation.

.. _commands-Debug:

Commands
--------
.. _command-debug-channeldb:

channeldb [<channel>]
  Returns the result of the channeldb converter.

.. _command-debug-collect:

collect [<times>]
  Does <times> gc collections, returning the number of objects collected each time. <times> defaults to 1.

.. _command-debug-environ:

environ takes no arguments
  Returns the environment of the supybot process.

.. _command-debug-eval:

eval <expression>
  Evaluates <expression> (which should be a Python expression) and returns its value. If an exception is raised, reports the exception (and logs the traceback to the bot's logfile).

.. _command-debug-exec:

exec <statement>
  Execs <code>. Returns success if it didn't raise any exceptions.

.. _command-debug-exn:

exn <exception name>
  Raises the exception matching <exception name>.

.. _command-debug-sendquote:

sendquote <raw IRC message>
  Sends (not queues) the raw IRC message given.

.. _command-debug-settrace:

settrace [<filename>]
  Starts tracing function calls to <filename>. If <filename> is not given, sys.stdout is used. This causes much output.

.. _command-debug-simpleeval:

simpleeval <expression>
  Evaluates the given expression.

.. _command-debug-unsettrace:

unsettrace takes no arguments
  Stops tracing function calls on stdout.

.. _conf-Debug:

Configuration
-------------

.. _conf-supybot.plugins.Debug.public:


supybot.plugins.Debug.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

