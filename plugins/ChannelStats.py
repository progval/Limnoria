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

Commands include:
  seen
  stats
"""

from baseplugin import *

import re
import time

import sqlite

import debug
import utils
import ircdb
import ircmsgs
import privmsgs
import ircutils
import callbacks

smileys = (':)', ';)', ':]', ':-)', ':-D', ':D', ':P', ':p', '(=', '=)')
frowns = (':|', ':-/', ':-\\', ':\\', ':/', ':(', ':-(', ':\'(')

smileyre = re.compile('|'.join([re.escape(s) for s in smileys]))
frownre = re.compile('|'.join([re.escape(s) for s in frowns]))

class ChannelStats(callbacks.Privmsg, ChannelDBHandler):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        ChannelDBHandler.__init__(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(filename)
        db = sqlite.connect(filename)
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE stats (
                          id INTEGER PRIMARY KEY,
                          username TEXT UNIQUE,
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
        cursor.execute("""CREATE INDEX stats_username ON stats (username)""")
        db.commit()
        return db
    
    def doPrivmsg(self, irc, msg):
        callbacks.Privmsg.doPrivmsg(self, irc, msg)
        if ircutils.isChannel(msg.args[0]):
            (channel, s) = msg.args
            db = self.getDb(channel)
            cursor = db.cursor()
            try:
                name = ircdb.users.getUserName(msg.prefix)
            except KeyError:
                return
            cursor.execute("""SELECT * FROM stats WHERE username=%s""", name)
            if cursor.rowcount == 0: # User isn't in database.
                cursor.execute("""INSERT INTO stats VALUES (
                                  NULL, %s, %s, %s, %s, %s,
                                  %s, %s, 1, %s,
                                  0, 0, 0, 0, 0, 0 )""",
                               name, int(time.time()), msg.args[1],
                               len(smileyre.findall(s)),
                               len(frownre.findall(s)), len(s), len(s.split()),
                               int(ircmsgs.isAction(msg)))
            else:
                cursor.execute("""SELECT chars, words, msgs,
                                         actions, smileys, frowns
                                  FROM stats WHERE username=%s""", name)
                values = cursor.fetchone()
                cursor.execute("""UPDATE stats SET
                                  last_seen=%s, last_msg=%s, chars=%s,
                                  words=%s, msgs=%s, actions=%s,
                                  smileys=%s, frowns=%s
                                  WHERE username=%s""",
                               int(time.time()),
                               s,
                               int(values.chars) + len(s),
                               int(values.words) + len(s.split()),
                               int(values.msgs) + 1,
                               int(values.actions) + ircmsgs.isAction(msg),
                               int(values.smileys) + len(smileyre.findall(s)),
                               int(values.frowns) + len(frownre.findall(s)),
                               name)
            db.commit()

    def doJoin(self, irc, msg):
        try:
            name = ircdb.users.getUserName(msg.prefix)
        except KeyError:
            return
        channels = msg.args[0].split(',')
        for channel in channels:
            db = self.getDb(channel)
            cursor = db.cursor()
            cursor.execute("SELECT joins FROM stats WHERE username=%s", name)
            if cursor.rowcount == 0:
                return
            joins = cursor.fetchone()[0]
            cursor.execute("UPDATE stats SET joins=%s WHERE username=%s",
                           joins+1, name)
            db.commit()
                                                   
    def doPart(self, irc, msg):
        try:
            name = ircdb.users.getUserName(msg.prefix)
        except KeyError:
            return
        channels = msg.args[0].split(',')
        for channel in channels:
            db = self.getDb(channel)
            cursor = db.cursor()
            cursor.execute("SELECT parts FROM stats WHERE username=%s", name)
            if cursor.rowcount == 0:
                return
            parts = cursor.fetchone()[0]
            cursor.execute("UPDATE stats SET parts=%s WHERE username=%s",
                           parts+1, name)
            db.commit()

    def doTopic(self, irc, msg):
        try:
            name = ircdb.users.getUserName(msg.prefix)
        except KeyError:
            return
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT topics FROM stats WHERE username=%s", name)
        if cursor.rowcount == 0:
            return
        topics = cursor.fetchone()[0]
        cursor.execute("UPDATE stats SET topics=%s WHERE username=%s",
                       topics+1, name)
        db.commit()

    def doMode(self, irc, msg):
        try:
            name = ircdb.users.getUserName(msg.prefix)
        except KeyError:
            return
        channel = msg.args[0]
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("SELECT modes FROM stats WHERE username=%s", name)
        if cursor.rowcount == 0:
            return
        modes = cursor.fetchone()[0]
        cursor.execute("UPDATE stats SET modes=%s WHERE username=%s",
                       modes+1, name)
        db.commit()

    def doKick(self, irc, msg):
        db = self.getDb(msg.args[0])
        cursor = db.cursor()
        try:
            name = ircdb.users.getUserName(msg.prefix)
            cursor.execute("SELECT kicks FROM stats WHERE username=%s", name)
            if cursor.rowcount != 0:
                kicks = cursor.fetchone()[0]
                cursor.execute("UPDATE stats SET kicks=%s WHERE username=%s",
                               kicks+1, name)
        except KeyError:
            pass
        try:
            kicked = msg.args[1]
            name = ircdb.users.getUserName(irc.state.nickToHostmask(kicked))
            cursor.execute("SELECT kicked FROM stats WHERE username=%s", name)
            if cursor.rowcount != 0:
                kicked = cursor.fetchone()[0]
                cursor.execute("UPDATE stats SET kicked=%s WHERE username=%s",
                               kicked+1, name)
        except KeyError:
            pass
        db.commit()

    def seen(self, irc, msg, args):
        "[<channel>] (if not sent on the channel itself) <nick>"
        channel = privmsgs.getChannel(msg, args)
        name = privmsgs.getArgs(args)
        if not ircdb.users.hasUser(name):
            hostmask = irc.state.nickToHostmask(name)
            try:
                name = ircdb.users.getUserName(hostmask)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
                return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT last_seen, last_msg FROM stats
                          WHERE username=%s""", name)
        if cursor.rowcount == 0:
            irc.reply(msg, 'I have no stats for that user.')
        else:
            (seen, m) = cursor.fetchone()
            seen = int(seen)
            s = '%s was last seen here %s ago saying %r' % \
                (name, utils.timeElapsed(time.time(), seen), m)
            irc.reply(msg, s)

    def stats(self, irc, msg, args):
        "[<channel>] (if not sent in the channel itself) <nick>"
        channel = privmsgs.getChannel(msg, args)
        name = privmsgs.getArgs(args)
        if not ircdb.users.hasUser(name):
            hostmask = irc.state.nickToHostmask(name)
            try:
                name = ircdb.users.getUserName(hostmask)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
                return
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT smileys, frowns, chars, words, msgs, actions,
                                 joins, parts, kicks, kicked, modes, topics
                          FROM stats WHERE username=%s""", name)
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


Class = ChannelStats

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
