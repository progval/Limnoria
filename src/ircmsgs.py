###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2010, James Vega
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
import time

import supybot.conf as conf
import supybot.utils as utils
from supybot.utils.iter import all
import supybot.ircutils as ircutils

###
# IrcMsg class -- used for representing IRC messages acquired from a network.
###

class MalformedIrcMsg(ValueError):
    pass

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
    if a programmer wanted to take a PRIVMSG he'd gotten and simply redirect it
    to a different source, he could do this:

    IrcMsg(prefix='', args=(newSource, otherMsg.args[1]), msg=otherMsg)
    """
    # It's too useful to be able to tag IrcMsg objects with extra, unforeseen
    # data.  Goodbye, __slots__.
    # On second thought, let's use methods for tagging.
    __slots__ = ('args', 'command', 'host', 'nick', 'prefix', 'user',
                 '_hash', '_str', '_repr', '_len', 'tags')
    def __init__(self, s='', command='', args=(), prefix='', msg=None):
        assert not (msg and s), 'IrcMsg.__init__ cannot accept both s and msg'
        if not s and not command and not msg:
            raise MalformedIrcMsg, 'IRC messages require a command.'
        self._str = None
        self._repr = None
        self._hash = None
        self._len = None
        self.tags = {}
        if s:
            originalString = s
            try:
                if not s.endswith('\n'):
                    s += '\n'
                self._str = s
                if s[0] == ':':
                    self.prefix, s = s[1:].split(None, 1)
                else:
                    self.prefix = ''
                if ' :' in s: # Note the space: IPV6 addresses are bad w/o it.
                    s, last = s.split(' :', 1)
                    self.args = s.split()
                    self.args.append(last.rstrip('\r\n'))
                else:
                    self.args = s.split()
                self.command = self.args.pop(0)
            except (IndexError, ValueError):
                raise MalformedIrcMsg, repr(originalString)
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
                self.tags = msg.tags.copy()
            else:
                self.prefix = prefix
                self.command = command
                assert all(ircutils.isValidArgument, args)
                self.args = args
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
                self._str = ':%s %s %s :%s\r\n' % \
                            (self.prefix, self.command,
                             ' '.join(self.args[:-1]), self.args[-1])
            else:
                if self.args:
                    self._str = ':%s %s :%s\r\n' % \
                                (self.prefix, self.command, self.args[0])
                else:
                    self._str = ':%s %s\r\n' % (self.prefix, self.command)
        else:
            if len(self.args) > 1:
                self._str = '%s %s :%s\r\n' % \
                            (self.command,
                             ' '.join(self.args[:-1]), self.args[-1])
            else:
                if self.args:
                    self._str = '%s :%s\r\n' % (self.command, self.args[0])
                else:
                    self._str = '%s\r\n' % self.command
        return self._str

    def __len__(self):
        return len(str(self))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
               hash(self) == hash(other) and \
               self.command == other.command and \
               self.prefix == other.prefix and \
               self.args == other.args
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
        self._repr = format('IrcMsg(prefix=%q, command=%q, args=%r)',
                            self.prefix, self.command, self.args)
        return self._repr

    def __reduce__(self):
        return (self.__class__, (str(self),))

    def tag(self, tag, value=True):
        self.tags[tag] = value

    def tagged(self, tag):
        return self.tags.get(tag) # Returns None if it's not there.

    def __getattr__(self, attr):
        return self.tagged(attr)


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
    at = getattr(msg, 'receivedAt', None)
    if timestampFormat and at:
        s = '%s %s' % (time.strftime(timestampFormat, time.localtime(at)), s)
    return s

###
# Various IrcMsg functions
###

isNick = ircutils.isNick
isChannel = ircutils.isChannel
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
    """Returns a KICK to kick nick from channel with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    if s:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, nick, s), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, nick), msg=msg)

def kicks(channel, nicks, s='', prefix='', msg=None):
    """Returns a KICK to kick each of nicks from channel with the message msg.
    """
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert all(isNick, nicks), nicks
    if msg and not prefix:
        prefix = msg.prefix
    if s:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, ','.join(nicks), s), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, ','.join(nicks)), msg=msg)

def privmsg(recipient, s, prefix='', msg=None):
    """Returns a PRIVMSG to recipient with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert (isChannel(recipient) or isNick(recipient)), repr(recipient)
        assert s, 's must not be empty.'
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
    """Returns a PRIVMSG ACTION to recipient with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert (isChannel(recipient) or isNick(recipient)), repr(recipient)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='PRIVMSG',
                  args=(recipient, '\x01ACTION %s\x01' % s), msg=msg)

def notice(recipient, s, prefix='', msg=None):
    """Returns a NOTICE to recipient with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert (isChannel(recipient) or isNick(recipient)), repr(recipient)
        assert s, 'msg must not be empty.'
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='NOTICE', args=(recipient, s), msg=msg)

def join(channel, key=None, prefix='', msg=None):
    """Returns a JOIN to a channel"""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
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
    """Returns a PART from channel with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
    if msg and not prefix:
        prefix = msg.prefix
    if s:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(channel, s), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(channel,), msg=msg)

def parts(channels, s='', prefix='', msg=None):
    """Returns a PART from each of channels with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert all(isChannel, channels), channels
    if msg and not prefix:
        prefix = msg.prefix
    if s:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(','.join(channels), s), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(','.join(channels),), msg=msg)

def quit(s='', prefix='', msg=None):
    """Returns a QUIT with the message msg."""
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

def who(hostmaskOrChannel, prefix='', msg=None):
    """Returns a WHO for the hostmask or channel hostmaskOrChannel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(hostmaskOrChannel) or \
               isUserHostmask(hostmaskOrChannel), repr(hostmaskOrChannel)
    if msg and not prefix:
        prefix = msg.prefix
    return IrcMsg(prefix=prefix, command='WHO',
                  args=(hostmaskOrChannel,), msg=msg)

def whois(nick, mask='', prefix='', msg=None):
    """Returns a WHOIS for nick."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isNick(nick), repr(nick)
    if msg and not prefix:
        prefix = msg.prefix
    args = (nick,)
    if mask:
        args = (nick, mask)
    return IrcMsg(prefix=prefix, command='WHOIS', args=args, msg=msg)

def names(channel=None, prefix='', msg=None):
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel)
    if msg and not prefix:
        prefix = msg.prefix
    if channel is not None:
        return IrcMsg(prefix=prefix, command='NAMES', args=(channel,), msg=msg)
    else:
        return IrcMsg(prefix=prefix, command='NAMES', msg=msg)

def mode(channel, args=(), prefix='', msg=None):
    if msg and not prefix:
        prefix = msg.prefix
    if isinstance(args, basestring):
        args = (args,)
    else:
        args = tuple(map(str, args))
    return IrcMsg(prefix=prefix, command='MODE', args=(channel,)+args, msg=msg)

def modes(channel, args=(), prefix='', msg=None):
    """Returns a MODE to quiet each of nicks on channel."""
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

def error(s, msg=None):
    return IrcMsg(command='ERROR', args=(s,), msg=msg)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
