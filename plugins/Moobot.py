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

###
# Note the exception above the declaration of _code.
###
"""
Provides several commands that shamelessly imitate Moobot, if only to show
developers coming from Moobot how to code to Supybot.
"""

from baseplugin import *

import re
import base64

import ircmsgs
import ircutils
import privmsgs
import callbacks

class Moobot(callbacks.Privmsg):
    def cool(self, irc, msg, args):
        """<something>

        Says something's cool.  Yeah. :cool: Supybot :cool: :)
        """
        something = privmsgs.getArgs(args)
        irc.reply(msg, ':cool: %s :cool:' % something)

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

    ditdaw = morse
    dawdit = unmorse

    def hi(self, irc, msg, args):
        "takes no arguments"
        irc.reply(msg, 'howdy, %s!' % msg.nick)

    def reverse(self, irc, msg, args):
        "<text>"
        text = privmsgs.getArgs(args)
        irc.reply(msg, text[::-1])

    def mime(self, irc, msg, args):
        """<text>

        Encodes text in base64.  Here for compatibility with Moobot; this and
        other encodings are available in the FunCommands module.
        """
        text = privmsgs.getArgs(args)
        s = base64.encodestring(text).strip()
        irc.reply(msg, s)

    def unmime(self, irc, msg, args):
        """<text>

        Decodes base64 encoded text.  Here for compatibility with Moobot; this
        and other encodings are available in the FunCommands module.
        """
        text = privmsgs.getArgs(args)
        s = base64.decodestring(text)
        irc.reply(msg, s)

    _stack = []
    def stack(self, irc, msg, args):
        """<'push'|'pop'|'size'|'xray'> <text>

        Maintains a stack of various strings; push pushes onto the stack,
        pop pops off it, size gives its current size, and xray takes an
        index into the stack and gives that element.
        """
        (command, value) = privmsgs.getArgs(args, optional=1)
        if command == 'pop':
            if self._stack:
                x = self._stack.pop()
                irc.reply(msg, x)
            else:
                irc.error(msg, 'Stack is empty.')
        elif command == 'push':
            self._stack.append(value)
            irc.reply(msg, '"%s" pushed.' % value)
        elif command == 'size':
            irc.reply(msg, 'Stack size is %s.' % len(self._stack))
        elif command == 'xray':
            i = int(value)
            try:
                irc.reply(msg, self._stack[-i])
            except IndexError:
                irc.error(msg, 'Invalid position %s' % i)
        else:
            irc.error(msg, 'I don\'t recognize that stack command.')

    def give(self, irc, msg, args):
        """<someone> <something>"""
        (someone, something) = privmsgs.getArgs(args, needed=2)
        if someone == 'me':
            someone = msg.nick
        elif someone in ('yourself', 'you', irc.nick):
            someone = 'himself'
        response = 'gives %s %s' % (someone, something)
        irc.queueMsg(ircmsgs.action(ircutils.replyTo(msg), response))


Class = Moobot
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
