###
# Copyright (c) 2004, Jeremiah Fincher
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

import re

import supybot.conf as conf
import supybot.registry as registry

join = registry.join
split = registry.split
escape = registry.escape
unescape = registry.unescape
class FunctionsTestCase(SupyTestCase):
    def testEscape(self):
        self.assertEqual('foo', escape('foo'))
        self.assertEqual('foo\\.bar', escape('foo.bar'))
        self.assertEqual('foo\\:bar', escape('foo:bar'))

    def testUnescape(self):
        self.assertEqual('foo', unescape('foo'))
        self.assertEqual('foo.bar', unescape('foo\\.bar'))
        self.assertEqual('foo:bar', unescape('foo\\:bar'))

    def testEscapeAndUnescapeAreInverses(self):
        for s in ['foo', 'foo.bar']:
            self.assertEqual(s, unescape(escape(s)))
            self.assertEqual(escape(s), escape(unescape(escape(s))))

    def testSplit(self):
        self.assertEqual(['foo'], split('foo'))
        self.assertEqual(['foo', 'bar'], split('foo.bar'))
        self.assertEqual(['foo.bar'], split('foo\\.bar'))

    def testJoin(self):
        self.assertEqual('foo', join(['foo']))
        self.assertEqual('foo.bar', join(['foo', 'bar']))
        self.assertEqual('foo\\.bar', join(['foo.bar']))

    def testJoinAndSplitAreInverses(self):
        for s in ['foo', 'foo.bar', 'foo\\.bar']:
            self.assertEqual(s, join(split(s)))
            self.assertEqual(split(s), split(join(split(s))))



class ValuesTestCase(SupyTestCase):
    def testBoolean(self):
        v = registry.Boolean(True, """Help""")
        self.failUnless(v())
        v.setValue(False)
        self.failIf(v())
        v.set('True')
        self.failUnless(v())
        v.set('False')
        self.failIf(v())
        v.set('On')
        self.failUnless(v())
        v.set('Off')
        self.failIf(v())
        v.set('enable')
        self.failUnless(v())
        v.set('disable')
        self.failIf(v())
        v.set('toggle')
        self.failUnless(v())
        v.set('toggle')
        self.failIf(v())

    def testInteger(self):
        v = registry.Integer(1, 'help')
        self.assertEqual(v(), 1)
        v.setValue(10)
        self.assertEqual(v(), 10)
        v.set('100')
        self.assertEqual(v(), 100)
        v.set('-1000')
        self.assertEqual(v(), -1000)

    def testPositiveInteger(self):
        v = registry.PositiveInteger(1, 'help')
        self.assertEqual(v(), 1)
        self.assertRaises(registry.InvalidRegistryValue, v.setValue, -1)
        self.assertRaises(registry.InvalidRegistryValue, v.set, '-1')

    def testFloat(self):
        v = registry.Float(1.0, 'help')
        self.assertEqual(v(), 1.0)
        v.setValue(10)
        self.assertEqual(v(), 10.0)
        v.set('0')
        self.assertEqual(v(), 0.0)

    def testString(self):
        v = registry.String('foo', 'help')
        self.assertEqual(v(), 'foo')
        v.setValue('bar')
        self.assertEqual(v(), 'bar')
        v.set('"biff"')
        self.assertEqual(v(), 'biff')
        v.set("'buff'")
        self.assertEqual(v(), 'buff')
        v.set('"xyzzy')
        self.assertEqual(v(), '"xyzzy')

    def testJson(self):
        data = {'foo': ['bar', 'baz', 5], 'qux': None}
        v = registry.Json('foo', 'help')
        self.assertEqual(v(), 'foo')
        v.setValue(data)
        self.assertEqual(v(), data)
        self.assertIsNot(v(), data)

        with v.editable() as dict_:
            dict_['supy'] = 'bot'
            del dict_['qux']
            self.assertNotIn('supy', v())
            self.assertIn('qux', v())
        self.assertIn('supy', v())
        self.assertEqual(v()['supy'], 'bot')
        self.assertIsNot(v()['supy'], 'bot')
        self.assertNotIn('qux', v())

    def testNormalizedString(self):
        v = registry.NormalizedString("""foo
        bar           baz
        biff
        """, 'help')
        self.assertEqual(v(), 'foo bar baz biff')
        v.setValue('foo          bar             baz')
        self.assertEqual(v(), 'foo bar baz')
        v.set('"foo         bar  baz"')
        self.assertEqual(v(), 'foo bar baz')

    def testStringSurroundedBySpaces(self):
        v = registry.StringSurroundedBySpaces('foo', 'help')
        self.assertEqual(v(), ' foo ')
        v.setValue('||')
        self.assertEqual(v(), ' || ')
        v.set('&&')
        self.assertEqual(v(), ' && ')

    def testCommaSeparatedListOfStrings(self):
        v = registry.CommaSeparatedListOfStrings(['foo', 'bar'], 'help')
        self.assertEqual(v(), ['foo', 'bar'])
        v.setValue(['foo', 'bar', 'baz'])
        self.assertEqual(v(), ['foo', 'bar', 'baz'])
        v.set('foo,bar')
        self.assertEqual(v(), ['foo', 'bar'])

    def testRegexp(self):
        v = registry.Regexp(None, 'help')
        self.assertEqual(v(), None)
        v.set('m/foo/')
        self.failUnless(v().match('foo'))
        v.set('')
        self.assertEqual(v(), None)
        self.assertRaises(registry.InvalidRegistryValue,
                          v.setValue, re.compile(r'foo'))

    def testBackslashes(self):
        conf.supybot.reply.whenAddressedBy.chars.set('\\')
        filename = conf.supybot.directories.conf.dirize('backslashes.conf')
        registry.close(conf.supybot, filename)
        registry.open_registry(filename)
        self.assertEqual(conf.supybot.reply.whenAddressedBy.chars(), '\\')

    def testWith(self):
        v = registry.String('foo', 'help')
        self.assertEqual(v(), 'foo')
        with v.context('bar'):
            self.assertEqual(v(), 'bar')
        self.assertEqual(v(), 'foo')

class SecurityTestCase(SupyTestCase):
    def testPrivate(self):
        v = registry.String('foo', 'help')
        self.assertFalse(v._private)
        v = registry.String('foo', 'help', private=True)
        self.assertTrue(v._private)

        g = registry.Group('foo')
        v = registry.String('foo', 'help')
        g.register('val', v)
        self.assertFalse(g._private)
        self.assertFalse(g.val._private)

        g = registry.Group('foo', private=True)
        v = registry.String('foo', 'help')
        g.register('val', v)
        self.assertTrue(g._private)
        self.assertTrue(g.val._private)

        g = registry.Group('foo')
        v = registry.String('foo', 'help', private=True)
        g.register('val', v)
        self.assertFalse(g._private)
        self.assertTrue(g.val._private)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
