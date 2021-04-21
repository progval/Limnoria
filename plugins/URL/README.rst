.. _plugin-URL:

Documentation for the URL plugin for Supybot
============================================

Purpose
-------
Keeps track of URLs posted to a channel, along with relevant context.  Allows
searching for URLs and returning random URLs.  Also provides statistics on the
URLs in the database.

Usage
-----
This plugin records how many URLs have been mentioned in
a channel and what the last URL was.

.. _commands-URL:

Commands
--------
.. _command-url-last:

last [<channel>] [--{from,with,without,near,proto} <value>] [--nolimit]
  Gives the last URL matching the given criteria. --from is from whom the URL came; --proto is the protocol the URL used; --with is something inside the URL; --without is something that should not be in the URL; --near is something in the same message as the URL. If --nolimit is given, returns all the URLs that are found to just the URL. <channel> is only necessary if the message isn't sent in the channel itself.

.. _command-url-stats:

stats [<channel>]
  Returns the number of URLs in the URL database. <channel> is only required if the message isn't sent in the channel itself.

.. _conf-URL:

Configuration
-------------

.. _conf-supybot.plugins.URL.nonSnarfingRegexp:


supybot.plugins.URL.nonSnarfingRegexp
  This config variable defaults to "", is network-specific, and is  channel-specific.

  Determines what URLs are not to be snarfed and stored in the database for the channel; URLs matching the given regexp will not be snarfed. Give the empty string if you have no URLs that you'd like to exclude from being snarfed.

.. _conf-supybot.plugins.URL.public:


supybot.plugins.URL.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

