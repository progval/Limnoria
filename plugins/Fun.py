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

__revision__ = "$Id$"

import plugins

import gc
import re
import sys
import md5
import sha
import random
import urllib
import inspect
import mimetypes
from itertools import imap

import conf
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks

class MyFunProxy(object):
    def reply(self, msg, s):
        self.s = s
        
class Fun(callbacks.Privmsg):
    def __init__(self):
        self.outFilters = ircutils.IrcDict()
        callbacks.Privmsg.__init__(self)

    def ping(self, irc, msg, args):
        """takes no arguments

        Checks to see if the bot is alive.
        """
        irc.reply('pong', prefixName=False)

    def hexip(self, irc, msg, args):
        """<ip>

        Returns the hexadecimal IP for that IP.
        """
        ip = privmsgs.getArgs(args)
        if not utils.isIP(ip):
            irc.error('%r is not a valid IP.' % ip)
            return
        quads = ip.split('.')
        ret = ""
        for quad in quads:
            i = int(quad)
            ret += '%02x' % i
        irc.reply(ret.upper())
            
    def ord(self, irc, msg, args):
        """<letter>

        Returns the 8-bit value of <letter>.
        """
        letter = privmsgs.getArgs(args)
        if len(letter) != 1:
            irc.error('Letter must be of length 1 (for obvious reasons)')
        else:
            irc.reply(str(ord(letter)))

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
            irc.reply(chr(i))
        except ValueError:
            irc.error('That number doesn\'t map to an 8-bit character.')

    def encode(self, irc, msg, args):
        """<encoding> <text>

        Returns an encoded form of the given text; the valid encodings are
        available in the documentation of the Python codecs module:
        <http://www.python.org/doc/lib/node127.html>.
        """
        encoding, text = privmsgs.getArgs(args, required=2)
        try:
            irc.reply(text.encode(encoding))
        except LookupError:
            irc.error('There is no such encoding %r' % encoding)

    def decode(self, irc, msg, args):
        """<encoding> <text>

        Returns an un-encoded form of the given text; the valid encodings are
        available in the documentation of the Python codecs module:
        <http://www.python.org/doc/lib/node127.html>.
        """
        encoding, text = privmsgs.getArgs(args, required=2)
        try:
            irc.reply(text.decode(encoding).encode('utf-8'))
        except LookupError:
            irc.error('There is no such encoding %r' % encoding)

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
        irc.reply(''.join(ret))

    def mimetype(self, irc, msg, args):
        """<filename>

        Returns the mime type associated with <filename>
        """
        filename = privmsgs.getArgs(args)
        (type, encoding) = mimetypes.guess_type(filename)
        if type is not None:
            irc.reply(type)
        else:
            s = 'I couldn\'t figure out that filename.'
            irc.reply(s)

    def md5(self, irc, msg, args):
        """<text>

        Returns the md5 hash of a given string.  Read
        http://www.rsasecurity.com/rsalabs/faq/3-6-6.html for more information
        about md5.
        """
        text = privmsgs.getArgs(args)
        irc.reply(md5.md5(text).hexdigest())

    def sha(self, irc, msg, args):
        """<text>

        Returns the SHA hash of a given string.  Read
        http://www.secure-hash-algorithm-md5-sha-1.co.uk/ for more information
        about SHA.
        """
        text = privmsgs.getArgs(args)
        irc.reply(sha.sha(text).hexdigest())

    def urlquote(self, irc, msg, args):
        """<text>

        Returns the URL quoted form of the text.
        """
        text = privmsgs.getArgs(args)
        irc.reply(urllib.quote(text))

    def urlunquote(self, irc, msg, args):
        """<text>

        Returns the text un-URL quoted.
        """
        text = privmsgs.getArgs(args)
        s = urllib.unquote(text)
        irc.reply(s)

    def coin(self, irc, msg, args):
        """takes no arguments

        Flips a coin and returns the result.
        """
        if random.randrange(0, 2):
            irc.reply('heads')
        else:
            irc.reply('tails')

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
            (dice, sides) = imap(int, m.groups())
            if dice > 6:
                irc.error('You can\'t roll more than 6 dice.')
            elif sides > 100:
                irc.error('Dice can\'t have more than 100 sides.')
            else:
                L = [0] * dice
                for i in xrange(dice):
                    L[i] = random.randrange(1, sides+1)
                irc.reply(utils.commaAndify([str(x) for x in L]))
        else:
            irc.error('Dice must be of the form <dice>d<sides>')

    def objects(self, irc, msg, args):
        """takes no arguments.

        Returns the number and types of Python objects in memory.
        """
        classes = 0
        functions = 0
        modules = 0
        strings = 0
        dicts = 0
        lists = 0
        tuples = 0
        refcounts = 0
        objs = gc.get_objects()
        for obj in objs:
            if isinstance(obj, str):
                strings += 1
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
                   '%s dictionaries, %s lists, %s tuples, %s strings, and a ' \
                   'few other odds and ends.  ' \
                   'I have a total of %s references.' % \
                   (len(objs), modules, classes, functions,
                    dicts, lists, tuples, strings, refcounts)
        irc.reply(response)

    def levenshtein(self, irc, msg, args):
        """<string1> <string2>

        Returns the levenshtein distance (also known as the "edit distance"
        between <string1> and <string2>
        """
        (s1, s2) = privmsgs.getArgs(args, required=2)
        irc.reply(str(utils.distance(s1, s2)))

    def soundex(self, irc, msg, args):
        """<string> [<length>]

        Returns the Soundex hash to a given length.  The length defaults to
        4, since that's the standard length for a soundex hash.  For unlimited
        length, use 0.
        """
        (s, length) = privmsgs.getArgs(args, optional=1)
        if length:
            try:
                length = int(length)
            except ValueError:
                irc.error('%r isn\'t a valid length.' % length)
                return
        else:
            length = 4
        irc.reply(utils.soundex(s, length))

    _eightballs = (
        'outlook not so good.',
        'my reply is no.',
        'don\'t count on it.',
        'you may rely on it.',
        'ask again later.',
        'most likely.',
        'cannot predict now.',
        'yes.',
        'yes, most definitely.',
        'better not tell you now.',
        'it is certain.',
        'very doubtful.',
        'it is decidedly so.',
        'concentrate and ask again.',
        'signs point to yes.',
        'my sources say no.',
        'without a doubt.',
        'reply hazy, try again.',
        'as I see it, yes.',
        )
    def eightball(self, irc, msg, args):
        """[<question>]

        Asks the magic eightball a question.
        """
        irc.reply(random.choice(self._eightballs))

    def roulette(self, irc, msg, args):
        """takes no arguments.

        Randomly picks a number from 1 to 6 and if it comes up 1, you get
        kicked.  Otherwise -- *click*
        """
        nick = msg.nick
        channel = msg.args[0]
        if not ircutils.isChannel(channel):
            irc.error('This message must be sent in a channel.')
        if random.randint(1, 6) == 1:
            if irc.nick not in irc.state.channels[channel].ops:
                irc.reply('*BANG* Hey, who put a blank in here?!',
                          prefixName=False)
            else:
                irc.queueMsg(ircmsgs.kick(channel, nick, 'BANG!'))
        else:
            irc.reply('*click*')


Class = Fun

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
