#!/usr/bin/python

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
import ircdb
import ircmsgs
import ircutils
import privmsgs
import callbacks
import configurable


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Herald')


class HeraldDB(object):
    def __init__(self):
        self.heralds = {}
        self.open()

    def open(self):
        filename = os.path.join(conf.dataDir, 'Herald.db')
        if os.path.exists(filename):
            fd = file(filename)
            for line in fd:
                line = line.rstrip()
                try:
                    (idChannel, msg) = line.split(':', 1)
                    (id, channel) = idChannel.split(',', 1)
                    id = int(id)
                except ValueError:
                    log.warning('Invalid line in HeraldDB: %r', line)
                    continue
                self.heralds[(id, channel)] = msg
            fd.close()

    def close(self):
        fd = file(os.path.join(conf.dataDir, 'Herald.db'), 'w')
        L = self.heralds.items()
        L.sort()
        for ((id, channel), msg) in L:
            fd.write('%s,%s:%s%s' % (id, channel, msg, os.linesep))
        fd.close()
        
    def getHerald(self, id, channel):
        return self.heralds[(id, channel)]

    def setHerald(self, id, channel, msg):
        self.heralds[(id, channel)] = msg

    def delHerald(self, id, channel):
        del self.heralds[(id, channel)]


class Herald(callbacks.Privmsg, configurable.Mixin):
    configurables = configurable.Dictionary(
        [('heralding', configurable.BoolType, True,
          """Determines whether messages will be sent to the channel when
             a recognized user joins; basically enables or disables the
             plugin."""),
         ('throttle-time', configurable.PositiveIntType, 600,
          """Determines the minimum number of seconds between heralds."""),
         ('throttle-after-part', configurable.IntType, 60,
          """Determines the minimum number of seconds after parting that the
          bot will not herald the person when he or she rejoins."""),]
    )
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        configurable.Mixin.__init__(self)
        self.db = HeraldDB()
        self.lastParts = {}
        self.lastHerald = {}

    def die(self):
        self.db.close()
        callbacks.Privmsg.die(self)
        configurable.Mixin.die(self)

    def doJoin(self, irc, msg):
        channel = msg.args[0]
        if self.configurables.get('heralding', channel):
            try:
                id = ircdb.users.getUserId(msg.prefix)
                herald = self.db.getHerald(id, channel)
            except KeyError:
                return
            now = time.time()
            throttle = self.configurables.get('throttle-time', channel)
            if now - self.lastHerald.get((id, channel), 0) > throttle:
                if (id, channel) in self.lastParts:
                   i = self.configurables.get('throttle-after-part', channel) 
                   if now - self.lastParts[(id, channel)] < i:
                       return
                self.lastHerald[(id, channel)] = now
                irc.queueMsg(ircmsgs.privmsg(channel, herald))

    def doPart(self, irc, msg):
        try:
            id = self._getId(msg.prefix)
            self.lastParts[(id, msg.args[0])] = time.time()
        except KeyError:
            pass

    def _getId(self, userNickHostmask):
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
            id = self._getId(userNickHostmask)
        except KeyError:
            irc.errorNoUser()
            return
        self.db.setHerald(id, channel, herald)
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
            id = self._getId(userNickHostmask)
        except KeyError:
            irc.errorNoUser()
            return
        self.db.delHerald(id, channel)
        irc.replySuccess()


Class = Herald

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
