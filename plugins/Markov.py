#!/usr/bin/env python

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
Silently listens to a channel, building an SQL database of Markov Chains for
later hijinks.  To read more about Markov Chains, check out
<http://www.cs.bell-labs.com/cm/cs/pearls/sec153.html>.  When the database is
large enough, you can have it make fun little random messages from it.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import sets
import Queue
import anydbm
import random
import os.path
import threading

import supybot.world as world
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks

class MarkovDBInterface(object):
    def close(self):
        pass

    def addPair(self, channel, first, second, follower,
                isFirst=False, isLast=False):
        pass

    def getFirstPair(self, channel):
        pass

    def getPair(self, channel, first, second):
        # Returns (follower, last) tuple.
        pass

class SqliteMarkovDB(object):
    def addPair(self, channel, first, second, follower,
                isFirst=False, isLast=False):
        pass

    def getFirstPair(self, channel):
        pass

    def getFollower(self, channel, first, second):
        # Returns (follower, last) tuple.
        pass


class DbmMarkovDB(object):
    def __init__(self):
        self.dbs = ircutils.IrcDict()

    def close(self):
        for db in self.dbs.values():
            db.close()

    def _getDb(self, channel):
        if channel not in self.dbs:
            # Stupid anydbm seems to append .db to the end of this.
            filename = plugins.makeChannelFilename('DbmMarkovDB', channel)
            # To keep the code simpler for addPair, I decided not to make
            # self.dbs[channel]['firsts'] and ['lasts'].  Instead, we'll pad
            # the words list being sent to addPair such that ['\n \n'] will be
            # ['firsts'] and ['\n'] will be ['lasts'].  This also means isFirst
            # and isLast aren't necessary, but they'll be left alone in case
            # one of the other Db formats uses them or someone decides that I
            # was wrong and changes my code.
            self.dbs[channel] = anydbm.open(filename, 'c')
        return self.dbs[channel]

    def _flush(self, db):
        if hasattr(db, 'sync'):
            db.sync()
        if hasattr(db, 'flush'):
            db.flush()

    def addPair(self, channel, first, second, follower,
                isFirst=False, isLast=False):
        db = self._getDb(channel)
        combined = self._combine(first, second)
        if db.has_key(combined): # EW!
            db[combined] = ' '.join([db[combined], follower])
        else:
            db[combined] = follower
        if follower == '\n':
            if '\n' in db:
                db['\n'] = ' '.join([db['\n'], second])
            else:
                db['\n'] = second
        self._flush(db)

    def getFirstPair(self, channel):
        db = self._getDb(channel)
        firsts = db['\n \n'].split()
        if firsts:
            if firsts:
                return ('\n', random.choice(firsts))
            else:
                raise KeyError, 'No firsts for %s.' % channel
        else:
            raise KeyError, 'No firsts for %s.' % channel

    def _combine(self, first, second):
        return '%s %s' % (first, second)

    def getFollower(self, channel, first, second):
        db = self._getDb(channel)
        followers = db[self._combine(first, second)]
        follower = random.choice(followers.split(' '))
        return (follower, follower == '\n')

    def firsts(self, channel):
        db = self._getDb(channel)
        if '\n \n' in db:
            return len(sets.Set(db['\n \n'].split()))
        else:
            return 0

    def lasts(self, channel):
        db = self._getDb(channel)
        if '\n' in db:
            return len(sets.Set(db['\n'].split()))
        else:
            return 0

    def pairs(self, channel):
        db = self._getDb(channel)
        pairs = [k for k in db.keys() if '\n' not in k]
        return len(pairs)

    def follows(self, channel):
        db = self._getDb(channel)
        follows = [len(v.split()) for (k,v) in db.iteritems() if '\n' not in k]
        return sum(follows)

def MarkovDB():
    return DbmMarkovDB()

class MarkovWorkQueue(threading.Thread):
    def __init__(self, *args, **kwargs):
        name = 'Thread #%s (MarkovWorkQueue)' % world.threadsSpawned
        world.threadsSpawned += 1
        threading.Thread.__init__(self, name=name)
        self.db = MarkovDB(*args, **kwargs)
        self.q = Queue.Queue()
        self.killed = False
        self.setDaemon(True)
        self.start()

    def die(self):
        self.killed = True
        self.q.put(None)

    def enqueue(self, f):
        self.q.put(f)

    def run(self):
        while not self.killed:
            f = self.q.get()
            if f is not None:
                f(self.db)
        self.db.close()

class Markov(callbacks.Privmsg):
    def __init__(self):
        self.q = MarkovWorkQueue()
        callbacks.Privmsg.__init__(self)

    def die(self):
        self.q.die()

    def tokenize(self, m):
        if ircmsgs.isAction(m):
            return ircmsgs.unAction(m).split()
        elif ircmsgs.isCtcp(m):
            return []
        else:
            return m.args[1].split()

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        if ircutils.isChannel(channel):
            words = self.tokenize(msg)
            words.insert(0, '\n')
            words.insert(0, '\n')
            words.append('\n')
            # This shouldn't happen often (CTCP messages being the possible exception)
            if not words or len(words) == 3:
                return
            def doPrivmsg(db):
                for (first, second, follower) in window(words, 3):
                    db.addPair(channel, first, second, follower)
            self.q.enqueue(doPrivmsg)

    def markov(self, irc, msg, args):
        """[<channel>] [word1 word2]

        Returns a randomly-generated Markov Chain generated sentence from the
        data kept on <channel> (which is only necessary if not sent in the
        channel itself).  If word1 and word2 are specified, they will be used
        to start the Markov chain.
        """
        channel = privmsgs.getChannel(msg, args)
        (word1, word2) = privmsgs.getArgs(args, required=0, optional=2)
        def markov(db):
            if word1 and word2:
                givenArgs = True
                words = [word1, word2]
            else:
                givenArgs = False
                try:
                    # words is of the form ['\r', word]
                    words = list(db.getFirstPair(channel))
                except KeyError:
                    irc.error('I don\'t have any first pairs for %s.' %channel)
                    return
            follower = words[-1]
            last = False
            resp = []
            while not last:
                resp.append(follower)
                try:
                    (follower,last) = db.getFollower(channel, words[-2],
                                                     words[-1])
                except KeyError:
                    irc.error('I found a broken link in the Markov chain.  '
                              'Maybe I received two bad links to start the '
                              'chain.')
                    return
                words.append(follower)
            if givenArgs:
                irc.reply(' '.join(words))
            else:
                irc.reply(' '.join(resp))
        self.q.enqueue(markov)

    def firsts(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's first links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        def firsts(db):
            s = 'There are %s firsts in my Markov database for %s.'
            irc.reply(s % (db.firsts(channel), channel))
        self.q.enqueue(firsts)

    def lasts(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's last links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        def lasts(db):
            s = 'There are %s lasts in my Markov database for %s.'
            irc.reply(s % (db.lasts(channel), channel))
        self.q.enqueue(lasts)

    def pairs(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's chain links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        def pairs(db):
            s = 'There are %s pairs in my Markov database for %s.'
            irc.reply(s % (db.pairs(channel), channel))
        self.q.enqueue(pairs)

    def follows(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's third links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        def follows(db):
            s = 'There are %s follows in my Markov database for %s.'
            irc.reply(s % (db.follows(channel), channel))
        self.q.enqueue(follows)


Class = Markov

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
