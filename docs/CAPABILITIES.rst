============
Capabilities
============

Introduction
------------

Ok, some explanation of the capabilities system is probably in order.  With
most IRC bots (including the ones I've written myself prior to this one) "what
a user can do" is set in one of two ways.  On the *really* simple bots, each
user has a numeric "level" and commands check to see if a user has a "high
enough level" to perform some operation.  On bots that are slightly more
complicated, users have a list of "flags" whose meanings are hardcoded, and the
bot checks to see if a user possesses the necessary flag before performing some
operation.  Both methods, IMO, are rather arbitrary, and force the user and the
programmer to be unduly confined to less expressive constructs.

This bot is different.  Every user has a set of "capabilities" that is
consulted every time they give the bot a command.  Commands, rather than
checking for a user level of 100, or checking if the user has an 'o' flag, are
instead able to check if a user has the 'owner' capability.  At this point such
a difference might not seem revolutionary, but at least we can already tell
that this method is self-documenting, and easier for users and developers to
understand what's truly going on.

User Capabilities
-----------------
What the heck can these capabilities DO?

If that was all, well, the capability system would be *cool*, but not many
people would say it was *awesome*.  But it **is** awesome!  Several things are
happening behind the scenes that make it awesome, and these are things that
couldn't happen if the bot was using numeric userlevels or single-character
flags.  First, whenever a user issues the bot a command, the command dispatcher
checks to make sure the user doesn't have the "anticapability" for that
command.  An anticapability is a capability that, instead of saying "what a
user can do", says what a user *cannot* do.  It's formed rather simply by
adding a dash ('-') to the beginning of a capability; 'rot13' is a capability,
and '-rot13' is an anticapability.

Anyway, when a user issues the bot a command, perhaps 'calc' or 'help', the bot
first checks to make sure the user doesn't have the '-calc' or the '-help'
(anti)capabilities before even considering responding to the user.  So commands
can be turned on or off on a *per user* basis, offering fine-grained control
not often (if at all!) seen in other bots.  This can be further refined by
limiting the (anti)capability to a command in a specific plugin or even an
entire plugin.  For example, the rot13 command is in the Filter plugin.  If a
user should be able to use another rot13 command, but not the one in the Format
plugin, they would simply need to be given '-Format.rot13' anticapability.
Similarly, if a user were to be banned from using the Filter plugin altogether,
they would simply need to be given the '-Filter' anticapability.

Channel Capabilities
--------------------
What if #linux wants completely different capabilities from #windows?

But that's not all!  The capabilities system also supports *channel*
capabilities, which are capabilities that only apply to a specific channel;
they're of the form '#channel,capability'.  Whenever a user issues a command to
the bot in a channel, the command dispatcher also checks to make sure the user
doesn't have the anticapability for that command *in that channel*, and if the
user does, the bot won't respond to the user in the channel.  Thus now, in
addition to having the ability to turn individual commands on or off for an
individual user, we can now turn commands on or off for an individual user on
an individual channel!

So when a user 'foo' sends a command 'bar' to the bot on channel '#baz', first
the bot checks to see if the user has the anticapability for the command by
itself, '-bar'.  If so, it errors right then and there, telling the user that
he lacks the 'bar' capability.  If the user doesn't have that anticapability,
then the bot checks to see if the user issued the command over a channel, and
if so, checks to see if the user has the antichannelcapability for that
command, '#baz,-bar'.  If so, again, he tells the user that he lacks the 'bar'
capability.  If neither of these anticapabilities are present, then the bot
just responds to the user like normal.

Default Capabilities
--------------------
So what capabilities am I dealing with already?

There are several default capabilities the bot uses.  The most important of
these is the 'owner' capability.  This capability allows the person having it
to use *any* command.  It's best to keep this capability reserved to people who
actually have access to the shell the bot is running on.  It's so important, in
fact, that the bot will not allow you to add it with a command--you'll have you
edit the users file directly to give it to someone.

There is also the 'admin' capability for non-owners that are highly trusted to
administer the bot appropriately.  They can do things such as change the bot's
nick, cause the bot to ignore a given user, make the bot join or part channels,
etc. They generally cannot do administration related to channels, which is
reserved for people with the next capability.

People who are to administer channels with the bot should have the
'#channel,op' capability--whatever channel they are to administrate, they
should have that channel capability for 'op'.  For example, since I want
inkedmn to be an administrator in #supybot, I'll give him the '#supybot,op'
capability.  This is in addition to his 'admin' capability, since the 'admin'
capability doesn't give the person having it control over channels.
'#channel,op' is used for such things as giving/receiving ops, kickbanning
people, lobotomizing the bot, ignoring users in the channel, and managing the
channel capabilities. The '#channel,op' capability is also basically the
equivalent of the 'owner' capability for capabilities involving
#channel--basically anyone with the #channel,op capability is considered to
have all positive capabilities and no negative capabilities for #channel.

One other globally important capability exists: 'trusted'.  This is a command
that basically says "This user can be trusted not to try and crash the bot." It
allows users to call commands like 'icalc' in the 'Math' plugin, which can
cause the bot to begin a calculation that could potentially never return (a
calculation like '10**10**10**10'). Another command that requires the 'trusted'
capability is the 're' command in the 'Utilities' plugin, which (due to the
regular expression implementation in Python (and any other language that uses
NFA regular expressions, like Perl or Ruby or Lua or ...) which can allow a
regular expression to take exponential time to process).  Consider what would
happen if someone gave the bot the command 're [format join "" s/./ [dict go]
/] [dict go]'  It would basically replace every character in the output of
'dict go' (14,896 characters!) with the entire output of 'dict go', resulting
in 221MB of memory allocated!  And that's not even the worst example!

Final Word
----------

From a programmer's perspective, capabilties are flexible and easy to use.  Any
command can check if a user has any capability, even ones not thought of when
the bot was originally written. Plugins can easily add their own
capabilities--it's as easy as just checking for a capability and documenting
somewhere that a user needs that capability to do something.

From an user's perspective, capabilities remove a lot of the mystery and
esotery of bot control, in addition to giving a bot owner absolutely
finegrained control over what users are allowed to do with the bot.
Additionally, defaults can be set by the bot owner for both individual channels
and for the bot as a whole, letting an end-user set the policy he wants the bot
to follow for users that haven't yet registered in his user database.  It's
really a revolution!
