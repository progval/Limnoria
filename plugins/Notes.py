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

Commands include:
  sendnote
  note
  notes
"""

from baseplugin import *

import time
import string
import os.path

import sqlite

import conf
import debug
import utils
import ircdb
import ircmsgs
import privmsgs
import callbacks
import ircutils

dbfilename = os.path.join(conf.dataDir, 'Notes.db')

class Notes(callbacks.Privmsg):
    
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.makeDB(dbfilename)

    def makeDB(self, filename):
        "create Notes database and tables"
        if os.path.exists(filename):
            self.db = sqlite.connect(filename)
            self.cursor = self.db.cursor()
            return
        self.db = sqlite.connect(filename, converters={'bool': bool})
        self.cursor = self.db.cursor()
        self.cursor.execute("""CREATE TABLE users (
                               id INTEGER PRIMARY KEY,
                               name TEXT UNIQUE ON CONFLICT IGNORE
                               )""")
        self.cursor.execute("""CREATE TABLE notes (
                               id INTEGER PRIMARY KEY,
                               from_id INTEGER,
                               to_id INTEGER,
                               added_at TIMESTAMP,
                               read BOOLEAN,
                               public BOOLEAN,
                               note TEXT
                               )""")
        self.cursor.execute("""CREATE INDEX users_username ON users (name)""")
        self.db.commit()
   
    def _addUser(self, username):
        "Not callable from channel, used to add users to database."
        self.cursor.execute('INSERT INTO users VALUES (NULL, %s)', username)
        self.db.commit()
        
    def getUserID(self, username):
        "Returns the user id matching the given username from the users table."
        self.cursor.execute('SELECT id FROM users where name=%s', username)
        if self.cursor.rowcount != 0:
            return self.cursor.fetchone()[0]
        else: 
            raise KeyError, username

    def getUserName(self, userid):
        "Returns the username matching the given user id from the users table."
        self.cursor.execute('SELECT name FROM users WHERE id=%s', userid)
        if self.cursor.rowcount != 0:
            return self.cursor.fetchone()[0]
        else:
            raise KeyError, userid

    def isValidNote(self, noteid):
        "Checks to see if a note id represents a valid note in the table."
        self.cursor.execute('SELECT * FROM notes WHERE id=%s', noteid)
        if self.cursor.rowcount == 0:
            return False
        else:
            return True
    
    def makePrivate(self, msg):
        "Returns an IrcMsg object with an updated target value."
        return ircmsgs.privmsg(msg.nick, msg.args[1])

    def setAsRead(self, noteid):
        "Changes a message's 'read' value to true in the notes table."
        self.cursor.execute('UPDATE notes SET read=1 WHERE id=%s', noteid)
        self.db.commit()

    def die(self):
        "Called when module is unloaded/reloaded."
        self.db.close()
    
    def sendnote(self, irc, msg, args):
        """<recipient> <text>
        
        Sends a new note to the user specified.
        """
        (name, note) = privmsgs.getArgs(args, needed=2)
        sender = msg.nick
        if ircdb.users.hasUser(name):
            recipient = name
        else:
            n = irc.state.nickToHostmask(name)
            recipient = ircdb.users.getUserName(n)
        self._addUser(sender)
        self._addUser(recipient)
        senderID = self.getUserID(sender)
        recipID = self.getUserID(recipient)
        if ircutils.isChannel(msg.args[0]): 
            public = 1
        else: 
            public = 0 
        self.cursor.execute("""INSERT INTO notes VALUES 
                               (NULL, %s, %s, %s, %s, %s, %s)""", 
                               senderID, recipID, int(time.time()),
                               0, public, note)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def note(self, irc, msg, args):
        """<note id>
        
        Retrieves a single note by unique note id.
        """
        noteid = privmsgs.getArgs(args)
        if not self.isValidNote(noteid):
            irc.error(msg, 'Not a valid note id')
            return
        sender = ircdb.users.getUserName(msg.prefix)
        senderID = self.getUserID(sender)
        self.cursor.execute("""SELECT note, to_id, from_id, added_at, public 
                               FROM notes WHERE id=%s LIMIT 1""", noteid)
        note, to_id, from_id, added_at, public = self.cursor.fetchone()
        author = self.getUserName(from_id)
        public = int(public)
        added_at = int(added_at)
        elapsed = utils.timeElapsed(time.time(), added_at)
        newnote = "%s (Sent by %s %s ago)" % (note, author, elapsed)
        if senderID == to_id:
            if public:
                irc.reply(msg, newnote)
            else:
                msg = self.makePrivate(msg)
                irc.queueMsg(ircmsgs.privmsg(msg.nick, newnote))
            #debug.printf("setting note to read=true")
            self.setAsRead(noteid)
        else:
            irc.error(msg, 'You are not the recipient of note %s' % noteid)

    def notes(self, irc, msg, args):
        """<takes no arguments>
        
        Retrieves all unread notes for the requesting user.
        """
        try:
            sender = ircdb.users.getUserName(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNoUser)
            return
        senderID = self.getUserID(sender)
        self.cursor.execute("""SELECT id, from_id, public, read FROM notes
                               WHERE to_id=%s
                               AND read=0""", senderID)
        notes = self.cursor.fetchall()
        self.cursor.execute("""SELECT count(*) FROM notes 
                               WHERE to_id=%s
                               AND read=0""", senderID)
        count = int(self.cursor.fetchone()[0])
        #debug.printf("count: %s" % count)
        L = []
        for (id, from_id, public, read) in notes:
            if not int(read):
                sender = self.getUserName(from_id)
                if int(public):
                    L.append(r'#%s from %s' % (id, sender))
                else:
                    L.append(r'#%s (private)' % id)
        if count > 5:
            L = string.join(L[:5], ', ')
            reply = "you have %s unread notes, 5 shown: %s" % (count, L)
        else:
            L = string.join(L, ', ')
            reply = "you have %s unread notes: %s" % (count, L)
        #debug.printf(L)
        irc.reply(msg, reply)


Class = Notes

# vim: shiftwidth=4 tabstop=8 expandtab textwidth=78:
