#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

__revision__ = "$Id$"

import supybot.fix as fix

import os
import sys
import socket
import string

import supybot.utils as utils
import supybot.registry as registry
import supybot.ircutils as ircutils

installDir = os.path.dirname(sys.modules[__name__].__file__)
_srcDir = installDir
_pluginsDir = os.path.join(installDir, 'plugins')

###
# version: This should be pretty obvious.
###
version ='0.77.2+cvs'

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
# allowEval: True if the owner (and only the owner) should be able to eval
#            arbitrary Python code.  This is specifically *not* a registry
#            variable because it shouldn't be modifiable in the bot.
###
allowEval = False

###
# allowDefaultOwner: True if the defaultCapabilities are allowed not to include
#                    '-owner' -- that is, if all users should be automatically
#                    recognized as owners.  That would suck, hence we require a
#                    command-line option to allow this stupidity.
###
allowDefaultOwner = False

###
# The standard registry.
###
supybot = registry.Group()
supybot.setName('supybot')

def registerGroup(Group, name, group=None):
    return Group.register(name, group)

def registerGlobalValue(group, name, value):
    return group.register(name, value)

def registerChannelValue(group, name, value):
    value.supplyDefault = True
    return group.register(name, value)

def registerPlugin(name, currentValue=None, public=True):
    group = registerGlobalValue(supybot.plugins, name,
        registry.Boolean(False, """Determines whether this plugin is loaded by
        default.""", showDefault=False))
    registerGlobalValue(group, 'public',
        registry.Boolean(public, """Determines whether this plugin is
        publicly visible."""))
    if currentValue is not None:
        supybot.plugins.get(name).setValue(currentValue)
    return registerGroup(users.plugins, name)

def channelValue(group, channel=None):
    if channel is None:
        return group()
    else:
        return group.get(channel)()

###
# The user info registry.
###
users = registry.Group()
users.setName('users')
registerGroup(users, 'plugins')

def registerUserValue(group, name, value):
    assert group._name.startswith('users')
    value.supplyDefault = True
    group.register(name, value)

class ValidNick(registry.String):
    """Value must be a valid IRC nick."""
    def setValue(self, v):
        if not ircutils.isNick(v):
            self.error()
        else:
            registry.String.setValue(self, v)

class ValidNicks(registry.SpaceSeparatedListOf):
    Value = ValidNick

class ValidChannel(registry.String):
    """Value must be a valid IRC channel name."""
    def setValue(self, v):
        if ',' in v:
            (channel, _) = v.split(',', 1)
        else:
            channel = v
        if not ircutils.isChannel(channel):
            self.error()
        else:
            registry.String.setValue(self, v)

registerGlobalValue(supybot, 'nick',
   ValidNick('supybot', """Determines the bot's default nick."""))

registerGlobalValue(supybot.nick, 'alternates', ValidNicks([], """Determines
    what alternative nicks will be used if the primary nick (supybot.nick)
    isn't available.  If none are given, or if all are taken, the primary nick
    will be perturbed appropriately until an unused nick is found."""))

registerGlobalValue(supybot, 'ident',
    ValidNick('supybot', """Determines the bot's ident string, if the server
    doesn't provide one by default."""))

registerGlobalValue(supybot, 'user',
    registry.String('Supybot %s' % version, """Determines the user the bot
    sends to the server."""))

registerGroup(supybot, 'networks')
registerGlobalValue(supybot.networks, 'default',
    registry.String('', """Determines what the default network joined by the
    bot will be."""))

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
        
class SpaceSeparatedSetOfChannels(registry.SpaceSeparatedListOf):
    List = ircutils.IrcSet
    Value = ValidChannel
    def removeChannel(self, channel):
        removals = []
        for c in self.value:
            chan = c
            if ',' in c:
                (chan, _) = c.split(',')
            if chan == channel:
                removals.append(c)
        for removal in removals:
            self.value.remove(removal)

def registerNetwork(name, password='', servers=()):
    network = registerGroup(supybot.networks, name)
    registerGlobalValue(network, 'password', registry.String(password,
        """Determines what password will be used on %s.  Yes, we know that
        technically passwords are server-specific and not network-specific,
        but this is the best we can do right now.""" % name))
    registerGlobalValue(network, 'servers', Servers(servers,
        """Determines what servers the bot will connect to for %s.  Each will
        be tried in order, wrapping back to the first when the cycle is
        completed.""" % name))
    registerGlobalValue(network, 'channels', SpaceSeparatedSetOfChannels([],
        """Determines what channels the bot will join only on %s.""" % name))
    return network

# Let's fill our networks.
for (name, s) in registry._cache.iteritems():
    if name.startswith('supybot.networks.'):
        parts = name.split('.')
        name = parts[2]
        if name != 'default':
            registerNetwork(name)


registerGlobalValue(supybot, 'channels',
    SpaceSeparatedSetOfChannels(['#supybot'], """Determines what channels the
    bot will join when it connects to the server."""))

class ValidPrefixChars(registry.String):
    """Value must contain only ~!@#$%^&*()_-+=[{}]\\|'\";:,<.>/?"""
    def setValue(self, v):
        if v.translate(string.ascii, '`~!@#$%^&*()_-+=[{}]\\|\'";:,<.>/?'):
            self.error()
        registry.String.setValue(self, v)

registerChannelValue(supybot, 'prefixChars',
    ValidPrefixChars('', """Determines what prefix characters the bot will
    reply to.  A prefix character is a single character that the bot will use
    to determine what messages are addressed to it; when there are no prefix
    characters set, it just uses its nick.  Each character in this string is
    interpreted individually; you can have multiple prefixChars simultaneously,
    and if any one of them is used as a prefix the bot will assume it is being
    addressed."""))

class DefaultCapabilities(registry.SpaceSeparatedListOfStrings):
    List = ircutils.IrcSet
    def setValue(self, v):
        registry.SpaceSeparatedListOfStrings.setValue(self, v)
        if '-owner' not in self.value and not allowDefaultOwner:
            print '*** You must run supybot with the --allow-default-owner'
            print '*** option in order to allow a default capability of owner.'
            print '*** Don\'t do that, it\'s dumb.  In all likelihood, you\'re'
            print '*** getting this message because you didn\'t remove the'
            print '*** commas from your supybot.defaultCapabilities value in'
            print '*** in your configuration file before start the bot.'
            self.value.add('-owner')

###
# supybot.capabilities
###
registerGlobalValue(supybot, 'capabilities',
    DefaultCapabilities(['-owner', '-admin', '-trusted'], """These are the
    capabilities that are given to everyone by default.  If they are normal
    capabilities, then the user will have to have the appropriate
    anti-capability if you want to override these capabilities; if they are
    anti-capabilities, then the user will have to have the actual capability
    to override these capabilities.  See docs/CAPABILITIES if you don't
    understand why these default to what they do."""))

registerGlobalValue(supybot.capabilities, 'default',
    registry.Boolean(True, """Determines whether the bot by default will allow
    users to have a capability.  If this is disabled, a user must explicitly
    have the capability for whatever command he wishes to run."""))

###
# Reply/error tweaking.
###
registerGroup(supybot, 'reply')

registerChannelValue(supybot.reply, 'truncate',
    registry.Boolean(False, """Determines whether the bot will simply truncate
    messages instead of breaking up long messages and using the 'more' command
    to get the remaining chunks."""))

registerGroup(supybot.reply, 'mores')
registerChannelValue(supybot.reply.mores, 'maximum',
    registry.PositiveInteger(50, """Determines what the maximum number of
    chunks (for use with the 'more' command) will be."""))

registerChannelValue(supybot.reply.mores, 'instant',
    registry.PositiveInteger(1, """Determines how many mores will be sent
    instantly (i.e., without the use of the more command, immediately when
    they are formed).  Defaults to 1, which means that a more command will be
    required for all but the first chunk."""))

registerGlobalValue(supybot.reply, 'oneToOne',
    registry.Boolean(True, """Determines whether the bot will send
    multi-message replies in a single messsage or in multiple messages.  For
    safety purposes (so the bot can't possibly flood) it will normally send
    everything in a single message."""))

class ValidBrackets(registry.OnlySomeStrings):
    validStrings = ('', '[]', '<>', '{}', '()')

registerChannelValue(supybot.reply, 'brackets',
    ValidBrackets('[]', """Supybot allows you to specify what brackets are used
    for your nested commands.  Valid sets of brackets include [], <>, and {}
    ().  [] has strong historical motivation, as well as being the brackets
    that don't require shift.  <> or () might be slightly superior because they
    cannot occur in a nick.  If this value is set to the empty string, no
    nesting will be allowed."""))

registerChannelValue(supybot.reply, 'pipeSyntax',
    registry.Boolean(False, """Supybot allows nested commands. Enabling this
    option will allow nested commands with a syntax similar to UNIX pipes, for
    example: 'bot: foo | bar'."""))

registerChannelValue(supybot.reply, 'whenNotCommand',
    registry.Boolean(True, """Determines whether the bot will reply with an
    error message when it is addressed but not given a valid command.  If this
    value is False, the bot will remain silent."""))

registerGlobalValue(supybot.reply, 'detailedErrors',
    registry.Boolean(False, """Determines whether error messages that result
    from bugs in the bot will show a detailed error message (the uncaught
    exception) or a generic error message."""))

registerChannelValue(supybot.reply, 'errorInPrivate',
    registry.Boolean(False, """Determines whether the bot will send error
    messages to users in private.  You might want to do this in order to keep
    channel traffic to minimum.  This can be used in combination with
    supybot.reply.errorWithNotice."""))

registerChannelValue(supybot.reply, 'errorWithNotice',
    registry.Boolean(False, """Determines whether the bot will send error
    messages to users via NOTICE instead of PRIVMSG.  You might want to do this
    so users can ignore NOTICEs from the bot and not have to see error
    messages; or you might want to use it in combination with
    supybot.reply.errorInPrivate so private errors don't open a query window
    in most IRC clients."""))

registerChannelValue(supybot.reply, 'noCapabilityError',
    registry.Boolean(False, """Determines whether the bot will send an error
    message to users who attempt to call a command for which they do not have
    the necessary capability.  You may wish to make this True if you don't want
    users to understand the underlying security system preventing them from
    running certain commands."""))

registerChannelValue(supybot.reply, 'withPrivateNotice',
    registry.Boolean(False, """Determines whether the bot will reply with a
    private notice to users rather than sending a message to a channel.
    Private notices are particularly nice because they don't generally cause
    IRC clients to open a new query window."""))

# XXX: User value.
registerGlobalValue(supybot.reply, 'withNoticeWhenPrivate',
    registry.Boolean(False, """Determines whether the bot will reply with a
    notice when it is sending a private message, in order not to open a /query
    window in clients.  This can be overridden by individual users via the user
    configuration variable reply.withNoticeWhenPrivate."""))

registerChannelValue(supybot.reply, 'withNickPrefix',
    registry.Boolean(True, """Determines whether the bot will always prefix the
    user's nick to its reply to that user's command."""))

registerChannelValue(supybot.reply, 'whenAddressedByNick',
    registry.Boolean(True, """Determines whether the bot will reply when people
    address it by its nick, rather than with a prefix character."""))

registerChannelValue(supybot.reply, 'whenNotAddressed',
    registry.Boolean(False, """Determines whether the bot should attempt to
    reply to all messages even if they don't address it (either via its nick
    or a prefix character).  If you set this to True, you almost certainly want
    to set supybot.reply.whenNotCommand to False."""))

registerChannelValue(supybot.reply, 'requireChannelCommandsToBeSentInChannel',
    registry.Boolean(False, """Determines whether the bot will allow you to
    send channel-related commands outside of that channel.  Sometimes people
    find it confusing if a channel-related command (like Filter.outfilter)
    changes the behavior of the channel but was sent outside the channel
    itself."""))

registerGlobalValue(supybot, 'followIdentificationThroughNickChanges',
    registry.Boolean(False, """Determines whether the bot will unidentify
    someone when that person changes his or her nick.  Setting this to True
    will cause the bot to track such changes.  It defaults to False for a
    little greater security."""))

registerGlobalValue(supybot, 'alwaysJoinOnInvite',
    registry.Boolean(False, """Determines whether the bot will always join a
    channel when it's invited.  If this value is False, the bot will only join
    a channel if the user inviting it has the 'admin' capability (or if it's
    explicitly told to join the channel using the Admin.join command)"""))

# XXX: ChannelValue-ishness is not respected for this yet.
registerChannelValue(supybot.reply, 'showSimpleSyntax',
    registry.Boolean(False, """Supybot normally replies with the full help
    whenever a user misuses a command.  If this value is set to True, the bot
    will only reply with the syntax of the command (the first line of the
    help) rather than the full help."""))

###
# Replies
###
registerGroup(supybot, 'replies')

registerChannelValue(supybot.replies, 'success',
    registry.NormalizedString("""The operation succeeded.""", """Determines
    what message the bot replies with when a command succeeded."""))

registerChannelValue(supybot.replies, 'error',
    registry.NormalizedString("""An error has occurred and has been logged.
    Please contact this bot's administrator for more information.""", """
    Determines what error message the bot gives when it wants to be
    ambiguous."""))

registerChannelValue(supybot.replies, 'incorrectAuthentication',
    registry.NormalizedString("""Your hostmask doesn't match or your password
    is wrong.""", """Determines what message the bot replies with when someone
    tries to use a command that requires being identified or having a password
    and neither credential is correct."""))

# XXX: This should eventually check that there's one and only one %s here.
registerChannelValue(supybot.replies, 'noUser',
    registry.NormalizedString("""I can't find %s in my user
    database.  If you didn't give a user name, then I might not know what your
    user is, and you'll need to identify before this command might work.""",
    """Determines what error message the bot replies with when someone tries
    to accessing some information on a user the bot doesn't know about."""))

registerChannelValue(supybot.replies, 'notRegistered',
    registry.NormalizedString("""You must be registered to use this command.
    If you are already registered, you must either identify (using the identify
    command) or add a hostmask matching your current hostmask (using the
    addhostmask command).""", """Determines what error message the bot replies
    with when someone tries to do something that requires them to be registered
    but they're not currently recognized."""))

registerChannelValue(supybot.replies, 'noCapability',
    registry.NormalizedString("""You don't have the %r capability.  If you
    think that you should have this capability, be sure that you are identified
    before trying again.  The 'whoami' command can tell you if you're
    identified.""", """Determines what error message is given when the bot is
    telling someone they aren't cool enough to use the command they tried to
    use."""))

registerChannelValue(supybot.replies, 'genericNoCapability',
    registry.NormalizedString("""You're missing some capability you need.
    This could be because you actually possess the anti-capability for the
    capability that's required of you, or because the channel provides that
    anti-capability by default, or because the global capabilities include
    that anti-capability.  Or, it could be because the channel or the global
    defaultAllow is set to False, meaning that no commands are allowed unless
    explicitly in your capabilities.  Either way, you can't do what you want
    to do.""", """Determines what generic error message is given when the bot
    is telling someone that they aren't cool enough to use the command they
    tried to use, and the author of the code calling errorNoCapability didn't
    provide an explicit capability for whatever reason."""))

registerChannelValue(supybot.replies, 'requiresPrivacy',
    registry.NormalizedString("""That operation cannot be done in a
    channel.""", """Determines what error messages the bot sends to people who
    try to do things in a channel that really should be done in private."""))

registerChannelValue(supybot.replies, 'possibleBug',
    registry.NormalizedString("""This may
    be a bug.  If you think it is, please file a bug report at
    <http://sourceforge.net/tracker/?func=add&group_id=58965&atid=489447>.""",
    """Determines what message the bot sends when it thinks you've encountered
    a bug that the developers don't know about."""))
###
# End supybot.replies.
###

registerGlobalValue(supybot, 'snarfThrottle',
    registry.Float(10.0, """A floating point number of seconds to throttle
    snarfed URLs, in order to prevent loops between two bots snarfing the same
    URLs and having the snarfed URL in the output of the snarf message."""))

registerGlobalValue(supybot, 'upkeepInterval',
    registry.PositiveInteger(3600, """Determines the number of seconds between
    running the upkeep function that flushes (commits) open databases, collects
    garbage, and records some useful statistics at the debugging level."""))

registerGlobalValue(supybot, 'flush',
    registry.Boolean(True, """Determines whether the bot will periodically
    flush data and configuration files to disk.  Generally, the only time
    you'll want to set this to False is when you want to modify those
    configuration files by hand and don't want the bot to flush its current
    version over your modifications.  Do note that if you change this to False
    inside the bot, your changes won't be flushed.  To make this change
    permanent, you must edit the registry yourself."""))

###
# supybot.commands.  For stuff relating to commands.
###
registerGroup(supybot, 'commands')
# supybot.commands.disabled moved to callbacks for canonicalName.


###
# supybot.drivers.  For stuff relating to Supybot's drivers (duh!)
###
registerGroup(supybot, 'drivers')
registerGlobalValue(supybot.drivers, 'poll',
    registry.Float(1.0, """Determines the default length of time a driver
    should block waiting for input."""))

class ValidDriverModule(registry.OnlySomeStrings):
    validStrings = ('default', 'socketDrivers',
                    'twistedDrivers', 'asyncoreDrivers')

registerGlobalValue(supybot.drivers, 'module',
    ValidDriverModule('default', """Determines what driver module the bot will
    use.  socketDrivers, a simple driver based on timeout sockets, is used by
    default because it's simple and stable.  asyncoreDrivers is a bit older
    (and less well-maintained) but allows you to integrate with asyncore-based
    applications.  twistedDrivers is very stable and simple, and if you've got
    Twisted installed, is probably your best bet."""))

###
# supybot.directories, for stuff relating to directories.
###

class Directory(registry.String):
    def __call__(self):
        # ??? Should we perhaps always return an absolute path here?
        v = super(Directory, self).__call__()
        if not os.path.exists(v):
            os.mkdir(v)
        return v

    def dirize(self, filename):
        dir = self()
        dirname = os.path.basename(filename)
        if not dirname.endswith(dir): # ??? Should this be an "in" test instead?
            return os.path.join(dir, os.path.basename(filename))
        return filename

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
    Directory('conf', """Determines what directory configuration data is
    put into."""))
registerGlobalValue(supybot.directories, 'data',
    Directory('data', """Determines what directory data is put into."""))
registerGlobalValue(supybot.directories.data, 'tmp',
    DataFilenameDirectory('tmp', """Determines what directory temporary files
    are put into."""))

# Remember, we're *meant* to replace this nice little wrapper.
def transactionalFile(*args, **kwargs):
    kwargs['tmpDir'] = supybot.directories.data.tmp()
    return utils.AtomicFile(*args, **kwargs)
utils.transactionalFile = transactionalFile

class PluginDirectories(registry.CommaSeparatedListOfStrings):
    def __call__(self):
        v = registry.CommaSeparatedListOfStrings.__call__(self)[:] # Copy!
        if _srcDir not in v:
            v.append(_srcDir)
        if _pluginsDir not in v:
            v.append(_pluginsDir)
        return v

registerGlobalValue(supybot.directories, 'plugins',
    PluginDirectories(['plugins'], """Determines what directories the bot will
    look for plugins in.  Accepts a comma-separated list of strings.  This
    means that to add another directory, you can nest the former value and add
    a new one.  E.g. you can say: bot: 'config supybot.directories.plugins
    [config supybot.directories.plugins], newPluginDirectory'."""))

registerGroup(supybot, 'plugins') # This will be used by plugins, but not here.

###
# supybot.databases.  For stuff relating to Supybot's databases (duh!)
###
registerGroup(supybot, 'databases')
registerGroup(supybot.databases, 'users')
registerGlobalValue(supybot.databases.users, 'filename',
    registry.String('users.conf', """Determines what filename will be used for
    the users database.  This file will go into the directory specified by the
    supybot.directories.conf variable."""))
registerGlobalValue(supybot.databases.users, 'timeoutIdentification',
    registry.Integer(0, """Determines how long it takes identification to time
    out.  If the value is less than or equal to zero, identification never
    times out."""))
registerGlobalValue(supybot.databases.users, 'hash',
    registry.Boolean(True, """Determines whether the passwords in the user
    database will be hashed by default."""))

registerGroup(supybot.databases, 'ignores')
registerGlobalValue(supybot.databases.ignores, 'filename',
    registry.String('ignores.conf', """Determines what filename will be used
    for the ignores database.  This file will go into the directory specified
    by the supybot.directories.conf variable."""))

registerGroup(supybot.databases, 'channels')
registerGlobalValue(supybot.databases.channels, 'filename',
    registry.String('channels.conf', """Determines what filename will be used
    for the channels database.  This file will go into the directory specified
    by the supybot.directories.conf variable."""))

registerGroup(supybot.databases, 'plugins')
registerChannelValue(supybot.databases.plugins, 'channelSpecific',
    registry.Boolean(True, """Determines whether database-based plugins that
    can be channel-specific will be so.  This can be overridden by individual
    channels."""))

###
# Protocol information.
###
originalIsNick = ircutils.isNick
def isNick(s, strictRfc=None):
    if strictRfc is None:
        strictRfc = supybot.protocols.irc.strictRfc()
    return originalIsNick(s, strictRfc=strictRfc)
ircutils.isNick = isNick

###
# supybot.protocols
###
registerGroup(supybot, 'protocols')

###
# supybot.protocols.irc
###
registerGroup(supybot.protocols, 'irc')
registerGlobalValue(supybot.protocols.irc, 'strictRfc',
    registry.Boolean(False, """Determines whether the bot will strictly follow
    the RFC; currently this only affects what strings are considered to be
    nicks. If you're using a server or a network that requires you to message
    a nick such as services@this.network.server then you you should set this to
    False."""))

registerGlobalValue(supybot.protocols.irc, 'maxHistoryLength',
    registry.Integer(1000, """Determines how many old messages the bot will
    keep around in its history.  Changing this variable will not take effect
    until the bot is restarted."""))

registerGlobalValue(supybot.protocols.irc, 'throttleTime',
    registry.Float(1.0, """A floating point number of seconds to throttle
    queued messages -- that is, messages will not be sent faster than once per
    throttleTime seconds."""))

registerGlobalValue(supybot.protocols.irc, 'ping',
    registry.Boolean(True, """Determines whether the bot will send PINGs to the
    server it's connected to in order to keep the connection alive and discover
    earlier when it breaks.  Really, this option only exists for debugging
    purposes: you always should make it True unless you're testing some strange
    server issues."""))

registerGlobalValue(supybot.protocols.irc.ping, 'interval',
    registry.Integer(120, """Determines the number of seconds between sending
    pings to the server, if pings are being sent to the server."""))

registerGlobalValue(supybot.protocols.irc, 'queueDuplicateMessages',
    registry.Boolean(False, """Determines whether the bot will allow duplicate
    messages to be queued for delivery to the server.  This is a safety
    mechanism put in place to prevent plugins from sending the same message
    multiple times; most of the time it doesn't matter, but when it does, you'll
    probably want it to disallowed."""))

###
# supybot.protocols.http
###
registerGroup(supybot.protocols, 'http')
registerGlobalValue(supybot.protocols.http, 'peekSize',
    registry.PositiveInteger(4096, """Determines how many bytes the bot will
    'peek' at when looking through a URL for a doctype or title or something
    similar.  It'll give up after it reads this many bytes, even if it hasn't
    found what it was looking for."""))

registerGlobalValue(supybot.protocols.http, 'proxy',
    registry.String('', """Determines what proxy all HTTP requests should go
    through."""))


###
# Especially boring stuff.
###
registerGlobalValue(supybot, 'defaultIgnore',
    registry.Boolean(False, """Determines whether the bot will ignore
    unregistered users by default.  Of course, that'll make it particularly
    hard for those users to register with the bot, but that's your problem to
    solve."""))

registerGlobalValue(supybot, 'humanTimestampFormat',
    registry.String('%I:%M %p, %B %d, %Y', """Determines how timestamps printed
    for human reading should be formatted. Refer to the Python documentation
    for the time module to see valid formatting characteres for time
    formats."""))

class IP(registry.String):
    """Value must be a valid IP."""
    def setValue(self, v):
        if v and not (utils.isIP(v) or utils.isIPV6(v)):
            self.error()
        else:
            registry.String.setValue(self, v)

registerGlobalValue(supybot, 'externalIP',
   IP('', """A string that is the external IP of the bot.  If this is the empty
   string, the bot will attempt to find out its IP dynamically (though
   sometimes that doesn't work, hence this variable)."""))

class SocketTimeout(registry.PositiveInteger):
    """Value must be an integer greater than supybot.drivers.poll and must be
    greater than or equal to 1."""
    def setValue(self, v):
        if v < supybot.drivers.poll() or v < 1:
            self.error()
        registry.PositiveInteger.setValue(self, v)
        socket.setdefaulttimeout(self.value)

registerGlobalValue(supybot, 'defaultSocketTimeout',
    SocketTimeout(10, """Determines what the default timeout for socket objects
    will be.  This means that *all* sockets will timeout when this many seconds
    has gone by (unless otherwise modified by the author of the code that uses
    the sockets)."""))

registerGlobalValue(supybot, 'pidFile',
    registry.String('', """Determines what file the bot should write its PID
    (Process ID) to, so you can kill it more easily.  If it's left unset (as is
    the default) then no PID file will be written.  A restart is required for
    changes to this variable to take effect."""))

###
# Debugging options.
###
registerGroup(supybot, 'debug')
registerGlobalValue(supybot.debug, 'threadAllCommands',
    registry.Boolean(False, """Determines whether the bot will automatically
    thread all commands."""))
registerGlobalValue(supybot.debug, 'flushVeryOften',
    registry.Boolean(False, """Determines whether the bot will automatically
    flush all flushers *very* often.  Useful for debugging when you don't know
    what's breaking or when, but think that it might be logged."""))

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
