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

from baseplugin import *

import cdb

class AnagramDatabase:
    def __init__(self, filename):
        self.filename = filename
        self.db = cdb.shelf(self.filename)

    def _makeKey(self, key):
        chars = list(key)
        chars.sort()
        return ''.join(chars)

    def find(self, key):
        key = self._makeKey(key)
        return self.db[key]

    def add(self, word):
        key = self._makeKey(word)
        initial = self.db.get(key, [])
        initial.append(word)
        self.db[key] = initial

    def remove(self, word):
        key = self._makeKey(word)
        l = self.db[key]
        if key not in l:
            raise KeyError, word
        else:
            self.db[key] = [x for x in l if x != key]

    def close(self):
        self.db.close()

    def flush(self):
        self.db.flush()


class Anagrams(BasePlugin):
    def startanagrams(self, irc, msg, args):
        "<filename of anagrams database>"
        if ircdb.checkCapability(msg.prefix, 'admin'):
            self.filename = os.path.join(world.dataDir, self.getArgs(args))
            self.db = AnagramDatabase(self.filename)
            self.started = True
            self.reply(privmsgs.replySuccess)
        else:
            self.error(privmsgs.replyNoCapability % 'admin')

    def stopanagrams(self, irc, msg, args):
        "<takes no arguments; stop the anagrams plugin."
        if ircdb.checkCapability(msg.prefix, 'admin'):
            self.db.close()
            self.started = False
            self.reply(privmsgs.replySuccess)
        else:
            self.error(privmsgs.replyNoCapability % 'admin')

    def addanagramword(self, irc, msg, args):
        "<word>"
        word = self.getArgs(args)
        self.db.add(word)
        self.reply(privmsgs.replySuccess)

    def delanagramword(self, irc, msg, args):
        "<word>"
        word = self.getArgs(args)
        self.db.remove(word)
        self.reply(privmsgs.replySuccess)

    def anagram(self, irc, msg, args):
        "<word>"
        word = self.getArgs(args)
        try:
            l = [s for s in self.db.find(word) if s != word]
            if l:
                self.reply(', '.join(self.db.find(word)))
            else:
                self.error('%s has no anagrams.' % word)
        except KeyError:
            self.error('%s isn\'t in my anagram dictionary.' % word)

Class = Anagrams

###
# This makes an anagram database from a list of words on stdin.
###
if __name__ == '__main__':
    import sys, string
    db = AnagramDatabase(os.path.join(world.dataDir, 'anagrams.db'))
    trans = string.maketrans(string.ascii_uppercase, string.ascii_lowercase)
    for line in sys.stdin:
        db.add(line.translate(trans, '\n'))
    db.flush()
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
