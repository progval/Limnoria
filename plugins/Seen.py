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
Keeps track of the last time a user was seen on a channel.
"""

__revision__ = "$Id$"

import plugins

import os
import re
import sets
import time
import getopt
import string
from itertools import imap, ifilter

import log
import conf
import utils
import world
import ircdb
import ircmsgs
import plugins
import ircutils
import privmsgs
import registry
import callbacks

class SeenDB(plugins.ChannelUserDatabase):
    def serialize(self, v):
        return list(v)

    def deserialize(self, L):
        (seen, saying) = L
        return (float(seen), saying)
    
    def update(self, channel, nickOrId, saying):
        seen = time.time()
        self[channel, nickOrId] = (seen, saying)

    def seen(self, channel, nickOrId):
        return self[channel, nickOrId]

filename = os.path.join(conf.supybot.directories.data(), 'Seen.db')
            
class Seen(callbacks.Privmsg):
    noIgnore = True
    def __init__(self):
        self.db = SeenDB(filename)
        world.flushers.append(self.db.flush)
        callbacks.Privmsg.__init__(self)

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        else:
            self.log.debug('Odd, no flush in flushers: %r', world.flushers)
        self.db.close()
        callbacks.Privmsg.die(self)
        
    def doPrivmsg(self, irc, msg):
        if ircutils.isChannel(msg.args[0]):
            said = ircmsgs.prettyPrint(msg)
            channel = msg.args[0]
            self.db.update(channel, msg.nick, said)
            try:
                id = ircdb.users.getUserId(msg.prefix)
                self.db.update(channel, id, said)
            except KeyError:
                pass # Not in the database.
        
    def seen(self, irc, msg, args):
        """[<channel>] [--user] <name>

        Returns the last time <name> was seen and what <name> was last seen
        saying.  --user will look for user <name> instead of using <name> as
        a nick (registered users, remember, can be recognized under any number
        of nicks) <channel> is only necessary if the message isn't sent on the
        channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        (optlist, rest) = getopt.getopt(args, '', ['user'])
        name = privmsgs.getArgs(rest)
        nickOrId = name
        if ('--user', '') in optlist:
            try:
                nickOrId = ircdb.users.getUserId(name)
            except KeyError:
                try:
                    hostmask = irc.state.nickToHostmask(name)
                    nickOrId = ircdb.users.getUserId(hostmask)
                except KeyError:
                    irc.errorNoUser()
                    return
        try:
            (when, said) = self.db.seen(channel, nickOrId)
            irc.reply('%s was last seen here %s ago saying: %s' % 
                      (name, utils.timeElapsed(time.time()-when), said))
        except KeyError:
            irc.reply('I have not seen %s.' % name)


Class = Seen

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
