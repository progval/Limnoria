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
Keeps statistics on who says what words in a channel.
"""

__revision__ = "$Id$"

import os
import csv
import string

import log
import conf
import utils
import world
import ircdb
import plugins
import ircutils
import privmsgs
import registry
import callbacks

conf.registerPlugin('WordStats')
conf.registerChannelValue(conf.supybot.plugins.WordStats,
    'rankingDisplay',
    registry.PositiveInteger(3, """Determines the maximum number of top users
    to show for a given wordstat when someone requests the wordstats for a
    particular word."""))

nonAlphaNumeric = filter(lambda s: not s.isalnum(), string.ascii)

class WordStatsDB(plugins.ChannelUserDB):
    def __init__(self, *args, **kwargs):
        self.channelWords = ircutils.IrcDict()
        plugins.ChannelUserDB.__init__(self, *args, **kwargs)

    def serialize(self, v):
        L = []
        for (word, count) in v.iteritems():
            L.append('%s:%s' % (word, count))
        return L

    def deserialize(self, channel, id, L):
        d = {}
        for s in L:
            (word, count) = s.split(':')
            count = int(count)
            d[word] = count
            if channel not in self.channelWords:
                self.channelWords[channel] = {}
            self.channelWords[channel].setdefault(word, 0)
            self.channelWords[channel][word] += count
        return d
    
    def getWordCount(self, channel, id, word):
        word = word.lower()
        return self[channel, id][word]

    def getUserWordCounts(self, channel, id):
        return self[channel, id].items()

    def getWords(self, channel):
        if channel not in self.channelWords:
            self.channelWords[channel] = {}
        L = self.channelWords[channel].keys()
        L.sort()
        return L
        
    def getTotalWordCount(self, channel, word):
        return self.channelWords[channel][word]

    def getNumUsers(self, channel):
        i = 0
        for ((chan, _), _) in self.iteritems():
            if chan == channel:
                i += 1
        return i

    def getTopUsers(self, channel, word, n):
        word = word.lower()
        L = [(id, d[word]) for ((chan, id), d) in self.iteritems()
             if channel == chan and word in d]
        utils.sortBy(lambda (_, i): i, L)
        L = L[-n:]
        L.reverse()
        return L

    def getRankAndNumber(self, channel, id, word):
        L = self.getTopUsers(channel, word, 0)
        n = 0
        for (someId, count) in L:
            n += 1
            if id == someId:
                return (n, count)
        raise KeyError

    def addWord(self, channel, word):
        word = word.lower()
        if channel not in self.channelWords:
            self.channelWords[channel] = {}
        self.channelWords[channel][word] = 0
        for ((chan, id), d) in self.iteritems():
            if channel == chan:
                if word not in d:
                    d[word] = 0

    def delWord(self, channel, word):
        word = word.lower()
        if word in self.channelWords[channel]:
            del self.channelWords[channel][word]
        for ((chan, id), d) in self.iteritems():
            if channel == chan:
                if word in d:
                    del d[word]
            
    def addMsg(self, msg):
        assert msg.command == 'PRIVMSG'
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            return
        (channel, text) = msg.args
        text = text.strip().lower()
        if not ircutils.isChannel(channel) or not text:
            return
        msgwords = [s.strip(nonAlphaNumeric) for s in text.split()]
        if channel not in self.channelWords:
            self.channelWords[channel] = {}
        for word in self.channelWords[channel]:
            for msgword in msgwords:
                if msgword == word:
                    self.channelWords[channel][word] += 1
                    if (channel, id) not in self:
                        self[channel, id] = {}
                    if word not in self[channel, id]:
                        self[channel, id][word] = 0
                    self[channel, id][word] += 1
                

filename=os.path.join(conf.supybot.directories.data(), 'WordStats.db')
class WordStats(callbacks.Privmsg):
    noIgnore = True
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = WordStatsDB(filename)
        world.flushers.append(self.db.flush)

    def die(self):
        if self.db.flush in world.flushers:
            world.flushers.remove(self.db.flush)
        self.db.close()
        callbacks.Privmsg.die(self)

    def doPrivmsg(self, irc, msg):
        self.db.addMsg(msg)
        
    def add(self, irc, msg, args):
        """[<channel>] <word>

        Keeps stats on <word> in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        word = privmsgs.getArgs(args)
        word = word.strip()
        if word.strip(nonAlphaNumeric) != word:
            irc.error('<word> must not contain non-alphanumeric chars.')
            return
        word = word.lower()
        self.db.addWord(channel, word)
        irc.replySuccess()

    def remove(self, irc, msg, args):
        """[<channel>] <word>

        Removes <word> from the list of words being tracked.  If <channel> is
        not specified, uses current channel.
        """
        channel = privmsgs.getChannel(msg, args)
        word = privmsgs.getArgs(args)
        words = self.db.getWords(channel)
        if words:
            if word in words:
                self.db.delWord(channel, word)
                irc.replySuccess()
            else:
                irc.error('%r doesn\'t look like a word I am keeping stats '
                          'on.' % word)
                return
        else:
            irc.error('I am not currently keeping any word stats.')
            return

    def wordstats(self, irc, msg, args):
        """[<channel>] [<user>] [<word>]

        With no arguments, returns the list of words that are being monitored
        for stats.  With <user> alone, returns all the stats for that user.
        With <word> alone, returns the top users for that word.  With <user>
        and <word>, returns that user's stat for that word. <channel> is only
        needed if not said in the channel.  (Note: if only one of <user> or
        <word> is given, <word> is assumed first and only if no stats are
        available for that word, do we assume it's <user>.)
        """
        channel = privmsgs.getChannel(msg, args)
        (arg1, arg2) = privmsgs.getArgs(args, required=0, optional=2)
        if not arg1 and not arg2:
            words = self.db.getWords(channel)
            if words:
                commaAndify = utils.commaAndify
                s = 'I am currently keeping stats for %s.' % commaAndify(words)
                irc.reply(s)
            else:
                irc.reply('I am not currently keeping any word stats.')
                return
        elif arg1 and arg2:
            user, word = (arg1, arg2)
            try:
                id = ircdb.users.getUserId(user)
            except KeyError: # Maybe it was a nick.  Check the hostmask.
                try:
                    hostmask = irc.state.nickToHostmask(user)
                    id = ircdb.users.getUserId(hostmask)
                except KeyError:
                    irc.errorNoUser()
                    return
            try:
                count = self.db.getWordCount(channel, id, word)
            except KeyError:
                irc.error('I\'m not keeping stats on %r.' % word)
                return
            if count:
                s = '%s has said %r %s.' % \
                    (user, word, utils.nItems('time', count))
                irc.reply(s)
            else:
                irc.error('%s has never said %r.' % (user, word))
        elif arg1 in self.db.getWords(channel):
            word = arg1
            total = self.db.getTotalWordCount(channel, word)
            n = self.registryValue('rankingDisplay', channel)
            try:
                id = ircdb.users.getUserId(msg.prefix)
                (rank, number) = self.db.getRankAndNumber(channel, id, word)
            except (KeyError, ValueError):
                id = None
                rank = None
                number = None
            ers = '%rer' % word
            L = []
            for (userid, count) in self.db.getTopUsers(channel, word, n):
                if userid == id:
                    rank = None
                try:
                    username = ircdb.users.getUser(userid).name
                except KeyError:
                    irc.error('Odd, I have a user in my WordStats database '
                              'that doesn\'t exist in the user database.')
                    return
                L.append('%s: %s' % (username, count))
            ret = 'Top %s (out of a total of %s seen):' % \
                  (utils.nItems(ers, len(L)), utils.nItems(repr(word), total))
            users = self.db.getNumUsers(channel)
            if rank is not None:
                s = '  You are ranked %s out of %s with %s.' % \
                    (rank, utils.nItems(ers, users),
                     utils.nItems(repr(word), number))
            else:
                s = ''
            ret = '%s %s.%s' % (ret, utils.commaAndify(L), s)
            irc.reply(ret)
        else:
            user = arg1
            try:
                id = ircdb.users.getUserId(user)
            except KeyError:
                irc.error('%r doesn\'t look like a word I\'m keeping stats '
                          'on or a user in my database.' % user)
                return
            try:
                L = ['%r: %s' % (word, count)
                     for (word,count) in self.db.getUserWordCounts(channel,id)]
                if L:
                    L.sort()
                    irc.reply(utils.commaAndify(L))
                else:
                    irc.error('%r doesn\'t look like a word I\'m keeping stats'
                              ' on or a user in my database.' % user)
                    return
            except KeyError:
                irc.error('I have no word stats for that person.')
Class = WordStats

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
