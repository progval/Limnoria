#!/usr/bin/python

###
# Copyright (c) 2003, Daniel DiPaolo
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
Add the module docstring here.  This will be used by the setup.py script.
"""

import os
import conf
import time
import ircdb
import sqlite
__revision__ = "$Id$"

import plugins

import utils
import privmsgs
import callbacks

dbfilename = os.path.join(conf.dataDir, 'Dunno.db')

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Dunno')

class Dunno(callbacks.Privmsg):
    priority = 100
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.makeDb(dbfilename)
    
    def makeDb(self, filename):
        """create Dunno database and tables"""
        if os.path.exists(filename):
            self.db = sqlite.connect(filename)
            return
        self.db = sqlite.connect(filename, converters={'bool': bool})
        cursor = self.db.cursor()
        cursor.execute("""CREATE TABLE dunnos (
                          id INTEGER PRIMARY KEY,
                          added_by INTEGER,
                          added_at TIMESTAMP,
                          dunno TEXT
                          )""")
        self.db.commit()
        
    def invalidCommand(self, irc, msg, tokens):
        cursor = self.db.cursor()
        cursor.execute("""SELECT dunno
                          FROM dunnos
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount != 0:
            dunno = cursor.fetchone()[0]
            dunno = plugins.standardSubstitute(irc, msg, dunno)
            irc.reply(msg, dunno, prefixName=False)

    def add(self, irc, msg, args):
        """<text>

        Adds <text> as a "dunno" to be used as a random response when no
        command or factoid key matches.  Can optionally contain '$who', which
        will be replaced by the user's name when the dunno is displayed.
        """
        # Must be registered to use this
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        text = privmsgs.getArgs(args, required=1)
        cursor = self.db.cursor()
        cursor.execute("""INSERT INTO dunnos
                          VALUES(NULL, %s, %s, %s)""",
                          id, int(time.time()), text)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def remove(self, irc, msg, args):
        """<id>

        Removes dunno with the given <id>.
        """
        # Must be registered to use this
        try:
            user_id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        dunno_id = privmsgs.getArgs(args, required=1)
        cursor = self.db.cursor()
        cursor.execute("""SELECT added_by, dunno
                          FROM dunnos
                          WHERE id = %s""" % dunno_id)
        if cursor.rowcount == 0:
            irc.error(msg, 'No dunno with id: %s' % dunno_id)
            return
        (added_by, dunno) = cursor.fetchone()
        if not (ircdb.checkCapability(user_id, 'admin') or \
                added_by == user_id):
            irc.error(msg, 'Only admins and the dunno creator may delete a '
                           'dunno.')
            return
        cursor.execute("""DELETE FROM dunnos WHERE id = %s""" % dunno_id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def search(self, irc, msg, args):
        """<text>

        Search for dunno containing the given text.  Returns the ids of the
        dunnos with the text in them.
        """
        text = privmsgs.getArgs(args, required=1)
        glob = "%" + text + "%"
        cursor = self.db.cursor()
        cursor.execute("""SELECT id FROM dunnos
                          WHERE dunno LIKE %s""", glob)
        if cursor.rowcount == 0:
            irc.error(msg, 'No dunnos with %r found.' % text)
            return
        ids = [str(t[0]) for t in cursor.fetchall()]
        s = 'Dunno search for %r (%s found): %s' % \
            (text, len(ids), utils.commaAndify(ids))
        irc.reply(msg, s)

    def get(self, irc, msg, args):
        """<id>

        Display the text of the dunno with the given id.
        """
        id = privmsgs.getArgs(args, required=1)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, '%r is not a valid dunno id' % id)
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT dunno FROM dunnos WHERE id = %s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'No dunno found with id #%s' % id)
            return
        dunno = cursor.fetchone()[0]
        irc.reply(msg, "Dunno #%s: %r" % (id, dunno))

Class = Dunno

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
