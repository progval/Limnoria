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
Provides numerous filters, and a command (outfilter) to set them as filters on
the output of the bot.
"""

__revision__ = "$Id$"

import plugins

import re
import string
import random

import conf
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks

class MyFilterProxy(object):
    def reply(self, s):
        self.s = s
        
class Filter(callbacks.Privmsg):
    """This plugin offers several commands which transform text in some way.
    It also provides the capability of using such commands to 'filter' the
    output of the bot -- for instance, you could make everything the bot says
    be in leetspeak, or morse code, or any number of other kinds of filters.
    Not very useful, but definitely quite fun :)"""
    def __init__(self):
        self.outFilters = ircutils.IrcDict()
        callbacks.Privmsg.__init__(self)

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if msg.args[0] in self.outFilters:
                if ircmsgs.isAction(msg):
                    s = ircmsgs.unAction(msg)
                else:
                    s = msg.args[1]
                methods = self.outFilters[msg.args[0]]
                for filtercommand in methods:
                    myIrc = MyFilterProxy()
                    filtercommand(myIrc, msg, [s])
                    s = myIrc.s
                if ircmsgs.isAction(msg):
                    msg = ircmsgs.action(msg.args[0], s)
                else:
                    msg = ircmsgs.IrcMsg(msg=msg, args=(msg.args[0], s))
        return msg

    _filterCommands = ['jeffk', 'leet', 'rot13', 'hexlify', 'binary', 'lithp',
                       'scramble', 'morse', 'reverse', 'colorize', 'squish',
                       'supa1337', 'colorstrip', 'aol']
    def outfilter(self, irc, msg, args, channel):
        """[<channel>] [<command>]
        
        Sets the outFilter of this plugin to be <command>.  If no command is
        given, unsets the outFilter.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        command = privmsgs.getArgs(args, required=0, optional=1)
        if command:
            command = callbacks.canonicalName(command)
            if command in self._filterCommands:
                method = getattr(self, command)
                self.outFilters.setdefault(channel, []).append(method)
                irc.replySuccess()
            else:
                irc.error('That\'s not a valid filter command.')
        else:
            self.outFilters[channel] = []
            irc.replySuccess()
    outfilter = privmsgs.checkChannelCapability(outfilter, 'op')
    
    def squish(self, irc, msg, args):
        """<text>

        Removes all the spaces from <text>.
        """
        text = privmsgs.getArgs(args)
        text = ''.join(text.split())
        irc.reply(text)

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
        irc.reply(''.join(L))

    def hexlify(self, irc, msg, args):
        """<text>

        Returns a hexstring from the given string; a hexstring is a string
        composed of the hexadecimal value of each character in the string
        """
        text = privmsgs.getArgs(args)
        irc.reply(text.encode('hex_codec'))

    def unhexlify(self, irc, msg, args):
        """<hexstring>

        Returns the string corresponding to <hexstring>.  Obviously,
        <hexstring> must be a string of hexadecimal digits.
        """
        text = privmsgs.getArgs(args)
        try:
            irc.reply(text.decode('hex_codec'))
        except TypeError:
            irc.error('Invalid input.')

    def rot13(self, irc, msg, args):
        """<text>

        Rotates <text> 13 characters to the right in the alphabet.  Rot13 is
        commonly used for text that simply needs to be hidden from inadvertent
        reading by roaming eyes, since it's easily reversible.
        """
        text = privmsgs.getArgs(args)
        irc.reply(text.encode('rot13'))

    def lithp(self, irc, msg, args):
        """<text>

        Returns the lisping version of <text>
        """
        text = privmsgs.getArgs(args)
        text = text.replace('sh', 'th')
        text = text.replace('SH', 'TH')
        text = text.replace('Sh', 'Th')
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
        irc.reply(text)

    _leettrans = string.maketrans('oOaAeElBTiIts', '004433187!1+5')
    _leetres = [(re.compile(r'\b(?:(?:[yY][o0O][oO0uU])|u)\b'), 'j00'),
                (re.compile(r'fear'), 'ph33r'),
                (re.compile(r'[aA][tT][eE]'), '8'),
                (re.compile(r'[aA][tT]'), '@'),
                (re.compile(r'[sS]\b'), 'z'),
                (re.compile(r'x'), '><'),]
    def leet(self, irc, msg, args):
        """<text>

        Returns the l33tspeak version of <text>
        """
        s = privmsgs.getArgs(args)
        for (r, sub) in self._leetres:
            s = re.sub(r, sub, s)
        s = s.translate(self._leettrans)
        irc.reply(s)

    _supaleetreplacers = [('xX', '><'), ('kK', '|<'), ('rR', '|2'),
                          ('hH', '|-|'), ('L', '|_'), ('uU', '|_|'),
                          ('O', '()'), ('nN', '|\\|'), ('mM', '/\\/\\'),
                          ('G', '6'), ('Ss', '$'), ('i', ';'), ('aA', '/-\\'),
                          ('eE', '3'), ('t', '+'), ('T', '7'), ('l', '1'),
                          ('D', '|)'), ('B', '|3'), ('I', ']['), ('Vv', '\\/'),
                          ('wW', '\\/\\/'), ('d', 'c|'), ('b', '|>'),
                          ('c', '<'), ('h', '|n'),] 
    def supa1337(self, irc, msg, args):
        """<text>

        Replies with an especially k-rad translation of <text>.
        """
        s = privmsgs.getArgs(args)
        for (r, sub) in self._leetres:
            s = re.sub(r, sub, s)
        for (letters, replacement) in self._supaleetreplacers:
            for letter in letters:
                s = s.replace(letter, replacement)
        irc.reply(s)

    _scrambleRe = re.compile(r'(?:\b|(?![a-zA-Z]))([a-zA-Z])([a-zA-Z]*)'
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
        irc.reply(s)

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
        "." : ".-.-.-",
        "," : "--..--",
        ":" : "---...",
        "?" : "..--..",
        "'" : ".----.",
        "-" : "-....-",
        "/" : "-..-.",
        '"' : ".-..-.",
        "@" : ".--.-.",
        "=" : "-...-"
    }
    _revcode = dict([(y, x) for (x, y) in _code.items()])
    _unmorsere = re.compile('([.-]+)')
    def unmorse(self, irc, msg, args):
        """<morse code text>

        Does the reverse of the morse command.
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
        irc.reply(text)

    def morse(self, irc, msg, args):
        """<text>

        Gives the morse code equivalent of a given string.
        """
        text = privmsgs.getArgs(args)
        L = []
        for c in text.upper():
            if c in self._code:
                L.append(self._code[c])
            else:
                L.append(c)
        irc.reply(' '.join(L))

    def reverse(self, irc, msg, args):
        """<text>

        Reverses <text>.
        """
        text = privmsgs.getArgs(args)
        irc.reply(text[::-1])

    def _color(self, c):
        if c == ' ':
            return c
        fg = str(random.randint(2, 15)).zfill(2)
        return '\x03%s%s' % (fg, c)

    def colorize(self, irc, msg, args):
        """<text>

        Returns <text> with each character randomly colorized.
        """
        text = privmsgs.getArgs(args)
        L = [self._color(c) for c in text]
        irc.reply('%s%s' % (''.join(L), '\x03'))

    def stripcolor(self, irc, msg, args):
        """<text>

        Returns <text> stripped of all color codes.
        """
        text = privmsgs.getArgs(args)
        irc.reply(ircutils.stripColor(text))

    def aol(self, irc, msg, args):
        """<text>

        Returns <text> as if an AOLuser had said it.
        """
        text = privmsg.getArgs(args)
        text = text.replace(' you ', ' u ')
        text = text.replace(' are ', ' r ')
        text = text.replace(' love ', ' <3 ')
        text = text.replace(' luv ', ' <3 ')
        text = text.replace(' too ', ' 2 ')
        text = text.replace(' to ', ' 2 ')
        text = text.replace(' two ', ' 2 ')
        text = text.replace(' for ', ' 4 ')
        text = text.replace(' be ', ' b ')
        text = text.replace(' four ', ' 4 ')
        text = text.replace(', ', ' ')
        text = text.replace(',', ' ')
        text = text.replace("'", '')
        text = text.replace(' their ', ' there ')
        smiley = random.choice(['<3', ':)', ':-)', ':D', ':-D'])
        text += smiley*3
        
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
            irc.reply(randomlyLaugh('NO YUO', probability=1))
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
        irc.reply(text)


Class = Filter


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
