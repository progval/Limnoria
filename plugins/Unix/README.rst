.. _plugin-Unix:

Documentation for the Unix plugin for Supybot
=============================================

Purpose
-------
Provides commands available only on Unix.

Usage
-----
Provides Utilities for Unix-like systems.

.. _commands-Unix:

Commands
--------
.. _command-unix-call:

call <command to call with any arguments>
  Calls any command available on the system, and returns its output. Requires owner capability. Note that being restricted to owner, this command does not do any sanity checking on input/output. So it is up to you to make sure you don't run anything that will spamify your channel or that will bring your machine to its knees.

.. _command-unix-crypt:

crypt <password> [<salt>]
  Returns the resulting of doing a crypt() on <password>. If <salt> is not given, uses a random salt. If running on a glibc2 system, prepending '$1$' to your salt will cause crypt to return an MD5sum based crypt rather than the standard DES based crypt.

.. _command-unix-errno:

errno <error number or code>
  Returns the number of an errno code, or the errno code of a number.

.. _command-unix-fortune:

fortune takes no arguments
  Returns a fortune from the Unix fortune program.

.. _command-unix-pid:

pid takes no arguments
  Returns the current pid of the process for this Supybot.

.. _command-unix-ping:

ping [--c <count>] [--i <interval>] [--t <ttl>] [--W <timeout>] [--4|--6] <host or ip>
  Sends an ICMP echo request to the specified host. The arguments correspond with those listed in ping(8). --c is limited to 10 packets or less (default is 5). --i is limited to 5 or less. --W is limited to 10 or less. --4 and --6 can be used if and only if the system has a unified ping command.

.. _command-unix-ping6:

ping6 [--c <count>] [--i <interval>] [--t <ttl>] [--W <timeout>] [--4|--6] <host or ip>
  Sends an ICMP echo request to the specified host. The arguments correspond with those listed in ping(8). --c is limited to 10 packets or less (default is 5). --i is limited to 5 or less. --W is limited to 10 or less. --4 and --6 can be used if and only if the system has a unified ping command.

.. _command-unix-progstats:

progstats takes no arguments
  Returns various unix-y information on the running supybot process.

.. _command-unix-shell:

shell <command to call with any arguments>
  Calls any command available on the system using the shell specified by the SHELL environment variable, and returns its output. Requires owner capability. Note that being restricted to owner, this command does not do any sanity checking on input/output. So it is up to you to make sure you don't run anything that will spamify your channel or that will bring your machine to its knees.

.. _command-unix-spell:

spell <word>
  Returns the result of passing <word> to aspell/ispell. The results shown are sorted from best to worst in terms of being a likely match for the spelling of <word>.

.. _command-unix-sysuname:

sysuname takes no arguments
  Returns the uname -a from the system the bot is running on.

.. _command-unix-sysuptime:

sysuptime takes no arguments
  Returns the uptime from the system the bot is running on.

.. _command-unix-wtf:

wtf [is] <something>
  Returns wtf <something> is. 'wtf' is a Unix command that first appeared in NetBSD 1.5. In most Unices, it's available in some sort of 'bsdgames' package.

.. _conf-Unix:

Configuration
-------------

.. _conf-supybot.plugins.Unix.public:

supybot.plugins.Unix.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

