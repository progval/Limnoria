==========================
Frequently Asked Questions
==========================

How do I make my Supybot connect to multiple servers?

  Just use the `connect` command in the `Network` plugin.

Why does my bot not recognize me or tell me that I don't have the
'owner' capability?

  Because you've not given it anything to recognize you from!

  You'll need to identify with the bot (``help identify`` to see how
  that works) or add your hostmask to your user record (``help hostmask
  add`` to see how that works) for it to know that you're you.

  You may wish to note that addhostmask can accept a password; rather
  than identify, you can send the command::

    hostmask add myOwnerUser [hostmask] myOwnerUserPassword

  and the bot will add your current hostmask to your owner user (of
  course, you should change myOwnerUser and myOwnerUserPassword
  appropriately for your bot).

What is a hostmask?

  Each user on IRC is uniquely identified by a string which we call a
  `hostmask`. The IRC RFC refers to it as a prefix. Either way, it
  consists of a nick, a user, and a host, in the form
  ``nick!user@host``.  If your Supybot complains that something you've
  given to it isn't a hostmask, make sure that you have those three
  components and that they're joined in the appropriate manner.

My bot can't handle nicks with brackets in them!

  It always complains about something not being a valid command, or
  about spurious or missing right brackets, etc.

  You should quote arguments (using double quotes, like this:
  ``"foo[bar]"``) that have brackets in them that you don't wish to be
  evaluated as nested commands. Otherwise, you can turn off nested
  commands by setting `supybot.commands.nested` to False, or change the
  brackets that nest commands, by setting
  `supybot.commands.nested.brackets` to some other value (like ``<>``,
  which can't occur in IRC nicks).

I added an alias, but it doesn't work!

  Take a look at ``help <alias you added>``. If the alias the bot has
  listed doesn't match what you're giving it, chances are you need to
  quote your alias in order for the brackets not to be evaluated. For
  instance, if you're adding an alias to give you a link to your
  homepage, you need to say::

    alias add mylink "format concat http://my.host.com/ [urlquote $1]"

  and not::

    alias add mylink format concat http://my.host.com/ [urlquote $1]

  The first version works; the second version will always return the
  same url.

What does 'lobotomized' mean?

  I see this word in commands and in my `channels.conf`, but I don't
  know what it means. What does Supybot mean when it says "lobotomized"?

  A lobotomy is an operation that removes the frontal lobe of the brain,
  the part that does most of a person's thinking. To "lobotomize" a bot
  is to tell it to stop thinking--thus, a lobotomized bot will not
  respond to anything said by anyone other than its owner in whichever
  channels it is lobotomized.

  The term is certainly suboptimal, but remains in use because it was
  historically used by certain other IRC bots, and we wanted to ease the
  transition to Supybot from those bots by reusing as much terminology
  as possible.

Is there a way to load all the plugins Supybot has?

  No, there isn't. Even if there were, some plugins conflict with other
  plugins, so it wouldn't make much sense to load them. For instance,
  what would a bot do with `Factoids`, `MoobotFactoids`, and `Infobot`
  all loaded? Probably just annoy people :)

  If you want to know more about the plugins that are available, check
  out our `plugin index`_ at our `website`_.

Is there a command that can tell me what capability another command
requires?

  No, there isn't, and there probably never will be.

  Commands have the flexibility to check any capabilities they wish to
  check; while this flexibility is useful, it also makes it hard to
  guess what capability a certain command requires. We could make a
  solution that would work in a large majority of cases, but it wouldn't
  (and couldn't!) be absolutely correct in all circumstances, and since
  we're anal and we hate doing things halfway, we probably won't ever
  add this partial solution.

Why doesn't `Karma` seem to work for me?

  `Karma`, by default, doesn't acknowledge karma updates. If you check
  the karma of whatever you increased/decreased, you'll note that your
  increment or decrement still took place. If you'd rather `Karma`
  acknowledge karma updates, change the `supybot.plugins.Karma.response`
  configuration variable to "On".

Why won't Supybot respond to private messages?

  The most likely cause is that you are running your bot on the Freenode
  network. Around Sept. 2005, Freenode added a user mode which
  registered user could set that `blocks`_ private messages from
  unregistered users.  So, the reason you aren't seeing a response from
  your Supybot is:

  * Your Supybot is not registered with NickServ, you are registered,
    and you have set the +E user mode for yourself.

  * or you have registered your Supybot with NickServ, you aren't
    registered, and your Supybot has the +E user mode set.

Can users with the "admin" capability change configuration?

  Currently, no.  Feel free to make your case to us as to why a certain
  configuration variable should only require the `admin` capability
  instead of the `owner` capability, and if we agree with you, we'll
  change it for the next release.

How can I make my Supybot log my IRC channel?

  To log all the channels your Supybot is in, simply load the
  `ChannelLogger` plugin, which is included in the main distribution.

How do I find out channel modes?

  I want to know who's an op in a certain channel, or who's voiced, or
  what the modes on the channel are.  How do I do that?

  Everything you need is kept in a `ChannelState` object in an
  `IrcState` object in the `Irc` object your plugin is given.  To see
  the ops in a given channel, for instance, you would do this::

    irc.state.channels['#channel'].ops

  To see a dictionary mapping mode chars to values (if any), you would
  do this::

    irc.state.channels['#channel'].modes

  From there, things should be self-evident.

Can Supybot connect through a proxy server?

  Supybot is not designed to be allowed to connect to an IRC server via
  a proxy server, however there are transparent proxy server helpers
  like tsocks_ that are designed to proxy-enable all network
  applications, and Supybot does work with these.

Why can't Supybot find the plugin I want to load?

  Why does my bot say that 'No plugin "foo" exists.' when I try to load
  the foo plugin?

  First, make sure you are typing the plugin name correctly.  ``@load
  foo`` is not the same as ``@load Foo`` [#plugindir]_.  If that is not
  the problem, 

.. [#plugindir] Yes, it used to be the same, but then we moved to using
   directories for plugins instead of a single file.  Apparently, that
   makes a difference to Python.

I've found a bug, what do I do?

  Submit your bug on `Sourceforge`_ through our `project page`_.

Why does @tell command from Later deliver messages immediatly?

  This is probably because the @tell command defaults to the one in the Misc
  plugin, which is intended to do this. Consider using ``@later tell``
  instead, or change the default with ``@owner defaultplugin``.

Is Python installed?

  I run Windows, and I'm not sure if Python is installed on my computer.
  How can I find out for sure?

  Python isn't commonly installed by default on Windows computers.  If
  you don't see it in your start menu somewhere, it's probably not
  installed.

  The easiest way to find out if Python is installed is simply to
  `download it`_ and try to install it.  If the installer complains, you
  probably already have it installed.  If it doesn't, well, now you have
  Python installed.

.. _plugin index: http://supybot.com/plugins.html
.. _website: http://supybot.com/
.. _blocks: http://freenode.net/faq.shtml#blockingmessages
.. _tsocks: http://tsocks.sourceforge.net
.. _Sourceforge: http://sourceforge.net/
.. _project page: http://sourceforge.net/projects/supybot
.. _download it: http://python.org/download/
