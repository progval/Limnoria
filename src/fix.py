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

from __future__ import generators

import sys
import string

sys.path.insert(0, 'others')

string.ascii = string.maketrans('', '')

def ignore(*args, **kwargs):
    """Simply ignore the arguments sent to it."""
    pass

def catch(f, *args, **kwargs):
    """Catches all exceptions raises by f."""
    try:
        return f(*args, **kwargs)
    except:
        return None

class bool(int):
    """Just a holdover until 2.3 comes out with its wonderful new bool type."""
    def __new__(cls, val=0):
        # This constructor always returns an existing instance
        if val:
            return True
        else:
            return False

    def __repr__(self):
        if self:
            return "True"
        else:
            return "False"

    __str__ = __repr__

    def __and__(self, other):
        if isinstance(other, bool):
            return bool(int(self) & int(other))
        else:
            return int.__and__(self, other)

    __rand__ = __and__

    def __or__(self, other):
        if isinstance(other, bool):
            return bool(int(self) | int(other))
        else:
            return int.__or__(self, other)

    __ror__ = __or__

    def __xor__(self, other):
        if isinstance(other, bool):
            return bool(int(self) ^ int(other))
        else:
            return int.__xor__(self, other)

    __rxor__ = __xor__

False = int.__new__(bool, 0)
True = int.__new__(bool, 1)


class set(object):
    """Just a holdover until 2.3 comes out with its wonderful new set type."""
    __slots__ = ('d',)
    def __init__(self, seq=()):
        self.d = {}
        for x in seq:
            self.d[x] = None

    def __contains__(self, x):
        return x in self.d

    def __iter__(self):
        return self.d.iterkeys()

    def __repr__(self):
        return '%s([%s])' % (self.__class__.__name__,
                             ', '.join(map(repr, self.d.iterkeys())))

    def __nonzero__(self):
        if self.d:
            return True
        else:
            return False

    def __getstate__(self):
        return self.d.keys()

    def __setstate__(self, t):
        for x in t:
            self.d[x] = None

    def __len__(self):
        return len(self.d)

    def add(self, x):
        self.d[x] = None

    def remove(self, x):
        del self.d[x]

    def discard(self, x):
        try:
            del self.d[x]
        except KeyError:
            pass


class queue(dict):
    """An FIFO Queue, O(1) for all operations."""
    __slots__ = ('first', 'last')
    def __init__(self, seq=()):
        self.first = 0
        self.last = 0
        for elt in seq:
            self.enqueue(elt)

    def enqueue(self, elt):
        dict.__setitem__(self, self.last, elt)
        self.last += 1

    def peek(self):
        try:
            return dict.__getitem__(self, self.first)
        except KeyError:
            raise IndexError, 'peek into empty queue'

    def dequeue(self):
        try:
            ret = dict.__getitem__(self, self.first)
            dict.__delitem__(self, self.first)
            self.first += 1
            return ret
        except KeyError:
            raise IndexError, 'dequeue from empty queue'

    def __len__(self):
        return self.last - self.first

    def __contains__(self, elt):
        return elt in self.itervalues()

    def __iter__(self):
        for i in xrange(self.first, self.last):
            yield dict.__getitem__(self, i)
            
    def __eq__(self, other):
        if len(self) == len(other):
            for (x, y) in zip(self, other):
                if x != y:
                    return False
            return True
        else:
            return False

    def __repr__(self):
        return 'queue([%s])' % ', '.join(map(repr, self.itervalues()))

    def __getitem__(self, i):
        try:
            if i >= 0:
                return dict.__getitem__(self, i+self.first)
            else:
                return dict.__getitem__(self, i+self.last)
        except KeyError:
            raise IndexError, i

    def __setitem__(self, i, v):
        try:
            if i >= 0:
                dict.__setitem__(self, i+self.first, v)
            else:
                dict.__setitem__(self, i+self.last, v)
        except KeyError:
            raise IndexError, i

    def __getstate__(self):
        return (self.first, self.last, dict(self))

    def __setstate__(self, (first, last, d)):
        self.first = first
        self.last = last
        for (k, v) in d.iteritems():
            dict.__setitem__(self, k, v)
            
class MaxLengthQueue(queue):
    __slots__ = ('length',)
    def __init__(self, length, *args):
        self.length = length
        queue.__init__(self, *args)
        
    def enqueue(self, elt):
        if len(self) > self.length:
            self.dequeue()

class IterableMap(object):
    """Define .iteritems() in a class and subclass this to get the other iters.
    """
    def iteritems(self):
        raise NotImplementedError

    def iterkeys(self):
        for (key, _) in self.iteritems():
            yield key

    def itervalues(self):
        for (_, value) in self.iteritems():
            yield value

    def items(self):
        return list(self.iteritems())

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def __len__(self):
        ret = 0
        for _ in self.iteritems():
            ret += 1
        return ret

    def __nonzero__(self):
        for _ in self.iteritems():
            return True
        return False

def mktemp(suffix=''):
    """Gives a decent random string, suitable for a filename."""
    import sha
    import md5
    import time
    import random
    r = random.Random()
    m = md5.md5(suffix)
    r.seed(time.time())
    s = str(r.getstate())
    for x in xrange(0, random.randrange(400), random.randrange(1, 5)):
        m.update(str(x))
        m.update(s)
        m.update(str(time.time()))
        s = m.hexdigest()
    return sha.sha(s + str(time.time())).hexdigest() + suffix

def zipiter(*args):
    args = map(iter, args)
    while 1:
        L = []
        for arg in args:
            L.append(arg.next())
        yield tuple(L)

def reviter(L):
    for i in xrange(len(L) - 1, -1, -1):
        yield L[i]

def enumerate(L):
    for i in xrange(len(L)):
        yield (i, L[i])

def window(L, size):
    if size < 1:
        raise ValueError, 'size <= 0 unallowed.'
    for i in xrange(len(L) - (size-1)):
        yield L[i:i+size]

def itersplit(iterable, isSeparator, yieldEmpty=False):
    acc = []
    for element in iterable:
        if isSeparator(element):
            if acc or yieldEmpty:
                yield acc
            acc = []
        else:
            acc.append(element)
    if acc or yieldEmpty:
        yield acc

def flatten(seq, strings=False):
    for elt in seq:
        if not strings and type(elt) == str or type(elt) == unicode:
            yield elt
        else:
            try:
                for x in flatten(elt):
                    yield x
            except TypeError:
                yield elt
            
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
