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

import types

__all__ = ['RingBuffer']

class RingBuffer(object):
    #__slots__ = ('L', 'i')
    def __init__(self, maxSize, seq=()):
##         if not maxSize and seq:
##             maxSize = len(seq)
        if maxSize <= 0:
            raise ValueError, 'maxSize must be > 0.'
        self.i = maxSize
        self.L = []
        for elt in seq:
            self.append(elt)

    def __len__(self):
        return len(self.L)
    
    def __nonzero__(self):
        return len(self) > 0
    
    def __contains__(self, elt):
        return elt in self.L

    def append(self, elt):
        if len(self) >= self.i:
            self.__class__ = _FullRingBuffer
            self.i = 0
            self.append(elt)
        else:
            self.L.append(elt)

    def extend(self, seq):
        for elt in seq:
            self.append(elt)
            
    def __getitem__(self, idx):
        if type(idx) == types.SliceType:
            pass
        else:
            return self.L[idx]

    def __setitem__(self, idx, elt):
        self.L[idx] = elt

    def __repr__(self):
        return 'RingBuffer(%r, %r)' % (self.i, list(self))

class _FullRingBuffer(RingBuffer):
    #__slots__ = ('L', 'i')
    def append(self, elt):
        self.L[self.i] = elt
        self.i += 1
        self.i %= len(self.L)
    def __getitem__(self, oidx):
        (m, idx) = divmod(oidx, len(self.L))
        if m and m != -1:
            raise IndexError, oidx
        idx = (idx + self.i) % len(self.L)
        return self.L[idx]
    def __setitem__(self, oidx, elt):
        (m, idx) = divmod(oidx, len(self.L))
        if m and m != -1:
            raise IndexError, oidx
        idx = (idx + self.i) % len(self.L)
        self.L[idx] = elt

    def __repr__(self):
        return 'RingBuffer(%r, %r)' % (len(self.L), list(self))
