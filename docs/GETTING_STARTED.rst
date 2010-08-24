============================
Getting Started with Supybot
============================

Introduction
------------

Ok, so you've decided to try out Supybot.  That's great!  The more people who
use Supybot, the more people can submit bugs and help us to make it the best
IRC bot in the world :)

You should have already read through our install document (if you had to
manually install) before reading any further.  Now we'll give you a whirlwind
tour as to how you can get Supybot setup and use Supybot effectively.

Initial Setup
-------------

Now that you have Supybot installed, you'll want to get it running.  The first
thing you'll want to do is run supybot-wizard.  Before running supybot-wizard,
you should be in the directory in which you want your bot-related files to
reside.  The wizard will walk you through setting up a base config file for
your Supybot.  Once you've completed the wizard, you will have a config file
called botname.conf.  In order to get the bot running, run ``supybot
botname.conf``.

Listing Commands
----------------

Ok, so let's assume your bot connected to the server and joined the channels
you told it to join.  For now we'll assume you named your bot 'supybot' (you
probably didn't, but it'll make it much clearer in the examples that follow to
assume that you did).  We'll also assume that you told it to join #channel (a
nice generic name for a channel, isn't it? :))  So what do you do with this
bot that you just made to join your channel?  Try this in the channel::

    supybot: list

Replacing 'supybot' with the actual name you picked for your bot, of course.
Your bot should reply with a list of the plugins he currently has loaded.  At
least `Admin`, `Channel`, `Config`, `Misc`, `Owner`, and `User` should be
there; if you used supybot-wizard to create your configuration file you may
have many more plugins loaded.  The list command can also be used to list the
commands in a given plugin::

    supybot: list Misc

will list all the commands in the `Misc` plugin.  If you want to see the help
for any command, just use the help command::

    supybot: help help
    supybot: help list
    supybot: help load

Sometimes more than one plugin will have a given command; for instance, the
"list" command exists in both the Misc and Config plugins (both loaded by
default).  List, in this case, defaults to the Misc plugin, but you may want
to get the help for the list command in the Config plugin.  In that case,
you'll want to give your command like this::

    supybot: help config list

Anytime your bot tells you that a given command is defined in several plugins,
you'll want to use this syntax ("plugin command") to disambiguate which
plugin's command you wish to call.  For instance, if you wanted to call the
Config plugin's list command, then you'd need to say::

    supybot: config list

Rather than just 'list'.

Making Supybot Recognize You
----------------------------

If you ran the wizard, then it is almost certainly the case that you already
added an owner user for yourself.  If not, however, you can add one via the
handy-dandy 'supybot-adduser' script.  You'll want to run it while the bot is
not running (otherwise it could overwrite supybot-adduser's changes to your
user database before you get a chance to reload them).  Just follow the
prompts, and when it asks if you want to give the user any capabilities, say
yes and then give yourself the 'owner' capability, restart the bot and you'll
be ready to load some plugins!

Now, in order for the bot to recognize you as your owner user, you'll have to
identify with the bot.  Open up a query window in your irc client ('/query'
should do it; if not, just know that you can't identify in a channel because
it requires sending your password to the bot).  Then type this::

    help identify

And follow the instructions; the command you send will probably look like
this, with 'myowneruser' and 'myuserpassword' replaced::

    identify myowneruser myuserpassword

The bot will tell you that 'The operation succeeded' if you got the right name
and password.  Now that you're identified, you can do anything that requires
any privilege: that includes all the commands in the Owner and Admin plugins,
which you may want to take a look at (using the list and help commands, of
course).  One command in particular that you might want to use (it's from the
User plugin) is the 'hostmask add' command: it lets you add a hostmask to your
user record so the bot recognizes you by your hostmask instead of requiring
you always to identify with it before it recognizes you.  Use the 'help'
command to see how this command works.  Here's how I often use it::

    hostmask add myuser [hostmask] mypassword

You may not have seen that '[hostmask]' syntax before.  Supybot allows nested
commands, which means that any command's output can be nested as an argument
to another command.  The hostmask command from the Misc plugin returns the
hostmask of a given nick, but if given no arguments, it returns the hostmask
of the person giving the command. So the command above adds the hostmask I'm
currently using to my user's list of recognized hostmasks.  I'm only required
to give mypassword if I'm not already identified with the bot.

Loading Plugins
---------------

Let's take a look at loading other plugins.  If you didn't use supybot-wizard,
though, you might do well to try it before playing around with loading plugins
yourself: each plugin has its own configure function that the wizard uses to
setup the appropriate registry entries if the plugin requires any.

If you do want to play around with loading plugins, you're going to need to
have the owner capability.

Remember earlier when I told you to try ``help load``?  That's the very command
you'll be using. Basically, if you want to load, say, the Games plugin, then
``load Games``.  Simple, right?  If you need a list of the plugins you can load,
you'll have to list the directory the plugins are in (using whatever command
is appropriate for your operating system, either 'ls' or 'dir').

Getting More From Your Supybot
------------------------------

Another command you might find yourself needing somewhat often is the 'more'
command.  The IRC protocol limits messages to 512 bytes, 60 or so of which
must be devoted to some bookkeeping.  Sometimes, however, Supybot wants to
send a message that's longer than that.  What it does, then, is break it into
"chunks" and send the first one, following it with ``(X more messages)`` where
X is how many more chunks there are.  To get to these chunks, use the `more`
command.  One way to try is to look at the default value of
`supybot.replies.genericNoCapability` -- it's so long that it'll stretch
across two messages::

    <jemfinch|lambda> $config default
                      supybot.replies.genericNoCapability
    <lambdaman> jemfinch|lambda: You're missing some capability
                you need. This could be because you actually
                possess the anti-capability for the capability
                that's required of you, or because the channel
                provides that anti-capability by default, or
                because the global capabilities include that
                anti-capability. Or, it could be because the
                channel or the global defaultAllow is set to
                False, meaning (1 more message)
    <jemfinch|lambda> $more
    <lambdaman> jemfinch|lambda: that no commands are allowed
                unless explicitly in your capabilities. Either
                way, you can't do what you want to do.

So basically, the bot keeps, for each person it sees, a list of "chunks" which
are "released" one at a time by the `more` command.  In fact, you can even get
the more chunks for another user: if you want to see another chunk in the last
command jemfinch gave, for instance, you would just say `more jemfinch` after
which, his "chunks" now belong to you.  So, you would just need to say `more`
to continue seeing chunks from jemfinch's initial command.

Final Word
----------

You should now have a solid foundation for using Supybot.  You can use the
`list` command to see what plugins your bot has loaded and what commands are
in those plugins; you can use the 'help' command to see how to use a specific
command, and you can use the 'more' command to continue a long response from
the bot.  With these three commands, you should have a strong basis with which
to discover the rest of the features of Supybot!

Do be sure to read our other documentation and make use of the resources we
provide for assistance; this website and, of course, #supybot on
irc.freenode.net if you run into any trouble!
