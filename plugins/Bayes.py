###
# Copyright (c) 2004, Jeremiah Fincher
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
Watches for paste-floods in a channel and takes appropriate measures against
violators.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch
__contributors__ = {}

import supybot.plugins as plugins

import glob
import os.path
import reverend.thomas
from cStringIO import StringIO as sio

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Bayes', True)

Bayes = conf.registerPlugin('Bayes')
conf.registerChannelValue(Bayes, 'maximumLines',
    registry.NonNegativeInteger(4, """Determines the maximum allowable number
    of consecutive messages that classify as a paste.  If this value is 0, no
    checking will be done."""))

def tokenize(s):
    return s.lower().split()

class PickleBayesDB(plugins.DbiChannelDB):
    class DB(object):
        def __init__(self, filename):
            self.filename = filename
            self.nickFilename = self.filename.replace('pickle', 'nick.pickle')
            self.bayes = reverend.thomas.Bayes(tokenize)
            if os.path.exists(self.filename) and \
               os.path.getsize(self.filename):
                self.bayes.load(self.filename)
            self.nickBayes = reverend.thomas.Bayes(tokenize)
            if os.path.exists(self.nickFilename) and \
               os.path.getsize(self.nickFilename):
                self.nickBayes.load(self.nickFilename)

        def close(self):
            self.bayes.save(self.filename)
            self.nickBayes.save(self.nickFilename)
        flush = close

        def train(self, kind, s):
            self.bayes.train(kind, s)

        def trainNick(self, nick, s):
            self.nickBayes.train(nick, s)

        def guess(self, s):
            matches = self.bayes.guess(s)
            if matches:
                if matches[0][1] > 0.5:
                    if len(matches) > 1 and \
                       matches[0][1] - matches[1][1] < 0.4:
                        return None
                    else:
                        return matches[0]
            else:
                self.bayes.train('normal', s)
                return None

        def guessNick(self, s):
            L = [t for t in self.nickBayes.guess(s) if t[1] > 0.01]
            if len(L) > 1:
                if L[0][1] / L[1][1] > 2:
                    return [L[0]]
            return L

BayesDB = plugins.DB('Bayes', {'pickle': PickleBayesDB})

class Bayes(callbacks.Privmsg):
    def __init__(self):
        self.__parent = super(Bayes, self)
        self.__parent.__init__()
        self.db = BayesDB()

    def die(self):
        self.db.close()

    def doPrivmsg(self, irc, msg):
        (channel, text) = msg.args
        if not ircutils.isChannel(channel) or msg.guessed:
            return
        kind = self.db.guess(channel, text)
        if kind is not None:
            (kind, prob) = kind
            prob *= 100
            text = utils.ellipsisify(text, 30)
            self.log.debug('Classified %r as %s. (%.2f%%)', text, kind, prob)
        self.db.trainNick(channel, msg.nick, text)

    def guess(self, irc, msg, args, channel, text):
        """[<channel>] <text>

        Guesses how <text> should be classified according to the Bayesian
        classifier for <channel>.  <channel> is only necessary if the message
        isn't sent in the channel itself, and then only if
        supybot.databases.plugins.channelSpecific is True.
        """
        msg.tag('guessed')
        kind = self.db.guess(channel, text)
        if kind is not None:
            (kind, prob) = kind
            prob *= 100
            irc.reply('That seems to me to be %s, '
                      'but I\'m only %.2f certain.' % (kind, prob))
        else:
            irc.reply('I don\'t know what the heck that is.')
    guess = wrap(guess, ['channeldb', 'something'])

    def who(self, irc, msg, args, channel, text):
        """[<channel>] <text>

        Guesses who might have said <text>.  <channel> is only necessary if the
        message isn't sent in the channel itself, and then only if
        supybot.databases.plugins.channelSpecific is True.
        """
        msg.tag('guessed')
        kinds = self.db.guessNick(channel, text)
        if kinds:
            if len(kinds) == 1:
                (kind, prob) = kinds.pop()
                irc.reply('It seems to me (with %.2f%% certainty) '
                          'that %s said that.' % (prob*100, kind))
            else:
                kinds = ['%s (%.2f%%)' % (k, prob*100) for (k, prob) in kinds]
                irc.reply('I\'m not quite sure who said that, but it could be '
                          + utils.commaAndify(kinds, And='or'))
        else:
            irc.reply('I have no idea who might\'ve said that.')
    who = wrap(who, ['channeldb', 'something'])

    def train(self, irc, msg, args, channel, language, pattern):
        """[<channel>] <language> <glob>


        Trains the bot to recognize text similar to that contained in the files
        matching <glob> as text of the language <language>.  <channel> is only
        necessary if the message isn't sent in the channel itself, and then
        only if supybot.databases.plugins.channelSpecific is True.
        """
        filenames = glob.glob(pattern)
        if not filenames:
            irc.errorInvalid('glob', pattern)
        for filename in filenames:
            fd = file(filename)
            for line in fd:
                self.db.train(channel, language, line)
            fd.close()
        irc.replySuccess()
    train = wrap(train, ['channeldb', 'something', 'something'])


Class = Bayes

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
