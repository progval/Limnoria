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

import plugins

class ToggleDictionaryTestCase(unittest.TestCase):
    def test(self):
        t = plugins.ToggleDictionary({'foo': True})
        self.assertEqual(t.get('foo'), True)
        self.assertEqual(t.get('foo', '#baz'), True)
        t.toggle('foo', value=False, channel='#baz')
        self.assertEqual(t.get('foo', '#baz'), False)
        t.toggle('foo', channel='#baz')
        self.assertEqual(t.get('foo', '#baz'), True)
        t.toggle('foo', channel='#baz')
        self.assertEqual(t.get('foo', '#baz'), False)
        #self.assertRaises(TypeError, t.toggle, 'foo', value='lak')

    def test__init__(self):
        self.assertRaises(TypeError, plugins.ToggleDictionary.__init__)
        self.assertRaises(ValueError, plugins.ToggleDictionary, {})

    def testToggle(self):
        t = plugins.ToggleDictionary({'foo': True})
        self.assertRaises(KeyError, t.toggle, 'bar')
        self.assertRaises(KeyError, t.toggle, 'bar', value=False)

    def testToString(self):
        t = plugins.ToggleDictionary({'foo': True, 'bar': False})
        self.assertEqual(t.toString(), '(bar: Off; foo: On)')
        t.toggle('foo', channel='#foo')
        self.assertEqual(t.toString(), '(bar: Off; foo: On)')
        self.assertEqual(t.toString(channel='#foo'),
                        '(bar: Off; foo: Off)')
        t.toggle('bar', value=True)
        self.assertEqual(t.toString(), '(bar: On; foo: On)')
        self.assertEqual(t.toString(channel='#foo'),
                        '(bar: Off; foo: Off)')
        
