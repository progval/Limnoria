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
Services: Handles management of nicks with NickServ, and ops with ChanServ.
"""

__revision__ = "$Id$"

import plugins

import re
import time

import conf
import ircmsgs
import privmsgs
import ircutils
import schedule
import callbacks

def configure(onStart, afterConnect, advanced):
    from questions import expect, anything, something, yn
    nick = something('What is your registered nick?')
    password = something('What is your password for that nick?')
    chanserv = 'ChanServ'
    if yn('Is your ChanServ named something other than ChanServ?') == 'y':
        chanserv = something('What is your ChanServ named?')
    nickserv = 'NickServ'
    if yn('Is your NickServ named something other than NickServ?') == 'y':
        nickserv = something('What is your NickServ named?')
    onStart.append('load Services')
    onStart.append('services start %s %s %s %s' % \
                   (nick, password, nickserv, chanserv))

class Services(privmsgs.CapabilityCheckingPrivmsg):
    capability = 'admin'
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.nickserv = ''

    def start(self, irc, msg, args):
        """<nick> <password> [<nickserv> <chanserv>]

        Sets the necessary values for the services plugin to work.  <nick>
        is the nick the bot should use (it must be registered with nickserv).
        <password> is the password the registered <nick> uses.  The optional
        arguments <nickserv> and <chanserv> are the names of the NickServ and
        ChanServ, respectively,  They default to NickServ and ChanServ.
        """
        if ircutils.isChannel(msg.args[0]):
            irc.error(msg, conf.replyRequiresPrivacy)
            return
        (self.nick, self.password, nickserv, chanserv) = \
                    privmsgs.getArgs(args, required=2, optional=2)
        if not self.nick:
            irc.error(msg, 'The registered nick cannot be blank.')
            return
        self.nick = ircutils.IrcString(self.nick)
        self.nickserv = ircutils.IrcString(nickserv or 'NickServ')
        self.chanserv = ircutils.IrcString(chanserv or 'ChanServ')
        self.sentGhost = False
        self._ghosted = re.compile('%s.*killed' % self.nick)
        irc.reply(msg, conf.replySuccess)

    def do376(self, irc, msg):
        if self.nickserv:
            assert self.nick, 'Services: Nick must not be empty.'
            identify = 'IDENTIFY %s' % self.password
            # It's important that this next statement is irc.sendMsg, not
            # irc.queueMsg.  We want this message to get through before any
            # JOIN messages also being sent on 376.
            irc.sendMsg(ircmsgs.privmsg(self.nickserv, identify))
    do377 = do376
    do422 = do376

    def doNotice(self, irc, msg):
        if self.nickserv:
            if msg.nick == self.nickserv:
                s = msg.args[1]
                if ('registered' in s or 'protected' in s) and \
                   ('not' not in s and 'isn\'t' not in s):
                    # NickServ told us the nick is registered.
                    identify = 'IDENTIFY %s' % self.password
                    irc.queueMsg(ircmsgs.privmsg(self.nickserv, identify))
                elif 'recognized' in msg.args[1]:
                    self.sentGhost = False
                elif self._ghosted.search(msg.args[1]):
                    # NickServ told us the nick has been ghost-killed.
                    irc.queueMsg(ircmsgs.nick(self.nick))

    def __call__(self, irc, msg):
        callbacks.Privmsg.__call__(self, irc, msg)
        if self.nickserv:
            if irc.nick != self.nick and not self.sentGhost:
                ghost = 'GHOST %s %s' % (self.nick, self.password)
                irc.queueMsg(ircmsgs.privmsg(self.nickserv, ghost))
                self.sentGhost = True
                def flipSentGhost():
                    self.sentGhost = False
                schedule.addEvent(flipSentGhost, time.time() + 300)

    def getops(self, irc, msg, args):
        """[<channel>]

        Attempts to get ops from ChanServ in <channel>.  If no channel is
        given, the current channel is assumed.
        """
        channel = privmsgs.getChannel(msg, args)
        irc.sendMsg(ircmsgs.privmsg(self.chanserv, 'op %s' % channel))



Class = Services

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
