###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008, James McCoy
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

from __future__ import print_function

from supybot.test import *

class MathTestCase(PluginTestCase):
    plugins = ('Math',)
    def testBase(self):
        self.assertNotRegexp('base 56 asdflkj', 'ValueError')
        self.assertResponse('base 16 2 F', '1111')
        self.assertResponse('base 2 16 1111', 'F')
        self.assertResponse('base 20 BBBB', '92631')
        self.assertResponse('base 10 20 92631', 'BBBB')
        self.assertResponse('base 2 36 10', '2')
        self.assertResponse('base 36 2 10', '100100')
        self.assertResponse('base 2 1010101', '85')
        self.assertResponse('base 2 2 11', '11')

        self.assertResponse('base 12 0', '0')
        self.assertResponse('base 36 2 0', '0')


        self.assertNotError("base 36 " +\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ")

        self.assertResponse("base 10 36 [base 36 " +\
            "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"\
            "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"\
            "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"\
            "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"\
            "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"\
            "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"\
            "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz]",

            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"\
            "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ")

        self.assertResponse('base 2 10 [base 10 2 12]', '12')
        self.assertResponse('base 16 2 [base 2 16 110101]', '110101')
        self.assertResponse('base 10 8 [base 8 76532]', '76532')
        self.assertResponse('base 10 36 [base 36 csalnwea]', 'CSALNWEA')
        self.assertResponse('base 5 4 [base 4 5 212231]', '212231')

        self.assertError('base 37 1')
        self.assertError('base 1 1')
        self.assertError('base 12 1 1')
        self.assertError('base 1 12 1')
        self.assertError('base 1.0 12 1')
        self.assertError('base A 1')

        self.assertError('base 4 4')
        self.assertError('base 10 12 A')

        self.assertRegexp('base 2 10 [base 10 2 -12]', '-12')
        self.assertRegexp('base 16 2 [base 2 16 -110101]', '-110101')

    def testCalc(self):
        self.assertResponse('calc 5*0.06', str(5*0.06))
        self.assertResponse('calc 2.0-7.0', str(2-7))
        self.assertResponse('calc e**(i*pi)+1', '0')
        if minisix.PY3:
            # Python 2 has bad handling of exponentiation of negative numbers
            self.assertResponse('calc (-1)**.5', 'i')
            self.assertRegexp('calc (-5)**.5', '2.236067977[0-9]+i')
            self.assertRegexp('calc -((-5)**.5)', '-2.236067977[0-9]+i')
        self.assertNotRegexp('calc [9, 5] + [9, 10]', 'TypeError')
        self.assertError('calc [9, 5] + [9, 10]')
        self.assertNotError('calc degrees(2)')
        self.assertNotError('calc (2 * 3) - 2*(3*4)')
        self.assertNotError('calc (3) - 2*(3*4)')
        self.assertNotError('calc (1600 * 1200) - 2*(1024*1280)')
        self.assertNotError('calc 3-2*4')
        self.assertNotError('calc (1600 * 1200)-2*(1024*1280)')
        self.assertResponse('calc factorial(20000)',
            'Error: factorial argument too large')
        self.assertResponse('calc factorial(20000) / factorial(19999)',
            'Error: factorial argument too large')

    def testCalcNoNameError(self):
        self.assertRegexp('calc foobar(x)', 'foobar is not a defined function')

    def testCalcInvalidNode(self):
        self.assertRegexp('calc {"foo": "bar"}', 'Illegal construct Dict')

    def testCalcImaginary(self):
        self.assertResponse('calc 3 + sqrt(-1)', '3+i')

    def testCalcFloorWorksWithSqrt(self):
        self.assertNotError('calc floor(sqrt(5))')

    def testCaseInsensitive(self):
        self.assertNotError('calc PI**PI')

    def testCalcMaxMin(self):
        self.assertResponse('calc max(1,2)', '2')
        self.assertResponse('calc min(1,2)', '1')

    def testCalcStrFloat(self):
        self.assertResponse('calc 3+33333333333333', '33333333333336')

    def testCalcMemoryError(self):
        self.assertRegexp('calc ' + '('*10000,
            r"(too much recursion"  # cpython < 3.10
            r"|too many nested parentheses"  # cpython >= 3.10
            r"|parenthesis is never closed"  # pypy for python < 3.10
            r"|'\(' was never closed)"  # pypy for python >= 3.10
        )

    def testICalc(self):
        self.assertResponse('icalc 1^1', '0')
        self.assertResponse('icalc 10**24', '1' + '0'*24)
        self.assertRegexp('icalc 49/6', '8.16')
        self.assertRegexp('icalc factorial(20000)',
            'Error: The answer exceeded')
        self.assertResponse('icalc factorial(20000) / factorial(19999)',
            '20000.0')

    def testRpn(self):
        self.assertResponse('rpn 5 2 +', '7')
        self.assertResponse('rpn 1 2 3 +', 'Stack: [1, 5]')
        self.assertResponse('rpn 1 dup', 'Stack: [1, 1]')
        self.assertResponse('rpn 2 3 4 + -', str(2-7))
        self.assertNotError('rpn 2 degrees')

    def testRpnSwap(self):
        self.assertResponse('rpn 1 2 swap', 'Stack: [2, 1]')

    def testRpmNoSyntaxError(self):
        self.assertNotRegexp('rpn 2 3 foobar', 'SyntaxError')

    def testConvert(self):
        self.assertResponse('convert 1 m to cm', '100')
        self.assertResponse('convert m to cm', '100')
        self.assertResponse('convert 3 metres to km', '0.003')
        self.assertResponse('convert 1 cm to km', '1e-05')
        self.assertResponse('convert 32 F to C', '0')
        self.assertResponse('convert 32 C to F', '89.6')
        self.assertResponse('convert [calc 2*pi] rad to degree', '360')
        self.assertResponse('convert amu to atomic mass unit',
                            '1')
        self.assertResponse('convert [calc 2*pi] rad to circle', '1')



        self.assertError('convert 1 meatball to bananas')
        self.assertError('convert 1 gram to meatballs')
        self.assertError('convert 1 mol to grams')
        self.assertError('convert 1 m to kpa')

    def testConvertSingularPlural(self):
        self.assertResponse('convert [calc 2*pi] rads to degrees', '360')
        self.assertResponse('convert 1 carat to grams', '0.2')
        self.assertResponse('convert 10 lbs to oz', '160')
        self.assertResponse('convert mA to amps', '0.001')

    def testConvertCaseSensitivity(self):
        self.assertError('convert MA to amps')
        self.assertError('convert M to amps')
        self.assertError('convert Radians to rev')

    def testUnits(self):
        self.assertNotError('units')
        self.assertNotError('units mass')
        self.assertNotError('units flux density')

    def testAbs(self):
        self.assertResponse('calc abs(2)', '2')
        self.assertResponse('calc abs(-2)', '2')
        self.assertResponse('calc abs(2.0)', '2')
        self.assertResponse('calc abs(-2.0)', '2')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

