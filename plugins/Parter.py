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
Some networks find out who's a bot by forcing clients to join a certain
channel when they connect, and the clients that don't leave are considered
bots.  This module makes supybot automatically part certain channels as soon
as he joins.
"""

from baseplugin import *

import conf
import ircdb
import irclib
import ircmsgs
import privmsgs
import callbacks

def configure(onStart, afterConnect, advanced):
    from questions import something, yn
    onStart.append('load Parter')
    s = ' '
    while s:
        if yn('Would you like to automatically part a channel?') == 'y':
            s = something('What channel?')
            while not ircutils.isChannel(s):
                print 'That\'s not a valid channel.'
                s = something('What channel?')
            onStart.append('autopartchannel %s' % s)
        else:
            s = ''

example = utils.wrapLines("""
<jemfinch> @list Parter
<supybot> jemfinch: autopartchannel, removeautopartchannel
<jemfinch> @autopartchannel #supybot
<supybot> jemfinch: The operation succeeded.
<jemfinch> @join #supybot

--> supybot (~supybot@dhcp065-024-059-168.columbus.rr.com) has joined #supybot
<-- supybot (~supybot@dhcp065-024-059-168.columbus.rr.com) has left #supybot

<jemfinch> @removeautopartchannel #supybot
<supybot> jemfinch: The operation succeeded.
<jemfinch> @join #supybot

--> supybot (~supybot@dhcp065-024-059-168.columbus.rr.com) has joined #supybot
""")

class Parter(callbacks.Privmsg):
    def autopartchannel(self, irc, msg, args):
        """<channel>


        Makes the bot part <channel> automatically, as soon as he joins it.
        """
        channel = privmsgs.getArgs(args)
        if ircdb.checkCapability(msg.prefix, 'admin'):
            if not hasattr(self, 'channels'):
                self.channels = [channel]
            else:
                self.channels.append(channel)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')

    def removeautopartchannel(self, irc, msg, args):
        """<channel>

        Removes the channel from the auto-part list.
        """
        channel = privmsgs.getArgs(args)
        if ircdb.checkCapability(msg.prefix, 'admin'):
            if hasattr(self, 'channels'):
                self.channels = [x for x in self.channels if x != channel]
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % 'admin')

    def doJoin(self, irc, msg):
        if irc.nick == msg.nick:
            channels = msg.args[0].split(',')
            for channel in channels:
                if channel in self.channels:
                    irc.sendMsg(ircmsgs.part(channel))


Class = Parter
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
