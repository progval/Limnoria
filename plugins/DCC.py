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
Supports various DCC things.
"""

import plugins

import socket
import textwrap
import threading

import debug
import utils
import world
import ircmsgs
import ircutils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load DCC')

class DCC(callbacks.Privmsg):
    def chat(self, irc, msg, args):
        """<text>

        Sends <text> to the user via a DCC CHAT.  Use nested commands to your
        benefit here.
        """
        text = privmsgs.getArgs(args)
        def openChatPort():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(60)
                host = ircutils.hostFromHostmask(irc.prefix)
                ip = socket.gethostbyname(host)
                i = ircutils.dccIP(ip)
                sock.bind((host, 0))
                port = sock.getsockname()[1]
                debug.msg('DCC CHAT port opened at (%s, %s)' % (host, port),
                          'normal')
                sock.listen(1)
                irc.queueMsg(ircmsgs.privmsg(msg.nick,
                                             '\x01DCC CHAT chat %s %s\x01' % \
                                             (i, port)))
                (realSock, addr) = sock.accept()
                debug.msg('DCC CHAT accepted from %s' % (addr,), 'normal')
                for line in textwrap.wrap(text, 80):
                    realSock.send(line)
                    realSock.send('\n')
            finally:
                debug.msg('Finally closing sock and realSock.', 'normal')
                sock.close()
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
