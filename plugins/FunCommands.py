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
"""

from baseplugin import *
from itertools import imap, ifilter

import os
import gc
import re
import imp
import sys
import new
import md5
import sha
import time
import math
import cmath
import string
import random
import urllib
import inspect
import binascii
import threading
import mimetypes

#import conf
import debug
import utils
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

    def inFilter(self, irc, msg):
        self.recvdMsgs += 1
        self.recvdBytes += len(str(msg))
        return msg

    def outFilter(self, irc, msg):
        self.sentMsgs += 1
        self.sentBytes += len(str(msg))
        return msg

    def netstats(self, irc, msg, args):
        """takes no arguments

        Returns some interesting network-related statistics.
        """
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
            irc.reply(msg, str(ord(letter)))

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
            LL = []
            i = ord(c)
            counter = 8
            while i:
                counter -= 1
                if i & 1:
                    LL.append('1')
                else:
                    LL.append('0')
                i >>= 1
            while counter:
                LL.append('0')
                counter -= 1
            LL.reverse()
            L.extend(LL)
        irc.reply(msg, ''.join(L))


    def encode(self, irc, msg, args):
        """<encoding> <text>

        Returns an encoded form of the given text; the valid encodings are
        available in the documentation of the Python codecs module.
        """
        encoding, text = privmsgs.getArgs(args, needed=2)
        irc.reply(msg, text.encode(encoding))

    def decode(self, irc, msg, args):
        """<encoding> <text>

        Returns an un-encoded form of the given text; the valid encodings are
        available in the documentation of the Python codecs module.
        """
        encoding, text = privmsgs.getArgs(args, needed=2)
        irc.reply(msg, text.decode(encoding).encode('utf-8'))

    def hexlify(self, irc, msg, args):
        """<text>

        Returns a hexstring from the given string; a hexstring is a string
        composed of the hexadecimal value of each character in the string
        """
        text = privmsgs.getArgs(args)
        irc.reply(msg, binascii.hexlify(text))

    def unhexlify(self, irc, msg, args):
        """<hexstring>

        Returns the string corresponding to <hexstring>.  Obviously,
        <hexstring> must be a string of hexadecimal digits.
        """
        text = privmsgs.getArgs(args)
        try:
            s = binascii.unhexlify(text)
            irc.reply(msg, s)
        except TypeError:
            irc.error(msg, 'Invalid input.')

    def xor(self, irc, msg, args):
        """<password> <text>

        Returns <text> XOR-encrypted with <password>.  See
        http://www.yoe.org/developer/xor.html for information about XOR
        encryption.
        """
        (password, text) = privmsgs.getArgs(args, 2)
        passwordlen = len(password)
        i = 0
        ret = []
        for c in text:
            ret.append(chr(ord(c) ^ ord(password[i])))
            i = (i + 1) % passwordlen
        irc.reply(msg, ''.join(ret))

    def mimetype(self, irc, msg, args):
        """<filename>

        Returns the mime type associated with <filename>
        """
        filename = privmsgs.getArgs(args)
        (type, encoding) = mimetypes.guess_type(filename)
        if type is not None:
            irc.reply(msg, type)
        else:
            s = 'I couldn\'t figure out that filename.'
            irc.reply(msg, s)

    def md5(self, irc, msg, args):
        """<text>

        Returns the md5 hash of a given string.  Read
        http://www.rsasecurity.com/rsalabs/faq/3-6-6.html for more information
        about md5.
        """
        text = privmsgs.getArgs(args)
        irc.reply(msg, md5.md5(text).hexdigest())

    def sha(self, irc, msg, args):
        """<text>

        Returns the SHA hash of a given string.  Read
        http://www.secure-hash-algorithm-md5-sha-1.co.uk/ for more information
        about SHA.
        """
        text = privmsgs.getArgs(args)
        irc.reply(msg, sha.sha(text).hexdigest())

    def urlquote(self, irc, msg, args):
        """<text>

        Returns the URL quoted form of the text.
        """
        text = privmsgs.getArgs(args)
        irc.reply(msg, urllib.quote(text))

    def urlunquote(self, irc, msg, args):
        """<text>

        Returns the text un-URL quoted.
        """
        text = privmsgs.getArgs(args)
        s = urllib.unquote(text)
        irc.reply(msg, s)

    def rot13(self, irc, msg, args):
        """<text>

        Rotates <text> 13 characters to the right in the alphabet.  Rot13 is
        commonly used for text that simply needs to be hidden from inadvertent
        reading by roaming eyes, since it's easily reversible.
        """
        text = privmsgs.getArgs(args)
        irc.reply(msg, text.encode('rot13'))

    def coin(self, irc, msg, args):
        """takes no arguments

        Flips a coin and returns the result.
        """
        if random.randrange(0, 2):
            irc.reply(msg, 'heads')
        else:
            irc.reply(msg, 'tails')

    _dicere = re.compile(r'(\d+)d(\d+)')
    def dice(self, irc, msg, args):
        """<dice>d<sides>

        Rolls a die with <sides> number of sides <dice> times.
        For example, 2d6 will roll 2 six-sided dice; 10d10 will roll 10
        ten-sided dice.
        """
        arg = privmsgs.getArgs(args)
        m = re.match(self._dicere, arg)
        if m:
            (dice, sides) = map(int, m.groups())
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
        """<text>

        Returns the lisping version of <text>
        """
        text = privmsgs.getArgs(args)
        text = text.replace('sh', 'th')
        text = text.replace('SH', 'TH')
        text = text.replace('ss', 'th')
        text = text.replace('SS', 'th')
        text = text.replace('s', 'th')
        text = text.replace('z', 'th')
        text = text.replace('S', 'TH')
        text = text.replace('Z', 'TH')
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
        """<text>

        Returns the l33tspeak version of <text>
        """
        s = privmsgs.getArgs(args)
        for (r, sub) in self._leetres:
            s = re.sub(r, sub, s)
        s = s.translate(self._leettrans)
        irc.reply(msg, s)

    def cpustats(self, irc, msg, args):
        """takes no arguments

        Returns some interesting CPU-related statistics on the bot.
        """
        (user, system, childUser, childSystem, elapsed) = os.times()
        timeRunning = time.time() - world.startedAt
        threads = threading.activeCount()
        response ='I have taken %s seconds of user time and %s seconds of '\
                  'system time, for a total of %s seconds of CPU time.  My '\
                  'children have taken %s seconds of user time and %s seconds'\
                  ' of system time for a total of %s seconds of CPU time.  ' \
                  'I\'ve taken a total of %s%% of this computer\'s time.  ' \
                  'Out of %s spawned %s, I have %s active.' %\
                    (user, system, user + system,
                     childUser, childSystem, childUser + childSystem,
                     (user+system+childUser+childSystem)/timeRunning,
                     world.threadsSpawned,
                     world.threadsSpawned == 1 and 'thread' or 'threads',
                     threads)
        irc.reply(msg, response)

    def uptime(self, irc, msg, args):
        "takes no arguments"
        response = 'I have been running for %s.' % \
                   utils.timeElapsed(time.time() - world.startedAt)
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
    _mathEnv = {'__builtins__': new.module('__builtins__'), 'i': 1j}
    _mathEnv.update(math.__dict__)
    _mathEnv.update(cmath.__dict__)
    _mathInt = re.compile(r'(?<!\d|\.)(\d+)(?!\d+|\.|\.\d+)')
    _mathHex = re.compile(r'(0x[A-Fa-f\d]+)')
    _mathOctal = re.compile(r'(^|[^\dA-Fa-f.])(0[0-7]+)')
    def _complexToString(self, x):
        real = x.real
        imag = x.imag
        if real < 1e-12 and imag < 1e-12:
            return '0'
        if int(real) == real:
            real = int(real)
        if int(imag) == imag:
            imag = int(imag)
        if real < 1e-12:
            real = 0
        if imag < 1e-12:
            imag = 0
        if imag == 0:
            return str(real)
        elif real == 0:
            return '%s*i' % imag
        else:
            return '%s+%si' % (real, imag)

    def calc(self, irc, msg, args):
        """<math expression>

        Returns the value of the evaluted <math expression>.  The syntax is
        Python syntax; the type of arithmetic is floating point.
        """
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
            irc.reply(msg, self._complexToString(x))
        except OverflowError:
            irc.reply(msg, 'Go get scanez, this is a *real* math problem!')
        except Exception, e:
            irc.reply(msg, debug.exnToString(e))

    def rpn(self, irc, msg, args):
        """<rpn math expression>

        Returns the value of an RPN expression.
        """
        stack = []
        for arg in args:
            try:
                stack.append(float(arg))
            except ValueError: # Not a float.
                if arg in self._mathEnv:
                    f = self._mathEnv[arg]
                    if callable(f):
                        called = False
                        arguments = []
                        while not called and stack:
                            arguments.append(stack.pop())
                            try:
                                stack.append(f(*arguments))
                                called = True
                            except TypeError:
                                pass
                        if not called:
                            irc.error(msg, 'Not enough arguments for %s' % arg)
                            return
                    else:
                        stack.append(f)
                else:
                    arg2 = stack.pop()
                    arg1 = stack.pop()
                    stack.append(eval('%s%s%s' % (arg1, arg, arg2),
                                      self._mathEnv, self._mathEnv))
        if len(stack) == 1:
            irc.reply(msg, str(self._complexToString(complex(stack[0]))))
        else:
            s = ', '.join(imap(self._complexToString, imap(complex, stack)))
            irc.reply(msg, 'Stack: [%s]' % s)

    def objects(self, irc, msg, args):
        """takes no arguments.

        Returns the number and types of Python objects in memory."""
        classes = 0
        functions = 0
        modules = 0
        dicts = 0
        lists = 0
        tuples = 0
        refcounts = 0
        objs = gc.get_objects()
        for obj in objs:
            if isinstance(obj, tuple):
                tuples += 1
            elif inspect.isroutine(obj):
                functions += 1
            elif isinstance(obj, dict):
                dicts += 1
            elif isinstance(obj, list):
                lists += 1
            elif inspect.isclass(obj):
                classes += 1
            elif inspect.ismodule(obj):
                modules += 1
            refcounts += sys.getrefcount(obj)
        response = 'I have %s objects: %s modules, %s classes, %s functions, '\
                   '%s dictionaries, %s lists, and %s tuples (and a few other'\
                   ' different types).  I have a total of %s references.' %\
                   (len(objs), modules, classes, functions,
                    dicts, lists, tuples, refcounts)
        irc.reply(msg, response)

    def last(self, irc, msg, args):
        """[<channel>] <message number>

        Gets message number <message number> from the bot's history.
        <message number> defaults to 1, the last message prior to this command
        itself.  <channel> is only necessary if the message isn't sent in the
        channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        n = privmsgs.getArgs(args, needed=0, optional=1)
        if n == '':
            n = 1
        else:
            try:
                n = int(n)
            except ValueError:
                irc.error(msg, '<message number> must be an integer.')
                return
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
        """[<channel>] <nick>

        Returns the last message in <channel> from <nick>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args)
        for m in reviter(irc.state.history):
            if m.command == 'PRIVMSG' and \
               m.nick == nick and \
               m.args[0] == channel:
                if ircmsgs.isAction(m):
                    irc.reply(msg, '* %s %s' % (nick, ircmsgs.unAction(m)))
                    return
                else:
                    irc.reply(msg, '<%s> %s' % (nick, m.args[1]))
                    return
                return
        irc.error(msg, 'I don\'t remember a message from that person.')

    def levenshtein(self, irc, msg, args):
        """<string1> <string2>

        Returns the levenshtein distance (also known as the "edit distance"
        between <string1> and <string2>
        """
        (s1, s2) = privmsgs.getArgs(args, needed=2)
        irc.reply(msg, str(utils.distance(s1, s2)))

    def soundex(self, irc, msg, args):
        """<string> [<length>]

        Returns the Soundex hash to a given length.  The length defaults to
        4, since that's the standard length for a soundex hash.  For unlimited
        length, use 0.
        """
        (s, length) = privmsgs.getArgs(args, optional=1)
        if length:
            length = int(length)
        else:
            length = 4
        irc.reply(msg, utils.soundex(s, length))

    modulechars = '%s%s%s' % (string.ascii_letters, string.digits, '_.')
    def pydoc(self, irc, msg, args):
        """<python function>

        Returns the __doc__ string for a given Python function.
        """
        funcname = privmsgs.getArgs(args)
        if funcname.translate(string.ascii, self.modulechars) != '':
            irc.error('That\'s not a valid module or function name.')
            return
        if '.' in funcname:
            parts = funcname.split('.')
            module = '.'.join(parts[:-1])
            if module not in __builtins__ and module not in sys.modules:
                path = os.path.dirname(os.__file__)
                for name in parts[:-1]:
                    try:
                        info = imp.find_module(name, path)
                        newmodule = imp.load_module(name, *info)
                        path = newmodule.__path__
                        info[1].close()
                    except ImportError:
                        irc.error(msg, 'No such module %s exists.' % module)
                        return
        try:
            s = eval(funcname + '.__doc__')
            s = s.replace('\n\n', '. ')
            s = ' '.join(s.split())
        except NameError:
            irc.error(msg, 'No such function exists.')
            return
        except AttributeError:
            irc.error(msg, 'That function has no documentation.')
            return
        irc.reply(msg, s)


Class = FunCommands

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
