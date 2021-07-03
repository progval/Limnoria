.. _plugin-DDG:

Documentation for the DDG plugin for Supybot
============================================

Purpose
-------
Searches for results on DuckDuckGo's web search.

Usage
-----
Searches for results on DuckDuckGo.

Example::

    <+jlu5> %ddg search eiffel tower
    <@Atlas> The Eiffel Tower is an iron lattice tower located on the Champ de Mars in Paris. It was named after the engineer Gustave Eiffel, whose company designed and built the tower. - <https://en.wikipedia.org/wiki/Eiffel_Tower>

.. _commands-DDG:

Commands
--------
.. _command-ddg-search:

search <text>
  Searches for <text> on DuckDuckGo's web search.

.. _conf-DDG:

Configuration
-------------

.. _conf-supybot.plugins.DDG.maxResults:


supybot.plugins.DDG.maxResults
  This config variable defaults to "4", is network-specific, and is  channel-specific.

  Determines the maximum number of results the bot will respond with.

.. _conf-supybot.plugins.DDG.public:


supybot.plugins.DDG.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.DDG.region:


supybot.plugins.DDG.region
  This config variable defaults to "", is network-specific, and is  channel-specific.

  Set the DDG search region to return results for the language/country of your choice. E.g. 'us-en' for United States. https://duckduckgo.com/params

.. _conf-supybot.plugins.DDG.searchFilter:


supybot.plugins.DDG.searchFilter
  This config variable defaults to "moderate", is network-specific, and is  channel-specific.

  Determines what level of search filtering to use by default. 'active' - most filtering, 'moderate' - default filtering, 'off' - no filtering  Valid strings: active, moderate, and off.

.. _conf-supybot.plugins.DDG.showSnippet:


supybot.plugins.DDG.showSnippet
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether the bot will show a snippet of each resulting link. If False, it will show the title of the link instead.

