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

import re
import time

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class IrcStringAndIntDict(utils.InsensitivePreservingDict):
    def key(self, x):
        if isinstance(x, int):
            return x
        else:
            return ircutils.toLower(x)

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
        nicks = ircutils.IrcSet()
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
                nicks.add(s)
        L = [[nick, self.seen(channel, nick)] for nick in nicks]
        def negativeTime(x):
            return -x[1][0]
        utils.sortBy(negativeTime, L)
        return L

    def seen(self, channel, nickOrId):
        return self[channel, nickOrId]

filename = conf.supybot.directories.data.dirize('Seen.db')
anyfilename = conf.supybot.directories.data.dirize('Seen.any.db')

class Seen(callbacks.Plugin):
    noIgnore = True
    def __init__(self, irc):
        self.__parent = super(Seen, self)
        self.__parent.__init__(irc)
        self.db = SeenDB(filename)
        self.anydb = SeenDB(anyfilename)
        self.lastmsg = {}
        self.ircstates = {}
        world.flushers.append(self.db.flush)

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        else:
            self.log.debug('Odd, no flush in flushers: %r', world.flushers)
        self.db.close()
        if self.anydb.flush in world.flushers:
            world.flushers.remove(self.anydb.flush)
        else:
            self.log.debug('Odd, no flush in flushers: %r', world.flushers)
        self.anydb.close()
        self.__parent.die()

    def __call__(self, irc, msg):
        try:
            if irc not in self.ircstates:
                self._addIrc(irc)
            self.ircstates[irc].addMsg(irc, self.lastmsg[irc])
        finally:
            self.lastmsg[irc] = msg
        self.__parent.__call__(irc, msg)

    def _addIrc(self, irc):
        # Let's just be extra-special-careful here.
        if irc not in self.ircstates:
            self.ircstates[irc] = irclib.IrcState()
        if irc not in self.lastmsg:
            self.lastmsg[irc] = ircmsgs.ping('this is just a fake message')
        if not world.testing:
            for channel in irc.state.channels:
                irc.queueMsg(ircmsgs.who(channel))
                irc.queueMsg(ircmsgs.names(channel))

    def doPrivmsg(self, irc, msg):
        if irc.isChannel(msg.args[0]):
            channel = msg.args[0]
            said = ircmsgs.prettyPrint(msg)
            self.db.update(channel, msg.nick, said)
            self.anydb.update(channel, msg.nick, said)
            try:
                id = ircdb.users.getUserId(msg.prefix)
                self.db.update(channel, id, said)
                self.anydb.update(channel, id, said)
            except KeyError:
                pass # Not in the database.

    def doPart(self, irc, msg):
        channel = msg.args[0]
        said = ircmsgs.prettyPrint(msg)
        self.anydb.update(channel, msg.nick, said)
        try:
            id = ircdb.users.getUserId(msg.prefix)
            self.anydb.update(channel, id, said)
        except KeyError:
            pass # Not in the database.
    doJoin = doPart
    doKick = doPart

    def doQuit(self, irc, msg):
        said = ircmsgs.prettyPrint(msg)
        if irc not in self.ircstates:
            return
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            id = None # Not in the database.
        for channel in self.ircstates[irc].channels:
            if msg.nick in self.ircstates[irc].channels[channel].users:
                self.anydb.update(channel, msg.nick, said)
                if id is not None:
                    self.anydb.update(channel, id, said)
    doNick = doQuit

    def doMode(self, irc, msg):
        # Filter out messages from network Services
        if msg.nick:
            self.doQuit(irc, msg)
    doTopic = doMode

    def _seen(self, irc, channel, name, any=False):
        if any:
            db = self.anydb
        else:
            db = self.db
        try:
            results = []
            if '*' in name:
                results = db.seenWildcard(channel, name)
            else:
                results = [[name, db.seen(channel, name)]]
            if len(results) == 1:
                (nick, info) = results[0]
                (when, said) = info
                irc.reply(format('%s was last seen in %s %s ago: %s',
                                 nick, channel,
                                 utils.timeElapsed(time.time()-when), said))
            elif len(results) > 1:
                L = []
                for (nick, info) in results:
                    (when, said) = info
                    L.append(format('%s (%s ago)', nick,
                                    utils.timeElapsed(time.time()-when)))
                irc.reply(format('%s could be %L', name, (L, 'or')))
            else:
                irc.reply(format('I haven\'t seen anyone matching %s.', name))
        except KeyError:
            irc.reply(format('I have not seen %s.', name))

    def seen(self, irc, msg, args, channel, name):
        """[<channel>] <nick>

        Returns the last time <nick> was seen and what <nick> was last seen
        saying. <channel> is only necessary if the message isn't sent on the
        channel itself.
        """
        self._seen(irc, channel, name)
    seen = wrap(seen, ['channel', 'nick'])

    def any(self, irc, msg, args, channel, optlist, name):
        """[<channel>] [--user <name>] [<nick>]

        Returns the last time <nick> was seen and what <nick> was last seen
        doing.  This includes any form of activity, instead of just PRIVMSGs.
        If <nick> isn't specified, returns the last activity seen in
        <channel>.  If --user is specified, looks up name in the user database
        and returns the last time user was active in <channel>.  <channel> is
        only necessary if the message isn't sent on the channel itself.
        """
        if name and optlist:
            raise callbacks.ArgumentError
        elif name:
            self._seen(irc, channel, name, any=True)
        elif optlist:
            for (option, arg) in optlist:
                if option == 'user':
                    user = arg
            self._user(irc, channel, user, any=True)
        else:
            self._last(irc, channel, any=True)
    any = wrap(any, ['channel', getopts({'user': 'otherUser'}),
                     additional('nick')])

    def _last(self, irc, channel, any=False):
        if any:
            db = self.anydb
        else:
            db = self.db
        try:
            (when, said) = db.seen(channel, '<last>')
            irc.reply(format('Someone was last seen in %s %s ago: %s',
                             channel, utils.timeElapsed(time.time()-when),
                             said))
        except KeyError:
            irc.reply('I have never seen anyone.')

    def last(self, irc, msg, args, channel):
        """[<channel>]

        Returns the last thing said in <channel>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        self._last(irc, channel)
    last = wrap(last, ['channel'])

    def _user(self, irc, channel, user, any=False):
        if any:
            db = self.anydb
        else:
            db = self.db
        try:
            (when, said) = db.seen(channel, user.id)
            irc.reply(format('%s was last seen in %s %s ago: %s',
                             user.name, channel,
                             utils.timeElapsed(time.time()-when), said))
        except KeyError:
            irc.reply(format('I have not seen %s.', user.name))

    def user(self, irc, msg, args, channel, user):
        """[<channel>] <name>

        Returns the last time <name> was seen and what <name> was last seen
        saying.  This looks up <name> in the user seen database, which means
        that it could be any nick recognized as user <name> that was seen.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        self._user(irc, channel, user)
    user = wrap(user, ['channel', 'otherUser'])

Class = Seen

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
