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
A plugin that tries to emulate Infobot somewhat faithfully.
"""

deprecated = True

__revision__ = "$Id$"

import plugins

import re
import os.path

import conf
import ircmsgs
import callbacks

try:
    import sqlite
except ImportError:
    raise callbacks.Error, 'You need to have PySQLite installed to use this ' \
                           'plugin.  Download it at <http://pysqlite.sf.net/>'

dbfilename = os.path.join(conf.supybot.directories.data(), 'Infobot.db')

def configure(onStart):
    from questions import expect, anything, something, yn
    conf.registerPlugin('Infobot', True)

def makeDb(filename):
    if os.path.exists(filename):
        return sqlite.connect(filename)
    db = sqlite.connect(filename)
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE is_factoids (
                      key TEXT UNIQUE ON CONFLICT REPLACE,
                      value TEXT
                      )""")
    cursor.execute("""CREATE TABLE are_factoids (
                      key TEXT UNIQUE ON CONFLICT REPLACE,
                      value TEXT
                      )""")
    cursor.execute("""CREATE TABLE dont_knows (saying TEXT)""")
    for s in ('I don\'t know.', 'No idea.', 'I don\'t have a clue.', 'Dunno.'):
        cursor.execute("""INSERT INTO dont_knows VALUES (%s)""", s)
    cursor.execute("""CREATE TABLE statements (saying TEXT)""")
    for s in ('I heard', 'Rumor has it', 'I think', 'I\'m pretty sure'):
        cursor.execute("""INSERT INTO statements VALUES (%s)""", s)
    cursor.execute("""CREATE TABLE confirms (saying TEXT)""")
    for s in ('Gotcha', 'Ok', '10-4', 'I hear ya', 'Got it'):
        cursor.execute("""INSERT INTO confirms VALUES (%s)""", s)
    cursor.execute("""CREATE INDEX is_key ON is_factoids (key)""")
    cursor.execute("""CREATE INDEX are_key ON are_factoids (key)""")
    db.commit()
    return db

class Infobot(callbacks.PrivmsgRegexp):
    def __init__(self):
        callbacks.PrivmsgRegexp.__init__(self)
        self.db = makeDb(dbfilename)

    def die(self):
        self.db.commit()
        self.db.close()

    def getRandomSaying(self, table):
        cursor = self.db.cursor()
        sql = 'SELECT saying FROM %s ORDER BY random() LIMIT 1' % table
        cursor.execute(sql)
        return cursor.fetchone()[0]

    def getFactoid(self, key):
        cursor = self.db.cursor()
        cursor.execute('SELECT value FROM is_factoids WHERE key=%s', key)
        if cursor.rowcount != 0:
            statement = self.getRandomSaying('statements')
            value = cursor.fetchone()[0]
            return '%s %s is %s' % (statement, key, value)
        cursor.execute('SELECT value FROM are_factoids WHERE key=%s', key)
        if cursor.rowcount != 0:
            statement = self.getRandomSaying('statements')
            value = cursor.fetchone()[0]
            return '%s %s are %s' % (statement, key, value)
        raise KeyError, key

    def hasFactoid(self, key, isAre):
        cursor = self.db.cursor()
        sql = 'SELECT COUNT(*) FROM %s_factoids WHERE key=%%s' % isAre
        cursor.execute(sql, key)
        return int(cursor.fetchone()[0])

    def insertFactoid(self, key, isAre, value):
        cursor = self.db.cursor()
        sql = 'INSERT INTO %s_factoids VALUES (%%s, %%s)' % isAre
        cursor.execute(sql, key, value)
        self.db.commit()

    def forget(self, irc, msg, match):
        r"^forget\s+(.+?)(?!\?+)[?.! ]*$"
        key = match.group(1)
        cursor = self.db.cursor()
        cursor.execute('DELETE FROM is_factoids WHERE key=%s', key)
        cursor.execute('DELETE FROM are_factoids WHERE key=%s', key)
        irc.reply(self.getRandomSaying('confirms'))

    def tell(self, irc, msg, match):
        r"^tell\s+(.+?)\s+about\s+(.+?)(?!\?+)[.! ]*$"
        (nick, key) = match.groups()
        try:
            s = '%s wants you to know that %s' %(msg.nick,self.getFactoid(key))
            irc.reply(nick, s)
        except KeyError:
            irc.reply('I don\'t know anything about %s' % key)

    def factoid(self, irc, msg, match):
        r"^(no[ :,-]+)?(.+?)\s+(was|is|am|were|are)\s+(also\s+)?(.+?)(?!\?+)$"
        (correction, key, isAre, addition, value) = match.groups()
        if self.hasFactoid(key, isAre):
            if not correction:
                factoid = self.getFactoid(key)
                irc.reply('No, %s %s %s' % (key, isAre, factoid))
            elif addition:
                factoid = self.getFactoid(key)
                newFactoid = '%s, or %s' % (factoid, value)
                self.insertFactoid(key, isAre, newFactoid)
                irc.reply(self.getRandomSaying('confirms'))
            else:
                self.insertFactoid(key, isAre, value)
                irc.reply(self.getRandomSaying('confirms'))
            return
        else:
            self.insertFactoid(key, isAre, value)
            irc.reply(self.getRandomSaying('confirms'))

    def unknown(self, irc, msg, match):
        r"^(.+?)\?[?.! ]*$"
        key = match.group(1)
        try:
            irc.reply(self.getFactoid(key))
        except KeyError:
            irc.reply(self.getRandomSaying('dont_knows'))

    def info(self, irc, msg, match):
        r"^info$"
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM is_factoids")
        numIs = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM are_factoids")
        numAre = cursor.fetchone()[0]
        s = 'I have %s is factoids and %s are factoids' % (numIs, numAre)
        irc.reply(s)




Class = Infobot

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2 and sys.argv[1] not in ('is', 'are'):
        print 'Usage: %s <is|are> <factpack> [<factpack> ...]' % sys.argv[0]
        sys.exit(-1)
    r = re.compile(r'\s+=>\s+')
    db = makeDb(dbfilename)
    cursor = db.cursor()
    if sys.argv[1] == 'is':
        table = 'is_factoids'
    else:
        table = 'are_factoids'
    sql = 'INSERT INTO %s VALUES (%%s, %%s)' % table
    for filename in sys.argv[2:]:
        fd = file(filename)
        for line in fd:
            line = line.strip()
            if not line or line[0] in ('*', '#'):
                continue
            else:
                try:
                    (key, value) = r.split(line, 1)
                    cursor.execute(sql, key, value)
                except Exception, e:
                    print 'Invalid line (%s): %r' %(utils.exnToString(e),line)
    db.commit()


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
