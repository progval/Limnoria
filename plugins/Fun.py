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

import plugins

import gc
import re
import sys
import md5
import sha
import string
import random
import urllib
import inspect
import mimetypes

import conf
import debug
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

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if msg.args[0] in self.outFilters:
                s = msg.args[1]
                methods = self.outFilters[msg.args[0]]
                for filtercommand in methods:
                    myIrc = MyFunProxy()
                    filtercommand(myIrc, msg, [s])
                    s = myIrc.s
                msg = ircmsgs.IrcMsg(msg=msg, args=(msg.args[0], s))
        return msg

    _filterCommands = ['jeffk', 'leet', 'rot13', 'hexlify', 'binary', 'lithp',
                       'scramble', 'morse', 'reverse', 'urlquote', 'md5','sha',
                       'colorize']
    def outfilter(self, irc, msg, args, channel):
        """[<channel>] [<command>]
        
        Sets the outFilter of this plugin to be <command>.  If no command is
        given, unsets the outFilter.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        command = privmsgs.getArgs(args, needed=0, optional=1)
        if command:
            command = callbacks.canonicalName(command)
            if command in self._filterCommands:
                method = getattr(self, command)
                self.outFilters.setdefault(channel, []).append(method)
                irc.reply(msg, conf.replySuccess)
            else:
                irc.error(msg, 'That\'s not a valid filter command.')
        else:
            self.outFilters[channel] = []
            irc.reply(msg, conf.replySuccess)
    outfilter = privmsgs.checkChannelCapability(outfilter, 'op')
    
    def hexip(self, irc, msg, args):
        """<ip>

        Returns the hexadecimal IP for that IP.
        """
        ip = privmsgs.getArgs(args)
        if not ircutils.isIP(ip):
            irc.error(msg, '%r is not a valid IP.' % ip)
            return
        quads = ip.split('.')
        ret = ""
        for quad in quads:
            i = int(quad)
            ret += '%02x' % i
        irc.reply(msg, ret.upper())
            
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
        available in the documentation of the Python codecs module:
        <http://www.python.org/doc/lib/node126.html>.
        """
        encoding, text = privmsgs.getArgs(args, needed=2)
        irc.reply(msg, text.encode(encoding))

    def decode(self, irc, msg, args):
        """<encoding> <text>

        Returns an un-encoded form of the given text; the valid encodings are
        available in the documentation of the Python codecs module:
        <http://www.python.org/doc/lib/node126.html>.
        """
        encoding, text = privmsgs.getArgs(args, needed=2)
        irc.reply(msg, text.decode(encoding).encode('utf-8'))

    def hexlify(self, irc, msg, args):
        """<text>

        Returns a hexstring from the given string; a hexstring is a string
        composed of the hexadecimal value of each character in the string
        """
        text = privmsgs.getArgs(args)
        irc.reply(msg, text.encode('hex_codec'))

    def unhexlify(self, irc, msg, args):
        """<hexstring>

        Returns the string corresponding to <hexstring>.  Obviously,
        <hexstring> must be a string of hexadecimal digits.
        """
        text = privmsgs.getArgs(args)
        try:
            irc.reply(msg, text.decode('hex_codec'))
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
                irc.reply(msg, utils.commaAndify([str(x) for x in L]))
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
        text = text.replace('SS', 'TH')
        text = text.replace('s', 'th')
        text = text.replace('z', 'th')
        text = text.replace('S', 'Th')
        text = text.replace('Z', 'Th')
        text = text.replace('x', 'kth')
        text = text.replace('X', 'KTH')
        text = text.replace('cce', 'kth')
        text = text.replace('CCE', 'KTH')
        text = text.replace('tion', 'thion')
        text = text.replace('TION', 'THION')
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

    def objects(self, irc, msg, args):
        """takes no arguments.

        Returns the number and types of Python objects in memory.
        """
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
            try:
                length = int(length)
            except ValueError:
                irc.error(msg, '%r isn\'t a valid length.' % length)
                return
        else:
            length = 4
        irc.reply(msg, utils.soundex(s, length))

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
        irc.reply(msg, random.choice(self._eightballs))

    _scrambleRe = re.compile(r'(?:\b|(?![a-zA-Z]))([a-zA-Z])([a-zA-Z]*)'\
                             r'([a-zA-Z])(?:\b|(?![a-zA-Z]))')
    def scramble(self, irc, msg, args):
        """<text>

        Replies with a string where each word is scrambled; i.e., each internal
        letter (that is, all letters but the first and last) are shuffled.
        """
        def _subber(m):
            L = list(m.group(2))
            random.shuffle(L)
            return '%s%s%s' % (m.group(1), ''.join(L), m.group(3))
        text = privmsgs.getArgs(args)
        s = self._scrambleRe.sub(_subber, text)
        irc.reply(msg, s)

    _code = {
        "A" : ".-",
        "B" : "-...",
        "C" : "-.-.",
        "D" : "-..",
        "E" : ".",
        "F" : "..-.",
        "G" : "--.",
        "H" : "....",
        "I" : "..",
        "J" : ".---",
        "K" : "-.-",
        "L" : ".-..",
        "M" : "--",
        "N" : "-.",
        "O" : "---",
        "P" : ".--.",
        "Q" : "--.-",
        "R" : ".-.",
        "S" : "...",
        "T" : "-",
        "U" : "..-",
        "V" : "...-",
        "W" : ".--",
        "X" : "-..-",
        "Y" : "-.--",
        "Z" : "--..",
        "0" : "-----",
        "1" : ".----",
        "2" : "..---",
        "3" : "...--",
        "4" : "....-",
        "5" : ".....",
        "6" : "-....",
        "7" : "--...",
        "8" : "---..",
        "9" : "----.",
    }

    _revcode = dict([(y, x) for (x, y) in _code.items()])

    _unmorsere = re.compile('([.-]+)')
    def unmorse(self, irc, msg, args):
        """<morse code text>

        Does the reverse of the morse/ditdaw command.
        """
        text = privmsgs.getArgs(args)
        text = text.replace('_', '-')
        def morseToLetter(m):
            s = m.group(1)
            return self._revcode.get(s, s)
        text = self._unmorsere.sub(morseToLetter, text)
        text = text.replace('  ', '\x00')
        text = text.replace(' ', '')
        text = text.replace('\x00', ' ')
        irc.reply(msg, text)

    def morse(self, irc, msg, args):
        """<text>

        Gives the more code equivalent of a given string.
        """
        text = privmsgs.getArgs(args)
        L = []
        for c in text.upper():
            if c in self._code:
                L.append(self._code[c])
            else:
                L.append(c)
        irc.reply(msg, ' '.join(L))

    def reverse(self, irc, msg, args):
        """<text>

        Reverses <text>.
        """
        text = privmsgs.getArgs(args)
        irc.reply(msg, text[::-1])

    def _color(self, c):
        if c == ' ':
            return c
        fg = random.randint(2, 15)
        return '\x03%s%s' % (fg, c)

    def colorize(self, irc, msg, args):
        """<text>

        Returns <text> with each character randomly colorized.
        """
        text = privmsgs.getArgs(args)
        L = [self._color(c) for c in text]
        irc.reply(msg, ''.join(L))

    def jeffk(self, irc, msg, args):
        """<text>

        Returns <text> as if JeffK had said it himself.
        """
        def randomlyPick(L):
            return random.choice(L)
        def quoteOrNothing(m):
            return randomlyPick(['"', '']).join(m.groups())
        def randomlyReplace(s, probability=0.5):
            def f(m):
                if random.random() < probability:
                    return m.expand(s)
                else:
                    return m.group(0)
            return f
        def randomExclaims(m):
            if random.random() < 0.85:
                return ('!' * random.randrange(1, 5)) + m.group(1)
            else:
                return '.' + m.group(1)
        def randomlyShuffle(m):
            L = list(m.groups())
            random.shuffle(L)
            return ''.join(L)
        def lessRandomlyShuffle(m):
            L = list(m.groups())
            if random.random() < .4:
                random.shuffle(L)
            return ''.join(L)
        def randomlyLaugh(text, probability=.3):
            if random.random() < probability:
                if random.random() < .5:
                    insult = random.choice([' fagot1', ' fagorts', ' jerks',
                                            'fagot' ' jerk', ' dumbshoes',
                                            ' dumbshoe'])
                else:
                    insult = ''
                laugh1 = random.choice(['ha', 'hah', 'lol', 'l0l', 'ahh'])
                laugh2 = random.choice(['ha', 'hah', 'lol', 'l0l', 'ahh'])
                laugh1 = laugh1 * random.randrange(1, 5)
                laugh2 = laugh2 * random.randrange(1, 5)
                exclaim = random.choice(['!', '~', '!~', '~!!~~',
                                         '!!~', '~~~!'])
                exclaim += random.choice(['!', '~', '!~', '~!!~~',
                                          '!!~', '~~~!'])
                if random.random() < 0.5:
                    exclaim += random.choice(['!', '~', '!~', '~!!~~',
                                              '!!~', '~~~!'])
                laugh = ''.join([' ', laugh1, laugh2, insult, exclaim])
                text += laugh
            return text
            
        text = privmsgs.getArgs(args)

        if random.random() < .03:
            irc.reply(msg, randomlyLaugh('NO YUO', probability=1))
            return

        alwaysInsertions = {
            r'er\b': 'ar',
            r'\bthe\b': 'teh',
            r'\byou\b': 'yuo',
            r'\bis\b': 'si',
            r'\blike\b': 'liek',
            r'[^e]ing\b': 'eing',
            }
        for (r, s) in alwaysInsertions.iteritems():
            text = re.sub(r, s, text)
            
        randomInsertions = {
            r'i': 'ui',
            r'le\b': 'al',
            r'i': 'io',
            r'l': 'll',
            r'to': 'too',
            r'that': 'taht',
            r'[^s]c([ei])': r'sci\1',
            r'ed\b': r'e',
            r'\band\b': 'adn',
            r'\bhere\b': 'hear',
            r'\bthey\'re': 'their',
            r'\bthere\b': 'they\'re',
            r'\btheir\b': 'there',
            r'[^e]y': 'ey',
            }
        for (r, s) in randomInsertions.iteritems():
            text = re.sub(r, randomlyReplace(s), text)
            
        text = re.sub(r'(\w)\'(\w)', quoteOrNothing, text)
        text = re.sub(r'\.(\s+|$)', randomExclaims, text)
        text = re.sub(r'([aeiou])([aeiou])', randomlyShuffle, text)
        text = re.sub(r'([bcdfghkjlmnpqrstvwxyz])([bcdfghkjlmnpqrstvwxyz])',
                      lessRandomlyShuffle, text)

        text = randomlyLaugh(text)

        if random.random() < .4:
            text = text.upper()

        irc.reply(msg, text)


Class = Fun


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
