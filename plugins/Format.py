#!/usr/bin/env python

###
# Copyright (c) 2004, Jeremiah Fincher
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
Provides simple commands for formatting text on IRC.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import string

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Format', True)


class Format(callbacks.Privmsg):
    def bold(self, irc, msg, args):
        """<text>

        Returns <text> bolded.
        """
        text = privmsgs.getArgs(args)
        irc.reply(ircutils.bold(text))

    def reverse(self, irc, msg, args):
        """<text>

        Returns <text> in reverse-video.
        """
        text = privmsgs.getArgs(args)
        irc.reply(ircutils.reverse(text))

    def underline(self, irc, msg, args):
        """<text>

        Returns <text> underlined.
        """
        text = privmsgs.getArgs(args)
        irc.reply(ircutils.underline(text))

    def color(self, irc, msg, args):
        """<foreground> [<background>] <text>

        Returns <text> with foreground color <foreground> and background color
        <background> (if given)
        """
        try:
            fg = args.pop(0)
            if args[0] in ircutils.mircColors:
                bg = args.pop(0)
            else:
                bg = None
        except IndexError:
            raise callbacks.ArgumentError
        text = privmsgs.getArgs(args)
        try:
            fg = ircutils.mircColors[fg]
        except KeyError:
            irc.error('%r is not a valid foreground color.' % fg)
            return
        if bg is not None:
            try:
                bg = ircutils.mircColors[bg]
            except KeyError:
                irc.error('%r is not a valid background color.' % bg)
                return
        irc.reply(ircutils.mircColor(text, fg=fg, bg=bg))

    def join(self, irc, msg, args):
        """<separator> <string 1> [<string> ...]

        Joins all the arguments together with <separator>.
        """
        sep = args.pop(0)
        irc.reply(sep.join(args))

    def translate(self, irc, msg, args):
        """<chars to translate> <chars to replace those with> <text>

        Replaces <chars to translate> with <chars to replace those with> in
        <text>.  The first and second arguments must necessarily be the same
        length.
        """
        (bad, good, text) = privmsgs.getArgs(args, required=3)
        irc.reply(text.translate(string.maketrans(bad, good)))

    def upper(self, irc, msg, args):
        """<text>

        Returns <text> uppercased.
        """
        irc.reply(privmsgs.getArgs(args).upper())

    def lower(self, irc, msg, args):
        """<text>

        Returns <text> lowercased.
        """
        irc.reply(privmsgs.getArgs(args).lower())

    def repr(self, irc, msg, args):
        """<text>

        Returns the text surrounded by double quotes.
        """
        text = privmsgs.getArgs(args)
        irc.reply(utils.dqrepr(text))

    def concat(self, irc, msg, args):
        """<string 1> <string 2>

        Concatenates two strings.  Do keep in mind that this is *not* the same
        thing as join "", since if <string 2> contains spaces, they won't be
        removed by concat.
        """
        (first, second) = privmsgs.getArgs(args, required=2)
        irc.reply(first+second)

    def cut(self, irc, msg, args):
        """<size> <text>

        Cuts <text> down to <size> by chopping off the rightmost characters in
        excess of <size>.  If <size> is a negative number, it chops that many
        characters off the end of <text>.
        """
        (size, text) = privmsgs.getArgs(args, required=2)
        try:
            size = int(size)
        except ValueError:
            irc.error('%r is not a valid integer.' % size)
        irc.reply(text[:size])

    def field(self, irc, msg, args):
        """<number> <text>

        Returns the <number>th space-separated field of <text>.  I.e., if text
        is "foo bar baz" and <number> is 2, "bar" is returned.
        """
        (number, text) = privmsgs.getArgs(args, required=2)
        try:
            index = int(number)
            if index > 0:
                index -= 1
        except ValueError:
            irc.error('%r is not a valid integer.' % number)
        try:
            irc.reply(text.split()[index])
        except IndexError:
            irc.error('That\'s not a valid field.')
                     
    def format(self, irc, msg, args):
        """<format string> [<arg> ...]

        Expands a Python-style format string using the remaining args.  Just be
        sure always to use %s, not %d or %f or whatever, because all the args
        are strings.
        """
        try:
            s = args.pop(0)
        except IndexError:
            raise callbacks.ArgumentError
        try:
            s %= tuple(args)
        except TypeError:
            irc.error('Not enough arguments for the format string.')
            return
        irc.reply(s)


Class = Format

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
