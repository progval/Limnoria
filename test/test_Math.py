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

class MathTestCase(PluginTestCase, PluginDocumentation):
    plugins = ('Math',)
    def testBase(self):
        self.assertNotRegexp('base 56 asdflkj', 'ValueError')
        
    def testCalc(self):
        self.assertResponse('calc 5*0.06', str(5*0.06))
        self.assertResponse('calc 2.0-7.0', str(2-7))
        self.assertResponse('calc (-1)**.5', 'i')
        self.assertResponse('calc e**(i*pi)+1', '0')
        self.assertResponse('calc (-5)**.5', '2.2360679775i')
        self.assertResponse('calc -((-5)**.5)', '-2.2360679775i')
        self.assertNotRegexp('calc [9, 5] + [9, 10]', 'TypeError')
        self.assertError('calc [9, 5] + [9, 10]')
        self.assertNotError('calc degrees(2)')

    def testICalc(self):
        self.assertResponse('icalc 1^1', '0')
        self.assertResponse('icalc 10**24', '1' + '0'*24)

    def testCalcNoNameError(self):
        self.assertNotRegexp('calc foobar(x)', 'NameError')

    def testCalcImaginary(self):
        self.assertResponse('calc 3 + sqrt(-1)', '3+i')

    def testCalcFloorWorksWithSqrt(self):
        self.assertNotError('calc floor(sqrt(5))')
        
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
        self.assertResponse('convert 1 m to cm', '100 cm')
        self.assertResponse('convert m to cm', '100 cm')
        self.assertResponse('convert 3 metres to km', '0.003 km')
        self.assertResponse('convert 32 F to C', '0 C')
        self.assertResponse('convert 32 C to F', '89.6 F')
        self.assertResponse('convert [calc 2*pi] rad to degree', '360 degree')
        self.assertResponse('convert amu to atomic mass unit', 
                            '1 atomic mass unit')
        self.assertResponse('convert [calc 2*pi] rad to circle', '1 circle')



        self.assertError('convert 1 meatball to bananas')
        self.assertError('convert 1 gram to meatballs')
        self.assertError('convert 1 mol to grams')
        self.assertError('convert 1 m to kpa')
    
    def testConvertSingularPlural(self):
        self.assertResponse('convert [calc 2*pi] rads to degrees',
                            '360 degrees')
        self.assertResponse('convert 1 carat to grams',
                            '0.2 grams')
        self.assertResponse('convert 10 lbs to oz', '160 oz')
        self.assertResponse('convert mA to amps', '0.001 amps')

    def testConvertCaseSensitivity(self):
        self.assertError('convert MA to amps')
        self.assertError('convert M to amps')
        self.assertError('convert Radians to rev')

    def testUnits(self):
        self.assertNotError('units')
        self.assertNotError('units mass')
        self.assertNotError('units flux density')


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

