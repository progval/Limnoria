###
# Copyright (c) 2014, Artur Krysiak
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

import sys
import unittest
from supybot import questions
from supybot.test import SupyTestCase

if sys.version_info >= (2, 7, 0):
    skipif = unittest.skipIf
else:
    skipif = lambda x, y: lambda z:None

try:
    from unittest import mock  # Python 3.3+
except ImportError:
    try:
        import mock  # Everything else, an external 'mock' library
    except ImportError:
        mock = None

# so complicated construction because I want to
# gain the string 'y' instead of the character 'y'
# the reason of usage this construction is to prove
# that comparing strings by 'is' is wrong
# better solution is usage of '==' operator ;)
_yes_answer = ''.join(['', 'y'])

@skipif(mock is None, 'python-mock is not installed.')
class TestYn(SupyTestCase):
    def test_default_yes_selected(self):
        questions.expect = mock.Mock(return_value=_yes_answer)

        answer = questions.yn('up', default='y')

        self.assertTrue(answer)

    def test_default_no_selected(self):
        questions.expect = mock.Mock(return_value='n')

        answer = questions.yn('up', default='n')

        self.assertFalse(answer)

    def test_yes_selected_without_defaults(self):
        questions.expect = mock.Mock(return_value=_yes_answer)

        answer = questions.yn('up')

        self.assertTrue(answer)

    def test_no_selected_without_defaults(self):
        questions.expect = mock.Mock(return_value='n')

        answer = questions.yn('up')

        self.assertFalse(answer)

    def test_no_selected_with_default_yes(self):
        questions.expect = mock.Mock(return_value='n')

        answer = questions.yn('up', default='y')

        self.assertFalse(answer)

    def test_yes_selected_with_default_yes(self):
        questions.expect = mock.Mock(return_value=_yes_answer)

        answer = questions.yn('up', default='y')

        self.assertTrue(answer)

    def test_yes_selected_with_default_no(self):
        questions.expect = mock.Mock(return_value=_yes_answer)

        answer = questions.yn('up', default='n')

        self.assertTrue(answer)

    def test_no_selected_with_default_no(self):
        questions.expect = mock.Mock(return_value='n')

        answer = questions.yn('up', default='n')

        self.assertFalse(answer)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
