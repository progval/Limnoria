#!/usr/bin/env python

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

"""
Supports various DCC things.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import socket
import textwrap
import threading

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks

class DCC(callbacks.Privmsg):
    def chat(self, irc, msg, args):
        """<text>

        Sends <text> to the user via a DCC CHAT.  Use nested commands to your
        benefit here.
        """
        text = privmsgs.getArgs(args)
        def openChatPort():
            try:
                host = ircutils.hostFromHostmask(irc.prefix)
                try:
                    sock = utils.getSocket(host)
                except socket.error, e:
                    s = 'Error connecting to %s: %s'
                    self.log.warning(s, host, e)
                    irc.replyError()
                    return
                sock.settimeout(60)
                if conf.supybot.externalIP():
                    ip = conf.supybot.externalIP()
                else:
                    try:
                        ip = socket.gethostbyname(host)
                    except socket.error, e:
                        s = 'Error trying to determine the external IP ' \
                            'address of this machine via the host %s: %s'
                        self.log.warning(s, host, e)
                        irc.replyError()
                        return
                i = ircutils.dccIP(ip)
                try:
                    sock.bind((host, 0))
                except socket.error, e:
                    irc.error('Unable to initiate DCC CHAT.')
                    return
                port = sock.getsockname()[1]
                self.log.info('DCC CHAT port opened at (%s, %s)', host, port)
                sock.listen(1)
                irc.queueMsg(ircmsgs.privmsg(msg.nick,
                                             '\x01DCC CHAT chat %s %s\x01' % \
                                             (i, port)))
                try:
                    (realSock, addr) = sock.accept()
                except socket.timeout:
                    self.log.info('DCC CHAT timed out.')
                    return
                self.log.info('DCC CHAT accepted from %s', addr)
                for line in textwrap.wrap(text, 80):
                    realSock.send(line)
                    realSock.send('\n')
            finally:
                self.log.info('Finally closing sock and realSock.')
                try:
                    sock.close()
                except UnboundLocalError:
                    pass
                try:
                    realSock.close()
                except UnboundLocalError:
                    pass
        t = threading.Thread(target=openChatPort)
        world.threadsSpawned += 1
        t.setDaemon(True)
        t.start()



Class = DCC

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
