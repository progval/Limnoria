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
import ircutils
import registry


def configure(onStart):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    conf.registerPlugin('Words', True)


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
        for (i, c) in enumerate(word):
            if c == letter:
                lst.append(i)
        return lst

    def addLetter(self, letter, word, pos):
        """
        Replaces all characters of word at positions contained in pos
        by letter.
        """
        newWord = []
        for (i, c) in enumerate(word):
            if i in pos:
                newWord.append(letter)
            else:
                newWord.append(c)
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
        anLetters = 'aefhilmnorsx'
        if letter in anLetters:
            return 'an'
        else:
            return 'a'

conf.registerPlugin('Words')
conf.registerChannelValue(conf.supybot.plugins.Words, 'hangmanMaxTries',
    registry.Integer(6, """Determines how many oppurtunities users will have to
    guess letters in the hangman game."""))
conf.registerChannelValue(conf.supybot.plugins.Words, 'hangmanPrefix',
    registry.StringWithSpaceOnRight('-= HANGMAN -= ', """Determines what prefix
    string is placed in front of hangman-related messages sent to the
    channel."""))
conf.registerChannelValue(conf.supybot.plugins.Words, 'hangmanTimeout',
    registry.Integer(300, """Determines how long a game must be idle before it
    will be replaced with a new game."""))

class Words(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        dataDir = conf.supybot.directories.data()
        self.dbHandler = WordsDB(os.path.join(dataDir, 'Words'))

    def add(self, irc, msg, args):
        """<word> [<word>]

        Adds a word or words to the database of words.  This database is used
        for the other commands in this plugin.
        """
        if not args:
            raise callbacks.ArgumentError
        for word in args:
            if word.translate(string.ascii, string.ascii_letters):
                irc.error('Word must contain only letters.')
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
            irc.error('"%" isn\'t allowed in the word.')
            return
        cursor.execute("""SELECT word FROM words
                          WHERE word LIKE %s
                          ORDER BY word""", word)
        words = [t[0] for t in cursor.fetchall()]
        if words:
            irc.reply(utils.commaAndify(words))
        else:
            irc.reply('No matching words were found.')

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
            irc.reply('That word has no anagrams I could find.')
        else:
            id = cursor.fetchone()[0]
            cursor.execute("""SELECT words.word FROM words
                              WHERE sorted_word_id=%s""", id)
            if cursor.rowcount > 1:
                words = [t[0] for t in cursor.fetchall()]
                irc.reply(utils.commaAndify(words))
            else:
                irc.reply('That word has no anagrams I could find.')
             
    ###
    # HANGMAN
    ###
    games = ircutils.IrcDict()
    validLetters = list(string.ascii_lowercase)

    def endGame(self, channel):
        self.games[channel] = None

    def letters(self, irc, msg, args):
        """[<channel>]

        Returns the unused letters that can be guessed in the hangman game
        in <channel>.  <channel> is only necessary if the message isn't sent in
        the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        if channel in self.games:
            game = self.games[channel]
            if game is not None:
                irc.reply('%s%s' % (game.prefix, ' '.join(game.unused)))
                return
        irc.error('There is no hangman game going on right now.')

    def hangman(self, irc, msg, args):
        """[<channel>]

        Creates a new game of hangman in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        channel = privmsgs.getChannel(msg, args)
        # Fill our dictionary of games
        if channel not in self.games:
            self.games[channel] = None
        # We only start a new game if no other game is going on right now
        if self.games[channel] is None:
            self.games[channel] = HangmanGame()
            game = self.games[channel]
            game.timeout = self.registryValue('hangmanTimeout', channel)
            game.timeGuess = time.time()
            game.tries = self.registryValue('hangmanMaxTries', channel)
            game.prefix = self.registryValue('hangmanPrefix', channel)
            game.guessed = False
            game.unused = copy.copy(self.validLetters)
            game.hidden = game.getWord(self.dbHandler)
            game.guess = '_' * len(game.hidden)
            irc.reply('%sOkay ladies and gentlemen, you have '
                      'a %s-letter word to find, you have %s!' %
                      (game.prefix, len(game.hidden),
                      game.triesLeft(game.tries)), prefixName=False)
        # So, a game is going on, but let's see if it's timed out.  If it is
        # we create a new one, otherwise we inform the user
        else:
            game = self.games[channel]
            secondsEllapsed = time.time() - game.timeGuess
            if secondsEllapsed > game.timeout:
                self.endGame(channel)
                self.hangman(irc, msg, args)
            else:
                irc.error('Sorry, there is already a game going on.  '
                          '%s left before timeout.' % \
                          utils.nItems('second',
                                       int(game.timeout - secondsEllapsed)))

    def guess(self, irc, msg, args):
        """[<channel>] <letter|word>

        Try to guess a single letter or the whole word.  If you try to guess
        the whole word and you are wrong, you automatically lose.
        """
        channel = privmsgs.getChannel(msg, args)
        try:
            game = self.games[channel]
            if game is None:
                raise KeyError
        except KeyError:
            irc.error('There is no hangman game going on right now.')
            return
        letter = privmsgs.getArgs(args)
        game.timeGuess = time.time()
        # User input a valid letter that hasn't been already tried
        if letter in game.unused:
            del game.unused[game.unused.index(letter)]
            if letter in game.hidden:
                irc.reply('%sYes, there is %s %r' % (game.prefix,
                    game.letterArticle(letter), letter), prefixName=False)
                game.guess = game.addLetter(letter, game.guess,
                        game.letterPositions(letter, game.hidden))
                if game.guess == game.hidden:
                    game.guessed = True
            else:
                irc.reply('%sNo, there is no %s' % (game.prefix,`letter`),
                        prefixName=False)
                game.tries -= 1
            irc.reply('%s%s (%s left)' % (game.prefix, game.guess,
                game.triesLeft(game.tries)), prefixName=False)
        # User input a valid character that has already been tried
        elif letter in self.validLetters:
            irc.error('That letter has already been tried.')
        # User tries to guess the whole word or entered an invalid input
        else:
            # The length of the word tried by the user and that of the hidden
            # word are same, so we assume the user wants to guess the whole
            # word
            if len(letter) == len(game.hidden):
                if letter == game.hidden:
                    game.guessed = True
                else:
                    irc.reply('%syou did not guess the correct word '
                        'and you lose a try' % game.prefix, prefixName=False)
                    game.tries -= 1
            else:
                # User input an invalid character
                if len(letter) == 1:
                    irc.error('That is not a valid character.')
                # User input an invalid word (len(try) != len(hidden))
                else:
                    irc.error('That is not a valid word guess.')
        # Verify if the user won or lost
        if game.guessed and game.tries > 0:
            irc.reply('%sYou win! The word was indeed %s' %
                    (game.prefix, game.hidden), prefixName=False)
            self.endGame(channel)
        elif not game.guessed and game.tries == 0:
            irc.reply('%sYou lose! The word was %s' %
                    (game.prefix, game.hidden), prefixName=False)
            self.endGame(channel)
    ###
    # END HANGMAN
    ###
                

Class = Words

### TODO: Write a script to make the database.
        

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
