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

import re
import time
import os.path

import sqlite

import ircdb
import privmsgs
import callbacks

class Quotes(DBHandler, callbacks.Privmsg):
    def __init__(self):
        DBHandler.__init__(self)
        callbacks.Privmsg.__init__(self)

    def makeDb(self, filename):
        if os.path.exists(filename):
            return sqlite.connect(db=filename, mode=0755,
                                  converters={'bool': bool})
        #else:
        db = sqlite.connect(db=filename, mode=0755, coverters={'bool': bool})
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE quotes (
                          id INTEGER PRIMARY KEY,
                          added_by VARCHAR(255),
                          added_at TIMESTAMP,
                          quote TEXT
                          );""")
        db.commit()
        return db

    def addquote(self, irc, msg, args):
        "[<channel>] (if not sent through the channel itself) <quote>"
        channel = privmsgs.getChannel(msg, args)
        quote = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""INSERT INTO quotes
                         VALUES(NULL, %s, %s, %s)""",
                       msg.nick, int(time.time()), quote)
        db.commit()
        irc.reply(msg, conf.replySuccess)

    def maxquote(self, irc, msg, args):
        "[<channel>] (if not sent through the channel itself)"
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT max(id) FROM quotes""")
        maxid = cursor.fetchone()[0]
        if maxid is None:
            maxid = 0
        s = 'There are approximately %s quotes in the database.' % maxid
        irc.reply(msg, s)

    def quote(self, irc, msg, args):
        "[<channel>] (if not sent through the channel itself) <number|regexp>"
        channel = privmsgs.getChannel(msg, args)
        value = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        try:
            id = int(value)
            cursor.execute("""SELECT quote FROM quotes WHERE id=%s""", id)
            ret = cursor.fetchall()
            if ret:
                irc.reply(msg, ret[0][0])
                return
            else:
                irc.reply(msg, "That quote doesn't exist.")
                return
        except ValueError: # It's not an int.
            r = re.compile(value, re.I)
            def p(s):
                return bool(r.match(s))
            db.create_function('p', 1, p)
            cursor.execute("""SELECT id, quote FROM quotes WHERE p(quote)""")
            if cursor.rowcount == 0:
                irc.reply(msg, 'No quotes matched that regexp.')
                return
            elif cursor.rowcount == 1:
                (id, quote) = cursor.fetchone()
                irc.reply(msg, 'Quote %s: %s' % (id, quote))
                return
            elif cursor.rowcount > 5:
                ids = [t[0] for t in cursor.fetchall()]
                irc.reply(msg, 'Quotes %s matched.' % ', '.join(ids))
                return
            else:
                L = ['%s: %s' % (id,s[:30]) for (id,s) in cursor.fetchall()]
                irc.reply(msg, 'These quotes matched: %s' % ', '.join(L))
                return

    def randomquote(self, irc, msg, args):
        "[<channel>] (if not sent through the channel itself)"
        channel = privmsgs.getChannel(msg, args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT quote FROM quotes
                          ORDER BY random()
                          LIMIT 1""")
        quote = cursor.fetchone()[0]
        irc.reply(msg, quote)
        return

    def quoteinfo(self, irc, msg, args):
        "[<channel>] (if not sent through the channel itself) <number>"
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT * FROM quotes WHERE id=%s""", id)
        row = cursor.fetchone()
        if row:
            irc.reply(msg, 'Quote %r added by %s at %s.' % \
               (row.quote, row.added_by, time.strftime(conf.timestampFormat)))
            return
        else:
            irc.reply(msg, 'There isn\'t a quote with that id.')
            return

    def removequote(self, irc, msg, args):
        "[<channel>] (if not sent through the channel itself) <number>"
        channel = privmsgs.getChannel(msg, args)
        id = privmsgs.getArgs(args)
        db = self.getDb(channel)
        cursor = db.cursor()
        capability = ircdb.makeChannelCapability(channel, 'op')
        if ircdb.checkCapability(msg.prefix, capability):
            cursor.execute("""DELETE FROM quotes WHERE id=%s""", id)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, conf.replyNoCapability % capability)
        

Class = Quotes
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
