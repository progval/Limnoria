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
Turns the bot into a poker dealer.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch
__contributors__ = {}

import random
import itertools

from poker import deck

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Holdem', True)

class PokerError(ValueError):
    pass

Holdem = conf.registerPlugin('Holdem')
conf.registerChannelValue(Holdem, 'blind',
    registry.PositiveInteger(10, """Determines what the little blind is."""))
conf.registerChannelValue(Holdem, 'color',
    registry.Boolean(True, """Determines whether the bot will use color to
    distinguish between consecutive hands."""))

users = {}

class Player(object):
    def __init__(self, user, stack):
        self.user = user
        self.stack = stack

    def __hash__(self):
        return hash(self.user)

    def nick(self):
        return users[self.user]

class Table(object):
    def __init__(self, channel):
        self.irc = None
        self.button = 0
        self.players = []
        self.channel = channel
        self.waitingToJoin = []
        self.waitingToLeave = []
        self.colors = itertools.cycle(['red', 'blue', 'green', 'yellow'])

    def _color(self, s):
        if conf.get(conf.supybot.plugins.Holdem.color, self.channel):
            s = ircutils.mircColor(s, self.color)
        return s

    def public(self, s):
        s = self._color(s)
        self.irc.reply(s, to=self.channel)

    def private(self, player, s, noColor=False):
        if not noColor:
            s = self._color(s)
        self.irc.reply(s, to=users[player.user], private=True)

    def error(self, s):
        s = self._color(s)
        self.irc.reply(s, to=self.channel)

    def sit(self, player):
        if player in self.players:
            self.public('You\'re already seated.')
            return
        self.waitingToJoin.append(player)
        self.public('You will join the table when the next hand begins.',True)

    def stand(self, player):
        if player in self.players:
            self.waitingToLeave.append(player)
            self.public('You will leave this table when this hand ends.',True)
        elif player in self.waitingToJoin:
            self.waitingToJoin.remove(player)
        else:
            self.public('You aren\'t currently seated.')

    def deal(self, player):
        # Ignore player.
        if self.waitingToJoin:
            self.players.extend(self.waitingToJoin)
            self.waitingToJoin = []
        while self.waitingToLeave:
            playa = self.waitingToLeave.pop()
            self.players.remove(playa)

        if len(self.players) < 2:
            self.error('You can\'t deal a new game with fewer than 2 people.')
            return
        self.hands = {}
        self.buckets = {}
        for player in self.players:
            self.buckets[player] = 0
        self.foldedBuckets = []
        self.deck = deck[:]
        self.tableCards = []
        self.button += 1
        self.button %= len(self.players)
        random.shuffle(self.deck)
        for player in self.players:
            self.hands[player] = [self.deck.pop()]
        for player in self.players:
            self.hands[player].append(self.deck.pop())
            self.private(player, 'Your cards are %s.' % self.hands[player])
        self.public('The cards are dealt.')
        self.startBettingRound()

    def nextRound(self):
        self.currentBet = 0
        self.currentBets = {}
        for player in self.buckets: # Folded people aren't in buckets.
            self.currentBets[player] = 0
        self.deck.pop() # Burn a card.
        if len(self.tableCards) == 0:
            self.tableCards.append(deck.pop())
            self.tableCards.append(deck.pop())
            self.tableCards.append(deck.pop())
            self.startBettingRound()
        elif len(self.tableCards) == 5:
            self.finishGame()
        else:
            self.tableCards.append(deck.pop())
            self.startBettingRound(self.button+3 % len(self.players))
            
    def waitingOn(self):
        return self.players[self._waitingOn]

    def startBettingRound(self, start=None):
        if start is None:
            start = self.button+1 % len(self.players)
        self._waitingOn = start
        self.public('The table shows %s.  Betting begins with %s.' %
                    self.tableCards, self.waitingOn().nick())

    def checkWrongPlayer(player):
        if player != self.waitingOn():
            self.public('It\'s not your turn, %s.' % player.nick())
            return True
        return False

    def nextPlayer(self):
        self._waitingOn += 1
        self._waitingOn %= len(self.players)
        while self.waitingOn() not in self.buckets:
            self._waitingOn += 1
            self._waitingOn %= len(self.players)
        return self.waitingOn()

    def checkEndOfRound(self):
        # if all currentBets are not currentBet for all users with stacks.
        if len(self.buckets) == 1:
            # Only one guy left, let's distribute.
            self.finishGame()
            return
        for player in self.buckets:
            if self.currentBet > self.currentBets[player] and player.stack:
                break
        else:
            player = self.nextPlayer()
            self.public('%s, it\'s your turn.  The current bet is %s.  '
                        'You\'ve bet %s already this round.' %
                        player.nick(), self.currentBet,
                        self.currentBets[player])

    def checkNoCurrentBet(self):
        if self.currentBet:
            self.public('There\'s a bet of %s, you must call it, raise it, '
                        'or fold.' % self.currentBet)
            return True
        return False
    
    def fold(self, player):
        if self.checkWrongPlayer(player):
            return
        bucket = self.buckets.pop(player)
        if bucket:
            self.foldedBuckets.append(bucket)
        self.checkEndOfRound()

    def check(self, player):
        if self.checkWrongPlayer(player):
            return
        if self.checkNoCurrentBet():
            return
        selef.checkEndOfRound()

    def addCurrentBet(self, player, amount):
        self.buckets[player] += amount
        self.currentBets[player] += amount
        self.currentBet = max(self.currentBet, self.currentBets[player])
        player.stack -= amount
            
    def call(self, player):
        if self.checkWrongPlayer(player):
            return
        self.addCurrentBet(player, min(self.currentBet, player.stack))
        self.checkEndOfRound()

    def bet(self, player, amount):
        if self.checkWrongPlayer(player):
            return
        if self.checkNoCurrentBet():
            return
        if amount > player.stack:
            self.public('You only have %s in your stack, you can\'t bet that '
                        'much.  Perhaps you should use the allin command.' %
                        player.stack)
            return
        if amount < 2*self.blind:
            self.public('You must bet at least the big blind.')
            return
        self.addCurrentBet(player, amount)
        self.checkEndOfRound()
        
    def RAISE(self, player, amount):
        if self.checkWrongPlayer(player):
            return
        if not self.currentBet:
            self.public('You can\'t raise when there\'s no current bet.  '
                        'Perhaps you should use the bet command.')
            return
        if amount < 2*self.currentBet:
            self.public('You can\'t raise less than twice the current bet '
                        'of %s.' % self.currentBet)
            return
        totalRaise = amount + self.currentBet - self.currentBets[player]
        self.addCurrentBet(player, min(totalRaise, player.stack))
        self.checkEndOfRound()
        
    def allin(self, player):
        if self.checkWrongPlayer(player):
            return
        self.addCurrentBet(player, player.stack)
        self.checkEndOfRound()
        
        
def getPlayer(irc, msg, args, state):
    callConverter('user', irc, msg, args, state)
    Holdem = irc.getCallback('Holdem')
    try:
        state.args[-1] = Holdem.getPlayer(state.args[-1])
    except KeyError:
        irc.error('You\'re not currently seated, sit down first.', Raise=True)

addConverter('player', getPlayer)

class Holdem(callbacks.Privmsg):
    def __init__(self):
        self.players = {}
        self.tables = ircutils.IrcDict()
        self.__parent = super(Holdem, self)
        self.__parent.__init__()
        setattr(self.__class__, 'raise', self.__class__.RAISE)
        
    def __call__(self, irc, msg):
        try:
            # users is a global, used by Tables.
            users[ircdb.users.getUser(msg.prefix)] = msg.nick
        except KeyError:
            pass
        self.__parent.__call__(irc, msg)

    def callCommand(self, name, irc, msg, *args, **kwargs):
        if irc.isChannel(msg.args[0]):
            self.__parent.callCommand(name, irc, msg, *args, **kwargs)

    def getPlayer(self, user):
        if user not in self.players:
            self.players[user] = Player(user, 1000)
        return self.players[user]

    def forwarder(name):
        def f(self, irc, msg, args, channel, player):
            """takes no arguments

            Does %s in the current game in the channel in which it's given.
            """
            #print 'irc:', irc, 'msg:', msg, 'args:', args, 'channel:', channel, 'player:', player
            try:
                table = self.tables[channel]
                getattr(table, name)(player)
            except KeyError:
                return
        f.__doc__ %= name
        f = utils.changeFunctionName(f, name)
        f = wrap(f, ['onlyInChannel', 'player'])
        return f
    #forwarder = staticmethod(forwarder)

    def start(self, irc, msg, args, player):
        """takes no arguments

        Starts a table in the channel this message is sent in.
        """
        channel = msg.args[0]
        if channel in self.tables:
            irc.error('There\'s already a table in this channel.', Raise=True)
        else:
            self.tables[channel] = Table(channel)
            irc.replySuccess()
    start = wrap(start, ['player'])

    sit = forwarder('sit')
    call = forwarder('call')
    deal = forwarder('deal')
    fold = forwarder('fold')
    check = forwarder('check')
    allin = forwarder('allin')
    stand = forwarder('stand')

    def stack(self, irc, msg, args, player):
        """takes no arguments

        Returns the size of your stack.
        """
        irc.reply(player.stack)
    stack = wrap(stack, ['player'])

    def bet(self, irc, msg, args, channel, player, amount):
        """<amount>

        Bets <amount>.
        """
        if channel in self.tables:
            self.tables[channel].bet(player, amount)
    bet = wrap(bet, ['onlyInChannel', 'player', 'positiveInt'])

    def RAISE(self, irc, msg, args, channel, user, amount):
        """<amount>

        Calls the current bet and raises it by <amount>.
        """
        if channel in self.tables:
            self.tables[channel].RAISE(player, amount)
    RAISE = wrap(RAISE, ['onlyInChannel', 'user', 'positiveInt'])


Class = Holdem

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
