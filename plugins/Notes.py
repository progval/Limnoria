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

example = utils.wrapLines("""
<jemfinch> @list Notes
<supybot> note, notes, oldnotes, sendnote
<jemfinch> @notes
<supybot> You have no unread notes.
<jemfinch> @oldnotes
<supybot> 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 15, 17, 18, 19, 25, 26, 27, 28, 37, 40, 41, 47
<jemfinch> @note 1
<supybot> I read their site, lurk on their forums and help out with the dc competitions (Sent by jamessan 18 weeks, 1 day, 6 hours, 46 minutes, and 53 seconds ago)
<jemfinch> @note 28
<supybot> er, you might want to change the ChannelStats module to ChannelDB in your conf file as well (Sent by Strike 2 weeks, 2 days, 20 hours, 11 minutes, and 58 seconds ago)
<jemfinch> @sendnote jemfinch hey, this is a note from yourself.
<supybot> The operation succeeded.
* jemfinch blah blah (he'll tell me I have unread notes)
<supybot> You have 1 unread note; 1 that I haven't told you about before now..
<jemfinch> @notes
<supybot> #49 from jemfinch
<jemfinch> @note 49
<supybot> hey, this is a note from yourself. (Sent by jemfinch 20 seconds ago)
""")

class Notes(callbacks.Privmsg):
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
            callbacks.Privmsg.doPrivmsg(self, irc, msg)
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
        callbacks.Privmsg.doPrivmsg(self, irc, msg)

    def sendnote(self, irc, msg, args):
        """<recipient> <text>

        Sends a new note to the user specified.
        """
        (name, note) = privmsgs.getArgs(args, needed=2)
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
        cursor.execute("""INSERT INTO notes VALUES
                          (NULL, %s, %s, %s, 0, 0, %s, %s)""",
                       fromId, toId, int(time.time()), public, note)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def note(self, irc, msg, args):
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
                          WHERE notes.to_id=%s AND notes.id=%s""",
                       id, noteid)
        if cursor.rowcount == 0:
            irc.error(msg, 'That\'s not a valid note id for you.')
            return
        (note, toId, fromId, addedAt, public) = cursor.fetchone()
        (toId,fromId,addedAt,public) = map(int, (toId,fromId,addedAt,public))
        author = ircdb.users.getUser(fromId).name
        elapsed = utils.timeElapsed(time.time() - addedAt)
        newnote = "%s (Sent by %s %s ago)" % (note, author, elapsed)
        if public:
            irc.reply(msg, newnote)
        else:
            ### FIXME: IrcObjectProxy should offer a private keyword arg.
            irc.queueMsg(ircmsgs.privmsg(msg.nick, newnote))
        self.setAsRead(noteid)

    def _formatNoteData(self, msg, id, fromId, public):
        (id, fromId, public) = map(int, (id, fromId, public))
        if public or not ircutils.isChannel(msg.args[0]):
            sender = ircdb.users.getUser(fromId).name
            return '#%s from %s' % (id, sender)
        else:
            return '#%s (private)' % id

    def notes(self, irc, msg, args):
        """takes no arguments

        Retrieves the ids of all your unread notes.
        """
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

    def oldnotes(self, irc, msg, args):
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



Class = Notes

# vim: shiftwidth=4 tabstop=8 expandtab textwidth=78:
