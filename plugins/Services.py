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
import registry
import schedule
import callbacks

def configure(advanced):
    from questions import expect, anything, something, yn
    conf.registerPlugin('Services', True)
    nick = something('What is your registered nick?')
    password = something('What is your password for that nick?')
    chanserv = 'ChanServ'
    if yn('Is your ChanServ named something other than ChanServ?') == 'y':
        chanserv = something('What is your ChanServ named?')
    nickserv = 'NickServ'
    if yn('Is your NickServ named something other than NickServ?') == 'y':
        nickserv = something('What is your NickServ named?')
    conf.supybot.plugins.Services.nick.setValue(nick)
    conf.supybot.plugins.Services.password.setValue(password)
    conf.supybot.plugins.Services.NickServ.setValue(nickserv)
    conf.supybot.plugins.Services.ChanServ.setValue(chanserv)

class ValidNickOrEmptyString(registry.String):
    def setValue(self, v):
        if v and not ircutils.isNick(v):
            raise registry.InvalidRegistryValue, \
                  'Value must be a valid nick or the empty string.'
        self.value = v
            
conf.registerPlugin('Services')
# Not really ChannelValues: but we can have values for each network.  We
# should probably document that this is possible.
conf.registerChannelValue(conf.supybot.plugins.Services, 'nick',
    ValidNickOrEmptyString('', """Determines what nick the bot will use with
    services."""))
conf.registerChannelValue(conf.supybot.plugins.Services, 'password',
    registry.String('', """Determines what password the bot will use with
    services."""))
conf.registerChannelValue(conf.supybot.plugins.Services, 'NickServ',
    ValidNickOrEmptyString('', """Determines what nick the 'NickServ' service
    has."""))
conf.registerChannelValue(conf.supybot.plugins.Services, 'ChanServ',
    ValidNickOrEmptyString('', """Determines what nick the 'ChanServ' service
    has."""))

    
class Services(privmsgs.CapabilityCheckingPrivmsg):
    capability = 'admin'
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.reset()

    def reset(self):
        self.sentGhost = False
        self.identified = False

    def _doIdentify(self, irc):
        nickserv = self.registryValue('NickServ', irc.network)
        if not nickserv:
            self.log.warning('_doIdentify called without a set NickServ.')
            return
        password = self.registryValue('password', irc.network)
        assert irc.nick == self.nick, 'Identifying with not normal nick.'
        self.log.info('Sending identify (current nick: %s)' % irc.nick)
        identify = 'IDENTIFY %s' % password
        # It's important that this next statement is irc.sendMsg, not
        # irc.queueMsg.  We want this message to get through before any
        # JOIN messages also being sent on 376.
        irc.sendMsg(ircmsgs.privmsg(nickserv, identify))

    def _doGhost(self, irc):
        nickserv = self.registryValue('NickServ', irc.network)
        if not nickserv:
            self.log.warning('_doIdentify called without a set NickServ.')
            return
        if self.sentGhost:
            self.log.warning('Refusing to send GHOST twice.')
        else:
            nick = self.registryValue('nick', irc.network)
            password = self.registryValue('password', irc.network)
            self.log.info('Sending ghost (current nick: %s)', irc.nick)
            ghost = 'GHOST %s %s' % (nick, password)
            # Ditto about the sendMsg (see _doIdentify).
            irc.sendMsg(ircmsgs.privmsg(nickserv, ghost))
            self.sentGhost = True

    def do001(self, irc, msg):
        # New connection, make sure sentGhost is False.
        self.sentGhost = False

    def do376(self, irc, msg):
        nickserv = self.registryValue('NickServ', irc.network)
        if nickserv: # Check to see if we're started.
            nick = self.registryValue('nick', irc.network)
            assert nick, 'Services: Nick must not be empty.'
            if irc.nick == nick:
                self._doIdentify(irc)
            else:
                self._doGhost(irc)
        else:
            s = 'supybot.plugins.Services.NickServ is unset; cannot identify.'
            self.log.warning(s)
    do422 = do377 = do376

    def do433(self, irc, msg):
        if irc.afterConnect:
            nickserv = self.registryValue('NickServ', irc.network)
            if nickserv:
                self._doGhost(irc)
            else:
                self.log.warning('do433 called without plugin being started.')

    def doNick(self, irc, msg):
        nick = self.registryValue('nick', irc.network)
        if msg.args[0] == nick:
            self._doIdentify(irc)

    def doNotice(self, irc, msg):
        if irc.afterConnect:
            nickserv = self.registryValue('NickServ', irc.network)
            if not nickserv or msg.nick != nickserv:
                return
            nick = self.registryValue('nick', irc.network)
            self.log.debug('Notice received from NickServ: %r', msg)
            s = msg.args[1]
            if self._ghosted.search(s):
                self.log.info('Received "GHOST succeeded" from NickServ')
                self.sentGhost = False
                irc.queueMsg(ircmsgs.nick(nick))
            if ('registered' in s or 'protected' in s) and \
               ('not' not in s and 'isn\'t' not in s):
                self.log.info('Received "Registered Nick" from NickServ')
                if nick == irc.nick:
                    self._doIdentify(irc)
                else:
                    irc.sendMsg(ircmsgs.nick(nick))
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
                chanserv = self.registryValue('ChanServ', irc.network)
                if chanserv:
                    irc.sendMsg(ircmsgs.privmsg(chanserv, 'op %s' % channel))
                else:
                    irc.error('You must set supybot.plugins.Services.ChanServ '
                              'before I\'m able to do get ops.')
        except KeyError:
            irc.error('I\'m not in %s.' % channel)

    def identify(self, irc, msg, args):
        """takes no arguments

        Identifies with NickServ.
        """
        if self.registryValue('NickServ', irc.network):
            self._doIdentify(irc)
            irc.replySuccess()
        else:
            irc.error('You must set supybot.plugins.Services.NickServ before '
                      'I\'m able to do identify.')



Class = Services

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
