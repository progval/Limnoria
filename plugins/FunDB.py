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

import string
import random
import os.path

import sqlite

import conf
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
                      insult TEXT
                      )""")
    cursor.execute("""CREATE TABLE excuses (
                      id INTEGER PRIMARY KEY,
                      excuse TEXT
                      )""")
    cursor.execute("""CREATE TABLE larts (
                      id INTEGER PRIMARY KEY,
                      lart TEXT
                      )""")
    cursor.execute("""CREATE TABLE praises (
                      id INTEGER PRIMARY KEY,
                      praise TEXT
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
        self.db = makeDb(dbFilename)

    def die(self):
        self.db.commit()
        self.db.close()

    '''
    def praise(self, irc, msg, args):
        """<something>

        Praises <something> with a praise from my vast database of praises.
        """
        something = privmsgs.getArgs(args)
        if something == 'me':
            something = msg.nick
        elif something == 'yourself':
            something = irc.nick
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, praise FROM praises
                          WHERE praise NOT NULL
                          ORDER BY random()
                          LIMIT 1""")
        (id, insult) = cursor.fetchone()
        s = insul
        irc.queueMsg(ircmsgs.action(ircutils.replyTo(msg),
    '''

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
        (id, insult) = cursor.fetchone()
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

    def getinsult(self, irc, msg, args):
        """<id>

        Returns insult #<id>
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The id must be an integer.')
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT insult FROM insults WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such insult.')
        else:
            irc.reply(msg, cursor.fetchone()[0])

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
        (id, excuse) = cursor.fetchone()
        irc.reply(msg, '%s (#%s)' % (excuse, id))

    def getexcuse(self, irc, msg, args):
        """<id>

        Gets the excuse with the id number <id>.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The id must be an integer.')
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT excuse FROM excuses WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such excuse.')
        else:
            irc.reply(msg, cursor.fetchone()[0])

    _tables = ['lart','excuse','insult','praise']
    def adddb(self, irc, msg, args):
        """<lart|excuse|insult|praise> <text>

        Adds another record to the data referred to in the first argument.
        """
        (table, s) = privmsgs.getArgs(args, needed=2)
        table = str.lower(table)
        if table == "lart" or table == "praise":
            if '$who' not in s:
                irc.error(msg, 'There must be an $who in the lart/praise '\
                    'somewhere.')
                return
        elif table not in self._tables:
            irc.error(msg, '\"%s\" is an invalid choice. Must be one of: '\
                'lart, excuse, insult, praise.' % table)
            return
        cursor = self.db.cursor()
        cursor.execute("""INSERT INTO %s VALUES (NULL, %s)""", table+'s', s)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def removedb(self, irc, msg, args):
        """<lart|excuse|insult|praise> <id>

        Removes the data, referred to in the first argument, with the id
        number <id> from the database.
        """
        (table, id) = privmsgs.getArgs(args, needed=2)
        table = str.lower(table)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'You must give a numeric id.')
            return
        if table not in self._tables:
            irc.error(msg, '\"%s\" is an invalid choice. Must be one of: '\
                'lart, excuse, insult, praise.' % table)
            return
        cursor = self.db.cursor()
        cursor.execute("""DELETE FROM %s WHERE id=%s""", table+'s', id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def numdb(self, irc, msg, args):
        """<lart|excuse|insult|praise>

        Returns the number of records, of the type specified, currently in
        the database.
        """
        table = privmsgs.getArgs(args)
        table = str.lower(table)
        if table not in self._tables:
            irc.error(msg, '\"%s\" is an invalid choice. Must be one of: '\
                'lart, excuse, insult, praise.' % table)
            return
        cursor = self.db.cursor()
        cursor.execute('SELECT count(*) FROM %s', table+'s')
        total = cursor.fetchone()[0]
        irc.reply(msg, 'There are currently %s %s in my database' %\
            (total,table+'s'))

    def getdb(self, irc, msg, args):
        """<lart|excuse|insult|praise> <id>

        Gets the record, of the type specified, with the id number <id>.
        """
        (table, id) = privmsgs.getArgs(args, needed=2)
        table = str.lower(table)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The id must be an integer.')
            return
        if table not in self._tables:
            irc.error(msg, '\"%s\" is an invalid choice. Must be one of: '\
                'lart, excuse, insult, praise.' % table)
            return
        cursor = self.db.cursor()
        print "%s %s" % (table, table+'s')
        cursor.execute("""SELECT %s FROM %s WHERE id=%s""", table, table+'s',
            id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such %s.' % table)
        else:
            irc.reply(msg, cursor.fetchone()[0])

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
        (id, lart) = cursor.fetchone()
        if nick == irc.nick or nick == 'me':
            lartee = msg.nick
        else:
            lartee = nick
        lart = lart.replace("$who", lartee)
        irc.queueMsg(ircmsgs.action(channel, '%s (#%s)' % (lart, id)))

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
        print 'Usage: %s <words|larts|excuses|insults|zipcodes> file' % \
              sys.argv[0]
        sys.exit(-1)
    category = sys.argv[1]
    filename = sys.argv[2]
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
                cursor.execute("""INSERT INTO larts VALUES (NULL, %s)""", line)
            else:
                print 'Invalid lart: %s' % line
        elif category == 'insults':
            cursor.execute("""INSERT INTO insults VALUES (NULL, %s)""", line)
        elif category == 'excuses':
            cursor.execute("""INSERT INTO excuses VALUES (NULL, %s)""", line)
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
