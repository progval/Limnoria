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
Fixes stuff that Python should have but doesn't.
"""

from __future__ import division

__revision__ = "$Id$"

__all__ = []

exported = ['ignore', 'reversed', 'window', 'group', 'sorted',
           'partition', 'any', 'all', 'rsplit']

import new
import string
string.ascii = string.maketrans('', '')

import random
_choice = random.choice
def choice(iterable):
    if isinstance(iterable, list):
        return _choice(iterable)
    else:
        n = 1
        ret = None
        for x in iterable:
            if random.random() < 1/n:
                ret = x
            n += 1
        return ret
random.choice = choice

def ignore(*args, **kwargs):
    """Simply ignore the arguments sent to it."""
    pass

def reversed(L):
    """Iterates through a sequence in reverse."""
    for i in xrange(len(L) - 1, -1, -1):
        yield L[i]

def window(L, size):
    """Returns a sliding 'window' through the list L of size size."""
    if size < 1:
        raise ValueError, 'size <= 0 unallowed.'
    for i in xrange(len(L) - (size-1)):
        yield L[i:i+size]

import itertools
def ilen(iterable):
    """Returns the length of an iterator."""
    i = 0
    for _ in iterable:
        i += 1
    return i

def trueCycle(iterable):
    while 1:
        yielded = False
        for x in iterable:
            yield x
            yielded = True
        if not yielded:
            raise StopIteration

itertools.trueCycle = trueCycle
itertools.ilen = ilen

def groupby(key, iterable):
    if key is None:
        key = lambda x: x
    it = iter(iterable)
    value = it.next() # If there are no items, this takes an early exit
    oldkey = key(value)
    group = [value]
    for value in it:
        newkey = key(value)
        if newkey != oldkey:
            yield group
            group = []
            oldkey = newkey
        group.append(value)
    yield group
itertools.groupby = groupby

def group(seq, groupSize, noneFill=True):
    """Groups a given sequence into sublists of length groupSize."""
    ret = []
    L = []
    i = groupSize
    for elt in seq:
        if i > 0:
            L.append(elt)
        else:
            ret.append(L)
            i = groupSize
            L = []
            L.append(elt)
        i -= 1
    if L:
        if noneFill:
            while len(L) < groupSize:
                L.append(None)
        ret.append(L)
    return ret

def partition(p, L):
    """Partitions a list L based on a predicate p.  Returns a (yes,no) tuple"""
    no = []
    yes = []
    for elt in L:
        if p(elt):
            yes.append(elt)
        else:
            no.append(elt)
    return (yes, no)

def any(p, seq):
    """Returns true if any element in seq satisfies predicate p."""
    for elt in itertools.ifilter(p, seq):
        return True
    else:
        return False

def all(p, seq):
    """Returns true if all elements in seq satisfy predicate p."""
    for elt in itertools.ifilterfalse(p, seq):
        return False
    else:
        return True

def rsplit(s, sep=None, maxsplit=-1):
    """Equivalent to str.split, except splitting from the right."""
    if sep is not None:
        sep = sep[::-1]
    L = s[::-1].split(sep, maxsplit)
    L.reverse()
    return [s[::-1] for s in L]

def sorted(iterable, cmp=None, key=None, reverse=False):
    L = list(iterable)
##     if key is None:
##         L.sort(cmp)
##     else:
##         # Oops, we don't have sortBy.  Let's come back to this.utils.
##     utils.sortBy(key

import operator
def itemgetter(i):
    return lambda x: x[i]

def attrgetter(attr):
    return lambda x: getattr(x, attr)
operator.itemgetter = itemgetter
operator.attrgetter = attrgetter

for name in exported:
    __builtins__[name] = globals()[name]


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

