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
.. _command-Web-doctype:

doctype <url>
  Returns the DOCTYPE string of <url>. Only HTTP urls are valid, of course.

.. _command-Web-fetch:

fetch <url>
  Returns the contents of <url>, or as much as is configured in supybot.plugins.Web.fetch.maximum. If that configuration variable is set to 0, this command will be effectively disabled.

.. _command-Web-headers:

headers <url>
  Returns the HTTP headers of <url>. Only HTTP urls are valid, of course.

.. _command-Web-location:

location <url>
  If the <url> is redirected to another page, returns the URL of that page. This works even if there are multiple redirects. Only HTTP urls are valid. Useful to "un-tinify" URLs.

.. _command-Web-size:

size <url>
  Returns the Content-Length header of <url>. Only HTTP urls are valid, of course.

.. _command-Web-title:

title [--no-filter] <url>
  Returns the HTML <title>...</title> of a URL. If --no-filter is given, the bot won't strip special chars (action, DCC, ...).

.. _command-Web-urlquote:

urlquote <text>
  Returns the URL quoted form of the text.

.. _command-Web-urlunquote:

urlunquote <text>
  Returns the text un-URL quoted.

Configuration
-------------
supybot.plugins.Web.checkIgnored
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the title snarfer checks if the author of a message is ignored.

supybot.plugins.Web.nonSnarfingRegexp
  This config variable defaults to "", is network-specific, and is  channel-specific.

  Determines what URLs matching the given regexp will not be snarfed. Give the empty string if you have no URLs that you'd like to exclude from being snarfed.

supybot.plugins.Web.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

supybot.plugins.Web.snarfMultipleUrls
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the title snarfer will query all URLs in a message, or only the first one.

supybot.plugins.Web.snarferPrefix
  This config variable defaults to "Title:", is network-specific, and is  channel-specific.

  Determines the string used at before a web page's title.

supybot.plugins.Web.snarferReportIOExceptions
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will notfiy the user about network exceptions like hostnotfound, timeout ....

supybot.plugins.Web.snarferShowDomain
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether domain names should be displayed by the title snarfer.

supybot.plugins.Web.snarferShowTargetDomain
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the domain name displayed by the snarfer will be the original one (posted on IRC) or the target one (got after following redirects, if any).

supybot.plugins.Web.timeout
  This config variable defaults to "5", is not network-specific, and is  not channel-specific.

  Determines the maximum number of seconds the bot will wait for the site to respond, when using a command in this plugin other than 'fetch'. If 0, will use socket.defaulttimeout

supybot.plugins.Web.titleSnarfer
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the bot will output the HTML title of URLs it sees in the channel.

supybot.plugins.Web.urlWhitelist
  This config variable defaults to " ", is not network-specific, and is  not channel-specific.

  If set, bot will only fetch data from urls in the whitelist, i.e. starting with http://domain/optionalpath/. This will apply to all commands that retrieve data from user-supplied URLs, including fetch, headers, title, doctype.

