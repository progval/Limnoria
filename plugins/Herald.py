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
Greets users who join the channel with a recognized hostmask with a nice
little greeting.  Otherwise, can greet 
"""

import plugins

import os
import time

import log
import conf
import utils
import world
import ircdb
import ircmsgs
import ircutils
import privmsgs
import registry
import callbacks

filename = os.path.join(conf.supybot.directories.data(), 'Herald.db')

class HeraldDB(plugins.ChannelUserDatabase):
    def serialize(self, v):
        return [v]

    def deserialize(self, L):
        if len(L) != 1:
            raise ValueError
        return L[0]

conf.registerPlugin('Herald')
conf.registerChannelValue(conf.supybot.plugins.Herald, 'heralding',
    registry.Boolean(True, """Determines whether messages will be sent to the
    channel when a recognized user joins; basically enables or disables the
    plugin."""))
conf.registerChannelValue(conf.supybot.plugins.Herald, 'throttleTime',
    registry.PositiveInteger(600, """Determines the minimum number of seconds
    between heralds."""))
conf.registerChannelValue(conf.supybot.plugins.Herald, 'throttleTimeAfterPart',
    registry.PositiveInteger(60, """Determines the minimum number of seconds
    after parting that the bot will not herald the person when he or she
    rejoins."""))

class Herald(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = HeraldDB(filename)
        world.flushers.append(self.db.flush)
        self.lastParts = plugins.ChannelUserDictionary()
        self.lastHerald = plugins.ChannelUserDictionary()

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        self.db.close()
        callbacks.Privmsg.die(self)

    def doJoin(self, irc, msg):
        channel = msg.args[0]
        if self.registryValue('heralding', channel):
            try:
                id = ircdb.users.getUserId(msg.prefix)
                herald = self.db[channel, id]
            except KeyError:
                return
            now = time.time()
            throttle = self.registryValue('throttleTime', channel)
            if now - self.lastHerald.get((channel, id), 0) > throttle:
                if (channel, id) in self.lastParts:
                   i = self.registryValue('throttleTimeAfterPart', channel) 
                   if now - self.lastParts[channel, id] < i:
                       return
                self.lastHerald[channel, id] = now
                irc.queueMsg(ircmsgs.privmsg(channel, herald))

    def doPart(self, irc, msg):
        try:
            id = self._getId(irc, msg.prefix)
            self.lastParts[(id, msg.args[0])] = time.time()
        except KeyError:
            pass

    def _getId(self, irc, userNickHostmask):
        try:
            id = ircdb.users.getUserId(userNickHostmask)
        except KeyError:
            if not ircutils.isUserHostmask(userNickHostmask):
                hostmask = irc.state.nickToHostmask(userNickHostmask)
                id = ircdb.users.getUserId(hostmask)
            else:
                raise KeyError
        return id

    def add(self, irc, msg, args):
        """[<channel>] <user|nick|hostmask> <msg>

        Sets the herald message for <user> (or the user <nick|hostmask> is
        currently identified or recognized as) to <msg>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (userNickHostmask, herald) = privmsgs.getArgs(args, required=2)
        try:
            id = self._getId(irc, userNickHostmask)
        except KeyError:
            irc.errorNoUser()
            return
        self.db[channel, id] = herald
        irc.replySuccess()

    def remove(self, irc, msg, args):
        """[<channel>] <user|nick|hostmask>

        Removes the herald message set for <user>, or the user
        <nick|hostmask> is currently identified or recognized as.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        channel = privmsgs.getChannel(msg, args)
        userNickHostmask = privmsgs.getArgs(args)
        try:
            id = self._getId(irc, userNickHostmask)
        except KeyError:
            irc.errorNoUser()
            return
        del self.db[channel, id]
        irc.replySuccess()


Class = Herald

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
