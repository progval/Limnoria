###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

from supybot.commands import *
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.callbacks as callbacks


class CommandsTestCase(SupyTestCase):
    def assertState(self, spec, given, expected, target='test', **kwargs):
        msg = ircmsgs.privmsg(target, 'foo')
        realIrc = getTestIrc()
        realIrc.nick = 'test'
        realIrc.state.supported['chantypes'] = '#'
        irc = callbacks.SimpleProxy(realIrc, msg)
        myspec = Spec(spec, **kwargs)
        state = myspec(irc, msg, given)
        self.assertEqual(state.args, expected,
                         'Expected %r, got %r' % (expected, state.args))

    def testEmptySpec(self):
        self.assertState([], [], [])

    def testSpecInt(self):
        self.assertState(['int'], ['1'], [1])
        self.assertState(['int', 'int', 'int'], ['1', '2', '3'], [1, 2, 3])

    def testRestHandling(self):
        self.assertState([rest(None)], ['foo', 'bar', 'baz'], ['foo bar baz'])

    def testOptional(self):
        spec = [optional('int', 999), None]
        self.assertState(spec, ['12', 'foo'], [12, 'foo'])
        self.assertState(spec, ['foo'], [999, 'foo'])

    def testAdditional(self):
        spec = [additional('int', 999)]
        self.assertState(spec, ['12'], [12])
        self.assertState(spec, [], [999])
        self.assertRaises(callbacks.Error,
                          self.assertState, spec, ['foo'], ['asdf'])

    def testReverse(self):
        spec = [reverse('positiveInt'), 'float', 'text']
        self.assertState(spec, ['-1.0', 'foo', '1'], [1, -1.0, 'foo'])

    def testGetopts(self):
        spec = ['int', getopts({'foo': None, 'bar': 'int'}), 'int']
        self.assertState(spec,
                         ['12', '--foo', 'baz', '--bar', '13', '15'],
                         [12, [('foo', 'baz'), ('bar', 13)], 15])

    def testAny(self):
        self.assertState([any('int')], ['1', '2', '3'], [[1, 2, 3]])
        self.assertState([None, any('int')], ['1', '2', '3'], ['1', [2, 3]])
        self.assertState([any('int')], [], [[]])

    def testMany(self):
        spec = [many('int')]
        self.assertState(spec, ['1', '2', '3'], [[1, 2, 3]])
        self.assertRaises(callbacks.Error,
                          self.assertState, spec, [], ['asdf'])
    def testChannelRespectsNetwork(self):
        spec = ['channel', 'text']
        self.assertState(spec, ['#foo', '+s'], ['#foo', '+s'])
        self.assertState(spec, ['+s'], ['#foo', '+s'], target='#foo')

    def testGlob(self):
        spec = ['glob']
        self.assertState(spec, ['foo'], ['*foo*'])
        self.assertState(spec, ['?foo'], ['?foo'])
        self.assertState(spec, ['foo*'], ['foo*'])

    def testGetId(self):
        spec = ['id']
        self.assertState(spec, ['#12'], [12])

    def testCommaList(self):
        spec = [commalist('int')]
        self.assertState(spec, ['12'], [[12]])
        self.assertState(spec, ['12,', '10'], [[12, 10]])
        self.assertState(spec, ['12,11,10,', '9'], [[12, 11, 10, 9]])
        spec.append('int')
        self.assertState(spec, ['12,11,10', '9'], [[12, 11, 10], 9])
        
        

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

