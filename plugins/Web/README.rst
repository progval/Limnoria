.. _plugin-Web:

Documentation for the Web plugin for Supybot
============================================

Purpose
-------
This plugin allows you to view website information, like the title of a page. Also provides a Snarfer for URLs.

Usage
-----
Add the help for 'help Web' here.

.. _commands-Web:

Commands
--------
.. _command-web-doctype:

doctype <url>
  Returns the DOCTYPE string of <url>. Only HTTP urls are valid, of course.

.. _command-web-fetch:

fetch <url>
  Returns the contents of <url>, or as much as is configured in supybot.plugins.Web.fetch.maximum. If that configuration variable is set to 0, this command will be effectively disabled.

.. _command-web-headers:

headers <url>
  Returns the HTTP headers of <url>. Only HTTP urls are valid, of course.

.. _command-web-location:

location <url>
  If the <url> is redirected to another page, returns the URL of that page. This works even if there are multiple redirects. Only HTTP urls are valid. Useful to "un-tinify" URLs.

.. _command-web-size:

size <url>
  Returns the Content-Length header of <url>. Only HTTP urls are valid, of course.

.. _command-web-title:

title [--no-filter] <url>
  Returns the HTML <title>...</title> of a URL. If --no-filter is given, the bot won't strip special chars (action, DCC, ...).

.. _command-web-urlquote:

urlquote <text>
  Returns the URL quoted form of the text.

.. _command-web-urlunquote:

urlunquote <text>
  Returns the text un-URL quoted.

.. _conf-Web:

Configuration
-------------

.. _conf-supybot.plugins.Web.checkIgnored:


supybot.plugins.Web.checkIgnored
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the title snarfer checks if the author of a message is ignored.

.. _conf-supybot.plugins.Web.fetch:


supybot.plugins.Web.fetch
  This is a group of:

  .. _conf-supybot.plugins.Web.fetch.maximum:


  supybot.plugins.Web.fetch.maximum
    This config variable defaults to "0", is not network-specific, and is  not channel-specific.

    Determines the maximum number of bytes the bot will download via the 'fetch' command in this plugin.

  .. _conf-supybot.plugins.Web.fetch.timeout:


  supybot.plugins.Web.fetch.timeout
    This config variable defaults to "5", is not network-specific, and is  not channel-specific.

    Determines the maximum number of seconds the bot will wait for the site to respond, when using the 'fetch' command in this plugin. If 0, will use socket.defaulttimeout

.. _conf-supybot.plugins.Web.nonSnarfingRegexp:


supybot.plugins.Web.nonSnarfingRegexp
  This config variable defaults to "", is network-specific, and is  channel-specific.

  Determines what URLs matching the given regexp will not be snarfed. Give the empty string if you have no URLs that you'd like to exclude from being snarfed.

.. _conf-supybot.plugins.Web.public:


supybot.plugins.Web.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Web.snarfMultipleUrls:


supybot.plugins.Web.snarfMultipleUrls
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the title snarfer will query all URLs in a message, or only the first one.

.. _conf-supybot.plugins.Web.snarferPrefix:


supybot.plugins.Web.snarferPrefix
  This config variable defaults to "Title:", is network-specific, and is  channel-specific.

  Determines the string used at before a web page's title.

.. _conf-supybot.plugins.Web.snarferReportIOExceptions:


supybot.plugins.Web.snarferReportIOExceptions
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will notfiy the user about network exceptions like hostnotfound, timeout ....

.. _conf-supybot.plugins.Web.snarferShowDomain:


supybot.plugins.Web.snarferShowDomain
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether domain names should be displayed by the title snarfer.

.. _conf-supybot.plugins.Web.snarferShowTargetDomain:


supybot.plugins.Web.snarferShowTargetDomain
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the domain name displayed by the snarfer will be the original one (posted on IRC) or the target one (got after following redirects, if any).

.. _conf-supybot.plugins.Web.timeout:


supybot.plugins.Web.timeout
  This config variable defaults to "5", is not network-specific, and is  not channel-specific.

  Determines the maximum number of seconds the bot will wait for the site to respond, when using a command in this plugin other than 'fetch'. If 0, will use socket.defaulttimeout

.. _conf-supybot.plugins.Web.titleSnarfer:


supybot.plugins.Web.titleSnarfer
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will output the HTML title of URLs it sees in the channel.

.. _conf-supybot.plugins.Web.urlWhitelist:


supybot.plugins.Web.urlWhitelist
  This config variable defaults to " ", is not network-specific, and is  not channel-specific.

  If set, bot will only fetch data from urls in the whitelist, i.e. starting with http://domain/optionalpath/. This will apply to all commands that retrieve data from user-supplied URLs, including fetch, headers, title, doctype.

