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

# add read delete count 
# Jeremy: ircdb.users.getUserName(msg.prefix)

from baseplugin import *

import time
import os.path

import sqlite

import conf
import ircdb
import privmsgs
import callbacks

class Notes(DBHandler, callbacks.Privmsg):
    
    def __init__(self):
        DBHandler.__init__(self)
        callbacks.Privmsg.__init__(self)
        self.filname = os.path.join(conf.dataDir, 'Notes.db')
        if os.path.exists(self.filename):
            self.db = sqlite.connect(self.filename)
            self.cursor = self.db.cursor()
        else:
            self.makeDB()


    def makeDB(self):
        "create Notes database and tables"
        self.db = sqlite.connect(self.filename)
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
        self.cursor.execute("""CREATE INDEX users_username 
                               ON users (username)""")
        self.db.commit()
   
    def _addUser(self, username):
        "not callable from channel, used to add users to database"
        self.cursor.execute("""INSERT INTO users
                               VALUES ('%s')""" % username)
        self.db.commit()
        
    def getUserID(self, username):
        self.cursor.execute("""SELECT id FROM users 
                               where name='%s'""" % username)
        if self.cursor.rowcount != 0:
            results = self.cursor.fetchall()
            return results[0]
        else: # this should NEVER happen
            return "ERROR"

    def setNoteUnread(self, irc, msg, args):
        "set a note as unread"
        
        self.cursor.execute("""UPDATE notes
                               SET read="False"
                               where id = %d""" % int(noteNum))
        self.db.commit()
        
    def sendNote(self, irc, msg, args):
        (name, note) = privmsgs.getArgs(args, needed=2)
        sender = ircdb.users.getUserName(msg.prefix)
        if ircdb.users.hasUser(name):
            recipient = ircdb.users.getUserName(name)
        else:
            n = irc.state.nickToHostmask(name)
            recipient = ircdb.users.getUserName(n)
        _addUser(sender)
        _addUser(recipient)
        senderID = self.getUserID(sender)
        recipID = self.getUserID(recipient)
        if msg.args[0][0] == "#": public = "True"
        else: public = "False"
        self.cursor.execute("""INSERT INTO notes
                               VALUES (%d,%d,%d,%s,'False',%s)""" %\
                               (int(senderID), int(recipID), int(time.time()),
                               public, note))
        self.db.commit()

    
