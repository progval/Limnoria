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

class QueueTest(unittest.TestCase):
    def testGetitem(self):
        q = queue()
        n = 10
        for i in xrange(n):
            q.enqueue(i)
        for i in xrange(n):
            self.assertEqual(q[i], i)
        for i in xrange(n, 0, -1):
            self.assertEqual(q[-i], n-i)
        self.assertRaises(IndexError, q.__getitem__, -(n+1))
        self.assertRaises(IndexError, q.__getitem__, n)
        #self.assertEqual(q[3:7], queue([3, 4, 5, 6]))
        
    def testSetitem(self):
        q1 = queue()
        for i in xrange(10):
            q1.enqueue(i)
        q2 = eval(repr(q1))
        for (i, elt) in enumerate(q2):
            q2[i] = elt*2
        self.assertEqual([x*2 for x in q1], list(q2))
        
    def testNonzero(self):
        q = queue()
        self.failIf(q, 'queue not zero after initialization')
        q.enqueue(1)
        self.failUnless(q, 'queue zero after adding element')
        q.dequeue()
        self.failIf(q, 'queue not zero after dequeue of only element')

    def testLen(self):
        q = queue()
        self.assertEqual(0, len(q), 'queue len not 0 after initialization')
        q.enqueue(1)
        self.assertEqual(1, len(q), 'queue len not 1 after enqueue')
        q.enqueue(2)
        self.assertEqual(2, len(q), 'queue len not 2 after enqueue')
        q.dequeue()
        self.assertEqual(1, len(q), 'queue len not 1 after dequeue')
        q.dequeue()
        self.assertEqual(0, len(q), 'queue len not 0 after dequeue')
        for i in range(10):
            L = range(i)
            q = queue(L)
            self.assertEqual(len(q), i)

    def testEq(self):
        q1 = queue()
        q2 = queue()
        self.failUnless(q1 == q1, 'queue not equal to itself')
        self.failUnless(q2 == q2, 'queue not equal to itself')
        self.failUnless(q1 == q2, 'initialized queues not equal')
        q1.enqueue(1)
        self.failUnless(q1 == q1, 'queue not equal to itself')
        self.failUnless(q2 == q2, 'queue not equal to itself')
        q2.enqueue(1)
        self.failUnless(q1 == q1, 'queue not equal to itself')
        self.failUnless(q2 == q2, 'queue not equal to itself')
        self.failUnless(q1 == q2, 'queues not equal after identical enqueue')
        q1.dequeue()
        self.failUnless(q1 == q1, 'queue not equal to itself')
        self.failUnless(q2 == q2, 'queue not equal to itself')
        self.failIf(q1 == q2, 'queues equal after one dequeue')
        q2.dequeue()
        self.failUnless(q1 == q2, 'queues not equal after both are dequeued')
        self.failUnless(q1 == q1, 'queue not equal to itself')
        self.failUnless(q2 == q2, 'queue not equal to itself')

    def testInit(self):
        self.assertEqual(len(queue()), 0, 'queue len not 0 after init')
        q = queue()
        q.enqueue(1)
        q.enqueue(2)
        q.enqueue(3)
        self.assertEqual(queue((1, 2, 3)),q, 'init not equivalent to enqueues')
        q = queue((1, 2, 3))
        self.assertEqual(q.dequeue(), 1, 'values not returned in proper order')
        self.assertEqual(q.dequeue(), 2, 'values not returned in proper order')
        self.assertEqual(q.dequeue(), 3, 'values not returned in proper order')

    def testRepr(self):
        q = queue()
        q.enqueue(1)
        self.assertEqual(q, eval(repr(q)), 'repr doesn\'t eval to same queue')
        q.enqueue('foo')
        self.assertEqual(q, eval(repr(q)), 'repr doesn\'t eval to same queue')
        q.enqueue(None)
        self.assertEqual(q, eval(repr(q)), 'repr doesn\'t eval to same queue')
        q.enqueue(1.0)
        self.assertEqual(q, eval(repr(q)), 'repr doesn\'t eval to same queue')
        q.enqueue([])
        self.assertEqual(q, eval(repr(q)), 'repr doesn\'t eval to same queue')
        q.enqueue(())
        self.assertEqual(q, eval(repr(q)), 'repr doesn\'t eval to same queue')
        q.enqueue([1])
        self.assertEqual(q, eval(repr(q)), 'repr doesn\'t eval to same queue')
        q.enqueue((1,))
        self.assertEqual(q, eval(repr(q)), 'repr doesn\'t eval to same queue')
        
    def testEnqueueDequeue(self):
        q = queue()
        self.assertRaises(IndexError, q.dequeue)
        q.enqueue(1)
        self.assertEqual(q.dequeue(), 1,
                         'first dequeue didn\'t return same as first enqueue')
        q.enqueue(1)
        q.enqueue(2)
        q.enqueue(3)
        self.assertEqual(q.dequeue(), 1)
        self.assertEqual(q.dequeue(), 2)
        self.assertEqual(q.dequeue(), 3)

    def testPeek(self):
        q = queue()
        self.assertRaises(IndexError, q.peek)
        q.enqueue(1)
        self.assertEqual(q.peek(), 1, 'peek didn\'t return first enqueue')
        q.enqueue(2)
        self.assertEqual(q.peek(), 1, 'peek didn\'t return first enqueue')
        q.dequeue()
        self.assertEqual(q.peek(), 2, 'peek didn\'t return second enqueue')
        q.dequeue()
        self.assertRaises(IndexError, q.peek)

    def testContains(self):
        q = queue()
        self.failIf(1 in q, 'empty queue cannot have elements')
        q.enqueue(1)
        self.failUnless(1 in q, 'recent enqueued element not in q')
        q.enqueue(2)
        self.failUnless(1 in q, 'original enqueued element not in q')
        self.failUnless(2 in q, 'second enqueued element not in q')
        q.dequeue()
        self.failIf(1 in q, 'dequeued element in q')
        self.failUnless(2 in q, 'not dequeued element not in q')
        q.dequeue()
        self.failIf(2 in q, 'dequeued element in q')

    def testIter(self):
        q1 = queue((1, 2, 3))
        q2 = queue()
        for i in q1:
            q2.enqueue(i)
        self.assertEqual(q1, q2, 'iterate didn\'t return all elements')
        for _ in queue():
            self.fail('no elements should be in empty queue')

    def testPickleCopy(self):
        q = queue(range(10))
        self.assertEqual(q, pickle.loads(pickle.dumps(q)))


class MaxLengthQueueTestCase(unittest.TestCase):
    def testMaxLength(self):
        q = MaxLengthQueue(3)
        q.enqueue(1)
        self.assertEqual(len(q), 1)
        q.enqueue(2)
        self.assertEqual(len(q), 2)
        q.enqueue(3)
        self.assertEqual(len(q), 3)
        q.enqueue(4)
        self.assertEqual(len(q), 3)
        self.assertEqual(q.peek(), 2)
        q.enqueue(5)
        self.assertEqual(len(q), 3)
        self.assertEqual(q[0], 3)

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
