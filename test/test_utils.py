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

from testsupport import *
import sets

import utils

class UtilsTest(unittest.TestCase):
    def testMatchCase(self):
        f = utils.matchCase
        self.assertEqual('bar', f('foo', 'bar'))
        self.assertEqual('Bar', f('Foo', 'bar'))
        self.assertEqual('BAr', f('FOo', 'bar'))
        self.assertEqual('BAR', f('FOO', 'bar'))
        self.assertEqual('bAR', f('fOO', 'bar'))
        self.assertEqual('baR', f('foO', 'bar'))
        self.assertEqual('BaR', f('FoO', 'bar'))

    def testPluralize(self):
        f = utils.pluralize
        self.assertEqual('bike', f('bike', 1))
        self.assertEqual('bikes', f('bike', 2))
        self.assertEqual('BIKE', f('BIKE', 1))
        self.assertEqual('BIKES', f('BIKE', 2))
        self.assertEqual('match', f('match', 1))
        self.assertEqual('matches', f('match', 2))
        self.assertEqual('Patch', f('Patch', 1))
        self.assertEqual('Patches', f('Patch', 2))

    def testDepluralize(self):
        f = utils.depluralize
        self.assertEqual('bike', f('bikes'))
        self.assertEqual('Bike', f('Bikes'))
        self.assertEqual('BIKE', f('BIKES'))
        self.assertEqual('match', f('matches'))
        self.assertEqual('Match', f('Matches'))
        
    def testTimeElapsed(self):
        self.assertRaises(ValueError, utils.timeElapsed, 0, 0, seconds=False)
        then = 0
        now = 0
        for now, expected in [(0, '0 seconds'),
                              (1, '1 second'),
                              (60, '1 minute and 0 seconds'),
                              (61, '1 minute and 1 second'),
                              (62, '1 minute and 2 seconds'),
                              (122, '2 minutes and 2 seconds'),
                              (3722, '1 hour, 2 minutes, and 2 seconds'),
                              (7322, '2 hours, 2 minutes, and 2 seconds')]:
            self.assertEqual(utils.timeElapsed(now - then), expected)

    def testEachSubstring(self):
        s = 'foobar'
        L = ['f', 'fo', 'foo', 'foob', 'fooba', 'foobar']
        self.assertEqual(list(utils.eachSubstring(s)), L)

    def testDistance(self):
        self.assertEqual(utils.distance('', ''), 0)
        self.assertEqual(utils.distance('a', 'b'), 1)
        self.assertEqual(utils.distance('a', 'a'), 0)
        self.assertEqual(utils.distance('foobar', 'jemfinch'), 8)
        self.assertEqual(utils.distance('a', 'ab'), 1)
        self.assertEqual(utils.distance('foo', ''), 3)
        self.assertEqual(utils.distance('', 'foo'), 3)
        self.assertEqual(utils.distance('appel', 'nappe'), 2)
        self.assertEqual(utils.distance('nappe', 'appel'), 2)

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
            soundex = utils.soundex(name)
            self.assertEqual(soundex, key,
                             '%s was %s, not %s' % (name, soundex, key))
        self.assertRaises(ValueError, utils.soundex, '3')
        self.assertRaises(ValueError, utils.soundex, "'")
        

    def testDQRepr(self):
        L = ['foo', 'foo\'bar', 'foo"bar', '"', '\\', '', '\x00']
        for s in L:
            r = utils.dqrepr(s)
            self.assertEqual(s, eval(r), s)
            self.failUnless(r[0] == '"' and r[-1] == '"', s)

    def testPerlReToPythonRe(self):
        r = utils.perlReToPythonRe('m/foo/')
        self.failUnless(r.search('foo'))
        r = utils.perlReToPythonRe('/foo/')
        self.failUnless(r.search('foo'))
        r = utils.perlReToPythonRe('m/\\//')
        self.failUnless(r.search('/'))
        r = utils.perlReToPythonRe('m/cat/i')
        self.failUnless(r.search('CAT'))
        self.assertRaises(ValueError, utils.perlReToPythonRe, 'm/?/')

    def testPerlReToReplacer(self):
        f = utils.perlReToReplacer('s/foo/bar/')
        self.assertEqual(f('foobarbaz'), 'barbarbaz')
        f = utils.perlReToReplacer('s/fool/bar/')
        self.assertEqual(f('foobarbaz'), 'foobarbaz')
        f = utils.perlReToReplacer('s/foo//')
        self.assertEqual(f('foobarbaz'), 'barbaz')
        f = utils.perlReToReplacer('s/ba//')
        self.assertEqual(f('foobarbaz'), 'foorbaz')
        f = utils.perlReToReplacer('s/ba//g')
        self.assertEqual(f('foobarbaz'), 'foorz')
        f = utils.perlReToReplacer('s/ba\\///g')
        self.assertEqual(f('fooba/rba/z'), 'foorz')
        f = utils.perlReToReplacer('s/cat/dog/i')
        self.assertEqual(f('CATFISH'), 'dogFISH')
        f = utils.perlReToReplacer('s/foo/foo\/bar/')
        self.assertEqual(f('foo'), 'foo/bar')
        f = utils.perlReToReplacer('s/^/foo/')
        self.assertEqual(f('bar'), 'foobar')

    def testPerlReToReplacerBug850931(self):
        f = utils.perlReToReplacer('s/\b(\w+)\b/\1./g')
        self.assertEqual(f('foo bar baz'), 'foo. bar. baz.')

    def testFindBinaryInPath(self):
        if os.name == 'posix':
            self.assertEqual(None, utils.findBinaryInPath('asdfhjklasdfhjkl'))
            self.failUnless(utils.findBinaryInPath('sh').endswith('/bin/sh'))

    def testCommaAndify(self):
        L = ['foo']
        original = L[:]
        self.assertEqual(utils.commaAndify(L), 'foo')
        self.assertEqual(utils.commaAndify(L, 'or'), 'foo')
        self.assertEqual(L, original)
        L.append('bar')
        original = L[:]
        self.assertEqual(utils.commaAndify(L), 'foo and bar')
        self.assertEqual(utils.commaAndify(L, 'or'), 'foo or bar')
        self.assertEqual(L, original)
        L.append('baz')
        original = L[:]
        self.assertEqual(utils.commaAndify(L), 'foo, bar, and baz')
        self.assertEqual(utils.commaAndify(L, 'or'), 'foo, bar, or baz')
        self.assertEqual(L, original)
        self.failUnless(utils.commaAndify(sets.Set(L)))

    def testCommaAndifyRaisesTypeError(self):
        L = [(2,)]
        self.assertRaises(TypeError, utils.commaAndify, L)
        L.append((3,))
        self.assertRaises(TypeError, utils.commaAndify, L)

    def testUnCommaThe(self):
        self.assertEqual(utils.unCommaThe('foo bar'), 'foo bar')
        self.assertEqual(utils.unCommaThe('foo bar, the'), 'the foo bar')
        self.assertEqual(utils.unCommaThe('foo bar, The'), 'The foo bar')
        self.assertEqual(utils.unCommaThe('foo bar,the'), 'the foo bar')

    def testNormalizeWhitespace(self):
        self.assertEqual(utils.normalizeWhitespace('foo   bar'), 'foo bar')
        self.assertEqual(utils.normalizeWhitespace('foo\nbar'), 'foo bar')
        self.assertEqual(utils.normalizeWhitespace('foo\tbar'), 'foo bar')

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
        self.assertEqual(utils.sorted(L), ['a', 'b', 'c'])
        self.assertEqual(L, ['a', 'c', 'b'])
        def mycmp(x, y):
            return -cmp(x, y)
        self.assertEqual(utils.sorted(L, mycmp), ['c', 'b', 'a'])
        
    def testNItems(self):
        self.assertEqual(utils.nItems('tool', 1, 'crazy'), '1 crazy tool')
        self.assertEqual(utils.nItems('tool', 1), '1 tool')
        self.assertEqual(utils.nItems('tool', 2, 'crazy'), '2 crazy tools')
        self.assertEqual(utils.nItems('tool', 2), '2 tools')

    def testItersplit(self):
        from utils import itersplit
        L = [1, 2, 3] * 3
        s = 'foo bar baz'
        self.assertEqual(list(itersplit(lambda x: x == 3, L)),
                         [[1, 2], [1, 2], [1, 2]])
        self.assertEqual(list(itersplit(lambda x: x == 3, L, yieldEmpty=True)),
                         [[1, 2], [1, 2], [1, 2], []])
        self.assertEqual(list(itersplit(lambda x: x, [])), [])
        self.assertEqual(list(itersplit(lambda c: c.isspace(), s)),
                         map(list, s.split()))
        self.assertEqual(list(itersplit('for'.__eq__, ['foo', 'for', 'bar'])),
                         [['foo'], ['bar']])
        self.assertEqual(list(itersplit('for'.__eq__,
                                        ['foo','for','bar','for', 'baz'], 1)),
                         [['foo'], ['bar', 'for', 'baz']])

    def testIterableMap(self):
        class alist(utils.IterableMap):
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
            return list(utils.flatten(seq))
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

    def testEllipsisify(self):
        f = utils.ellipsisify
        self.assertEqual(f('x'*30, 30), 'x'*30)
        self.failUnless(len(f('x'*35, 30)) <= 30)
        self.failUnless(f(' '.join(['xxxx']*10), 30)[:-3].endswith('xxxx'))

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

    def testLines(self):
        L = ['foo', 'bar', '#baz', '  ', 'biff']
        self.assertEqual(list(utils.nonEmptyLines(L)),
                         ['foo', 'bar', '#baz', 'biff'])
        self.assertEqual(list(utils.nonCommentLines(L)),
                         ['foo', 'bar', '  ', 'biff'])
        self.assertEqual(list(utils.nonCommentNonEmptyLines(L)),
                         ['foo', 'bar', 'biff'])

    def testIsIP(self):
        self.failIf(utils.isIP('a.b.c'))
        self.failIf(utils.isIP('256.0.0.0'))
        self.failUnless(utils.isIP('127.1'))
        self.failUnless(utils.isIP('0.0.0.0'))
        self.failUnless(utils.isIP('100.100.100.100'))
        # This test is too flaky to bother with.
        # self.failUnless(utils.isIP('255.255.255.255'))

    def testIsIPV6(self):
        f = utils.isIPV6
        self.failUnless(f('2001::'))
        self.failUnless(f('2001:888:0:1::666'))


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

