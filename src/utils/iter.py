###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

from __future__ import division

import sys
import new
import random

from itertools import *

def len(iterable):
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

if sys.version_info < (2, 4, 0):
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

def partition(p, iterable):
    """Partitions an iterable based on a predicate p.
    Returns a (yes,no) tuple"""
    no = []
    yes = []
    for elt in iterable:
        if p(elt):
            yes.append(elt)
        else:
            no.append(elt)
    return (yes, no)

def any(p, iterable):
    """Returns true if any element in iterable satisfies predicate p."""
    for elt in ifilter(p, iterable):
        return True
    else:
        return False

def all(p, iterable):
    """Returns true if all elements in iterable satisfy predicate p."""
    for elt in ifilterfalse(p, iterable):
        return False
    else:
        return True

def choice(iterable):
    if isinstance(iterable, (list, tuple)):
        return random.choice(iterable)
    else:
        n = 1
        m = new.module('') # Guaranteed unique value.
        ret = m
        for x in iterable:
            if random.random() < 1/n:
                ret = x
            n += 1
        if ret is m:
            raise IndexError
        return ret

def flatten(iterable, strings=False):
    """Flattens a list of lists into a single list.  See the test for examples.
    """
    for elt in iterable:
        if not strings and isinstance(elt, basestring):
            yield elt
        else:
            try:
                for x in flatten(elt):
                    yield x
            except TypeError:
                yield elt

def split(isSeparator, iterable, maxsplit=-1, yieldEmpty=False):
    """split(isSeparator, iterable, maxsplit=-1, yieldEmpty=False)

    Splits an iterator based on a predicate isSeparator."""
    if isinstance(isSeparator, basestring):
        f = lambda s: s == isSeparator
    else:
        f = isSeparator
    acc = []
    for element in iterable:
        if maxsplit == 0 or not f(element):
            acc.append(element)
        else:
            maxsplit -= 1
            if acc or yieldEmpty:
                yield acc
            acc = []
    if acc or yieldEmpty:
        yield acc

def ilen(iterable):
    i = 0
    for _ in iterable:
        i += 1
    return i

def startswith(long, short):
    longI = iter(long)
    shortI = iter(short)
    try:
        while True:
            if shortI.next() != longI.next():
                return False
    except StopIteration:
        return True

def limited(iterable, limit):
    i = limit
    iterable = iter(iterable)
    try:
        while i:
            yield iterable.next()
            i -= 1
    except StopIteration:
        raise ValueError, 'Expected %s elements in iterable (%r), got %s.' % \
              (limit, iterable, limit-i)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
