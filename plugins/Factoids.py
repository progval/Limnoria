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

from baseplugin import *

import time
import os.path

import sqlite

import conf
import ircdb
import privmsgs
import callbacks

class Factoids(DBHandler, callbacks.Privmsg):
    def __init__(self):
        DBHandler.__init__(self)
        callbacks.Privmsg.__init__(self)
        
    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(filename)
        db = sqlite.connect(filename)
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE keys (
                          id INTEGER PRIMARY KEY,
                          key TEXT,
                          locked BOOLEAN
                          )""")
        cursor.execute("""CREATE TABLE factoids (
                          id INTEGER PRIMARY KEY,
                          key_id INTEGER,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          fact TEXT
                          )""")
        cursor.execute("""CREATE TRIGGER remove_factoids
                          BEFORE DELETE ON keys
                          BEGIN
                            DELETE FROM factoids WHERE key_id = old.id;
                          END
                       """)
        db.commit()
        return db

    def addfactoid(self, irc, msg, args):
        "[<channel>] (If not sent in the channel itself) <key> <value>"
        channel = privmsgs.getChannel(msg, args)
        (key, factoid) = privmsgs.getArgs(args, needed=2)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, locked FROM keys WHERE key=%s""", key)
        if cursor.rowcount == 0:
            cursor.execute("""INSERT INTO keys VALUES (NULL, %s, 0)""", key)
            db.commit()
            cursor.execute("""SELECT id, locked FROM keys WHERE key=%s""", key)
        (id, locked) = map(int, cursor.fetchone())
        capability = ircdb.makeChannelCapability(channel, 'factoids')
        if not locked:
            if not ircdb.checkCapability(msg.prefix, capability):
                irc.error(msg, conf.replyNoCapability % capability)
                return
            if ircdb.users.hasUser(msg.prefix):
                name = ircdb.users.getUserName(msg.prefix)
            else:
                name = msg.nick
            cursor.execute("""INSERT INTO factoids VALUES
                              (NULL, %s, %s, %s, %s)""",
                           id, name, int(time.time()), factoid)
            db.commit()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'That factoid is locked.')
        
    def lookupfactoid(self, irc, msg, args):
        "[<channel>] (If not sent in the channel itself) <key> [<number>]"
        channel = privmsgs.getChannel(msg, args)
        (key, number) = privmsgs.getArgs(args, optional=1)
        try:
            number = int(number)
        except ValueError:
            key += number
            number = 0
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT factoids.fact FROM factoids, keys WHERE
                          keys.key=%s AND factoids.key_id=keys.id
                          ORDER BY factoids.id""", key)
        results = cursor.fetchall()
        if len(results) == 0:
            irc.error(msg, 'No factoid matches that key.')
        else:
            factoid = results[number][0]
            irc.reply(msg, '%s/%s: %s' % (key, number, factoid))
            
    def lockfactoid(self, irc, msg, args):
        "[<channel>] (If not sent in the channel itself) <key>"
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args)
        db = self.getDb(channel)
        capability = ircdb.makeChannelCapability(channel, 'factoids')
        if ircdb.checkCapability(msg.prefix, capability):
            cursor = db.cursor()
            cursor.execute("""UPDATE keys SET locked = 1 WHERE key=%s""", key)
            db.commit()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)
        
    def unlockfactoid(self, irc, msg, args):
        "[<channel>] (If not sent in the channel itself) <key>"
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args)
        db = self.getDb(channel)
        capability = ircdb.makeChannelCapability(channel, 'factoids')
        if ircdb.checkCapability(msg.prefix, capability):
            cursor = db.cursor()
            cursor.execute("""UPDATE keys SET locked = 0 WHERE key=%s""", key)
            db.commit()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)

    def removefactoid(self, irc, msg, args):
        "[<channel>] (If not sent in the channel itself) <key>"
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args)
        db = self.getDb(channel)
        capability = ircdb.makeChannelCapability(channel, 'factoids')
        if ircdb.checkCapability(msg.prefix, capability):
            cursor = db.cursor()
            cursor.execute("""DELETE FROM keys WHERE key=%s""", key)
            db.commit()
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)
            
    def randomfactoid(self, irc, msg, args):
        "[<channel>] (If not sent in the channel itself)"
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT fact, key_id FROM factoids
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount != 0:
            (factoid, keyId) = cursor.fetchone()
            cursor.execute("""SELECT key FROM keys WHERE id=%s""", keyId)
            key = cursor.fetchone()[0]
            irc.reply(msg, '%s: %s' % (key, factoid))
        else:
            irc.error(msg, 'I couldn\'t find a factoid.')

    def factoidinfo(self, irc, msg, args):
        "[<channel>] (If not sent in the channel itself) <key>"
        channel = privmsgs.getChannel(msg, args)
        key = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, locked FROM keys WHERE key=%s""", key)
        if cursor.rowcount == 0:
            irc.error(msg, 'No factoid matches that key.')
            return
        (id, locked) = map(int, cursor.fetchone())
        cursor.execute("""SELECT  added_by, added_at FROM factoids
                          WHERE key_id=%s
                          ORDER BY id""", id)
        factoids = cursor.fetchall()
        L = []
        counter = 0
        for (added_by, added_at) in factoids:
            added_at = time.strftime(conf.timestampFormat,
                                     time.localtime(int(added_at)))
            L.append('#%s was added by %s at %s' % (counter,added_by,added_at))
            counter += 1
        factoids = '; '.join(L)
        s = 'Key %r is %s and has %s factoids associated with it: %s' % \
            (key, locked and 'locked' or 'not locked', counter, '; '.join(L))
        irc.reply(msg, s)
                       


Class = Factoids
