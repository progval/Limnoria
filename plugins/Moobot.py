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
"""Module to replicate some of moobot's functionality."""

from baseplugin import *

import base64

import ircutils
import privmsgs
import callbacks

class Moobot(callbacks.Privmsg):
    def __init__(self):
        super(self.__class__, self).__init__()
        #callbacks.Privmsg.__init__(self)
        if not self._revcode:
            for (k, v) in self._code.iteritems():
                self._revcode[v.strip()] = k

    def cool(self, irc, msg, args):
        "<something>"
        something = privmsgs.getArgs(args)
        irc.reply(msg, ':cool: %s :cool:' % something)

    # Stolen shamelessless from moobot, so I suppose this data structure is
    # GPLed.  Don't worry, it doesn't infect the rest of the code because it's
    # not essential to the operation of the bot.
    _code = {
        "A" : ".- ",
        "B" : "-... ",
        "C" : "-.-. ",
        "D" : "-.. ",
        "E" : ". ",
        "F" : "..-. ",
        "G" : "--. ",
        "H" : ".... ",
        "I" : ".. ",
        "J" : ".--- ",
        "K" : "-.- ",
        "L" : ".-.. ",
        "M" : "-- ",
        "N" : "-. ",
        "O" : "--- ",
        "P" : ".--. ",
        "Q" : "--.- ",
        "R" : ".-. ",
        "S" : "... ",
        "T" : "- ",
        "U" : "..- ",
        "V" : "...- ",
        "W" : ".-- ",
        "X" : "-..- ",
        "Y" : "-.-- ",
        "Z" : "--.. ",
        "0" : "----- ",
        "1" : ".---- ",
        "2" : "..--- ",
        "3" : "...-- ",
        "4" : "....- ",
        "5" : "..... ",
        "6" : "-.... ",
        "7" : "--... ",
        "8" : "---.. ",
        "9" : "----. ",
        " " : " "
    }

    _revcode = {}

    def unmorse(self, irc, msg, args):
        "<morse code text>"
        text = privmsgs.getArgs(args)
        L = []
        for code in text.split():
            try:
                L.append(self._revcode[code])
            except KeyError:
                L.append(code)
        irc.reply(msg, ''.join(L))

    def morse(self, irc, msg, args):
        "<text>"
        text = privmsgs.getArgs(args)
        L = []
        for c in text.upper():
            if c in self._code:
                L.append(self._code[c])
            else:
                L.append(c)
        irc.reply(msg, ' '.join(L))

    ditdaw = morse

    def hi(self, irc, msg, args):
        "takes no arguments"
        irc.reply(msg, 'howdy, %s!' % msg.nick)

    def reverse(self, irc, msg, args):
        "<text>"
        text = privmsgs.getArgs(args)
        L = list(text)
        L.reverse()
        irc.reply(msg, ''.join(L))

    def mime(self, irc, msg, args):
        "<text>"
        text = privmsgs.getArgs(args)
        s = base64.encodestring(text).strip()
        if ircutils.validArgument(s):
            irc.reply(msg, s)
        else:
            irc.error(msg, 'Base64 requires a newline in that string. '\
                       'Try a smaller string.')

    def unmime(self, irc, msg, args):
        "<text>"
        text = privmsgs.getArgs(args)
        s = base64.decodestring(text)
        if ircutils.validArgument(s):
            irc.reply(msg, s)
        else:
            irc.error(msg, 'I can\'t send \\n, \\r, or \\0.')

    _stack = []
    def stack(self, irc, msg, args):
        "<'push'|'pop'|'size'|'xray'> <text>"
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





Class = Moobot
