#!/usr/bin/env python

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
The Dunno module is used to spice up the "replyWhenNotCommand" behavior with
random "I dunno"-like responses.
"""

__revision__ = "$Id$"

import os
import time

import conf
import utils
import ircdb
import plugins
import privmsgs
import callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

dbfilename = os.path.join(conf.supybot.directories.data(), 'Dunno.db')

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
            irc.reply(dunno, prefixName=False)

    def add(self, irc, msg, args):
        """<text>

        Adds <text> as a "dunno" to be used as a random response when no
        command or factoid key matches.  Can optionally contain '$who', which
        will be replaced by the user's name when the dunno is displayed.
        """
        # Must be registered to use this
        try:
            user_id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        text = privmsgs.getArgs(args)
        cursor = self.db.cursor()
        at = int(time.time())
        cursor.execute("""INSERT INTO dunnos VALUES(NULL, %s, %s, %s)""",
                          user_id, at, text)
        self.db.commit()
        cursor.execute("""SELECT id FROM dunnos WHERE added_at=%s""", at)
        id = cursor.fetchone()[0]
        irc.replySuccess('Dunno #%s added.' % id)

    def remove(self, irc, msg, args):
        """<id>

        Removes dunno with the given <id>.
        """
        # Must be registered to use this
        try:
            user_id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        dunno_id = privmsgs.getArgs(args, required=1)
        cursor = self.db.cursor()
        cursor.execute("""SELECT added_by, dunno FROM dunnos
                          WHERE id=%s""", dunno_id)
        if cursor.rowcount == 0:
            irc.error('No dunno with id #%s.' % dunno_id)
            return
        (added_by, dunno) = cursor.fetchone()
        if not (ircdb.checkCapability(user_id, 'admin') or \
                added_by == user_id):
            irc.error('Only admins and the dunno creator may delete a dunno.')
            return
        cursor.execute("""DELETE FROM dunnos WHERE id=%s""", dunno_id)
        self.db.commit()
        irc.replySuccess()

    def search(self, irc, msg, args):
        """<text>

        Search for dunno containing the given text.  Returns the ids of the
        dunnos with the text in them.
        """
        text = privmsgs.getArgs(args, required=1)
        glob = "%" + text + "%"
        cursor = self.db.cursor()
        cursor.execute("""SELECT id FROM dunnos WHERE dunno LIKE %s""", glob)
        if cursor.rowcount == 0:
            irc.error('No dunnos with %r found.' % text)
            return
        ids = [str(t[0]) for t in cursor.fetchall()]
        s = 'Dunno search for %r (%s found): %s.' % \
            (text, len(ids), utils.commaAndify(ids))
        irc.reply(s)

    def get(self, irc, msg, args):
        """<id>

        Display the text of the dunno with the given id.
        """
        id = privmsgs.getArgs(args, required=1)
        try:
            id = int(id)
        except ValueError:
            irc.error('%r is not a valid dunno id.' % id)
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT dunno FROM dunnos WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error('No dunno found with id #%s.' % id)
            return
        dunno = cursor.fetchone()[0]
        irc.reply("Dunno #%s: %r." % (id, dunno))

    def change(self, irc, msg, args):
        """<id> <regexp>

        Alters the dunno with the given id according to the provided regexp.
        """
        id, regexp = privmsgs.getArgs(args, required=2)
        # Must be registered to use this
        try:
            user_id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            irc.errorNotRegistered()
            return
        # Check id arg
        try:
            id = int(id)
        except ValueError:
            irc.error('%r is not a valid dunno id.' % id)
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT dunno FROM dunnos WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error('There is no dunno #%s.' % id)
            return
        try:
            replacer = utils.perlReToReplacer(regexp)
        except:
            irc.error('%r is not a valid regular expression.' % regexp)
            return
        dunno = cursor.fetchone()[0]
        new_dunno = replacer(dunno)
        cursor.execute("""UPDATE dunnos SET dunno=%s WHERE id=%s""",
                       new_dunno, id)
        self.db.commit()
        irc.replySuccess()
        


Class = Dunno

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
