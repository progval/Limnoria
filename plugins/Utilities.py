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
Various utility commands, mostly useful for manipulating nested commands.
"""

from baseplugin import *

import string

import utils
import privmsgs
import callbacks

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, yn
    onStart.append('load Utilities')

class Utilities(callbacks.Privmsg):
    def strjoin(self, irc, msg, args):
        "<separator> <strings to join>"
        sep = args.pop(0)
        args = flatten(map(callbacks.tokenize, args))
        irc.reply(msg, sep.join(args))

    def strtranslate(self, irc, msg, args):
        """<chars to translate> <chars to replace those with> <text>

        Replaces <chars to translate> with <chars to replace those with> in
        <text>.  The first and second arguments must necessarily be the same
        length.
        """
        (bad, good, text) = privmsgs.getArgs(args, needed=3)
        irc.reply(msg, text.translate(string.maketrans(bad, good)))

    def strupper(self, irc, msg, args):
        """<text>

        Returns <text> uppercased.
        """
        irc.reply(msg, privmsgs.getArgs(args).upper())

    def strlower(self, irc, msg, args):
        """<text>

        Returns <text> lowercased.
        """
        irc.reply(msg, privmsgs.getArgs(args).lower())

    def repr(self, irc, msg, args):
        """<text>

        Returns the text surrounded by double quotes.
        """
        text = privmsgs.getArgs(args)
        irc.reply(msg, utils.dqrepr(text))

    def strconcat(self, irc, msg, args):
        "<string 1> <string 2>"
        (first, second) = privmsgs.getArgs(args, needed=2)
        irc.reply(msg, first+second)

    def strsplit(self, irc, msg, args):
        "<separator> <text"
        (sep, text) = privmsgs.getArgs(args, needed=2)
        if sep == '':
            sep = None
        irc.reply(msg, ' '.join(map(repr, text.split(sep))))

    def echo(self, irc, msg, args):
        """takes any number of arguments

        Returns the arguments given it.
        """
        irc.reply(msg, ' '.join(args))

    def arg(self, irc, msg, args):
        (i, rest) = privmsgs.getArgs(args, needed=2)
        i = int(i)
        args = callbacks.tokenize(rest)
        irc.reply(msg, args[i])

    def re(self, irc, msg, args):
        """<regexp> <text>

        Returns all matches to <regexp> (in the form /regexp/flags) in text.
        """
        (regexp, text) = privmsgs.getArgs(args, needed=2)
        try:
            r = utils.perlReToPythonRe(regexp)
        except ValueError, e:
            irc.error(msg, 'Invalid regexp: %s' % e.args[0])
            return
        irc.reply(msg, ' '.join(r.findall(text)))
        
        
Class = Utilities
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
