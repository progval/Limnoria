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
Silently listens to a channel, building a database of Markov Chains for later
hijinks.  To read more about Markov Chains, check out
<http://www.cs.bell-labs.com/cm/cs/pearls/sec153.html>.  When the database is
large enough, you can have it make fun little random messages from it.
"""

__revision__ = "$Id$"

import plugins

import anydbm
import random
import os.path

import conf
import world
import ircmsgs
import ircutils
import privmsgs
import callbacks


class Markov(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.dbCache = ircutils.IrcDict()

    def die(self):
        for db in self.dbCache:
            try:
                db.close()
            except:
                continue

    # FIXME: database independency? (All of these private functions)
    def _getDb(self, channel):
        channel = channel.lower()
        if not channel in self.dbCache:
            filename = '%s-Markov.db' % channel
            filename = os.path.join(conf.supybot.directories.data(), filename)
            self.dbCache[channel] = anydbm.open(filename, 'c')
        return self.dbCache[channel]

    def _getNumberOfPairs(self, db):
        # Minus one, because we have a key storing the first pairs.
        return len(db) - 1

    def _getNumberOfFirstPairs(self, db):
        try:
            pairs = db[''].split()
        except KeyError:
            return 0
        return len(pairs)

    def _getFirstPair(self, db):
        try:
            pairs = db[''].split()
        except KeyError:
            raise ValueError('No starting pairs in the database.')
        pair = random.choice(pairs)
        return pair.split('\x00', 1)

    def _getFollower(self, db, first, second):
        pair = '%s %s' % (first, second)
        try:
            followers = db[pair].split()
        except KeyError:
            return '\x00'
        return random.choice(followers)

    def _addFirstPair(self, db, first, second):
        pair = '%s\x00%s' % (first, second)
        try:
            startingPairs = db['']
        except KeyError:
            startingPairs = ''
        db[''] = '%s%s ' % (startingPairs, pair)

    def _addPair(self, db, first, second, follower):
        pair = '%s %s' % (first, second)
        try:
            followers = db[pair]
        except KeyError:
            followers = ''
        db[pair] = '%s%s ' % (followers, follower)

    def doPrivmsg(self, irc, msg):
        if not ircutils.isChannel(msg.args[0]):
            return
        channel = msg.args[0]
        db = self._getDb(channel)
        if ircmsgs.isAction(msg):
            words = ircmsgs.unAction(msg).split()
            words.insert(0, '\x00nick')
            #words.insert(0, msg.nick)
        else:
            words = msg.args[1].split()
        isFirst = True
        for (first, second, follower) in window(words, 3):
            if isFirst:
                self._addFirstPair(db, first, second)
                isFirst = False
            self._addPair(db, first, second, follower)
        if not isFirst: # i.e., if the loop iterated at all.
            self._addPair(db, second, follower, '\x00')

    _maxMarkovLength = 80
    _minMarkovLength = 7
    def markov(self, irc, msg, args):
        """[<channel>]

        Returns a randomly-generated Markov Chain generated sentence from the
        data kept on <channel> (which is only necessary if not sent in the
        channel itself).
        """
        channel = privmsgs.getChannel(msg, args)
        db = self._getDb(channel)
        try:
            pair = self._getFirstPair(db)
        except ValueError:
            irc.error('I have no records for this channel.')
            return
        words = [pair[0], pair[1]]
        while len(words) < self._maxMarkovLength:
            follower = self._getFollower(db, words[-2], words[-1])
            if follower == '\x00':
                if len(words) < self._minMarkovLength:
                    pair = self._getFirstPair(db)
                    words = [pair[0], pair[1]]
                else:
                    break
            else:
                words.append(follower)
        if words[0] == '\x00nick':
            words[0] = choice(irc.state.channels[channel].users)
        irc.reply(' '.join(words))

    def pairs(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's chain links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self._getDb(channel)
        n = self._getNumberOfPairs(db)
        s = 'There are %s pairs in my Markov database for %s' % (n, channel)
        irc.reply(s)

    def firsts(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's first links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self._getDb(channel)
        n = self._getNumberOfFirstPairs(db)
        s = 'There are %s first pairs in my Markov database for %s'%(n,channel)
        irc.reply(s)

#    def follows(self, irc, msg, args):
#        """[<channel>]
#
#        Returns the number of Markov's third links in the database for
#        <channel>.
#        """
#        channel = privmsgs.getChannel(msg, args)
#        db = self._getDb(channel)
#        cursor = db.cursor()
#        cursor.execute("""SELECT COUNT(*) FROM follows""")
#        n = int(cursor.fetchone()[0])
#        s = 'There are %s follows in my Markov database for %s' % (n, channel)
#        irc.reply(s)

#    def lasts(self, irc, msg, args):
#        """[<channel>]
#
#        Returns the number of Markov's last links in the database for
#        <channel>.
#        """
#        channel = privmsgs.getChannel(msg, args)
#        db = self._getDb(channel)
#        cursor = db.cursor()
#        cursor.execute("""SELECT COUNT(*) FROM follows WHERE word ISNULL""")
#        n = int(cursor.fetchone()[0])
#        s = 'There are %s lasts in my Markov database for %s' % (n, channel)
#        irc.reply(s)


Class = Markov

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
