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

import supybot.fix

# Constants.
S = 's'
C = 'c'
H = 'h'
D = 'd'

class Rank(int):
    def __str__(self):
        if 2 <= self <= 10:
            return str(self)
        elif self == 11:
            return 'J'
        elif self == 12:
            return 'Q'
        elif self == 13:
            return 'K'
        elif self == 14:
            return 'A'
        elif self == 1:
            return 'A'

A = Rank(14)
K = Rank(13)
Q = Rank(12)
J = Rank(11)

class Card(object):
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return '%s%s' % (self.rank, self.suit)
    __repr__ = __str__

    def __cmp__(self, other):
        return cmp(self.rank, other.rank)

def combinations(L, n):
    if len(L) >= n:
        if n == 0:
            yield []
        else:
            (first, rest) = (L[:1], L[1:])
            for miniL in combinations(rest, n-1):
                yield first + miniL
            for miniL in combinations(rest, n):
                yield miniL
        
def sort(hand):
    hand.sort()
    hand.reverse()
    return hand

def getFlush(hand):
    if all(lambda c: c.suit == hand[0].suit, hand):
        return sort(hand)
    return []

def getStraight(hand):
    sort(hand)
    if all(lambda i: i==1, [x.rank-y.rank for (x,y) in window(hand,2)]):
        return hand
    elif hand[0].rank == A:
        (hand[0], hand[-1]) = (hand[-1], hand[0])
        if all(lambda i: i == 1, [x.rank-y.rank for (x,y) in window(hand,2)]):
            return hand
    sort(hand)
    return []

def getPair(hand):
    sort(hand)
    for (x, y) in window(hand, 2):
        if x.rank == y.rank:
            return ([x,y], [c for c in hand if c.rank != x.rank])
    return ([], hand)

def getTrips(hand):
    sort(hand)
    for (x, y, z) in window(hand, 3):
        if x.rank == y.rank == z.rank:
            return ([x,y,z], [c for c in hand if c.rank != x.rank])
    return ([], hand)

def getFours(hand):
    sort(hand)
    for (x, y, z, w) in window(hand, 4):
        if x.rank == y.rank == z.rank == w.rank:
            return ([x,y,z,w], [c for c in hand if c.rank != x.rank])
    return ([], hand)

def score(cards):
    """Returns a comparable value for a list of cards."""
    def getRank(hand):
        assert len(hand) == 5
        (pair, pairRest) = getPair(hand)
        if pair:
            # Can't be flushes or straights.
            (trips, tripRest) = getTrips(hand)
            if trips:
                (fours, fourRest) = getFours(hand)
                if fours:
                    return (7, fours + fourRest)
                (pair, _) = getPair(tripRest)
                if pair:
                    # Full house.
                    return (6, trips + pair)
                sort(tripRest)
                return (3, trips + tripRest)
            (otherPair, twoPairRest) = getPair(pairRest)
            if otherPair:
                if otherPair[0] > pair[0]:
                    return (2, otherPair + pair + twoPairRest)
                else:
                    return (2, pair + otherPair + twoPairRest)
            sort(pairRest)
            return (1, pair + pairRest)
        else:
            flush = getFlush(hand)
            if flush:
                straight = getStraight(hand)
                if straight:
                    return (8, straight)
                return (5, flush)
            straight = getStraight(hand)
            if straight:
                return (4, straight)
            hand.sort()
            return (0, hand)
    first = 0
    second = None
    for hand in combinations(cards, 5):
        (maybeFirst, maybeSecond) = getRank(hand)
        if maybeFirst > first:
            first = maybeFirst
            second = maybeSecond
        elif maybeFirst == first:
            second = max(second, maybeSecond)
    assert len(second) == 5, 'invalid second len'
    return (first, second)
    
deck = []
for suit in [S, H, C, D]:
    for rank in [A, K, Q, J] + range(10, 1, -1):
        deck.append(Card(rank, suit))


if __name__ == '__main__':
    import random
    random.shuffle(deck)
    for hand in window(deck, 7):
        print '%s: %s' % (hand, score(hand))
