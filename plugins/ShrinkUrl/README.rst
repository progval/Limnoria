.. _plugin-ShrinkUrl:

Documentation for the ShrinkUrl plugin for Supybot
==================================================

Purpose
-------
Shrinks URLs using various URL shortening services, like tinyurl.

Usage
-----
This plugin features commands to shorten URLs through different services,
like tinyurl.

.. _commands-ShrinkUrl:

Commands
--------
.. _command-shrinkurl-tiny:

tiny <url>
  Returns a TinyURL.com version of <url>

.. _command-shrinkurl-ur1:

ur1 <url>
  Returns an ur1 version of <url>.

.. _command-shrinkurl-x0:

x0 <url>
  Returns an x0.no version of <url>.

.. _conf-ShrinkUrl:

Configuration
-------------

.. _conf-supybot.plugins.ShrinkUrl.bold:


supybot.plugins.ShrinkUrl.bold
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin will bold certain portions of its replies.

.. _conf-supybot.plugins.ShrinkUrl.default:


supybot.plugins.ShrinkUrl.default
  This config variable defaults to "x0", is network-specific, and is  channel-specific.

  Determines what website the bot will use when shrinking a URL.  Valid strings: tiny, ur1, and x0.

.. _conf-supybot.plugins.ShrinkUrl.minimumLength:


supybot.plugins.ShrinkUrl.minimumLength
  This config variable defaults to "48", is network-specific, and is  channel-specific.

  The minimum length a URL must be before the bot will shrink it.

.. _conf-supybot.plugins.ShrinkUrl.nonSnarfingRegexp:


supybot.plugins.ShrinkUrl.nonSnarfingRegexp
  This config variable defaults to "", is network-specific, and is  channel-specific.

  Determines what URLs are to be snarfed; URLs matching the regexp given will not be snarfed. Give the empty string if you have no URLs that you'd like to exclude from being snarfed.

.. _conf-supybot.plugins.ShrinkUrl.outFilter:


supybot.plugins.ShrinkUrl.outFilter
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will shrink the URLs of outgoing messages if those URLs are longer than supybot.plugins.ShrinkUrl.minimumLength.

.. _conf-supybot.plugins.ShrinkUrl.public:


supybot.plugins.ShrinkUrl.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.ShrinkUrl.serviceRotation:


supybot.plugins.ShrinkUrl.serviceRotation
  This config variable defaults to " ", is network-specific, and is  channel-specific.

  If set to a non-empty value, specifies the list of services to rotate through for the shrinkSnarfer and outFilter.

.. _conf-supybot.plugins.ShrinkUrl.shrinkSnarfer:


supybot.plugins.ShrinkUrl.shrinkSnarfer
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the shrink snarfer is enabled. This snarfer will watch for URLs in the channel, and if they're sufficiently long (as determined by supybot.plugins.ShrinkUrl.minimumLength) it will post a smaller URL from the service as denoted in supybot.plugins.ShrinkUrl.default.

  .. _conf-supybot.plugins.ShrinkUrl.shrinkSnarfer.showDomain:


  supybot.plugins.ShrinkUrl.shrinkSnarfer.showDomain
    This config variable defaults to "True", is network-specific, and is  channel-specific.

    Determines whether the snarfer will show the domain of the URL being snarfed along with the shrunken URL.

