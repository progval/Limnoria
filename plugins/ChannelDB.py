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
Silently listens to every message received on a channel and keeps statistics
concerning joins, parts, and various other commands in addition to tracking
statistics about smileys, actions, characters, and words.
"""

from baseplugin import *

import re
import sets
import time

import sqlite

import debug
import utils
import ircdb
import ircmsgs
import privmsgs
import ircutils
import callbacks

example = utils.wrapLines("""
<jemfinch> @list ChannelDB
<supybot> channelstats, karma, seen, stats
<jemfinch> @channelstats
<supybot> Error: Command must be sent in a channel or include a channel in its arguments.
<jemfinch> (Obviously, you gotta give it a channel :))
<jemfinch> @channelstats #sourcereview
<supybot> On #sourcereview there have been 46965 messages, containing 1801703 characters, 319510 words, 4663 smileys, and 657 frowns; 2262 of those messages were ACTIONs.  There have been 2404 joins, 139 parts, 1 kicks, 323 mode changes, and 129 topic changes.
<jemfinch> @stats #sourcereview jemfinch
<supybot> jemfinch has sent 16131 messages; a total of 687961 characters, 118915 words, 1482 smileys, and 226 frowns; 797 of those messages were ACTIONs.  jemfinch has joined 284 times, parted 25 times, kicked someone 0 times been kicked 0 times, changed the topic 2 times, and changed the mode 2 times.
<jemfinch> @karma #sourcereview birthday_sex
<supybot> Karma for 'birthday_sex' has been increased 1 time and decreased 0 times for a total karma of 1.
<jemfinch> @seen #sourcereview inkedmn
<supybot> inkedmn was last seen here 1 day, 18 hours, 42 minutes, and 23 seconds ago saying 'ah'
""")

smileys = (':)', ';)', ':]', ':-)', ':-D', ':D', ':P', ':p', '(=', '=)')
frowns = (':|', ':-/', ':-\\', ':\\', ':/', ':(', ':-(', ':\'(')

smileyre = re.compile('|'.join(map(re.escape, smileys)))
frownre = re.compile('|'.join(map(re.escape, frowns)))

class ChannelDB(callbacks.PrivmsgCommandAndRegexp, ChannelDBHandler):
    regexps = sets.Set(['increaseKarma', 'decreaseKarma'])
    def __init__(self):
        ChannelDBHandler.__init__(self)
        callbacks.PrivmsgCommandAndRegexp.__init__(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(filename)
        db = sqlite.connect(filename)
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE user_stats (
                          id INTEGER PRIMARY KEY,
                          name TEXT UNIQUE,
                          last_seen TIMESTAMP,
                          last_msg TEXT,
                          smileys INTEGER,
                          frowns INTEGER,
                          chars INTEGER,
                          words INTEGER,
                          msgs INTEGER,
                          actions INTEGER,
                          joins INTEGER,
                          parts INTEGER,
                          kicks INTEGER,
                          kicked INTEGER,
                          modes INTEGER,
                          topics INTEGER
                          )""")
        cursor.execute("""CREATE TABLE channel_stats (
                          smileys INTEGER,
                          frowns INTEGER,
                          chars INTEGER,
                          words INTEGER,
                          msgs INTEGER,
                          actions INTEGER,
                          joins INTEGER,
                          parts INTEGER,
                          kicks INTEGER,
                          modes INTEGER,
                          topics INTEGER
                          )""")
        cursor.execute("""INSERT INTO channel_stats
                          VALUES (0, 0, 0, 0, 0,
                                  0, 0, 0, 0, 0, 0)""")

        cursor.execute("""CREATE TABLE karma (
                          id INTEGER PRIMARY KEY,
                          name TEXT UNIQUE ON CONFLICT IGNORE,
                          added INTEGER,
                          subtracted INTEGER
                          )""")
        db.commit()
        return db

    def doPrivmsg(self, irc, msg):
        callbacks.PrivmsgCommandAndRegexp.doPrivmsg(self, irc, msg)
        if ircutils.isChannel(msg.args[0]):
            (channel, s) = msg.args
            db = self.getDb(channel)
            cursor = db.cursor()
            chars = len(s)
            words = len(s.split())
            isAction = ircmsgs.isAction(msg)
            frowns = len(frownre.findall(s))
            smileys = len(smileyre.findall(s))
            cursor.execute("""UPDATE channel_stats
                              SET smileys=smileys+%s,
                                  frowns=frowns+%s,
                                  chars=chars+%s,
                                  words=words+%s,
                                  msgs=msgs+1,
                                  actions=actions+%s""",
                           smileys, frowns, chars, words, int(isAction))
            try:
                name = ircdb.users.getUser(msg.prefix).name
            except KeyError:
                return
            cursor.execute("""SELECT COUNT(*)
                              FROM user_stats
                              WHERE name=%s""", name)
            count = int(cursor.fetchone()[0])
            if count == 0: # User isn't in database.
                cursor.execute("""INSERT INTO user_stats VALUES (
                                  NULL, %s, %s, %s, %s, %s,
                                  %s, %s, 1, %s,
                                  0, 0, 0, 0, 0, 0 )""",
                               name, int(time.time()), msg.args[1],
                               smileys, frowns, chars, words, int(isAction))
            else:
                cursor.execute("""UPDATE user_stats SET
                                  last_seen=%s, last_msg=%s, chars=chars+%s,
                                  words=words+%s, msgs=msgs+1,
                                  actions=actions+%s, smileys=smileys+%s,
                                  frowns=frowns+%s
                                  WHERE name=%s""",
                               int(time.time()), s,
                               chars, words, int(isAction),
                               smileys, frowns, name)
            db.commit()

    def doJoin(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET joins=joins+1""")
        try:
            if ircutils.isUserHostmask(msg.prefix):
                name = ircdb.users.getUser(msg.prefix).name
            else:
                name = msg.prefix
            cursor.execute("""UPDATE user_stats
                              SET joins=joins+1
                              WHERE name=%s""", name)
        except KeyError:
            pass
        db.commit()

    def doPart(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET parts=parts+1""")
        try:
            if ircutils.isUserHostmask(msg.prefix):
                name = ircdb.users.getUser(msg.prefix).name
            else:
                name = msg.prefix
            cursor.execute("UPDATE user_stats SET parts=parts+1 WHERE name=%s",
                           name)
        except KeyError:
            pass
        db.commit()

    def doTopic(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET topics=topics+1""")
        try:
            if ircutils.isUserHostmask(msg.prefix):
                name = ircdb.users.getUser(msg.prefix).name
            else:
                name = msg.prefix
            cursor.execute("""UPDATE user_stats
                              SET topics=topics+1
                              WHERE name=%s""", name)
        except KeyError:
            pass
        db.commit()

    def doMode(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET modes=modes+1""")
        try:
            if ircutils.isUserHostmask(msg.prefix):
                name = ircdb.users.getUser(msg.prefix).name
            else:
                name = msg.prefix
            cursor.execute("""UPDATE user_stats
                              SET modes=modes+1
                              WHERE name=%s""", name)
        except KeyError:
            pass
        db.commit()

    def doKick(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET kicks=kicks+1""")
        try:
            if ircutils.isUserHostmask(msg.prefix):
                name = ircdb.users.getUser(msg.prefix).name
            else:
                name = msg.prefix
            cursor.execute("""UPDATE user_stats
                              SET kicks=kicks+1
                              WHERE name=%s""", name)
        except KeyError:
            pass
        try:
            kicked = msg.args[1]
            name = ircdb.users.getUser(irc.state.nickToHostmask(kicked)).name
            cursor.execute("""UPDATE user_stats
                              SET kicked=kicked+1
                              WHERE name=%s""", name)
        except KeyError:
            pass
        db.commit()

    def seen(self, irc, msg, args):
        """[<channel>] <nick>

        Returns the last time <nick> was seen and what <nick> was last seen
        saying.  <channel> is only necessary if the message isn't sent on the
        channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        name = privmsgs.getArgs(args)
        if not ircdb.users.hasUser(name):
            try:
                hostmask = irc.state.nickToHostmask(name)
                name = ircdb.users.getUser(hostmask).name
            except KeyError:
                irc.error(msg, conf.replyNoUser)
                return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT last_seen, last_msg FROM user_stats
                          WHERE name=%s""", name)
        if cursor.rowcount == 0:
            irc.reply(msg, 'I have no stats for that user.')
        else:
            (seen, m) = cursor.fetchone()
            seen = int(seen)
            if m.startswith('\x01ACTION') and m.endswith('\x01'):
                m = '* %s%s' % (name, m[7:-1])
            s = '%s was last seen here %s ago saying %s' % \
                (name, utils.timeElapsed(time.time() - seen), m)
            irc.reply(msg, s)

    def karma(self, irc, msg, args):
        """[<channel>] <text>

        Returns the karma of <text>.  <channel> is only necessary if the
        message isn't sent on the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        if len(args) == 1:
            name = args[0]
            cursor.execute("""SELECT added, subtracted
                              FROM karma
                              WHERE name=%s""", name)
            if cursor.rowcount == 0:
                irc.reply(msg, '%s has no karma.' % name)
            else:
                (added, subtracted) = map(int, cursor.fetchone())
                total = added - subtracted
                s = 'Karma for %r has been increased %s %s ' \
                    'and decreased %s %s for a total karma of %s.' % \
                    (name, added, added == 1 and 'time' or 'times',
                     subtracted, subtracted == 1 and 'time' or 'times', total)
                irc.reply(msg, s)
        elif len(args) > 1:
            criteria = ' OR '.join(['name=%s'] * len(args))
            sql = """SELECT name, added-subtracted
                     FROM karma WHERE %s
                     ORDER BY added-subtracted DESC""" % criteria
            cursor.execute(sql, *args)
            s = utils.commaAndify(['%s: %s' % (n,t)
                                   for (n,t) in cursor.fetchall()])
            irc.reply(msg, s + '.')
        else: # No name was given.  Return the top/bottom 3 karmas.
            cursor.execute("""SELECT name, added-subtracted
                              FROM karma
                              ORDER BY added-subtracted DESC
                              LIMIT 3""")
            highest = ['%r (%s)' % (t[0], t[1]) for t in cursor.fetchall()]
            cursor.execute("""SELECT name, added-subtracted
                              FROM karma
                              ORDER BY added-subtracted ASC
                              LIMIT 3""")
            lowest = ['%r (%s)' % (t[0], t[1]) for t in cursor.fetchall()]
            s = 'Highest karma: %s.  Lowest karma: %s.' % \
                (utils.commaAndify(highest), utils.commaAndify(lowest))
            irc.reply(msg, s)
            
    def increaseKarma(self, irc, msg, match):
        r"^(.)(\S+)\+\+$"
        (first, name) = match.groups()
        if first not in conf.prefixChars:
            return
        db = self.getDb(msg.args[0])
        cursor = db.cursor()
        cursor.execute("""INSERT INTO karma VALUES (NULL, %s, 0, 0)""", name)
        cursor.execute("""UPDATE karma SET added=added+1 WHERE name=%s""",name)

    def decreaseKarma(self, irc, msg, match):
        r"^(.)(\S+)--$"
        (first, name) = match.groups()
        if first not in conf.prefixChars:
            return
        db = self.getDb(msg.args[0])
        cursor = db.cursor()
        cursor.execute("""INSERT INTO karma VALUES (NULL, %s, 0, 0)""", name)
        cursor.execute("""UPDATE karma
                          SET subtracted=subtracted+1
                          WHERE name=%s""", name)

    def stats(self, irc, msg, args):
        """[<channel>] <nick>

        Returns the statistics for <nick> on <channel>.  <channel> is only
        necessary if the message isn't sent on the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        name = privmsgs.getArgs(args)
        if not ircdb.users.hasUser(name):
            hostmask = irc.state.nickToHostmask(name)
            try:
                name = ircdb.users.getUser(hostmask).name
            except KeyError:
                irc.error(msg, conf.replyNoUser)
                return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT smileys, frowns, chars, words, msgs, actions,
                                 joins, parts, kicks, kicked, modes, topics
                          FROM user_stats WHERE name=%s""", name)
        if cursor.rowcount == 0:
            irc.reply(msg, 'I have no stats for that user.')
            return
        values = cursor.fetchone()
        s = '%s has sent %s messages; a total of %s characters, %s words, ' \
            '%s smileys, and %s frowns; %s of those messages were ACTIONs.  ' \
            '%s has joined %s times, parted %s times, kicked someone %s times'\
            ' been kicked %s times, changed the topic %s times, ' \
            'and changed the mode %s times.' % \
            (name, values.msgs, values.chars, values.words,
             values.smileys, values.frowns, values.actions,
             name, values.joins, values.parts, values.kicks,
             values.kicked, values.topics,
             values.modes)
        irc.reply(msg, s)

    def channelstats(self, irc, msg, args):
        """[<channel>]

        Returns the statistics for <channel>.  <channel> is only necessary if
        the message isn't sent on the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM channel_stats""")
        values = cursor.fetchone()
        s = 'On %s there have been %s messages, containing %s characters, ' \
            '%s words, %s smileys, and %s frowns; %s of those messages were ' \
            'ACTIONs.  There have been %s joins, %s parts, %s kicks, ' \
            '%s mode changes, and %s topic changes.' % \
            (channel, values.msgs, values.chars,
             values.words, values.smileys, values.frowns, values.actions,
             values.joins, values.parts, values.kicks,
             values.modes, values.topics)
        irc.reply(msg, s)


Class = ChannelDB

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
