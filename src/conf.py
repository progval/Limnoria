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

import fix

import os
import sys
import string

import utils
import registry
import ircutils

installDir = os.path.dirname(os.path.dirname(sys.modules[__name__].__file__))
_srcDir = os.path.join(installDir, 'src')
_pluginsDir = os.path.join(installDir, 'plugins')

###
# allowEval: True if the owner (and only the owner) should be able to eval
#            arbitrary Python code.  This is specifically *not* a registry
#            variable because it shouldn't be modifiable in the bot.
###
allowEval = False


supybot = registry.Group()
supybot.setName('supybot')
supybot.registerGroup('plugins') # This will be used by plugins, but not here.

def registerPlugin(name, currentValue=None):
    supybot.plugins.registerGroup(
        name,
        registry.GroupWithValue(registry.Boolean(False, """Determines whether
        this plugin is loaded by default.""")))
    if currentValue is not None:
        supybot.plugins.getChild(name).setValue(currentValue)

def registerChannelValue(group, name, value):
    group.registerGroup(name, registry.GroupWithDefault(value))

def registerGlobalValue(group, name, value):
    group.registerGroup(name, registry.GroupWithValue(value))

def registerGroup(group, name, Group=None):
    group.registerGroup(name, Group)

class ValidNick(registry.String):
    def setValue(self, v):
        if not ircutils.isNick(v):
            raise registry.InvalidRegistryValue, \
                  'Value must be a valid IRC nick.'
        else:
            registry.String.setValue(self, v)

class ValidChannel(registry.String):
    def setValue(self, v):
        if not ircutils.isChannel(v):
            raise registry.InvalidRegistryValue, \
                  'Value must be a valid IRC channel name.'
        else:
            registry.String.setValue(self, v)

supybot.register('nick', ValidNick('supybot',
"""Determines the bot's nick."""))

supybot.register('ident', ValidNick('supybot',
"""Determines the bot's ident."""))

supybot.register('user', registry.String('supybot', """Determines the user
the bot sends to the server."""))

supybot.register('password', registry.String('', """Determines the password to
be sent to the server if it requires one."""))

# TODO: Make this check for validity.
supybot.register('server', registry.String('irc.freenode.net', """Determines
what server the bot connects to."""))

class SpaceSeparatedListOfChannels(registry.SeparatedListOf):
    Value = ValidChannel
    def splitter(self, s):
        return s.split()
    joiner = ' '.join

supybot.register('channels', SpaceSeparatedListOfChannels(['#supybot'], """
Determines what channels the bot will join when it connects to the server."""))

supybot.registerGroup('databases')
supybot.databases.registerGroup('users')
supybot.databases.registerGroup('channels')
supybot.databases.users.register('filename', registry.String('users.conf', """
Determines what filename will be used for the users database.  This file will
go into the directory specified by the supybot.directories.conf
variable."""))
supybot.databases.channels.register('filename',registry.String('channels.conf',
"""Determines what filename will be used for the channels database.  This file
will go into the directory specified by the supybot.directories.conf
variable."""))
                                                                
supybot.registerGroup('directories')
supybot.directories.register('conf', registry.String('conf', """
Determines what directory configuration data is put into."""))
supybot.directories.register('data', registry.String('data', """
Determines what directory data is put into."""))
supybot.directories.register('plugins',
registry.CommaSeparatedListOfStrings([_srcDir,_pluginsDir],
"""Determines what directories the bot will look for plugins in."""))

supybot.register('humanTimestampFormat', registry.String('%I:%M %p, %B %d, %Y',
"""Determines how timestamps printed for human reading should be formatted.
Refer to the Python documentation for the time module to see valid formatting
characteres for time formats."""))

class IP(registry.String):
    def setValue(self, v):
        if v and not (utils.isIP(v) or utils.isIPV6(v)):
            raise registry.InvalidRegistryValue, 'Value must be a valid IP.'
        else:
            registry.String.setValue(self, v)
        
supybot.register('externalIP', IP('', """A string that is the external IP of
the bot.  If this is the empty string, the bot will attempt to find out its IP
dynamically (though sometimes that doesn't work, hence this variable)."""))

# XXX Should this (and a few others) be made into a group 'network' or
# 'server' or something?
supybot.register('throttleTime', registry.Float(1.0, """A floating point
number of seconds to throttle queued messages -- that is, messages will not
be sent faster than once per throttleTime seconds."""))

supybot.register('snarfThrottle', registry.Float(10.0, """A floating point
number of seconds to throttle snarfed URLs, in order to prevent loops between
two bots snarfing the same URLs and having the snarfed URL in the output of
the snarf message."""))

supybot.register('threadAllCommands', registry.Boolean(False, """Determines
whether the bot will automatically thread all commands.  At this point this
option exists almost exclusively for debugging purposes; it can do very little
except to take up more CPU."""))

supybot.register('httpPeekSize', registry.PositiveInteger(4096, """Determines
how many bytes the bot will 'peek' at when looking through a URL for a
doctype or title or something similar.  It'll give up after it reads this many
bytes."""))

###
# Reply/error tweaking.
###
supybot.registerGroup('reply')
supybot.reply.register('oneToOne', registry.Boolean(True, """Determines whether
the bot will send multi-message replies in a single messsage or in multiple
messages.  For safety purposes (so the bot can't possibly flood) it will
normally send everything in a single message."""))

supybot.reply.register('detailedErrors', registry.Boolean(True, """Determines
whether error messages that result from bugs in the bot will show a detailed
error message (the uncaught exception) or a generic error message."""))

supybot.reply.register('errorInPrivate', registry.Boolean(False, """
Determines whether the bot will send error messages to users in private."""))

supybot.reply.register('noCapabilityError', registry.Boolean(False, """
Determines whether the bot will send an error message to users who attempt to
call a command for which they do not have the necessary capability.  You may
wish to make this False if you don't want users to understand the underlying
security system preventing them from running certain commands."""))

supybot.reply.register('whenNotCommand', registry.Boolean(True, """
Determines whether the bot will reply with an error message when it is
addressed but not given a valid command.  If this value is False, the bot
will remain silent."""))

supybot.reply.register('withPrivateNotice', registry.Boolean(False, """
Determines whether the bot will reply with a private notice to users rather
than sending a message to a channel.  Private notices are particularly nice
because they don't generally cause IRC clients to open a new query window."""))

supybot.reply.register('withNickPrefix', registry.Boolean(True, """
Determines whether the bot will always prefix the user's nick to its reply to
that user's command."""))

supybot.reply.register('whenAddressedByNick', registry.Boolean(True, """
Determines whether the bot will reply when people address it by its nick,
rather than with a prefix character."""))

supybot.reply.register('whenNotAddressed', registry.Boolean(False, """
Determines whether the bot should attempt to reply to all messages even if they
don't address it (either via its nick or a prefix character).  If you set this
to True, you almost certainly want to set supybot.reply.whenNotCommand to
False."""))

# XXX: Removed requireRegistration: it wasn't being used.

supybot.reply.register('requireChannelCommandsToBeSentInChannel',
registry.Boolean(False, """Determines whether the bot will allow you to send
channel-related commands outside of that channel.  Sometimes people find it
confusing if a channel-related command (like Filter.outfilter) changes the
behavior of the channel but was sent outside the channel itself."""))

supybot.register('followIdentificationThroughNickChanges',
registry.Boolean(False, """Determines whether the bot will unidentify someone
when that person changes his or her nick.  Setting this to True will cause the
bot to track such changes.  It defaults to false for a little greater security.
"""))

supybot.register('alwaysJoinOnInvite', registry.Boolean(False, """Determines
whether the bot will always join a channel when it's invited.  If this value
is False, the bot will only join a channel if the user inviting it has the
'admin' capability (or if it's explicitly told to join the channel using the
Admin.join command)"""))

supybot.register('pipeSyntax', registry.Boolean(False, """Supybot allows
nested commands; generally, commands are nested via square brackets.  Supybot
can also provide a syntax more similar to UNIX pipes.  The square bracket
nesting syntax is always enabled, but when this value is True, users can also
nest commands by saying 'bot: foo | bar' instead of 'bot: bar [foo]'."""))

supybot.register('showSimpleSyntax', registry.Boolean(False, """Supybot
normally replies with the full help whenever a user misuses a command.  If this
value is set to True, the bot will only reply with the syntax of the command
(the first line of the docstring) rather than the full help."""))

supybot.register('defaultCapabilities',
registry.CommaSeparatedSetOfStrings(['-owner', '-admin', '-trusted'], """
These are the capabilities that are given to everyone by default.  If they are
normal capabilities, then the user will have to have the appropriate
anti-capability if you want to override these capabilities; if they are
anti-capabilities, then the user will have to have the actual capability to
override these capabilities.  See docs/CAPABILITIES if you don't understand
why these default to what they do."""))

###
# Replies
###
supybot.registerGroup('replies')

registerChannelValue(supybot.replies, 'error',
    registry.NormalizedString("""An error has occurred and has been logged.
    Please contact this bot's administrator for more information.""", """
    Determines what error message the bot gives when it wants to be
    ambiguous."""))

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
    to do.""", """Dertermines what generic error message is given when the bot
    is telling someone that they aren't cool enough to use the command they
    tried to use, and the author of the code calling errorNoCapability didn't
    provide an explicit capability for whatever reason."""))

registerChannelValue(supybot.replies, 'success',
    registry.NormalizedString("""The operation succeeded.""", """Determines
    what message the bot replies with when a command succeeded."""))

registerChannelValue(supybot.replies, 'incorrectAuthentication',
    registry.NormalizedString("""Your hostmask doesn't match or your password
    is wrong.""", """Determines what message the bot replies with when someone
    tries to use a command that requires being identified or having a password
    and neither credential is correct."""))

registerChannelValue(supybot.replies, 'noUser',
    registry.NormalizedString("""I can't find that user in my user
    database.  If you didn't give a user name, then I don't know what *your*
    user is, and you'll need to identify before this command will work.""",
    """Determines what error message the bot replies with when someone tries
    to accessing some information on a user the bot doesn't know about."""))

registerChannelValue(supybot.replies, 'notRegistered',
    registry.NormalizedString("""You must be registered to use this command.
    If you are already registered, you must either identify (using the identify
    command) or add a hostmask matching your current hostmask (using the
    addhostmask command).""", """Determines what error message the bot replies
    with when someone tries to do something that requires them to be registered
    but they're not currently recognized."""))

registerChannelValue(supybot.replies, 'requiresPrivacy',
    registry.NormalizedString("""That operation cannot be done in a
    channel.""", """Determines what error messages the bot sends to people who
    try to do things in a channel that really should be done in private."""))

supybot.replies.register('possibleBug', registry.NormalizedString("""This may
be a bug.  If you think it is, please file a bug report at
<http://sourceforge.net/tracker/?func=add&group_id=58965&atid=489447>.""",
"""Determines what message the bot sends when it thinks you've encountered a
bug that the developers don't know about."""))
###
# End supybot.replies.
###

supybot.register('pingServer', registry.Boolean(True, """Determines whether
the bot will send PINGs to the server it's connected to in order to keep the
connection alive and discover earlier when it breaks.  Really, this option
only exists for debugging purposes: you always should make it True unless
you're testing some strange server issues."""))

supybot.register('pingInterval', registry.Integer(120, """Determines the
number of seconds between sending pings to the server, if pings are being sent
to the server."""))

supybot.register('maxHistoryLength', registry.Integer(1000, """Determines
how many old messages the bot will keep around in its history.  Changing this
variable will not take effect until the bot is restarted."""))

supybot.register('nickmods', registry.CommaSeparatedListOfStrings(
    '__%s__,%s^,%s`,%s_,%s__,_%s,__%s,[%s]'.split(','),
    """A list of modifications to be made to a nick when the nick the bot tries
    to get from the server is in use.  There should be one %s in each string;
    this will get replaced with the original nick."""))

supybot.register('defaultAllow', registry.Boolean(True, """Determines whether
the bot by default will allow users to run commands.  If this is disabled, a
user will have to have the capability for whatever command he wishes to run.
"""))

supybot.register('defaultIgnore', registry.Boolean(False, """Determines
whether the bot will ignore unregistered users by default.  Of course, that'll
make it particularly hard for those users to register with the bot, but that's
your problem to solve."""))

supybot.register('ignores', registry.CommaSeparatedListOfStrings('', """
A list of hostmasks ignored by the bot.  Add people you don't like to here.
"""))

class ValidPrefixChars(registry.String):
    def set(self, s):
        registry.String.set(self, s)
        if self.value.translate(string.ascii,
                                '`~!@#$%^&*()_-+=[{}]\\|\'";:,<.>/?'):
            raise registry.InvalidRegistryValue, \
                  'Value must contain only ~!@#$%^&*()_-+=[{}]\\|\'";:,<.>/?'

supybot.register('prefixChars', ValidPrefixChars('@', """Determines what prefix
characters the bot will reply to.  A prefix character is a single character
that the bot will use to determine what messages are addressed to it; when
there are no prefix characters set, it just uses its nick."""))

###
# Driver stuff.
###
supybot.registerGroup('drivers')
supybot.drivers.register('poll', registry.Float(1.0, """Determines the default
length of time a driver should block waiting for input."""))

class ValidDriverModule(registry.String):
    def set(self, s):
        original = getattr(self, 'value', self.default)
        registry.String.set(self, s)
        if self.value not in ('socketDrivers',
                              'twistedDrivers',
                              'asyncoreDrivers'):
            self.value = original
            raise registry.InvalidRegistryValue, \
                  'Value must be one of "socketDrivers", "asyncoreDrivers", ' \
                  'or twistedDrivers.'
        else:
            # TODO: check to make sure Twisted is available if it's set to
            # twistedDrivers.
            pass

supybot.drivers.register('module', ValidDriverModule('socketDrivers', """
Determines what driver module the bot will use.  socketDrivers, a simple
driver based on timeout sockets, is used by default because it's simple and
stable.  asyncoreDrivers is a bit older (and less well-maintained) but allows
you to integrate with asyncore-based applications.  twistedDrivers is very
stable and simple, and if you've got Twisted installed, is probably your best
bet."""))

###############################
###############################
###############################
# DO NOT EDIT PAST THIS POINT #
###############################
###############################
###############################
version ='0.76.1'

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
