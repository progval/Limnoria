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

__revision__ = "$Id$"

import plugins

import time
import getopt
import os.path
from itertools import imap

import conf
import utils
import ircdb
import ircmsgs
import plugins
import privmsgs
import ircutils
import callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

class NoteDb(plugins.DBHandler):
    def makeDb(self, filename):
        "create Notes database and tables"
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename, converters={'bool': bool})
            cursor = db.cursor()
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
            db.commit()
        return db
        


class Note(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        dataDir = conf.supybot.directories.data()
        self.dbHandler = NoteDb(name=os.path.join(dataDir, 'Notes'))

    def setAsRead(self, id):
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""UPDATE notes
                          SET read=1, notified=1
                          WHERE id=%s""", id)
        db.commit()

    def die(self):
        self.dbHandler.die()

    def doPrivmsg(self, irc, msg):
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            return
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT COUNT(*) FROM notes
                          WHERE notes.to_id=%s AND notified=0""", id)
        unnotified = int(cursor.fetchone()[0])
        if unnotified != 0:
            cursor.execute("""SELECT COUNT(*) FROM notes
                              WHERE notes.to_id=%s AND read=0""", id)
            unread = int(cursor.fetchone()[0])
            s = 'You have %s; ' \
                '%s that I haven\'t told you about before now..' % \
                (utils.nItems('note', unread, 'unread'), unnotified)
            irc.queueMsg(ircmsgs.privmsg(msg.nick, s))
            cursor.execute("""UPDATE notes SET notified=1
                              WHERE notes.to_id=%s""", id)
            db.commit()

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
                irc.errorNoUser()
                return
        try:
            fromId = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        if ircutils.isChannel(msg.args[0]):
            public = 1
        else:
            public = 0
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        now = int(time.time())
        cursor.execute("""INSERT INTO notes VALUES
                          (NULL, %s, %s, %s, 0, 0, %s, %s)""",
                       fromId, toId, now, public, note)
        db.commit()
        cursor.execute("""SELECT id FROM notes WHERE
                          from_id=%s AND to_id=%s AND added_at=%s""",
                       fromId, toId, now)
        id = cursor.fetchone()[0]
        irc.reply('Note #%s sent to %s.' % (id, name))

    def unsend(self, irc, msg, args):
        """<id>

        Unsends the note with the id given.  You must be the
        author of the note, and it must be unread.
        """
        id = privmsgs.getArgs(args)
        try:
            userid = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT from_id, read FROM notes WHERE id=%s""", id)
        if cursor.rowcount < 1:
            irc.error('That\'s not a valid note id.')
            return
        (from_id, read) = map(int, cursor.fetchone())
        if from_id == userid:
            if not read:
                cursor.execute("""DELETE FROM notes WHERE id=%s""", id)
                db.commit()
                irc.replySuccess()
            else:
                irc.error('That note has been read already.')
        else:
            irc.error('That note wasn\'t sent by you.')
            

    def note(self, irc, msg, args):
        """<note id>

        Retrieves a single note by its unique note id.
        """
        noteid = privmsgs.getArgs(args)
        if noteid.startswith('get'):
            irc.error('The Note.get command has changed to be simply "note".')
            return
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        try:
            noteid = int(noteid)
        except ValueError:
            irc.error('%r is not a valid note id.' % noteid)
            return
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute("""SELECT note, to_id, from_id, added_at, public
                          FROM notes
                          WHERE (to_id=%s OR from_id=%s) AND id=%s""",
                       id, id, noteid)
        if cursor.rowcount < 1:
            s = 'You may only retrieve notes you\'ve sent or received.'
            irc.error(s)
            return
        (note, toId, fromId, addedAt, public) = cursor.fetchone()
        (toId,fromId,addedAt,public) = imap(int, (toId,fromId,addedAt,public))
        elapsed = utils.timeElapsed(time.time() - addedAt)
        if toId == id:
            author = ircdb.users.getUser(fromId).name
            newnote = '%s (Sent by %s %s ago)' % (note, author, elapsed)
        elif fromId == id:
            recipient = ircdb.users.getUser(toId).name
            newnote = '%s (Sent to %s %s ago)' % (note, recipient, elapsed)
        irc.reply(newnote, private=(not public))
        self.setAsRead(noteid)

    def _formatNoteData(self, msg, id, fromId, public, sent=False):
        (id, fromId, public) = imap(int, (id, fromId, public))
        if public or not ircutils.isChannel(msg.args[0]):
            sender = ircdb.users.getUser(fromId).name
            if sent:
                return '#%s to %s' % (id, sender)
            else:
                return '#%s from %s' % (id, sender)
        else:
            return '#%s (private)' % id

    def list(self, irc, msg, args):
        """[--{old,sent}] [--{from,to} <user>]

        Retrieves the ids of all your unread notes.  If --old is given, list
        read notes.  If --sent is given, list notes that you have sent.  If
        --from is specified, only lists notes sent to you from <user>.  If
        --to is specified, only lists notes sent by you to <user>.
        """
        options = ['old', 'sent', 'from=', 'to=']
        (optlist, rest) = getopt.getopt(args, '', options)
        sender, receiver, old, sent = ('', '', False, False)
        for (option, arg) in optlist:
            option = option.lstrip('-')
            if option == 'old':
                old = True
            if option == 'sent':
                sent = True
            if option == 'from':
                sender = arg
            if option == 'to':
                receiver = arg
                sent = True
        if old:
            return self._oldnotes(irc, msg, sender)
        if sent:
            return self._sentnotes(irc, msg, receiver)
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        sql = """SELECT id, from_id, public
                 FROM notes
                 WHERE notes.to_id=%r AND notes.read=0""" % id
        if sender:
            try:
                sender = ircdb.users.getUserId(sender)
            except KeyError:
                irc.error('That user is not in my user database.')
                return
            sql = '%s %s' % (sql, 'AND notes.from_id=%r' % sender)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute(sql)
        count = cursor.rowcount
        if count < 1:
            irc.reply('You have no unread notes.')
        else:
            L = [self._formatNoteData(msg, *t) for t in cursor.fetchall()]
            L = self._condense(L)
            irc.reply(utils.commaAndify(L))

    def _condense(self, notes):
        temp = {}
        for note in notes:
            note = note.split(' ', 1)
            if note[1] in temp:
                temp[note[1]].append(note[0])
            else:
                temp[note[1]] = [note[0]]
        notes = []
        for (k,v) in temp.iteritems():
            notes.append('%s %s' % (', '.join(v), k))
        return notes

    def _sentnotes(self, irc, msg, receiver):
        """takes no arguments

        Returns a list of your most recent old notes.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        sql = """SELECT id, to_id, public
                 FROM notes
                 WHERE notes.from_id=%r""" % id
        if receiver:
            try:
                receiver = ircdb.users.getUserId(receiver)
            except KeyError:
                irc.error('That user is not in my user database.')
                return
            sql = '%s %s' % (sql, 'AND notes.to_id=%r' % receiver)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute(sql)
        if cursor.rowcount < 1:
            irc.reply('I couldn\'t find any sent notes for your user.')
        else:
            ids = [self._formatNoteData(msg, sent=True, *t) for t in
                   cursor.fetchall()]
            ids = self._condense(ids)
            irc.reply(utils.commaAndify(ids))

    def _oldnotes(self, irc, msg, sender):
        """takes no arguments

        Returns a list of your most recent old notes.
        """
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        sql = """SELECT id, from_id, public
                 FROM notes
                 WHERE notes.to_id=%r AND notes.read=1""" % id
        #self.log.warning(sender)
        if sender:
            try:
                sender = ircdb.users.getUserId(sender)
            except KeyError:
                irc.error('That user is not in my user database.')
                return
            sql = '%s %s' % (sql, 'AND notes.from_id=%r' % sender)
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        cursor.execute(sql)
        #self.log.warning(cursor.rowcount)
        if cursor.rowcount < 1:
            irc.reply('I couldn\'t find any read notes for your user.')
        else:
            ids = [self._formatNoteData(msg, *t) for t in cursor.fetchall()]
            #self.log.warning(ids)
            ids.reverse()
            ids = self._condense(ids)
            irc.reply(utils.commaAndify(ids))


Class = Note

# vim: shiftwidth=4 tabstop=8 expandtab textwidth=78:
