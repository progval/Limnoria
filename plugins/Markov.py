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
Silently listens to a channel, building an SQL database of Markov Chains for
later hijinks.  To read more about Markov Chains, check out
<http://www.cs.bell-labs.com/cm/cs/pearls/sec153.html>.  When the database is
large enough, you can have it make fun little random messages from it.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import Queue
import anydbm
import random
import os.path
import threading

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
            self.dbs[channel] = anydbm.open('%s-DbmMarkovDB' % channel, 'c')
            self.dbs[channel]['lasts'] = ''
            self.dbs[channel]['firsts'] = ''
        return self.dbs[channel]

    def _addFirst(self, db, combined):
        db['firsts'] = db['firsts'] + (combined + '\n')

    def _addLast(self, db, second, follower):
        combined = self._combine(second, follower)
        db['lasts'] = db['lasts'] + (combined + '\n')

    def addPair(self, channel, first, second, follower,
                isFirst=False, isLast=False):
        db = self._getDb(channel)
        combined = self._combine(first, second)
        if isFirst:
            self._addFirst(db, combined)
        elif isLast:
            self._addLast(db, second, follower)
        else:
            if db.has_key(combined): # EW!
                db[combined] = db[combined] + (' ' + follower)
            else:
                db[combined] = follower
        #db.flush()

    def getFirstPair(self, channel):
        db = self._getDb(channel)
        firsts = db['firsts'].splitlines()
        if firsts:
            firsts.pop() # Empty line.
            if firsts:
                return random.choice(firsts).split()
            else:
                raise KeyError, 'No firsts for %s.' % channel
        else:
            raise KeyError, 'No firsts for %s.' % channel

    def _combine(self, first, second):
        return '%s %s' % (first, second)

    def getFollower(self, channel, first, second):
        db = self._getDb(channel)
        followers = db[self._combine(first, second)]
        follower = random.choice(followers.split())
        if self._combine(second, follower) in db['lasts']:
            last = True
        else:
            last = False
        return (follower, last)

def MarkovDB():
    return DbmMarkovDB()

class MarkovWorkQueue(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.db = MarkovDB(*args, **kwargs)
        self.q = Queue.Queue()
        self.killed = False
        self.setDaemon(True)
        self.start()

    def die(self):
        self.killed = True

    def enqueue(self, f):
        self.q.put(f)

    def run(self):
        while not self.killed:
            f = self.q.get()
            f(self.db)
        self.db.close()
        
class Markov(callbacks.Privmsg):
    def __init__(self):
        self.q = MarkovWorkQueue()
        callbacks.Privmsg.__init__(self)
        
    def die(self):
        self.q.die()
        
    def tokenize(self, s):
        # XXX: Should this be smarter?
        return s.split()

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0]
        if ircutils.isChannel(channel):
            words = self.tokenize(msg.args[1])
            if len(words) >= 3:
                def doPrivmsg(db):
                    db.addPair(channel, words[0], words[1], words[2],
                                    isFirst=True)
                    db.addPair(channel, words[-3], words[-2], words[-1],
                                    isLast=True)
                    del words[0] # Remove first.
                    del words[-1] # Remove last.
                    for (first, second, follower) in window(words, 3):
                        db.addPair(channel, first, second, follower)
                self.q.enqueue(doPrivmsg)
        
    def markov(self, irc, msg, args):
        """[<channel>]

        Returns a randomly-generated Markov Chain generated sentence from the
        data kept on <channel> (which is only necessary if not sent in the
        channel itself).
        """
        channel = privmsgs.getChannel(msg, args)
        def markov(db):
            try:
                words = list(db.getFirstPair(channel))
            except KeyError:
                irc.error('I don\'t have any first pairs for %s.' % channel)
                return
            last = False
            while not last:
                (follower,last) = db.getFollower(channel, words[-2], words[-1])
                words.append(follower)
            irc.reply(' '.join(words))
        self.q.enqueue(markov)


Class = Markov
