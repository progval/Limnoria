###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2010, James McCoy
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

"""
This module provides the basic IrcMsg object used throughout the bot to
represent the actual messages.  It also provides several helper functions to
construct such messages in an easier way than the constructor for the IrcMsg
object (which, as you'll read later, is quite...full-featured :))
"""

import re
import sys
import time
import base64
import datetime
import warnings
import functools

from . import conf, ircutils, utils
from .utils.iter import all
from .utils import minisix

###
# IrcMsg class -- used for representing IRC messages acquired from a network.
###

class MalformedIrcMsg(ValueError):
    pass

# http://ircv3.net/specs/core/message-tags-3.2.html#escaping-values
SERVER_TAG_ESCAPE = [
    ('\\', '\\\\'), # \ -> \\
    (' ', r'\s'),
    (';', r'\:'),
    ('\r', r'\r'),
    ('\n', r'\n'),
    ]
escape_server_tag_value = utils.str.MultipleReplacer(
        dict(SERVER_TAG_ESCAPE))

_server_tag_unescape = {k: v for (v, k) in SERVER_TAG_ESCAPE}
_escape_sequence_pattern = re.compile(r'\\.?')
def _unescape_replacer(m):
    escape_sequence = m.group(0)
    unescaped = _server_tag_unescape.get(escape_sequence)
    if unescaped is None:
        # Matches both a lone \ at the end and a \ followed by an "invalid"
        # character. In both cases, the \ must be dropped.
        return escape_sequence[1:]
    return unescaped
def unescape_server_tag_value(s):
    return _escape_sequence_pattern.sub(_unescape_replacer, s)

def _parse_server_tags(s):
    server_tags = {}
    for tag in s.split(';'):
        if '=' not in tag:
            server_tags[sys.intern(tag)] = None
        else:
            (key, value) = tag.split('=', 1)
            value = unescape_server_tag_value(value)
            if value == '':
                # "Implementations MUST interpret empty tag values (e.g. foo=)
                # as equivalent to missing tag values (e.g. foo)."
                value = None
            server_tags[sys.intern(key)] = value
    return server_tags
def _format_server_tags(server_tags):
    parts = []
    for (key, value) in server_tags.items():
        if value is None:
            parts.append(key)
        else:
            parts.append('%s=%s' % (key, escape_server_tag_value(value)))
    return '@' + ';'.join(parts)

def split_args(s, maxsplit=-1):
    """Splits on spaces, treating consecutive spaces as one."""
    return list(filter(bool, s.split(' ', maxsplit=maxsplit)))

class IrcMsg(object):
    """Class to represent an IRC message.

    As usual, ignore attributes that begin with an underscore.  They simply
    don't exist.  Instances of this class are *not* to be modified, since they
    are hashable.  Public attributes of this class are .prefix, .command,
    .args, .nick, .user, and .host.

    The constructor for this class is pretty intricate.  It's designed to take
    any of three major (sets of) arguments.

    Called with no keyword arguments, it takes a single string that is a raw
    IRC message (such as one taken straight from the network).

    Called with keyword arguments, it *requires* a command parameter.  Args is
    optional, but with most commands will be necessary.  Prefix is obviously
    optional, since clients aren't allowed (well, technically, they are, but
    only in a completely useless way) to send prefixes to the server.

    Since this class isn't to be modified, the constructor also accepts a 'msg'
    keyword argument representing a message from which to take all the
    attributes not provided otherwise as keyword arguments.  So, for instance,
    if a programmer wanted to take a PRIVMSG they'd gotten and simply redirect
    it to a different source, they could do this:

    IrcMsg(prefix='', args=(newSource, otherMsg.args[1]), msg=otherMsg)

    .. attribute:: command

        The IRC command of the message (eg. PRIVMSG, NOTICE, MODE, QUIT, ...).
        In case of "split" commands (eg. CAP LS), this is only the first part,
        and the other parts are in `args`.

    .. attribute:: args

        Arguments of the IRC command (including subcommands).
        For example, for a PRIVMSG,
        `args = ('#channel', 'content of the message')`.

    .. attribute:: channel

        The name of the channel this message was received on or will be sent
        to; or None if this is not a channel message (PRIVMSG to a nick, QUIT,
        etc.)

        `msg.args[0]` was formerly used to get the channel, but it had several
        pitfalls (such as needing server-specific channel vs nick detection,
        and needing to strip statusmsg characters).

    .. attribute:: prefix

        `nick!user@host` of the author of the message, or None.

    .. attribute:: nick

        Nickname of the author of the message, or None.

    .. attribute:: user

        Username/ident of the author of the message, or None.

    .. attribute:: host

        Hostname of the author of the message, or None.

    .. attribute:: time

       Float timestamp of the moment the message was sent by the server.
       If the server does not support `server-time`, this falls back to the
       value of `time.time()` when the message was received.

    .. attribute:: server_tags

        Dictionary of IRCv3 message tags. `None` values indicate the tag is
        present but has no value.

        This includes client tags; the name is meant to disambiguate wrt the
        `tags` attribute, which are tags used internally by Supybot/Limnoria.

    .. attribute:: reply_env

        (Mutable) dictionary of internal key:value pairs, all of which must be
        strings.

        Several plugins offer string templating, such as the 'echo' command in
        the Misc plugin; which replace `$variable` with a value.

        Adding values to this dictionary allows access to these values from
        these commands; this is especially useful when nesting commands.

    .. attribute:: tags

        (Mutable) dictionary of internal key:value pairs on this message.

        This is not to be confused with IRCv3 message tags; these are
        stored as `server_tags` (including the client tags).
    """
    # It's too useful to be able to tag IrcMsg objects with extra, unforeseen
    # data.  Goodbye, __slots__.
    # On second thought, let's use methods for tagging.
    __slots__ = ('args', 'command', 'host', 'nick', 'prefix', 'user',
                 '_hash', '_str', '_repr', '_len', 'tags', 'reply_env',
                 'server_tags', 'time', 'channel')

    def __init__(self, s='', command='', args=(), prefix='', server_tags=None, msg=None,
            reply_env=None):
        assert not (msg and s), 'IrcMsg.__init__ cannot accept both s and msg'
        if not s and not command and not msg:
            raise MalformedIrcMsg('IRC messages require a command.')
        self._str = None
        self._repr = None
        self._hash = None
        self._len = None
        self.reply_env = reply_env
        self.tags = {}
        if s:
            originalString = s
            try:
                if not s.endswith('\n'):
                    s += '\n'
                self._str = s
                if s[0] == '@':
                    (server_tags, s) = s.split(' ', 1)
                    self.server_tags = _parse_server_tags(server_tags[1:])
                else:
                    self.server_tags = {}
                if ' :' in s: # Note the space: IPV6 addresses are bad w/o it.
                    s, last = s.split(' :', 1)
                    self.args = split_args(s)
                    self.args.append(last.rstrip('\r\n'))
                else:
                    self.args = split_args(s.rstrip('\r\n'))
                if self.args[0][0] == ':':
                    self.prefix = self.args.pop(0)[1:]
                else:
                    self.prefix = ''
                self.command = self.args.pop(0)
                if 'time' in self.server_tags:
                    s = self.server_tags['time']
                    date = datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ')
                    date = minisix.make_datetime_utc(date)
                    self.time = minisix.datetime__timestamp(date)
                else:
                    self.time = time.time()
            except (IndexError, ValueError):
                raise MalformedIrcMsg(repr(originalString))
        else:
            if msg is not None:
                if prefix:
                    self.prefix = prefix
                else:
                    self.prefix = msg.prefix
                if command:
                    self.command = command
                else:
                    self.command = msg.command
                if args:
                    self.args = args
                else:
                    self.args = msg.args
                if reply_env:
                    self.reply_env = reply_env
                elif msg.reply_env:
                    self.reply_env = msg.reply_env.copy()
                else:
                    self.reply_env = None
                self.tags = msg.tags.copy()
                if server_tags is None:
                    self.server_tags = msg.server_tags.copy()
                else:
                    self.server_tags = server_tags
                self.time = msg.time
            else:
                self.prefix = prefix
                self.command = command
                assert all(ircutils.isValidArgument, args), args
                self.args = args
                self.time = None
                if server_tags is None:
                    self.server_tags = {}
                else:
                    self.server_tags = server_tags
        self.prefix = sys.intern(self.prefix)
        self.command = sys.intern(self.command)
        self.args = tuple(self.args)
        if isUserHostmask(self.prefix):
            (self.nick,self.user,self.host)=ircutils.splitHostmask(self.prefix)
        else:
            (self.nick, self.user, self.host) = (self.prefix,)*3

    def __str__(self):
        if self._str is not None:
            return self._str
        if self.prefix:
            if len(self.args) > 1:
                s = ':%s %s %s :%s\r\n' % (
                    self.prefix, self.command,
                    ' '.join(self.args[:-1]), self.args[-1])
            else:
                if self.args:
                    s = ':%s %s :%s\r\n' % (
                        self.prefix, self.command, self.args[0])
                else:
                    s = ':%s %s\r\n' % (self.prefix, self.command)
        else:
            if len(self.args) > 1:
                s = '%s %s :%s\r\n' % (
                    self.command,
                    ' '.join(self.args[:-1]), self.args[-1])
            else:
                if self.args:
                    s = '%s :%s\r\n' % (self.command, self.args[0])
                else:
                    s = '%s\r\n' % self.command

        if self.server_tags:
            s = _format_server_tags(self.server_tags) + ' ' + s

        self._str = s

        return self._str

    def __len__(self):
        return len(str(self))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
               hash(self) == hash(other) and \
               self.command == other.command and \
               self.prefix == other.prefix and \
               self.args == other.args and \
               self.server_tags == other.server_tags
    __req__ = __eq__ # I don't know exactly what this does, but it can't hurt.

    def __ne__(self, other):
        return not (self == other)
    __rne__ = __ne__ # Likewise as above.

    def __hash__(self):
        if self._hash is not None:
            return self._hash
        self._hash = hash(self.command) ^ \
                     hash(self.prefix) ^ \
                     hash(repr(self.args))
        return self._hash

    def __repr__(self):
        if self._repr is not None:
            return self._repr
        self._repr = format(
            'IrcMsg(server_tags=%r, prefix=%q, command=%q, args=%r)',
            self.server_tags, self.prefix, self.command, self.args)
        return self._repr

    def __reduce__(self):
        return (self.__class__, (str(self),))

    def tag(self, tag, value=True):
        """Affect an internal key:value pair to this message.

        This is not to be confused with IRCv3 message tags; these are
        stored as `server_tags` (including the client tags)."""
        self.tags[tag] = value

    def tagged(self, tag):
        """Get the value affected to a tag, or None if it is not set.."""
        return self.tags.get(tag) # Returns None if it's not there.

    def __getattr__(self, attr):
        if attr.startswith('__'): # Since PEP 487, Python calls __set_name__
            raise AttributeError("'%s' object has no attribute '%s'" %
                    (self.__class__.__name__, attr))
        if attr in self.tags:
            warnings.warn("msg.<tagname> is deprecated. Use "
                    "msg.tagged('<tagname>') or msg.tags['<tagname>']"
                    "instead.", DeprecationWarning)
            return self.tags[attr]
        else:
            # TODO: make this raise AttributeError
            return None


def isCtcp(msg):
    """Returns whether or not msg is a CTCP message."""
    return msg.command in ('PRIVMSG', 'NOTICE') and \
           msg.args[1].startswith('\x01') and \
           msg.args[1].endswith('\x01') and \
           len(msg.args[1]) >= 2

def isAction(msg):
    """A predicate returning true if the PRIVMSG in question is an ACTION"""
    if isCtcp(msg):
        s = msg.args[1]
        payload = s[1:-1] # Chop off \x01.
        command = payload.split(None, 1)[0]
        return command == 'ACTION'
    else:
        return False

def isSplit(msg):
    if msg.command == 'QUIT':
        # It's a quit.
        quitmsg = msg.args[0]
        if not quitmsg.startswith('"') and not quitmsg.endswith('"'):
            # It's not a user-generated quitmsg.
            servers = quitmsg.split()
            if len(servers) == 2:
                # We could check if domains match, or if the hostnames actually
                # resolve, but we're going to put that off for now.
                return True
    return False

_unactionre = re.compile(r'^\x01ACTION\s+(.*)\x01$')
def unAction(msg):
    """Returns the payload (i.e., non-ACTION text) of an ACTION msg."""
    assert isAction(msg)
    return _unactionre.match(msg.args[1]).group(1)

def _escape(s):
    s = s.replace('&', '&amp;')
    s = s.replace('"', '&quot;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    return s

def toXml(msg, pretty=True, includeTime=True):
    assert msg.command == _escape(msg.command)
    L = []
    L.append('<msg command="%s" prefix="%s"'%(msg.command,_escape(msg.prefix)))
    if includeTime:
        L.append(' time="%s"' % time.time())
    L.append('>')
    if pretty:
        L.append('\n')
    for arg in msg.args:
        if pretty:
            L.append('    ')
        L.append('<arg>%s</arg>' % _escape(arg))
        if pretty:
            L.append('\n')
    L.append('</msg>\n')
    return ''.join(L)

def prettyPrint(msg, addRecipients=False, timestampFormat=None, showNick=True):
    """Provides a client-friendly string form for messages.

    IIRC, I copied BitchX's (or was it XChat's?) format for messages.
    """
    def nickorprefix():
        return msg.nick or msg.prefix
    def nick():
        if addRecipients:
            return '%s/%s' % (msg.nick, msg.args[0])
        else:
            return msg.nick
    if msg.command == 'PRIVMSG':
        m = _unactionre.match(msg.args[1])
        if m:
            s = '* %s %s' % (nick(), m.group(1))
        else:
            if not showNick:
                s = '%s' % msg.args[1]
            else:
                s = '<%s> %s' % (nick(), msg.args[1])
    elif msg.command == 'NOTICE':
        if not showNick:
            s = '%s' % msg.args[1]
        else:
            s = '-%s- %s' % (nick(), msg.args[1])
    elif msg.command == 'JOIN':
        prefix = msg.prefix
        if msg.nick:
            prefix = '%s <%s>' % (msg.nick, prefix)
        s = '*** %s has joined %s' % (prefix, msg.args[0])
    elif msg.command == 'PART':
        if len(msg.args) > 1:
            partmsg = ' (%s)' % msg.args[1]
        else:
            partmsg = ''
        s = '*** %s <%s> has parted %s%s' % (msg.nick, msg.prefix,
                                             msg.args[0], partmsg)
    elif msg.command == 'KICK':
        if len(msg.args) > 2:
            kickmsg = ' (%s)' % msg.args[1]
        else:
            kickmsg = ''
        s = '*** %s was kicked by %s%s' % (msg.args[1], msg.nick, kickmsg)
    elif msg.command == 'MODE':
        s = '*** %s sets mode: %s' % (nickorprefix(), ' '.join(msg.args))
    elif msg.command == 'QUIT':
        if msg.args:
            quitmsg = ' (%s)' % msg.args[0]
        else:
            quitmsg = ''
        s = '*** %s <%s> has quit IRC%s' % (msg.nick, msg.prefix, quitmsg)
    elif msg.command == 'TOPIC':
        s = '*** %s changes topic to %s' % (nickorprefix(), msg.args[1])
    elif msg.command == 'NICK':
        s = '*** %s is now known as %s' % (msg.nick, msg.args[0])
    else:
        s = utils.str.format('--- Unknown command %q', ' '.join(msg.args))
    at = msg.tagged('receivedAt')
    if timestampFormat and at:
        s = '%s %s' % (time.strftime(timestampFormat, time.localtime(at)), s)
    return s

###
# Various IrcMsg functions
###

isNick = ircutils.isNick
areNicks = ircutils.areNicks
isChannel = ircutils.isChannel
areChannels = ircutils.areChannels
areReceivers = ircutils.areReceivers
isUserHostmask = ircutils.isUserHostmask

def pong(payload, prefix='', msg=None):
    """Takes a payload and returns the proper PONG IrcMsg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert payload, 'PONG requires a payload'
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='PONG', args=(payload,), msg=msg)

def ping(payload, prefix='', msg=None):
    """Takes a payload and returns the proper PING IrcMsg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert payload, 'PING requires a payload'
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='PING', args=(payload,), msg=msg)

def op(channel, nick, prefix='', msg=None):
    """Returns a MODE to op nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=(channel, '+o', nick), msg=msg)

def ops(channel, nicks, prefix='', msg=None):
    """Returns a MODE to op each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=(channel, '+' + ('o'*len(nicks))) + tuple(nicks),
                  msg=msg)

def deop(channel, nick, prefix='', msg=None):
    """Returns a MODE to deop nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=(channel, '-o', nick), msg=msg)

def deops(channel, nicks, prefix='', msg=None):
    """Returns a MODE to deop each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE', msg=msg,
                  args=(channel, '-' + ('o'*len(nicks))) + tuple(nicks))

def halfop(channel, nick, prefix='', msg=None):
    """Returns a MODE to halfop nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=(channel, '+h', nick), msg=msg)

def halfops(channel, nicks, prefix='', msg=None):
    """Returns a MODE to halfop each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE', msg=msg,
                  args=(channel, '+' + ('h'*len(nicks))) + tuple(nicks))

def dehalfop(channel, nick, prefix='', msg=None):
    """Returns a MODE to dehalfop nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=(channel, '-h', nick), msg=msg)

def dehalfops(channel, nicks, prefix='', msg=None):
    """Returns a MODE to dehalfop each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE', msg=msg,
                  args=(channel, '-' + ('h'*len(nicks))) + tuple(nicks))

def voice(channel, nick, prefix='', msg=None):
    """Returns a MODE to voice nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=(channel, '+v', nick), msg=msg)

def voices(channel, nicks, prefix='', msg=None):
    """Returns a MODE to voice each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE', msg=msg,
                  args=(channel, '+' + ('v'*len(nicks))) + tuple(nicks))

def devoice(channel, nick, prefix='', msg=None):
    """Returns a MODE to devoice nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=(channel, '-v', nick), msg=msg)

def devoices(channel, nicks, prefix='', msg=None):
    """Returns a MODE to devoice each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE', msg=msg,
                  args=(channel, '-' + ('v'*len(nicks))) + tuple(nicks))

def ban(channel, hostmask, exception='', prefix='', msg=None):
    """Returns a MODE to ban nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isUserHostmask(hostmask), repr(hostmask)
    modes = [('+b', hostmask)]
    if exception:
        modes.append(('+e', exception))
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=[channel] + ircutils.joinModes(modes), msg=msg)

def bans(channel, hostmasks, exceptions=(), prefix='', msg=None):
    """Returns a MODE to ban each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert all(isUserHostmask, hostmasks), hostmasks
    modes = [('+b', s) for s in hostmasks] + [('+e', s) for s in exceptions]
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=[channel] + ircutils.joinModes(modes), msg=msg)

def unban(channel, hostmask, prefix='', msg=None):
    """Returns a MODE to unban nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isUserHostmask(hostmask), repr(hostmask)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=(channel, '-b', hostmask), msg=msg)

def unbans(channel, hostmasks, prefix='', msg=None):
    """Returns a MODE to unban each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert all(isUserHostmask, hostmasks), hostmasks
    modes = [('-b', s) for s in hostmasks]
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=[channel] + ircutils.joinModes(modes), msg=msg)

def kick(channel, nick, s='', prefix='', msg=None):
    """Returns a KICK to kick nick from channel with the message s."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    if minisix.PY2 and isinstance(s, unicode):
        s = s.encode('utf8')
    assert isinstance(s, str)
    if s:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, nick, s), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, nick), msg=msg)

def kicks(channels, nicks, s='', prefix='', msg=None):
    """Returns a KICK to kick each of nicks from channel with the message s.
    """
    if isinstance(channels, str): # Backward compatibility
        channels = [channels]
    if conf.supybot.protocols.irc.strictRfc():
        assert areChannels(channels), repr(channels)
        assert areNicks(nicks), repr(nicks)
    if msg and not prefix:
        prefix = msg.prefix
    if minisix.PY2 and isinstance(s, unicode):
        s = s.encode('utf8')
    assert isinstance(s, str)
    if s:
        for channel in channels:
            return IrcMsg(prefix=prefix, command='KICK',
                          args=(channel, ','.join(nicks), s), msg=msg)
    else:
        for channel in channels:
            return IrcMsg(prefix=prefix, command='KICK',
                          args=(channel, ','.join(nicks)), msg=msg)

def privmsg(recipient, s, prefix='', msg=None):
    """Returns a PRIVMSG to recipient with the message s."""
    if conf.supybot.protocols.irc.strictRfc():
        assert (areReceivers(recipient)), repr(recipient)
        assert s, 's must not be empty.'
    if minisix.PY2 and isinstance(s, unicode):
        s = s.encode('utf8')
    assert isinstance(s, str)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='PRIVMSG',
                  args=(recipient, s), msg=msg)

def dcc(recipient, kind, *args, **kwargs):
    # Stupid Python won't allow (recipient, kind, *args, prefix=''), so we have
    # to use the **kwargs form.  Blech.
    assert isNick(recipient), 'Can\'t DCC a channel.'
    kind = kind.upper()
    assert kind in ('SEND', 'CHAT', 'RESUME', 'ACCEPT'), 'Invalid DCC command.'
    args = (kind,) + args
    return IrcMsg(prefix=kwargs.get('prefix', ''), command='PRIVMSG',
                  args=(recipient, ' '.join(args)))

def action(recipient, s, prefix='', msg=None):
    """Returns a PRIVMSG ACTION to recipient with the message s."""
    if conf.supybot.protocols.irc.strictRfc():
        assert (isChannel(recipient) or isNick(recipient)), repr(recipient)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='PRIVMSG',
                  args=(recipient, '\x01ACTION %s\x01' % s), msg=msg)

def notice(recipient, s, prefix='', msg=None):
    """Returns a NOTICE to recipient with the message s."""
    if conf.supybot.protocols.irc.strictRfc():
        assert areReceivers(recipient), repr(recipient)
        assert s, 'msg must not be empty.'
    if minisix.PY2 and isinstance(s, unicode):
        s = s.encode('utf8')
    assert isinstance(s, str)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='NOTICE', args=(recipient, s), msg=msg)

def join(channel, key=None, prefix='', msg=None):
    """Returns a JOIN to a channel"""
    if conf.supybot.protocols.irc.strictRfc():
        assert areChannels(channel), repr(channel)
    if msg and not prefix:
        prefix = msg.prefix
    if key is None:
        return IrcMsg(prefix=prefix, command='JOIN', args=(channel,), msg=msg)
    else:
        if conf.supybot.protocols.irc.strictRfc():
            chars = '\x00\r\n\f\t\v '
            assert not any([(ord(x) >= 128 or x in chars) for x in key])
        return IrcMsg(prefix=prefix, command='JOIN',
                      args=(channel, key), msg=msg)

def joins(channels, keys=None, prefix='', msg=None):
    """Returns a JOIN to each of channels."""
    if conf.supybot.protocols.irc.strictRfc():
        assert all(isChannel, channels), channels
    if msg and not prefix:
        prefix = msg.prefix
    if keys is None:
        keys = []
    assert len(keys) <= len(channels), 'Got more keys than channels.'
    if not keys:
        return IrcMsg(prefix=prefix,
                      command='JOIN',
                      args=(','.join(channels),), msg=msg)
    else:
        if conf.supybot.protocols.irc.strictRfc():
            chars = '\x00\r\n\f\t\v '
            for key in keys:
                assert not any([(ord(x) >= 128 or x in chars) for x in key])
        return IrcMsg(prefix=prefix,
                      command='JOIN',
                      args=(','.join(channels), ','.join(keys)), msg=msg)

def part(channel, s='', prefix='', msg=None):
    """Returns a PART from channel with the message s."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
    if msg and not prefix:
        prefix = msg.prefix
    if minisix.PY2 and isinstance(s, unicode):
        s = s.encode('utf8')
    assert isinstance(s, str)
    if s:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(channel, s), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(channel,), msg=msg)

def parts(channels, s='', prefix='', msg=None):
    """Returns a PART from each of channels with the message s."""
    if conf.supybot.protocols.irc.strictRfc():
        assert all(isChannel, channels), channels
    if msg and not prefix:
        prefix = msg.prefix
    if minisix.PY2 and isinstance(s, unicode):
        s = s.encode('utf8')
    assert isinstance(s, str)
    if s:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(','.join(channels), s), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(','.join(channels),), msg=msg)

def quit(s='', prefix='', msg=None):
    """Returns a QUIT with the message s."""
    if msg and not prefix:
        prefix = msg.prefix
    if s:
        return IrcMsg(prefix=prefix, command='QUIT', args=(s,), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='QUIT', msg=msg)

def topic(channel, topic=None, prefix='', msg=None):
    """Returns a TOPIC for channel with the topic topic."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
    if msg and not prefix:
        prefix = msg.prefix
    if topic is None:
        return IrcMsg(prefix=prefix, command='TOPIC',
                      args=(channel,), msg=msg)
    else:
        if minisix.PY2 and isinstance(topic, unicode):
            topic = topic.encode('utf8')
        assert isinstance(topic, str)
        return IrcMsg(prefix=prefix, command='TOPIC',
                      args=(channel, topic), msg=msg)

def nick(nick, prefix='', msg=None):
    """Returns a NICK with nick nick."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='NICK', args=(nick,), msg=msg)

def user(ident, user, prefix='', msg=None):
    """Returns a USER with ident ident and user user."""
    if conf.supybot.protocols.irc.strictRfc():
        assert '\x00' not in ident and \
               '\r' not in ident and \
               '\n' not in ident and \
               ' ' not in ident and \
               '@' not in ident
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='USER',
                  args=(ident, '0', '*', user), msg=msg)

def who(hostmaskOrChannel, prefix='', msg=None, args=()):
    """Returns a WHO for the hostmask or channel hostmaskOrChannel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(hostmaskOrChannel) or \
               isUserHostmask(hostmaskOrChannel), repr(hostmaskOrChannel)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='WHO',
                  args=(hostmaskOrChannel,) + args, msg=msg)

def _whois(COMMAND, nick, mask='', prefix='', msg=None):
    """Returns a WHOIS for nick."""
    if conf.supybot.protocols.irc.strictRfc():
        assert areNicks(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    args = (nick,)
    if mask:
        args = (nick, mask)
    return IrcMsg(prefix=prefix, command=COMMAND, args=args, msg=msg)
whois = functools.partial(_whois, 'WHOIS')
whowas = functools.partial(_whois, 'WHOWAS')

def names(channel=None, prefix='', msg=None):
    if conf.supybot.protocols.irc.strictRfc():
        assert areChannels(channel)
    if msg and not prefix:
        prefix = msg.prefix
    if channel is not None:
        return IrcMsg(prefix=prefix, command='NAMES', args=(channel,), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='NAMES', msg=msg)

def mode(channel, args=(), prefix='', msg=None):
    if msg and not prefix:
        prefix = msg.prefix
    if isinstance(args, minisix.string_types):
        args = (args,)
    else:
        args = tuple(map(str, args))
    return IrcMsg(prefix=prefix, command='MODE', args=(channel,)+args, msg=msg)

def modes(channel, args=(), prefix='', msg=None):
    """Returns a MODE message for the channel for all the (mode, targetOrNone) 2-tuples in 'args'."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
    modes = args
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='MODE',
                  args=[channel] + ircutils.joinModes(modes), msg=msg)

def limit(channel, limit, prefix='', msg=None):
    return mode(channel, ['+l', limit], prefix=prefix, msg=msg)

def unlimit(channel, limit, prefix='', msg=None):
    return mode(channel, ['-l', limit], prefix=prefix, msg=msg)

def invite(nick, channel, prefix='', msg=None):
    """Returns an INVITE for nick."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='INVITE',
                  args=(nick, channel), msg=msg)

def password(password, prefix='', msg=None):
    """Returns a PASS command for accessing a server."""
    if conf.supybot.protocols.irc.strictRfc():
        assert password, 'password must not be empty.'
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='PASS', args=(password,), msg=msg)

def ison(nick, prefix='', msg=None):
    if conf.supybot.protocols.irc.strictRfc():
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='ISON', args=(nick,), msg=msg)

def monitor(subcommand, nicks=None, prefix='', msg=None):
    if conf.supybot.protocols.irc.strictRfc():
        for nick in nicks:
            assert isNick(nick), repr(nick)
        assert subcommand in '+-CLS'
        if subcommand in 'CLS':
            assert nicks is None
    if msg and not prefix:
        prefix = msg.prefix
    if not isinstance(nicks, str):
        nicks = ','.join(nicks)
    return IrcMsg(prefix=prefix, command='MONITOR', args=(subcommand, nicks),
            msg=msg)


def error(s, msg=None):
    return IrcMsg(command='ERROR', args=(s,), msg=msg)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
