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

import plugins

import os
import re
import sets
import time
import getopt

import sqlite

import conf
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

class ChannelDB(plugins.ChannelDBHandler, callbacks.PrivmsgCommandAndRegexp):
    addressedRegexps = sets.Set(['increaseKarma', 'decreaseKarma'])
    def __init__(self):
        plugins.ChannelDBHandler.__init__(self)
        callbacks.PrivmsgCommandAndRegexp.__init__(self)
        self.lastmsg = None
        self.laststate = None

    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename)
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE user_stats (
                              id INTEGER PRIMARY KEY,
                              user_id INTEGER UNIQUE,
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
                              topics INTEGER,
                              quits INTEGER
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
                              topics INTEGER,
                              quits INTEGER
                              )""")
            cursor.execute("""CREATE TABLE nick_seen (
                              name TEXT UNIQUE ON CONFLICT REPLACE,
                              last_seen TIMESTAMP,
                              last_msg TEXT
                              )""")
            cursor.execute("""INSERT INTO channel_stats
                              VALUES (0, 0, 0, 0, 0, 0,
                                      0, 0, 0, 0, 0, 0)""")

            cursor.execute("""CREATE TABLE karma (
                              id INTEGER PRIMARY KEY,
                              name TEXT UNIQUE ON CONFLICT IGNORE,
                              added INTEGER,
                              subtracted INTEGER
                              )""")
            db.commit()
        def p(s1, s2):
            return int(ircutils.nickEqual(s1, s2))
        db.create_function('nickeq', 2, p)
        return db

    def __call__(self, irc, msg):
        try:
            if self.lastmsg:
                self.laststate.addMsg(irc, self.lastmsg)
            else:
                self.laststate = irc.state.copy()
        finally:
            self.lastmsg = msg
        callbacks.PrivmsgCommandAndRegexp.__call__(self, irc, msg)
        
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
            s = ircmsgs.prettyPrint(msg)
            cursor.execute("""UPDATE channel_stats
                              SET smileys=smileys+%s,
                                  frowns=frowns+%s,
                                  chars=chars+%s,
                                  words=words+%s,
                                  msgs=msgs+1,
                                  actions=actions+%s""",
                           smileys, frowns, chars, words, int(isAction))
            cursor.execute("""INSERT INTO nick_seen VALUES (%s, %s, %s)""",
                           msg.nick, int(time.time()), s)
            try:
                id = ircdb.users.getUserId(msg.prefix)
            except KeyError:
                return
            cursor.execute("""SELECT COUNT(*)
                              FROM user_stats
                              WHERE user_id=%s""", id)
            count = int(cursor.fetchone()[0])
            if count == 0: # User isn't in database.
                cursor.execute("""INSERT INTO user_stats VALUES (
                                  NULL, %s, %s, %s, %s, %s,
                                  %s, %s, 1, %s,
                                  0, 0, 0, 0, 0, 0, 0)""",
                               id, int(time.time()), s,
                               smileys, frowns, chars, words, int(isAction))
            else:
                cursor.execute("""UPDATE user_stats SET
                                  last_seen=%s, last_msg=%s, chars=chars+%s,
                                  words=words+%s, msgs=msgs+1,
                                  actions=actions+%s, smileys=smileys+%s,
                                  frowns=frowns+%s
                                  WHERE user_id=%s""",
                               int(time.time()), s,
                               chars, words, int(isAction),
                               smileys, frowns, id)
            db.commit()

    def doPart(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET parts=parts+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats SET parts=parts+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doTopic(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET topics=topics+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats
                              SET topics=topics+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doMode(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET modes=modes+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats
                              SET modes=modes+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doKick(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET kicks=kicks+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats
                              SET kicks=kicks+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        try:
            kicked = msg.args[1]
            id = ircdb.users.getUserId(irc.state.nickToHostmask(kicked))
            cursor.execute("""UPDATE user_stats
                              SET kicked=kicked+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doJoin(self, irc, msg):
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""UPDATE channel_stats SET joins=joins+1""")
        try:
            id = ircdb.users.getUserId(msg.prefix)
            cursor.execute("""UPDATE user_stats
                              SET joins=joins+1
                              WHERE user_id=%s""", id)
        except KeyError:
            pass
        db.commit()

    def doQuit(self, irc, msg):
        for (channel, c) in self.laststate.channels.iteritems():
            if msg.nick in c.users:
                db = self.getDb(channel)
                cursor = db.cursor()
                cursor.execute("""UPDATE channel_stats SET quits=quits+1""")
                try:
                    id = ircdb.users.getUserId(msg.prefix)
                    cursor.execute("""UPDATE user_stats SET quits=quits+1
                                      WHERE user_id=%s""", id)
                except KeyError:
                    pass
                db.commit()

    def seen(self, irc, msg, args):
        """[<channel>] [--user] <name>

        Returns the last time <name> was seen and what <name> was last seen
        saying.  --user will look for user <name> instead of using <name> as
        a nick (registered users, remember, can be recognized under any number
        of nicks) <channel> is only necessary if the message isn't sent on the
        channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        (optlist, rest) = getopt.getopt(args, '', ['user'])
        name = privmsgs.getArgs(rest)
        #debug.printf(optlist)
        if ('--user', '') in optlist:
            table = 'user_stats'
            criterion = 'user_id=%s'
            if not ircdb.users.hasUser(name):
                try:
                    hostmask = irc.state.nickToHostmask(name)
                    name = ircdb.users.getUserId(hostmask)
                except KeyError:
                    irc.error(msg, conf.replyNoUser)
                    return
        else:
            table = 'nick_seen'
            criterion = 'nickeq(name,%s)'
        sql = "SELECT last_seen, last_msg FROM %s WHERE %s" % (table,criterion)
        #debug.printf(sql)
        cursor.execute(sql, name)
        if cursor.rowcount == 0:
            irc.error(msg, 'I have not seen %s.' % name)
        else:
            (seen, m) = cursor.fetchone()
            seen = int(seen)
            if name.isdigit():
                name = ircdb.getUser(int(name)).name
            s = '%s was last seen here %s ago saying %r' % \
                (name, utils.timeElapsed(time.time() - seen), m)
            irc.reply(msg, s)

    def karma(self, irc, msg, args):
        """[<channel>] [<text>]

        Returns the karma of <text>.  If <text> is not given, returns the top
        three and bottom three karmas. <channel> is only necessary if the
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
            s = utils.commaAndify(['%s: %s' % (n, t)
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
        r"^(\S+)\+\+$"
        name = match.group(1)
        db = self.getDb(msg.args[0])
        cursor = db.cursor()
        cursor.execute("""INSERT INTO karma VALUES (NULL, %s, 0, 0)""", name)
        cursor.execute("""UPDATE karma SET added=added+1 WHERE name=%s""",name)

    def decreaseKarma(self, irc, msg, match):
        r"^(\S+)--$"
        name = match.group(1)
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
            try:
                hostmask = irc.state.nickToHostmask(name)
                id = ircdb.users.getUserId(hostmask)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
                return
        else:
            id = ircdb.users.getUserId(name)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM user_stats WHERE user_id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'I have no stats for that user.')
            return
        values = cursor.fetchone()
        s = '%s has sent %s; a total of %s, %s, ' \
            '%s, and %s; %s of those messages %s' \
            '%s has joined %s, parted %s, quit %s, kicked someone %s, '\
            'been kicked %s, changed the topic %s, ' \
            'and changed the mode %s.' % \
            (name, utils.nItems(values.msgs, 'message'),
             utils.nItems(values.chars, 'character'),
             utils.nItems(values.words, 'word'),
             utils.nItems(values.smileys, 'smiley'),
             utils.nItems(values.frowns, 'frown'),
             values.actions, values.actions == 1 and 'was an ACTION.  '
                                                 or 'were ACTIONs.  ',
             name,
             utils.nItems(values.joins, 'time'),
             utils.nItems(values.parts, 'time'),
             utils.nItems(values.quits, 'time'),
             utils.nItems(values.kicks, 'time'),
             utils.nItems(values.kicked, 'time'),
             utils.nItems(values.topics, 'time'),
             utils.nItems(values.modes, 'time'))
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
            'ACTIONs.  There have been %s joins, %s parts, %s quits, ' \
            '%s kicks, %s mode changes, and %s topic changes.' % \
            (channel, values.msgs, values.chars,
             values.words, values.smileys, values.frowns, values.actions,
             values.joins, values.parts, values.quits,
             values.kicks, values.modes, values.topics)
        irc.reply(msg, s)


Class = ChannelDB

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
