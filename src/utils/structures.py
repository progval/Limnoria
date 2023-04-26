###
# Copyright (c) 2002-2009, Jeremiah Fincher
# Copyright (c) 2010-2022, Valentin Lorentz
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
import threading
import collections.abc


class RingBuffer(object):
    """Class to represent a fixed-size ring buffer."""
    __slots__ = ('L', 'i', 'full', 'maxSize')
    def __init__(self, maxSize, seq=()):
        if maxSize <= 0:
            raise ValueError('maxSize must be > 0.')
        self.maxSize = maxSize
        self.reset()
        for elt in seq:
            self.append(elt)

    def reset(self):
        self.full = False
        self.L = []
        self.i = 0

    def resize(self, size):
        L = list(self)
        i = self.i
        self.reset()
        self.maxSize = size
        for elt in L[i+1:]:
            self.append(elt)
        for elt in L[0:i]:
            self.append(elt)

    def __len__(self):
        return len(self.L)

    def __eq__(self, other):
        if self.__class__ == other.__class__ and \
           self.maxSize == other.maxSize and len(self) == len(other):
            iterator = iter(other)
            for elt in self:
                otherelt = next(iterator)
                if not elt == otherelt:
                    return False
            return True
        return False

    def __bool__(self):
        return len(self) > 0
    __nonzero__ = __bool__

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
            if isinstance(oidx, slice):
                L = []
                for i in range(*slice.indices(oidx, len(self))):
                    L.append(self[i])
                return L
            else:
                (m, idx) = divmod(oidx, len(self.L))
                if m and m != -1:
                    raise IndexError(oidx)
                idx = (idx + self.i) % len(self.L)
                return self.L[idx]
        else:
            if isinstance(idx, slice):
                L = []
                for i in range(*slice.indices(idx, len(self))):
                    L.append(self[i])
                return L
            else:
                return self.L[idx]

    def __setitem__(self, idx, elt):
        if self.full:
            oidx = idx
            if isinstance(oidx, slice):
                range_ = range(*slice.indices(oidx, len(self)))
                if len(range_) != len(elt):
                    raise ValueError('seq must be the same length as slice.')
                else:
                    for (i, x) in zip(range_, elt):
                        self[i] = x
            else:
                (m, idx) = divmod(oidx, len(self.L))
                if m and m != -1:
                    raise IndexError(oidx)
                idx = (idx + self.i) % len(self.L)
                self.L[idx] = elt
        else:
            if isinstance(idx, slice):
                range_ = range(*slice.indices(idx, len(self)))
                if len(range_) != len(elt):
                    raise ValueError('seq must be the same length as slice.')
                else:
                    for (i, x) in zip(range_, elt):
                        self[i] = x
            else:
                self.L[idx] = elt

    def __repr__(self):
        return 'RingBuffer(%r, %r)' % (self.maxSize, list(self))

    def __getstate__(self):
        return (self.maxSize, self.full, self.i, self.L)

    def __setstate__(self, state):
        (maxSize, full, i, L) = state
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

    def __bool__(self):
        return bool(self.back or self.front)
    __nonzero__ = __bool__

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
                otherelt = next(otheriter)
                if not (elt == otherelt):
                    return False
            return True
        else:
            return False

    def __repr__(self):
        return 'queue([%s])' % ', '.join(map(repr, self))

    def __getitem__(self, oidx):
        if len(self) == 0:
            raise IndexError('queue index out of range')
        if isinstance(oidx, slice):
            L = []
            for i in range(*slice.indices(oidx, len(self))):
                L.append(self[i])
            return L
        else:
            (m, idx) = divmod(oidx, len(self))
            if m and m != -1:
                raise IndexError(oidx)
            if len(self.front) > idx:
                return self.front[-(idx+1)]
            else:
                return self.back[(idx-len(self.front))]

    def __setitem__(self, oidx, value):
        if len(self) == 0:
            raise IndexError('queue index out of range')
        if isinstance(oidx, slice):
            range_ = range(*slice.indices(oidx, len(self)))
            if len(range_) != len(value):
                raise ValueError('seq must be the same length as slice.')
            else:
                for i in range_:
                    (m, idx) = divmod(oidx, len(self))
                    if m and m != -1:
                        raise IndexError(oidx)
                for (i, x) in zip(range_, value):
                    self[i] = x
        else:
            (m, idx) = divmod(oidx, len(self))
            if m and m != -1:
                raise IndexError(oidx)
            if len(self.front) > idx:
                self.front[-(idx+1)] = value
            else:
                self.back[idx-len(self.front)] = value

    def __delitem__(self, oidx):
        if isinstance(oidx, slice):
            range_ = range(*slice.indices(oidx, len(self)))
            for i in range_:
                del self[i]
        else:
            (m, idx) = divmod(oidx, len(self))
            if m and m != -1:
                raise IndexError(oidx)
            if len(self.front) > idx:
                del self.front[-(idx+1)]
            else:
                del self.back[idx-len(self.front)]

    def __getstate__(self):
        return (list(self),)

    def __setstate__(self, state):
        (L,) = state
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
        return 'smallqueue([%s])' % ', '.join(map(repr, self))

    def reset(self):
        self[:] = []


class TimeoutQueue(object):
    """A queue whose elements are dropped after a certain time."""

    __slots__ = ('queue', 'timeout')
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
        self._clearOldElements()

        # You may think re-checking _getTimeout() after we just called
        # _clearOldElements is redundant, but what happens if someone stores
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

    def __setstate__(self, state):
        (length, q) = state
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
        for (key, value) in kwargs.items():
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
    __slots__ = ('d',)
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


class CacheDict(collections.abc.MutableMapping):
    __slots__ = ('d', 'max')
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

    def items(self):
        return self.d.items()

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)


class ExpiringDict(collections.abc.MutableMapping):
    """An efficient dictionary that MAY drop its items when they are too old.
    For guaranteed expiry, use TimeoutDict.

    Currently, this is implemented by internally alternating two "generation"
    dicts, which are dropped after a certain time.
    """
    __slots__ = ('_lock', 'old_gen', 'new_gen', 'timeout', '_last_switch')

    def __init__(self, timeout, items=None):
        self._lock = threading.Lock()
        self.old_gen = {}
        self.new_gen = {} if items is None else items
        self.timeout = timeout
        self._last_switch = time.time()

    def __reduce__(self):
        return (self.__class__, (self.timeout, dict(self)))

    def __repr__(self):
        return 'ExpiringDict(%s, %r)' % (self.timeout, dict(self))

    def __getitem__(self, key):
        try:
            # Check the new_gen first, as it contains the most recent
            # insertion.
            # We must also check them in this order to be thread-safe when
            # _expireGenerations() runs.
            return self.new_gen[key]
        except KeyError:
            try:
                return self.old_gen[key]
            except KeyError:
                raise KeyError(key) from None

    def __contains__(self, key):
        # the two clauses must be in this order to be thread-safe when
        # _expireGenerations() runs.
        return key in self.new_gen or key in self.old_gen

    def __setitem__(self, key, value):
        self._expireGenerations()
        self.new_gen[key] = value

    def _expireGenerations(self):
        with self._lock:
            now = time.time()
            if self._last_switch + self.timeout < now:
                # We last wrote to self.old_gen a long time ago
                # (ie. more than self.timeout); let's drop the old_gen and
                # make new_gen become the old_gen
                # self.old_gen must be written before self.new_gen for
                # __getitem__ and __contains__ to be able to run concurrently
                # to this function.
                self.old_gen = self.new_gen
                self.new_gen = {}
                self._last_switch = now

    def clear(self):
        self.old_gen.clear()
        self.new_gen.clear()

    def __delitem__(self, key):
        self.old_gen.pop(key, None)
        self.new_gen.pop(key, None)

    def __iter__(self):
        # order matters
        keys = set(self.new_gen.keys()) | set(self.old_gen.keys())
        return iter(keys)

    def __len__(self):
        # order matters
        return len(set(self.new_gen.keys()) | set(self.old_gen.keys()))


class TimeoutDict: # Don't inherit from MutableMapping: not thread-safe
    """A dictionary that drops its items after they have been in the dict
    for a certain time.

    Use ExpiringDict for a more efficient implementation that doesn't require
    guaranteed timeout.
    """
    __slots__ = ('_lock', 'd', 'timeout')

    def __init__(self, timeout, items=None):
        expiry = time.time() + timeout
        self._lock = threading.Lock()
        self.d = {k: (expiry, v) for (k, v) in (items or {}).items()}
        self.timeout = timeout

    def __reduce__(self):
        return (self.__class__, (self.timeout, dict(self)))

    def __repr__(self):
        return 'TimeoutDict(%s, %r)' % (self.timeout, dict(self))

    def __getitem__(self, key):
        with self._lock:
            try:
                (expiry, value) = self.d[key]
                if expiry < time.time():
                    del self.d[key]
                    raise KeyError
            except KeyError:
                raise KeyError(key) from None

            return value

    def __setitem__(self, key, value):
        with self._lock:
            self.d[key] = (time.time() + self.timeout, value)

    def clear(self):
        with self._lock:
            self.d.clear()

    def __delitem__(self, key):
        with self._lock:
            del self.d[key]

    def _items(self):
        now = time.time()
        with self._lock:
            return [
                (k, v) for (k, (expiry, v)) in self.d.items()
                if expiry >= now]

    def keys(self):
        return [k for (k, v) in self._items()]

    def values(self):
        return [v for (k, v) in self._items()]

    def items(self):
        return self._items()

    def __iter__(self):
        return (k for (k, v) in self._items())

    def __len__(self):
        return len(self._items())

    def __eq__(self, other):
        return self._items() == list(other.items())

    def __ne__(self, other):
        return not (self == other)


class TruncatableSet(collections.abc.MutableSet):
    """A set that keeps track of the order of inserted elements so
    the oldest can be removed."""
    __slots__ = ('_ordered_items', '_items')
    def __init__(self, iterable=[]):
        self._ordered_items = list(iterable)
        self._items = set(self._ordered_items)
    def __repr__(self):
        return 'TruncatableSet({%r})' % self._items
    def __contains__(self, item):
        return item in self._items
    def __iter__(self):
        return iter(self._items)
    def __len__(self):
        return len(self._items)
    def add(self, item):
        if item not in self._items:
            self._items.add(item)
            self._ordered_items.append(item)
    def discard(self, item):
        self._items.discard(item)
        self._ordered_items.remove(item)
    def truncate(self, size):
        assert size >= 0
        removed_size = len(self)-size
        # I make two different cases depending on removed_size<size
        # in order to make if faster if one is significantly bigger than the
        # other.
        if removed_size <= 0:
            return
        elif removed_size < size:
            # If there are more kept items than removed items
            for old_item in self._ordered_items[0:-size]:
                self.discard(old_item)
            self._ordered_items = self._ordered_items[-size:]
        else:
            self._ordered_items = self._ordered_items[-size:]
            self._items = set(self._ordered_items)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
