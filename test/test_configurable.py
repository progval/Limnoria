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

import configurable

class DictionaryTestCase(unittest.TestCase):
    def test(self):
        t = configurable.Dictionary([('foo', bool, False, 'bar')])
        self.assertEqual(t.help('foo'), 'bar')
        self.assertEqual(t.help('f-o-o'), 'bar')
        self.assertRaises(KeyError, t.help, 'bar')
        self.assertEqual(t.get('foo'), False)
        self.assertEqual(t.get('f-o-o'), False)
        t.set('foo', True)
        self.assertEqual(t.get('foo'), True)
        t.set('foo', False, '#foo')
        self.assertEqual(t.get('foo', '#foo'), False)
        self.assertEqual(t.get('foo'), True)
        self.assertRaises(KeyError, t.set, 'bar', True)
        self.assertRaises(KeyError, t.set, 'bar', True, '#foo')
        t.set('f-o-o', False)
        self.assertEqual(t.get('foo'), False)



# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

