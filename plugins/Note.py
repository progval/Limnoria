#!/usr/bin/env python

###
# Copyright (c) 2003, Brett Kelly
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
A complete messaging system that allows users to leave 'notes' for other
users that can be retrieved later.
"""

import plugins

import time
import os.path

import sqlite

import conf
import debug
import utils
import ircdb
import ircmsgs
import privmsgs
import ircutils
import callbacks

dbfilename = os.path.join(conf.dataDir, 'Notes.db')

class Note(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.makeDB(dbfilename)

    def makeDB(self, filename):
        "create Notes database and tables"
        if os.path.exists(filename):
            self.db = sqlite.connect(filename)
            return
        self.db = sqlite.connect(filename, converters={'bool': bool})
        cursor = self.db.cursor()
        cursor.execute("""CREATE TABLE notes (
                          id INTEGER PRIMARY KEY,
                          from_id INTEGER,
                          to_id INTEGER,
                          added_at TIMESTAMP,
                          notified BOOLEAN,
                          read BOOLEAN,
                          public BOOLEAN,
                          note TEXT
                          )""")
        self.db.commit()

    def setAsRead(self, id):
        cursor = self.db.cursor()
        cursor.execute("""UPDATE notes
                          SET read=1, notified=1
                          WHERE id=%s""", id)
        self.db.commit()

    def die(self):
        self.db.commit()
        self.db.close()
        del self.db

    def doPrivmsg(self, irc, msg):
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM notes
                          WHERE notes.to_id=%s AND notified=0""", id)
        unnotified = int(cursor.fetchone()[0])
        if unnotified != 0:
            cursor.execute("""SELECT COUNT(*) FROM notes
                              WHERE notes.to_id=%s AND read=0""", id)
            unread = int(cursor.fetchone()[0])
            s = 'You have %s; ' \
                '%s that I haven\'t told you about before now..' % \
                (utils.nItems(unread, 'note', 'unread'), unnotified)
            irc.queueMsg(ircmsgs.privmsg(msg.nick, s))
            cursor.execute("""UPDATE notes SET notified=1
                              WHERE notes.to_id=%s""", id)
            self.db.commit()

    def send(self, irc, msg, args):
        """<recipient> <text>

        Sends a new note to the user specified.
        """
        (name, note) = privmsgs.getArgs(args, required=2)
        if ircdb.users.hasUser(name):
            toId = ircdb.users.getUserId(name)
        else:
            # name must be a nick, we'll try that.
            try:
                hostmask = irc.state.nickToHostmask(name)
                toId = ircdb.users.getUserId(hostmask)
            except KeyError:
                irc.error(msg, conf.replyNoUser)
                return
        try:
            fromId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        if ircutils.isChannel(msg.args[0]):
            public = 1
        else:
            public = 0
        cursor = self.db.cursor()
        now = int(time.time())
        cursor.execute("""INSERT INTO notes VALUES
                          (NULL, %s, %s, %s, 0, 0, %s, %s)""",
                       fromId, toId, now, public, note)
        self.db.commit()
        cursor.execute("""SELECT id FROM notes WHERE
                          from_id=%s AND to_id=%s AND added_at=%s""",
                       fromId, toId, now)
        id = cursor.fetchone()[0]
        irc.reply(msg, 'Note #%s sent to %s.' % (id, name))

    def get(self, irc, msg, args):
        """<note id>

        Retrieves a single note by its unique note id.
        """
        noteid = privmsgs.getArgs(args)
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT note, to_id, from_id, added_at, public
                          FROM notes
                          WHERE (to_id=%s OR from_id=%s) AND id=%s""",
                       id, id, noteid)
        if cursor.rowcount == 0:
            s = 'You may only retrieve notes you\'ve sent or received.'
            irc.error(msg, s)
            return
        (note, toId, fromId, addedAt, public) = cursor.fetchone()
        (toId,fromId,addedAt,public) = map(int, (toId,fromId,addedAt,public))
        elapsed = utils.timeElapsed(time.time() - addedAt)
        if toId == id:
            author = ircdb.users.getUser(fromId).name
            newnote = '%s (Sent by %s %s ago)' % (note, author, elapsed)
        elif fromId == id:
            recipient = ircdb.users.getUser(toId).name
            newnote = '%s (Sent to %s %s ago)' % (note, recipient, elapsed)
        irc.reply(msg, newnote, private=(not public))
        self.setAsRead(noteid)

    def _formatNoteData(self, msg, id, fromId, public):
        (id, fromId, public) = map(int, (id, fromId, public))
        if public or not ircutils.isChannel(msg.args[0]):
            sender = ircdb.users.getUser(fromId).name
            return '#%s from %s' % (id, sender)
        else:
            return '#%s (private)' % id

    def list(self, irc, msg, args):
        """[--old]

        Retrieves the ids of all your unread notes.  If --old is given, list
        read notes.
        """
        if '--old' in args:
            while '--old' in args:
                args.remove('--old')
            return self._oldnotes(irc, msg, args)
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, from_id, public
                          FROM notes
                          WHERE notes.to_id=%s AND notes.read=0""", id)
        count = cursor.rowcount
        L = []
        if count == 0:
            irc.reply(msg, 'You have no unread notes.')
        else:
            L = [self._formatNoteData(msg, *t) for t in cursor.fetchall()]
            irc.reply(msg, utils.commaAndify(L))

    def _oldnotes(self, irc, msg, args):
        """takes no arguments

        Returns a list of your most recent old notes.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, from_id, public
                          FROM notes
                          WHERE notes.to_id=%s AND notes.read=1""", id)
        if cursor.rowcount == 0:
            irc.reply(msg, 'I couldn\'t find any read notes for your user.')
        else:
            ids = [self._formatNoteData(msg, *t) for t in cursor.fetchall()]
            ids.reverse()
            irc.reply(msg, utils.commaAndify(ids))


Class = Note

# vim: shiftwidth=4 tabstop=8 expandtab textwidth=78:
