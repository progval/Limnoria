###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008-2009,2011, James Vega
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import os
import sys
import time
import socket

import supybot.utils as utils
import supybot.registry as registry
import supybot.ircutils as ircutils
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization()

###
# version: This should be pretty obvious.
###
from supybot.version import version

###
# *** The following variables are affected by command-line options.  They are
#     not registry variables for a specific reason.  Do *not* change these to
#     registry variables without first consulting people smarter than yourself.
###

###
# daemonized: This determines whether or not the bot has been daemonized
#             (i.e., set to run in the background).  Obviously, this defaults
#             to False.  A command-line option for obvious reasons.
###
daemonized = False

###
# allowDefaultOwner: True if supybot.capabilities is allowed not to include
#                    '-owner' -- that is, if all users should be automatically
#                    recognized as owners.  That would suck, hence we require a
#                    command-line option to allow this stupidity.
###
allowDefaultOwner = False

###
# Here we replace values in other modules as appropriate.
###
utils.web.defaultHeaders['User-agent'] = \
                         'Mozilla/5.0 (Compatible; Supybot %s)' % version

###
# The standard registry.
###
supybot = registry.Group()
supybot.setName('supybot')

def registerGroup(Group, name, group=None, **kwargs):
    if kwargs:
        group = registry.Group(**kwargs)
    return Group.register(name, group)

def registerGlobalValue(group, name, value):
    value.channelValue = False
    return group.register(name, value)

def registerChannelValue(group, name, value):
    value._supplyDefault = True
    value.channelValue = True
    g = group.register(name, value)
    gname = g._name.lower()
    for name in registry._cache.iterkeys():
        if name.lower().startswith(gname) and len(gname) < len(name):
            name = name[len(gname)+1:] # +1 for .
            parts = registry.split(name)
            if len(parts) == 1 and parts[0] and ircutils.isChannel(parts[0]):
                # This gets the channel values so they always persist.
                g.get(parts[0])()

def registerPlugin(name, currentValue=None, public=True):
    group = registerGlobalValue(supybot.plugins, name,
        registry.Boolean(False, _("""Determines whether this plugin is loaded
         by default."""), showDefault=False))
    supybot.plugins().add(name)
    registerGlobalValue(group, 'public',
        registry.Boolean(public, _("""Determines whether this plugin is
        publicly visible.""")))
    if currentValue is not None:
        supybot.plugins.get(name).setValue(currentValue)
    registerGroup(users.plugins, name)
    return group

def get(group, channel=None):
    if group.channelValue and \
       channel is not None and ircutils.isChannel(channel):
        return group.get(channel)()
    else:
        return group()

###
# The user info registry.
###
users = registry.Group()
users.setName('users')
registerGroup(users, 'plugins', orderAlphabetically=True)

def registerUserValue(group, name, value):
    assert group._name.startswith('users')
    value._supplyDefault = True
    group.register(name, value)

class ValidNick(registry.String):
    """Value must be a valid IRC nick."""
    def setValue(self, v):
        if not ircutils.isNick(v):
            self.error()
        else:
            registry.String.setValue(self, v)

class ValidNickOrEmpty(ValidNick):
    """Value must be a valid IRC nick or empty."""
    def setValue(self, v):
        if v != '' and not ircutils.isNick(v):
            self.error()
        else:
            registry.String.setValue(self, v)

class ValidNicks(registry.SpaceSeparatedListOf):
    Value = ValidNick

class ValidNickAllowingPercentS(ValidNick):
    """Value must be a valid IRC nick, with the possible exception of a %s
    in it."""
    def setValue(self, v):
        # If this works, it's a valid nick, aside from the %s.
        try:
            ValidNick.setValue(self, v.replace('%s', ''))
            # It's valid aside from the %s, we'll let it through.
            registry.String.setValue(self, v)
        except registry.InvalidRegistryValue:
            self.error()

class ValidNicksAllowingPercentS(ValidNicks):
    Value = ValidNickAllowingPercentS

class ValidChannel(registry.String):
    """Value must be a valid IRC channel name."""
    def setValue(self, v):
        self.channel = v
        if ',' in v:
            # To prevent stupid users from: a) trying to add a channel key
            # with a comma in it, b) trying to add channels separated by
            # commas instead of spaces
            try:
                (channel, _) = v.split(',')
            except ValueError:
                self.error()
        else:
            channel = v
        if not ircutils.isChannel(channel):
            self.error()
        else:
            registry.String.setValue(self, v)

    def error(self):
        try:
            super(ValidChannel, self).error()
        except registry.InvalidRegistryValue, e:
            e.channel = self.channel
            raise e

class ValidHostmask(registry.String):
    """Value must be a valid user hostmask."""
    def setValue(self, v):
        if not ircutils.isUserHostmask(v):
            self.error()
        super(ValidHostmask, self).setValue(v)

registerGlobalValue(supybot, 'nick',
   ValidNick('supybot', _("""Determines the bot's default nick.""")))

registerGlobalValue(supybot.nick, 'alternates',
   ValidNicksAllowingPercentS(['%s`', '%s_'], _("""Determines what alternative
   nicks will be used if the primary nick (supybot.nick) isn't available.  A
   %s in this nick is replaced by the value of supybot.nick when used. If no
   alternates are given, or if all are used, the supybot.nick will be perturbed
   appropriately until an unused nick is found.""")))

registerGlobalValue(supybot, 'ident',
    ValidNick('limnoria', _("""Determines the bot's ident string, if the server
    doesn't provide one by default.""")))

class VersionIfEmpty(registry.String):
    def __call__(self):
        ret = registry.String.__call__(self)
        if not ret:
            ret = 'Supybot %s' % version
        return ret

registerGlobalValue(supybot, 'user',
    VersionIfEmpty('', _("""Determines the user the bot sends to the server.
    A standard user using the current version of the bot will be generated if
    this is left empty.""")))

class Networks(registry.SpaceSeparatedSetOfStrings):
    List = ircutils.IrcSet

registerGlobalValue(supybot, 'networks',
    Networks([], _("""Determines what networks the bot will connect to."""),
             orderAlphabetically=True))

class Servers(registry.SpaceSeparatedListOfStrings):
    def normalize(self, s):
        if ':' not in s:
            s += ':6667'
        return s

    def convert(self, s):
        s = self.normalize(s)
        (server, port) = s.split(':')
        port = int(port)
        return (server, port)

    def __call__(self):
        L = registry.SpaceSeparatedListOfStrings.__call__(self)
        return map(self.convert, L)

    def __str__(self):
        return ' '.join(registry.SpaceSeparatedListOfStrings.__call__(self))

    def append(self, s):
        L = registry.SpaceSeparatedListOfStrings.__call__(self)
        L.append(s)

class SpaceSeparatedSetOfChannels(registry.SpaceSeparatedListOf):
    sorted = True
    List = ircutils.IrcSet
    Value = ValidChannel
    def join(self, channel):
        import ircmsgs # Don't put this globally!  It's recursive.
        key = self.key.get(channel)()
        if key:
            return ircmsgs.join(channel, key)
        else:
            return ircmsgs.join(channel)

def registerNetwork(name, password='', ssl=False, sasl_username='',
        sasl_password=''):
    network = registerGroup(supybot.networks, name)
    registerGlobalValue(network, 'password', registry.String(password,
        _("""Determines what password will be used on %s.  Yes, we know that
        technically passwords are server-specific and not network-specific,
        but this is the best we can do right now.""") % name, private=True))
    registryServers = registerGlobalValue(network, 'servers', Servers([],
        _("""Determines what servers the bot will connect to for %s.  Each will
        be tried in order, wrapping back to the first when the cycle is
        completed.""") % name))
    registerGlobalValue(network, 'channels', SpaceSeparatedSetOfChannels([],
        _("""Determines what channels the bot will join only on %s.""") %
        name))
    registerGlobalValue(network, 'ssl', registry.Boolean(ssl,
        _("""Determines whether the bot will attempt to connect with SSL
        sockets to %s.""") % name))
    registerChannelValue(network.channels, 'key', registry.String('',
        _("""Determines what key (if any) will be used to join the
        channel.""")))
    registerGlobalValue(network, 'nick', ValidNickOrEmpty('', _("""Determines
        what nick the bot will use on this network. If empty, defaults to
        supybot.nick.""")))
    sasl = registerGroup(network, 'sasl')
    registerGlobalValue(sasl, 'username', registry.String(sasl_username,
        _("""Determines what SASL username will be used on %s. This should
        be the bot's account name. Due to the way SASL works, you can't use
        any grouped nick.""") % name, private=False))
    registerGlobalValue(sasl, 'password', registry.String(sasl_password,
        _("""Determines what SASL password will be used on %s.""") \
        % name, private=True))
    return network

# Let's fill our networks.
for (name, s) in registry._cache.iteritems():
    if name.startswith('supybot.networks.'):
        parts = name.split('.')
        name = parts[2]
        if name != 'default':
            registerNetwork(name)


###
# Reply/error tweaking.
###
registerGroup(supybot, 'reply')

registerGroup(supybot.reply, 'format')
registerChannelValue(supybot.reply.format, 'time',
    registry.String('%I:%M %p, %B %d, %Y', _("""Determines how timestamps
    printed for human reading should be formatted. Refer to the Python
    documentation for the time module to see valid formatting characters for
    time formats.""")))
def timestamp(t):
    if t is None:
        t = time.time()
    t = time.localtime(t)
    format = get(supybot.reply.format.time, dynamic.channel)
    return time.strftime(format, t)
utils.str.timestamp = timestamp

registerGroup(supybot.reply.format.time, 'elapsed')
registerChannelValue(supybot.reply.format.time.elapsed, 'short',
    registry.Boolean(False, _("""Determines whether elapsed times will be given
    as "1 day, 2 hours, 3 minutes, and 15 seconds" or as "1d 2h 3m 15s".""")))

originalTimeElapsed = utils.timeElapsed
def timeElapsed(*args, **kwargs):
    kwargs['short'] = supybot.reply.format.time.elapsed.short()
    return originalTimeElapsed(*args, **kwargs)
utils.timeElapsed = timeElapsed

registerGlobalValue(supybot.reply, 'maximumLength',
    registry.Integer(512*256, _("""Determines the absolute maximum length of
    the bot's reply -- no reply will be passed through the bot with a length
    greater than this.""")))

registerChannelValue(supybot.reply, 'mores',
    registry.Boolean(True, _("""Determines whether the bot will break up long
    messages into chunks and allow users to use  the 'more' command to get the
    remaining chunks.""")))

registerChannelValue(supybot.reply.mores, 'maximum',
    registry.PositiveInteger(50, _("""Determines what the maximum number of
    chunks (for use with the 'more' command) will be.""")))

registerChannelValue(supybot.reply.mores, 'length',
    registry.NonNegativeInteger(0, _("""Determines how long individual chunks
    will be.  If set to 0, uses our super-tweaked,
    get-the-most-out-of-an-individual-message default.""")))

registerChannelValue(supybot.reply.mores, 'instant',
    registry.PositiveInteger(1, _("""Determines how many mores will be sent
    instantly (i.e., without the use of the more command, immediately when
    they are formed).  Defaults to 1, which means that a more command will be
    required for all but the first chunk.""")))

registerGlobalValue(supybot.reply, 'oneToOne',
    registry.Boolean(True, _("""Determines whether the bot will send
    multi-message replies in a single message or in multiple messages.  For
    safety purposes (so the bot is less likely to flood) it will normally send
    everything in a single message, using mores if necessary.""")))

registerChannelValue(supybot.reply, 'whenNotCommand',
    registry.Boolean(True, _("""Determines whether the bot will reply with an
    error message when it is addressed but not given a valid command.  If this
    value is False, the bot will remain silent, as long as no other plugins
    override the normal behavior.""")))

registerGroup(supybot.reply, 'error')
registerGlobalValue(supybot.reply.error, 'detailed',
    registry.Boolean(False, _("""Determines whether error messages that result
    from bugs in the bot will show a detailed error message (the uncaught
    exception) or a generic error message.""")))
registerChannelValue(supybot.reply.error, 'inPrivate',
    registry.Boolean(False, _("""Determines whether the bot will send error
    messages to users in private.  You might want to do this in order to keep
    channel traffic to minimum.  This can be used in combination with
    supybot.reply.error.withNotice.""")))
registerChannelValue(supybot.reply.error, 'withNotice',
    registry.Boolean(False, _("""Determines whether the bot will send error
    messages to users via NOTICE instead of PRIVMSG.  You might want to do this
    so users can ignore NOTICEs from the bot and not have to see error
    messages; or you might want to use it in combination with
    supybot.reply.errorInPrivate so private errors don't open a query window
    in most IRC clients.""")))
registerChannelValue(supybot.reply.error, 'noCapability',
    registry.Boolean(False, _("""Determines whether the bot will send an error
    message to users who attempt to call a command for which they do not have
    the necessary capability.  You may wish to make this True if you don't want
    users to understand the underlying security system preventing them from
    running certain commands.""")))

registerChannelValue(supybot.reply, 'inPrivate',
    registry.Boolean(False, _("""Determines whether the bot will reply
     privatelywhen replying in a channel, rather than replying to the whole
     channel.""")))

registerChannelValue(supybot.reply, 'withNotice',
    registry.Boolean(False, _("""Determines whether the bot will reply with a
    notice when replying in a channel, rather than replying with a privmsg as
    normal.""")))

# XXX: User value.
registerGlobalValue(supybot.reply, 'withNoticeWhenPrivate',
    registry.Boolean(False, _("""Determines whether the bot will reply with a
    notice when it is sending a private message, in order not to open a /query
    window in clients.  This can be overridden by individual users via the user
    configuration variable reply.withNoticeWhenPrivate.""")))

registerChannelValue(supybot.reply, 'withNickPrefix',
    registry.Boolean(True, _("""Determines whether the bot will always prefix
     theuser's nick to its reply to that user's command.""")))

registerChannelValue(supybot.reply, 'whenNotAddressed',
    registry.Boolean(False, _("""Determines whether the bot should attempt to
    reply to all messages even if they don't address it (either via its nick
    or a prefix character).  If you set this to True, you almost certainly want
    to set supybot.reply.whenNotCommand to False.""")))

registerChannelValue(supybot.reply, 'requireChannelCommandsToBeSentInChannel',
    registry.Boolean(False, _("""Determines whether the bot will allow you to
    send channel-related commands outside of that channel.  Sometimes people
    find it confusing if a channel-related command (like Filter.outfilter)
    changes the behavior of the channel but was sent outside the channel
    itself.""")))

registerGlobalValue(supybot, 'followIdentificationThroughNickChanges',
    registry.Boolean(False, _("""Determines whether the bot will unidentify
    someone when that person changes his or her nick.  Setting this to True
    will cause the bot to track such changes.  It defaults to False for a
    little greater security.""")))

registerGlobalValue(supybot, 'alwaysJoinOnInvite',
    registry.Boolean(False, _("""Determines whether the bot will always join a
    channel when it's invited.  If this value is False, the bot will only join
    a channel if the user inviting it has the 'admin' capability (or if it's
    explicitly told to join the channel using the Admin.join command)""")))

registerChannelValue(supybot.reply, 'showSimpleSyntax',
    registry.Boolean(False, _("""Supybot normally replies with the full help
    whenever a user misuses a command.  If this value is set to True, the bot
    will only reply with the syntax of the command (the first line of the
    help) rather than the full help.""")))

class ValidPrefixChars(registry.String):
    """Value must contain only ~!@#$%^&*()_-+=[{}]\\|'\";:,<.>/?"""
    def setValue(self, v):
        if v.translate(utils.str.chars, '`~!@#$%^&*()_-+=[{}]\\|\'";:,<.>/?'):
            self.error()
        registry.String.setValue(self, v)

registerGroup(supybot.reply, 'whenAddressedBy')
registerChannelValue(supybot.reply.whenAddressedBy, 'chars',
    ValidPrefixChars('', _("""Determines what prefix characters the bot will
    reply to.  A prefix character is a single character that the bot will use
    to determine what messages are addressed to it; when there are no prefix
    characters set, it just uses its nick.  Each character in this string is
    interpreted individually; you can have multiple prefix chars
    simultaneously, and if any one of them is used as a prefix the bot will
    assume it is being addressed.""")))

registerChannelValue(supybot.reply.whenAddressedBy, 'strings',
    registry.SpaceSeparatedSetOfStrings([], _("""Determines what strings the
    bot will reply to when they are at the beginning of the message.  Whereas
    prefix.chars can only be one character (although there can be many of
    them), this variable is a space-separated list of strings, so you can
    set something like '@@ ??' and the bot will reply when a message is
    prefixed by either @@ or ??.""")))
registerChannelValue(supybot.reply.whenAddressedBy, 'nick',
    registry.Boolean(True, _("""Determines whether the bot will reply when
    people address it by its nick, rather than with a prefix character.""")))
registerChannelValue(supybot.reply.whenAddressedBy.nick, 'atEnd',
    registry.Boolean(False, _("""Determines whether the bot will reply when
    people address it by its nick at the end of the message, rather than at
    the beginning.""")))
registerChannelValue(supybot.reply.whenAddressedBy, 'nicks',
    registry.SpaceSeparatedSetOfStrings([], _("""Determines what extra nicks
    the bot will always respond to when addressed by, even if its current nick
    is something else.""")))

###
# Replies
###
registerGroup(supybot, 'replies')

registerChannelValue(supybot.replies, 'success',
    registry.NormalizedString(_("""The operation succeeded."""),
    _("""Determines what message the bot replies with when a command succeeded.
    If this configuration variable is empty, no success message will be
    sent.""")))

registerChannelValue(supybot.replies, 'error',
    registry.NormalizedString(_("""An error has occurred and has been logged.
    Please contact this bot's administrator for more information."""), _("""
    Determines what error message the bot gives when it wants to be
    ambiguous.""")))

registerChannelValue(supybot.replies, 'errorOwner',
    registry.NormalizedString(_("""An error has occurred and has been logged.
    Check the logs for more informations."""), _("""Determines what error
    message the bot gives to the owner when it wants to be ambiguous.""")))

registerChannelValue(supybot.replies, 'incorrectAuthentication',
    registry.NormalizedString(_("""Your hostmask doesn't match or your password
    is wrong."""), _("""Determines what message the bot replies with when
     someone tries to use a command that requires being identified or having a
    password and neither credential is correct.""")))

# XXX: This should eventually check that there's one and only one %s here.
registerChannelValue(supybot.replies, 'noUser',
    registry.NormalizedString(_("""I can't find %s in my user
    database.  If you didn't give a user name, then I might not know what your
    user is, and you'll need to identify before this command might work."""),
    _("""Determines what error message the bot replies with when someone tries
    to accessing some information on a user the bot doesn't know about.""")))

registerChannelValue(supybot.replies, 'notRegistered',
    registry.NormalizedString(_("""You must be registered to use this command.
    If you are already registered, you must either identify (using the identify
    command) or add a hostmask matching your current hostmask (using the
    "hostmask add" command)."""), _("""Determines what error message the bot
    replies with when someone tries to do something that requires them to be
    registered but they're not currently recognized.""")))

registerChannelValue(supybot.replies, 'noCapability',
    registry.NormalizedString(_("""You don't have the %s capability.  If you
    think that you should have this capability, be sure that you are identified
    before trying again.  The 'whoami' command can tell you if you're
    identified."""), _("""Determines what error message is given when the bot
    is telling someone they aren't cool enough to use the command they tried to
    use.""")))

registerChannelValue(supybot.replies, 'genericNoCapability',
    registry.NormalizedString(_("""You're missing some capability you need.
    This could be because you actually possess the anti-capability for the
    capability that's required of you, or because the channel provides that
    anti-capability by default, or because the global capabilities include
    that anti-capability.  Or, it could be because the channel or
    supybot.capabilities.default is set to False, meaning that no commands are
    allowed unless explicitly in your capabilities.  Either way, you can't do
    what you want to do."""),
    _("""Determines what generic error message is given when the bot is telling
    someone that they aren't cool enough to use the command they tried to use,
    and the author of the code calling errorNoCapability didn't provide an
    explicit capability for whatever reason.""")))

registerChannelValue(supybot.replies, 'requiresPrivacy',
    registry.NormalizedString(_("""That operation cannot be done in a
    channel."""), _("""Determines what error messages the bot sends to people
    who try to do things in a channel that really should be done in
    private.""")))

registerChannelValue(supybot.replies, 'possibleBug',
    registry.NormalizedString(_("""This may be a bug.  If you think it is,
    please file a bug report at
    <https://github.com/ProgVal/Limnoria/issues>."""),
    _("""Determines what message the bot sends when it thinks you've
    encountered a bug that the developers don't know about.""")))
###
# End supybot.replies.
###

registerGlobalValue(supybot, 'snarfThrottle',
    registry.Float(10.0, _("""A floating point number of seconds to throttle
    snarfed URLs, in order to prevent loops between two bots snarfing the same
    URLs and having the snarfed URL in the output of the snarf message.""")))

registerGlobalValue(supybot, 'upkeepInterval',
    registry.PositiveInteger(3600, _("""Determines the number of seconds
    between running the upkeep function that flushes (commits) open databases,
    collects garbage, and records some useful statistics at the debugging
     level.""")))

registerGlobalValue(supybot, 'flush',
    registry.Boolean(True, _("""Determines whether the bot will periodically
    flush data and configuration files to disk.  Generally, the only time
    you'll want to set this to False is when you want to modify those
    configuration files by hand and don't want the bot to flush its current
    version over your modifications.  Do note that if you change this to False
    inside the bot, your changes won't be flushed.  To make this change
    permanent, you must edit the registry yourself.""")))


###
# supybot.commands.  For stuff relating to commands.
###
registerGroup(supybot, 'commands')

class ValidQuotes(registry.Value):
    """Value must consist solely of \", ', and ` characters."""
    def setValue(self, v):
        if [c for c in v if c not in '"`\'']:
            self.error()
        super(ValidQuotes, self).setValue(v)

    def __str__(self):
        return str(self.value)

registerChannelValue(supybot.commands, 'quotes',
    ValidQuotes('"', _("""Determines what characters are valid for quoting
    arguments to commands in order to prevent them from being tokenized.
    """)))
# This is a GlobalValue because bot owners should be able to say, "There will
# be no nesting at all on this bot."  Individual channels can just set their
# brackets to the empty string.
registerGlobalValue(supybot.commands, 'nested',
    registry.Boolean(True, _("""Determines whether the bot will allow nested
    commands, which rule.  You definitely should keep this on.""")))
registerGlobalValue(supybot.commands.nested, 'maximum',
    registry.PositiveInteger(10, _("""Determines what the maximum number of
    nested commands will be; users will receive an error if they attempt
    commands more nested than this.""")))

class ValidBrackets(registry.OnlySomeStrings):
    validStrings = ('', '[]', '<>', '{}', '()')

registerChannelValue(supybot.commands.nested, 'brackets',
    ValidBrackets('[]', _("""Supybot allows you to specify what brackets are
    used for your nested commands.  Valid sets of brackets include [], <>, and
    {} ().  [] has strong historical motivation, as well as being the brackets
    that don't require shift.  <> or () might be slightly superior because they
    cannot occur in a nick.  If this string is empty, nested commands will
    not be allowed in this channel.""")))
registerChannelValue(supybot.commands.nested, 'pipeSyntax',
    registry.Boolean(False, _("""Supybot allows nested commands. Enabling this
    option will allow nested commands with a syntax similar to UNIX pipes, for
    example: 'bot: foo | bar'.""")))

registerGroup(supybot.commands, 'defaultPlugins',
    orderAlphabetically=True, help=_("""Determines what commands have default
    plugins set, and which plugins are set to be the default for each of those
    commands."""))
registerGlobalValue(supybot.commands.defaultPlugins, 'importantPlugins',
    registry.SpaceSeparatedSetOfStrings(
        ['Admin', 'Channel', 'Config', 'Misc', 'Owner', 'Plugin', 'User'],
        _("""Determines what plugins automatically get precedence over all
        other plugins when selecting a default plugin for a command.  By
        default, this includes the standard loaded plugins.  You probably
        shouldn't change this if you don't know what you're doing; if you do
        know what you're doing, then also know that this set is
        case-sensitive.""")))

# supybot.commands.disabled moved to callbacks for canonicalName.

###
# supybot.abuse.  For stuff relating to abuse of the bot.
###
registerGroup(supybot, 'abuse')
registerGroup(supybot.abuse, 'flood')
registerGlobalValue(supybot.abuse.flood, 'command',
    registry.Boolean(True, _("""Determines whether the bot will defend itself
    against command-flooding.""")))
registerGlobalValue(supybot.abuse.flood.command, 'maximum',
    registry.PositiveInteger(12, _("""Determines how many commands users are
    allowed per minute.  If a user sends more than this many commands in any
    60 second period, he or she will be ignored for
    supybot.abuse.flood.command.punishment seconds.""")))
registerGlobalValue(supybot.abuse.flood.command, 'punishment',
    registry.PositiveInteger(300, _("""Determines how many seconds the bot
    will ignore users who flood it with commands.""")))

registerGlobalValue(supybot.abuse.flood.command, 'invalid',
    registry.Boolean(True, _("""Determines whether the bot will defend itself
    against invalid command-flooding.""")))
registerGlobalValue(supybot.abuse.flood.command.invalid, 'maximum',
    registry.PositiveInteger(5, _("""Determines how many invalid commands users
    are allowed per minute.  If a user sends more than this many invalid
    commands in any 60 second period, he or she will be ignored for
    supybot.abuse.flood.command.invalid.punishment seconds.  Typically, this
    value is lower than supybot.abuse.flood.command.maximum, since it's far
    less likely (and far more annoying) for users to flood with invalid
    commands than for them to flood with valid commands.""")))
registerGlobalValue(supybot.abuse.flood.command.invalid, 'punishment',
    registry.PositiveInteger(600, _("""Determines how many seconds the bot
    will ignore users who flood it with invalid commands.  Typically, this
    value is higher than supybot.abuse.flood.command.punishment, since it's far
    less likely (and far more annoying) for users to flood with invalid
    commands than for them to flood with valid commands.""")))
registerGlobalValue(supybot.abuse.flood.command.invalid, 'notify',
    registry.Boolean(True, _("""Determines whether the bot will notify people
    that they're being ignored for invalid command flooding.""")))


###
# supybot.drivers.  For stuff relating to Supybot's drivers (duh!)
###
registerGroup(supybot, 'drivers')
registerGlobalValue(supybot.drivers, 'poll',
    registry.PositiveFloat(1.0, _("""Determines the default length of time a
    driver should block waiting for input.""")))

class ValidDriverModule(registry.OnlySomeStrings):
    validStrings = ('default', 'Socket', 'Twisted')

registerGlobalValue(supybot.drivers, 'module',
    ValidDriverModule('default', _("""Determines what driver module the bot
    will use.  Socket, a simple driver based on timeout sockets, is used by
    default because it's simple and stable.  Twisted is very stable and simple,
    and if you've got Twisted installed, is probably your best bet.""")))

registerGlobalValue(supybot.drivers, 'maxReconnectWait',
    registry.PositiveFloat(300.0, _("""Determines the maximum time the bot will
    wait before attempting to reconnect to an IRC server.  The bot may, of
    course, reconnect earlier if possible.""")))

###
# supybot.directories, for stuff relating to directories.
###

# XXX This shouldn't make directories willy-nilly.  As it is now, if it's
#     configured, it'll still make the default directories, I think.
class Directory(registry.String):
    def __call__(self):
        # ??? Should we perhaps always return an absolute path here?
        v = super(Directory, self).__call__()
        if not os.path.exists(v):
            os.mkdir(v)
        return v

    def dirize(self, filename):
        myself = self()
        if os.path.isabs(filename):
            filename = os.path.abspath(filename)
            selfAbs = os.path.abspath(myself)
            commonPrefix = os.path.commonprefix([selfAbs, filename])
            filename = filename[len(commonPrefix):]
        elif not os.path.isabs(myself):
            if filename.startswith(myself):
                filename = filename[len(myself):]
        filename = filename.lstrip(os.path.sep) # Stupid os.path.join!
        return os.path.join(myself, filename)

class DataFilename(registry.String):
    def __call__(self):
        v = super(DataFilename, self).__call__()
        dataDir = supybot.directories.data()
        if not v.startswith(dataDir):
            v = os.path.basename(v)
            v = os.path.join(dataDir, v)
        self.setValue(v)
        return v

class DataFilenameDirectory(DataFilename, Directory):
    def __call__(self):
        v = DataFilename.__call__(self)
        v = Directory.__call__(self)
        return v

registerGroup(supybot, 'directories')
registerGlobalValue(supybot.directories, 'conf',
    Directory('conf', _("""Determines what directory configuration data is
    put into.""")))
registerGlobalValue(supybot.directories, 'data',
    Directory('data', _("""Determines what directory data is put into.""")))
registerGlobalValue(supybot.directories, 'backup',
    Directory('backup', _("""Determines what directory backup data is put
    into.""")))
registerGlobalValue(supybot.directories.data, 'tmp',
    DataFilenameDirectory('tmp', _("""Determines what directory temporary files
    are put into.""")))

utils.file.AtomicFile.default.tmpDir = supybot.directories.data.tmp
utils.file.AtomicFile.default.backupDir = supybot.directories.backup

registerGlobalValue(supybot.directories, 'plugins',
    registry.CommaSeparatedListOfStrings([], _("""Determines what directories
    the bot will look for plugins in.  Accepts a comma-separated list of
    strings.
    This means that to add another directory, you can nest the former value and
    add a new one.  E.g. you can say: bot: 'config supybot.directories.plugins
    [config supybot.directories.plugins], newPluginDirectory'.""")))

registerGlobalValue(supybot, 'plugins',
    registry.SpaceSeparatedSetOfStrings([], _("""Determines what plugins will
    be loaded."""), orderAlphabetically=True))
registerGlobalValue(supybot.plugins, 'alwaysLoadImportant',
    registry.Boolean(True, _("""Determines whether the bot will always load
    important plugins (Admin, Channel, Config, Misc, Owner, and User)
    regardless of what their configured state is.  Generally, if these plugins
    are configured not to load, you didn't do it on purpose, and you still
    want them to load.  Users who don't want to load these plugins are smart
    enough to change the value of this variable appropriately :)""")))

###
# supybot.databases.  For stuff relating to Supybot's databases (duh!)
###
class Databases(registry.SpaceSeparatedListOfStrings):
    def __call__(self):
        v = super(Databases, self).__call__()
        if not v:
            v = ['anydbm', 'cdb', 'flat', 'pickle']
            if 'sqlite' in sys.modules:
                v.insert(0, 'sqlite')
            if 'sqlite3' in sys.modules:
                v.insert(0, 'sqlite3')
            if 'pysqlite2' in sys.modules: # for python 2.4
                v.insert(0, 'sqlite3')
        return v

    def serialize(self):
        return ' '.join(self.value)

registerGlobalValue(supybot, 'databases',
    Databases([], _("""Determines what databases are available for use. If this
    value is not configured (that is, if its value is empty) then sane defaults
    will be provided.""")))

registerGroup(supybot.databases, 'users')
registerGlobalValue(supybot.databases.users, 'filename',
    registry.String('users.conf', _("""Determines what filename will be used
    for the users database.  This file will go into the directory specified by
    the supybot.directories.conf variable.""")))
registerGlobalValue(supybot.databases.users, 'timeoutIdentification',
    registry.Integer(0, _("""Determines how long it takes identification to
    time out.  If the value is less than or equal to zero, identification never
    times out.""")))
registerGlobalValue(supybot.databases.users, 'allowUnregistration',
    registry.Boolean(False, _("""Determines whether the bot will allow users to
    unregister their users.  This can wreak havoc with already-existing
    databases, so by default we don't allow it.  Enable this at your own risk.
    (Do also note that this does not prevent the owner of the bot from using
    the unregister command.)
    """)))

registerGroup(supybot.databases, 'ignores')
registerGlobalValue(supybot.databases.ignores, 'filename',
    registry.String('ignores.conf', _("""Determines what filename will be used
    for the ignores database.  This file will go into the directory specified
    by the supybot.directories.conf variable.""")))

registerGroup(supybot.databases, 'channels')
registerGlobalValue(supybot.databases.channels, 'filename',
    registry.String('channels.conf', _("""Determines what filename will be used
    for the channels database.  This file will go into the directory specified
    by the supybot.directories.conf variable.""")))

# TODO This will need to do more in the future (such as making sure link.allow
# will let the link occur), but for now let's just leave it as this.
class ChannelSpecific(registry.Boolean):
    def getChannelLink(self, channel):
        channelSpecific = supybot.databases.plugins.channelSpecific
        channels = [channel]
        def hasLinkChannel(channel):
            if not get(channelSpecific, channel):
                lchannel = get(channelSpecific.link, channel)
                if not get(channelSpecific.link.allow, lchannel):
                    return False
                return channel != lchannel
            return False
        lchannel = channel
        while hasLinkChannel(lchannel):
            lchannel = get(channelSpecific.link, lchannel)
            if lchannel not in channels:
                channels.append(lchannel)
            else:
                # Found a cyclic link.  We'll just use the current channel
                lchannel = channel
                break
        return lchannel

registerGroup(supybot.databases, 'plugins')
registerChannelValue(supybot.databases.plugins, 'channelSpecific',
    ChannelSpecific(True, _("""Determines whether database-based plugins that
    can be channel-specific will be so.  This can be overridden by individual
    channels.  Do note that the bot needs to be restarted immediately after
    changing this variable or your db plugins may not work for your channel;
    also note that you may wish to set
    supybot.databases.plugins.channelSpecific.link appropriately if you wish
    to share a certain channel's databases globally.""")))
registerChannelValue(supybot.databases.plugins.channelSpecific, 'link',
    ValidChannel('#', _("""Determines what channel global
    (non-channel-specific) databases will be considered a part of.  This is
    helpful if you've been running channel-specific for awhile and want to turn
    the databases for your primary channel into global databases.  If
    supybot.databases.plugins.channelSpecific.link.allow prevents linking, the
    current channel will be used.  Do note that the bot needs to be restarted
    immediately after changing this variable or your db plugins may not work
    for your channel.""")))
registerChannelValue(supybot.databases.plugins.channelSpecific.link, 'allow',
    registry.Boolean(True, _("""Determines whether another channel's global
    (non-channel-specific) databases will be allowed to link to this channel's
    databases.  Do note that the bot needs to be restarted immediately after
    changing this variable or your db plugins may not work for your channel.
    """)))


class CDB(registry.Boolean):
    def connect(self, filename):
        import supybot.cdb as cdb
        basename = os.path.basename(filename)
        journalName = supybot.directories.data.tmp.dirize(basename+'.journal')
        return cdb.open(filename, 'c',
                        journalName=journalName,
                        maxmods=self.maximumModifications())

registerGroup(supybot.databases, 'types')
registerGlobalValue(supybot.databases.types, 'cdb', CDB(True, _("""Determines
    whether CDB databases will be allowed as a database implementation.""")))
registerGlobalValue(supybot.databases.types.cdb, 'maximumModifications',
    registry.Probability(0.5, _("""Determines how often CDB databases will have
    their modifications flushed to disk.  When the number of modified records
    is greater than this fraction of the total number of records, the database
    will be entirely flushed to disk.""")))

# XXX Configuration variables for dbi, sqlite, flat, mysql, etc.

###
# Protocol information.
###
originalIsNick = ircutils.isNick
def isNick(s, strictRfc=None, **kw):
    if strictRfc is None:
        strictRfc = supybot.protocols.irc.strictRfc()
    return originalIsNick(s, strictRfc=strictRfc, **kw)
ircutils.isNick = isNick

###
# supybot.protocols
###
registerGroup(supybot, 'protocols')

###
# supybot.protocols.irc
###
registerGroup(supybot.protocols, 'irc')

class Banmask(registry.SpaceSeparatedSetOfStrings):
    validStrings = ('exact', 'nick', 'user', 'host')
    def __init__(self, *args, **kwargs):
        assert self.validStrings, 'There must be some valid strings.  ' \
                                  'This is a bug.'
        self.__parent = super(Banmask, self)
        self.__parent.__init__(*args, **kwargs)
        self.__doc__ = format('Valid values include %L.',
                              map(repr, self.validStrings))

    def help(self):
        strings = [s for s in self.validStrings if s]
        return format('%s  Valid strings: %L.', self._help, strings)

    def normalize(self, s):
        lowered = s.lower()
        L = list(map(str.lower, self.validStrings))
        try:
            i = L.index(lowered)
        except ValueError:
            return s # This is handled in setValue.
        return self.validStrings[i]

    def setValue(self, v):
        v = map(self.normalize, v)
        for s in v:
            if s not in self.validStrings:
                self.error()
        self.__parent.setValue(self.List(v))

    def makeBanmask(self, hostmask, options=None):
        """Create a banmask from the given hostmask.  If a style of banmask
        isn't specified via options, the value of
        conf.supybot.protocols.irc.banmask is used.

        options - A list specifying which parts of the hostmask should
        explicitly be matched: nick, user, host.  If 'exact' is given, then
        only the exact hostmask will be used."""
        channel = dynamic.channel
        assert channel is None or ircutils.isChannel(channel)
        (nick, user, host) = ircutils.splitHostmask(hostmask)
        bnick = '*'
        buser = '*'
        bhost = '*'
        if not options:
            options = get(supybot.protocols.irc.banmask, channel)
        for option in options:
            if option == 'nick':
                bnick = nick
            elif option == 'user':
                buser = user
            elif option == 'host':
                bhost = host
            elif option == 'exact':
                return hostmask
        return ircutils.joinHostmask(bnick, buser, bhost)

registerChannelValue(supybot.protocols.irc, 'banmask',
    Banmask(['user', 'host'], _("""Determines what will be used as the
    default banmask style.""")))

registerGlobalValue(supybot.protocols.irc, 'strictRfc',
    registry.Boolean(True, _("""Determines whether the bot will strictly follow
    the RFC; currently this only affects what strings are considered to be
    nicks. If you're using a server or a network that requires you to message
    a nick such as services@this.network.server then you you should set this to
    False.""")))

registerGlobalValue(supybot.protocols.irc, 'umodes',
    registry.String('', _("""Determines what user modes the bot will request
    from the server when it first connects.  Many people might choose +i; some
    networks allow +x, which indicates to the auth services on those networks
    that you should be given a fake host.""")))

registerGlobalValue(supybot.protocols.irc, 'vhost',
    registry.String('', _("""Determines what vhost the bot will bind to before
    connecting to the IRC server.""")))

registerGlobalValue(supybot.protocols.irc, 'maxHistoryLength',
    registry.Integer(1000, _("""Determines how many old messages the bot will
    keep around in its history.  Changing this variable will not take effect
    until the bot is restarted.""")))

registerGlobalValue(supybot.protocols.irc, 'throttleTime',
    registry.Float(1.0, _("""A floating point number of seconds to throttle
    queued messages -- that is, messages will not be sent faster than once per
    throttleTime seconds.""")))

registerGlobalValue(supybot.protocols.irc, 'ping',
    registry.Boolean(True, _("""Determines whether the bot will send PINGs to
    the server it's connected to in order to keep the connection alive and
    discover earlier when it breaks.  Really, this option only exists for
    debugging purposes: you always should make it True unless you're testing
    some strange server issues.""")))

registerGlobalValue(supybot.protocols.irc.ping, 'interval',
    registry.Integer(120, _("""Determines the number of seconds between sending
    pings to the server, if pings are being sent to the server.""")))

registerGroup(supybot.protocols.irc, 'queuing')
registerGlobalValue(supybot.protocols.irc.queuing, 'duplicates',
    registry.Boolean(False, _("""Determines whether the bot will refuse
    duplicated messages to be queued for delivery to the server.  This is a
    safety mechanism put in place to prevent plugins from sending the same
    message multiple times; most of the time it doesn't matter, unless you're
    doing certain kinds of plugin hacking.""")))

registerGroup(supybot.protocols.irc.queuing, 'rateLimit')
registerGlobalValue(supybot.protocols.irc.queuing.rateLimit, 'join',
    registry.Float(0, _("""Determines how many seconds must elapse between
    JOINs sent to the server.""")))

###
# supybot.protocols.http
###
registerGroup(supybot.protocols, 'http')
registerGlobalValue(supybot.protocols.http, 'peekSize',
    registry.PositiveInteger(4096, _("""Determines how many bytes the bot will
    'peek' at when looking through a URL for a doctype or title or something
    similar.  It'll give up after it reads this many bytes, even if it hasn't
    found what it was looking for.""")))

registerGlobalValue(supybot.protocols.http, 'proxy',
    registry.String('', _("""Determines what proxy all HTTP requests should go
    through.  The value should be of the form 'host:port'.""")))
utils.web.proxy = supybot.protocols.http.proxy


###
# HTTP server
###
registerGroup(supybot, 'servers')
registerGroup(supybot.servers, 'http')

class IP(registry.String):
    """Value must be a valid IP."""
    def setValue(self, v):
        if v and not utils.net.isIP(v):
            self.error()
        else:
            registry.String.setValue(self, v)

registerGlobalValue(supybot.servers.http, 'host',
    IP('0.0.0.0', _("Determines what host the HTTP server will bind.")))
registerGlobalValue(supybot.servers.http, 'port',
    registry.Integer(8080, _("""Determines what port the HTTP server will
    bind.""")))
registerGlobalValue(supybot.servers.http, 'keepAlive',
    registry.Boolean(False, _("""Determiness whether the server will stay
    alive if no plugin is using it. This also means that the server will
    start even if it is not used.""")))
registerGlobalValue(supybot.servers.http, 'robots',
    registry.String('', _("""Determines the content of the robots.txt file,
    served on the server to search engine.""")))


###
# Especially boring stuff.
###
registerGlobalValue(supybot, 'defaultIgnore',
    registry.Boolean(False, _("""Determines whether the bot will ignore
    unregistered users by default.  Of course, that'll make it particularly
    hard for those users to register or identify with the bot, but that's your
    problem to solve.""")))


registerGlobalValue(supybot, 'externalIP',
   IP('', _("""A string that is the external IP of the bot.  If this is the
   empty string, the bot will attempt to find out its IP dynamically (though
   sometimes that doesn't work, hence this variable).""")))

class SocketTimeout(registry.PositiveInteger):
    """Value must be an integer greater than supybot.drivers.poll and must be
    greater than or equal to 1."""
    def setValue(self, v):
        if v < supybot.drivers.poll() or v < 1:
            self.error()
        registry.PositiveInteger.setValue(self, v)
        socket.setdefaulttimeout(self.value)

registerGlobalValue(supybot, 'defaultSocketTimeout',
    SocketTimeout(10, _("""Determines what the default timeout for socket
    objects will be.  This means that *all* sockets will timeout when this many
    seconds has gone by (unless otherwise modified by the author of the code
    that uses the sockets).""")))

registerGlobalValue(supybot, 'pidFile',
    registry.String('', _("""Determines what file the bot should write its PID
    (Process ID) to, so you can kill it more easily.  If it's left unset (as is
    the default) then no PID file will be written.  A restart is required for
    changes to this variable to take effect.""")))

###
# Debugging options.
###
registerGroup(supybot, 'debug')
registerGlobalValue(supybot.debug, 'threadAllCommands',
    registry.Boolean(False, _("""Determines whether the bot will automatically
    thread all commands.""")))
registerGlobalValue(supybot.debug, 'flushVeryOften',
    registry.Boolean(False, _("""Determines whether the bot will automatically
    flush all flushers *very* often.  Useful for debugging when you don't know
    what's breaking or when, but think that it might be logged.""")))


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
