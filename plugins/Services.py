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
        self.reset()

    def reset(self):
        self.sentGhost = False
        self.identified = False

    def start(self, irc, msg, args):
        """<nick> <password> [<nickserv> <chanserv>]

        Sets the necessary values for the services plugin to work.  <nick>
        is the nick the bot should use (it must be registered with nickserv).
        <password> is the password the registered <nick> uses.  The optional
        arguments <nickserv> and <chanserv> are the names of the NickServ and
        ChanServ, respectively,  They default to NickServ and ChanServ.
        """
        if ircutils.isChannel(msg.args[0]):
            irc.errorRequiresPrivacy()
            return
        (self.nick, self.password, nickserv, chanserv) = \
                    privmsgs.getArgs(args, required=2, optional=2)
        if not self.nick:
            irc.error('The registered nick cannot be blank.')
            return
        self.nick = ircutils.IrcString(self.nick)
        self.nickserv = ircutils.IrcString(nickserv or 'NickServ')
        self.chanserv = ircutils.IrcString(chanserv or 'ChanServ')
        self._ghosted = re.compile('(Ghost|%s).*killed' % self.nick, re.I)
        self.sentGhost = False
        self.log.info('Services started.')
        irc.replySuccess()

    def _doIdentify(self, irc):
        assert self.nickserv, 'Nickserv must not be empty.'
        assert irc.nick == self.nick, 'Identifying with not normal nick.'
        self.log.info('Sending identify (current nick: %s)' % irc.nick)
        identify = 'IDENTIFY %s' % self.password
        # It's important that this next statement is irc.sendMsg, not
        # irc.queueMsg.  We want this message to get through before any
        # JOIN messages also being sent on 376.
        irc.sendMsg(ircmsgs.privmsg(self.nickserv, identify))

    def _doGhost(self, irc):
        assert self.nickserv, 'Nickserv must not be empty.'
        if self.sentGhost:
            self.log.warning('Refusing to send GHOST twice.')
        else:
            self.log.info('Sending ghost (current nick: %s)', irc.nick)
            ghost = 'GHOST %s %s' % (self.nick, self.password)
            # Ditto about the sendMsg.
            irc.sendMsg(ircmsgs.privmsg(self.nickserv, ghost))
            self.sentGhost = True

    def do001(self, irc, msg):
        # New connection, make sure sentGhost is False.
        self.sentGhost = False

    def do376(self, irc, msg):
        if self.nickserv: # Check to see if we're started.
            assert self.nick, 'Services: Nick must not be empty.'
            if irc.nick == self.nick:
                self._doIdentify(irc)
            else:
                self._doGhost(irc)
        else:
            self.log.warning('do376 called without plugin being started.')
    do422 = do377 = do376

    def do433(self, irc, msg):
        if self.nickserv and irc.afterConnect:
            self._doGhost(irc)
        else:
            self.log.warning('do433 called without plugin being started.')

    def doNick(self, irc, msg):
        if msg.args[0] == self.nick:
            hostmask = '*!' + '@'.join(ircutils.splitHostmask(msg.prefix)[1:])
            if ircutils.hostmaskPatternEqual(hostmask, irc.prefix):
                self._doIdentify(irc)

    def doNotice(self, irc, msg):
        if self.nickserv and msg.nick == self.nickserv:
            self.log.debug('Notice received from NickServ: %r', msg)
            s = msg.args[1]
            if self._ghosted.search(msg.args[1]):
                self.log.info('Received "GHOST succeeded" from NickServ')
                self.sentGhost = False
                irc.queueMsg(ircmsgs.nick(self.nick))
            if ('registered' in s or 'protected' in s) and \
               ('not' not in s and 'isn\'t' not in s):
                self.log.info('Received "Registered Nick" from NickServ')
                if self.nick == irc.nick:
                    self._doIdentify(irc)
                else:
                    irc.sendMsg(ircmsgs.nick(self.nick))
            elif 'now recognized' in s:
                self.log.info('Received "Password accepted" from NickServ')
                self.identified = True

    def getops(self, irc, msg, args):
        """[<channel>]

        Attempts to get ops from ChanServ in <channel>.  If no channel is
        given, the current channel is assumed.
        """
        channel = privmsgs.getChannel(msg, args)
        try:
            if irc.nick in irc.state.channels[channel].ops:
                irc.error('I\'ve already got ops in %sx' % channel)
            else:
                irc.sendMsg(ircmsgs.privmsg(self.chanserv, 'op %s' % channel))
        except KeyError:
            irc.error('I\'m not in %s.' % channel)

    def identify(self, irc, msg, args):
        """takes no arguments

        Identifies with NickServ.
        """
        if self.nickserv:
            self._doIdentify(irc)
            irc.replySuccess()
        else:
            s = 'This plugin must first be started via the start command.'
            irc.error(s)



Class = Services

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
