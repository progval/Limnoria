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

"""
This module provides the basic IrcMsg object used throughout the bot to
represent the actual messages.  It also provides several helper functions to
construct such messages in an easier way than the constructor for the IrcMsg
object (which, as you'll read later, is quite...full-featured :))
"""

__revision__ = "$Id$"

import supybot.fix as fix

import re
import time
import string

import supybot.conf as conf
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
    IRC message (such as one taken straight from the network.

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
    __slots__ = ('args', 'command', 'host', 'nick', 'prefix', 'user',
                 '_hash', '_str', '_repr', '_len')
    def __init__(self, s='', command='', args=(), prefix='', msg=None):
        assert not (msg and s), 'Ircmsg.__init__ cannot accept both s and msg'
        if not s and not command and not msg:
            raise MalformedIrcMsg, 'IRC messages require a command.'
        self._str = None
        self._repr = None
        self._hash = None
        self._len = None
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
                if ' :' in s:
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
            else:
                self.prefix = intern(prefix)
                self.command = intern(command)
                assert all(ircutils.isValidArgument, args)
                self.args = args
        self.args = tuple(map(intern, self.args))
        if ircutils.isUserHostmask(self.prefix):
            (self.nick,self.user,self.host) = \
                 map(intern, ircutils.splitHostmask(self.prefix))
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
        if self._len is not None:
            return self._len
        self._len = 0
        if self.prefix:
            self._len += len(self.prefix)
        self._len += len(self.command)
        if self.args:
            for arg in self.args:
                self._len += len(arg) + 1 # Remember space prior to the arg.
        self._len += 2 # For colon before the prefix and before the last arg.
        return self._len

    def __eq__(self, other):
        return hash(self) == hash(other) and \
               self.command == other.command and \
               self.prefix == other.prefix and \
               self.args == other.args

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        if self._hash is not None:
            return self._hash
        self._hash = hash(self.command) ^ \
                     hash(self.prefix) ^ \
                     hash(self.args)
        return self._hash

    def __repr__(self):
        if self._repr is not None:
            return self._repr
        self._repr = 'IrcMsg(prefix=%r, command=%r, args=%r)' % \
                     (self.prefix, self.command, self.args)
        return self._repr

    def __getstate__(self):
        return str(self)

    def __setstate__(self, s):
        self.__init__(s)

## try:
##     import _ircmsg
##     IrcMsg = _ircmsg.IrcMsg
## except:
##     pass


def isAction(msg):
    """A predicate returning true if the PRIVMSG in question is an ACTION"""
    if msg.command == 'PRIVMSG' and msg.args[1].endswith('\x01'):
        L = msg.args[1].split(None, 1)
        return len(L) == 2 and L[0] == '\x01ACTION'
    else:
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

def prettyPrint(msg, addRecipients=False):
    """Provides a client-friendly string form for messages.

    IIRC, I copied BitchX's (or was it xchat's?) format for messages.
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
            s = '<%s> %s' % (nick(), msg.args[1])
    elif msg.command == 'NOTICE':
        s = '-%s- %s' % (nick(), msg.args[1])
    elif msg.command == 'JOIN':
        s = '*** %s has joined %s' % (msg.nick, msg.args[0])
    elif msg.command == 'PART':
        if len(msg.args) > 1:
            partmsg = ' (%s)' % msg.args[1]
        else:
            partmsg = ''
        s = '*** %s has parted %s%s' % (msg.nick, msg.args[0], partmsg)
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
        s = '*** %s has quit IRC%s' % (msg.nick, quitmsg)
    elif msg.command == 'TOPIC':
        s = '*** %s changes topic to %s' % (nickorprefix(), msg.args[1])
    return s

###
# Various IrcMsg functions
###

MODE = 'MODE'

isNick = ircutils.isNick
isChannel = ircutils.isChannel
isUserHostmask = ircutils.isUserHostmask

def pong(payload, prefix=''):
    """Takes a payload and returns the proper PONG IrcMsg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert payload, 'PONG requires a payload'
    return IrcMsg(prefix=prefix, command='PONG', args=(payload,))

def ping(payload, prefix=''):
    """Takes a payload and returns the proper PING IrcMsg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert payload, 'PING requires a payload'
    return IrcMsg(prefix=prefix, command='PING', args=(payload,))

def op(channel, nick, prefix=''):
    """Returns a MODE to op nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '+o', nick))

def ops(channel, nicks, prefix=''):
    """Returns a MODE to op each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '+' + ('o'*len(nicks))) + tuple(nicks))

def deop(channel, nick, prefix=''):
    """Returns a MODE to deop nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '-o', nick))

def deops(channel, nicks, prefix=''):
    """Returns a MODE to deop each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '-' + ('o'*len(nicks))) + tuple(nicks))

def halfop(channel, nick, prefix=''):
    """Returns a MODE to halfop nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '+h', nick))

def halfops(channel, nicks, prefix=''):
    """Returns a MODE to halfop each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    return IrcMsg(prefix=prefix,
                  command=MODE,
                  args=(channel, '+' + ('h'*len(nicks))) + tuple(nicks))

def dehalfop(channel, nick, prefix=''):
    """Returns a MODE to dehalfop nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '-h', nick))

def dehalfops(channel, nicks, prefix=''):
    """Returns a MODE to dehalfop each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '-' + ('h'*len(nicks))) + tuple(nicks))

def voice(channel, nick, prefix=''):
    """Returns a MODE to voice nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '+v', nick))

def voices(channel, nicks, prefix=''):
    """Returns a MODE to voice each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks)
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '+' + ('v'*len(nicks))) + tuple(nicks))

def devoice(channel, nick, prefix=''):
    """Returns a MODE to devoice nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '-v', nick))

def devoices(channel, nicks, prefix=''):
    """Returns a MODE to devoice each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert nicks, 'Nicks must not be empty.'
        assert all(isNick, nicks), nicks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '-' + ('v'*len(nicks))) + tuple(nicks))

def ban(channel, hostmask, exception='', prefix=''):
    """Returns a MODE to ban nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isUserHostmask(hostmask), repr(hostmask)
    modes = [('+b', hostmask)]
    if exception:
        modes.append(('+e', exception))
    return IrcMsg(prefix=prefix, command=MODE,
                  args=[channel] + ircutils.joinModes(modes))

def bans(channel, hostmasks, exceptions=(), prefix=''):
    """Returns a MODE to ban each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert all(isUserHostmask, hostmasks), hostmasks
    modes = [('+b', s) for s in hostmasks] + [('+e', s) for s in exceptions]
    return IrcMsg(prefix=prefix, command=MODE,
                  args=[channel] + ircutils.joinModes(modes))

def unban(channel, hostmask, prefix=''):
    """Returns a MODE to unban nick on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isUserHostmask(hostmask), repr(hostmask)
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '-b', hostmask))

def unbans(channel, hostmasks, prefix=''):
    """Returns a MODE to unban each of nicks on channel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert all(isUserHostmask, hostmasks), hostmasks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '-' + ('b'*len(hostmasks)), hostmasks))

def kick(channel, nick, msg='', prefix=''):
    """Returns a KICK to kick nick from channel with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert isNick(nick), repr(nick)
    if msg:
        return IrcMsg(prefix=prefix, command='KICK', args=(channel, nick, msg))
    else:
        return IrcMsg(prefix=prefix, command='KICK', args=(channel, nick))

def kicks(channel, nicks, msg='', prefix=''):
    """Returns a KICK to kick each of nicks from channel with the message msg.
    """
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
        assert all(isNick, nicks), nicks
    if msg:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, ','.join(nicks), msg))
    else:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, ','.join(nicks)))

def privmsg(recipient, msg, prefix=''):
    """Returns a PRIVMSG to recipient with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert (isChannel(recipient) or isNick(recipient)), repr(recipient)
        assert msg, 'msg must not be empty.'
    return IrcMsg(prefix=prefix, command='PRIVMSG', args=(recipient, msg))

def dcc(recipient, kind, *args, **kwargs):
    # Stupid Python won't allow (recipient, kind, *args, prefix=''), so we have
    # to use the **kwargs form.  Blech.
    assert ircutils.isNick(recipient), 'Can\'t DCC a channel.'
    kind = kind.upper()
    assert kind in ('SEND', 'CHAT', 'RESUME', 'ACCEPT'), 'Invalid DCC command.'
    args = (kind,) + args
    return IrcMsg(prefix=kwargs.get('prefix', ''), command='PRIVMSG',
                  args=(recipient, ' '.join(args)))

def action(recipient, msg, prefix=''):
    """Returns a PRIVMSG ACTION to recipient with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert (isChannel(recipient) or isNick(recipient)), repr(recipient)
    return IrcMsg(prefix=prefix, command='PRIVMSG',
                  args=(recipient,'\x01ACTION %s\x01'% msg))

def notice(recipient, msg, prefix=''):
    """Returns a NOTICE to recipient with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert (isChannel(recipient) or isNick(recipient)), repr(recipient)
        assert msg, 'msg must not be empty.'
    return IrcMsg(prefix=prefix, command='NOTICE', args=(recipient, msg))

def join(channel, key=None, prefix=''):
    """Returns a JOIN to a channel"""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
    if key is None:
        return IrcMsg(prefix=prefix, command='JOIN', args=(channel,))
    else:
        if conf.supybot.protocols.irc.strictRfc():
            assert key.translate(string.ascii, string.ascii[128:]) == key and \
                   '\x00' not in key and \
                   '\r' not in key and \
                   '\n' not in key and \
                   '\f' not in key and \
                   '\t' not in key and \
                   '\v' not in key and \
                   ' ' not in key
        return IrcMsg(prefix=prefix, command='JOIN', args=(channel, key))

def joins(channels, keys=None, prefix=''):
    """Returns a JOIN to each of channels."""
    if conf.supybot.protocols.irc.strictRfc():
        assert all(isChannel, channels), channels
    if keys is None:
        keys = []
    assert len(keys) <= len(channels), 'Got more keys than channels.'
    if not keys:
        return IrcMsg(prefix=prefix,
                      command='JOIN',
                      args=(','.join(channels),))
    else:
        for key in keys:
            if conf.supybot.protocols.irc.strictRfc():
                assert key.translate(string.ascii,string.ascii[128:])==key and\
                       '\x00' not in key and \
                       '\r' not in key and \
                       '\n' not in key and \
                       '\f' not in key and \
                       '\t' not in key and \
                       '\v' not in key and \
                       ' ' not in key
        return IrcMsg(prefix=prefix,
                      command='JOIN',
                      args=(','.join(channels), ','.join(keys)))

def part(channel, msg='', prefix=''):
    """Returns a PART from channel with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
    if msg:
        return IrcMsg(prefix=prefix, command='PART', args=(channel, msg))
    else:
        return IrcMsg(prefix=prefix, command='PART', args=(channel,))

def parts(channels, msg='', prefix=''):
    """Returns a PART from each of channels with the message msg."""
    if conf.supybot.protocols.irc.strictRfc():
        assert all(isChannel, channels), channels
    if msg:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(','.join(channels), msg,))
    else:
        return IrcMsg(prefix=prefix, command='PART',
                      args=(','.join(channels),))

def quit(msg='', prefix=''):
    """Returns a QUIT with the message msg."""
    if msg:
        return IrcMsg(prefix=prefix, command='QUIT', args=(msg,))
    else:
        return IrcMsg(prefix=prefix, command='QUIT')

def topic(channel, topic=None, prefix=''):
    """Returns a TOPIC for channel with the topic topic."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(channel), repr(channel)
    if topic is None:
        return IrcMsg(prefix=prefix, command='TOPIC', args=(channel,))
    else:
        return IrcMsg(prefix=prefix, command='TOPIC', args=(channel, topic))

def nick(nick, prefix=''):
    """Returns a NICK with nick nick."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isNick(nick), repr(nick)
    return IrcMsg(prefix=prefix, command='NICK', args=(nick,))

def user(ident, user, prefix=''):
    """Returns a USER with ident ident and user user."""
    if conf.supybot.protocols.irc.strictRfc():
        assert '\x00' not in ident and \
               '\r' not in ident and \
               '\n' not in ident and \
               ' ' not in ident and \
               '@' not in ident
    return IrcMsg(prefix=prefix, command='USER', args=(ident, '0', '*', user))

def who(hostmaskOrChannel, prefix=''):
    """Returns a WHO for the hostmask or channel hostmaskOrChannel."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isChannel(hostmaskOrChannel) or \
               isUserHostmask(hostmaskOrChannel), repr(hostmaskOrChannel)
    return IrcMsg(prefix=prefix, command='WHO', args=(hostmaskOrChannel,))

def whois(nick, mask='', prefix=''):
    """Returns a WHOIS for nick."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isNick(nick), repr(nick)
    return IrcMsg(prefix=prefix, command='WHOIS', args=(nick, mask))

def mode(channel, args=(), prefix=''):
    if isinstance(args, basestring):
        args = (args,)
    else:
        args = tuple(map(str, args))
    return IrcMsg(prefix=prefix, command='MODE', args=(channel,)+args)

def invite(nick, channel, prefix=''):
    """Returns an INVITE for nick."""
    if conf.supybot.protocols.irc.strictRfc():
        assert isNick(nick), repr(nick)
    return IrcMsg(prefix=prefix, command='INVITE', args=(nick, channel))

def password(password, prefix=''):
    """Returns a PASS command for accessing a server."""
    if conf.supybot.protocols.irc.strictRfc():
        assert password, 'password must not be empty.'
    return IrcMsg(prefix=prefix, command='PASS', args=(password,))

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
