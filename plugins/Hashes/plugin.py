###
# Copyright (c) 2017, Ken Spencer
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

import hashlib

import supybot.conf as conf
import supybot.registry as registry
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.commands as commands
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Hashes')

class Hashes(callbacks.Plugin):
    """Provides hash or encryption related commands"""

    @internationalizeDocstring
    def md5(self, irc, msg, args, text):
        """<text>

        Returns the md5 hash of a given string.
        """
        irc.reply(hashlib.md5(text.encode('utf8')).hexdigest())
    md5 = wrap(md5, ['text'])

    @internationalizeDocstring
    def sha(self, irc, msg, args, text):
        """<text>

        Returns the SHA1 hash of a given string.
        """
        irc.reply(hashlib.sha1(text.encode('utf8')).hexdigest())
    sha = wrap(sha, ['text'])

    @internationalizeDocstring
    def sha256(self, irc, msg, args, text):
        """<text>

        Returns a SHA256 hash of the given string.
        """
        irc.reply(hashlib.sha256(text.encode('utf8')).hexdigest())
    sha256 = wrap(sha256, ['text'])

    @internationalizeDocstring
    def sha512(self, irc, msg, args, text):
        """<text>

        Returns a SHA512 hash of the given string.
        """
        irc.reply(hashlib.sha512(text.encode('utf8')).hexdigest())
    sha512 = wrap(sha512, ['text'])

    @internationalizeDocstring
    def algorithms(self, irc, msg, args):
        """<takes no arguments>

        Returns the list of available algorithms."""
        irc.reply(utils.str.format("%L", hashlib.algorithms_available))

    if hasattr(hashlib, 'algorithms_available'):
        algorithms = wrap(algorithms)

    @internationalizeDocstring
    def mkhash(self, irc, msg, args, algorithm, text):
        """<algorithm> <text>

        Returns TEXT after it has been hashed with ALGORITHM. See the 'algorithms' command in this plugin to return the algorithms available on this system."""
        if algorithm not in hashlib.algorithms_available:
            irc.error("Algorithm not available.")
        else:
            irc.reply(hashlib.new(algorithm, text.encode('utf8')).hexdigest())
    if hasattr(hashlib, 'algorithms_available'):
        mkhash = wrap(mkhash, ['something', 'text'])

Class = Hashes
