.. _plugin-Google:

Documentation for the Google plugin for Supybot
===============================================

Purpose
-------
Accesses Google for various things.

Usage
-----
This is a simple plugin to provide access to the Google services we
all know and love from our favorite IRC bot.

1. google

   Searches for a string and gives you 3 results from Google search
   ``!google something``

2. lucky

   Return the first result (Google's "I'm Feeling Lucky" search)
   ``!lucky something``

3. calc

   Does mathematic calculations
   ``!calc 5+4``

4. translate

   Translates a string
   ``!translate en ar test``

Check: `Supported language codes`_

.. _Supported language codes: <https://cloud.google.com/translate/v2/using_rest#language-params>`

.. _commands-Google:

Commands
--------
.. _command-google-cache:

cache <url>
  Returns a link to the cached version of <url> if it is available.

.. _command-google-calc:

calc <expression>
  Uses Google's calculator to calculate the value of <expression>.

.. _command-google-fight:

fight <search string> <search string> [<search string> ...]
  Returns the results of each search, in order, from greatest number of results to least.

.. _command-google-google:

google <search> [--{filter,language} <value>]
  Searches google.com for the given string. As many results as can fit are included. --language accepts a language abbreviation; --filter accepts a filtering level ('active', 'moderate', 'off').

.. _command-google-lucky:

lucky [--snippet] <search>
  Does a google search, but only returns the first result. If option --snippet is given, returns also the page text snippet.

.. _command-google-phonebook:

phonebook <phone number>
  Looks <phone number> up on Google.

.. _command-google-translate:

translate <source language> [to] <target language> <text>
  Returns <text> translated from <source language> into <target language>. <source language> and <target language> take language codes (not language names), which are listed here: https://cloud.google.com/translate/docs/languages

.. _conf-Google:

Configuration
-------------

.. _conf-supybot.plugins.Google.baseUrl:


supybot.plugins.Google.baseUrl
  This config variable defaults to "google.com", is network-specific, and is  channel-specific.

  Determines the base URL used for requests.

.. _conf-supybot.plugins.Google.bold:


supybot.plugins.Google.bold
  This config variable defaults to "True", is network-specific, and is  channel-specific.

  Determines whether results are bolded.

.. _conf-supybot.plugins.Google.colorfulFilter:


supybot.plugins.Google.colorfulFilter
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the word 'google' in the bot's output will be made colorful (like Google's logo).

.. _conf-supybot.plugins.Google.defaultLanguage:


supybot.plugins.Google.defaultLanguage
  This config variable defaults to "lang_en", is network-specific, and is  channel-specific.

  Determines what default language is used in searches. If left empty, no specific language will be requested.  Valid strings: lang_af, lang_sq, lang_am, lang_ar, lang_hy, lang_az, lang_eu, lang_be, lang_bn, lang_bg, lang_my, lang_ca, lang_zh, lang_zh-CN, lang_zh-TW, lang_hr, lang_cs, lang_da, lang_dv, lang_nl, lang_en, lang_eo, lang_et, lang_tl, lang_fi, lang_fr, lang_gl, lang_ka, lang_de, lang_el, lang_gu, lang_iw, lang_hi, lang_hu, lang_is, lang_id, lang_iu, lang_it, lang_ja, lang_kn, lang_kk, lang_km, lang_ko, lang_ku, lang_ky, lang_lo, lang_lv, lang_lt, lang_mk, lang_ms, lang_ml, lang_mt, lang_mr, lang_mn, lang_ne, lang_no, lang_or, lang_ps, lang_fa, lang_pl, lang_pt-PT, lang_pa, lang_ro, lang_ru, lang_sa, lang_sr, lang_sd, lang_si, lang_sk, lang_sl, lang_es, lang_sv, lang_tg, lang_ta, lang_tl, lang_te, lang_th, lang_bo, lang_tr, lang_uk, lang_ur, lang_uz, lang_ug, lang_vi, and lang_auto.

.. _conf-supybot.plugins.Google.maximumResults:


supybot.plugins.Google.maximumResults
  This config variable defaults to "3", is network-specific, and is  channel-specific.

  Determines the maximum number of results returned from the google command.

.. _conf-supybot.plugins.Google.oneToOne:


supybot.plugins.Google.oneToOne
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether results are sent in different lines or all in the same one.

.. _conf-supybot.plugins.Google.public:


supybot.plugins.Google.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

.. _conf-supybot.plugins.Google.referer:


supybot.plugins.Google.referer
  This config variable defaults to "", is not network-specific, and is  not channel-specific.

  Determines the URL that will be sent to Google for the Referer field of the search requests. If this value is empty, a Referer will be generated in the following format: http://$server/$botName

.. _conf-supybot.plugins.Google.searchFilter:


supybot.plugins.Google.searchFilter
  This config variable defaults to "moderate", is network-specific, and is  channel-specific.

  Determines what level of search filtering to use by default. 'active' - most filtering, 'moderate' - default filtering, 'off' - no filtering  Valid strings: active, moderate, and off.

.. _conf-supybot.plugins.Google.searchSnarfer:


supybot.plugins.Google.searchSnarfer
  This config variable defaults to "False", is network-specific, and is  channel-specific.

  Determines whether the search snarfer is enabled. If so, messages (even unaddressed ones) beginning with the word 'google' will result in the first URL Google returns being sent to the channel.

