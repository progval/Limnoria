###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

import time
import supybot.utils as utils

class GenTest(SupyTestCase):
    def testInsensitivePreservingDict(self):
        ipd = utils.InsensitivePreservingDict
        d = ipd(dict(Foo=10))
        self.failUnless(d['foo'] == 10)
        self.assertEqual(d.keys(), ['Foo'])
        self.assertEqual(d.get('foo'), 10)
        self.assertEqual(d.get('Foo'), 10)

    def testFindBinaryInPath(self):
        if os.name == 'posix':
            self.assertEqual(None, utils.findBinaryInPath('asdfhjklasdfhjkl'))
            self.failUnless(utils.findBinaryInPath('sh').endswith('/bin/sh'))

    def testExnToString(self):
        try:
            raise KeyError, 1
        except Exception, e:
            self.assertEqual(utils.exnToString(e), 'KeyError: 1')
        try:
            raise EOFError
        except Exception, e:
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
            self.failUnless(r[0] == '"' and r[-1] == '"', s)

    def testPerlReToPythonRe(self):
        f = utils.str.perlReToPythonRe
        r = f('m/foo/')
        self.failUnless(r.search('foo'))
        r = f('/foo/')
        self.failUnless(r.search('foo'))
        r = f('m/\\//')
        self.failUnless(r.search('/'))
        r = f('m/cat/i')
        self.failUnless(r.search('CAT'))
        self.assertRaises(ValueError, f, 'm/?/')

    def testP2PReDifferentSeparator(self):
        r = utils.str.perlReToPythonRe('m!foo!')
        self.failUnless(r.search('foo'))

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
        f = PRTR('s/cat/dog/i')
        self.assertEqual(f('CATFISH'), 'dogFISH')
        f = PRTR('s/foo/foo\/bar/')
        self.assertEqual(f('foo'), 'foo/bar')
        f = PRTR('s/^/foo/')
        self.assertEqual(f('bar'), 'foobar')

    def testPReToReplacerDifferentSeparator(self):
        f = utils.str.perlReToReplacer('s#foo#bar#')
        self.assertEqual(f('foobarbaz'), 'barbarbaz')

    def testPerlReToReplacerBug850931(self):
        f = utils.str.perlReToReplacer('s/\b(\w+)\b/\1./g')
        self.assertEqual(f('foo bar baz'), 'foo. bar. baz.')

    def testPerlVariableSubstitute(self):
        f = utils.str.perlVariableSubstitute
        vars = {'foo': 'bar', 'b a z': 'baz', 'b': 'c', 'i': 100,
                'f': lambda: 'called'}
        self.assertEqual(f(vars, '$foo'), 'bar')
        self.assertEqual(f(vars, '${foo}'), 'bar')
        self.assertEqual(f(vars, '$b'), 'c')
        self.assertEqual(f(vars, '${b}'), 'c')
        self.assertEqual(f(vars, '$i'), '100')
        self.assertEqual(f(vars, '${i}'), '100')
        self.assertEqual(f(vars, '$f'), 'called')
        self.assertEqual(f(vars, '${f}'), 'called')
        self.assertEqual(f(vars, '${b a z}'), 'baz')
        self.assertEqual(f(vars, '$b:$i'), 'c:100')
        
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
        self.failUnless(f(set(L)))

    def testCommaAndifyRaisesTypeError(self):
        L = [(2,)]
        self.assertRaises(TypeError, utils.str.commaAndify, L)
        L.append((3,))
        self.assertRaises(TypeError, utils.str.commaAndify, L)

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

    def testNItems(self):
        nItems = utils.str.nItems
        self.assertEqual(nItems(0, 'tool'), '0 tools')
        self.assertEqual(nItems(1, 'tool', 'crazy'), '1 crazy tool')
        self.assertEqual(nItems(1, 'tool'), '1 tool')
        self.assertEqual(nItems(2, 'tool', 'crazy'), '2 crazy tools')
        self.assertEqual(nItems(2, 'tool'), '2 tools')

    def testEllipsisify(self):
        f = utils.str.ellipsisify
        self.assertEqual(f('x'*30, 30), 'x'*30)
        self.failUnless(len(f('x'*35, 30)) <= 30)
        self.failUnless(f(' '.join(['xxxx']*10), 30)[:-3].endswith('xxxx'))


class IterTest(SupyTestCase):
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
                         map(list, s.split()))
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
        self.assertEqual(lflatten(range(10)), range(10))
        twoRanges = range(10)*2
        twoRanges.sort()
        self.assertEqual(lflatten(zip(range(10), range(10))), twoRanges)
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


class NetTest(SupyTestCase):
    def testEmailRe(self):
        emailRe = utils.net.emailRe
        self.failUnless(emailRe.match('jemfinch@supybot.com'))

    def testIsIP(self):
        isIP = utils.net.isIP
        self.failIf(isIP('a.b.c'))
        self.failIf(isIP('256.0.0.0'))
        self.failUnless(isIP('127.1'))
        self.failUnless(isIP('0.0.0.0'))
        self.failUnless(isIP('100.100.100.100'))
        # This test is too flaky to bother with.
        # self.failUnless(utils.isIP('255.255.255.255'))

    def testIsIPV6(self):
        f = utils.net.isIPV6
        self.failUnless(f('2001::'))
        self.failUnless(f('2001:888:0:1::666'))

class WebTest(SupyTestCase):
    def testGetDomain(self):
        url = 'http://slashdot.org/foo/bar.exe'
        self.assertEqual(utils.web.getDomain(url), 'slashdot.org')

    if network:
        def testGetUrlWithSize(self):
            url = 'http://slashdot.org/'
            self.failUnless(len(utils.web.getUrl(url, 1024)) == 1024)

class FormatTestCase(SupyTestCase):
    def testNormal(self):
        format = utils.str.format
        self.assertEqual(format('I have %n of fruit: %L.', (3, 'kind'),
                                ['apples', 'oranges', 'watermelon']),
                         'I have 3 kinds of fruit: '
                         'apples, oranges, and watermelon.')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

