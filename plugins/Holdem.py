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

###
# TODO:
#
# Betting timeouts.
# Change the "bet" command to allow saying a specific amount to bet to.
# Change the stack command to see another person's stack.
# Keep a bankroll in the users registry.
# Allow the "sit" command to have specified a stack size, subtracting it from
#   the bankroll.
# Write a command to allow Owner users to give a person money.
# Re-expand the commands using forwarder so they can have better help.
# Have tables in each channel be entirely persistently configurable.
# Have the bot automatically start the next hand if people are seated.
# Have a slight pause before sending the "foo, it's your turn to bet" message,
#   and if the user replies before then, don't send it.
# ??? Should we allow "to" in a raise command? raise to 100?
###

import sets
import random
import operator
import itertools

import poker

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
    registry.PositiveInteger(10, """Determines what the small blind is.
    The big blind will be twice this."""))
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
        self.colors = itertools.cycle(['red', 'orange', 'yellow',
                                       'green', 'light blue', 'blue',
                                       'purple'])

    def _color(self, s):
        if conf.get(conf.supybot.plugins.Holdem.color, self.channel):
            s = ircutils.mircColor(s, self.color)
            s = ircutils.bold(s)
        return s

    def public(self, s, noColor=False):
        if not noColor:
            s = self._color(s)
        self.irc.reply(s, to=self.channel)

    def private(self, player, s, noColor=False):
        if not noColor:
            s = self._color(s)
        self.irc.reply(s, to=users[player.user], private=True)

    def error(self, s):
        s = self._color('%s: %s' % (self.irc.msg.nick, s))
        self.irc.reply(s, to=self.channel)

    def sit(self, player):
        if player in self.players:
            self.error('You\'re already seated.')
            return
        self.waitingToJoin.append(player)
        self.irc.reply('You will be dealt in when the next hand begins.')

    def stand(self, player):
        if player in self.players:
            self.waitingToLeave.append(player)
            self.irc.reply('You will leave this table when this hand ends.')
        elif player in self.waitingToJoin:
            self.waitingToJoin.remove(player)
            self.irc.reply('You are no longer waiting to join this table.')
        else:
            self.error('You aren\'t currently seated.')

    def deal(self, startingPlayer):
        # Ignore player.
        self.color = self.colors.next()
        self.blind = conf.get(conf.supybot.plugins.Holdem.blind, self.channel)
        if self.waitingToJoin:
            self.players.extend(self.waitingToJoin)
            self.waitingToJoin = []
        while self.waitingToLeave:
            playa = self.waitingToLeave.pop()
            self.players.remove(playa)

        for player in self.players[:]:
            if player.stack < 2*self.blind:
                self.public('%s doesn\'t have enough money to play this hand.'
                            % player.nick())
                self.players.remove(player)

        if len(self.players) < 2:
            self.public('I can\'t deal a new game with fewer than 2 people.')
            return

        self.hands = {}
        self.buckets = {}
        for player in self.players:
            self.buckets[player] = 0
        self.foldedBuckets = []
        self.tableCards = []
        self.button += 1
        self.button %= len(self.players)
        self._waitingOn = self.button
        self.deck = poker.deck[:]
        random.shuffle(self.deck)
        for player in self.players:
            self.hands[player] = [self.deck.pop()]
        for player in self.players:
            self.hands[player].append(self.deck.pop())
            self.hand(player)
        self.public('The cards are dealt.')
        self.startRound()
        # Blinds.
        smallBlind = self.nextPlayer()
        smallBlind.stack -= self.blind
        self.buckets[smallBlind] += self.blind
        self.currentBets[smallBlind] = self.blind
        self.public('%s places small blind of %s.' %
                    (smallBlind.nick(), self.blind))
        bigBlind = self.nextPlayer()
        bigBlind.stack -= 2*self.blind
        self.buckets[bigBlind] += 2*self.blind
        self.currentBets[bigBlind] = 2*self.blind
        self.public('%s places big blind of %s.' %
                    (bigBlind.nick(), 2*self.blind))
        self.currentBet = 2*self.blind
        self.startBettingRound()

    def startRound(self):
        self.couldBet = {}
        self.currentBet = 0
        self.currentBets = {}
        self._waitingOn = self.button
        for player in self.hands:
            self.currentBets[player] = 0

    def nextRound(self):
        self.startRound()
        self.deck.pop() # Burn a card.
        if len(self.tableCards) == 0:
            self.tableCards.append(self.deck.pop())
            self.tableCards.append(self.deck.pop())
            self.tableCards.append(self.deck.pop())
            self.public('Flop dealt, table shows %s.' % self.tableCards)
            self.startBettingRound()
        elif len(self.tableCards) == 3:
            self.tableCards.append(self.deck.pop())
            self.public('Turn dealt, table shows %s.' % self.tableCards)
            self.startBettingRound()
        elif len(self.tableCards) == 4:
            self.tableCards.append(self.deck.pop())
            self.public('River dealt, table shows %s.' % self.tableCards)
            self.startBettingRound()
        else:
            self.finishGame()

    def finishGame(self):
        try:
            if len(self.buckets) == 1:
                total = self.pot()
                player = self.buckets.keys()[0]
                player.stack += total
                self.public('%s wins the hand for %s.' % (player.nick(), total))
                return
            assert len(self.hands) == len(self.buckets)
            hands = [(player, poker.score(hand + self.tableCards))
                     for (player, hand) in self.hands.iteritems()]
            utils.sortBy(operator.itemgetter(1), hands)
            hands.reverse()
            buckets = self.buckets.values() + self.foldedBuckets
            for (player, (kind, hand)) in hands:
                amountBet = self.buckets[player]
                totalReceived = 0
                for (i, bucket) in enumerate(buckets):
                    received = min(bucket, amountBet)
                    totalReceived += received
                    buckets[i] -= received
                player.stack += totalReceived
                self.public('%s wins %s with a %s, %s' %
                            (player.nick(), totalReceived, kind[2:], hand))
                buckets = filter(None, buckets)
                if not buckets:
                    break
        finally:
            self.public('This hand is finished, prepare for the next hand.')
        
    def waitingOn(self):
        self._waitingOn %= len(self.players)
        return self.players[self._waitingOn]

    def pot(self):
        return sum(self.buckets.values()) + sum(self.foldedBuckets)

    def possibleBettors(self):
        L = []
        for player in self.hands:
            if player.stack > 0:
                L.append(player)
        return L

    def startBettingRound(self):
        player = self.nextPlayer()
        if player is None or len(self.possibleBettors()) <= 1:
            self.nextRound()
            return
        s = 'Betting begins with %s.' % self.waitingOn().nick()
        s = 'The pot is currently at %s.  %s' % (self.pot(), s)
        self.public(s)

    def checkWrongPlayer(self, player):
        if player != self.waitingOn():
            self.public('It\'s not your turn, %s.' % player.nick())
            return True
        return False

    def nextPlayer(self):
        seen = sets.Set()
        while 1:
            self._waitingOn += 1
            player = self.waitingOn()
            if player in seen:
                return None # Handled by checkEndOfRound.
            seen.add(player)
            if player not in self.buckets or player.stack <= 0:
                continue
            else:
                break
        return self.waitingOn()

    def checkEndOfRound(self):
        # if all currentBets are not currentBet for all users with stacks.
        if len(self.buckets) == 1:
            # Only one guy left, let's distribute.
            self.finishGame()
            return
        finished = True
        for player in self.buckets:
            if player not in self.couldBet:
                finished = False
                break
            if self.currentBet > self.currentBets[player] and player.stack:
                finished = False
                break
        if finished:
            self.nextRound()
        else:
            player = self.nextPlayer()
            if player is not None:
                s = '%s, it\'s your turn.  ' % player.nick()
                if self.currentBet:
                    s += 'The current bet is %s.  ' % self.currentBet
                    playerBet = self.currentBets[player]
                    if playerBet:
                        s += 'You\'ve already bet %s this round.' % playerBet
                    else:
                        s += 'You haven\'t yet bet this round.'
                else:
                    s += 'There have not yet been any bets this round.'
                self.public(s)
            else:
                self.nextRound()

    def checkNoCurrentBet(self):
        if self.currentBet:
            self.error('There\'s a bet of %s, you must call it, '
                       'raise it, or fold.' % self.currentBet)
            return True
        return False
    
    def hand(self, player):
        try:
            self.private(player, 'Your hand is %s.' % self.hands[player])
        except KeyError:
            self.error('You\'re not dealt in right now.')

    def table(self, player):
        self.public('The table shows %s.' % self.tableCards)

    def fold(self, player):
        if self.checkWrongPlayer(player):
            return
        bucket = self.buckets.pop(player)
        if bucket:
            self.foldedBuckets.append(bucket)
        del self.hands[player]
        self.public('%s folds.' % player.nick())
        self.checkEndOfRound()

    def check(self, player):
        if self.checkWrongPlayer(player):
            return
        if self.currentBet and self.currentBets[player] < self.currentBet:
            self.error('There is a bet of %s, you must call it, raise it, '
                       'or fold.' % self.currentBet)
        self.public('%s checks.' % player.nick())
        self.couldBet[player] = True
        self.checkEndOfRound()

    def addCurrentBet(self, player, amount):
        self.couldBet[player] = True
        self.buckets[player] += amount
        self.currentBets[player] += amount
        self.currentBet = max(self.currentBet, self.currentBets[player])
        player.stack -= amount
        return amount
            
    def call(self, player):
        if self.checkWrongPlayer(player):
            return
        if not self.currentBet:
            self.error('There isn\'t any bet to call.  '
                       'Perhaps you should check.')
            return
        toCall = self.currentBet - self.currentBets[player]
        bet = self.addCurrentBet(player, min(toCall, player.stack))
        self.public('%s calls %s.' % (player.nick(), bet))
        self.checkEndOfRound()

    def bet(self, player, amount):
        if self.checkWrongPlayer(player):
            return
        if self.currentBet and amount < self.currentBet:
            self.error('The current bet is %s, you must bet at least that.' %
                       self.currentBet)
            return
        if amount > player.stack:
            self.error('You only have %s in your stack, you can\'t '
                       'bet that much.  Perhaps you should use the allin '
                       'command.' % player.stack)
            return
        if amount < 2*self.blind:
            self.error('You must bet at least the big blind.')
            return
        bet = self.addCurrentBet(player, amount)
        self.public('%s bets %s.' % (player.nick(), bet))
        self.checkEndOfRound()
        
    def RAISE(self, player, amount):
        if self.checkWrongPlayer(player):
            return
        if not self.currentBet:
            self.error('You can\'t raise when there\'s no current '
                       'bet.  Perhaps you should use the bet command.')
            return
        if amount < self.currentBet:
            self.error('You can\'t raise by less than the current '
                       'bet of %s.' % self.currentBet)
            return
        totalRaise = amount + self.currentBet - self.currentBets[player]
        bet = self.addCurrentBet(player, min(totalRaise, player.stack))
        self.public('%s raises to %s.' % (player.nick(), bet))
        self.checkEndOfRound()
        
    def allin(self, player):
        if self.checkWrongPlayer(player):
            return
        bet = self.addCurrentBet(player, player.stack)
        self.public('%s goes all-in, %s.' % (player.nick(), bet))
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

    def getTable(self, irc, channel):
        table = self.tables[channel]
        table.irc = irc
        return table

    def forwarder(name):
        def f(self, irc, msg, args, channel, player):
            """takes no arguments

            Does %s in the current game in the channel in which it's given.
            """
            try:
                table = self.getTable(irc, channel)
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
    hand = forwarder('hand')
    table = forwarder('table')
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
            self.getTable(irc, channel).bet(player, amount)
    bet = wrap(bet, ['onlyInChannel', 'player', 'positiveInt'])

    def RAISE(self, irc, msg, args, channel, player, amount):
        """<amount>

        Calls the current bet and raises it by <amount>.
        """
        if channel in self.tables:
            self.getTable(irc, channel).RAISE(player, amount)
    RAISE = wrap(RAISE, ['onlyInChannel', 'player', 'positiveInt'])


Class = Holdem

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
