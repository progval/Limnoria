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

import os.path

import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.callbacks as callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

class Markov(plugins.ChannelDBHandler, callbacks.Privmsg):
    threaded = True
    def __init__(self):
        plugins.ChannelDBHandler.__init__(self)
        callbacks.Privmsg.__init__(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(filename)
        db = sqlite.connect(filename)
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE pairs (
                          id INTEGER PRIMARY KEY,
                          first TEXT,
                          second TEXT,
                          is_first BOOLEAN,
                          UNIQUE (first, second) ON CONFLICT IGNORE
                          )""")
        cursor.execute("""CREATE TABLE follows (
                          id INTEGER PRIMARY KEY,
                          pair_id INTEGER,
                          word TEXT
                          )""")
        cursor.execute("""CREATE INDEX follows_pair_id ON follows (pair_id)""")
        db.commit()
        return db

    def doPrivmsg(self, irc, msg):
        if not ircutils.isChannel(msg.args[0]):
            return
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        if ircmsgs.isAction(msg):
            words = ircmsgs.unAction(msg).split()
        else:
            words = msg.args[1].split()
        isFirst = True
        for (first, second, follower) in window(words, 3):
            if isFirst:
                cursor.execute("""INSERT OR REPLACE
                                  INTO pairs VALUES (NULL, %s, %s, 1)""",
                               first, second)
                isFirst = False
            else:
                cursor.execute("INSERT INTO pairs VALUES (NULL, %s, %s, 0)",
                               first, second)
            cursor.execute("""SELECT id FROM pairs
                              WHERE first=%s AND second=%s""", first, second)
            id = int(cursor.fetchone()[0])
            cursor.execute("""INSERT INTO follows VALUES (NULL, %s, %s)""",
                           id, follower)
        if not isFirst: # i.e., if the loop iterated at all.
            cursor.execute("""INSERT INTO pairs VALUES (NULL, %s, %s, 0)""",
                           second, follower)
            cursor.execute("""SELECT id FROM pairs
                              WHERE first=%s AND second=%s""", second,follower)
            id = int(cursor.fetchone()[0])
            cursor.execute("INSERT INTO follows VALUES (NULL, %s, NULL)", id)
        db.commit()

    _maxMarkovLength = 80
    _minMarkovLength = 7
    def markov(self, irc, msg, args):
        """[<channel>]

        Returns a randomly-generated Markov Chain generated sentence from the
        data kept on <channel> (which is only necessary if not sent in the
        channel itself).
        """
        argsCopy = args[:]
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        words = []
        cursor.execute("""SELECT id, first, second FROM pairs
                          WHERE is_first=1
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error('I have no records for that channel.')
            return
        (id, first, second) = cursor.fetchone()
        id = int(id)
        words.append(first)
        words.append(second)
        sql = """SELECT follows.word FROM pairs, follows
                 WHERE pairs.first=%s AND
                       pairs.second=%s AND
                       pairs.id=follows.pair_id
                 ORDER BY random()
                 LIMIT 1"""
        while len(words) < self._maxMarkovLength:
            cursor.execute(sql, words[-2], words[-1])
            results = cursor.fetchone()
            if not results:
                break
            word = results[0]
            if word is None:
                break
            words.append(word)
        if len(words) < self._minMarkovLength:
            self.markov(irc, msg, argsCopy)
        else:
            irc.reply(' '.join(words))

    def pairs(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's chain links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM pairs""")
        n = int(cursor.fetchone()[0])
        s = 'There are %s pairs in my Markov database for %s' % (n, channel)
        irc.reply(s)

    def firsts(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's first links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM pairs WHERE is_first=1""")
        n = int(cursor.fetchone()[0])
        s = 'There are %s first pairs in my Markov database for %s'%(n,channel)
        irc.reply(s)

    def follows(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's third links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM follows""")
        n = int(cursor.fetchone()[0])
        s = 'There are %s follows in my Markov database for %s' % (n, channel)
        irc.reply(s)

    def lasts(self, irc, msg, args):
        """[<channel>]

        Returns the number of Markov's last links in the database for
        <channel>.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM follows WHERE word ISNULL""")
        n = int(cursor.fetchone()[0])
        s = 'There are %s lasts in my Markov database for %s' % (n, channel)
        irc.reply(s)


Class = Markov

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
