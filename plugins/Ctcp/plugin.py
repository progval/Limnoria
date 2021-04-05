###
# Copyright (c) 2002-2004, Jeremiah Fincher
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
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.schedule as schedule
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Ctcp')

class Ctcp(callbacks.PluginRegexp):
    """
    Provides replies to common CTCPs (version, time, etc.), and a command
    to fetch version responses from channels.

    Please note that the command `ctcp version` cannot receive any responses if the channel is
    mode +C or similar which prevents CTCP requests to channel.
    """
    public = False
    regexps = ('ctcpPing', 'ctcpVersion', 'ctcpUserinfo',
               'ctcpTime', 'ctcpFinger', 'ctcpSource')
    def __init__(self, irc):
        self.__parent = super(Ctcp, self)
        self.__parent.__init__(irc)
        self.ignores = ircutils.IrcDict()
        self.floods = ircutils.FloodQueue(conf.supybot.abuse.flood.interval())
        conf.supybot.abuse.flood.interval.addCallback(self.setFloodQueueTimeout)

    def setFloodQueueTimeout(self, *args, **kwargs):
        self.floods.timeout = conf.supybot.abuse.flood.interval()

    def callCommand(self, command, irc, msg, *args, **kwargs):
        if conf.supybot.abuse.flood.ctcp():
            now = time.time()
            for (ignore, expiration) in self.ignores.items():
                if expiration < now:
                    del self.ignores[ignore]
                elif ircutils.hostmaskPatternEqual(ignore, msg.prefix):
                        return
            self.floods.enqueue(msg)
            max = conf.supybot.abuse.flood.ctcp.maximum()
            if self.floods.len(msg) > max:
                expires = conf.supybot.abuse.flood.ctcp.punishment()
                self.log.warning('Apparent CTCP flood from %s, '
                                 'ignoring CTCP messages for %s seconds.',
                                 msg.prefix, expires)
                ignoreMask = '*!%s@%s' % (msg.user, msg.host)
                self.ignores[ignoreMask] = now + expires
                return
        self.__parent.callCommand(command, irc, msg, *args, **kwargs)

    def _reply(self, irc, msg, s):
        s = '\x01%s\x01' % s
        irc.reply(s, notice=True, private=True, to=msg.nick, stripCtcp=False)

    def ctcpPing(self, irc, msg, match):
        "^\x01PING(?: (.+))?\x01$"
        self.log.info('Received CTCP PING from %s', msg.prefix)
        payload = match.group(1)
        if payload:
            self._reply(irc, msg, 'PING %s' % match.group(1))
        else:
            self._reply(irc, msg, 'PING')

    def ctcpVersion(self, irc, msg, match):
        "^\x01VERSION\x01$"
        self.log.info('Received CTCP VERSION from %s', msg.prefix)
        self._reply(irc, msg, 'VERSION Limnoria %s' % conf.version)

    def ctcpUserinfo(self, irc, msg, match):
        "^\x01USERINFO\x01$"
        self.log.info('Received CTCP USERINFO from %s', msg.prefix)
        self._reply(irc, msg, 'USERINFO %s' % self.registryValue('userinfo'))

    def ctcpTime(self, irc, msg, match):
        "^\x01TIME\x01$"
        self.log.info('Received CTCP TIME from %s', msg.prefix)
        self._reply(irc, msg, 'TIME %s' % time.ctime())

    def ctcpFinger(self, irc, msg, match):
        "^\x01FINGER\x01$"
        self.log.info('Received CTCP FINGER from %s', msg.prefix)
        self._reply(irc, msg, 'FINGER ' +
                    _('Supybot, the best Python IRC bot in existence!'))

    def ctcpSource(self, irc, msg, match):
        "^\x01SOURCE\x01$"
        self.log.info('Received CTCP SOURCE from %s', msg.prefix)
        self._reply(irc, msg,
                    'SOURCE https://github.com/ProgVal/Limnoria')

    def doNotice(self, irc, msg):
        if ircmsgs.isCtcp(msg):
            try:
                (version, payload) = msg.args[1][1:-1].split(None, 1)
            except ValueError:
                return
            if version == 'VERSION':
                self.versions.setdefault(payload, []).append(msg.nick)

    @internationalizeDocstring
    def version(self, irc, msg, args, channel, optlist):
        """[<channel>] [--nicks]

        Sends a CTCP VERSION to <channel>, returning the various
        version strings returned.  It waits for 10 seconds before returning
        the versions received at that point.  If --nicks is given, nicks are
        associated with the version strings; otherwise, only the version
        strings are given.
        """
        self.versions = ircutils.IrcDict()
        nicks = False
        for (option, arg) in optlist:
            if option == 'nicks':
                nicks = True
        irc.queueMsg(ircmsgs.privmsg(channel, '\x01VERSION\x01'))
        def doReply():
            if self.versions:
                L = []
                for (reply, nickslist) in self.versions.items():
                    if nicks:
                        L.append(format('%L responded with %q', nickslist, reply))
                    else:
                        L.append(reply)
                irc.reply(format('%L', L))
            else:
                irc.reply('I received no version responses.')
        wait = self.registryValue('versionWait')
        schedule.addEvent(doReply, time.time()+wait)
    version = wrap(version, ['channel', getopts({'nicks':''})])

Class = Ctcp
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
