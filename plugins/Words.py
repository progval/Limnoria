#!/usr/bin/python

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
This handles interesting things to do with a dictionary (words) database.
"""

import supybot
import plugins

import os
import string

import sqlite

import conf
import utils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Words')


class WordsDB(plugins.DBHandler):
    def makeDb(self, filename):
        if os.path.exists(filename):
            db = sqlite.connect(filename)
        else:
            db = sqlite.connect(filename, converters={'bool': bool})
            cursor = db.cursor()
            cursor.execute("""CREATE TABLE words (
                              id INTEGER PRIMARY KEY,
                              word TEXT UNIQUE ON CONFLICT IGNORE,
                              sorted_word_id INTEGER)""")
            cursor.execute("""CREATE TABLE sorted_words (
                              id INTEGER PRIMARY KEY,
                              word TEXT UNIQUE ON CONFLICT IGNORE)""")
            cursor.execute("""CREATE INDEX sorted_word_id
                              ON words (sorted_word_id)""")
            cursor.execute("""CREATE INDEX sorted_words_word
                              ON sorted_words (word)""")
            db.commit()
        return db

def addWord(db, word, commit=False):
    word = word.strip().lower()
    if word.translate(string.ascii, string.ascii_letters):
        raise ValueError, 'Invalid word: %r' % word
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


class Words(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.dbHandler = WordsDB(os.path.join(conf.dataDir, 'Words'))

    def add(self, irc, msg, args):
        """<word> [<word>]

        Adds a word or words to the database of words.  This database is used
        for the other commands in this plugin.
        """
        if not args:
            raise callbacks.ArgumentError
        for word in args:
            if word.translate(string.ascii, string.ascii_letters):
                irc.error(msg, 'Word must contain only letters.')
                return
            else:
                addWord(self.dbHandler.getDb(), word, commit=True)
        irc.reply(msg, conf.replySuccess)

    def crossword(self, irc, msg, args):
        """<word>

        Gives the possible crossword completions for <word>; use underscores
        ('_') to denote blank spaces.
        """
        word = privmsgs.getArgs(args).lower()
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        if '%' in word:
            irc.error(msg, '"%" isn\'t allowed in the word.')
            return
        cursor.execute("""SELECT word FROM words
                          WHERE word LIKE %s
                          ORDER BY word""", word)
        words = [t[0] for t in cursor.fetchall()]
        if words:
            irc.reply(msg, utils.commaAndify(words))
        else:
            irc.reply(msg, 'No matching words were found.')

    def anagram(self, irc, msg, args):
        """<word>

        Using the words database, determines if a word has any anagrams.
        """
        word = privmsgs.getArgs(args).strip().lower()
        db = self.dbHandler.getDb()
        cursor = db.cursor()
        L = list(word.lower())
        L.sort()
        sorted = ''.join(L)
        cursor.execute("""SELECT id FROM sorted_words WHERE word=%s""", sorted)
        if cursor.rowcount == 0:
            irc.reply(msg, 'That word has no anagrams I could find.')
        else:
            id = cursor.fetchone()[0]
            cursor.execute("""SELECT words.word FROM words
                              WHERE sorted_word_id=%s""", id)
            if cursor.rowcount > 1:
                words = [t[0] for t in cursor.fetchall()]
                irc.reply(msg, utils.commaAndify(words))
            else:
                irc.reply(msg, 'That word has no anagrams I could find.')
                

Class = Words


if __name__ == '__main__':
    import sys, log
    if len(sys.argv) < 2:
        fd = sys.stdin
    else:
        try:
            fd = file(sys.argv[1])
        except EnvironmentError, e:
            sys.stderr.write(str(e) + '\n')
            sys.exit(-1)
    db = WordsDB(os.path.join(conf.dataDir, 'Words')).getDb()
    cursor = db.cursor()
    cursor.execute("""PRAGMA cache_size=20000""")
    lineno = 0
    for line in fd:
        lineno += 1
        line = line.rstrip()
        try:
            addWord(db, line)
        except KeyboardInterrupt:
            sys.exit(-1)
        except Exception, e:
            sys.stderr.write('Error on line %s: %s\n' % (lineno, e))
    db.commit()
        

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
