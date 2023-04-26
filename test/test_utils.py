###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009,2011, James McCoy
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

from supybot.test import *

import sys
import time
import pickle
import supybot.conf as conf
import supybot.utils as utils
from supybot.utils.structures import *
import supybot.utils.minisix as minisix

class UtilsTest(SupyTestCase):
    def testReversed(self):
        L = list(range(10))
        revL = list(reversed(L))
        L.reverse()
        self.assertEqual(L, revL, 'reversed didn\'t return reversed list')
        for _ in reversed([]):
            self.fail('reversed caused iteration over empty sequence')


class SeqTest(SupyTestCase):
    def testRenumerate(self):
        for i in range(5):
            L = list(enumerate(range(i)))
            LL = list(utils.seq.renumerate(range(i)))
            self.assertEqual(L, LL[::-1])
        
    def testWindow(self):
        L = list(range(10))
        def wwindow(*args):
            return list(utils.seq.window(*args))
        self.assertEqual(wwindow([], 1), [], 'Empty sequence, empty window')
        self.assertEqual(wwindow([], 2), [], 'Empty sequence, empty window')
        self.assertEqual(wwindow([], 5), [], 'Empty sequence, empty window')
        self.assertEqual(wwindow([], 100), [], 'Empty sequence, empty window')
        self.assertEqual(wwindow(L, 1), [[x] for x in L], 'Window length 1')
        self.assertRaises(ValueError, wwindow, [], 0)
        self.assertRaises(ValueError, wwindow, [], -1)



class GenTest(SupyTestCase):
    def testInsensitivePreservingDict(self):
        ipd = utils.InsensitivePreservingDict
        d = ipd(dict(Foo=10))
        self.assertEqual(d['foo'], 10)
        self.assertEqual(d.keys(), ['Foo'])
        self.assertEqual(d.get('foo'), 10)
        self.assertEqual(d.get('Foo'), 10)

    def testFindBinaryInPath(self):
        if os.name == 'posix':
            self.assertEqual(None, utils.findBinaryInPath('asdfhjklasdfhjkl'))
            self.assertTrue(utils.findBinaryInPath('sh').endswith('/bin/sh'))

    def testExnToString(self):
        try:
            raise KeyError(1)
        except Exception as e:
            self.assertEqual(utils.exnToString(e), 'KeyError: 1')
        try:
            raise EOFError()
        except Exception as e:
            self.assertEqual(utils.exnToString(e), 'EOFError')

    def testSaltHash(self):
        s = utils.saltHash('jemfinch')
        (salt, hash) = s.split('|')
        self.assertEqual(utils.saltHash('jemfinch', salt=salt), s)

    def testSafeEval(self):
        for s in ['1', '()', '(1,)', '[]', '{}', '{1:2}', '{1:(2,3)}',
                  '1.0', '[1,2,3]', 'True', 'False', 'None',
                  '(True,False,None)', '"foo"', '{"foo": "bar"}']:
            self.assertEqual(eval(s), utils.safeEval(s))
        for s in ['lambda: 2', 'import foo', 'foo.bar']:
            self.assertRaises(ValueError, utils.safeEval, s)

    def testSafeEvalTurnsSyntaxErrorIntoValueError(self):
        self.assertRaises(ValueError, utils.safeEval, '/usr/local/')

    def testIterableMap(self):
        class alist(utils.IterableMap):
            def __init__(self):
                self.L = []

            def __setitem__(self, key, value):
                self.L.append((key, value))

            def items(self):
                for (k, v) in self.L:
                    yield (k, v)
        AL = alist()
        self.assertFalse(AL)
        AL[1] = 2
        AL[2] = 3
        AL[3] = 4
        self.assertTrue(AL)
        self.assertEqual(list(AL.items()), [(1, 2), (2, 3), (3, 4)])
        self.assertEqual(list(AL.items()), [(1, 2), (2, 3), (3, 4)])
        self.assertEqual(list(AL.keys()), [1, 2, 3])
        if minisix.PY2:
            self.assertEqual(list(AL.keys()), [1, 2, 3])
            self.assertEqual(list(AL.values()), [2, 3, 4])
            self.assertEqual(list(AL.values()), [2, 3, 4])
        self.assertEqual(len(AL), 3)

    def testSortBy(self):
        L = ['abc', 'z', 'AD']
        utils.sortBy(len, L)
        self.assertEqual(L, ['z', 'AD', 'abc'])
        utils.sortBy(str.lower, L)
        self.assertEqual(L, ['abc', 'AD', 'z'])
        L = ['supybot', 'Supybot']
        utils.sortBy(str.lower, L)
        self.assertEqual(L, ['supybot', 'Supybot'])

    def testSorted(self):
        L = ['a', 'c', 'b']
        self.assertEqual(sorted(L), ['a', 'b', 'c'])
        self.assertEqual(L, ['a', 'c', 'b'])
        self.assertEqual(sorted(L, reverse=True), ['c', 'b', 'a'])

    def testTimeElapsed(self):
        self.assertRaises(ValueError, utils.timeElapsed, 0,
                          leadingZeroes=False, seconds=False)
        then = 0
        now = 0
        for now, expected in [(0, '0 seconds'),
                              (1, '1 second'),
                              (60, '1 minute and 0 seconds'),
                              (61, '1 minute and 1 second'),
                              (62, '1 minute and 2 seconds'),
                              (122, '2 minutes and 2 seconds'),
                              (3722, '1 hour, 2 minutes, and 2 seconds'),
                              (7322, '2 hours, 2 minutes, and 2 seconds'),
                              (90061,'1 day, 1 hour, 1 minute, and 1 second'),
                              (180122, '2 days, 2 hours, 2 minutes, '
                                       'and 2 seconds')]:
            self.assertEqual(utils.timeElapsed(now - then), expected)

    def timeElapsedShort(self):
        self.assertEqual(utils.timeElapsed(123, short=True), '2m 3s')

    def testAbbrev(self):
        L = ['abc', 'bcd', 'bbe', 'foo', 'fool']
        d = utils.abbrev(L)
        def getItem(s):
            return d[s]
        self.assertRaises(KeyError, getItem, 'f')
        self.assertRaises(KeyError, getItem, 'fo')
        self.assertRaises(KeyError, getItem, 'b')
        self.assertEqual(d['bb'], 'bbe')
        self.assertEqual(d['bc'], 'bcd')
        self.assertEqual(d['a'], 'abc')
        self.assertEqual(d['ab'], 'abc')
        self.assertEqual(d['fool'], 'fool')
        self.assertEqual(d['foo'], 'foo')

    def testAbbrevFailsWithDups(self):
        L = ['english', 'english']
        self.assertRaises(ValueError, utils.abbrev, L)


class StrTest(SupyTestCase):
    def testRsplit(self):
        rsplit = utils.str.rsplit
        self.assertEqual(rsplit('foo bar baz'), 'foo bar baz'.split())
        self.assertEqual(rsplit('foo bar baz', maxsplit=1),
                         ['foo bar', 'baz'])
        self.assertEqual(rsplit('foo        bar baz', maxsplit=1),
                         ['foo        bar', 'baz'])
        self.assertEqual(rsplit('foobarbaz', 'bar'), ['foo', 'baz'])

    def testMatchCase(self):
        f = utils.str.matchCase
        self.assertEqual('bar', f('foo', 'bar'))
        self.assertEqual('Bar', f('Foo', 'bar'))
        self.assertEqual('BAr', f('FOo', 'bar'))
        self.assertEqual('BAR', f('FOO', 'bar'))
        self.assertEqual('bAR', f('fOO', 'bar'))
        self.assertEqual('baR', f('foO', 'bar'))
        self.assertEqual('BaR', f('FoO', 'bar'))

    def testPluralize(self):
        f = utils.str.pluralize
        self.assertEqual('bikes', f('bike'))
        self.assertEqual('BIKES', f('BIKE'))
        self.assertEqual('matches', f('match'))
        self.assertEqual('Patches', f('Patch'))
        self.assertEqual('fishes', f('fish'))
        self.assertEqual('tries', f('try'))
        self.assertEqual('days', f('day'))

    def testDepluralize(self):
        f = utils.str.depluralize
        self.assertEqual('bike', f('bikes'))
        self.assertEqual('Bike', f('Bikes'))
        self.assertEqual('BIKE', f('BIKES'))
        self.assertEqual('match', f('matches'))
        self.assertEqual('Match', f('Matches'))
        self.assertEqual('fish', f('fishes'))
        self.assertEqual('try', f('tries'))

    def testDistance(self):
        self.assertEqual(utils.str.distance('', ''), 0)
        self.assertEqual(utils.str.distance('a', 'b'), 1)
        self.assertEqual(utils.str.distance('a', 'a'), 0)
        self.assertEqual(utils.str.distance('foobar', 'jemfinch'), 8)
        self.assertEqual(utils.str.distance('a', 'ab'), 1)
        self.assertEqual(utils.str.distance('foo', ''), 3)
        self.assertEqual(utils.str.distance('', 'foo'), 3)
        self.assertEqual(utils.str.distance('appel', 'nappe'), 2)
        self.assertEqual(utils.str.distance('nappe', 'appel'), 2)

    def testSoundex(self):
        L = [('Euler', 'E460'),
             ('Ellery', 'E460'),
             ('Gauss', 'G200'),
             ('Ghosh', 'G200'),
             ('Hilbert', 'H416'),
             ('Heilbronn', 'H416'),
             ('Knuth', 'K530'),
             ('Kant', 'K530'),
             ('Lloyd', 'L300'),
             ('Ladd', 'L300'),
             ('Lukasiewicz', 'L222'),
             ('Lissajous', 'L222')]
        for (name, key) in L:
            soundex = utils.str.soundex(name)
            self.assertEqual(soundex, key,
                             '%s was %s, not %s' % (name, soundex, key))
        self.assertRaises(ValueError, utils.str.soundex, '3')
        self.assertRaises(ValueError, utils.str.soundex, "'")

    def testDQRepr(self):
        L = ['foo', 'foo\'bar', 'foo"bar', '"', '\\', '', '\x00']
        for s in L:
            r = utils.str.dqrepr(s)
            self.assertEqual(s, eval(r), s)
            self.assertTrue(r[0] == '"' and r[-1] == '"', s)

    def testPerlReToPythonRe(self):
        f = utils.str.perlReToPythonRe
        r = f('m/foo/')
        self.assertTrue(r.search('foo'))
        r = f('/foo/')
        self.assertTrue(r.search('foo'))
        r = f('m/\\//')
        self.assertTrue(r.search('/'))
        r = f('m/cat/i')
        self.assertTrue(r.search('CAT'))
        self.assertRaises(ValueError, f, 'm/?/')

    def testP2PReDifferentSeparator(self):
        r = utils.str.perlReToPythonRe('m!foo!')
        self.assertTrue(r.search('foo'))
        r = utils.str.perlReToPythonRe('m{cat}')
        self.assertTrue(r.search('cat'))

    def testPerlReToReplacer(self):
        PRTR = utils.str.perlReToReplacer
        f = PRTR('s/foo/bar/')
        self.assertEqual(f('foobarbaz'), 'barbarbaz')
        f = PRTR('s/fool/bar/')
        self.assertEqual(f('foobarbaz'), 'foobarbaz')
        f = PRTR('s/foo//')
        self.assertEqual(f('foobarbaz'), 'barbaz')
        f = PRTR('s/ba//')
        self.assertEqual(f('foobarbaz'), 'foorbaz')
        f = PRTR('s/ba//g')
        self.assertEqual(f('foobarbaz'), 'foorz')
        f = PRTR('s/ba\\///g')
        self.assertEqual(f('fooba/rba/z'), 'foorz')
        f = PRTR('s/ba\\\\//g')
        self.assertEqual(f('fooba\\rba\\z'), 'foorz')
        f = PRTR('s/cat/dog/i')
        self.assertEqual(f('CATFISH'), 'dogFISH')
        f = PRTR(r's/foo/foo\/bar/')
        self.assertEqual(f('foo'), 'foo/bar')
        f = PRTR('s/^/foo/')
        self.assertEqual(f('bar'), 'foobar')

    def testMultipleReplacer(self):
        replacer = utils.str.MultipleReplacer({'foo': 'bar', 'a': 'b'})
        self.assertEqual(replacer('hi foo hi'), 'hi bar hi')

    def testMultipleRemover(self):
        remover = utils.str.MultipleRemover(['foo', 'bar'])
        self.assertEqual(remover('testfoobarbaz'), 'testbaz')

    def testPReToReplacerDifferentSeparator(self):
        f = utils.str.perlReToReplacer('s#foo#bar#')
        self.assertEqual(f('foobarbaz'), 'barbarbaz')

    def testPerlReToReplacerBug850931(self):
        f = utils.str.perlReToReplacer(r's/\b(\w+)\b/\1./g')
        self.assertEqual(f('foo bar baz'), 'foo. bar. baz.')

    def testCommaAndify(self):
        f = utils.str.commaAndify
        L = ['foo']
        original = L[:]
        self.assertEqual(f(L), 'foo')
        self.assertEqual(f(L, And='or'), 'foo')
        self.assertEqual(L, original)
        L.append('bar')
        original = L[:]
        self.assertEqual(f(L), 'foo and bar')
        self.assertEqual(f(L, And='or'), 'foo or bar')
        self.assertEqual(L, original)
        L.append('baz')
        original = L[:]
        self.assertEqual(f(L), 'foo, bar, and baz')
        self.assertEqual(f(L, And='or'), 'foo, bar, or baz')
        self.assertEqual(f(L, comma=';'), 'foo; bar; and baz')
        self.assertEqual(f(L, comma=';', And='or'),
                         'foo; bar; or baz')
        self.assertEqual(L, original)
        self.assertTrue(f(set(L)))

    def testCommaAndifyRaisesTypeError(self):
        L = [(2,)]
        self.assertRaises(TypeError, utils.str.commaAndify, L)
        L.append((3,))
        self.assertRaises(TypeError, utils.str.commaAndify, L)

    def testCommaAndifyConfig(self):
        f = utils.str.commaAndify
        L = ['foo', 'bar']
        with conf.supybot.reply.format.list.maximumItems.context(3):
            self.assertEqual(f(L), 'foo and bar')
            L.append('baz')
            self.assertEqual(f(L), 'foo, bar, and baz')
            L.append('qux')
            self.assertEqual(f(L), 'foo, bar, and 2 others')
            L.append('quux')
            self.assertEqual(f(L), 'foo, bar, and 3 others')

    def testUnCommaThe(self):
        f = utils.str.unCommaThe
        self.assertEqual(f('foo bar'), 'foo bar')
        self.assertEqual(f('foo bar, the'), 'the foo bar')
        self.assertEqual(f('foo bar, The'), 'The foo bar')
        self.assertEqual(f('foo bar,the'), 'the foo bar')

    def testNormalizeWhitespace(self):
        f = utils.str.normalizeWhitespace
        self.assertEqual(f('foo   bar'), 'foo bar')
        self.assertEqual(f('foo\nbar'), 'foo bar')
        self.assertEqual(f('foo\tbar'), 'foo bar')
        self.assertEqual(f('foo\rbar'), 'foo bar')

    def testNItems(self):
        nItems = utils.str.nItems
        self.assertEqual(nItems(0, 'tool'), '0 tools')
        self.assertEqual(nItems(1, 'tool', 'crazy'), '1 crazy tool')
        self.assertEqual(nItems(1, 'tool'), '1 tool')
        self.assertEqual(nItems(2, 'tool', 'crazy'), '2 crazy tools')
        self.assertEqual(nItems(2, 'tool'), '2 tools')

    def testOrdinal(self):
        ordinal = utils.str.ordinal
        self.assertEqual(ordinal(3), '3rd')
        self.assertEqual(ordinal('3'), '3rd')
        self.assertRaises(ValueError, ordinal, 'a')

    def testEllipsisify(self):
        f = utils.str.ellipsisify
        self.assertEqual(f('x'*30, 30), 'x'*30)
        self.assertLessEqual(len(f('x'*35, 30)), 30)
        self.assertTrue(f(' '.join(['xxxx']*10), 30)[:-3].endswith('xxxx'))


class IterTest(SupyTestCase):
    def testLimited(self):
        L = range(10)
        self.assertEqual([], list(utils.iter.limited(L, 0)))
        self.assertEqual([0], list(utils.iter.limited(L, 1)))
        self.assertEqual([0, 1], list(utils.iter.limited(L, 2)))
        self.assertEqual(list(range(10)), list(utils.iter.limited(L, 10)))
        self.assertRaises(ValueError, list, utils.iter.limited(L, 11))

    def testRandomChoice(self):
        choice = utils.iter.choice
        self.assertRaises(IndexError, choice, {})
        self.assertRaises(IndexError, choice, [])
        self.assertRaises(IndexError, choice, ())
        L = [1, 2]
        seenList = set()
        seenIterable = set()
        for n in range(300):
            # 2**266 > 10**80, the number of atoms in the known universe.
            # (ignoring dark matter, but that likely doesn't exist in atoms
            #  anyway, so it shouldn't have a significant impact on that #)
            seenList.add(choice(L))
            seenIterable.add(choice(iter(L)))
        self.assertEqual(len(L), len(seenList),
                         'choice isn\'t being random with lists')
        self.assertEqual(len(L), len(seenIterable),
                         'choice isn\'t being random with iterables')

##     def testGroup(self):
##         group = utils.iter.group
##         s = '1. d4 d5 2. Nf3 Nc6 3. e3 Nf6 4. Nc3 e6 5. Bd3 a6'
##         self.assertEqual(group(s.split(), 3)[:3],
##                          [['1.', 'd4', 'd5'],
##                           ['2.', 'Nf3', 'Nc6'],
##                           ['3.', 'e3', 'Nf6']])

    def testAny(self):
        any = utils.iter.any
        self.assertTrue(any(lambda i: i == 0, range(10)))
        self.assertFalse(any(None, range(1)))
        self.assertTrue(any(None, range(2)))
        self.assertFalse(any(None, []))

    def testAll(self):
        all = utils.iter.all
        self.assertFalse(all(lambda i: i == 0, range(10)))
        self.assertFalse(all(lambda i: i % 2, range(2)))
        self.assertFalse(all(lambda i: i % 2 == 0, [1, 3, 5]))
        self.assertTrue(all(lambda i: i % 2 == 0, [2, 4, 6]))
        self.assertTrue(all(None, ()))

    def testPartition(self):
        partition = utils.iter.partition
        L = range(10)
        def even(i):
            return not(i % 2)
        (yes, no) = partition(even, L)
        self.assertEqual(yes, [0, 2, 4, 6, 8])
        self.assertEqual(no, [1, 3, 5, 7, 9])

    def testIlen(self):
        ilen = utils.iter.ilen
        self.assertEqual(ilen(iter(range(10))), 10)

    def testSplit(self):
        itersplit = utils.iter.split
        L = [1, 2, 3] * 3
        s = 'foo bar baz'
        self.assertEqual(list(itersplit(lambda x: x == 3, L)),
                         [[1, 2], [1, 2], [1, 2]])
        self.assertEqual(list(itersplit(lambda x: x == 3, L, yieldEmpty=True)),
                         [[1, 2], [1, 2], [1, 2], []])
        self.assertEqual(list(itersplit(lambda x: x, [])), [])
        self.assertEqual(list(itersplit(lambda c: c.isspace(), s)),
                         list(map(list, s.split())))
        self.assertEqual(list(itersplit('for'.__eq__, ['foo', 'for', 'bar'])),
                         [['foo'], ['bar']])
        self.assertEqual(list(itersplit('for'.__eq__,
                                        ['foo','for','bar','for', 'baz'], 1)),
                         [['foo'], ['bar', 'for', 'baz']])

    def testFlatten(self):
        def lflatten(seq):
            return list(utils.iter.flatten(seq))
        self.assertEqual(lflatten([]), [])
        self.assertEqual(lflatten([1]), [1])
        self.assertEqual(lflatten(range(10)), list(range(10)))
        twoRanges = list(range(10))*2
        twoRanges.sort()
        self.assertEqual(lflatten(list(zip(range(10), range(10)))), twoRanges)
        self.assertEqual(lflatten([1, [2, 3], 4]), [1, 2, 3, 4])
        self.assertEqual(lflatten([[[[[[[[[[]]]]]]]]]]), [])
        self.assertEqual(lflatten([1, [2, [3, 4], 5], 6]), [1, 2, 3, 4, 5, 6])
        self.assertRaises(TypeError, lflatten, 1)


class FileTest(SupyTestCase):
    def testLines(self):
        L = ['foo', 'bar', '#baz', '  ', 'biff']
        self.assertEqual(list(utils.file.nonEmptyLines(L)),
                         ['foo', 'bar', '#baz', 'biff'])
        self.assertEqual(list(utils.file.nonCommentLines(L)),
                         ['foo', 'bar', '  ', 'biff'])
        self.assertEqual(list(utils.file.nonCommentNonEmptyLines(L)),
                         ['foo', 'bar', 'biff'])

    def testMktemp(self):
        # This is mostly to test that it actually halts.
        self.assertTrue(utils.file.mktemp())
        self.assertTrue(utils.file.mktemp())
        self.assertTrue(utils.file.mktemp())

    def testSanitizeName(self):
        self.assertEqual(utils.file.sanitizeName('#foo'), '#foo')
        self.assertEqual(utils.file.sanitizeName('#f/../oo'), '#f..oo')


class NetTest(SupyTestCase):
    def testEmailRe(self):
        emailRe = utils.net.emailRe
        self.assertTrue(emailRe.match('jemfinch@supybot.com'))

    def testIsIP(self):
        isIP = utils.net.isIP
        self.assertFalse(isIP('a.b.c'))
        self.assertFalse(isIP('256.0.0.0'))
        self.assertFalse(isIP('127.0.0.1 127.0.0.1'))
        self.assertTrue(isIP('0.0.0.0'))
        self.assertTrue(isIP('100.100.100.100'))
        self.assertTrue(isIP('255.255.255.255'))

    def testIsIPV6(self):
        f = utils.net.isIPV6
        self.assertFalse(f('2001:: 2001::'))
        self.assertTrue(f('2001::'))
        self.assertTrue(f('2001:888:0:1::666'))

class WebTest(SupyTestCase):
    def testHtmlToText(self):
        self.assertEqual(
            utils.web.htmlToText('foo<p>bar<span>baz</span>qux</p>quux'),
            'foo barbazqux quux')

    def testGetDomain(self):
        url = 'http://slashdot.org/foo/bar.exe'
        self.assertEqual(utils.web.getDomain(url), 'slashdot.org')

    if network:
        def testGetUrlWithSize(self):
            url = 'http://slashdot.org/'
            self.assertEqual(len(utils.web.getUrl(url, 1024)), 1024)

class FormatTestCase(SupyTestCase):
    def testNormal(self):
        format = utils.str.format
        self.assertEqual(format('I have %n of fruit: %L.', (3, 'kind'),
                                ['apples', 'oranges', 'watermelon']),
                         'I have 3 kinds of fruit: '
                         'apples, oranges, and watermelon.')

    def testPercentL(self):
        self.assertIn(format('%L', set(['apples', 'oranges', 'watermelon'])), [
                         'apples, oranges, and watermelon',
                         'oranges, apples, and watermelon',
                         'apples, watermelon, and oranges',
                         'oranges, watermelon, and apples',
                         'watermelon, apples, and oranges',
                         'watermelon, oranges, and apples'])

        self.assertEqual(format('%L',
            (['apples', 'oranges', 'watermelon'], 'or')),
            'apples, oranges, or watermelon')
class RingBufferTestCase(SupyTestCase):
    def testInit(self):
        self.assertRaises(ValueError, RingBuffer, -1)
        self.assertRaises(ValueError, RingBuffer, 0)
        self.assertEqual(list(range(10)), list(RingBuffer(10, range(10))))

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
        self.assertFalse(b)
        b.append(1)
        self.assertTrue(b)

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
        self.assertIn(0, b)
        self.assertIn(1, b)
        self.assertIn(2, b)
        self.assertNotIn(3, b)

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
        L = list(range(10))
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
        L = list(range(10))
        b = RingBuffer(len(L), [0]*len(L))
        self.assertRaises(ValueError, b.__setitem__, slice(0, 10), [])
        b[2:4] = L[2:4]
        self.assertEqual(b[2:4], L[2:4])
        for _ in range(len(b)):
            b.append(0)
        b[2:4] = L[2:4]
        self.assertEqual(b[2:4], L[2:4])

    def testExtend(self):
        b = RingBuffer(3, range(3))
        self.assertEqual(list(b), list(range(3)))
        b.extend(range(6))
        self.assertEqual(list(b), list(range(6)[3:]))

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
        self.assertNotEqual(b, list(range(3)))
        b1 = RingBuffer(3)
        self.assertNotEqual(b, b1)
        b1.append(0)
        self.assertNotEqual(b, b1)
        b1.append(1)
        self.assertNotEqual(b, b1)
        b1.append(2)
        self.assertEqual(b, b1)
        b = RingBuffer(100, range(10))
        b1 = RingBuffer(10, range(10))
        self.assertNotEqual(b, b1)

    def testIter(self):
        b = RingBuffer(3, range(3))
        L = []
        for elt in b:
            L.append(elt)
        self.assertEqual(L, list(range(3)))
        for elt in range(3):
            b.append(elt)
        del L[:]
        for elt in b:
            L.append(elt)
        self.assertEqual(L, list(range(3)))


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
        for i in range(n):
            q.enqueue(i)
        for i in range(n):
            self.assertEqual(q[i], i)
        for i in range(n, 0, -1):
            self.assertEqual(q[-i], n-i)
        for i in range(len(q)):
            self.assertEqual(list(q), list(q[:i]) + list(q[i:]))
        self.assertRaises(IndexError, q.__getitem__, -(n+1))
        self.assertRaises(IndexError, q.__getitem__, n)
        self.assertEqual(q[3:7], queue([3, 4, 5, 6]))

    def testSetitem(self):
        q1 = queue()
        self.assertRaises(IndexError, q1.__setitem__, 0, 0)
        for i in range(10):
            q1.enqueue(i)
        q2 = eval(repr(q1))
        for (i, elt) in enumerate(q2):
            q2[i] = elt*2
        self.assertEqual([x*2 for x in q1], list(q2))

    def testNonzero(self):
        q = queue()
        self.assertFalse(q, 'queue not zero after initialization')
        q.enqueue(1)
        self.assertTrue(q, 'queue zero after adding element')
        q.dequeue()
        self.assertFalse(q, 'queue not zero after dequeue of only element')

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
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')
        self.assertEqual(q1, q2, 'initialized queues not equal')
        q1.enqueue(1)
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')
        q2.enqueue(1)
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')
        self.assertEqual(q1, q2, 'queues not equal after identical enqueue')
        q1.dequeue()
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')
        self.assertNotEqual(q1, q2, 'queues equal after one dequeue')
        q2.dequeue()
        self.assertEqual(q1, q2, 'queues not equal after both are dequeued')
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')

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
        self.assertNotIn(1, q, 'empty queue cannot have elements')
        q.enqueue(1)
        self.assertIn(1, q, 'recent enqueued element not in q')
        q.enqueue(2)
        self.assertIn(1, q, 'original enqueued element not in q')
        self.assertIn(2, q, 'second enqueued element not in q')
        q.dequeue()
        self.assertNotIn(1, q, 'dequeued element in q')
        self.assertIn(2, q, 'not dequeued element not in q')
        q.dequeue()
        self.assertNotIn(2, q, 'dequeued element in q')

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
        for i in range(n):
            q.enqueue(i)
        for i in range(n):
            self.assertEqual(q[i], i)
        for i in range(n, 0, -1):
            self.assertEqual(q[-i], n-i)
        for i in range(len(q)):
            self.assertEqual(list(q), list(q[:i]) + list(q[i:]))
        self.assertRaises(IndexError, q.__getitem__, -(n+1))
        self.assertRaises(IndexError, q.__getitem__, n)
        self.assertEqual(q[3:7], queue([3, 4, 5, 6]))

    def testSetitem(self):
        q1 = queue()
        self.assertRaises(IndexError, q1.__setitem__, 0, 0)
        for i in range(10):
            q1.enqueue(i)
        q2 = eval(repr(q1))
        for (i, elt) in enumerate(q2):
            q2[i] = elt*2
        self.assertEqual([x*2 for x in q1], list(q2))

    def testNonzero(self):
        q = queue()
        self.assertFalse(q, 'queue not zero after initialization')
        q.enqueue(1)
        self.assertTrue(q, 'queue zero after adding element')
        q.dequeue()
        self.assertFalse(q, 'queue not zero after dequeue of only element')

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
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')
        self.assertEqual(q1, q2, 'initialized queues not equal')
        q1.enqueue(1)
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')
        q2.enqueue(1)
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')
        self.assertEqual(q1, q2, 'queues not equal after identical enqueue')
        q1.dequeue()
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')
        self.assertNotEqual(q1, q2, 'queues equal after one dequeue')
        q2.dequeue()
        self.assertEqual(q1, q2, 'queues not equal after both are dequeued')
        self.assertEqual(q1, q1, 'queue not equal to itself')
        self.assertEqual(q2, q2, 'queue not equal to itself')

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
        self.assertNotIn(1, q, 'empty queue cannot have elements')
        q.enqueue(1)
        self.assertIn(1, q, 'recent enqueued element not in q')
        q.enqueue(2)
        self.assertIn(1, q, 'original enqueued element not in q')
        self.assertIn(2, q, 'second enqueued element not in q')
        q.dequeue()
        self.assertNotIn(1, q, 'dequeued element in q')
        self.assertIn(2, q, 'not dequeued element not in q')
        q.dequeue()
        self.assertNotIn(2, q, 'dequeued element in q')

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
        self.assertIn('foo', d)
        self.assertIn('bar', d)

        d = TwoWayDictionary({1: 2})
        self.assertIn(1, d)
        self.assertIn(2, d)

    def testSetitem(self):
        d = TwoWayDictionary()
        d['foo'] = 'bar'
        self.assertIn('foo', d)
        self.assertIn('bar', d)

    def testDelitem(self):
        d = TwoWayDictionary(foo='bar')
        del d['foo']
        self.assertNotIn('foo', d)
        self.assertNotIn('bar', d)
        d = TwoWayDictionary(foo='bar')
        del d['bar']
        self.assertNotIn('bar', d)
        self.assertNotIn('foo', d)


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
        timeFastForward(1.1)
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
        timeFastForward(1.1)
        self.assertEqual(len(q), 0)
        self.assertEqual(sum(q), 0)

    def testContains(self):
        q = TimeoutQueue(1)
        q.enqueue(1)
        self.assertIn(1, q)
        self.assertIn(1, q) # For some reason, the second one might fail.
        self.assertNotIn(2, q)
        timeFastForward(1.1)
        self.assertNotIn(1, q)

    def testIter(self):
        q = TimeoutQueue(1)
        q.enqueue(1)
        it1 = iter(q)
        timeFastForward(0.5)
        q.enqueue(2)
        it2 = iter(q)
        self.assertEqual(next(it1), 1)
        self.assertEqual(next(it2), 1)
        self.assertEqual(next(it2), 2)
        with self.assertRaises(StopIteration):
            next(it2)

        timeFastForward(0.6)
        self.assertEqual(next(it1), 2)
        with self.assertRaises(StopIteration):
            next(it1)

        it3 = iter(q)
        self.assertEqual(next(it3), 2)
        with self.assertRaises(StopIteration):
            next(it3)

    def testReset(self):
        q = TimeoutQueue(10)
        q.enqueue(1)
        self.assertIn(1, q)
        q.reset()
        self.assertNotIn(1, q)

    def testClean(self):
        def iter_and_next(q):
            next(iter(q))

        def contains(q):
            42 in q

        for f in (len, repr, list, iter_and_next, contains):
            print(f)
            with self.subTest(f=f.__name__):
                q = TimeoutQueue(1)
                q.enqueue(1)
                timeFastForward(0.5)
                q.enqueue(2)

                self.assertEqual([x for (_, x) in q.queue], [1, 2])
                f(q)
                self.assertEqual([x for (_, x) in q.queue], [1, 2])

                timeFastForward(0.6)

                self.assertEqual([x for (_, x) in q.queue], [1, 2])  # not cleaned yet
                f(q)
                self.assertEqual([x for (_, x) in q.queue], [2])  # now it is

class TestCacheDict(SupyTestCase):
    def testMaxNeverExceeded(self):
        max = 10
        d = CacheDict(10)
        for i in range(max**2):
            d[i] = i
            self.assertLessEqual(len(d), max)
            self.assertIn(i, d)
            self.assertEqual(d[i], i)

class TestExpiringDict(SupyTestCase):
    def testInit(self):
        d = ExpiringDict(10)
        self.assertEqual(dict(d), {})
        d['foo'] = 'bar'
        d['baz'] = 'qux'
        self.assertEqual(dict(d), {'foo': 'bar', 'baz': 'qux'})

    def testExpire(self):
        d = ExpiringDict(10)
        self.assertEqual(dict(d), {})
        d['foo'] = 'bar'
        timeFastForward(11)
        d['baz'] = 'qux'  # Moves 'foo' to the old gen
        self.assertEqual(dict(d), {'foo': 'bar', 'baz': 'qux'})

        timeFastForward(11)
        self.assertEqual(dict(d), {'foo': 'bar', 'baz': 'qux'})

        d['quux'] = 42  # removes the old gen and moves 'baz' to the old gen
        self.assertEqual(dict(d), {'baz': 'qux', 'quux': 42})

    def testEquality(self):
        d1 = ExpiringDict(10)
        d2 = ExpiringDict(10)
        self.assertEqual(d1, d2)

        d1['foo'] = 'bar'
        self.assertNotEqual(d1, d2)

        timeFastForward(5)  # check they are equal despite the time difference

        d2['foo'] = 'bar'
        self.assertEqual(d1, d2)

        timeFastForward(7)

        d1['baz'] = 'qux'  # moves 'foo' to the old gen (12 seconds old)
        d2['baz'] = 'qux'  # does not move it (7 seconds old)
        self.assertEqual(d1, d2)


class TestTimeoutDict(SupyTestCase):
    def testInit(self):
        d = TimeoutDict(10)
        self.assertEqual(dict(d), {})
        d['foo'] = 'bar'
        d['baz'] = 'qux'
        self.assertEqual(dict(d), {'foo': 'bar', 'baz': 'qux'})

    def testExpire(self):
        d = TimeoutDict(10)
        self.assertEqual(dict(d), {})
        d['foo'] = 'bar'
        timeFastForward(11)
        d['baz'] = 'qux'
        self.assertEqual(dict(d), {'baz': 'qux'})

        timeFastForward(11)
        self.assertEqual(dict(d), {})

        d['quux'] = 42
        self.assertEqual(dict(d), {'quux': 42})

    def testEquality(self):
        d1 = TimeoutDict(10)
        d2 = TimeoutDict(10)
        self.assertEqual(d1, d2)

        d1['foo'] = 'bar'
        self.assertNotEqual(d1, d2)

        timeFastForward(5)  # check they are equal despite the time difference

        d2['foo'] = 'bar'
        self.assertEqual(d1, d2)

        timeFastForward(7)
        self.assertNotEqual(d1, d2)
        self.assertEqual(d1, {})
        self.assertEqual(d2, {'foo': 'bar'})

        timeFastForward(7)
        self.assertEqual(d1, d2)
        self.assertEqual(d1, {})
        self.assertEqual(d2, {})

        d1['baz'] = 'qux'
        d2['baz'] = 'qux'
        self.assertEqual(d1, d2)


class TestTruncatableSet(SupyTestCase):
    def testBasics(self):
        s = TruncatableSet(['foo', 'bar', 'baz', 'qux'])
        self.assertEqual(s, set(['foo', 'bar', 'baz', 'qux']))
        self.assertIn('foo', s)
        self.assertIn('bar', s)
        self.assertNotIn('quux', s)
        s.discard('baz')
        self.assertIn('foo', s)
        self.assertNotIn('baz', s)
        s.add('quux')
        self.assertIn('quux', s)

    def testTruncate(self):
        s = TruncatableSet(['foo', 'bar'])
        s.add('baz')
        s.add('qux')
        s.truncate(3)
        self.assertEqual(s, set(['bar', 'baz', 'qux']))

    def testTruncateUnion(self):
        s = TruncatableSet(['bar', 'foo'])
        s |= set(['baz', 'qux'])
        s.truncate(3)
        self.assertEqual(s, set(['foo', 'baz', 'qux']))

class UtilsPythonTest(SupyTestCase):
    def test_dict(self):
        class Foo:
            def __hasattr__(self, n):
                raise Exception(n)
            def __getattr__(self, n):
                raise Exception(n)

        def f():
            self = Foo()
            self.bar = 'baz'
            raise Exception('f')

        try:
            f()
        except:
            res = utils.python.collect_extra_debug_data()

        self.assertTrue(re.search('self.bar.*=.*baz', res), res)

    def test_slots(self):
        class Foo:
            __slots__ = ('bar',)
            def __hasattr__(self, n):
                raise Exception(n)
            def __getattr__(self, n):
                raise Exception(n)

        def f():
            self = Foo()
            self.bar = 'baz'
            raise Exception('f')

        try:
            f()
        except:
            res = utils.python.collect_extra_debug_data()

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

