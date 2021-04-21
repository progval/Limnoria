.. _plugin-Scheduler:

Documentation for the Scheduler plugin for Supybot
==================================================

Purpose
-------
Gives the user the ability to schedule commands to run at a particular time,
or repeatedly run at a particular interval. For example,
``scheduler add [time seconds 30m] "utilities echo [status cpu]"``
will schedule the command `cpu` to be sent to the channel in 30 minutes.

Usage
-----
This plugin allows you to schedule commands to execute at a later time.

.. _commands-Scheduler:

Commands
--------
.. _command-scheduler-add:

add <seconds> <command>
  Schedules the command string <command> to run <seconds> seconds in the future. For example, 'scheduler add [seconds 30m] "echo [cpu]"' will schedule the command "cpu" to be sent to the channel the schedule add command was given in (with no prefixed nick, a consequence of using echo). Do pay attention to the quotes in that example.

.. _command-scheduler-list:

list takes no arguments
  Lists the currently scheduled events.

.. _command-scheduler-remind:

remind <seconds> <text>
  Sets a reminder with string <text> to run <seconds> seconds in the future. For example, 'scheduler remind [seconds 30m] "Hello World"' will return '<nick> Reminder: Hello World' 30 minutes after being set.

.. _command-scheduler-remove:

remove <id>
  Removes the event scheduled with id <id> from the schedule.

.. _command-scheduler-repeat:

repeat [--delay <delay>] <name> <seconds> <command>
  Schedules the command <command> to run every <seconds> seconds, starting now (i.e., the command runs now, and every <seconds> seconds thereafter). <name> is a name by which the command can be unscheduled. If --delay is given, starts in <delay> seconds instead of now.

.. _conf-Scheduler:

Configuration
-------------

.. _conf-supybot.plugins.Scheduler.public:


supybot.plugins.Scheduler.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

