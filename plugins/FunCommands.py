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
Provides a multitude of fun, useless commands.

Commands include:
  netstats
  ord
  chr
  base
  hexlify
  unhexlify
  xor
  mimetype
  md5
  sha
  urlquote
  urlunquote
  rot13
  coin
  dice
  leet
  cpustats
  uptime
  calc
  objects
  last
  lastfrom
  lithp
"""

from baseplugin import *

import os
import gc
import re
import new
import md5
import sha
import time
import math
import cmath
import types
import string
import random
import urllib
import inspect
import binascii
import threading
import mimetypes

#import conf
import debug
import ircmsgs
import privmsgs
import callbacks


class FunCommands(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.sentMsgs = 0
        self.recvdMsgs = 0
        self.sentBytes = 0
        self.recvdBytes = 0
        self._startTime = time.time()

    def inFilter(self, irc, msg):
        self.recvdMsgs += 1
        self.recvdBytes += len(str(msg))
        return msg

    def outFilter(self, irc, msg):
        self.sentMsgs += 1
        self.sentBytes += len(str(msg))
        return msg

    def netstats(self, irc, msg, args):
        "takes no arguments"
        #debug.printf('HEY I GOT RELOADED')
        irc.reply(msg,
                   'I have received %s messages for a total of %s bytes.  '\
                   'I have sent %s messages for a total of %s bytes.' %\
                   (self.recvdMsgs, self.recvdBytes,
                    self.sentMsgs, self.sentBytes))

    def ord(self, irc, msg, args):
        """<letter>

        Returns the 8-bit value of <letter>.
        """
        letter = privmsgs.getArgs(args)
        if len(letter) != 1:
            irc.error(msg, 'Letter must be of length 1 (for obvious reasons)')
        else:
            i = ord(letter)
            irc.reply(msg, str(i))

    def chr(self, irc, msg, args):
        """<number>

        Returns the character associated with the 8-bit value <number>
        """
        try:
            i = privmsgs.getArgs(args)
            if i.startswith('0x'):
                base = 16
            elif i.startswith('0b'):
                base = 2
                i = i[2:]
            elif i.startswith('0'):
                base = 8
            else:
                base = 10
            i = int(i, base)
            irc.reply(msg, chr(i))
        except ValueError:
            irc.error(msg, 'That number doesn\'t map to an 8-bit character.')
                
    def base(self, irc, msg, args):
        """<base> <number>

        Converts from base <base> the number <number>
        """
        (base, number) = privmsgs.getArgs(args, needed=2)
        irc.reply(msg, str(long(number, int(base))))

    def binary(self, irc, msg, args):
        """<text>

        Returns the binary representation of <text>.
        """
        L = []
        for c in privmsgs.getArgs(args):
            i = ord(c)
            while i:
                if i & 1:
                    L.append('1')
                else:
                    L.append('0')
                i >>= 1
        irc.reply(msg, ''.join(L))
        
    def hexlify(self, irc, msg, args):
        "<text>; turn string into a hexstring."
        text = privmsgs.getArgs(args)
        irc.reply(msg, binascii.hexlify(text))

    def unhexlify(self, irc, msg, args):
        "<even number of hexadecimal digits>"
        text = privmsgs.getArgs(args)
        try:
            s = binascii.unhexlify(text)
            irc.reply(msg, s)
        except TypeError:
            irc.error(msg, 'Invalid input.')

    def xor(self, irc, msg, args):
        "<password> <text>"
        (password, text) = privmsgs.getArgs(args, 2)
        passwordlen = len(password)
        i = 0
        ret = []
        for c in text:
            ret.append(chr(ord(c) ^ ord(password[i])))
            i = (i + 1) % passwordlen
        irc.reply(msg, repr(''.join(ret)))

    def mimetype(self, irc, msg, args):
        "<filename>"
        filename = privmsgs.getArgs(args)
        (type, encoding) = mimetypes.guess_type(filename)
        if type is not None:
            irc.reply(msg, type)
        else:
            s = 'I couldn\'t figure out that filename.'
            irc.reply(msg, s)

    def md5(self, irc, msg, args):
        "<text>; returns the md5 sum of the text."
        text = privmsgs.getArgs(args)
        irc.reply(msg, md5.md5(text).hexdigest())

    def sha(self, irc, msg, args):
        "<text>; returns the sha sum of the text."
        text = privmsgs.getArgs(args)
        irc.reply(msg, sha.sha(text).hexdigest())

    def urlquote(self, irc, msg, args):
        "<text>; returns the URL quoted form of the text."
        text = privmsgs.getArgs(args)
        irc.reply(msg, urllib.quote(text))

    def urlunquote(self, irc, msg, args):
        "<text>; returns the text un-URL quoted."
        text = privmsgs.getArgs(args)
        s = urllib.unquote(text)
        irc.reply(msg, s)

    def rot13(self, irc, msg, args):
        "<text>"
        text = privmsgs.getArgs(args)
        irc.reply(msg, text.encode('rot13'))

    def coin(self, irc, msg, args):
        "takes no arguments"
        if random.randrange(0, 2):
            irc.reply(msg, 'The coin landed heads.')
        else:
            irc.reply(msg, 'The coin landed tails.')

    _dicere = re.compile(r'(\d+)d(\d+)')
    def dice(self, irc, msg, args):
        "<dice>d<sides> (e.g., 2d6 will roll 2 six-sided dice)"
        arg = privmsgs.getArgs(args)
        m = re.match(self._dicere, arg)
        if m:
            (dice, sides) = [int(s) for s in m.groups()]
            if dice > 6:
                irc.error(msg, 'You can\'t roll more than 6 dice.')
            elif sides > 100:
                irc.error(msg, 'Dice can\'t have more than 100 sides.')
            else:
                L = [0] * dice
                for i in xrange(dice):
                    L[i] = random.randrange(1, sides+1)
                irc.reply(msg, ', '.join([str(x) for x in L]))
        else:
            irc.error(msg, 'Dice must be of the form <dice>d<sides>')

    def lithp(self, irc, msg, args):
        "<text>"
        text = privmsgs.getArgs(args)
        text = text.replace('sh', 'th')
        text = text.replace('SH', 'TH')
        text = text.replace('ss', 'th')
        text = text.replace('SS', 'th')
        text = text.replace('s', 'th')
        text = text.replace('S', 'TH')
        text = text.replace('x', 'kth')
        text = text.replace('X', 'KTH')
        irc.reply(msg, text)
        
    _leettrans = string.maketrans('oOaAeElBTiIts', '004433187!1+5')
    _leetres = ((re.compile(r'\b(?:(?:[yY][o0O][oO0uU])|u)\b'), 'j00'),
                (re.compile(r'fear'), 'ph33r'),
                (re.compile(r'[aA][tT][eE]'), '8'),
                (re.compile(r'[aA][tT]'), '@'),
                (re.compile(r'[sS]\b'), 'z'),
                (re.compile(r'x'), '><'),)
    def leet(self, irc, msg, args):
        "<text>"
        s = privmsgs.getArgs(args)
        for (r, sub) in self._leetres:
            s = re.sub(r, sub, s)
        s = s.translate(self._leettrans)
        irc.reply(msg, s)

    def cpustats(self, irc, msg, args):
        "takes no arguments"
        (user, system, childUser, childSystem, elapsed) = os.times()
        timeRunning = time.time() - self._startTime
        threads = threading.activeCount()
        response ='I have taken %s seconds of user time and %s seconds of '\
                  'system time, for a total of %s seconds of CPU time.  My '\
                  'children have taken %s seconds of user time and %s seconds'\
                  ' of system time for a total of %s seconds of CPU time.  ' \
                  'I\'ve taken a total of %s%% of this computer\'s time.  ' \
                  'I currently have %s active %s.' %\
                    (user, system, user + system,
                     childUser, childSystem, childUser + childSystem,
                     (user+system+childUser+childSystem)/timeRunning,
                     threads, threads == 1 and 'thread' or 'threads')
        irc.reply(msg, response)

    def uptime(self, irc, msg, args):
        "takes no arguments"
        elapsed = time.time() - self._startTime
        days, elapsed = elapsed // 86400, elapsed % 86400
        hours, elapsed = elapsed // 3600, elapsed % 3600
        minutes, seconds = elapsed // 60, elapsed % 60
        response = 'I have been running for %i %s, %i %s, %i %s, and %i %s.' %\
                   (days, days == 1 and 'day' or 'days',
                    hours, hours == 1 and 'hour' or 'hours',
                    minutes, minutes == 1 and 'minute' or 'minutes',
                    seconds, seconds == 1 and 'second' or 'seconds')
        irc.reply(msg, response)


    ###
    # So this is how the 'calc' command works:
    # First, we make a nice little safe environment for evaluation; basically,
    # the names in the 'math' and 'cmath' modules.  Then, we remove the ability
    # of a random user to get ints evaluated: this means we have to turn all
    # int literals (even octal numbers and hexadecimal numbers) into floats.
    # Then we delete all square brackets, underscores, and whitespace, so no
    # one can do list comprehensions or call __...__ functions.
    ###
    _mathEnv = {}
    _mathEnv.update(math.__dict__)
    _mathEnv.update(cmath.__dict__)
    _mathEnv['__builtins__'] = new.module('__builtins__')
    _mathInt = re.compile(r'(?<!\d|\.)(\d+)(?!\d+|\.|\.\d+)')
    _mathHex = re.compile(r'(0x[A-Fa-f\d]+)')
    _mathOctal = re.compile(r'(^|[^\dA-Fa-f])(0[0-7]+)')
    def calc(self, irc, msg, args):
        "<math expr>"
        text = privmsgs.getArgs(args)
        text = text.translate(string.ascii, '_[] \t')
        text = text.replace('lambda', '')
        def hex2float(m):
            literal = m.group(1)
            i = long(literal, 16)
            return '%s.0' % i
        def oct2float(m):
            (previous, literal) = m.groups()
            i = long(literal, 8)
            return '%s%s.0' % (previous, i)
        text = self._mathHex.sub(hex2float, text)
        #debug.printf('After unhexing: %r' % text)
        text = self._mathOctal.sub(oct2float, text)
        #debug.printf('After unocting: %r' % text)
        text = self._mathInt.sub(r'\1.0', text)
        #debug.printf('After uninting: %r' % text)
        try:
            x = complex(eval(text, self._mathEnv, self._mathEnv))
            real = x.real
            imag = x.imag
            if real == int(real):
                real = int(real)
            if real < 1e-12:
                real = 0
            if imag < 1e-12:
                imag = 0
            if real < 1e-12 and imag < 1e-12:
                irc.reply(msg, '0')
            elif imag < 1e-12:
                irc.reply(msg, '%s' % real)
            elif real < 1e-12:
                irc.reply(msg, '%s' % imag)
            else:
                irc.reply(msg, '%s + %si' % (real, imag))
        except Exception, e:
            irc.reply(msg, debug.exnToString(e))

    def objects(self, irc, msg, args):
        "takes no arguments.  Returns the number of Python objects in memory."
        objs = gc.get_objects()
        classes = len([obj for obj in objs if inspect.isclass(obj)])
        functions = len([obj for obj in objs if inspect.isroutine(obj)])
        modules = len([obj for obj in objs if inspect.ismodule(obj)])
        dicts = len([obj for obj in objs if type(obj) == types.DictType])
        lists = len([obj for obj in objs if type(obj) == types.ListType])
        tuples = len([obj for obj in objs if type(obj) == types.TupleType])
        response = 'I have %s objects: %s modules, %s classes, %s functions, '\
                   '%s dictionaries, %s lists, and %s tuples (and a few other'\
                   ' different types).' %\
                   (len(objs), modules, classes, functions,
                    dicts, lists, tuples)
        irc.reply(msg, response)

    def last(self, irc, msg, args):
        "[<channel>] <message number (defaults to 1, the last message)>"
        channel = privmsgs.getChannel(msg, args)
        n = privmsgs.getArgs(args, needed=0, optional=1)
        if n == '':
            n = 1
        else:
            n = int(n)
        n += 1 # To remove the last question asked.
        for msg in reviter(irc.state.history):
            if msg.command == 'PRIVMSG' and msg.args[0] == channel and n == 1:
                irc.reply(msg, msg.args[1])
                return
            else:
                n -= 1
        if n > 1:
            s = 'I don\'t have a history of that many messages.'
            irc.error(msg, s)

    def lastfrom(self, irc, msg, args):
        "[<channel>] <nick>"
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args)
        for m in reviter(irc.state.history):
            if m.command == 'PRIVMSG' and \
               m.nick == nick and \
               m.args[0] == channel:
                if ircmsgs.isAction(m):
                    irc.reply(msg, '* %s %s' % (nick, ircmsgs.unAction(m)))
                else:
                    irc.reply(msg, '<%s> %s' % (nick, m.args[1]))
                return
        irc.error(msg, 'I don\'t remember a message from that person.')
            

Class = FunCommands
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
