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
Provides fun commands that require a database to operate.
"""

import plugins

import re
import sets
import time
import string
import os.path

import sqlite

import conf
import debug
import ircdb
import utils
import world
import ircmsgs
import ircutils
import privmsgs
import callbacks

dbFilename = os.path.join(conf.dataDir, 'FunDB.db')

tableCreateStatements = {
    'larts': ("""CREATE TABLE larts (
                 id INTEGER PRIMARY KEY,
                 lart TEXT,
                 added_by TEXT
                 )""",),
    'praises': ("""CREATE TABLE praises (
                   id INTEGER PRIMARY KEY,
                   praise TEXT,
                   added_by TEXT
                   )""",),
    'insults': ("""CREATE TABLE insults (
                   id INTEGER PRIMARY KEY,
                   insult TEXT,
                   added_by TEXT
                   )""",),
    'excuses': ("""CREATE TABLE excuses (
                   id INTEGER PRIMARY KEY,
                   excuse TEXT,
                   added_by TEXT
                   )""",),
    'words': ("""CREATE TABLE words (
                 id INTEGER PRIMARY KEY,
                 word TEXT UNIQUE ON CONFLICT IGNORE,
                 sorted_word_id INTEGER
                 )""",
              """CREATE INDEX sorted_word_id ON words (sorted_word_id)""",
              """CREATE TABLE sorted_words (
                 id INTEGER PRIMARY KEY,
                 word TEXT UNIQUE ON CONFLICT IGNORE
                 )""",
              """CREATE INDEX sorted_words_word ON sorted_words (word)"""),
    }
    
def makeDb(dbfilename, replace=False):
    if os.path.exists(dbfilename):
        if replace:
            os.remove(dbfilename)
    db = sqlite.connect(dbfilename)
    cursor = db.cursor()
    for table in tableCreateStatements:
        try:
            cursor.execute("""SELECT * FROM %s LIMIT 1""" % table)
        except sqlite.DatabaseError: # The table doesn't exist.
            for sql in tableCreateStatements[table]:
                cursor.execute(sql)
    db.commit()
    return db

def addWord(db, word, commit=False):
    word = word.strip().lower()
    L = list(word)
    L.sort()
    sorted = ''.join(L)
    cursor = db.cursor()
    cursor.execute("""INSERT INTO sorted_words VALUES (NULL, %s)""", sorted)
    cursor.execute("""INSERT INTO words VALUES (NULL, %s,
                      (SELECT id FROM sorted_words
                       WHERE word=%s))""", word, sorted)
    if commit:
        db.commit()


class FunDB(callbacks.Privmsg):
    """
    Contains the 'fun' commands that require a database.  Currently includes
    database-backed commands for crossword puzzle solving, anagram searching,
    larting, praising, excusing, and insulting.
    """
    _tables = sets.Set(['lart', 'insult', 'excuse', 'praise'])
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = makeDb(dbFilename)
        cursor = self.db.cursor()

    def die(self):
        self.db.commit()
        self.db.close()
        del self.db

    def insult(self, irc, msg, args):
        """<nick>

        Insults <nick>.
        """
        nick = privmsgs.getArgs(args)
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, insult FROM insults
                          WHERE insult NOT NULL
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error(msg, 'There are currently no available insults.')
            return
        (id, insult) = cursor.fetchone()
        nick = nick.strip()
        if nick in (irc.nick, 'yourself', 'me'):
            insultee = msg.nick
        else:
            insultee = nick
        if ircutils.isChannel(msg.args[0]):
            means = msg.args[0]
            s = '%s: %s (#%s)' % (insultee, insult, id)
        else:
            means = insultee
            s = insult
        irc.queueMsg(ircmsgs.privmsg(means, s))

    def crossword(self, irc, msg, args):
        """<word>

        Gives the possible crossword completions for <word>; use underscores
        ('_') to denote blank spaces.
        """
        word = privmsgs.getArgs(args).lower()
        cursor = self.db.cursor()
        if '%' in word:
            irc.error(msg, '"%" isn\'t allowed in the word.')
            return
        cursor.execute("""SELECT word FROM words
                          WHERE word LIKE %s
                          ORDER BY word""", word)
        words = map(lambda t: t[0], cursor.fetchall())
        irc.reply(msg, ', '.join(words))

    def excuse(self, irc, msg, args):
        """takes no arguments

        Gives you a standard BOFH excuse.
        """
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, excuse FROM excuses
                          WHERE excuse NOTNULL
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error(msg, 'There are currently no available excuses.')
        else:
            (id, excuse) = cursor.fetchone()
            irc.reply(msg, '%s (#%s)' % (excuse, id))

    def dbadd(self, irc, msg, args):
        """<lart|excuse|insult|praise> <text>

        Adds another record to the data referred to in the first argument.  For
        commands that will later respond with an ACTION (lart and praise), $who
        should be in the message to show who should be larted or praised.  I.e.
        'dbadd lart slices $who in half with a free AOL cd' would make the bot,
        when it used that lart against, say, jemfinch, to say '/me slices
        jemfinch in half with a free AOL cd'
        """
        (table, s) = privmsgs.getArgs(args, needed=2)
        table = table.lower()
        try:
            name = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        if table == "lart" or table == "praise":
            if '$who' not in s:
                irc.error(msg, 'There must be a $who in the lart/praise '\
                               'somewhere.')
                return
        elif table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' % \
                           (table, utils.commaAndify(self._tables)))
            return
        cursor = self.db.cursor()
        sql = """INSERT INTO %ss VALUES (NULL, %%s, %%s)""" % table
        cursor.execute(sql, s, name)
        self.db.commit()
        sql = """SELECT id FROM %ss WHERE %s=%%s""" % (table, table)
        cursor.execute(sql, s)
        id = cursor.fetchone()[0]
        response = '%s (%s #%s)' % (conf.replySuccess, table, id)
        irc.reply(msg, response)

    def dbremove(self, irc, msg, args):
        """<lart|excuse|insult|praise> <id>

        Removes the data, referred to in the first argument, with the id
        number <id> from the database.
        """
        (table, id) = privmsgs.getArgs(args, needed=2)
        table = table.lower()
        try:
            ircdb.users.getUser(msg.prefix).name
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' % \
                           (table, utils.commaAndify(self._tables)))
            return
        cursor = self.db.cursor()
        sql = """DELETE FROM %ss WHERE id=%%s""" % table
        cursor.execute(sql, id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def dbchange(self, irc, msg, args):
        """<lart|excuse|insult|praise> <id> <regexp>

        Changes the data, referred to in the first argument, with the id
        number <id> according to the regular expression <regexp>. <id> is the
        zero-based index into the db; <regexp> is a regular expression of the
        form s/regexp/replacement/flags.
        """
        (table, id, regexp) = privmsgs.getArgs(args, needed=3)
        table = table.lower()
        try:
            name = ircdb.users.getUser(msg.prefix).name
        except KeyError:
            irc.error(msg, conf.replyNotRegistered)
            return
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' % \
                           (table, utils.commaAndify(self._tables)))
            return
        try:
            replacer = utils.perlReToReplacer(regexp)
        except ValueError, e:
            irc.error(msg, 'The regexp wasn\'t valid: %s.' % e.args[0])
        except re.error, e:
            irc.error(msg, debug.exnToString(e))
            return
        cursor = self.db.cursor()
        sql = """SELECT %s FROM %ss WHERE id=%%s""" % (table, table)
        cursor.execute(sql, id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such %s.' % table)
        else:
            old_entry = cursor.fetchone()[0]
            new_entry = replacer(old_entry)
            sql = """UPDATE %ss SET %s=%%s, added_by=%%s WHERE id=%%s""" % \
                  (table, table)
            cursor.execute(sql, new_entry, name, id)
            self.db.commit()
            irc.reply(msg, conf.replySuccess)

    def dbnum(self, irc, msg, args):
        """<lart|excuse|insult|praise>

        Returns the number of records, of the type specified, currently in
        the database.
        """
        table = privmsgs.getArgs(args)
        table = table.lower()
        if table not in self._tables:
            irc.error(msg, '%r is not valid. Valid values include %s.' % \
                           (table, utils.commaAndify(self._tables)))
            return
        cursor = self.db.cursor()
        sql = """SELECT count(*) FROM %ss""" % table
        cursor.execute(sql)
        total = int(cursor.fetchone()[0])
        irc.reply(msg, 'There %s currently %s in my database.' % \
                  (utils.be(total), utils.nItems(total, table)))

    def dbget(self, irc, msg, args):
        """<lart|excuse|insult|praise> <id>

        Gets the record with id <id> from the table specified.
        """
        (table, id) = privmsgs.getArgs(args, needed=2)
        table = table.lower()
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' % \
                           (table, utils.commaAndify(self._tables)))
            return
        cursor = self.db.cursor()
        sql = """SELECT %s FROM %ss WHERE id=%%s""" % (table, table)
        cursor.execute(sql, id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such %s.' % table)
        else:
            reply = cursor.fetchone()[0]
            irc.reply(msg, reply)

    def dbinfo(self, irc, msg, args):
        """<lart|excuse|insult|praise> <id>

        Gets the info for the record with id <id> from the table specified.
        """
        (table, id) = privmsgs.getArgs(args, needed=2)
        table = table.lower()
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The <id> argument must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s.' % \
                           (table, utils.commaAndify(self._tables)))
            return
        cursor = self.db.cursor()
        sql = """SELECT added_by FROM %ss WHERE id=%%s""" % table
        cursor.execute(sql, id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such %s.' % table)
        else:
            add = cursor.fetchone()[0]
            reply = '%s #%s: Created by %s.' % (table, id, add)
            irc.reply(msg, reply)

    def lart(self, irc, msg, args):
        """<text> [for <reason>]

        Uses a lart on <text> (giving the reason, if offered).
        """
        nick = privmsgs.getArgs(args)
        try:
            (nick, reason) = map(' '.join,
                             utils.itersplit('for'.__eq__, nick.split(), 1))
        except ValueError:
            nick = ' '.join(args)
            reason = ''
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, lart FROM larts
                          WHERE lart NOTNULL
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error(msg, 'There are currently no available larts.')
        else:
            (id, lart) = cursor.fetchone()
            if nick == irc.nick or nick == 'me':
                lartee = msg.nick
            else:
                lartee = nick
            lart = lart.replace("$who", lartee)
            if len(reason) > 0:
                s = '%s for %s (#%s)' % (lart, reason, id)
            else:
                s = '%s (#%s)' % (lart, id)
            irc.reply(msg, s, action=True)

    def praise(self, irc, msg, args):
        """<text> [for <reason>]

        Uses a praise on <text> (giving the reason, if offered).
        """
        nick = privmsgs.getArgs(args)
        try:
            (nick, reason) = map(' '.join,
                             utils.itersplit('for'.__eq__, nick.split(), 1))
        except ValueError:
            nick = ' '.join(args)
            reason = ''
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, praise FROM praises
                          WHERE praise NOTNULL
                          ORDER BY random()
                          LIMIT 1""")
        if cursor.rowcount == 0:
            irc.error(msg, 'There are currently no available praises.')
        else:
            (id, praise) = cursor.fetchone()
            if nick == msg.nick or nick == 'me':
                praisee = msg.nick
            else:
                praisee = nick
            praise = praise.replace("$who", praisee)
            if len(reason) > 0:
                s = '%s for %s (#%s)' % (praise, reason, id)
            else:
                s = '%s (#%s)' % (praise, id)
            irc.reply(msg, s, action=True)

    def addword(self, irc, msg, args):
        """<word>

        Adds a word to the database of words.  This database is used for the
        anagram and crossword commands.
        """
        word = privmsgs.getArgs(args)
        if word.translate(string.ascii, string.ascii_letters) != '':
            irc.error(msg, 'Word must contain only letters.')
        addWord(self.db, word, commit=True)
        irc.reply(msg, conf.replySuccess)

    def anagram(self, irc, msg, args):
        """<word>

        Using the words database, determines if a word has any anagrams.
        """
        word = privmsgs.getArgs(args).strip().lower()
        cursor = self.db.cursor()
        cursor.execute("""SELECT words.word FROM words
                          WHERE sorted_word_id=(
                                SELECT sorted_word_id FROM words
                                WHERE word=%s)""", word)
        words = map(lambda t: t[0], cursor.fetchall())
        try:
            words.remove(word)
        except ValueError:
            pass
        if words:
            irc.reply(msg, ', '.join(words))
        else:
            irc.reply(msg, 'That word has no anagrams that I know of.')

Class = FunDB


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print 'Usage: %s <words|larts|excuses|insults|zipcodes> file'\
              ' [<console>]' % sys.argv[0]
        sys.exit(-1)
    category = sys.argv[1]
    filename = sys.argv[2]
    if len(sys.argv) == 4:
        added_by = sys.argv[3]
    else:
        added_by = '<console>'
    db = makeDb(dbFilename)
    cursor = db.cursor()
    for line in open(filename, 'r'):
        line = line.rstrip()
        if not line:
            continue
        if category == 'words':
            cursor.execute("""PRAGMA cache_size = 50000""")
            addWord(db, line)
        elif category == 'larts':
            if '$who' in line:
                cursor.execute("""INSERT INTO larts VALUES (NULL, %s,
                                  %s)""", line, added_by)
            else:
                print 'Invalid lart: %s' % line
        elif category == 'praises':
            if '$who' in line:
                cursor.execute("""INSERT INTO praises VALUES (NULL, %s,
                                  %s)""", line, added_by)
            else:
                print 'Invalid praise: %s' % line
        elif category == 'insults':
            cursor.execute("""INSERT INTO insults VALUES (NULL, %s, %s
                              )""", line, added_by)
        elif category == 'excuses':
            cursor.execute("""INSERT INTO excuses VALUES (NULL, %s, %s
                              )""", line, added_by)
    db.commit()
    db.close()

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
