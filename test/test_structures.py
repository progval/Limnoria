#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

from testsupport import *

import pickle

from supybot.structures import *

class RingBufferTestCase(SupyTestCase):
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
            self.assertEqual(L[-i], b[-i])
        for i in range(len(b)):
            b.append(i)
        for i in range(len(b)):
            self.assertEqual(L[i], b[i])
        for i in range(len(b)):
            self.assertEqual(list(b), list(b[:i]) + list(b[i:]))

    def testSliceGetitem(self):
        L = range(10)
        b = RingBuffer(len(L), L)
        for i in range(len(b)):
            self.assertEqual(L[:i], b[:i])
            self.assertEqual(L[i:], b[i:])
            self.assertEqual(L[i:len(b)-i], b[i:len(b)-i])
            self.assertEqual(L[:-i], b[:-i])
            self.assertEqual(L[-i:], b[-i:])
            self.assertEqual(L[i:-i], b[i:-i])
        for i in range(len(b)):
            b.append(i)
        for i in range(len(b)):
            self.assertEqual(L[:i], b[:i])
            self.assertEqual(L[i:], b[i:])
            self.assertEqual(L[i:len(b)-i], b[i:len(b)-i])
            self.assertEqual(L[:-i], b[:-i])
            self.assertEqual(L[-i:], b[-i:])
            self.assertEqual(L[i:-i], b[i:-i])

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

    def testSliceSetitem(self):
        L = range(10)
        b = RingBuffer(len(L), [0]*len(L))
        self.assertRaises(ValueError, b.__setitem__, slice(0, 10), [])
        b[2:4] = L[2:4]
        self.assertEquals(b[2:4], L[2:4])
        for _ in range(len(b)):
            b.append(0)
        b[2:4] = L[2:4]
        self.assertEquals(b[2:4], L[2:4])

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

    def testPickleCopy(self):
        b = RingBuffer(10, range(10))
        self.assertEqual(pickle.loads(pickle.dumps(b)), b)

    def testEq(self):
        b = RingBuffer(3, range(3))
        self.failIf(b == range(3))
        b1 = RingBuffer(3)
        self.failIf(b == b1)
        b1.append(0)
        self.failIf(b == b1)
        b1.append(1)
        self.failIf(b == b1)
        b1.append(2)
        self.failUnless(b == b1)
        b = RingBuffer(100, range(10))
        b1 = RingBuffer(10, range(10))
        self.failIf(b == b1)

    def testIter(self):
        b = RingBuffer(3, range(3))
        L = []
        for elt in b:
            L.append(elt)
        self.assertEqual(L, range(3))
        for elt in range(3):
            b.append(elt)
        del L[:]
        for elt in b:
            L.append(elt)
        self.assertEqual(L, range(3))


class QueueTest(SupyTestCase):
    def testReset(self):
        q = queue()
        q.enqueue(1)
        self.assertEqual(len(q), 1)
        q.reset()
        self.assertEqual(len(q), 0)

    def testGetitem(self):
        q = queue()
        n = 10
        self.assertRaises(IndexError, q.__getitem__, 0)
        for i in xrange(n):
            q.enqueue(i)
        for i in xrange(n):
            self.assertEqual(q[i], i)
        for i in xrange(n, 0, -1):
            self.assertEqual(q[-i], n-i)
        for i in xrange(len(q)):
            self.assertEqual(list(q), list(q[:i]) + list(q[i:]))
        self.assertRaises(IndexError, q.__getitem__, -(n+1))
        self.assertRaises(IndexError, q.__getitem__, n)
        self.assertEqual(q[3:7], queue([3, 4, 5, 6]))

    def testSetitem(self):
        q1 = queue()
        self.assertRaises(IndexError, q1.__setitem__, 0, 0)
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

queue = smallqueue

class SmallQueueTest(SupyTestCase):
    def testReset(self):
        q = queue()
        q.enqueue(1)
        self.assertEqual(len(q), 1)
        q.reset()
        self.assertEqual(len(q), 0)

    def testGetitem(self):
        q = queue()
        n = 10
        self.assertRaises(IndexError, q.__getitem__, 0)
        for i in xrange(n):
            q.enqueue(i)
        for i in xrange(n):
            self.assertEqual(q[i], i)
        for i in xrange(n, 0, -1):
            self.assertEqual(q[-i], n-i)
        for i in xrange(len(q)):
            self.assertEqual(list(q), list(q[:i]) + list(q[i:]))
        self.assertRaises(IndexError, q.__getitem__, -(n+1))
        self.assertRaises(IndexError, q.__getitem__, n)
        self.assertEqual(q[3:7], queue([3, 4, 5, 6]))

    def testSetitem(self):
        q1 = queue()
        self.assertRaises(IndexError, q1.__setitem__, 0, 0)
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


class MaxLengthQueueTestCase(SupyTestCase):
    def testInit(self):
        q = MaxLengthQueue(3, (1, 2, 3))
        self.assertEqual(list(q), [1, 2, 3])
        self.assertRaises(TypeError, MaxLengthQueue, 3, 1, 2, 3)

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


class TwoWayDictionaryTestCase(SupyTestCase):
    def testInit(self):
        d = TwoWayDictionary(foo='bar')
        self.failUnless('foo' in d)
        self.failUnless('bar' in d)

        d = TwoWayDictionary({1: 2})
        self.failUnless(1 in d)
        self.failUnless(2 in d)

    def testSetitem(self):
        d = TwoWayDictionary()
        d['foo'] = 'bar'
        self.failUnless('foo' in d)
        self.failUnless('bar' in d)

    def testDelitem(self):
        d = TwoWayDictionary(foo='bar')
        del d['foo']
        self.failIf('foo' in d)
        self.failIf('bar' in d)
        d = TwoWayDictionary(foo='bar')
        del d['bar']
        self.failIf('bar' in d)
        self.failIf('foo' in d)


class TestTimeoutQueue(SupyTestCase):
    def test(self):
        q = TimeoutQueue(1)
        q.enqueue(1)
        self.assertEqual(len(q), 1)
        q.enqueue(2)
        self.assertEqual(len(q), 2)
        q.enqueue(3)
        self.assertEqual(len(q), 3)
        self.assertEqual(sum(q), 6)
        time.sleep(1)
        self.assertEqual(len(q), 0)
        self.assertEqual(sum(q), 0)

    def testCallableTimeout(self):
        q = TimeoutQueue(lambda : 1)
        q.enqueue(1)
        self.assertEqual(len(q), 1)
        q.enqueue(2)
        self.assertEqual(len(q), 2)
        q.enqueue(3)
        self.assertEqual(len(q), 3)
        self.assertEqual(sum(q), 6)
        time.sleep(1)
        self.assertEqual(len(q), 0)
        self.assertEqual(sum(q), 0)

    def testContains(self):
        q = TimeoutQueue(1)
        q.enqueue(1)
        self.failUnless(1 in q)
        self.failIf(2 in q)
        time.sleep(1)
        self.failIf(1 in q)
        

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

