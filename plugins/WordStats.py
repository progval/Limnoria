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

import plugins

import conf
import utils
import plugins
import privmsgs
import callbacks


conf.registerPlugin('WordStats')
conf.registerChannelValue(conf.supybot.plugins.WordStats,
    'wordstatsRankingDisplay',
    registry.PositiveInteger(3, """Determines the maximum number of top users
    to show for a given wordstat when someone requests the wordstats for a
    particular word."""))

class WordStats(callbacks.Privmsg, plugins.ChannelDBHandler):
    noIgnore = True
    def die(self):
        callbacks.Privmsg.die(self)
        plugins.ChannelDBHandler.die(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename)
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE words (
                              id INTEGER PRIMARY KEY,
                              word TEXT UNIQUE ON CONFLICT IGNORE
                              )""")
            cursor.execute("""CREATE TABLE word_stats (
                              id INTEGER PRIMARY KEY,
                              word_id INTEGER,
                              user_id INTEGER,
                              count INTEGER,
                              UNIQUE (word_id, user_id) ON CONFLICT IGNORE
                              )""")
            cursor.execute("""CREATE INDEX word_stats_word_id
                              ON word_stats (word_id)""")
            cursor.execute("""CREATE INDEX word_stats_user_id
                              ON word_stats (user_id)""")
            db.commit()
        return db

    _alphanumeric = string.ascii_letters + string.digits
    _nonAlphanumeric = string.ascii.translate(string.ascii, _alphanumeric)
    def doPrivmsg(self, irc, msg):
        if not ircutils.isChannel(msg.args[0]):
            return
        callbacks.Privmsg.doPrivmsg(self, irc, msg)
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            return
        (channel, s) = msg.args
        s = s.strip()
        if not s:
            return
        db = self.getDb(channel)
        cursor = db.cursor()
        words = s.lower().split()
        words = [s.strip(self._nonAlphanumeric) for s in words]
        criteria = ['word=%s'] * len(words)
        criterion = ' OR '.join(criteria)
        cursor.execute("SELECT id, word FROM words WHERE %s"%criterion, *words)
        for (wordId, word) in cursor.fetchall():
            cursor.execute("""INSERT INTO word_stats
                              VALUES(NULL, %s, %s, 0)""", wordId, id)
            cursor.execute("""UPDATE word_stats SET count=count+%s
                              WHERE word_id=%s AND user_id=%s""",
                           words.count(word), wordId, id)
        db.commit()
        
    def add(self, irc, msg, args):
        """[<channel>] <word>

        Keeps stats on <word> in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        word = privmsgs.getArgs(args)
        word = word.strip()
        if word.strip(self._nonAlphanumeric) != word:
            irc.error('<word> must not contain non-alphanumeric chars.')
            return
        word = word.lower()
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO words VALUES (NULL, %s)""", word)
        db.commit()
        irc.replySuccess()

    def stats(self, irc, msg, args):
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
        db = self.getDb(channel)
        cursor = db.cursor()
        if not arg1 and not arg2:
            cursor.execute("""SELECT word FROM words""")
            if cursor.rowcount == 0:
                irc.reply('I am not currently keeping any word stats.')
                return
            l = [repr(tup[0]) for tup in cursor.fetchall()]
            s = 'Currently keeping stats for: %s' % utils.commaAndify(l)
            irc.reply(s)
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
            db = self.getDb(channel)
            cursor = db.cursor()
            word = word.lower()
            cursor.execute("""SELECT word_stats.count FROM words, word_stats
                              WHERE words.word=%s AND
                                    word_id=words.id AND
                                    word_stats.user_id=%s""", word, id)
            if cursor.rowcount == 0:
                cursor.execute("""SELECT id FROM words WHERE word=%s""", word)
                if cursor.rowcount == 0:
                    irc.error('I\'m not keeping stats on %r.' % word)
                else:
                    irc.error('%s has never said %r.' % (user, word))
                return
            count = int(cursor.fetchone()[0])
            s = '%s has said %r %s.' % (user,word,utils.nItems('time', count))
            irc.reply(s)
        else:
            # Figure out if we got a user or a word
            cursor.execute("""SELECT word FROM words
                              WHERE word=%s""", arg1)
            if cursor.rowcount == 0:
                # It was a user.
                try:
                    id = ircdb.users.getUserId(arg1)
                except KeyError: # Maybe it was a nick.  Check the hostmask.
                    try:
                        hostmask = irc.state.nickToHostmask(arg1)
                        id = ircdb.users.getUserId(hostmask)
                    except KeyError:
                        irc.error('%r doesn\'t look like a user I know '
                                           'or a word that I\'m keeping stats '
                                           'on' % arg1)
                        return
                cursor.execute("""SELECT words.word, word_stats.count
                                  FROM words, word_stats
                                  WHERE words.id = word_stats.word_id
                                  AND word_stats.user_id=%s
                                  ORDER BY words.word""", id)
                if cursor.rowcount == 0:
                    username = ircdb.users.getUser(id).name
                    irc.error('%r has no wordstats' % username)
                    return
                L = [('%r: %s' % (word, count)) for
                     (word, count) in cursor.fetchall()]
                irc.reply(utils.commaAndify(L))
                return
            else:
                # It's a word, not a user
                word = arg1
                numUsers = self.registryValue('wordstatsRankingDisplay',
                                              msg.args[0])
                cursor.execute("""SELECT word_stats.count,
                                         word_stats.user_id
                                  FROM words, word_stats
                                  WHERE words.word=%s AND
                                        words.id=word_stats.word_id
                                  ORDER BY word_stats.count DESC""",
                                  word)
                if cursor.rowcount == 0:
                    irc.error('No one has said %r' % word)
                    return
                results = cursor.fetchall()
                numResultsShown = min(cursor.rowcount, numUsers)
                cursor.execute("""SELECT sum(word_stats.count)
                                  FROM words, word_stats
                                  WHERE words.word=%s AND
                                        words.id=word_stats.word_id""",
                                  word)
                total = int(cursor.fetchone()[0])
                ers = '%rer' % word
                ret = 'Top %s ' % utils.nItems(ers, numResultsShown)
                ret += '(out of a total of %s seen):' % \
                       utils.nItems(repr(word), total)
                L = []
                for (count, id) in results[:numResultsShown]:
                    username = ircdb.users.getUser(id).name
                    L.append('%s: %s' % (username, count))
                try:
                    id = ircdb.users.getUserId(msg.prefix)
                    rank = 1
                    s = ""  # Don't say anything if they show in the output
                            # already
                    seenUser = False
                    for (count, userId) in results:
                        if userId == id:
                            seenUser = True
                            if rank > numResultsShown:
                                s = 'You are ranked %s out of %s with %s.' % \
                                    (rank, utils.nItems(ers, len(results)),
                                     utils.nItems(repr(word), count))
                                break
                        else:
                            rank += 1
                    else:
                        if not seenUser:
                            s = 'You have not said %r' % word
                    ret = '%s %s.  %s' % (ret, utils.commaAndify(L), s)
                except KeyError:
                    ret = '%s %s.' % (ret, utils.commaAndify(L))
                irc.reply(ret)
 
Class = WordStats

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
