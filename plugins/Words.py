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
import copy
import string
import time
import random

import sqlite

import conf
import utils
import privmsgs
import callbacks
import configurable
import ircutils


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


class HangmanGame:
    def __init__(self):
        self.gameOn = False
        self.timeout = 0
        self.timeGuess = 0
        self.tries = 0
        self.prefix = ''
        self.guessed = False
        self.unused = ''
        self.hidden = ''
        self.guess = ''
        
    def getWord(self, dbHandler):
        db = dbHandler.getDb()
        cur = db.cursor()
        cur.execute("""SELECT word FROM words ORDER BY random() LIMIT 1""")
        word = cur.fetchone()[0]
        return word

    def letterPositions(self, letter, word):
        """
        Returns a list containing the positions of letter in word.
        """
        lst = []
        for i in xrange(len(word)):
            if word[i] == letter:
                lst.append(i)
        return lst

    def addLetter(self, letter, word, pos):
        """
        Replaces all characters of word at positions contained in pos
        by letter.
        """
        newWord = []
        for i in xrange(len(word)):
            if i in pos:
                newWord.append(letter)
            else:
                newWord.append(word[i])
        return ''.join(newWord)

    def triesLeft(self, n):
        """
        Returns the number of tries and the correctly pluralized try/tries
        """
        return utils.nItems('try', n)

    def letterArticle(self, letter):
        """
        Returns 'a' or 'an' to match the letter that will come after
        """
        anLetter = 'aefhilmnorsx'
        if letter in anLetter:
            return 'an'
        else:
            return 'a'


class Words(callbacks.Privmsg, configurable.Mixin):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        configurable.Mixin.__init__(self)
        self.dbHandler = WordsDB(os.path.join(conf.dataDir, 'Words'))
        try:
            dictfile = os.path.join(conf.dataDir, 'dict')
            self.wordList = file(dictfile).readlines() 
            self.gotDictFile = True
        except IOError:
            self.gotDictFile = False
        self.gameon = False 

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
        irc.replySuccess()

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
             
    ###
    # HANGMAN
    ###
    configurables = configurable.Dictionary(
        [('tries', configurable.IntType, 6, 'Number of tries to guess a word'),
         ('prefix', configurable.StrType, '-= HANGMAN =-',
             'Prefix string of the hangman plugin'),
         ('timeout', configurable.IntType, 300, 'Time before a game times out')]
    )
    dicturl = 'http://www.unixhideout.com/freebsd/share/dict/words'
    games = ircutils.IrcDict()
    validLetters = [chr(c) for c in range(ord('a'), ord('z')+1)]

    def endGame(self, channel):
        self.games[channel].gameOn = False

    def letters(self, irc, msg, args):
        """takes no arguments

        Returns unused letters
        """
        channel = msg.args[0]
        game = self.games[channel]
        irc.reply(msg, '%s %s' % (game.prefix, ' '.join(game.unused)))

    def hangman(self, irc, msg, args):
        """takes no arguments

        Creates a new game of hangman
        """
        channel = msg.args[0]
        # Fill our dictionary of games
        if channel not in self.games:
            self.games[channel] = HangmanGame()
        game = self.games[channel]
        # We only start a new game if no other game is going on right now
        if not game.gameOn:
            game.gameOn = True
            game.timeout = self.configurables.get('timeout', channel)
            game.timeGuess = time.time()
            game.tries = self.configurables.get('tries', channel)
            game.prefix = self.configurables.get('prefix', channel) + ' '
            game.guessed = False
            game.unused = copy.copy(self.validLetters)
            game.hidden = game.getWord(self.dbHandler)
            game.guess = '_' * len(game.hidden)
            irc.reply(msg, '%sOkay ladies and gentlemen, you have '
                      'a %s-letter word to find, you have %s!' %
                      (game.prefix, len(game.hidden),
                      game.triesLeft(game.tries)), prefixName=False)
        # So, a game is going on, but let's see if it's timed out.  If it is
        # we create a new one, otherwise we inform the user
        else:
            secondsEllapsed = time.time() - game.timeGuess
            if secondsEllapsed > game.timeout:
                self.endGame(channel)
                self.newhangman(irc, msg, args)
            else:
                irc.error(msg, 'Sorry, there is already a game going on.  '
                        '%s left before timeout.' % utils.nItems('seconds',
                            int(game.timeout - secondsEllapsed)))

    def guess(self, irc, msg, args):
        """<single letter>|<whole word>

        Try to guess a single letter or the whole word.  If you try to guess
        the whole word and you are wrong, you automatically lose.
        """
        channel = msg.args[0]
        game = self.games[channel]
        if not game.gameOn:
            irc.error(msg, 'There is no hangman game going on right now.')
            return
        letter = privmsgs.getArgs(args)
        game.timeGuess = time.time()
        # User input a valid letter that hasn't been already tried
        if letter in game.unused:
            del game.unused[game.unused.index(letter)]
            if letter in game.hidden:
                irc.reply(msg, '%sYes, there is %s %s' % (game.prefix,
                    game.letterArticle(letter), `letter`), prefixName=False)
                game.guess = game.addLetter(letter, game.guess,
                        game.letterPositions(letter, game.hidden))
                if game.guess == game.hidden:
                    game.guessed = True
            else:
                irc.reply(msg,'%sNo, there is no %s' % (game.prefix,`letter`),
                        prefixName=False)
                game.tries -= 1
            irc.reply(msg, '%s%s (%s left)' % (game.prefix, game.guess,
                game.triesLeft(game.tries)), prefixName=False)
        # User input a valid character that has already been tried
        elif letter in self.validLetters:
            irc.error(msg, 'That letter has already been tried.')
        # User tries to guess the whole word or entered an invalid input
        else:
            # The length of the word tried by the user and that of the hidden
            # word are same, so we assume the user wants to guess the whole
            # word
            if len(letter) == len(game.hidden):
                if letter == game.hidden:
                    game.guessed = True
                else:
                    irc.reply(msg, '%syou did not guess the correct word '
                        'and you lose a try' % game.prefix, prefixName=False)
                    game.tries -= 1
            else:
                # User input an invalid character
                if len(letter) == 1:
                    irc.error(msg, 'That is not a valid character.')
                # User input an invalid word (len(try) != len(hidden))
                else:
                    irc.error(msg, 'That is not a valid word guess.')
        # Verify if the user won or lost
        if game.guessed and game.tries > 0:
            irc.reply(msg, '%sYou win! The word was indeed %s' %
                    (game.prefix, game.hidden), prefixName=False)
            self.endGame(channel)
        elif not game.guessed and game.tries == 0:
            irc.reply(msg, '%sYou lose! The word was %s' %
                    (game.prefix, game.hidden), prefixName=False)
            self.endGame(channel)
    ###
    # END HANGMAN
    ###
                

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
