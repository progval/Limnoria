###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2015, James McCoy
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
import getopt

from supybot.test import *

from supybot.commands import *
import supybot.conf as conf
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.utils.minisix as minisix
import supybot.callbacks as callbacks


class CommandsTestCase(SupyTestCase):
    def assertState(self, spec, given, expected, target='test', **kwargs):
        msg = ircmsgs.privmsg(target, 'foo')
        realIrc = getTestIrc()
        realIrc.nick = 'test'
        realIrc.state.supported['chantypes'] = '#'
        realIrc._tagMsg(msg)
        irc = callbacks.SimpleProxy(realIrc, msg)
        myspec = Spec(spec, **kwargs)
        state = myspec(irc, msg, given)
        self.assertEqual(state.args, expected,
                         'Expected %r, got %r' % (expected, state.args))

    def assertError(self, spec, given):
        self.assertRaises(callbacks.Error,
                          self.assertState, spec, given, given)

    def assertStateErrored(self, spec, given, target='test', errored=True,
                           **kwargs):
        msg = ircmsgs.privmsg(target, 'foo')
        realIrc = getTestIrc()
        realIrc.nick = 'test'
        realIrc.state.supported['chantypes'] = '#'
        irc = callbacks.SimpleProxy(realIrc, msg)
        myspec = Spec(spec, **kwargs)
        state = myspec(irc, msg, given)
        self.assertEqual(state.errored, errored,
                         'Expected %r, got %r' % (errored, state.errored))


class GeneralContextTestCase(CommandsTestCase):
    def testEmptySpec(self):
        self.assertState([], [], [])

    def testSpecInt(self):
        self.assertState(['int'], ['1'], [1])
        self.assertState(['int', 'int', 'int'], ['1', '2', '3'], [1, 2, 3])
        self.assertError(['int'], ['9e999'])

    def testSpecNick(self):
        strict = conf.supybot.protocols.irc.strictRfc()
        try:
            conf.supybot.protocols.irc.strictRfc.setValue(True)
            self.assertError(['nick'], ['1abc'])
            conf.supybot.protocols.irc.strictRfc.setValue(False)
            self.assertState(['nick'], ['1abc'], ['1abc'])
        finally:
            conf.supybot.protocols.irc.strictRfc.setValue(strict)

    if minisix.PY2:
        def testSpecLong(self):
            self.assertState(['long'], ['1'], [long(1)])
            self.assertState(['long', 'long', 'long'], ['1', '2', '3'],
                             [long(1), long(2), long(3)])

    def testRestHandling(self):
        self.assertState([rest(None)], ['foo', 'bar', 'baz'], ['foo bar baz'])

    def testRestRequiresArgs(self):
        self.assertError([rest('something')], [])

    def testOptional(self):
        spec = [optional('int', 999), None]
        self.assertState(spec, ['12', 'foo'], [12, 'foo'])
        self.assertState(spec, ['foo'], [999, 'foo'])

    def testAdditional(self):
        spec = [additional('int', 999)]
        self.assertState(spec, ['12'], [12])
        self.assertState(spec, [], [999])
        self.assertError(spec, ['foo'])

    def testReverse(self):
        spec = [reverse('positiveInt'), 'float', 'text']
        self.assertState(spec, ['-1.0', 'foo', '1'], [1, -1.0, 'foo'])

    def testGetopts(self):
        spec = ['int', getopts({'foo': None, 'bar': 'int'}), 'int']
        self.assertState(spec,
                         ['12', '--foo', 'baz', '--bar', '13', '15'],
                         [12, [('foo', 'baz'), ('bar', 13)], 15])

    def testGetoptsShort(self):
        spec = ['int', getopts({'foo': None, 'bar': 'int'}), 'int']
        self.assertState(spec,
                         ['12', '--f', 'baz', '--ba', '13', '15'],
                         [12, [('foo', 'baz'), ('bar', 13)], 15])

    def testGetoptsConflict(self):
        spec = ['int', getopts({'foo': None, 'fbar': 'int'}), 'int']
        self.assertRaises(getopt.GetoptError, self.assertStateErrored,
                         spec, ['12', '--f', 'baz', '--ba', '13', '15'])

    def testAny(self):
        self.assertState([any('int')], ['1', '2', '3'], [[1, 2, 3]])
        self.assertState([None, any('int')], ['1', '2', '3'], ['1', [2, 3]])
        self.assertState([any('int')], [], [[]])
        self.assertState([any('int', continueOnError=True), 'text'],
                         ['1', '2', 'test'], [[1, 2], 'test'])

    def testMany(self):
        spec = [many('int')]
        self.assertState(spec, ['1', '2', '3'], [[1, 2, 3]])
        self.assertError(spec, [])

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

    def testLiteral(self):
        spec = [('literal', ['foo', 'bar', 'baz'])]
        self.assertState(spec, ['foo'], ['foo'])
        self.assertState(spec, ['fo'], ['foo'])
        self.assertState(spec, ['f'], ['foo'])
        self.assertState(spec, ['bar'], ['bar'])
        self.assertState(spec, ['baz'], ['baz'])
        self.assertError(spec, ['ba'])

class ConverterTestCase(CommandsTestCase):
    def testUrlAllowsHttps(self):
        url = 'https://foo.bar/baz'
        self.assertState(['url'], [url], [url])
        self.assertState(['httpUrl'], [url], [url])

    def testEmail(self):
        email = 'jemfinch@supybot.com'
        self.assertState(['email'], [email], [email])
        self.assertError(['email'], ['foo'])
        self.assertError(['email'], ['foo@'])
        self.assertError(['email'], ['@foo'])

class FirstTestCase(CommandsTestCase):
    def testRepr(self):
        self.assertTrue(repr(first('int')))

    def testFirstConverterFailsAndNotErroredState(self):
        self.assertStateErrored([first('int', 'something')], ['words'],
                                errored=False)

    def testLongRegexp(self):
        spec = [first('regexpMatcher', 'regexpReplacer'), 'text']
        self.assertStateErrored(spec, ['s/foo/bar/', 'x' * 512], errored=False)

class GetoptTestCase(PluginTestCase):
    plugins = ('Misc',) # We put something so it does not complain
    class Foo(callbacks.Plugin):
        def bar(self, irc, msg, args, optlist):
            irc.reply(' '.join(sorted(['%s:%d'%x for x in optlist])))
        bar = wrap(bar, [getopts({'foo': 'int', 'fbar': 'int'})],
                   checkDoc=False)

    def testGetoptsExact(self):
        self.irc.addCallback(self.Foo(self.irc))
        self.assertResponse('bar --foo 3 --fbar 4', 'fbar:4 foo:3')
        self.assertResponse('bar --fo 3 --fb 4', 'fbar:4 foo:3')
        self.assertResponse('bar --f 3 --fb 5',
                'Error: Invalid arguments for bar.')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

