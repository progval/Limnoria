###
# Copyright (c) 2004-2005, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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

import string

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Format')

class Format(callbacks.Plugin):
    """Provides some commands for formatting text, such as making text bold or
    capitalized."""
    @internationalizeDocstring
    def bold(self, irc, msg, args, text):
        """<text>

        Returns <text> bolded.
        """
        irc.reply(ircutils.bold(text))
    bold = wrap(bold, ['text'])

    @internationalizeDocstring
    def reverse(self, irc, msg, args, text):
        """<text>

        Returns <text> in reverse-video.
        """
        irc.reply(ircutils.reverse(text))
    reverse = wrap(reverse, ['text'])

    @internationalizeDocstring
    def underline(self, irc, msg, args, text):
        """<text>

        Returns <text> underlined.
        """
        irc.reply(ircutils.underline(text))
    underline = wrap(underline, ['text'])

    @internationalizeDocstring
    def color(self, irc, msg, args, fg, bg, text):
        """<foreground> [<background>] <text>

        Returns <text> with foreground color <foreground> and background color
        <background> (if given)
        """
        irc.reply(ircutils.mircColor(text, fg=fg, bg=bg))
    color = wrap(color, ['color', optional('color'), 'text'])

    @internationalizeDocstring
    def join(self, irc, msg, args, sep):
        """<separator> <string 1> [<string> ...]

        Joins all the arguments together with <separator>.
        """
        irc.reply(sep.join(args))
    join = wrap(join, ['anything'], allowExtra=True)

    @internationalizeDocstring
    def translate(self, irc, msg, args, bad, good, text):
        """<chars to translate> <chars to replace those with> <text>

        Replaces <chars to translate> with <chars to replace those with> in
        <text>.  The first and second arguments must necessarily be the same
        length.
        """
        if len(bad) != len(good):
            irc.error(_('<chars to translate> must be the same length as '
                      '<chars to replace those with>.'), Raise=True)
        irc.reply(utils.str.MultipleReplacer(dict(list(zip(bad, good))))(text))
    translate = wrap(translate, ['something', 'something', 'text'])

    @internationalizeDocstring
    def replace(self, irc, msg, args, bad, good, text):
        """<substring to translate> <substring to replace it with> <text>

        Replaces all non-overlapping occurrences of <substring to translate>
        with <substring to replace it with> in <text>.
        """
        irc.reply(text.replace(bad, good))
    replace = wrap(replace, ['anything', 'anything', 'text'])

    def upper(self, irc, msg, args, text):
        """<text>

        Returns <text> uppercased.
        """
        irc.reply(text.upper())
    upper = wrap(upper, ['text'])

    @internationalizeDocstring
    def lower(self, irc, msg, args, text):
        """<text>

        Returns <text> lowercased.
        """
        irc.reply(text.lower())
    lower = wrap(lower, ['text'])

    @internationalizeDocstring
    def capitalize(self, irc, msg, args, text):
        """<text>

        Returns <text> capitalized.
        """
        irc.reply(text.capitalize())
    capitalize = wrap(capitalize, ['text'])

    @internationalizeDocstring
    def title(self, irc, msg, args, text):
        """<text>

        Returns <text> titlecased.
        """
        irc.reply(string.capwords(text, " "))
    title = wrap(title, ['text'])

    @internationalizeDocstring
    def repr(self, irc, msg, args, text):
        """<text>

        Returns <text> surrounded by double quotes.
        """
        irc.reply(utils.str.dqrepr(text))
    repr = wrap(repr, ['text'])

    @internationalizeDocstring
    def concat(self, irc, msg, args, first, second):
        """<string 1> <string 2>

        Concatenates two strings.  Do keep in mind that this is *not* the same
        thing as join "", since if <string 2> contains spaces, they won't be
        removed by concat.
        """
        irc.reply(first+second)
    concat = wrap(concat, ['something', 'text'])

    @internationalizeDocstring
    def cut(self, irc, msg, args, size, text):
        """<size> <text>

        Cuts <text> down to <size> by chopping off the rightmost characters in
        excess of <size>.  If <size> is a negative number, it chops that many
        characters off the end of <text>.
        """
        irc.reply(text[:size])
    cut = wrap(cut, ['int', 'text'])

    @internationalizeDocstring
    def field(self, irc, msg, args, index, text):
        """<number> <text>

        Returns the <number>th space-separated field of <text>.  I.e., if text
        is "foo bar baz" and <number> is 2, "bar" is returned.
        """
        try:
            irc.reply(text.split()[index])
        except IndexError:
            irc.errorInvalid('field')
    field = wrap(field, ['index', 'text'])

    @internationalizeDocstring
    def format(self, irc, msg, args):
        """<format string> [<arg> ...]

        Expands a Python-style format string using the remaining args.  Just be
        sure always to use %s, not %d or %f or whatever, because all the args
        are strings.
        """
        if not args:
            raise callbacks.ArgumentError
        s = args.pop(0)
        try:
            s %= tuple(args)
            irc.reply(s)
        except TypeError as e:
            self.log.debug(utils.exnToString(e))
            irc.error(_('Not enough arguments for the format string.'),
                      Raise=True)


Class = Format

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
