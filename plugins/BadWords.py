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
Filters bad words on outgoing messages from the bot, so the bot can't be made
to say bad words.
"""

__revision__ = "$Id$"

import plugins

import re
import math
import sets
import time

import conf
import utils
import ircdb
import ircmsgs
import privmsgs
import registry
import callbacks

def configure(advanced):
    from questions import output, expect, anything, something, yn
    conf.registerPlugin('BadWords', True)
    if yn('Would you like to add some bad words?'):
        words = anything('What words? (separate individual words by spaces)')
        conf.supybot.plugins.BadWords.words.set(words)

class LastModifiedSetOfStrings(registry.SpaceSeparatedListOfStrings):
    List = sets.Set
    lastModified = 0
    def setValue(self, v):
        self.lastModified = time.time()
        registry.SpaceSeparatedListOfStrings.setValue(self, v)

conf.registerPlugin('BadWords')
conf.registerGlobalValue(conf.supybot.plugins.BadWords, 'words',
    LastModifiedSetOfStrings([], """Determines what words are
    considered to be 'bad' so the bot won't say them."""))
conf.registerGlobalValue(conf.supybot.plugins.BadWords,'requireWordBoundaries',
    registry.Boolean(False, """Determines whether the bot will require bad
    words to be independent words, or whether it will censor them within other
    words.  For instance, if 'darn' is a bad word, then if this is true, 'darn'
    will be censored, but 'darnit' will not.  You probably want this to be
    false."""))

class String256(registry.String):
    def setValue(self, s):
        multiplier = int(math.ceil(1024/len(s)))
        registry.String.setValue(self, s*multiplier)
                               
conf.registerGlobalValue(conf.supybot.plugins.BadWords, 'nastyChars',
    String256('!@#&', """Determines what characters will replace bad words; a
    chunk of these characters matching the size of the replaced bad word will
    be used to replace the bad words you've configured."""))

class ReplacementMethods(registry.OnlySomeStrings):
    validStrings = ('simple', 'nastyCharacters')
    
conf.registerGlobalValue(conf.supybot.plugins.BadWords, 'replaceMethod',
    ReplacementMethods('nastyCharacters', """Determines the manner in which
    bad words will be replaced.  'nastyCharacters' (the default) will replace a
    bad word with the same number of 'nasty characters' (like those used in
    comic books; configurable by supybot.plugins.BadWords.nastyChars).
    'simple' will replace a bad word with a simple strings (regardless of the
    length of the bad word); this string is configurable via
    supybot.plugins.BadWords.simpleReplacement."""))
conf.registerGlobalValue(conf.supybot.plugins.BadWords,'simpleReplacement',
    registry.String('[CENSORED]', """Determines what word will replace bad
    words if the replacement method is 'simple'."""))

class BadWords(privmsgs.CapabilityCheckingPrivmsg):
    priority = 1
    capability = 'admin'
    def __init__(self):
        privmsgs.CapabilityCheckingPrivmsg.__init__(self)
        self.lastModified = 0
        self.words = conf.supybot.plugins.BadWords.words

    def sub(self, m):
        replaceMethod = self.registryValue('replaceMethod')
        if replaceMethod == 'simple':
            return self.registryValue('simpleReplacement')
        elif replaceMethod == 'nastyCharacters':
            return self.registryValue('nastyChars')[:len(m.group(1))]

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if self.lastModified < self.words.lastModified:
                self.makeRegexp(self.words())
                self.lastModified = time.time()
            s = msg.args[1]
            s = self.regexp.sub(self.sub, s)
            return ircmsgs.privmsg(msg.args[0], s)
        else:
            return msg

    def makeRegexp(self, iterable):
        s = '(%s)' % '|'.join(map(re.escape, iterable))
        if self.registryValue('requireWordBoundaries'):
            s = r'\b%s\b' % s
        self.regexp = re.compile(s, re.I)

    def add(self, irc, msg, args):
        """<word> [<word> ...]

        Adds all <word>s to the list of words the bot isn't to say.
        """
        set = self.words()
        set.update(args)
        self.words.setValue(set)
        irc.replySuccess()

    def remove(self, irc, msg, args):
        """<word> [<word> ...]

        Removes a <word>s from the list of words the bot isn't to say.
        """
        set = self.words()
        for word in args:
            set.discard(word)
        self.words.setValue(set)
        irc.replySuccess()
            

Class = BadWords


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
