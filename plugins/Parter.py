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

import sets

import conf
import utils
import ircdb
import ircmsgs
import ircutils
__revision__ = "$Id$"

import plugins
import privmsgs
import callbacks

def configure(advanced):
    from questions import output, something, yn
    conf.registerPlugin('Parter', True)
    channel = ' '
    while channel:
        L = []
        if yn('Would you like to automatically part a channel?'):
            channel = something('What channel?')
            while not ircutils.isChannel(s):
                output('That\'s not a valid channel.')
                channel = something('What channel?')
            L.append(channel)
        else:
            channel = ''
    conf.supybot.plugins.Parter.channels.setValue(L)

conf.registerPlugin('Parter')
conf.registerGlobalValue(conf.supybot.plugins.Parter, 'channels',
    conf.SpaceSeparatedSetOfChannels([], """Determines what channels the bot
    will automatically part whenever it joins them."""))

class Parter(callbacks.Privmsg):
    def doJoin(self, irc, msg):
        if irc.nick == msg.nick:
            channels = msg.args[0].split(',')
            autoParts = self.registryValue('channels')
            for channel in channels:
                if channel in autoParts:
                    irc.sendMsg(ircmsgs.part(channel))


Class = Parter
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
