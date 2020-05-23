# -*- encoding: utf-8 -*-
###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

from __future__ import unicode_literals

import re
import sys
import codecs
import string
import random

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Filter')

class MyFilterProxy(object):
    def reply(self, s):
        self.s = s

class Filter(callbacks.Plugin):
    """This plugin offers several commands which transform text in some way.
    It also provides the capability of using such commands to 'filter' the
    output of the bot -- for instance, you could make everything the bot says
    be in leetspeak, or Morse code, or any number of other kinds of filters.
    Not very useful, but definitely quite fun :)"""
    def __init__(self, irc):
        self.__parent = super(Filter, self)
        self.__parent.__init__(irc)
        self.outFilters = ircutils.IrcDict()

    def outFilter(self, irc, msg):
        if msg.command in ('PRIVMSG', 'NOTICE'):
            if msg.channel in self.outFilters:
                if ircmsgs.isAction(msg):
                    s = ircmsgs.unAction(msg)
                else:
                    s = msg.args[1]
                methods = self.outFilters[msg.channel]
                for filtercommand in methods:
                    myIrc = MyFilterProxy()
                    filtercommand(myIrc, msg, [s])
                    s = myIrc.s
                if ircmsgs.isAction(msg):
                    msg = ircmsgs.action(msg.args[0], s, msg=msg)
                else:
                    msg = ircmsgs.IrcMsg(msg=msg, args=(msg.args[0], s))
        return msg

    _filterCommands = ['jeffk', 'leet', 'rot13', 'hexlify', 'binary',
                       'scramble', 'morse', 'reverse', 'colorize', 'squish',
                       'supa1337', 'stripcolor', 'aol', 'rainbow', 'spellit',
                       'hebrew', 'undup', 'uwu', 'gnu', 'shrink', 'uniud', 'capwords',
                       'caps', 'vowelrot']
    @internationalizeDocstring
    def outfilter(self, irc, msg, args, channel, command):
        """[<channel>] [<command>]

        Sets the outFilter of this plugin to be <command>.  If no command is
        given, unsets the outFilter.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        if command:
            if not self.isDisabled(command) and \
               command in self._filterCommands:
                method = getattr(self, command)
                self.outFilters.setdefault(channel, []).append(method)
                irc.replySuccess()
            else:
                irc.error(_('That\'s not a valid filter command.'))
        else:
            self.outFilters[channel] = []
            irc.replySuccess()
    outfilter = wrap(outfilter,
                     [('checkChannelCapability', 'op'),
                      additional('commandName')])

    _hebrew_remover = utils.str.MultipleRemover('aeiou')
    @internationalizeDocstring
    def hebrew(self, irc, msg, args, text):
        """<text>

        Removes all the vowels from <text>.  (If you're curious why this is
        named 'hebrew' it's because I (jemfinch) thought of it in Hebrew class,
        and printed Hebrew often elides the vowels.)
        """
        irc.reply(self._hebrew_remover(text))
    hebrew = wrap(hebrew, ['text'])

    def _squish(self, text):
        return text.replace(' ', '')

    @internationalizeDocstring
    def squish(self, irc, msg, args, text):
        """<text>

        Removes all the spaces from <text>.
        """
        irc.reply(self._squish(text))
    squish = wrap(squish, ['text'])

    @internationalizeDocstring
    def undup(self, irc, msg, args, text):
        """<text>

        Returns <text>, with all consecutive duplicated letters removed.
        """
        L = [text[0]]
        for c in text:
            if c != L[-1]:
                L.append(c)
        irc.reply(''.join(L))
    undup = wrap(undup, ['text'])

    @internationalizeDocstring
    def binary(self, irc, msg, args, text):
        """<text>

        Returns the binary representation of <text>.
        """
        L = []
        if minisix.PY3:
            if isinstance(text, str):
                bytes_ = text.encode()
            else:
                bytes_ = text
        else:
            if isinstance(text, unicode):
                text = text.encode()
            bytes_ = map(ord, text)
        for i in bytes_:
            LL = []
            assert i<=256
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
    binary = wrap(binary, ['text'])

    def unbinary(self, irc, msg, args, text):
        """<text>

        Returns the character representation of binary <text>.
        Assumes ASCII, 8 digits per character.
        """
        text = self._squish(text)  # Strip spaces.
        try:
            L = [chr(int(text[i:(i+8)], 2)) for i in range(0, len(text), 8)]
            irc.reply(''.join(L))
        except ValueError:
            irc.errorInvalid('binary string', text)
    unbinary = wrap(unbinary, ['text'])

    _hex_encoder = staticmethod(codecs.getencoder('hex_codec'))
    def hexlify(self, irc, msg, args, text):
        """<text>

        Returns a hexstring from the given string; a hexstring is a string
        composed of the hexadecimal value of each character in the string
        """
        irc.reply(self._hex_encoder(text.encode('utf8'))[0].decode('utf8'))
    hexlify = wrap(hexlify, ['text'])

    _hex_decoder = staticmethod(codecs.getdecoder('hex_codec'))
    @internationalizeDocstring
    def unhexlify(self, irc, msg, args, text):
        """<hexstring>

        Returns the string corresponding to <hexstring>.  Obviously,
        <hexstring> must be a string of hexadecimal digits.
        """
        try:
            irc.reply(self._hex_decoder(text.encode('utf8'))[0]
                    .decode('utf8', 'replace'))
        except TypeError:
            irc.error(_('Invalid input.'))
    unhexlify = wrap(unhexlify, ['text'])

    _rot13_encoder = codecs.getencoder('rot-13')
    @internationalizeDocstring
    def rot13(self, irc, msg, args, text):
        """<text>

        Rotates <text> 13 characters to the right in the alphabet.  Rot13 is
        commonly used for text that simply needs to be hidden from inadvertent
        reading by roaming eyes, since it's easily reversible.
        """
        if minisix.PY2:
            text = text.decode('utf8')
        irc.reply(self._rot13_encoder(text)[0])
    rot13 = wrap(rot13, ['text'])

    _leettrans = utils.str.MultipleReplacer(dict(list(zip('oOaAeElBTiIts',
                                                     '004433187!1+5'))))
    _leetres = [(re.compile(r'\b(?:(?:[yY][o0O][oO0uU])|u)\b'), 'j00'),
                (re.compile(r'fear'), 'ph33r'),
                (re.compile(r'[aA][tT][eE]'), '8'),
                (re.compile(r'[aA][tT]'), '@'),
                (re.compile(r'[sS]\b'), 'z'),
                (re.compile(r'x'), '><'),]
    @internationalizeDocstring
    def leet(self, irc, msg, args, text):
        """<text>

        Returns the l33tspeak version of <text>
        """
        for (r, sub) in self._leetres:
            text = re.sub(r, sub, text)
        text = self._leettrans(text)
        irc.reply(text)
    leet = wrap(leet, ['text'])

    _supaleetreplacers = [('xX', '><'), ('kK', '|<'), ('rR', '|2'),
                          ('hH', '|-|'), ('L', '|_'), ('uU', '|_|'),
                          ('O', '()'), ('nN', '|\\|'), ('mM', '/\\/\\'),
                          ('G', '6'), ('Ss', '$'), ('i', ';'), ('aA', '/-\\'),
                          ('eE', '3'), ('t', '+'), ('T', '7'), ('l', '1'),
                          ('D', '|)'), ('B', '|3'), ('I', ']['), ('Vv', '\\/'),
                          ('wW', '\\/\\/'), ('d', 'c|'), ('b', '|>'),
                          ('c', '<'), ('h', '|n'),]
    @internationalizeDocstring
    def supa1337(self, irc, msg, args, text):
        """<text>

        Replies with an especially k-rad translation of <text>.
        """
        for (r, sub) in self._leetres:
            text = re.sub(r, sub, text)
        for (letters, replacement) in self._supaleetreplacers:
            for letter in letters:
                text = text.replace(letter, replacement)
        irc.reply(text)
    supa1337 = wrap(supa1337, ['text'])

    _scrambleRe = re.compile(r'(?:\b|(?![a-zA-Z]))([a-zA-Z])([a-zA-Z]*)'
                             r'([a-zA-Z])(?:\b|(?![a-zA-Z]))')
    @internationalizeDocstring
    def scramble(self, irc, msg, args, text):
        """<text>

        Replies with a string where each word is scrambled; i.e., each internal
        letter (that is, all letters but the first and last) are shuffled.
        """
        def _subber(m):
            L = list(m.group(2))
            random.shuffle(L)
            return '%s%s%s' % (m.group(1), ''.join(L), m.group(3))
        s = self._scrambleRe.sub(_subber, text)
        irc.reply(s)
    scramble = wrap(scramble, ['text'])

    _morseCode = {
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
    _revMorseCode = dict([(y, x) for (x, y) in _morseCode.items()])
    _unmorsere = re.compile('([.-]+)')
    @internationalizeDocstring
    def unmorse(self, irc, msg, args, text):
        """<Morse code text>

        Does the reverse of the morse command.
        """
        text = text.replace('_', '-')
        def morseToLetter(m):
            s = m.group(1)
            return self._revMorseCode.get(s, s)
        text = self._unmorsere.sub(morseToLetter, text)
        text = text.replace('  ', '\x00')
        text = text.replace(' ', '')
        text = text.replace('\x00', ' ')
        irc.reply(text)
    unmorse = wrap(unmorse, ['text'])

    @internationalizeDocstring
    def morse(self, irc, msg, args, text):
        """<text>

        Gives the Morse code equivalent of a given string.
        """
        L = []
        for c in text.upper():
            L.append(self._morseCode.get(c, c))
        irc.reply(' '.join(L))
    morse = wrap(morse, ['text'])

    @internationalizeDocstring
    def reverse(self, irc, msg, args, text):
        """<text>

        Reverses <text>.
        """
        irc.reply(text[::-1])
    reverse = wrap(reverse, ['text'])

    @internationalizeDocstring
    def _color(self, c, fg=None):
        if c == ' ':
            return c
        if fg is None:
            fg = random.randint(2, 15)
        fg = str(fg).zfill(2)
        return '\x03%s%s' % (fg, c)

    @internationalizeDocstring
    def colorize(self, irc, msg, args, text):
        """<text>

        Returns <text> with each character randomly colorized.
        """
        if minisix.PY2:
            text = text.decode('utf-8')
        text = ircutils.stripColor(text)
        L = [self._color(c) for c in text]
        if minisix.PY2:
            L = [c.encode('utf-8') for c in L]
        irc.reply('%s%s' % (''.join(L), '\x03'))
    colorize = wrap(colorize, ['text'])

    @internationalizeDocstring
    def rainbow(self, irc, msg, args, text):
        """<text>

        Returns <text> colorized like a rainbow.
        """
        if minisix.PY2:
            text = text.decode('utf-8')
        text = ircutils.stripColor(text)
        colors = utils.iter.cycle(['05', '04', '07', '08', '09', '03', '11',
                                   '10', '12', '02', '06', '13'])
        L = [self._color(c, fg=next(colors)) for c in text]
        if minisix.PY2:
            L = [c.encode('utf-8') for c in L]
        irc.reply(''.join(L) + '\x03')
    rainbow = wrap(rainbow, ['text'])

    @internationalizeDocstring
    def stripcolor(self, irc, msg, args, text):
        """<text>

        Returns <text> stripped of all color codes.
        """
        irc.reply(ircutils.stripColor(text))
    stripcolor = wrap(stripcolor, ['text'])

    @internationalizeDocstring
    def aol(self, irc, msg, args, text):
        """<text>

        Returns <text> as if an AOL user had said it.
        """
        text = text.replace(' you ', ' u ')
        text = text.replace(' are ', ' r ')
        text = text.replace(' love ', ' <3 ')
        text = text.replace(' luv ', ' <3 ')
        text = text.replace(' too ', ' 2 ')
        text = text.replace(' to ', ' 2 ')
        text = text.replace(' two ', ' 2 ')
        text = text.replace('fore', '4')
        text = text.replace(' for ', ' 4 ')
        text = text.replace('be', 'b')
        text = text.replace('four', ' 4 ')
        text = text.replace(' their ', ' there ')
        text = text.replace(', ', ' ')
        text = text.replace(',', ' ')
        text = text.replace("'", '')
        text = text.replace('one', '1')
        smiley = utils.iter.choice(['<3', ':)', ':-)', ':D', ':-D'])
        text += smiley*3
        irc.reply(text)
    aol = wrap(aol, ['text'])

    @internationalizeDocstring
    def jeffk(self, irc, msg, args, text):
        """<text>

        Returns <text> as if JeffK had said it himself.
        """
        def randomlyPick(L):
            return utils.iter.choice(L)
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
                    insult = utils.iter.choice([' fagot1', ' fagorts',
                                                ' jerks', 'fagot' ' jerk',
                                                'dumbshoes', ' dumbshoe'])
                else:
                    insult = ''
                laugh1 = utils.iter.choice(['ha', 'hah', 'lol', 'l0l', 'ahh'])
                laugh2 = utils.iter.choice(['ha', 'hah', 'lol', 'l0l', 'ahh'])
                laugh1 = laugh1 * random.randrange(1, 5)
                laugh2 = laugh2 * random.randrange(1, 5)
                exclaim = utils.iter.choice(['!', '~', '!~', '~!!~~',
                                             '!!~', '~~~!'])
                exclaim += utils.iter.choice(['!', '~', '!~', '~!!~~',
                                              '!!~', '~~~!'])
                if random.random() < 0.5:
                    exclaim += utils.iter.choice(['!', '~', '!~', '~!!~~',
                                                  '!!~', '~~~!'])
                laugh = ''.join([' ', laugh1, laugh2, insult, exclaim])
                text += laugh
            return text
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
        for (r, s) in alwaysInsertions.items():
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
        for (r, s) in randomInsertions.items():
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
    jeffk = wrap(jeffk, ['text'])

    # Keeping these separate so people can just replace the alphabets for
    # whatever their language of choice
    _spellLetters = {
        'a': _('ay'), 'b': _('bee'), 'c': _('see'), 'd': _('dee'),
        'e': _('ee'), 'f': _('eff'), 'g': _('gee'), 'h': _('aych'),
        'i': _('eye'), 'j': _('jay'), 'k': _('kay'), 'l': _('ell'),
        'm': _('em'), 'n': _('en'), 'o': _('oh'), 'p': _('pee'), 'q': _('cue'),
        'r': _('arr'), 's': _('ess'), 't': _('tee'), 'u': _('you'),
        'v': _('vee'), 'w': _('double-you'), 'x': _('ecks'), 'y': _('why'),
        'z': _('zee')
    }
    for (k, v) in list(_spellLetters.items()):
        _spellLetters[k.upper()] = v
    _spellPunctuation = {
        '!': _('exclamation point'),
        '"': _('quote'),
        '#': _('pound'),
        '$': _('dollar sign'),
        '%': _('percent'),
        '&': _('ampersand'),
        '\'': _('single quote'),
        '(': _('left paren'),
        ')': _('right paren'),
        '*': _('asterisk'),
        '+': _('plus'),
        ',': _('comma'),
        '-': _('minus'),
        '.': _('period'),
        '/': _('slash'),
        ':': _('colon'),
        ';': _('semicolon'),
        '<': _('less than'),
        '=': _('equals'),
        '>': _('greater than'),
        '?': _('question mark'),
        '@': _('at'),
        '[': _('left bracket'),
        '\\': _('backslash'),
        ']': _('right bracket'),
        '^': _('caret'),
        '_': _('underscore'),
        '`': _('backtick'),
        '{': _('left brace'),
        '|': _('pipe'),
        '}': _('right brace'),
        '~': _('tilde')
    }
    _spellNumbers = {
        '0': _('zero'), '1': _('one'), '2': _('two'), '3': _('three'), 
        '4': _('four'), '5': _('five'), '6': _('six'), '7': _('seven'),
        '8': _('eight'), '9': _('nine')
    }
    @internationalizeDocstring
    def spellit(self, irc, msg, args, text):
        """<text>

        Returns <text>, phonetically spelled out.
        """
        d = {}
        if self.registryValue('spellit.replaceLetters'):
            d.update(self._spellLetters)
        if self.registryValue('spellit.replaceNumbers'):
            d.update(self._spellNumbers)
        if self.registryValue('spellit.replacePunctuation'):
            d.update(self._spellPunctuation)
# A bug in unicode on OSX prevents me from testing this.
##         dd = {}
##         for (c, v) in d.items():
##             dd[ord(c)] = unicode(v + ' ')
##         irc.reply(unicode(text).translate(dd))
        out = minisix.io.StringIO()
        write = out.write
        for c in text:
            try:
                c = d[c]
                write(' ')
            except KeyError:
                pass
            write(c)
        irc.reply(out.getvalue().strip())
    spellit = wrap(spellit, ['text'])

    @internationalizeDocstring
    def gnu(self, irc, msg, args, text):
        """<text>

        Returns <text> as GNU/RMS would say it.
        """
        irc.reply(' '.join(['GNU/' + s for s in text.split()]))
    gnu = wrap(gnu, ['text'])

    @internationalizeDocstring
    def shrink(self, irc, msg, args, text):
        """<text>

        Returns <text> with each word longer than
        supybot.plugins.Filter.shrink.minimum being shrunken (i.e., like
        "internationalization" becomes "i18n").
        """
        L = []
        minimum = self.registryValue('shrink.minimum',
                                     msg.channel, irc.network)
        r = re.compile(r'[A-Za-z]{%s,}' % minimum)
        def shrink(m):
            s = m.group(0)
            return ''.join((s[0], str(len(s)-2), s[-1]))
        text = r.sub(shrink, text)
        irc.reply(text)
    shrink = wrap(shrink, ['text'])


    # TODO: 2,4,;
    # XXX suckiest: B,K,P,Q,T
    # alternatives: 3: U+2107
    _uniudMap = {
    ' ': ' ',      '0': '0',      '@': '@',
    '!': '\u00a1', '1': '1',      'A': '\u2200',
    '"': '\u201e', '2': '\u2681', 'B': 'q',
    '#': '#',      '3': '\u0190', 'C': '\u0186',
    '$': '$',      '4': '\u2683', 'D': '\u15e1',
    '%': '%',      '5': '\u1515', 'E': '\u018e',
    '&': '\u214b', '6': '9',      'F': '\u2132',
    "'": '\u0375', '7': 'L',      'G': '\u2141',
    '(': ')',      '8': '8',      'H': 'H',
    ')': '(',      '9': '6',      'I': 'I',
    '*': '*',      ':': ':',      'J': '\u148b',
    '+': '+',      ';': ';',      'K': '\u029e',
    ',': '\u2018', '<': '>',      'L': '\u2142',
    '-': '-',      '=': '=',      'M': '\u019c',
    '.': '\u02d9', '>': '<',      'N': 'N',
    '/': '/',      '?': '\u00bf', 'O': 'O',

    'P': 'd',      '`': '\u02ce', 'p': 'd',
    'Q': 'b',      'a': '\u0250', 'q': 'b',
    'R': '\u1d1a', 'b': 'q',      'r': '\u0279',
    'S': 'S',      'c': '\u0254', 's': 's',
    'T': '\u22a5', 'd': 'p',      't': '\u0287',
    'U': '\u144e', 'e': '\u01dd', '': 'n',
    'V': '\u039b', 'f': '\u214e', 'v': '\u028c',
    'W': 'M',      'g': '\u0253', 'w': '\u028d',
    'X': 'X',      'h': '\u0265', 'x': 'x',
    'Y': '\u2144', 'i': '\u1d09', 'y': '\u028e',
    'Z': 'Z',      'j': '\u027f', 'z': 'z',
    '[': ']',      'k': '\u029e', '{': '}',
    '\\': '\\',    'l': '\u05df', '|': '|',
    ']': '[',      'm': '\u026f', '}': '{',
    '^': '\u2335', 'n': '',      '~': '~',
    '_': '\u203e', 'o': 'o',
    }

    @internationalizeDocstring
    def uniud(self, irc, msg, args, text):
        """<text>

        Returns <text> rotated 180 degrees. Only really works for ASCII
        printable characters.
        """
        turned = []
        tlen = 0
        for c in text:
            if c in self._uniudMap:
                tmp = self._uniudMap[c]
                if not len(tmp):
                    tmp = '\ufffd'
                turned.append(tmp)
                tlen += 1
            elif c == '\t':
                tablen = 8 - tlen % 8
                turned.append(' ' * tablen)
                tlen += tablen
            elif ord(c) >= 32:
                turned.append(c)
                tlen += 1
        s = '%s \x02 \x02' % ''.join(reversed(turned))
        irc.reply(s)
    uniud = wrap(uniud, ['text'])

    def capwords(self, irc, msg, args, text):
        """<text>

        Capitalises the first letter of each word.
        """
        text = string.capwords(text)
        irc.reply(text)
    capwords = wrap(capwords, ['text'])

    def caps(self, irc, msg, args, text):
        """<text>

        EVERYONE LOVES CAPS LOCK.
        """
        irc.reply(text.upper())
    caps = wrap(caps, ['text'])

    _vowelrottrans = utils.str.MultipleReplacer(dict(list(zip('aeiouAEIOU', 'eiouaEIOUA'))))
    def vowelrot(self, irc, msg, args, text):
        """<text>

        Returns <text> with vowels rotated
        """
        text = self._vowelrottrans(text)
        irc.reply(text)
    vowelrot = wrap(vowelrot, ['text'])


    _uwutrans = utils.str.MultipleReplacer(dict(list(zip('lrLR', 'wwWW'))))
    def uwu(self, irc, msg, args, text):
        """<text>

        Returns <text> in uwu-speak.
        """
        text = self._uwutrans(text)
        text += random.choice([''] * 10 + [' uwu', ' UwU', ' owo', ' OwO'])
        irc.reply(text)
    uwu = wrap(uwu, ['text'])

Filter = internationalizeDocstring(Filter)

Class = Filter


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
