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
NickServ: Handles management of nicks with NickServ.

Commands include:
  startnickserv (bot's nick, password, NickServ's nick [defaults to NickServ])
"""

from baseplugin import *

import re

import ircdb
import ircmsgs
import privmsgs
import ircutils
import callbacks

class NickServ(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.started = False
        
    def startnickserv(self, irc, msg, args):
        "<bot's nick> <password> <NickServ's nick (defaults to NickServ)>"
        if ircutils.isChannel(msg.args[0]):
            irc.error(msg, 'Command must not be done in a channel.')
        if ircdb.checkCapability(msg.prefix, 'owner'):
            (self.nick, self.password, nickserv) = privmsgs.getArgs(args, 
                                                                    needed=2, 
                                                                    optional=1)
            self.nickserv = nickserv or 'NickServ'
            self.sentGhost = 0
            self._ghosted = re.compile('%s.*killed' % self.nick)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'owner')

    _owned = re.compile('nick.*(?:(?<!not)(?:registered|protected|owned))')
    def doNotice(self, irc, msg):
        if self.started:
            if msg.nick == self.nickserv:
                if self._owned.search(msg.args[1]):
                    # NickServ told us the nick is registered.
                    identify = 'IDENTIFY %s' % self.password
                    irc.queueMsg(ircmsgs.privmsg(self.nickserv, identify))
                elif self._ghosted.search(msg.args[1]):
                    # NickServ told us the nick has been ghost-killed.
                    irc.queueMsg(ircmsgs.nick(self.nick))

    def do376(self, irc, msg):
        if self.started:
            if irc.nick != self.nick:
                ghost = 'GHOST %s %s' % (self.nick, self.password)
                irc.queueMsg(ircmsgs.privmsg(self.nickserv, ghost))


Class = NickServ
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
