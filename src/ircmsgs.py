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

import ircutils

###
# IrcMsg class -- used for representing IRC messages acquired from a network.
###
class IrcMsg(object):
    """Class to represent an IRC message.
    """
    #__slots__ = ('_args', '_command', '_host', '_nick', '_prefix', '_user')
    def __init__(self, s='', command='', args=None, prefix='', msg=None):
        if msg:
            prefix = msg.prefix
            command = msg.command
            args = msg.args
        if command: # Must be using command=, args=, prefix= form.
            if args is not None:
                for arg in args:
                    if not ircutils.validArgument(arg):
                        raise ValueError, 'Invalid argument: %r' % arg
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
                args.append(last.strip())
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

##     def copy(self):
##         return self.__class__(command=self.command,
##                               args=self.args,
##                               prefix=self.prefix)

    def __str__(self):
        ret = ''
        if self.prefix:
            #debug.printf(1)
            ret = ':%s %s' % (self.prefix, self.command)
        else:
            ret = self.command
        if self.args:
            if len(self.args) > 1:
                #debug.printf(2)
                ret = '%s %s :%s\r\n' % (ret, ' '.join(self.args[:-1]),
                                         self.args[-1])
            else:
                #debug.printf(3)
                ret = '%s :%s\r\n' % (ret, self.args[0])
        else:
            #debug.printf(4)
            ret = ret + '\r\n'
        return ret

    def __len__(self):
        # This might not take into account the length of the prefix, but leaves
        # some room for variation.
        ret = 0
        if self.prefix:
            ret += len(self.prefix)
        ret += len(self.command)
        if self.args:
            for arg in self.args:
                ret += len(arg)
        ret += 2 # For the colon before the prefix and before the last arg.
        ret += 2 # For the ! and the @ in the prefix.
        return ret

    def __eq__(self, other):
        return hash(self) == hash(other) and\
               self.command == other.command and\
               self.prefix == other.prefix and\
               self.args == other.args

    def __hash__(self):
        return hash(self.command) & hash(self.prefix) & hash(self.args)

    def __repr__(self):
        return '%s(prefix=%r, command=%r, args=%r)' % \
               (self.__class__.__name__, self.prefix, self.command, self.args)


def isAction(msg):
    return msg.command == 'PRIVMSG' and \
           msg.args[1].startswith('\x01ACTION') and \
           msg.args[1].endswith('\x01')

_unactionre = re.compile(r'\x01ACTION (.*)\x01')
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

def pong(payload):
    """Takes a payload and returns the proper PONG IrcMsg"""
    return IrcMsg(command='PONG', args=(payload,))

def fromPong(msg):
    """Takes a PONG IrcMsg and returns the payload."""
    assert msg.command == 'PONG'
    return msg.args[0]

def ping(payload):
    """Takes a payload and returns the proper PING IrcMsg"""
    return IrcMsg(command='PING', args=(payload,))

def fromPing(msg):
    """Takes a PING IrcMsg and returns the payload."""
    assert msg.command == 'PING'
    return msg.args[0]

def op(channel, nick):
    return IrcMsg(command=MODE, args=(channel, '+o', nick))

def ops(channel, nicks):
    return IrcMsg(command=MODE,
                  args=(channel, '+' + ('o'*len(nicks)), nicks))

def deop(channel, nick):
    return IrcMsg(command=MODE, args=(channel, '-o', nick))

def deops(channel, nicks):
    return IrcMsg(command=MODE, args=(channel, '-' + ('o'*len(nicks)), nicks))

def halfop(channel, nick):
    return IrcMsg(command=MODE, args=(channel, '+h', nick))

def halfops(channel, nicks):
    return IrcMsg(command=MODE, args=(channel, '+' + ('h'*len(nicks)), nicks))

def dehalfop(channel, nick):
    return IrcMsg(command=MODE, args=(channel, '-h', nick))

def dehalfops(channel, nicks):
    return IrcMsg(command=MODE, args=(channel, '-' + ('h'*len(nicks)), nicks))

def voice(channel, nick):
    return IrcMsg(command=MODE, args=(channel, '+v', nick))

def voices(channel, nicks):
    return IrcMsg(command=MODE, args=(channel, '+' + ('v'*len(nicks)), nicks))

def devoice(channel, nick):
    return IrcMsg(command=MODE, args=(channel, '-v', nick))

def devoices(channel, nicks):
    return IrcMsg(command=MODE, args=(channel, '-' + ('v'*len(nicks)), nicks))

def ban(channel, hostmask):
    return IrcMsg(command=MODE, args=(channel, '+b', hostmask))

def bans(channel, hostmasks):
    return IrcMsg(command=MODE,
                  args=(channel, '+' + ('b'*len(hostmasks)), hostmasks))

def unban(channel, hostmask):
    return IrcMsg(command=MODE, args=(channel, '-b', hostmask))

def unbans(channel, hostmasks):
    return IrcMsg(command=MODE,
                  args=(channel, '-' + ('b'*len(hostmasks)), hostmasks))

def kick(channel, nick, msg=''):
    if msg:
        return IrcMsg(command='KICK', args=(channel, nick, msg))
    else:
        return IrcMsg(command='KICK', args=(channel, nick))

def kicks(channel, nicks, msg=''):
    if msg:
        return IrcMsg(command='KICK', args=(channel, ','.join(nicks), msg))
    else:
        return IrcMsg(command='KICK', args=(channel, ','.join(nicks)))

def privmsg(recipient, msg):
    return IrcMsg(command='PRIVMSG', args=(recipient, msg))

def action(recipient, msg):
    return IrcMsg(command='PRIVMSG', args=(recipient,'\x01ACTION %s\x01'% msg))

def notice(recipient, msg):
    return IrcMsg(command='NOTICE', args=(recipient, msg))

def join(channel):
    return IrcMsg(command='JOIN', args=(channel,))

def joins(channels):
    return IrcMsg(command='JOIN', args=(','.join(channels),))

def part(channel, msg=""):
    if msg:
        return IrcMsg(command='PART', args=(channel, msg))
    else:
        return IrcMsg(command='PART', args=(channel,))

def parts(channels, msg=""):
    if msg:
        return IrcMsg(command='PART', args=(','.join(channels), msg,))
    else:
        return IrcMsg(command='PART', args=(','.join(channels),))

def quit(msg=''):
    if msg:
        return IrcMsg(command='QUIT', args=(msg,))
    else:
        return IrcMsg(command='QUIT')

def topic(channel, topic):
    return IrcMsg(command='TOPIC', args=(channel, topic))

def nick(nick):
    return IrcMsg(command='NICK', args=(nick,))

def user(user, ident):
    return IrcMsg(command='USER', args=(ident, '0', '*', user))

def who(hostmask):
    return IrcMsg(command='WHO', args=(hostmask,))

def whois(nick):
    return IrcMsg(command='WHOIS', args=(nick,))

def invite(channel, user):
    return IrcMsg(command='INVITE', args=(channel, user))

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
