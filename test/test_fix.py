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

from test import *

import pickle

class FunctionsTest(unittest.TestCase):
    def testCatch(self):
        def f():
            raise Exception
        catch(f)

    def testReviter(self):
        L = range(10)
        revL = list(reviter(L))
        L.reverse()
        self.assertEqual(L, revL, 'reviter didn\'t return reversed list')
        for elt in reviter([]):
            self.fail('reviter caused iteration over empty sequence')

    def testWindow(self):
        L = range(10)
        def wwindow(*args):
            return list(window(*args))
        self.assertEqual(wwindow([], 1), [], 'Empty sequence, empty window')
        self.assertEqual(wwindow([], 2), [], 'Empty sequence, empty window')
        self.assertEqual(wwindow([], 5), [], 'Empty sequence, empty window')
        self.assertEqual(wwindow([], 100), [], 'Empty sequence, empty window')
        self.assertEqual(wwindow(L, 1), [[x] for x in L], 'Window length 1')
        self.assertRaises(ValueError, wwindow, [], 0)
        self.assertRaises(ValueError, wwindow, [], -1)

    def testItersplit(self):
        L = [1, 2, 3] * 3
        s = 'foo bar baz'
        self.assertEqual(list(itersplit(L, lambda x: x == 3)),
                         [[1, 2], [1, 2], [1, 2]])
        self.assertEqual(list(itersplit(L, lambda x: x == 3, True)),
                         [[1, 2], [1, 2], [1, 2], []])
        self.assertEqual(list(itersplit([], lambda x: x)), [])
        self.assertEqual(list(itersplit(s, lambda c: c.isspace())),
                         map(list, s.split()))

    def testIterableMap(self):
        class alist(IterableMap):
            def __init__(self):
                self.L = []

            def __setitem__(self, key, value):
                self.L.append((key, value))

            def iteritems(self):
                for (k, v) in self.L:
                    yield (k, v)
        AL = alist()
        self.failIf(AL)
        AL[1] = 2
        AL[2] = 3
        AL[3] = 4
        self.failUnless(AL)
        self.assertEqual(AL.items(), [(1, 2), (2, 3), (3, 4)])
        self.assertEqual(list(AL.iteritems()), [(1, 2), (2, 3), (3, 4)])
        self.assertEqual(AL.keys(), [1, 2, 3])
        self.assertEqual(list(AL.iterkeys()), [1, 2, 3])
        self.assertEqual(AL.values(), [2, 3, 4])
        self.assertEqual(list(AL.itervalues()), [2, 3, 4])
        self.assertEqual(len(AL), 3)

    def testFlatten(self):
        def lflatten(seq):
            return list(flatten(seq))
        self.assertEqual(lflatten([]), [])
        self.assertEqual(lflatten([1]), [1])
        self.assertEqual(lflatten(range(10)), range(10))
        twoRanges = range(10)*2
        twoRanges.sort()
        self.assertEqual(lflatten(zip(range(10), range(10))), twoRanges)
        self.assertEqual(lflatten([1, [2, 3], 4]), [1, 2, 3, 4])
        self.assertEqual(lflatten([[[[[[[[[[]]]]]]]]]]), [])
        self.assertEqual(lflatten([1, [2, [3, 4], 5], 6]), [1, 2, 3, 4, 5, 6])
        self.assertRaises(TypeError, lflatten, 1)
