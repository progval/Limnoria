###
# Copyright (c) 2002-2009, Jeremiah Fincher
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

import time
import types
import UserDict
from itertools import imap

class RingBuffer(object):
    """Class to represent a fixed-size ring buffer."""
    __slots__ = ('L', 'i', 'full', 'maxSize')
    def __init__(self, maxSize, seq=()):
        if maxSize <= 0:
            raise ValueError, 'maxSize must be > 0.'
        self.maxSize = maxSize
        self.reset()
        for elt in seq:
            self.append(elt)

    def reset(self):
        self.full = False
        self.L = []
        self.i = 0

    def resize(self, i):
        if self.full:
            L = list(self)
            self.reset()
            self.L = L
        self.maxSize = i

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
        elif len(self) == self.maxSize:
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
                for i in xrange(*slice.indices(oidx, len(self))):
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
                for i in xrange(*slice.indices(idx, len(self))):
                    L.append(self[i])
                return L
            else:
                return self.L[idx]

    def __setitem__(self, idx, elt):
        if self.full:
            oidx = idx
            if type(oidx) == types.SliceType:
                range = xrange(*slice.indices(oidx, len(self)))
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
                range = xrange(*slice.indices(idx, len(self)))
                if len(range) != len(elt):
                    raise ValueError, 'seq must be the same length as slice.'
                else:
                    for (i, x) in zip(range, elt):
                        self[i] = x
            else:
                self.L[idx] = elt

    def __repr__(self):
        return 'RingBuffer(%r, %r)' % (self.maxSize, list(self))

    def __getstate__(self):
        return (self.maxSize, self.full, self.i, self.L)

    def __setstate__(self, (maxSize, full, i, L)):
        self.maxSize = maxSize
        self.full = full
        self.i = i
        self.L = L


class queue(object):
    """Queue class for handling large queues.  Queues smaller than 1,000 or so
    elements are probably better served by the smallqueue class.
    """
    __slots__ = ('front', 'back')
    def __init__(self, seq=()):
        self.back = []
        self.front = []
        for elt in seq:
            self.enqueue(elt)

    def reset(self):
        self.back[:] = []
        self.front[:] = []

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

    def __nonzero__(self):
        return bool(self.back or self.front)

    def __contains__(self, elt):
        return elt in self.front or elt in self.back

    def __iter__(self):
        for elt in reversed(self.front):
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
        return 'queue([%s])' % ', '.join(imap(repr, self))

    def __getitem__(self, oidx):
        if len(self) == 0:
            raise IndexError, 'queue index out of range'
        if type(oidx) == types.SliceType:
            L = []
            for i in xrange(*slice.indices(oidx, len(self))):
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
        if len(self) == 0:
            raise IndexError, 'queue index out of range'
        if type(oidx) == types.SliceType:
            range = xrange(*slice.indices(oidx, len(self)))
            if len(range) != len(value):
                raise ValueError, 'seq must be the same length as slice.'
            else:
                for i in range:
                    (m, idx) = divmod(oidx, len(self))
                    if m and m != -1:
                        raise IndexError, oidx
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
            range = xrange(*slice.indices(oidx, len(self)))
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

class smallqueue(list):
    __slots__ = ()
    def enqueue(self, elt):
        self.append(elt)

    def dequeue(self):
        return self.pop(0)

    def peek(self):
        return self[0]

    def __repr__(self):
        return 'smallqueue([%s])' % ', '.join(imap(repr, self))

    def reset(self):
        self[:] = []


class TimeoutQueue(object):
    def __init__(self, timeout, queue=None):
        if queue is None:
            queue = smallqueue()
        self.queue = queue
        self.timeout = timeout

    def reset(self):
        self.queue.reset()

    def __repr__(self):
        self._clearOldElements()
        return '%s(timeout=%r, queue=%r)' % (self.__class__.__name__,
                                             self.timeout, self.queue)

    def _getTimeout(self):
        if callable(self.timeout):
            return self.timeout()
        else:
            return self.timeout

    def _clearOldElements(self):
        now = time.time()
        while self.queue and now - self.queue.peek()[0] > self._getTimeout():
            self.queue.dequeue()

    def setTimeout(self, i):
        self.timeout = i

    def enqueue(self, elt, at=None):
        if at is None:
            at = time.time()
        self.queue.enqueue((at, elt))

    def dequeue(self):
        self._clearOldElements()
        return self.queue.dequeue()[1]

    def __iter__(self):
        # We could _clearOldElements here, but what happens if someone stores
        # the resulting generator and elements that should've timed out are
        # yielded?  Hmm?  What happens then, smarty-pants?
        for (t, elt) in self.queue:
            if time.time() - t < self._getTimeout():
                yield elt

    def __len__(self):
        # No dependency on utils.iter
        # return ilen(self)
        self._clearOldElements()
        return len(self.queue)

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


class TwoWayDictionary(dict):
    __slots__ = ()
    def __init__(self, seq=(), **kwargs):
        if hasattr(seq, 'iteritems'):
            seq = seq.iteritems()
        elif hasattr(seq, 'items'):
            seq = seq.items()
        for (key, value) in seq:
            self[key] = value
            self[value] = key
        for (key, value) in kwargs.iteritems():
            self[key] = value
            self[value] = key

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __delitem__(self, key):
        value = self[key]
        dict.__delitem__(self, key)
        dict.__delitem__(self, value)


class MultiSet(object):
    def __init__(self, seq=()):
        self.d = {}
        for elt in seq:
            self.add(elt)

    def add(self, elt):
        try:
            self.d[elt] += 1
        except KeyError:
            self.d[elt] = 1

    def remove(self, elt):
        self.d[elt] -= 1
        if not self.d[elt]:
            del self.d[elt]

    def __getitem__(self, elt):
        return self.d[elt]

    def __contains__(self, elt):
        return elt in self.d


class CacheDict(UserDict.DictMixin):
    def __init__(self, max, **kwargs):
        self.d = dict(**kwargs)
        self.max = max

    def __getitem__(self, key):
        return self.d[key]

    def __setitem__(self, key, value):
        if len(self.d) >= self.max:
            self.d.clear()
        self.d[key] = value

    def __delitem__(self, key):
        del self.d[key]

    def keys(self):
        return self.d.keys()
    
    def iteritems(self):
        return self.d.iteritems()

    def __iter__(self):
        return iter(self.d)


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
