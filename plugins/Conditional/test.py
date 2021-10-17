###
# Copyright (c) 2010, Daniel Folkinshteyn
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

class ConditionalTestCase(PluginTestCase):
    plugins = ('Conditional','Utilities',)

    def testCif(self):
        self.assertError('cif stuff')
        self.assertRegexp('cif [ceq bla bla] "echo moo" "echo foo"', 'moo')
        self.assertRegexp('cif [ceq bla bar] "echo moo" "echo foo"', 'foo')
        self.assertRegexp('cif [cand [ceq bla bla] [ne soo boo]] "echo moo" "echo foo"', 'moo')
        self.assertRegexp('cif [ceq [echo $nick] "test"] "echo yay" "echo nay"', 'yay')
        self.assertRegexp('cif 0 "echo nay" "echo yay"', 'yay')
        self.assertRegexp('cif 1 "echo yay" "echo nay"', 'yay')
        self.assertRegexp('cif 4 "echo yay" "echo nay"', 'yay')
        self.assertRegexp('cif -1 "echo yay" "echo nay"', 'yay')
        
    def testCand(self):
        self.assertRegexp('cand true true', 'true')
        self.assertRegexp('cand false true', 'false')
        self.assertRegexp('cand true false', 'false')
        self.assertRegexp('cand false false', 'false')
        self.assertRegexp('cand true true true', 'true')
    
    def testCor(self):
        self.assertRegexp('cor true true', 'true')
        self.assertRegexp('cor false true', 'true')
        self.assertRegexp('cor true false', 'true')
        self.assertRegexp('cor false false', 'false')
        self.assertRegexp('cor true true true', 'true')
    
    def testCxor(self):
        self.assertRegexp('cxor true true', 'false')
        self.assertRegexp('cxor false true', 'true')
        self.assertRegexp('cxor true false', 'true')
        self.assertRegexp('cxor false false', 'false')
        self.assertRegexp('cxor true true true', 'false')
    
    def testCeq(self):
        self.assertRegexp('ceq bla bla', 'true')
        self.assertRegexp('ceq bla moo', 'false')
        self.assertError('ceq bla bla bla')
    
    def testNe(self):
        self.assertRegexp('ne bla bla', 'false')
        self.assertRegexp('ne bla moo', 'true')
        self.assertError('ne bla bla bla')
    
    def testGt(self):
        self.assertRegexp('gt bla bla', 'false')
        self.assertRegexp('gt bla moo', 'false')
        self.assertRegexp('gt moo bla', 'true')
        self.assertError('gt bla bla bla')
        
    def testGe(self):
        self.assertRegexp('ge bla bla', 'true')
        self.assertRegexp('ge bla moo', 'false')
        self.assertRegexp('ge moo bla', 'true')
        self.assertError('ge bla bla bla')
        
    def testLt(self):
        self.assertRegexp('lt bla bla', 'false')
        self.assertRegexp('lt bla moo', 'true')
        self.assertRegexp('lt moo bla', 'false')
        self.assertError('lt bla bla bla')
        
    def testLe(self):
        self.assertRegexp('le bla bla', 'true')
        self.assertRegexp('le bla moo', 'true')
        self.assertRegexp('le moo bla', 'false')
        self.assertError('le bla bla bla')
    
    def testMatch(self):
        self.assertRegexp('match bla mooblafoo', 'true')
        self.assertRegexp('match bla mooblfoo', 'false')
        self.assertRegexp('match Bla moobLafoo', 'false')
        self.assertRegexp('match --case-insensitive Bla moobLafoo', 'true')
        self.assertError('match bla bla stuff')
    
    def testNceq(self):
        self.assertRegexp('nceq 10.0 10', 'true')
        self.assertRegexp('nceq 4 5', 'false')
        self.assertError('nceq 1 2 3')
        self.assertError('nceq bla 1')
    
    def testNne(self):
        self.assertRegexp('nne 1 1', 'false')
        self.assertRegexp('nne 2.2 3', 'true')
        self.assertError('nne 1 2 3')
        self.assertError('nne bla 3')
    
    def testNgt(self):
        self.assertRegexp('ngt 3 3', 'false')
        self.assertRegexp('ngt 2 3', 'false')
        self.assertRegexp('ngt 4 3', 'true')
        self.assertError('ngt 1 2 3')
        self.assertError('ngt 3 bla')
        
    def testNge(self):
        self.assertRegexp('nge 3 3', 'true')
        self.assertRegexp('nge 3 4', 'false')
        self.assertRegexp('nge 5 4.3', 'true')
        self.assertError('nge 3 4.5 4')
        self.assertError('nge 45 bla')
        
    def testNlt(self):
        self.assertRegexp('nlt 3 3', 'false')
        self.assertRegexp('nlt 3 4.5', 'true')
        self.assertRegexp('nlt 5 3', 'false')
        self.assertError('nlt 2 3 4')
        self.assertError('nlt bla bla')
        
    def testNle(self):
        self.assertRegexp('nle 2 2', 'true')
        self.assertRegexp('nle 2 3.5', 'true')
        self.assertRegexp('nle 4 3', 'false')
        self.assertError('nle 3 4 5')
        self.assertError('nle 1 bla')

    def testIferror(self):
        self.assertResponse('cerror "echo hi"', 'false')
        self.assertResponse('cerror "foobarbaz"', 'true')
        self.assertResponse('cerror "help foobarbaz"', 'true')

        
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
