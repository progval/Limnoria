#!/usr/bin/python

###
# Copyright (c) 2004, Jeremiah Fincher
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
This module attempts to capture the bot's nick, watching for an opportunity to
switch to that nick.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import time

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('NickCapture', True)

conf.registerPlugin('NickCapture')
conf.registerGlobalValue(conf.supybot.plugins.NickCapture, 'ison',
    registry.Boolean(True, """Determines whether the bot will check
    occasionally if its preferred nick is in use via the ISON command."""))
conf.registerGlobalValue(conf.supybot.plugins.NickCapture.ison, 'period',
    registry.PositiveInteger(600, """Determines how often (in seconds) the bot
    will check whether its nick ISON."""))

class NickCapture(callbacks.Privmsg):
    """This module constantly tries to take whatever nick is configured as
    supybot.nick.  Just make sure that's set appropriately, and thus plugin
    will do the rest."""
    public = False
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.lastIson = 0
        
    def _getNick(self):
        return conf.supybot.nick()

    def __call__(self, irc, msg):
        if irc.afterConnect:
            nick = self._getNick()
            if nick and not ircutils.strEqual(nick, irc.nick):
                if nick not in irc.state.nicksToHostmasks:
                    # We don't know if it's online, let's ISON it.
                    self._ison(irc, nick)
                callbacks.Privmsg.__call__(self, irc, msg)

    def _ison(self, irc, nick):
        if self.registryValue('ison'):
            now = time.time()
            if now - self.lastIson > self.registryValue('ison.period'):
                self.lastIson = now
                self._sendIson(irc, nick)
                
    def _sendIson(self, irc, nick):
        self.log.info('Checking if %s ISON %s.', nick, irc.network)
        irc.queueMsg(ircmsgs.ison(nick))

    def _sendNick(self, irc, nick):
        self.log.info('Attempting to switch to nick %s on %s.',
                      nick, irc.network)
        irc.sendMsg(ircmsgs.nick(nick))
        
    def doQuit(self, irc, msg):
        nick = self._getNick()
        if ircutils.strEqual(msg.nick, nick):
            self._sendNick(irc, nick)
            
    def doNick(self, irc, msg):
        nick = self._getNick()
        if ircutils.strEqual(msg.nick, nick):
            self._sendNick(irc, nick)

    def do303(self, irc, msg):
        """This is returned by the ISON command."""
        if not msg.args[1]:
            nick = self._getNick()
            if nick:
                self._sendNick(irc, nick)


Class = NickCapture

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
