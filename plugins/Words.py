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

__revision__ = "$Id$"

import supybot
import supybot.plugins as plugins

import os
import re
import copy
import time
import random
import string

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

conf.registerPlugin('Words')
conf.registerGlobalValue(conf.supybot.plugins.Words, 'file',
    conf.DataFilename('words', """Determines what file in your data directory
    will be used by this plugin as its list of words."""))
conf.registerGroup(conf.supybot.plugins.Words, 'hangman')
conf.registerChannelValue(conf.supybot.plugins.Words.hangman, 'maxTries',
    registry.Integer(6, """Determines how many oppurtunities users will have to
    guess letters in the hangman game."""))
conf.registerChannelValue(conf.supybot.plugins.Words.hangman, 'prefix',
    registry.StringWithSpaceOnRight('-= HANGMAN =- ', """Determines what prefix
    string is placed in front of hangman-related messages sent to the
    channel."""))
conf.registerChannelValue(conf.supybot.plugins.Words.hangman, 'timeout',
    registry.Integer(300, """Determines how long a game must be idle before it
    will be replaced with a new game."""))


def wordsFile():
    return file(conf.supybot.plugins.Words.file())

class HangmanGame:
    def __init__(self):
        self.tries = 0
        self.guess = ''
        self.prefix = ''
        self.unused = ''
        self.hidden = ''
        self.timeout = 0
        self.timeGuess = 0
        self.guessed = False

    def getWord(self):
        fd = wordsFile()
        try:
            return random.choice(fd).strip().lower()
        finally:
            fd.close()

    def letterPositions(self, letter, word):
        """Returns a list containing the positions of letter in word."""
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

    def triesLeft(self, n=None):
        """
        Returns the number of tries and the correctly pluralized try/tries
        """
        if n is None:
            n = self.tries
        return utils.nItems('try', n)

    def letterArticle(self, letter):
        """Returns 'a' or 'an' to match the letter that will come after."""
        anLetters = 'aefhilmnorsx'
        if letter in anLetters:
            return 'an'
        else:
            return 'a'


class Words(callbacks.Privmsg):
    def crossword(self, irc, msg, args):
        """<word>

        Gives the possible crossword completions for <word>; use underscores
        ('_') to denote blank spaces.
        """
        # XXX: Should we somehow disable this during a hangman game?
        word = privmsgs.getArgs(args).lower()
        word = re.escape(word)
        word = word.replace('\\_', '_') # Stupid re.escape escapes underscores!
        word = word.replace('_', '.')
        word = '^%s$' % word
        wordRe = re.compile(word, re.I)
        words = []
        fd = wordsFile()
        try:
            for line in fd:
                line = line.strip()
                if wordRe.match(line):
                    words.append(line)
                    if len(words) > 100:
                        irc.reply('More than 100 words matched.')
                        return
        finally:
            fd.close()
        if words:
            words.sort()
            irc.reply(utils.commaAndify(words))
        else:
            irc.reply('No matching words were found.')

    ###
    # HANGMAN
    ###
    games = ircutils.IrcDict()
    validLetters = list(string.ascii_lowercase)

    def endGame(self, channel):
        del self.games[channel]

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
                self._hangmanReply(irc, channel, ' '.join(game.unused))
                return
        irc.error('There is currently no hangman game in %s.' % channel)

    def _hangmanReply(self, irc, channel, s):
        s = self.registryValue('hangman.prefix', channel=channel) + s
        irc.reply(s, prefixName=False)

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
            game.timeout = self.registryValue('hangman.timeout', channel)
            game.timeGuess = time.time()
            game.tries = self.registryValue('hangman.maxTries', channel)
            game.prefix = self.registryValue('hangman.prefix', channel)
            game.guessed = False
            game.unused = copy.copy(self.validLetters)
            game.hidden = game.getWord()
            game.guess = '_' * len(game.hidden)
            self._hangmanReply(irc, channel,
                               'Okay ladies and gentlemen, you have '
                               'a %s-letter word to find, you have %s!' %
                               (len(game.hidden), game.triesLeft()))
        # So, a game is going on, but let's see if it's timed out.  If it is
        # we create a new one, otherwise we inform the user
        else:
            game = self.games[channel]
            secondsElapsed = time.time() - game.timeGuess
            if secondsElapsed > game.timeout:
                self.endGame(channel)
                self.hangman(irc, msg, args)
            else:
                irc.reply('Sorry, there is already a game going on.  '
                          '%s left before the game times out.' % \
                          utils.timeElapsed(game.timeout - secondsElapsed))

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
                self._hangmanReply(irc, channel,
                                   'Yes, there is %s %r.' %
                                   (game.letterArticle(letter), letter))
                game.guess = game.addLetter(letter, game.guess,
                                            game.letterPositions(letter,
                                                                 game.hidden))
                if game.guess == game.hidden:
                    game.guessed = True
            else:
                self._hangmanReply(irc, channel, 'No, there is no %r.' % letter)
                game.tries -= 1
            self._hangmanReply(irc, channel,
                               '%s (%s left)' % (game.guess, game.triesLeft()))
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
                    self._hangmanReply(irc, channel,
                                       'You did not guess the word, so you '
                                       'lose a try.')
                    game.tries -= 1
            else:
                # User input an invalid character
                if len(letter) == 1:
                    irc.error('That is not a valid letter.')
                # User input an invalid word (len(try) != len(hidden))
                else:
                    irc.error('That is not a valid word guess.')
        # Verify if the user won or lost
        if game.guessed and game.tries > 0:
            self._hangmanReply(irc, channel,
                               'You win!  The was indeed %r.' % game.hidden)
            self.endGame(channel)
        elif not game.guessed and game.tries == 0:
            self._hangmanReply(irc, channel,
                               'You lose!  The was %r.' % game.hidden)
            self.endGame(channel)
    ###
    # END HANGMAN
    ###


Class = Words

### TODO: Write a script to make the database.


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
