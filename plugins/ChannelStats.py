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
import time

import privmsgs
import ircutils
import callbacks

smileys = (':)', ';)', ':]', ':-)', ':-D', ':D', ':P', ':p', '(=', '=)')
frowns = (':|', ':-/', ':-\\', ':\\', ':/', ':(', ':-(', ':\'(')

smileyRegexp = re.compile('|'.join([re.escape(s) for s in smileys]))
frownRegexp = re.compile('|'.join([re.escape(s) for s in frowns]))

class ChannelStats(callbacks.Privmsg, DBHandler):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        DBHandler.__init__(self, '.stats')

    def doPrivmsg(self, irc, msg):
        recipient = msg.args[0]
        if ircutils.isChannel(recipient):
            db = self.getDb(recipient)
            db[msg.nick] = (time.time(), msg.args[1])
        #callbacks.Privmsg.doPrivmsg(self, irc, msg)
        super(self.__class__, self).doPrivmsg(irc, msg)
        #self.__class__.__bases__[0].doPrivmsg(self, irc, msg)

    def seen(self, irc, msg, args):
        "<nick>"
        channel = privmsgs.getChannel(msg, args)
        nick = ircutils.nick(privmsgs.getArgs(args))
        db = self.getDb(channel)
        try:
            (t, saying) = db[nick]
            if t == 0.0: # Default record time.
                raise KeyError
            t = time.localtime(t)
            ret = '%s was last seen on %s on %s at %s saying {%s}' %\
                  (nick, channel, time.strftime('%d-%b-%Y', t),
                   time.strftime('%H:%M:%S'), saying)
            irc.reply(msg, ret)
        except KeyError:
            irc.reply(msg, 'I haven\'t seen any user by that nick.')


Class = ChannelStats

