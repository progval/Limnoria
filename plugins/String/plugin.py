###
# Copyright (c) 2003-2005, Jeremiah Fincher
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

import md5
import sha
import types

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class String(callbacks.Plugin):
    def ord(self, irc, msg, args, letter):
        """<letter>

        Returns the 8-bit value of <letter>.
        """
        irc.reply(str(ord(letter)))
    ord = wrap(ord, ['letter'])

    def chr(self, irc, msg, args, i):
        """<number>

        Returns the character associated with the 8-bit value <number>
        """
        try:
            irc.reply(chr(i))
        except ValueError:
            irc.error('That number doesn\'t map to an 8-bit character.')
    chr = wrap(chr, ['int'])

    def encode(self, irc, msg, args, encoding, text):
        """<encoding> <text>

        Returns an encoded form of the given text; the valid encodings are
        available in the documentation of the Python codecs module:
        <http://www.python.org/doc/lib/node127.html>.
        """
        try:
            irc.reply(text.encode(encoding))
        except LookupError:
            irc.errorInvalid('encoding', encoding)
    encode = wrap(encode, ['something', 'text'])

    def decode(self, irc, msg, args, encoding, text):
        """<encoding> <text>

        Returns an un-encoded form of the given text; the valid encodings are
        available in the documentation of the Python codecs module:
        <http://www.python.org/doc/lib/node127.html>.
        """
        try:
            irc.reply(text.decode(encoding).encode('utf-8'))
        except LookupError:
            irc.errorInvalid('encoding', encoding)
    decode = wrap(decode, ['something', 'text'])

    def levenshtein(self, irc, msg, args, s1, s2):
        """<string1> <string2>

        Returns the levenshtein distance (also known as the "edit distance"
        between <string1> and <string2>)
        """
        max = self.registryValue('levenshtein.max')
        if len(s1) > max or len(s2) > max:
            irc.error('Levenshtein distance is a complicated algorithm, try '
                      'it with some smaller inputs.')
        else:
            irc.reply(str(utils.str.distance(s1, s2)))
    levenshtein = wrap(levenshtein, ['something', 'text'])

    def soundex(self, irc, msg, args, text, length):
        """<string> [<length>]

        Returns the Soundex hash to a given length.  The length defaults to
        4, since that's the standard length for a soundex hash.  For unlimited
        length, use 0.
        """
        irc.reply(utils.str.soundex(text, length))
    soundex = wrap(soundex, ['somethingWithoutSpaces', additional('int', 4)])

    def len(self, irc, msg, args):
        """<text>

        Returns the length of <text>.
        """
        total = 0
        for arg in args:
            total += len(arg)
        total += len(args)-1 # spaces between the arguments.
        irc.reply(str(total))

    def re(self, irc, msg, args, ff, text):
        """<regexp> <text>

        If <regexp> is of the form m/regexp/flags, returns the portion of
        <text> that matches the regexp.  If <regexp> is of the form
        s/regexp/replacement/flags, returns the result of applying such a
        regexp to <text>
        """
        if isinstance(ff, (types.FunctionType, types.MethodType)):
            f = ff
        else:
            f = lambda s: ff.search(s) and ff.search(s).group(0) or ''
        if f('') and len(f(' ')) > len(f(''))+1: # Matches the empty string.
            s = 'You probably don\'t want to match the empty string.'
            irc.error(s)
        else:
            irc.reply(f(text))
    re = wrap(re, [('checkCapability', 'trusted'),
                   first('regexpMatcher', 'regexpReplacer'),
                   'text'])

    def xor(self, irc, msg, args, password, text):
        """<password> <text>

        Returns <text> XOR-encrypted with <password>.  See
        http://www.yoe.org/developer/xor.html for information about XOR
        encryption.
        """
        chars = utils.iter.cycle(password)
        ret = [chr(ord(c) ^ ord(chars.next())) for c in text]
        irc.reply(''.join(ret))
    xor = wrap(xor, ['something', 'text'])

    def md5(self, irc, msg, args, text):
        """<text>

        Returns the md5 hash of a given string.  Read
        http://www.rsasecurity.com/rsalabs/faq/3-6-6.html for more information
        about md5.
        """
        irc.reply(md5.md5(text).hexdigest())
    md5 = wrap(md5, ['text'])

    def sha(self, irc, msg, args, text):
        """<text>

        Returns the SHA hash of a given string.  Read
        http://www.secure-hash-algorithm-md5-sha-1.co.uk/ for more information
        about SHA.
        """
        irc.reply(sha.sha(text).hexdigest())
    sha = wrap(sha, ['text'])

Class = String


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
