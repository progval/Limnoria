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

import time

import supybot.conf as conf
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('NickCapture')

class NickCapture(callbacks.Plugin):
    """This plugin constantly tries to take whatever nick is configured as
    supybot.nick.  Just make sure that's set appropriately, and thus plugin
    will do the rest."""
    public = False
    def __init__(self, irc):
        self.__parent = super(NickCapture, self)
        self.__parent.__init__(irc)
        self.lastIson = 0
        self.monitoring = []

    def die(self):
        for irc in self.monitoring:
            nick = self._getNick(irc.network)
            irc.unmonitor(nick)
        
    def _getNick(self, network):
        network_nick = conf.supybot.networks.get(network).nick()
        if network_nick == '':
            return conf.supybot.nick()
        else:
            return network_nick

    def __call__(self, irc, msg):
        if irc.afterConnect:
            nick = self._getNick(irc.network)
            if nick and not ircutils.strEqual(nick, irc.nick):
                # We used to check this, but nicksToHostmasks is never cleared
                # except on reconnects, which can cause trouble.
                # if nick not in irc.state.nicksToHostmasks:
                if 'monitor' in irc.state.supported:
                    if irc not in self.monitoring:
                        irc.monitor(nick)
                        self.monitoring.append(irc)
                else:
                    self._ison(irc, nick)
                self.__parent.__call__(irc, msg)

    def _ison(self, irc, nick):
        assert 'monitor' not in irc.state.supported
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
        nick = self._getNick(irc.network)
        if ircutils.strEqual(msg.nick, nick):
            self._sendNick(irc, nick)
            
    def doNick(self, irc, msg):
        nick = self._getNick(irc.network)
        if ircutils.strEqual(msg.nick, nick):
            self._sendNick(irc, nick)

    def do303(self, irc, msg):
        """This is returned by the ISON command."""
        if not msg.args[1]:
            nick = self._getNick(irc.network)
            if nick:
                self._sendNick(irc, nick)

    def do731(self, irc, msg):
        """This is sent by the MONITOR when a nick goes offline."""
        nick = self._getNick(irc.network)
        for target in msg.args[1].split(','):
            if nick == target:
                self._sendNick(irc, nick)
                self.monitoring.remove(irc)
                irc.unmonitor(nick)
                break

    def do437(self, irc, msg):
        """Nick/channel is temporarily unavailable"""
        if irc.isChannel(msg.args[1]):
            return
        self.log.info('Nick %s is unavailable; attempting NickServ release '
                      'on %s.' % (msg.args[1], irc.network))
        irc.sendMsg(ircmsgs.privmsg('NickServ', 'release %s' % msg.args[1]))
NickCapture = internationalizeDocstring(NickCapture)

Class = NickCapture

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
