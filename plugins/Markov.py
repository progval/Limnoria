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
Silently listens to a channel, building a database of Markov Chains for
later hijinks.  To read more about Markov Chains, check out
<http://www.cs.bell-labs.com/cm/cs/pearls/sec153.html>.  When the database is
large enough, you can have it make fun little random messages from it.
"""

__revision__ = "$Id$"

import supybot.plugins as plugins

import sets
import time
import Queue
import anydbm
import random
import os.path
import threading

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.schedule as schedule
import supybot.callbacks as callbacks

conf.registerPlugin('Markov')
conf.registerChannelValue(conf.supybot.plugins.Markov, 'ignoreBotCommands',
    registry.Boolean(False, """Determines whether messages addressed to the
    bot are ignored."""))
conf.registerChannelValue(conf.supybot.plugins.Markov, 'minChainLength',
    registry.PositiveInteger(1, """Determines the length of the smallest chain
    which the markov command will generate."""))
conf.registerChannelValue(conf.supybot.plugins.Markov, 'maxAttempts',
    registry.PositiveInteger(1, """Determines the maximum number of times the
    bot will attempt to generate a chain that meets or exceeds the size set in
    minChainLength."""))

conf.registerGroup(conf.supybot.plugins.Markov, 'randomSpeaking')
conf.registerChannelValue(conf.supybot.plugins.Markov.randomSpeaking,
    'probability', registry.Probability(0, """Determines the probability that
    will be checked against to determine whether the bot should randomly say
    something.  If 0, the bot will never say anything on it's own.  If 1, the
    bot will speak every time we make a check."""))
conf.registerChannelValue(conf.supybot.plugins.Markov.randomSpeaking,
    'maxDelay', registry.PositiveInteger(10, """Determines the upper bound for
    how long the bot will wait before randomly speaking.  The delay is a
    randomly generated number of seconds below the value of this config
    variable."""))
conf.registerChannelValue(conf.supybot.plugins.Markov.randomSpeaking,
    'throttleTime', registry.PositiveInteger(300, """Determines the minimum
    number of seconds between the bot randomly speaking."""))

class DbmMarkovDB(object):
    def __init__(self, filename):
        self.dbs = ircutils.IrcDict()
        self.filename = filename

    def close(self):
        for db in self.dbs.values():
            db.close()

    def _getDb(self, channel):
        if channel not in self.dbs:
            filename = plugins.makeChannelFilename(self.filename, channel)
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
            if db.has_key('\n'):
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
        if db.has_key('\n \n'):
            return len(sets.Set(db['\n \n'].split()))
        else:
            return 0

    def lasts(self, channel):
        db = self._getDb(channel)
        if db.has_key('\n'):
            return len(sets.Set(db['\n'].split()))
        else:
            return 0

    def pairs(self, channel):
        db = self._getDb(channel)
        pairs = [k for k in db.keys() if '\n' not in k]
        return len(pairs)

    def follows(self, channel):
        db = self._getDb(channel)
        # anydbm sucks in that we're not guaranteed to have .iteritems()
        # *cough*gdbm*cough*, so this has to be done the stupid way
        follows = [len(db[k].split()) for k in db.keys() if '\n' not in k]
        return sum(follows)

MarkovDB = plugins.DB('Markov', {'anydbm': DbmMarkovDB})

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
        self.__parent = super(Markov, self)
        self.__parent.__init__()
        self.lastSpoke = time.time()

    def die(self):
        self.q.die()
        self.__parent.die()

    def tokenize(self, m):
        if ircmsgs.isAction(m):
            return ircmsgs.unAction(m).split()
        elif ircmsgs.isCtcp(m):
            return []
        else:
            return m.args[1].split()

    def doPrivmsg(self, irc, msg):
        channel = plugins.getChannel(msg.args[0])
        if irc.isChannel(channel):
            canSpeak = False
            now = time.time()
            throttle = self.registryValue('randomSpeaking.throttleTime',
                                          channel)
            prob = self.registryValue('randomSpeaking.probability', channel)
            delay = self.registryValue('randomSpeaking.maxDelay', channel)
            irc = callbacks.SimpleProxy(irc, msg)
            if now > self.lastSpoke + throttle:
                canSpeak = True
            if canSpeak and random.random() < prob:
                f = self._markov(channel, irc, private=True, to=channel)
                schedule.addEvent(lambda: self.q.enqueue(f), now + delay)
                self.lastSpoke = now + delay
            words = self.tokenize(msg)
            words.insert(0, '\n')
            words.insert(0, '\n')
            words.append('\n')
            # This shouldn't happen often (CTCP messages being the possible exception)
            if not words or len(words) == 3:
                return
            if self.registryValue('ignoreBotCommands', channel) and \
                    callbacks.addressed(irc.nick, msg):
                return
            def doPrivmsg(db):
                for (first, second, follower) in window(words, 3):
                    db.addPair(channel, first, second, follower)
            self.q.enqueue(doPrivmsg)

    def _markov(self, channel, irc, word1=None, word2=None, **kwargs):
        def f(db):
            minLength = self.registryValue('minChainLength', channel)
            maxTries = self.registryValue('maxAttempts', channel)
            while maxTries > 0:
                maxTries -= 1;
                if word1 and word2:
                    givenArgs = True
                    words = [word1, word2]
                elif word1 or word2:
                    # Can't just "raise callbacks.ArgumentError" because
                    # exception is thrown in MarkovQueue, where it isn't
                    # caught and no message is sent to the server
                    irc.reply(self.getCommandHelp('markov'))
                    return
                else:
                    givenArgs = False
                    try:
                        # words is of the form ['\r', word]
                        words = list(db.getFirstPair(channel))
                    except KeyError:
                        irc.error('I don\'t have any first pairs for %s.' %
                                  channel)
                        return # We can't use raise here because the exception
                               # isn't caught and therefore isn't sent to the
                               # server
                follower = words[-1]
                last = False
                resp = []
                while not last:
                    resp.append(follower)
                    try:
                        (follower,last) = db.getFollower(channel, words[-2],
                                                         words[-1])
                    except KeyError:
                        irc.error('I found a broken link in the Markov chain. '
                                  ' Maybe I received two bad links to start '
                                  'the chain.')
                        return # ditto here re: Raise
                    words.append(follower)
                if givenArgs:
                    if len(words[:-1]) >= minLength:
                        irc.reply(' '.join(words[:-1]), **kwargs)
                        return
                    else:
                        continue
                else:
                    if len(resp) >= minLength:
                        irc.reply(' '.join(resp), **kwargs)
                        return
                    else:
                        continue
            irc.error('I was unable to generate a Markov chain at least %s '
                      'long.' % utils.nItems('word', minLength))
        return f

    def markov(self, irc, msg, args, channel, word1, word2):
        """[<channel>] [word1 word2]

        Returns a randomly-generated Markov Chain generated sentence from the
        data kept on <channel> (which is only necessary if not sent in the
        channel itself).  If word1 and word2 are specified, they will be used
        to start the Markov chain.
        """
        f = self._markov(channel, irc, word1, word2)
        self.q.enqueue(f)
    markov = wrap(markov, ['channeldb', optional('something'),
                           additional('something')])

    def firsts(self, irc, msg, args, channel):
        """[<channel>]

        Returns the number of Markov's first links in the database for
        <channel>.
        """
        def firsts(db):
            s = 'There are %s firsts in my Markov database for %s.'
            irc.reply(s % (db.firsts(channel), channel))
        self.q.enqueue(firsts)
    firsts = wrap(firsts, ['channeldb'])

    def lasts(self, irc, msg, args, channel):
        """[<channel>]

        Returns the number of Markov's last links in the database for
        <channel>.
        """
        def lasts(db):
            s = 'There are %s lasts in my Markov database for %s.'
            irc.reply(s % (db.lasts(channel), channel))
        self.q.enqueue(lasts)
    lasts = wrap(lasts, ['channeldb'])

    def pairs(self, irc, msg, args, channel):
        """[<channel>]

        Returns the number of Markov's chain links in the database for
        <channel>.
        """
        def pairs(db):
            s = 'There are %s pairs in my Markov database for %s.'
            irc.reply(s % (db.pairs(channel), channel))
        self.q.enqueue(pairs)
    pairs = wrap(pairs, ['channeldb'])

    def follows(self, irc, msg, args, channel):
        """[<channel>]

        Returns the number of Markov's third links in the database for
        <channel>.
        """
        def follows(db):
            s = 'There are %s follows in my Markov database for %s.'
            irc.reply(s % (db.follows(channel), channel))
        self.q.enqueue(follows)
    follows = wrap(follows, ['channeldb'])

    def stats(self, irc, msg, args, channel):
        """[<channel>]

        Returns all stats (firsts, lasts, pairs, follows) for <channel>'s
        Markov database.
        """
        def stats(db):
            s = '; '.join(['Firsts: %s', 'Lasts: %s', 'Pairs: %s',
                           'Follows: %s'])
            irc.reply(s % (db.firsts(channel), db.lasts(channel),
                           db.pairs(channel), db.follows(channel)))
        self.q.enqueue(stats)
    stats = wrap(stats, ['channeldb'])

Class = Markov

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
