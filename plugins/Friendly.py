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
Just a regexp module to make the bot a wee bit friendlier.
"""

import plugins

import re

import ircmsgs
import ircutils
import callbacks

class Friendly(callbacks.PrivmsgRegexp):
    def greet(self, irc, msg, match):
        r"(?:heya?|(?:w(?:hat'?s\b|as)s?up)|howdy|hi|hello)"
        if irc.nick in msg.args[1]:
            s = 'howdy, %s :)' % msg.nick
            irc.queueMsg(callbacks.reply(msg, s, prefixName=False))

    def goodbye(self, irc, msg, match):
        r"(?:good)?bye|adios|vale|ciao|au revoir|seeya|night"
        if irc.nick in msg.args[1]:
            s = 'seeya, %s!' % msg.nick
            irc.queueMsg(callbacks.reply(msg, s, prefixName=False))

    def exclaim(self, irc, msg, match):
        r"^([^\s]+)!"
        if match.group(1) == irc.nick:
            s = msg.nick + '!'
            irc.queueMsg(callbacks.reply(msg, s, prefixName=False))

    def beGracious(self, irc, msg, match):
        r"\b(?:thank'?s?|thx|tnks?)\b"
        if irc.nick in msg.args[1]:
            s = 'you\'re welcome, %s' % msg.nick
            irc.queueMsg(callbacks.reply(msg, s, prefixName=False))


Class = Friendly

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
