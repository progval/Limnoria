###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008-2009,2011, James McCoy
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
import random

from . import ircutils, registry, utils
from .utils import minisix
from .utils.net import isSocketAddress
from .version import version
from .i18n import PluginInternationalization
_ = PluginInternationalization()
if minisix.PY2:
    from urllib2 import build_opener, install_opener, ProxyHandler
else:
    from urllib.request import build_opener, install_opener, ProxyHandler

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
    value._networkValue = False
    value._channelValue = False
    return group.register(name, value)

def registerNetworkValue(group, name, value):
    value._supplyDefault = True
    value._networkValue = True
    value._channelValue = False
    g = group.register(name, value)
    gname = g._name.lower()
    for name in registry._cache.keys():
        if name.lower().startswith(gname) and len(gname) < len(name):
            name = name[len(gname)+1:] # +1 for .
            parts = registry.split(name)
            if len(parts) == 1 and parts[0] and ircutils.isChannel(parts[0]):
                # This gets the network values so they always persist.
                g.get(parts[0])()
    return g

def registerChannelValue(group, name, value, opSettable=True):
    value._supplyDefault = True
    value._networkValue = True
    value._channelValue = True
    value._opSettable = opSettable
    g = group.register(name, value)
    gname = g._name.lower()
    for name in registry._cache.keys():
        if name.lower().startswith(gname) and len(gname) < len(name):
            name = name[len(gname)+1:] # +1 for .
            parts = registry.split(name)
            if len(parts) == 2 and parts[0] and parts[0].startswith(':') \
                    and parts[1] and ircutils.isChannel(parts[1]):
                # This gets the network+channel values so they always persist.
                g.get(parts[0])()
                g.get(parts[0]).get(parts[1])()
            elif len(parts) == 1 and parts[0] and ircutils.isChannel(parts[0]):
                # Old-style variant of the above, without a network
                g.get(parts[0])()
    return g

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

def get(group, channel=None, network=None):
    return group.getSpecific(channel=channel, network=network)()

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
    __slots__ = ()
    def setValue(self, v):
        if not ircutils.isNick(v):
            self.error()
        else:
            registry.String.setValue(self, v)

class ValidNickOrEmpty(ValidNick):
    """Value must be a valid IRC nick or empty."""
    __slots__ = ()
    def setValue(self, v):
        if v != '' and not ircutils.isNick(v):
            self.error()
        else:
            registry.String.setValue(self, v)

class ValidNicks(registry.SpaceSeparatedListOf):
    __slots__ = ()
    Value = ValidNick

class ValidNickAllowingPercentS(ValidNick):
    """Value must be a valid IRC nick, with the possible exception of a %s
    in it."""
    __slots__ = ()
    def setValue(self, v):
        # If this works, it's a valid nick, aside from the %s.
        try:
            ValidNick.setValue(self, v.replace('%s', ''))
            # It's valid aside from the %s, we'll let it through.
            registry.String.setValue(self, v)
        except registry.InvalidRegistryValue:
            self.error()

class ValidNicksAllowingPercentS(ValidNicks):
    __slots__ = ()
    Value = ValidNickAllowingPercentS

class ValidChannel(registry.String):
    """Value must be a valid IRC channel name."""
    __slots__ = ('channel',)
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
        except registry.InvalidRegistryValue as e:
            e.channel = self.channel
            raise e

class ValidHostmask(registry.String):
    """Value must be a valid user hostmask."""
    __slots__ = ()
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

# Although empty version strings are theoretically allowed by the RFC,
# popular IRCds do not.
# So, we keep replacing the empty string by the current version for
# bots which are migrated from Supybot or an old version of Limnoria
# (whose default value of supybot.user is the empty string).
class VersionIfEmpty(registry.String):
    __slots__ = ()
    def __call__(self):
        ret = registry.String.__call__(self)
        if not ret:
            ret = 'Limnoria $version'
        return ret

registerGlobalValue(supybot, 'user',
    VersionIfEmpty('Limnoria $version', _("""Determines the real name which the bot sends to
    the server. A standard real name using the current version of the bot
    will be generated if this is left empty.""")))

class Networks(registry.SpaceSeparatedSetOfStrings):
    __slots__ = ()
    List = ircutils.IrcSet

registerGlobalValue(supybot, 'networks',
    Networks([], _("""Determines what networks the bot will connect to."""),
             orderAlphabetically=True))

class Servers(registry.SpaceSeparatedListOfStrings):
    __slots__ = ()
    def normalize(self, s):
        if ':' not in s:
            s += ':6667'
        return s

    def convert(self, s):
        from .drivers import Server

        s = self.normalize(s)
        (hostname, port) = s.rsplit(':', 1)

        # support for `[ipv6]:port` format
        if hostname.startswith("[") and hostname.endswith("]"):
            hostname = hostname[1:-1]

        port = int(port)
        return Server(hostname, port, None, force_tls_verification=False)

    def __call__(self):
        L = registry.SpaceSeparatedListOfStrings.__call__(self)
        return list(map(self.convert, L))

    def __str__(self):
        return ' '.join(registry.SpaceSeparatedListOfStrings.__call__(self))

    def append(self, s):
        L = registry.SpaceSeparatedListOfStrings.__call__(self)
        L.append(s)

class SocksProxy(registry.String):
    """Value must be a valid hostname:port string."""
    __slots__ = ()
    def setValue(self, v):
        # TODO: improve checks
        if ':' not in v:
            self.error()
        try:
            int(v.rsplit(':', 1)[1])
        except ValueError:
            self.error()
        super(SocksProxy, self).setValue(v)

class SpaceSeparatedSetOfChannels(registry.SpaceSeparatedListOf):
    __slots__ = ()
    sorted = True
    List = ircutils.IrcSet
    Value = ValidChannel
    def join(self, channel):
        from . import ircmsgs # Don't put this globally!  It's recursive.
        key = self.key.get(channel)()
        if key:
            return ircmsgs.join(channel, key)
        else:
            return ircmsgs.join(channel)
    def joins(self):
        from . import ircmsgs # Don't put this globally!  It's recursive.
        channels = []
        channels_with_key = []
        keys = []
        old = None
        msgs = []
        msg = None
        for channel in self():
            key = self.key.get(channel)()
            if key:
                keys.append(key)
                channels_with_key.append(channel)
            else:
                channels.append(channel)
            msg = ircmsgs.joins(channels_with_key + channels, keys)
            if len(str(msg)) > 512:
                # Use previous short enough join message
                msgs.append(old)
                # Reset and construct a new join message using the current
                # channel.
                keys = []
                channels_with_key = []
                channels = []
                if key:
                    keys.append(key)
                    channels_with_key.append(channel)
                else:
                    channels.append(channel)
                msg = ircmsgs.joins(channels_with_key + channels, keys)
            old = msg
        if msg:
            msgs.append(msg)
            return msgs
        else:
            # Let's be explicit about it
            return None

class ValidSaslMechanism(registry.OnlySomeStrings):
    __slots__ = ()
    validStrings = ('ecdsa-nist256p-challenge', 'external', 'plain',
            'scram-sha-256')

class SpaceSeparatedListOfSaslMechanisms(registry.SpaceSeparatedListOf):
    __slots__ = ()
    Value = ValidSaslMechanism

def registerNetwork(name, password='', ssl=True, sasl_username='',
        sasl_password=''):
    network = registerGroup(supybot.networks, name)
    registerGlobalValue(network, 'password', registry.String(password,
        _("""Determines what password will be used on %s.  Yes, we know that
        technically passwords are server-specific and not network-specific,
        but this is the best we can do right now.""") % name, private=True))
    registerGlobalValue(network, 'servers', Servers([],
        _("""Space-separated list of servers the bot will connect to for %s.
        Each will be tried in order, wrapping back to the first when the cycle
        is completed.""") % name))
    registerGlobalValue(network, 'channels', SpaceSeparatedSetOfChannels([],
        _("""Space-separated list of channels the bot will join only on %s.""")
        % name, private=True))

    registerGlobalValue(network, 'ssl', registry.Boolean(ssl,
        _("""Determines whether the bot will attempt to connect with SSL
        sockets to %s.""") % name))
    registerGlobalValue(network.ssl, 'serverFingerprints',
        registry.SpaceSeparatedSetOfStrings([], format(_("""Space-separated list
        of fingerprints of trusted certificates for this network.
        Supported hash algorithms are: %L.
        If non-empty, Certification Authority signatures will not be used to
        verify certificates."""), utils.net.FINGERPRINT_ALGORITHMS)))
    registerGlobalValue(network.ssl, 'authorityCertificate',
        registry.String('', _("""A certificate that is trusted to verify
        certificates of this network (aka. Certificate Authority).""")))
    registerGlobalValue(network, 'requireStarttls', registry.Boolean(False,
        _("""Deprecated config value, keep it to False.""")))

    registerGlobalValue(network, 'certfile', registry.String('',
        _("""Determines what certificate file (if any) the bot will use to
        connect with SSL sockets to %s.""") % name))
    registerChannelValue(network.channels, 'key', registry.String('',
        _("""Determines what key (if any) will be used to join the
        channel."""), private=True))
    registerGlobalValue(network, 'nick', ValidNickOrEmpty('', _("""Determines
        what nick the bot will use on this network. If empty, defaults to
        supybot.nick.""")))
    registerGlobalValue(network, 'ident', ValidNickOrEmpty('', _("""Determines
        the bot's ident string, if the server doesn't provide one by default.
        If empty, defaults to supybot.ident.""")))
    registerGlobalValue(network, 'user', registry.String('', _("""Determines
        the real name which the bot sends to the server. If empty, defaults to
        supybot.user""")))
    registerGlobalValue(network, 'umodes',
        registry.String('', _("""Determines what user modes the bot will request
        from the server when it first connects. If empty, defaults to
        supybot.protocols.irc.umodes""")))
    sasl = registerGroup(network, 'sasl')
    registerGlobalValue(sasl, 'username', registry.String(sasl_username,
        _("""Determines what SASL username will be used on %s. This should
        be the bot's account name.""") % name, private=False))
    registerGlobalValue(sasl, 'password', registry.String(sasl_password,
        _("""Determines what SASL password will be used on %s.""") \
        % name, private=True))
    registerGlobalValue(sasl, 'ecdsa_key', registry.String('',
        _("""Determines what SASL ECDSA key (if any) will be used on %s.
        The public key must be registered with NickServ for SASL
        ECDSA-NIST256P-CHALLENGE to work.""") % name, private=False))
    registerGlobalValue(sasl, 'mechanisms', SpaceSeparatedListOfSaslMechanisms(
        ['ecdsa-nist256p-challenge', 'external', 'plain'], _("""Determines
        what SASL mechanisms will be tried and in which order.""")))
    registerGlobalValue(sasl, 'required', registry.Boolean(False,
        _("""Determines whether the bot will abort the connection if the
        none of the enabled SASL mechanism succeeded.""")))
    registerGlobalValue(network, 'socksproxy', registry.String('',
        _("""If not empty, determines the hostname:port of the socks proxy that
        will be used to connect to this network.""")))
    return network

# Let's fill our networks.
for (name, s) in registry._cache.items():
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
registerChannelValue(supybot.reply.format, 'url',
    registry.String('<%s>', _("""Determines how urls should be formatted.""")))
def url(s):
    if s:
        return supybot.reply.format.url() % s
    else:
        return ''
utils.str.url = url
registerChannelValue(supybot.reply.format, 'time',
    registry.String('%Y-%m-%dT%H:%M:%S%z', _("""Determines how timestamps
    printed for human reading should be formatted. Refer to the Python
    documentation for the time module to see valid formatting characters for
    time formats.""")))
def timestamp(t):
    if t is None:
        t = time.time()
    if isinstance(t, float) or isinstance(t, int):
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

registerGroup(supybot.reply.format, 'list')
registerChannelValue(supybot.reply.format.list, 'maximumItems',
    registry.NonNegativeInteger(0, _("""Maximum number of items in a list
    before the end is replaced with 'and others'. Set to 0 to always
    show the entire list.""")))

originalCommaAndify = utils.str.commaAndify
def commaAndify(seq, *args, **kwargs):
    maximum_items = supybot.reply.format.list.maximumItems.getSpecific(
        channel=dynamic.channel,
        network=getattr(dynamic.irc, 'network', None))()
    if maximum_items:
        seq = list(seq)
        initial_length = len(seq)
        if len(seq) > maximum_items:
            seq = seq[:maximum_items]
            nb_skipped = initial_length - maximum_items + 1
            # Even though nb_skipped is always >= 2, some languages require
            # nItems for proper pluralization.
            seq[-1] = utils.str.nItems(nb_skipped, _('other'))
    return originalCommaAndify(seq, *args, **kwargs)
utils.str.commaAndify = commaAndify

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

registerChannelValue(supybot.reply, 'oneToOne',
    registry.Boolean(True, _("""Determines whether the bot will send
    multi-message replies in a single message. This defaults to True 
    in order to prevent the bot from flooding. If this is set to False
    the bot will send multi-message replies on multiple lines.""")))

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
    supybot.reply.error.inPrivate so private errors don't open a query window
    in most IRC clients.""")))
registerChannelValue(supybot.reply.error, 'noCapability',
    registry.Boolean(False, _("""Determines whether the bot will *not* provide
    details in the error
    message to users who attempt to call a command for which they do not have
    the necessary capability.  You may wish to make this True if you don't want
    users to understand the underlying security system preventing them from
    running certain commands.""")))

registerChannelValue(supybot.reply, 'inPrivate',
    registry.Boolean(False, _("""Determines whether the bot will reply
     privately when replying in a channel, rather than replying to the whole
     channel.""")))

registerChannelValue(supybot.reply, 'withNotice',
    registry.Boolean(False, _("""Determines whether the bot will reply with a
    notice when replying in a channel, rather than replying with a privmsg as
    normal.""")))

# XXX: User value.
registerGlobalValue(supybot.reply, 'withNoticeWhenPrivate',
    registry.Boolean(True, _("""Determines whether the bot will reply with a
    notice when it is sending a private message, in order not to open a /query
    window in clients.""")))

registerChannelValue(supybot.reply, 'withNickPrefix',
    registry.Boolean(True, _("""Determines whether the bot will always prefix
     the user's nick to its reply to that user's command.""")))

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
    someone when that person changes their nick.  Setting this to True
    will cause the bot to track such changes.  It defaults to False for a
    little greater security.""")))

registerChannelValue(supybot, 'alwaysJoinOnInvite',
    registry.Boolean(False, _("""Determines whether the bot will always join a
    channel when it's invited.  If this value is False, the bot will only join
    a channel if the user inviting it has the 'admin' capability (or if it's
    explicitly told to join the channel using the Admin.join command).""")))

registerChannelValue(supybot.reply, 'showSimpleSyntax',
    registry.Boolean(False, _("""Supybot normally replies with the full help
    whenever a user misuses a command.  If this value is set to True, the bot
    will only reply with the syntax of the command (the first line of the
    help) rather than the full help.""")))

class ValidPrefixChars(registry.String):
    """Value must contain only ~!@#$%^&*()_-+=[{}]\\|'\";:,<.>/?"""
    __slots__ = ()
    def setValue(self, v):
        if any([x not in '`~!@#$%^&*()_-+=[{}]\\|\'";:,<.>/?' for x in v]):
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
    Check the logs for more information."""), _("""Determines what error
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

class DatabaseRecordTemplatedString(registry.TemplatedString):
    requiredTemplates = ['text']

registerChannelValue(supybot.replies, 'databaseRecord',
    DatabaseRecordTemplatedString(_('$Type #$id: $text (added by $username at $at)'),
    _("""Format used by generic database plugins (Lart, Dunno, Prase, Success,
    Quote, ...) to show an entry. You can use the following variables:
    $type/$types/$Type/$Types (plugin name and variants), $id, $text,
    $at (creation time), $userid/$username/$nick (author).""")))

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
    __slots__ = ()
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
    __slots__ = ()
    validStrings = ('', '[]', '<>', '{}', '()')

registerChannelValue(supybot.commands.nested, 'brackets',
    ValidBrackets('[]', _("""Supybot allows you to specify what brackets
    are used for your nested commands.  Valid sets of brackets include
    [], <>, {}, and ().  [] has strong historical motivation, but <> or
    () might be slightly superior because they cannot occur in a nick.
    If this string is empty, nested commands will not be allowed in this
    channel.""")))
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
        ['Admin', 'Channel', 'Config', 'Misc', 'Owner', 'User'],
        _("""Determines what plugins automatically get precedence over all
        other plugins when selecting a default plugin for a command.  By
        default, this includes the standard loaded plugins.  You probably
        shouldn't change this if you don't know what you're doing; if you do
        know what you're doing, then also know that this set is
        case-sensitive.""")))

# For this config variable to make sense, it must no be writable via IRC.
# Make sure it is always blacklisted from the Config plugin.
registerGlobalValue(supybot.commands, 'allowShell',
    registry.Boolean(True, _("""Allows this bot's owner user to use commands
    that grants them shell access. This config variable exists in case you want
    to prevent MITM from the IRC network itself (vulnerable IRCd or IRCops)
    from gaining shell access to the bot's server by impersonating the owner.
    Setting this to False also disables plugins and commands that can be
    used to indirectly gain shell access.""")))

# supybot.commands.disabled moved to callbacks for canonicalName.

###
# supybot.abuse.  For stuff relating to abuse of the bot.
###
registerGroup(supybot, 'abuse')
registerGroup(supybot.abuse, 'flood')
registerGlobalValue(supybot.abuse.flood, 'interval',
    registry.PositiveInteger(60, _("""Determines the interval used for
    the history storage.""")))
registerGlobalValue(supybot.abuse.flood, 'command',
    registry.Boolean(True, _("""Determines whether the bot will defend itself
    against command-flooding.""")))
registerGlobalValue(supybot.abuse.flood.command, 'maximum',
    registry.PositiveInteger(12, _("""Determines how many commands users are
    allowed per minute.  If a user sends more than this many commands in any
    60 second period, they will be ignored for
    supybot.abuse.flood.command.punishment seconds.""")))
registerGlobalValue(supybot.abuse.flood.command, 'punishment',
    registry.PositiveInteger(300, _("""Determines how many seconds the bot
    will ignore users who flood it with commands.""")))
registerGlobalValue(supybot.abuse.flood.command, 'notify',
    registry.Boolean(True, _("""Determines whether the bot will notify people
    that they're being ignored for command flooding.""")))

registerGlobalValue(supybot.abuse.flood.command, 'invalid',
    registry.Boolean(True, _("""Determines whether the bot will defend itself
    against invalid command-flooding.""")))
registerGlobalValue(supybot.abuse.flood.command.invalid, 'maximum',
    registry.PositiveInteger(5, _("""Determines how many invalid commands users
    are allowed per minute.  If a user sends more than this many invalid
    commands in any 60 second period, they will be ignored for
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
    __slots__ = ()
    validStrings = ('default', 'Socket')

registerGlobalValue(supybot.drivers, 'module',
    ValidDriverModule('default', _("""Determines what driver module the 
    bot will use. Current, the only (and default) driver is Socket.""")))

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
    __slots__ = ()
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
    __slots__ = ()
    def __call__(self):
        v = super(DataFilename, self).__call__()
        dataDir = supybot.directories.data()
        if not v.startswith(dataDir):
            v = os.path.basename(v)
            v = os.path.join(dataDir, v)
        self.setValue(v)
        return v

class DataFilenameDirectory(DataFilename, Directory):
    __slots__ = ()
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
    into. Set it to /dev/null to disable backup (it is a special value,
    so it also works on Windows and systems without /dev/null).""")))
registerGlobalValue(supybot.directories, 'log',
    Directory('logs', """Determines what directory the bot will store its
    logfiles in."""))
registerGlobalValue(supybot.directories.data, 'tmp',
    DataFilenameDirectory('tmp', _("""Determines what directory temporary files
    are put into.""")))
registerGlobalValue(supybot.directories.data, 'web',
    DataFilenameDirectory('web', _("""Determines what directory files of the
    web server (templates, custom images, ...) are put into.""")))

def _update_tmp():
    utils.file.AtomicFile.default.tmpDir = supybot.directories.data.tmp
supybot.directories.data.tmp.addCallback(_update_tmp)
_update_tmp()
def _update_backup():
    utils.file.AtomicFile.default.backupDir = supybot.directories.backup
supybot.directories.backup.addCallback(_update_backup)
_update_backup()

registerGlobalValue(supybot.directories, 'plugins',
    registry.CommaSeparatedListOfStrings([], _("""Determines what directories
    the bot will look for plugins in.  Accepts a comma-separated list of
    strings.
    This means that to add another directory, you can nest the former value and
    add a new one.  E.g. you can say: bot: 'config supybot.directories.plugins
    [config supybot.directories.plugins], newPluginDirectory'.""")))

registerGlobalValue(supybot, 'plugins',
    registry.SpaceSeparatedSetOfStrings([], _("""List of all plugins that were
    ever loaded. Currently has no effect whatsoever. You probably want to use
    the 'load' or 'unload' commands, or edit supybot.plugins.<pluginname>
    instead of this."""), orderAlphabetically=True))
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
    __slots__ = ()
    def __call__(self):
        v = super(Databases, self).__call__()
        if not v:
            v = ['anydbm', 'dbm', 'cdb', 'flat', 'pickle']
            if 'sqlite' in sys.modules:
                v.insert(0, 'sqlite')
            if 'sqlite3' in sys.modules:
                v.insert(0, 'sqlite3')
            if 'sqlalchemy' in sys.modules:
                v.insert(0, 'sqlalchemy')
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

registerGroup(supybot.databases, 'networks')
registerGlobalValue(supybot.databases.networks, 'filename',
    registry.String('networks.conf', _("""Determines what filename will be used
    for the networks database.  This file will go into the directory specified
    by the supybot.directories.conf variable.""")))

# TODO This will need to do more in the future (such as making sure link.allow
# will let the link occur), but for now let's just leave it as this.
class ChannelSpecific(registry.Boolean):
    __slots__ = ()
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

registerChannelValue(supybot.databases.plugins, 'requireRegistration',
    registry.Boolean(True, _("""Determines whether the bot will require user
    registration to use 'add' commands in database-based Supybot
    plugins.""")))
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
    __slots__ = ()
    def connect(self, filename):
        from . import cdb
        basename = os.path.basename(filename)
        journalName = supybot.directories.data.tmp.dirize(basename+'.journal')
        return cdb.open_db(filename, 'c',
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
    __slots__ = ('__parent', '__dict__') # __dict__ is needed to set __doc__
    validStrings = ('exact', 'nick', 'user', 'host')
    def __init__(self, *args, **kwargs):
        assert self.validStrings, 'There must be some valid strings.  ' \
                                  'This is a bug.'
        self.__parent = super(Banmask, self)
        self.__parent.__init__(*args, **kwargs)
        self.__doc__ = format('Valid values include %L.',
                              list(map(repr, self.validStrings)))

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
        v = list(map(self.normalize, v))
        for s in v:
            if s not in self.validStrings:
                self.error()
        self.__parent.setValue(self.List(v))

    def makeBanmask(self, hostmask, options=None, channel=None, network=None):
        """Create a banmask from the given hostmask.  If a style of banmask
        isn't specified via options, the value of
        conf.supybot.protocols.irc.banmask is used.

        options - A list specifying which parts of the hostmask should
        explicitly be matched: nick, user, host.  If 'exact' is given, then
        only the exact hostmask will be used."""
        if not channel:
            channel = dynamic.channel
        if not network:
            network = dynamic.irc.network
        (nick, user, host) = ircutils.splitHostmask(hostmask)
        bnick = '*'
        buser = '*'
        bhost = '*'
        if not options:
            options = supybot.protocols.irc.banmask.getSpecific(
                network, channel)()
        for option in options:
            if option == 'nick':
                bnick = nick
            elif option == 'user':
                buser = user
            elif option == 'host':
                bhost = host
            elif option == 'exact':
                return hostmask
        if (bnick, buser, bhost) == ('*', '*', '*') and \
                ircutils.isUserHostmask(hostmask):
            return hostmask
        return ircutils.joinHostmask(bnick, buser, bhost)

registerChannelValue(supybot.protocols.irc, 'banmask',
    Banmask(['host'], _("""Determines what will be used as the
    default banmask style.""")))

registerGlobalValue(supybot.protocols.irc, 'strictRfc',
    registry.Boolean(False, _("""Determines whether the bot will strictly
    follow the RFC; currently this only affects what strings are
    considered to be nicks. If you're using a server or a network that
    requires you to message a nick such as services@this.network.server
    then you you should set this to False.""")))

registerGlobalValue(supybot.protocols.irc, 'experimentalExtensions',
    registry.Boolean(False, _("""Determines whether the bot will enable
    draft/experimental extensions of the IRC protocol. Setting this to True
    may break your bot at any time without warning and/or break your
    configuration irreversibly. So keep it False unless you know what you are
    doing.""")))

registerGlobalValue(supybot.protocols.irc, 'certfile',
    registry.String('', _("""Determines what certificate file (if any) the bot
    will use connect with SSL sockets by default.""")))

registerGlobalValue(supybot.protocols.irc, 'umodes',
    registry.String('', _("""Determines what user modes the bot will request
    from the server when it first connects.  Many people might choose +i; some
    networks allow +x, which indicates to the auth services on those networks
    that you should be given a fake host.""")))

registerGlobalValue(supybot.protocols.irc, 'vhost',
    registry.String('', _("""Determines what vhost the bot will bind to before
    connecting a server (IRC, HTTP, ...) via IPv4.""")))

registerGlobalValue(supybot.protocols.irc, 'vhostv6',
    registry.String('', _("""Determines what vhost the bot will bind to before
    connecting a server (IRC, HTTP, ...) via IPv6.""")))

registerGlobalValue(supybot.protocols.irc, 'maxHistoryLength',
    registry.Integer(1000, _("""Determines how many old messages the bot will
    keep around in its history.  Changing this variable will not take effect
    on a network until it is reconnected.""")))

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
    registry.PositiveInteger(8192, _("""Determines how many bytes the bot will
    'peek' at when looking through a URL for a doctype or title or something
    similar.  It'll give up after it reads this many bytes, even if it hasn't
    found what it was looking for.""")))

class HttpProxy(registry.String):
    """Value must be a valid hostname:port string."""
    __slots__ = ()
    def setValue(self, v):
        proxies = {}
        if v != "":
            if isSocketAddress(v):
                proxies = {
                    'http': v,
                    'https': v
                    }
            else:
                self.error()
        proxyHandler = ProxyHandler(proxies)
        proxyOpenerDirector = build_opener(proxyHandler)
        install_opener(proxyOpenerDirector)
        super(HttpProxy, self).setValue(v)

registerGlobalValue(supybot.protocols.http, 'proxy',
    HttpProxy('', _("""Determines what HTTP proxy all HTTP requests should go
    through.  The value should be of the form 'host:port'.""")))
utils.web.proxy = supybot.protocols.http.proxy

def defaultHttpHeaders(network, channel):
    """Returns the default HTTP headers to use for this channel/network."""
    headers = utils.web.baseDefaultHeaders.copy()
    try:
        language = supybot.protocols.http.requestLanguage.getSpecific(
                network, channel)()
        agent = supybot.protocols.http.userAgents.getSpecific(
                network, channel)()
    except registry.NonExistentRegistryEntry:
        pass # Starting up; headers will be set by HttpRequestLanguage/UserAgents later
    else:
        if language:
            headers['Accept-Language'] = language
        elif 'Accept-Language' in headers:
            del headers['Accept-Language']
        if agent:
            agent = random.choice(agent).strip()
            if agent:
                headers['User-agent'] = agent
    return headers

class HttpRequestLanguage(registry.String):
    """Must be a valid HTTP Accept-Language value."""
    __slots__ = ()
    def setValue(self, v):
        super(HttpRequestLanguage, self).setValue(v)
        utils.web.defaultHeaders = defaultHttpHeaders(None, None)

class HttpUserAgents(registry.CommaSeparatedListOfStrings):
    """Must be a valid HTTP User-Agent value."""
    __slots__ = ()
    def setValue(self, v):
        super(HttpUserAgents, self).setValue(v)
        utils.web.defaultHeaders = defaultHttpHeaders(None, None)

registerChannelValue(supybot.protocols.http, 'requestLanguage',
    HttpRequestLanguage('', _("""If set, the Accept-Language HTTP header will be set to this
    value for requests. Useful for overriding the auto-detected language based on
    the server's location.""")))


registerChannelValue(supybot.protocols.http, 'userAgents',
    HttpUserAgents([], _("""If set, the User-Agent HTTP header will be set to a randomly
    selected value from this comma-separated list of strings for requests.""")))

###
# supybot.protocols.ssl
###
registerGroup(supybot.protocols, 'ssl')
registerGlobalValue(supybot.protocols.ssl, 'verifyCertificates',
    registry.Boolean(False, _("""Determines whether server certificates
    will be verified, which checks whether the server certificate is signed
    by a known certificate authority, and aborts the connection if it is not.
    This is assumed to be True of serverFingerprints or authorityCertificate
    is set.""")))


###
# HTTP server
###
registerGroup(supybot, 'servers')
registerGroup(supybot.servers, 'http')

class IP(registry.String):
    """Value must be a valid IP."""
    __slots__ = ()
    def setValue(self, v):
        if v and not utils.net.isIP(v):
            self.error()
        else:
            registry.String.setValue(self, v)

class ListOfIPs(registry.SpaceSeparatedListOfStrings):
    __slots__ = ()
    Value = IP

registerGlobalValue(supybot.servers.http, 'singleStack',
    registry.Boolean(True, _("""If true, uses IPV6_V6ONLY to disable
    forwaring of IPv4 traffic to IPv6 sockets. On *nix, has the same
    effect as setting kernel variable net.ipv6.bindv6only to 1.""")))
registerGlobalValue(supybot.servers.http, 'hosts4',
    ListOfIPs(['0.0.0.0'], _("""Space-separated list of IPv4 hosts the HTTP server
    will bind.""")))
registerGlobalValue(supybot.servers.http, 'hosts6',
    ListOfIPs(['::0'], _("""Space-separated list of IPv6 hosts the HTTP server will
    bind.""")))
registerGlobalValue(supybot.servers.http, 'port',
    registry.Integer(8080, _("""Determines what port the HTTP server will
    bind.""")))
registerGlobalValue(supybot.servers.http, 'keepAlive',
    registry.Boolean(False, _("""Determines whether the server will stay
    alive if no plugin is using it. This also means that the server will
    start even if it is not used.""")))
registerGlobalValue(supybot.servers.http, 'favicon',
    registry.String('', _("""Determines the path of the file served as
    favicon to browsers.""")))
registerGlobalValue(supybot.servers.http, 'publicUrl',
    registry.String('', _("""Determines the public URL of the server.
    By default it is http://<hostname>:<port>/, but you will want to change
    this if there is a reverse proxy (nginx, apache, ...) in front of
    the bot.""")))


###
# Especially boring stuff.
###
registerGlobalValue(supybot, 'defaultIgnore',
    registry.Boolean(False, _("""Determines whether the bot will ignore
    unidentified users by default.  Of course, that'll make it
    particularly hard for those users to register or identify with the bot
    without adding their hostmasks, but that's your problem to solve.""")))


registerGlobalValue(supybot, 'externalIP',
   IP('', _("""A string that is the external IP of the bot.  If this is the
   empty string, the bot will attempt to find out its IP dynamically (though
   sometimes that doesn't work, hence this variable). This variable is not used
   by Limnoria and its built-in plugins: see supybot.protocols.irc.vhost /
   supybot.protocols.irc.vhost6 to set the IRC bind host, and
   supybot.servers.http.hosts4 / supybot.servers.http.hosts6 to set the HTTP
   server bind host.""")))

class SocketTimeout(registry.PositiveInteger):
    """Value must be an integer greater than supybot.drivers.poll and must be
    greater than or equal to 1."""
    __slots__ = ()
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
