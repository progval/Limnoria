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
Data structures for Python.
"""

from __future__ import generators

from fix import *

import types

__all__ = ['RingBuffer', 'queue', 'MaxLengthQueue']

class RingBuffer(object):
    __slots__ = ('L', 'i', 'full', 'maxSize')
    def __init__(self, maxSize, seq=()):
        if maxSize <= 0:
            raise ValueError, 'maxSize must be > 0.'
        self.maxSize = maxSize
        self.full = False
        self.L = []
        self.i = 0
        for elt in seq:
            self.append(elt)

    def __len__(self):
        return len(self.L)

    def __eq__(self, other):
        if self.__class__ == other.__class__ and \
           self.maxSize == other.maxSize and len(self) == len(other):
            iterator = iter(other)
            for elt in self:
                otherelt = iterator.next()
                if not elt == otherelt:
                    return False
            return True
        return False
    
    def __nonzero__(self):
        return len(self) > 0
    
    def __contains__(self, elt):
        return elt in self.L

    def append(self, elt):
        if self.full:
            self.L[self.i] = elt
            self.i += 1
            self.i %= len(self.L)
        else:
            if len(self) >= self.maxSize:
                self.full = True
                self.append(elt)
            else:
                self.L.append(elt)

    def extend(self, seq):
        for elt in seq:
            self.append(elt)
            
    def __getitem__(self, idx):
        if self.full:
            oidx = idx
            if type(oidx) == types.SliceType:
                L = []
                for i in xrange(*sliceIndices(oidx, len(self))):
                    L.append(self[i])
                return L
            else:
                (m, idx) = divmod(oidx, len(self.L))
                if m and m != -1:
                    raise IndexError, oidx
                idx = (idx + self.i) % len(self.L)
                return self.L[idx]
        else:
            if type(idx) == types.SliceType:
                L = []
                for i in xrange(*sliceIndices(idx, len(self))):
                    L.append(self[i])
                return L
            else:
                return self.L[idx]

    def __setitem__(self, idx, elt):
        if self.full:
            oidx = idx
            if type(oidx) == types.SliceType:
                range = xrange(*sliceIndices(oidx, len(self)))
                if len(range) != len(elt):
                    raise ValueError, 'seq must be the same length as slice.'
                else:
                    for (i, x) in zip(range, elt):
                        self[i] = x
            else:
                (m, idx) = divmod(oidx, len(self.L))
                if m and m != -1:
                    raise IndexError, oidx
                idx = (idx + self.i) % len(self.L)
                self.L[idx] = elt
        else:
            if type(idx) == types.SliceType:
                range = xrange(*sliceIndices(idx, len(self)))
                if len(range) != len(elt):
                    raise ValueError, 'seq must be the same length as slice.'
                else:
                    for (i, x) in zip(range, elt):
                        self[i] = x
            else:
                self.L[idx] = elt

    def __repr__(self):
        if self.full:
            return 'RingBuffer(%r, %r)' % (self.maxSize, list(self))
        else:
            return 'RingBuffer(%r, %r)' % (self.maxSize, list(self))

    def __getstate__(self):
        return (self.maxSize, self.full, self.i, self.L)

    def __setstate__(self, (maxSize, full, i, L)):
        self.maxSize = maxSize
        self.full = full
        self.i = i
        self.L = L


class queue(object):
    __slots__ = ('front', 'back')
    def __init__(self, seq=()):
        self.back = []
        self.front = []
        for elt in seq:
            self.enqueue(elt)

    def enqueue(self, elt):
        self.back.append(elt)

    def dequeue(self):
        try:
            return self.front.pop()
        except IndexError:
            self.back.reverse()
            self.front = self.back
            self.back = []
            return self.front.pop()

    def peek(self):
        if self.front:
            return self.front[-1]
        else:
            return self.back[0]

    def __len__(self):
        return len(self.front) + len(self.back)

    def __contains__(self, elt):
        return elt in self.front or elt in self.back

    def __iter__(self):
        for elt in reviter(self.front):
            yield elt
        for elt in self.back:
            yield elt

    def __eq__(self, other):
        if len(self) == len(other):
            otheriter = iter(other)
            for elt in self:
                otherelt = otheriter.next()
                if not (elt == otherelt):
                    return False
            return True
        else:
            return False

    def __repr__(self):
        return 'queue([%s])' % ', '.join(map(repr, self))

    def __getitem__(self, oidx):
        if type(oidx) == types.SliceType:
            L = []
            for i in xrange(*sliceIndices(oidx, len(self))):
                L.append(self[i])
            return L
        else:
            (m, idx) = divmod(oidx, len(self))
            if m and m != -1:
                raise IndexError, oidx
            if len(self.front) > idx:
                return self.front[-(idx+1)]
            else:
                return self.back[(idx-len(self.front))]
        
    def __setitem__(self, oidx, value):
        if type(oidx) == types.SliceType:
            range = xrange(*sliceIndices(oidx, len(self)))
            if len(range) != len(value):
                raise ValueError, 'seq must be the same length as slice.'
            else:
                for (i, x) in zip(range, value):
                    self[i] = x
        else:
            (m, idx) = divmod(oidx, len(self))
            if m and m != -1:
                raise IndexError, oidx
            if len(self.front) > idx:
                self.front[-(idx+1)] = value
            else:
                self.back[idx-len(self.front)] = value

    def __delitem__(self, oidx):
        if type(oidx) == types.SliceType:
            range = xrange(*sliceIndices(oidx, len(self)))
            for i in range:
                del self[i]
        else:
            (m, idx) = divmod(oidx, len(self))
            if m and m != -1:
                raise IndexError, oidx
            if len(self.front) > idx:
                del self.front[-(idx+1)]
            else:
                del self.back[idx-len(self.front)]

    def __getstate__(self):
        return (list(self),)

    def __setstate__(self, (L,)):
        L.reverse()
        self.front = L
        self.back = []

            
class MaxLengthQueue(queue):
    __slots__ = ('length',)
    def __init__(self, length, seq=()):
        self.length = length
        queue.__init__(self, seq)

    def __getstate__(self):
        return (self.length, queue.__getstate__(self))

    def __setstate__(self, (length, q)):
        self.length = length
        queue.__setstate__(self, q)
        
    def enqueue(self, elt):
        queue.enqueue(self, elt)
        if len(self) > self.length:
            self.dequeue()

## class MaxLengthQueue(RingBuffer):
##     enqueue = RingBuffer.append
##     def peek(self):
##         return self[0]


def sliceIndices(slice, length):
    if slice.step is None:
        step = 1
    else:
        if slice.step == 0:
            raise ValueError, 'slice step cannot be zero'
        step = slice.step
    if step < 0:
        defstart = length - 1
        defstop = -1
    else:
        defstart = 0
        defstop = length
    if slice.start is None:
        start = defstart
    else:
        start = slice.start
        if start < 0:
            start += length
        if start < 0:
            if step < 0:
                start = -1
            else:
                start = 0
        if start >= length:
            if step < 0:
                start = length - 1
            else:
                start = length
    if slice.stop is None:
        stop = defstop
    else:
        stop = slice.stop
        if stop < 0:
            stop += length
        if stop < 0:
            stop = -1
        if stop > length:
            stop = length
    if (step < 0 and stop >= start) or \
       (step > 0 and start >= stop):
        slicelength = 0
    elif step < 0:
        slicelength = (stop - start + 1)/step + 1
    else:
        slicelength = (stop - start - 1)/step + 1
    return (start, stop, step)
