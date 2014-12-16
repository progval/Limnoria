This plugin allows you to quickly download and install a plugin from other repositories.

Usage
=====

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
--------

```
< Mikaela> @load PluginDownloader
< Limnoria> Ok.
< Mikaela> @plugindownloader repolist
< Limnoria> Antibody, GLolol, Hoaas, Iota, ProgVal, SpiderDave, boombot, code4lib, code4lib-edsu, code4lib-snapshot, doorbot, frumious, jonimoose, mailed-notifier, mtughan-weather, nanotube-bitcoin, nyuszika7h, nyuszika7h-old, pingdom, quantumlemur, resistivecorpse, scrum, skgsergio, stepnem
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
```
