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
Keeps track of the last time a user was seen on a channel.
"""

import supybot

__revision__ = "$Id$"
__contributors__ = {
    supybot.authors.skorobeus: ['wildcard support'],
    }

import os
import re
import sets
import time
import getopt
import string
from itertools import imap, ifilter

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks

class IrcStringAndIntDict(utils.InsensitivePreservingDict):
    def key(self, x):
        if isinstance(x, int):
            return x
        else:
            return ircutils.toLower(x)

ANY = '<any>'

class SeenDB(plugins.ChannelUserDB):
    IdDict = IrcStringAndIntDict
    def serialize(self, v):
        return list(v)

    def deserialize(self, channel, id, L):
        (seen, saying) = L
        return (float(seen), saying)

    def update(self, channel, nickOrId, saying):
        seen = time.time()
        self[channel, nickOrId] = (seen, saying)
        self[channel, '<last>'] = (seen, saying)
    
    def seenWildcard(self, channel, nick):
        nicks = []
        nickRe = re.compile('.*'.join(nick.split('*')), re.I)
        for (searchChan, searchNick) in self.keys():
            #print 'chan: %s ... nick: %s' % (searchChan, searchNick)
            if isinstance(searchNick, int):
                # We need to skip the reponses that are keyed by id as they
                # apparently duplicate the responses for the same person that
                # are keyed by nick-string
                continue
            if ircutils.strEqual(searchChan, channel):
                try:
                    s = nickRe.match(searchNick).group()
                except AttributeError:
                    continue
                nicks.append(s)
        L = [[nick, self.seen(channel, nick)] for nick in nicks]
        def negativeTime(x):
            return -x[1][0]
        utils.sortBy(negativeTime, L)
        return L

    def seen(self, channel, nickOrId):
        return self[channel, nickOrId]

filename = conf.supybot.directories.data.dirize('Seen.db')

class Seen(callbacks.Privmsg):
    noIgnore = True
    def __init__(self):
        self.db = SeenDB(filename)
        world.flushers.append(self.db.flush)
        self.__parent = super(Seen, self)
        self.__parent.__init__()

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        else:
            self.log.debug('Odd, no flush in flushers: %r', world.flushers)
        self.db.close()
        self.__parent.die()

    def doPrivmsg(self, irc, msg):
        if irc.isChannel(msg.args[0]):
            said = ircmsgs.prettyPrint(msg)
            channel = plugins.getChannel(msg.args[0])
            self.db.update(channel, msg.nick, said)
            self.db.update(ANY + channel, msg.nick, said)
            try:
                id = ircdb.users.getUserId(msg.prefix)
                self.db.update(channel, id, said)
                self.db.update(ANY + channel, id, said)
            except KeyError:
                pass # Not in the database.

    # non-PRIVMSG which have a channel association
    def doNonPrivmsgWithChannel(self, irc, msg):
        if irc.isChannel(msg.args[0]):
            said = ircmsgs.prettyPrint(msg)
            channel = ANY + plugins.getChannel(msg.args[0])
            self.db.update(channel, msg.nick, said)
            try:
                id = ircdb.users.getUserId(msg.prefix)
                self.db.update(channel, id, said)
            except KeyError:
                pass # Not in the database.
    doJoin = doNonPrivmsgWithChannel
    doKick = doNonPrivmsgWithChannel
    doMode = doNonPrivmsgWithChannel
    doPart = doNonPrivmsgWithChannel
    doTopic = doNonPrivmsgWithChannel
    doNotice = doNonPrivmsgWithChannel

    # non-PRIVMSG which don't have a channel association
    def doNonPrivmsg(self, irc, msg):
        said = ircmsgs.prettyPrint(msg)
        self.db.update(ANY, msg.nick, said)
        try:
            id = ircdb.users.getUserId(msg.prefix)
            self.db.update(ANY, id, said)
        except KeyError:
            pass # Not in the database.
    doNick = doNonPrivmsg
    doQuit = doNonPrivmsg

    def seen(self, irc, msg, args, channel, optlist, name):
        """[<channel>] [--any] <nick>

        Returns the last time <nick> was seen and what <nick> was last seen
        saying. * can be used as a wildcard in the nick.  If --any is
        specified, also search for non-PRIVMSG activity.  <channel> is only
        necessary if the message isn't sent on the channel itself.
        """
        any = False
        for (opt, _) in optlist:
            if opt == 'any':
                any = True
        try:
            results = []
            if '*' in name:
                if not any:
                    results = self.db.seenWildcard(channel, name)
                else:
                    results = self.db.seenWildcard(ANY + channel, name)
            else:
                if not any:
                    results = [[name, self.db.seen(channel, name)]]
                else:
                    results = [[name, self.db.seen(ANY + channel, name)]]
            if len(results) == 1:
                (nick, info) = results[0]
                (when, said) = info
                irc.reply('%s was last seen in %s %s ago saying: %s' %
                          (nick, channel, utils.timeElapsed(time.time()-when),
                           said))
            elif len(results) > 1:
                L = []
                for (nick, info) in results:
                    (when, said) = info
                    L.append('%s (%s ago)' % 
                            (nick, utils.timeElapsed(time.time()-when)))
                irc.reply('%s could be %s' %
                          (name, utils.commaAndify(L, And='or')))
            else:
                irc.reply('I haven\'t seen anyone matching %s.' % name)
        except KeyError:
            irc.reply('I have not seen %s.' % name)
    # Have to use 'something' instead of 'nick' because * isn't necessarily a
    # valid character in a nick
    seen = wrap(seen, ['channeldb', getopts({'any': ''}), 'something'])

    def last(self, irc, msg, args, channel):
        """[<channel>]

        Returns the last thing said in <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        try:
            (when, said) = self.db.seen(channel, '<last>')
            irc.reply('Someone was last seen in %s %s ago saying: %s' %
                      (channel, utils.timeElapsed(time.time()-when), said))
        except KeyError:
            irc.reply('I have never seen anyone.')
    last = wrap(last, ['channeldb'])

    def user(self, irc, msg, args, channel, optlist, user):
        """[<channel>] [--any] <name>

        Returns the last time <name> was seen and what <name> was last seen
        saying.  This looks up <name> in the user seen database, which means
        that it could be any nick recognized as user <name> that was seen.  If
        --any is specified, also search for non-PRIVMSG activity by <name>.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        any = False
        for (opt, arg) in optlist:
            if opt == 'any':
                any = True
        try:
            if not any:
                (when, said) = self.db.seen(channel, user.id)
            else:
                (when, said) = self.db.seen(ANY + channel, user.id)
            irc.reply('%s was last seen in %s %s ago saying: %s' %
                      (user.name, channel, utils.timeElapsed(time.time()-when),
                       said))
        except KeyError:
            irc.reply('I have not seen %s.' % user.name)
    user = wrap(user, ['channeldb', getopts({'any': ''}), 'otherUser'])


Class = Seen

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
