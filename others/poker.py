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
        cmp(self.rank, other.rank)

class Hand(object):
    def __init__(self, cards):
        self.cards = cards

    def cmpVal(self):
        self.cards.sort()
        self.cards.reverse() # High before low.
        first = 0
        if self.isFlush() and self.isStraight():
            first = 8
        elif self.isFourOfAKind():
            first = 7
        elif self.isFullHouse():
            first = 6
        elif self.isFlush():
            first = 5
        elif self.isStraight():
            first = 4
        elif self.isThreeOfAKind():
            first = 3
        elif self.isTwoPair():
            first = 2
        elif self.isPair():
            first = 1
        return (first, self.cards)

    # These assume self.cards is sorted.
    def isFlush(self):
        return all(lambda s: s == self.cards[0].suit, self.cards)

    def isStraight(self):
        diffs = [x-y for (x, y) in window(self.cards, 2)]
        return all(lambda x: x == 1, diffs)

    def _isSomeOfAKind(self, i):
        def eq(x, y):
            return x == y
        for cards in window(self.cards, i):
            if all(None, map(eq, window(cards, 2))):
                return True
        return False

    def isFourOfAKind(self):
        return _isSomeOfAKind(4)

    def isThreeOfAKind(self):
        return _isSomeOfAKind(3)

    def isPair(self):
        return _isSomeOfAKind(2)

    def isFullHouse(self):
        pass

    def __cmp__(self, other):
        cmp(self.cmpVal(), other.cmpVal())
        
deck = []
for suit in [S, H, C, D]:
    for rank in [A, K, Q, J] + range(2, 11):
        deck.append(Card(rank, suit))

