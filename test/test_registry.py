#!/usr/bin/env python

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

from testsupport import *

import re

import supybot.conf as conf
import supybot.registry as registry

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


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
