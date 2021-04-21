.. _plugin-Time:

Documentation for the Time plugin for Supybot
=============================================

Purpose
-------
A plugin for time-related functions.

Usage
-----
This plugin allows you to use different time-related functions.

.. _commands-Time:

Commands
--------
.. _command-time-at:

at [<time string>]
  Returns the number of seconds since epoch <time string> is. <time string> can be any number of natural formats; just try something and see if it will work. If the <time string> is not given, defaults to now.

.. _command-time-ctime:

ctime [<seconds since epoch>]
  Returns the ctime for <seconds since epoch>, or the current ctime if no <seconds since epoch> is given.

.. _command-time-ddate:

ddate [<year> <month> <day>]
  Returns a the Discordian date today, or an optional different date.

.. _command-time-elapsed:

elapsed <seconds>
  Returns a pretty string that is the amount of time represented by <seconds>.

.. _command-time-seconds:

seconds [<years>y] [<weeks>w] [<days>d] [<hours>h] [<minutes>m] [<seconds>s]
  Returns the number of seconds in the number of <years>, <weeks>, <days>, <hours>, <minutes>, and <seconds> given. An example usage is "seconds 2h 30m", which would return 9000, which is '3600*2 + 30*60'. Useful for scheduling events at a given number of seconds in the future.

.. _command-time-time:

time [<channel>] [<format>] [<seconds since epoch>]
  Returns the current time in <format> format, or, if <format> is not given, uses the configurable format for the current channel. If no <seconds since epoch> time is given, the current time is used. If <channel> is given without <format>, uses the format for <channel>.

.. _command-time-tztime:

tztime <region>/<city>
  Takes a city and its region, and returns its local time. This command uses the IANA Time Zone Database.

.. _command-time-until:

until <time string>
  Returns the number of seconds until <time string>.

.. _conf-Time:

Configuration
-------------

.. _conf-supybot.plugins.Time.format:


supybot.plugins.Time.format
  This config variable defaults to "%Y-%m-%dT%H:%M:%S%z", is network-specific, and is  channel-specific.

  Determines the format string for timestamps. Refer to the Python documentation for the time module to see what formats are accepted. If you set this variable to the empty string, the timestamp will not be shown.

.. _conf-supybot.plugins.Time.public:


supybot.plugins.Time.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

