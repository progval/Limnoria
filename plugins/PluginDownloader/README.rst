.. _plugin-PluginDownloader:

Documentation for the PluginDownloader plugin for Supybot
=========================================================

Purpose
-------
This plugin allows you to quickly download and install a plugin from other 
repositories.

Usage
-----
This plugin allows you to install unofficial plugins from
multiple repositories easily. Use the "repolist" command to see list of
available repositories and "repolist <repository>" to list plugins,
which are available in that repository. When you want to install a plugin,
just run command "install <repository> <plugin>".

First start by using the `plugindownloader repolist` command to see the
available repositories.

To see the plugins inside repository, use command
`plugindownloader repolist <repository>`

When you see anything interesting, you can use
`plugindownloader info <repository> <plugin>` to see what the plugin is
for.

And finally to install the plugin,
`plugindownloader install <repository> <plugin>`.

Examples
^^^^^^^^

::

    < Mikaela> @load PluginDownloader
    < Limnoria> Ok.
    < Mikaela> @plugindownloader repolist
    < Limnoria> Antibody, jlu5, Hoaas, Iota, ProgVal, SpiderDave, boombot, code4lib, code4lib-edsu, code4lib-snapshot, doorbot, frumious, jonimoose, mailed-notifier, mtughan-weather, nanotube-bitcoin, nyuszika7h, nyuszika7h-old, pingdom, quantumlemur, resistivecorpse, scrum, skgsergio, stepnem
    < Mikaela> @plugindownloader repolist ProgVal
    < Limnoria> AttackProtector, AutoTrans, Biography, Brainfuck, ChannelStatus, Cleverbot, Coffee, Coinpan, Debian, ERepublik, Eureka, Fortune, GUI, GitHub, Glob2Chan, GoodFrench, I18nPlaceholder, IMDb, IgnoreNonVoice, Iwant, Kickme, LimnoriaChan, LinkRelay, ListEmpty, Listener, Markovgen, MegaHAL, MilleBornes, NoLatin1, NoisyKarma, OEIS, PPP, PingTime, Pinglist, RateLimit, Rbls, Redmine, Scheme, Seeks, (1 more message)
    < Mikaela> more
    < Limnoria> SilencePlugin, StdoutCapture, Sudo, SupyML, SupySandbox, TWSS, Trigger, Trivia, Twitter, TwitterStream, Untiny, Variables, WebDoc, WebLogs, WebStats, Website, WikiTrans, Wikipedia, WunderWeather
    < Mikaela> @plugindownloader info ProgVal Wikipedia
    < Limnoria> Grabs data from Wikipedia.
    < Mikaela> @plugindownloader install ProgVal Wikipedia
    < Limnoria> Ok.
    < Mikaela> @load Wikipedia
    < Limnoria> Ok.

.. _commands-PluginDownloader:

Commands
--------
.. _command-plugindownloader-info:

info <repository> <plugin>
  Displays informations on the <plugin> in the <repository>.

.. _command-plugindownloader-install:

install <repository> <plugin>
  Downloads and installs the <plugin> from the <repository>.

.. _command-plugindownloader-repolist:

repolist [<repository>]
  Displays the list of plugins in the <repository>. If <repository> is not given, returns a list of available repositories.

.. _conf-PluginDownloader:

Configuration
-------------

.. _conf-supybot.plugins.PluginDownloader.public:


supybot.plugins.PluginDownloader.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

