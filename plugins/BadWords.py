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

nastyChars = '!@#$' * 256
def subber(m):
    return nastyChars[:len(m.group(1))]

class LastModifiedSetOfStrings(registry.SpaceSeparatedListOfStrings):
    List = sets.Set
    lastModified = 0
    def setValue(self, v):
        self.lastModified = time.time()
        registry.SpaceSeparatedListOfStrings.setValue(self, v)

conf.registerPlugin('BadWords')
conf.registerChannelValue(conf.supybot.plugins.BadWords, 'words',
    LastModifiedSetOfStrings([], """Determines what words are
    considered to be 'bad' so the bot won't say them."""))

class BadWords(privmsgs.CapabilityCheckingPrivmsg):
    priority = 1
    capability = 'admin'
    def __init__(self):
        privmsgs.CapabilityCheckingPrivmsg.__init__(self)
        self.lastModified = 0
        self.words = conf.supybot.plugins.BadWords.words

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if self.lastModified < self.words.lastModified:
                self.makeRegexp(self.words())
                self.lastModified = time.time()
            s = msg.args[1]
            s = self.regexp.sub(subber, s)
            return ircmsgs.privmsg(msg.args[0], s)
        else:
            return msg

    def makeRegexp(self, iterable):
        self.regexp = re.compile(r'\b('+'|'.join(iterable)+r')\b', re.I)

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
