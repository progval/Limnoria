.. _plugin-SedRegex:

Documentation for the SedRegex plugin for Supybot
=================================================

Purpose
-------
History replacer using sed-style expressions.

Usage
-----
Enable SedRegex on the desired channels:
``config channel #yourchannel plugins.sedregex.enable True``
After enabling SedRegex, typing a regex in the form
``s/text/replacement/`` will make the bot announce replacements.

::

   20:24 <jlu5> helli world
   20:24 <jlu5> s/i/o/
   20:24 <Limnoria> jlu5 meant to say: hello world

You can also do ``othernick: s/text/replacement/`` to only replace
messages from a certain user. Supybot ignores are respected by the plugin,
and messages from ignored users will only be considered if their nick is
explicitly given.

Regex flags
^^^^^^^^^^^

The following regex flags (i.e. the ``g`` in ``s/abc/def/g``, etc.) are
supported:

- ``i``: case insensitive replacement
- ``g``: replace all occurences of the original text
- ``s``: *(custom flag specific to this plugin)* replace only messages
  from the caller

.. _conf-SedRegex:

Configuration
-------------

.. _conf-supybot.plugins.SedRegex.boldReplacementText:


supybot.plugins.SedRegex.boldReplacementText
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Should the replacement text be bolded?

.. _conf-supybot.plugins.SedRegex.displayErrors:


supybot.plugins.SedRegex.displayErrors
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Should errors be displayed?

.. _conf-supybot.plugins.SedRegex.enable:


supybot.plugins.SedRegex.enable
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Should Perl/sed-style regex replacing work in this channel?

.. _conf-supybot.plugins.SedRegex.ignoreRegex:


supybot.plugins.SedRegex.ignoreRegex
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Should Perl/sed regex replacing ignore messages which look like valid regex?

.. _conf-supybot.plugins.SedRegex.processTimeout:


supybot.plugins.SedRegex.processTimeout
  This config variable defaults to "0.5", is not network-specific, and is  not channel-specific.

  Sets the timeout when processing a single regexp. The default should be adequate unless you have a busy or low-powered system that cannot process regexps quickly enough. However, you will not want to set this value too high as that would make your bot vulnerable to ReDoS attacks.

.. _conf-supybot.plugins.SedRegex.public:


supybot.plugins.SedRegex.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

