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

import re

import ircdb
import ircmsgs
import privmsgs
import callbacks

class BadWords(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.badwords = set()

    def outFilter(self, irc, msg):
        if hasattr(self, 'regexp') and msg.command == 'PRIVMSG':
            s = msg.args[1]
            s = self.regexp.sub('!@#$', s)
            return ircmsgs.privmsg(msg.args[0], s)
        else:
            return msg

    def makeRegexp(self):
        self.regexp = re.compile('|'.join(self.badwords), re.I)

    def addbadword(self, irc, msg, args):
        "<word>"
        if ircdb.checkCapability(msg.prefix, 'admin'):
            word = privmsgs.getArgs(args)
            self.badwords.add(word)
            self.makeRegexp()
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return

    def addbadwords(self, irc, msg, args):
        "<word> [<word> ...]"
        if ircdb.checkCapability(msg.prefix, 'admin'):
            words = privmsgs.getArgs(args).split()
            self.badwords.extend(words)
            self.makeRegexp()
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return

    def removebadword(self, irc, msg, args):
        "<word>"
        if ircdb.checkCapability(msg.prefix, 'admin'):
            word = privmsgs.getArgs(args)
            self.badwords.remove(word)
            self.makeRegexp()
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return

    def removebadwords(self, irc, msg, args):
        "<word> [<word> ...]"
        if ircdb.checkCapability(msg.prefix, 'admin'):
            words = privmsgs.getArgs(args).split()
            for word in words:
                self.badwords.remove(word)
            self.makeRegexp()
            irc.reply(msg, conf.replySuccess)
            return
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')
            return


Class = BadWords
