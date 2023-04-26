###
# Copyright (c) 2008, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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
from supybot import log
import supybot.utils.minisix as minisix

class FirewallTestCase(SupyTestCase):
    def setUp(self):
        log.testing = False

    def tearDown(self):
        log.testing = True

    # Python 3's syntax for metaclasses is incompatible with Python 3 so
    # using Python 3's syntax directly will raise a SyntaxError on Python 2.
    exec("""
class C(%s
    __firewalled__ = {'foo': None}
    class MyException(Exception):
        pass
    def foo(self):
        raise self.MyException()""" %
        ('metaclass=log.MetaFirewall):\n' if minisix.PY3 else
            'object):\n    __metaclass__ = log.MetaFirewall'))

    def testCFooDoesNotRaise(self):
        c = self.C()
        self.assertEqual(c.foo(), None)

    class D(C):
        def foo(self):
            raise self.MyException()

    def testDFooDoesNotRaise(self):
        d = self.D()
        self.assertEqual(d.foo(), None)

    class E(C):
        __firewalled__ = {'bar': None}
        def foo(self):
            raise self.MyException()
        def bar(self):
            raise self.MyException()

    def testEFooDoesNotRaise(self):
        e = self.E()
        self.assertEqual(e.foo(), None)

    def testEBarDoesNotRaise(self):
        e = self.E()
        self.assertEqual(e.bar(), None)

    class F(C):
        __firewalled__ = {'bar': lambda self: 2}
        def bar(self):
            raise self.MyException()

    def testFBarReturns2(self):
        f = self.F()
        self.assertEqual(f.bar(), 2)



# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

