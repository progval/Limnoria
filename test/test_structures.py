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

from test import *

from structures import *

class RingBufferTestCase(unittest.TestCase):
    def testInit(self):
        self.assertRaises(ValueError, RingBuffer, -1)
        self.assertRaises(ValueError, RingBuffer, 0)
        self.assertEqual(range(10), list(RingBuffer(10, range(10))))

    def testLen(self):
        b = RingBuffer(3)
        self.assertEqual(0, len(b))
        b.append(1)
        self.assertEqual(1, len(b))
        b.append(2)
        self.assertEqual(2, len(b))
        b.append(3)
        self.assertEqual(3, len(b))
        b.append(4)
        self.assertEqual(3, len(b))
        b.append(5)
        self.assertEqual(3, len(b))

    def testNonzero(self):
        b = RingBuffer(3)
        self.failIf(b)
        b.append(1)
        self.failUnless(b)

    def testAppend(self):
        b = RingBuffer(3)
        self.assertEqual([], list(b))
        b.append(1)
        self.assertEqual([1], list(b))
        b.append(2)
        self.assertEqual([1, 2], list(b))
        b.append(3)
        self.assertEqual([1, 2, 3], list(b))
        b.append(4)
        self.assertEqual([2, 3, 4], list(b))
        b.append(5)
        self.assertEqual([3, 4, 5], list(b))
        b.append(6)
        self.assertEqual([4, 5, 6], list(b))

    def testContains(self):
        b = RingBuffer(3, range(3))
        self.failUnless(0 in b)
        self.failUnless(1 in b)
        self.failUnless(2 in b)
        self.failIf(3 in b)

    def testGetitem(self):
        L = range(10)
        b = RingBuffer(len(L), L)
        for i in range(len(b)):
            self.assertEqual(L[i], b[i])
        for i in range(len(b)):
            b.append(i)
        for i in range(len(b)):
            self.assertEqual(L[i], b[i])

    def testSetitem(self):
        L = range(10)
        b = RingBuffer(len(L), [0]*len(L))
        for i in range(len(b)):
            b[i] = i
        for i in range(len(b)):
            self.assertEqual(b[i], i)
        for i in range(len(b)):
            b.append(0)
        for i in range(len(b)):
            b[i] = i
        for i in range(len(b)):
            self.assertEqual(b[i], i)

    def testExtend(self):
        b = RingBuffer(3, range(3))
        self.assertEqual(list(b), range(3))
        b.extend(range(6))
        self.assertEqual(list(b), range(6)[3:])

    def testRepr(self):
        b = RingBuffer(3)
        self.assertEqual(repr(b), 'RingBuffer(3, [])')
        b.append(1)
        self.assertEqual(repr(b), 'RingBuffer(3, [1])')
        b.append(2)
        self.assertEqual(repr(b), 'RingBuffer(3, [1, 2])')
        b.append(3)
        self.assertEqual(repr(b), 'RingBuffer(3, [1, 2, 3])')
        b.append(4)
        self.assertEqual(repr(b), 'RingBuffer(3, [2, 3, 4])')
        b.append(5)
        self.assertEqual(repr(b), 'RingBuffer(3, [3, 4, 5])')
        b.append(6)
        self.assertEqual(repr(b), 'RingBuffer(3, [4, 5, 6])')
