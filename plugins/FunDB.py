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

from baseplugin import *

import sets
import string
import random
import os.path

import sqlite

import conf
import ircdb
import utils
import ircmsgs
import ircutils
import privmsgs
import callbacks

dbFilename = os.path.join(conf.dataDir, 'FunDB.db')

def makeDb(dbfilename, replace=False):
    if os.path.exists(dbfilename):
        if replace:
            os.remove(dbfilename)
        else:
            return sqlite.connect(dbfilename)
    db = sqlite.connect(dbfilename)
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE insults (
                      id INTEGER PRIMARY KEY,
                      insult TEXT, added_by TEXT,
                      requested_by TEXT,
                      use_count INTEGER
                      )""")
    cursor.execute("""CREATE TABLE excuses (
                      id INTEGER PRIMARY KEY,
                      excuse TEXT, added_by TEXT,
                      requested_by TEXT,
                      use_count INTEGER
                      )""")
    cursor.execute("""CREATE TABLE larts (
                      id INTEGER PRIMARY KEY,
                      lart TEXT, added_by TEXT,
                      requested_by TEXT,
                      use_count INTEGER
                      )""")
    cursor.execute("""CREATE TABLE praises (
                      id INTEGER PRIMARY KEY,
                      praise TEXT, added_by TEXT,
                      requested_by TEXT,
                      use_count INTEGER
                      )""")
    cursor.execute("""CREATE TABLE words (
                      id INTEGER PRIMARY KEY,
                      word TEXT UNIQUE ON CONFLICT IGNORE,
                      sorted_word_id INTEGER
                      )""")
    cursor.execute("""CREATE INDEX sorted_word_id ON words (sorted_word_id)""")
    cursor.execute("""CREATE TABLE sorted_words (
                      id INTEGER PRIMARY KEY,
                      word TEXT UNIQUE ON CONFLICT IGNORE
                      )""")
    cursor.execute("""CREATE INDEX sorted_words_word ON sorted_words (word)""")
    cursor.execute("""CREATE TABLE zipcodes (
                      zipcode INTEGER PRIMARY KEY,
                      city TEXT,
                      state CHAR(2)
                      )""")
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
    larting, excusing, and insulting.
    """
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self._tables = sets.Set(['lart', 'insult', 'excuse', 'praise'])
        self.db = makeDb(dbFilename)

    def die(self):
        self.db.commit()
        self.db.close()

    def _pluralize(self, string, count, verb=None):
        if verb is None:
            if count == 1:
                return string
            else:
                return '%ss' % string
        else:
            if count == 1:
                return ('is', string)
            else:
                return ('are', '%ss' % string)

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
        try:
            (id, insult) = cursor.fetchone()
        except TypeError:
            irc.error(msg, 'There are currently no available insults.')
            return
        sql = """UPDATE insults SET use_count=use_count+1, requested_by=%s
                 WHERE id=%s"""
        cursor.execute(sql, msg.prefix, id)
        if nick.strip() in (irc.nick, 'himself', 'me'):
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
        try:
            (id, excuse) = cursor.fetchone()
        except TypeError:
            irc.error(msg, 'There are currently no available excuses.')
            return
        sql = """UPDATE excuses SET use_count=use_count+1, requested_by=%s
                 WHERE id=%s"""
        cursor.execute(sql, msg.prefix, id)
        irc.reply(msg, '%s (#%s)' % (excuse, id))

    def dbadd(self, irc, msg, args):
        """<lart|excuse|insult|praise> <text>

        Adds another record to the data referred to in the first argument.
        """
        (table, s) = privmsgs.getArgs(args, needed=2)
        table = table.lower()
        try:
            name = ircdb.users.getUserName(msg.prefix)
        except KeyError:
            irc.error(msg, 'You must register first')
            return
        if table == "lart" or table == "praise":
            if '$who' not in s:
                irc.error(msg, 'There must be an $who in the lart/praise '\
                    'somewhere.')
                return
        elif table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s' % \
                           (table, utils.commaAndify(self._tables)))
            return
        cursor = self.db.cursor()
        sql = """INSERT INTO %ss VALUES (NULL, %%s, %%s, 'nobody',
                 0)""" % table
        cursor.execute(sql, s, msg.prefix)
        self.db.commit()
        sql = """SELECT id FROM %ss WHERE %s=%%s""" % (table, table)
        cursor.execute(sql, s)
        id = cursor.fetchone()[0]
        response = [conf.replySuccess,'(%s #%s)' % (table,id)]
        irc.reply(msg, ' '.join(response))

    def dbremove(self, irc, msg, args):
        """<lart|excuse|insult|praise> <id>

        Removes the data, referred to in the first argument, with the id
        number <id> from the database.
        """
        (table, id) = privmsgs.getArgs(args, needed=2)
        table = table.lower()
        try:
            ircdb.users.getUserName(msg.prefix)
        except KeyError:
            irc.error(msg, 'You must register first')
            return
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'You must give a numeric id.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s' % \
                           (table, utils.commaAndify(self._tables)))
            return
        cursor = self.db.cursor()
        sql = """DELETE FROM %ss WHERE id=%%s""" % table
        cursor.execute(sql, id)
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
            irc.error(msg, '"%s" is not valid. Valid values include %s' % \
                           (table, utils.commaAndify(self._tables)))
            return
        cursor = self.db.cursor()
        sql = """SELECT count(*) FROM %ss""" % table
        cursor.execute(sql)
        try:
            total = int(cursor.fetchone()[0])
        except ValueError:
            irc.error(msg, 'Unexpected response from database')
        (verb, table) = self._pluralize(table, total, 1)
        irc.reply(msg, 'There %s currently %s %s in my database' %\
            (verb, total, table))

    def dbget(self, irc, msg, args):
        """<lart|excuse|insult|praise> <id>

        Gets the record with id <id> from the table specified.
        """
        (table, id) = privmsgs.getArgs(args, needed=2)
        table = table.lower()
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, '<id> must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s' % \
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
            irc.error(msg, '<id> must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '"%s" is not valid. Valid values include %s' % \
                           (table, utils.commaAndify(self._tables)))
            return
        cursor = self.db.cursor()
        sql = """SELECT added_by, requested_by, use_count FROM %ss WHERE
                 id=%%s""" % table
        cursor.execute(sql, id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such %s.' % table)
        else:
            (add,req,count) = cursor.fetchone()
            reply = '%s #%s: Created by %s. last requested by %s, requested '\
                ' a total of %s %s' % (table, id, add, req, count,
                self._pluralize('time',count))
            irc.reply(msg, reply)

    def lart(self, irc, msg, args):
        """[<channel>] <nick>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  Uses a lart on <nick>.
        """
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args)
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, lart FROM larts
                          WHERE lart NOTNULL
                          ORDER BY random()
                          LIMIT 1""")
        try:
            (id, lart) = cursor.fetchone()
        except TypeError:
            irc.error(msg, 'There are currently no available larts.')
            return
        sql = """UPDATE larts SET use_count=use_count+1, requested_by=%s
                 WHERE id=%s"""
        cursor.execute(sql, msg.prefix, id)
        if nick == irc.nick or nick == 'me':
            lartee = msg.nick
        else:
            lartee = nick
        lart = lart.replace("$who", lartee)
        irc.queueMsg(ircmsgs.action(channel, '%s (#%s)' % (lart, id)))

    def praise(self, irc, msg, args):
        """[<channel>] <nick>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  Uses a praise on <nick>.
        """
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args)
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, praise FROM praises
                          WHERE praise NOTNULL
                          ORDER BY random()
                          LIMIT 1""")
        try:
            (id, praise) = cursor.fetchone()
        except TypeError:
            irc.error(msg, 'There are currently no available praises.')
            return
        sql = """UPDATE praises SET use_count=use_count+1, requested_by=%s
                 WHERE id=%s"""
        cursor.execute(sql, msg.prefix, id)
        self.db.commit()
        if nick == irc.nick or nick == 'me':
            praisee = msg.nick
        else:
            praisee = nick
        praise = praise.replace("$who", praisee)
        irc.queueMsg(ircmsgs.action(channel, '%s (#%s)' % (praise, id)))

    def addword(self, irc, msg, args):
        """<word>

        Adds a word to the database of words.  This database is used for the
        anagram and crossword commands.
        """
        word = privmsgs.getArgs(args)
        if word.translate(string.ascii, string.ascii_letters) != '':
            irc.error(msg, 'Word must contain only letters')
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

    def zipcode(self, irc, msg, args):
        """<zipcode>

        Returns the City, ST for a given zipcode.
        """
        try:
            zipcode = int(privmsgs.getArgs(args))
        except ValueError:
            # Must not be an integer.  Try zipcodefor.
            try:
                self.zipcodefor(irc, msg, args)
                return
            except:
                pass
            irc.error(msg, 'Invalid zipcode.')
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT city, state
                          FROM zipcodes
                          WHERE zipcode=%s""", zipcode)
        if cursor.rowcount == 0:
            irc.reply(msg, 'I have nothing for that zipcode.')
        else:
            (city, state) = cursor.fetchone()
            irc.reply(msg, '%s, %s' % (city, state))


    def zipcodefor(self, irc, msg, args):
        """<city> <state>

        Returns the zipcode for a <city> in <state>.
        """
        (city, state) = privmsgs.getArgs(args, needed=2)
        state = args.pop()
        city = ' '.join(args)
        if '%' in msg.args[1]:
            irc.error(msg, '% wildcard is not allowed.  Use _ instead.')
            return
        city = city.rstrip(',') # In case they did "City, ST"
        cursor = self.db.cursor()
        cursor.execute("""SELECT zipcode
                          FROM zipcodes
                          WHERE city LIKE %s AND
                                state LIKE %s""", city, state)
        if cursor.rowcount == 0:
            irc.reply(msg, 'I have no zipcode for %r, %r.' % \
                      (city, state))
        elif cursor.rowcount == 1:
            irc.reply(msg, str(cursor.fetchone()[0]))
        else:
            zipcodes = [str(t[0]) for t in cursor.fetchall()]
            ircutils.shrinkList(zipcodes, ', ', 400)
            if len(zipcodes) < cursor.rowcount:
                random.shuffle(zipcodes)
            irc.reply(msg, '(%s shown of %s): %s' % \
                      (len(zipcodes), cursor.rowcount, ', '.join(zipcodes)))

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
                                  %s, nobody, 0)""", line, added_by)
            else:
                print 'Invalid lart: %s' % line
        elif category == 'praises':
            if '$who' in line:
                cursor.execute("""INSERT INTO praises VALUES (NULL, %s,
                                  %s, nobody, 0)""", line, added_by)
            else:
                print 'Invalid praise: %s' % line
        elif category == 'insults':
            cursor.execute("""INSERT INTO insults VALUES (NULL, %s, %s,
                              nobody, 0)""", line, added_by)
        elif category == 'excuses':
            cursor.execute("""INSERT INTO excuses VALUES (NULL, %s, %s,
                              nobody, 0)""", line, added_by)
        elif category == 'zipcodes':
            (zipcode, cityState) = line.split(':')
            if '-' in zipcode:
                (begin, end) = map(int, zipcode.split('-'))
                zipcodes = range(begin, end+1)
                (zipcode, _) = zipcode.split('-')
            else:
                zipcodes = [int(zipcode)]
            cityStateList = cityState.split(', ')
            state = cityStateList.pop()
            city = ', '.join(cityStateList)
            for zipcode in zipcodes:
                cursor.execute("""INSERT INTO zipcodes VALUES (%s, %s, %s)""",
                               zipcode, city, state)
    db.commit()
    db.close()

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
