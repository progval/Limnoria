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

from fix import *

import re

import debug
import ircutils

###
# IrcMsg class -- used for representing IRC messages acquired from a network.
###

class IrcMsg(object):
    """Class to represent an IRC message.
    """
    __slots__ = ('_args', '_command', '_host', '_nick',
                 '_prefix', '_user', '_hash')
    def __init__(self, s='', command='', args=None, prefix='', msg=None):
        if not s and not command and not msg:
            raise ValueError, 'IRC messages require a command.'
        if msg:
            prefix = msg.prefix
            command = msg.command
            args = msg.args
        if command: # Must be using command=, args=, prefix= form.
            if args is not None:
                #debug.printf(args)
                assert filter(ircutils.isValidArgument, args) == args
            else:
                args = ()
        else: # Must be using a string.
            if s[0] == ':':
                prefix, s = s[1:].split(None, 1)
            else:
                prefix = ''
            if s.find(' :') != -1:
                s, last = s.split(' :', 1)
                args = s.split()
                args.append(last.rstrip('\r\n'))
            else:
                args = s.split()
            command = args.pop(0)
        if ircutils.isUserHostmask(prefix):
            (nick, user, host) = ircutils.splitHostmask(prefix)
        else:
            (nick, user, host) = ('', '', '')
        self._prefix = prefix
        self._nick = ircutils.nick(nick)
        self._user = user
        self._host = host
        self._command = command
        self._args = tuple(args)

    prefix = property(lambda self: self._prefix)
    nick = property(lambda self: self._nick)
    user = property(lambda self: self._user)
    host = property(lambda self: self._host)
    command = property(lambda self: self._command)
    args = property(lambda self: self._args)

    def __str__(self):
        ret = ''
        if self.prefix:
            ret = ':%s %s' % (self.prefix, self.command)
        else:
            ret = self.command
        if self.args:
            if len(self.args) > 1:
                ret = '%s %s :%s\r\n' % (ret, ' '.join(self.args[:-1]),
                                         self.args[-1])
            else:
                ret = '%s :%s\r\n' % (ret, self.args[0])
        else:
            ret = ret + '\r\n'
        return ret

    def __len__(self):
        # This might not take into account the length of the prefix, but leaves
        # some room for variation.
        ret = 0
        if self.prefix:
            ret += len(self.prefix)
        else:
            ret += 42 # Ironically, the average length of an IRC prefix.
        ret += len(self.command)
        if self.args:
            for arg in self.args:
                ret += len(arg) + 1 # Remember the space prior to the arg.
        ret += 2 # For the colon before the prefix and before the last arg.
        return ret

    def __eq__(self, other):
        return hash(self) == hash(other) and \
               self.command == other.command and \
               self.prefix == other.prefix and \
               self.args == other.args

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self.command) & \
                         hash(self.prefix) & \
                         hash(self.args)
            return self._hash

    def __repr__(self):
        return '%s(prefix=%r, command=%r, args=%r)' % \
               (self.__class__.__name__, self.prefix, self.command, self.args)

    def __getstate__(self):
        return str(self)

    def __setstate__(self, s):
        self.__init__(s)


def isAction(msg):
    return msg.command == 'PRIVMSG' and \
           msg.args[1].startswith('\x01ACTION') and \
           msg.args[1].endswith('\x01')

_unactionre = re.compile(r'^\x01ACTION (.*)\x01$')
def unAction(msg):
    return _unactionre.match(msg.args[1]).group(1)

def prettyPrint(msg, addRecipients=False):
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
        s = '*** %s has quit IRC%s' % quitmsg
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
    assert payload, 'PONG requires a payload'
    return IrcMsg(prefix=prefix, command='PONG', args=(payload,))

def ping(payload, prefix=''):
    """Takes a payload and returns the proper PING IrcMsg."""
    assert payload, 'PING requires a payload'
    return IrcMsg(prefix=prefix, command='PING', args=(payload,))

def op(channel, nick, prefix=''):
    """Returns a MODE to op nick on channel."""
    assert isChannel(channel), channel
    assert isNick(nick), nick
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '+o', nick))

def ops(channel, nicks, prefix=''):
    """Returns a MODE to op each of nicks on channel."""
    assert isChannel(channel), channel
    assert filter(isNick, nicks) == nicks, nicks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '+' + ('o'*len(nicks)), nicks))

def deop(channel, nick, prefix=''):
    """Returns a MODE to deop nick on channel."""
    assert isChannel(channel), channel
    assert isNick(nick), nick
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '-o', nick))

def deops(channel, nicks, prefix=''):
    """Returns a MODE to deop each of nicks on channel."""
    assert isChannel(channel), channel
    assert filter(isNick, nicks) == nicks, nicks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '-' + ('o'*len(nicks)), nicks))

def halfop(channel, nick, prefix=''):
    """Returns a MODE to halfop nick on channel."""
    assert isChannel(channel), channel
    assert isNick(nick), nick
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '+h', nick))

def halfops(channel, nicks, prefix=''):
    """Returns a MODE to halfop each of nicks on channel."""
    assert isChannel(channel), channel
    assert filter(isNick, nicks) == nicks, nicks
    return IrcMsg(prefix=prefix,
                  command=MODE,
                  args=(channel, '+' + ('h'*len(nicks)), nicks))

def dehalfop(channel, nick, prefix=''):
    """Returns a MODE to dehalfop nick on channel."""
    assert isChannel(channel), channel
    assert isNick(nick), nick
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '-h', nick))

def dehalfops(channel, nicks, prefix=''):
    """Returns a MODE to dehalfop each of nicks on channel."""
    assert isChannel(channel), channel
    assert filter(isNick, nicks) == nicks, nicks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '-' + ('h'*len(nicks)), nicks))

def voice(channel, nick, prefix=''):
    """Returns a MODE to voice nick on channel."""
    assert isChannel(channel), channel
    assert isNick(nick), nick
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '+v', nick))

def voices(channel, nicks, prefix=''):
    """Returns a MODE to voice each of nicks on channel."""
    assert isChannel(channel), channel
    assert filter(isNick, nicks) == nicks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '+' + ('v'*len(nicks)), nicks))

def devoice(channel, nick, prefix=''):
    """Returns a MODE to devoice nick on channel."""
    assert isChannel(channel), channel
    assert isNick(nick), nick
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '-v', nick))

def devoices(channel, nicks, prefix=''):
    """Returns a MODE to devoice each of nicks on channel."""
    assert isChannel(channel), channel
    assert filter(isNick, nicks) == nicks, nicks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '-' + ('v'*len(nicks)), nicks))

def ban(channel, hostmask, exception='', prefix=''):
    """Returns a MODE to ban nick on channel."""
    assert isChannel(channel), channel
    assert isUserHostmask(hostmask), hostmask
    modes = [('+b', hostmask)]
    if exception:
        modes.append(('+e', exception))
    return IrcMsg(prefix=prefix, command=MODE,
                  args=[channel] + ircutils.joinModes(modes))

def bans(channel, hostmasks, exceptions=(), prefix=''):
    """Returns a MODE to ban each of nicks on channel."""
    assert isChannel(channel), channel
    assert filter(isUserHostmask, hostmasks) == hostmasks, hostmasks
    modes = [('+b', s) for s in hostmasks] + [('+e', s) for s in exceptions]
    return IrcMsg(prefix=prefix, command=MODE,
                  args=[channel] + ircutils.joinModes(modes))

def unban(channel, hostmask, prefix=''):
    """Returns a MODE to unban nick on channel."""
    assert isChannel(channel), channel
    assert isUserHostmask(hostmask), hostmask
    return IrcMsg(prefix=prefix, command=MODE, args=(channel, '-b', hostmask))

def unbans(channel, hostmasks, prefix=''):
    """Returns a MODE to unban each of nicks on channel."""
    assert isChannel(channel), channel
    assert filter(isUserHostmask, hostmasks) == hostmasks, hostmasks
    return IrcMsg(prefix=prefix, command=MODE,
                  args=(channel, '-' + ('b'*len(hostmasks)), hostmasks))

def kick(channel, nick, msg='', prefix=''):
    """Returns a KICK to kick nick from channel with the message msg."""
    assert isChannel(channel), channel
    assert isNick(nick), nick
    if msg:
        return IrcMsg(prefix=prefix, command='KICK', args=(channel, nick, msg))
    else:
        return IrcMsg(prefix=prefix, command='KICK', args=(channel, nick))

def kicks(channel, nicks, msg='', prefix=''):
    """Returns a KICK to kick each of nicks from channel with the message msg.
    """
    assert isChannel(channel), channel
    assert filter(isNick, nicks) == nicks, nicks
    if msg:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, ','.join(nicks), msg))
    else:
        return IrcMsg(prefix=prefix, command='KICK',
                      args=(channel, ','.join(nicks)))

def privmsg(recipient, msg, prefix=''):
    """Returns a PRIVMSG to recipient with the message msg."""
    assert (isChannel(recipient) or isNick(recipient)), recipient
    assert msg, 'msg must not be empty.'
    return IrcMsg(prefix=prefix, command='PRIVMSG', args=(recipient, msg))

def action(recipient, msg, prefix=''):
    """Returns a PRIVMSG ACTION to recipient with the message msg."""
    assert (isChannel(recipient) or isNick(recipient)), recipient
    assert msg, 'msg must not be empty.'
    return IrcMsg(prefix=prefix, command='PRIVMSG',
                  args=(recipient,'\x01ACTION %s\x01'% msg))

def notice(recipient, msg, prefix=''):
    """Returns a NOTICE to recipient with the message msg."""
    assert (isChannel(recipient) or isNick(recipient)), recipient
    assert msg, 'msg must not be empty.'
    return IrcMsg(prefix=prefix, command='NOTICE', args=(recipient, msg))

def join(channel, key=None, prefix=''):
    """Returns a JOIN to a channel"""
    assert isChannel(channel), channel
    if key is None:
        return IrcMsg(prefix=prefix, command='JOIN', args=(channel,))
    else:
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
    assert filter(isChannel, channels) == channels, channels
    if keys is None:
        keys = []
    assert len(keys) <= len(channels)
    if not keys:
        return IrcMsg(prefix=prefix,
                      command='JOIN',
                      args=(','.join(channels),))
    else:
        for key in keys:
            assert key.translate(string.ascii, string.ascii[128:]) == key and \
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
    assert isChannel(channel), channel
    if msg:
        return IrcMsg(prefix=prefix, command='PART', args=(channel, msg))
    else:
        return IrcMsg(prefix=prefix, command='PART', args=(channel,))

def parts(channels, msg='', prefix=''):
    """Returns a PART from each of channels with the message msg."""
    assert filter(isChannel, channels) == channels, channels
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

def topic(channel, topic, prefix=''):
    """Returns a TOPIC for channel with the topic topic."""
    assert isChannel(channel), channel
    return IrcMsg(prefix=prefix, command='TOPIC', args=(channel, topic))

def nick(nick, prefix=''):
    """Returns a NICK with nick nick."""
    assert isNick(nick), nick
    return IrcMsg(prefix=prefix, command='NICK', args=(nick,))

def user(ident, user, prefix=''):
    """Returns a USER with ident ident and user user."""
    assert '\x00' not in ident and \
           '\r' not in ident and \
           '\n' not in ident and \
           ' ' not in ident and \
           '@' not in ident
    return IrcMsg(prefix=prefix, command='USER', args=(ident, '0', '*', user))

def who(hostmaskOrChannel, prefix=''):
    """Returns a WHO for the hostmask or channel hostmaskOrChannel."""
    assert isChannel(hostmaskOrChannel) or isUserHostmask(hostmaskOrChannel), \
           hostmaskOrChannel
    return IrcMsg(prefix=prefix, command='WHO', args=(hostmaskOrChannel,))

def whois(nick, prefix=''):
    """Returns a WHOIS for nick."""
    assert isNick(nick), nick
    return IrcMsg(prefix=prefix, command='WHOIS', args=(nick,))

def invite(channel, nick, prefix=''):
    """Returns an INVITE for nick."""
    assert isNick(nick), nick
    return IrcMsg(prefix=prefix, command='INVITE', args=(channel, nick))

def password(password, prefix=''):
    assert password, 'password must not be empty.'
    return IrcMsg(prefix=prefix, command='PASS', args=(password,))

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
