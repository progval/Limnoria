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

## from __future__ import generators

"""
Fixes stuff that Python should have but doesn't.
"""

import sys

if 'others' not in sys.path:
    sys.path.insert(0, 'others')

import string
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

def reviter(L):
    """Iterates through a list in reverse."""
    for i in xrange(len(L) - 1, -1, -1):
        yield L[i]

def window(L, size):
    """Returns a sliding 'window' through the list L of size size."""
    if size < 1:
        raise ValueError, 'size <= 0 unallowed.'
    for i in xrange(len(L) - (size-1)):
        yield L[i:i+size]

import itertools
def ilen(iterator):
    """Returns the length of an iterator."""
    i = 0
    for _ in iterator:
        i += 1
    return i
itertools.ilen = ilen
del ilen

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
    if p is None:
        p = bool
    for elt in seq:
        if p(elt):
            return True
    return False

def all(p, seq):
    """Returns true if all elements in seq satisfy predicate p."""
    if p is None:
        p = bool
    for elt in seq:
        if not p(elt):
            return False
    return True

def rsplit(s, sep=None, maxsplit=-1):
    L = s[::-1].split(sep, maxsplit)
    L.reverse()
    return [s[::-1] for s in L]


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
