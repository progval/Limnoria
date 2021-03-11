###
# Copyright (c) 2003-2005, Jeremiah Fincher
# Copyright (c) 2008-2009, James McCoy
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

import re
import sys
import types
import codecs
import base64
import binascii
import unicodedata

import supybot.utils as utils
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.plugins as plugins
import supybot.commands as commands
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization('String')

import multiprocessing

class String(callbacks.Plugin):
    """Provides useful commands for manipulating characters and strings."""
    def ord(self, irc, msg, args, letter):
        """<letter>

        Returns the unicode codepoint of <letter>.
        """
        irc.reply(str(ord(letter)))
    ord = wrap(ord, ['letter'])

    def chr(self, irc, msg, args, i):
        """<number>

        Returns the unicode character associated with codepoint <number>
        """
        try:
            irc.reply(chr(i), stripCtcp=False)
        except ValueError:
            irc.error(_('That number doesn\'t map to a unicode character.'))
    chr = wrap(chr, ['int'])

    def unicodename(self, irc, msg, args, character):
        """<character>

        Returns the name of the given unicode <character>."""
        if len(character) != 1:
            irc.errorInvalid('character', character)
        try:
            irc.reply(unicodedata.name(character))
        except ValueError:
            irc.error(_('No name found for this character.'))
    unicodename = wrap(unicodename, ['something'])

    def unicodesearch(self, irc, msg, args, name):
        """<name>

        Searches for a unicode character from its <name>."""
        try:
            irc.reply(unicodedata.lookup(name))
        except KeyError:
            irc.error(_('No character found with this name.'))
    unicodesearch = wrap(unicodesearch, ['text'])

    def encode(self, irc, msg, args, encoding, text):
        """<encoding> <text>

        Returns an encoded form of the given text; the valid encodings are
        available in the documentation of the Python codecs module:
        <http://docs.python.org/library/codecs.html#standard-encodings>.
        """
        # Binary codecs are prefixed with _codec in Python 3
        if encoding in 'base64 bz2 hex quopri uu zlib':
            encoding += '_codec'
        if encoding.endswith('_codec'):
            text = text.encode()

        # Do the encoding
        try:
            encoder = codecs.getencoder(encoding)
        except LookupError:
            irc.errorInvalid(_('encoding'), encoding)
        text = encoder(text)[0]

        # If this is a binary codec, re-encode it with base64
        if encoding.endswith('_codec') and encoding != 'base64_codec':
            text = codecs.getencoder('base64_codec')(text)[0].decode()

        # Change result into a string
        if minisix.PY2 and isinstance(text, unicode):
            text = text.encode('utf-8')
        elif minisix.PY3 and isinstance(text, bytes):
            text = text.decode()

        if encoding in ('base64', 'base64_codec'):
            text = text.replace('\n', '')

        # Reply
        irc.reply(text.rstrip('\n'))
    encode = wrap(encode, ['something', 'text'])

    def decode(self, irc, msg, args, encoding, text):
        """<encoding> <text>

        Returns an un-encoded form of the given text; the valid encodings are
        available in the documentation of the Python codecs module:
        <http://docs.python.org/library/codecs.html#standard-encodings>.
        """
        # Binary codecs are prefixed with _codec in Python 3
        if encoding in 'base64 bz2 hex quopri uu zlib':
            encoding += '_codec'

        # If this is a binary codec, pre-decode it with base64
        if encoding.endswith('_codec') and encoding != 'base64_codec':
            text = codecs.getdecoder('base64_codec')(text.encode())[0]

        # Do the decoding
        try:
            decoder = codecs.getdecoder(encoding)
        except LookupError:
            irc.errorInvalid(_('encoding'), encoding)
        if minisix.PY3 and not isinstance(text, bytes):
            text = text.encode()
        try:
            text = decoder(text)[0]
        except binascii.Error:
            irc.errorInvalid(_('base64 string'),
                             s=_('Base64 strings must be a multiple of 4 in '
                               'length, padded with \'=\' if necessary.'))
            return

        # Change result into a string
        if minisix.PY2 and isinstance(text, unicode):
            text = text.encode('utf-8')
        elif minisix.PY3 and isinstance(text, bytes):
            try:
                text = text.decode()
            except UnicodeDecodeError:
                pass

        # Reply
        irc.reply(text)
    decode = wrap(decode, ['something', 'text'])

    def levenshtein(self, irc, msg, args, s1, s2):
        """<string1> <string2>

        Returns the levenshtein distance (also known as the "edit distance"
        between <string1> and <string2>)
        """
        max = self.registryValue('levenshtein.max')
        if len(s1) > max or len(s2) > max:
            irc.error(_('Levenshtein distance is a complicated algorithm, try '
                      'it with some smaller inputs.'))
        else:
            irc.reply(str(utils.str.distance(s1, s2)))
    levenshtein = thread(wrap(levenshtein, ['something', 'text']))

    def soundex(self, irc, msg, args, text, length):
        """<string> [<length>]

        Returns the Soundex hash to a given length.  The length defaults to
        4, since that's the standard length for a soundex hash.  For unlimited
        length, use 0. Maximum length 1024.
        """
        if length > 1024:
            irc.error("Maximum allowed length is 1024.")
            return
        irc.reply(utils.str.soundex(text, length))
    soundex = wrap(soundex, ['somethingWithoutSpaces', additional('int', 4)])

    def len(self, irc, msg, args, text):
        """<text>

        Returns the length of <text>.
        """
        irc.reply(str(len(text)))
    len = wrap(len, ['text'])

    def re(self, irc, msg, args, f, text):
        """<regexp> <text>

        If <regexp> is of the form m/regexp/flags, returns the portion of
        <text> that matches the regexp.  If <regexp> is of the form
        s/regexp/replacement/flags, returns the result of applying such a
        regexp to <text>.
        """
        if f('') and len(f(' ')) > len(f(''))+1: # Matches the empty string.
            s = _('You probably don\'t want to match the empty string.')
            irc.error(s)
        else:
            t = self.registryValue('re.timeout')
            try:
                v = process(f, text, timeout=t, pn=self.name(), cn='re')
                if isinstance(v, list):
                    v = format('%L', v)
                irc.reply(v)
            except commands.ProcessTimeoutError as e:
                irc.error("ProcessTimeoutError: %s" % (e,))
            except re.error as e:
                irc.error(e.args[0])
    re = thread(wrap(re, [first('regexpMatcherMany', 'regexpReplacer'),
                   'text']))

    def xor(self, irc, msg, args, password, text):
        """<password> <text>

        Returns <text> XOR-encrypted with <password>.
        """
        chars = utils.iter.cycle(password)
        ret = [chr(ord(c) ^ ord(next(chars))) for c in text]
        irc.reply(''.join(ret))
    xor = wrap(xor, ['something', 'text'])

    def md5(self, irc, msg, args, text):
        """<text>

        Returns the md5 hash of a given string.
        """
        irc.reply(utils.crypt.md5(text.encode('utf8')).hexdigest())
    md5 = wrap(md5, ['text'])

    def sha(self, irc, msg, args, text):
        """<text>

        Returns the SHA1 hash of a given string.
        """
        irc.reply(utils.crypt.sha(text.encode('utf8')).hexdigest())
    sha = wrap(sha, ['text'])

Class = String


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
