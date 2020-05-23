# -*- coding: utf8 -*-
###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

from __future__ import unicode_literals

from supybot.test import *

import re
import codecs

import supybot.utils as utils
import supybot.callbacks as callbacks
from supybot.utils.minisix import u

class FilterTest(ChannelPluginTestCase):
    plugins = ('Filter', 'Utilities', 'Reply')
    def testNoErrors(self):
        self.assertNotError('leet foobar')
        self.assertNotError('supa1337 foobar')
        self.assertNotError('aol I\'m too legit to quit.')

    def testDisabledCommandsCannotFilter(self):
        self.assertNotError('outfilter rot13')
        self.assertResponse('echo foo', 'sbb')
        self.assertNotError('outfilter')
        try:
            self.assertNotError('disable rot13')
            self.assertError('outfilter rot13')
            self.assertNotError('enable rot13')
            self.assertNotError('outfilter rot13')
        finally:
            try:
                callbacks.Plugin._disabled.remove('rot13')
            except KeyError:
                pass

    def testHebrew(self):
        self.assertResponse('hebrew The quick brown fox '
                            'jumps over the lazy dog.',
                            'Th qck brwn fx jmps vr th lzy dg.')
    def testJeffk(self):
        for i in range(100):
            self.assertNotError('jeffk the quick brown fox is ghetto')

    def testSquish(self):
        self.assertResponse('squish foo bar baz', 'foobarbaz')
        self.assertResponse('squish "foo bar baz"', 'foobarbaz')

    def testUndup(self):
        self.assertResponse('undup foo bar baz quux', 'fo bar baz qux')
        self.assertResponse('undup aaaaaaaaaa', 'a')

    def testMorse(self):
        self.assertResponse('unmorse [morse jemfinch]', 'JEMFINCH')

    def testReverse(self):
        for s in map(str, range(1000, 1010)):
            self.assertResponse('reverse %s' % s, s[::-1])

    def testBinary(self):
        self.assertResponse('binary A', '01000001')

    def testUnbinary(self):
        self.assertResponse('unbinary 011011010110111101101111', 'moo')
        self.assertError('unbinary moo')
        self.assertResponse('unbinary 01101101 01101111 01101111', 'moo')

    def testRot13(self):
        for s in map(str, range(1000, 1010)):
            self.assertResponse('rot13 [rot13 %s]' % s, s)

    def testRot13HandlesNonAsciiStuff(self):
        self.assertNotError('rot13 é')

    def testHexlifyUnhexlify(self):
        for s in map(str, range(1000, 1010)):
            self.assertResponse('unhexlify [hexlify %s]' % s, s)
        self.assertNotError('unhexlify ff')

    def testScramble(self):
        s = 'the recalcitrant jamessan tests his scramble function'
        self.assertNotRegexp('scramble %s' % s, s)
        s = 'the recalc1trant jam3ssan tests his scramble fun><tion'
        self.assertNotRegexp('scramble %s' % s, s)

    def testColorize(self):
        self.assertNotRegexp('colorize foobar', r'\s+')
        self.assertRegexp('colorize foobar', r'\x03')
        # Make sure we're closing colorize with an 'end color' marker
        self.assertRegexp('colorize foobar', r'\x03$')

    _strings = ('Supybot pwns!', '123456', 'A string with \x02bold\x15')
    def testColorstrip(self):
        for s in self._strings:
            self.assertResponse('stripcolor [colorize %s]' % s, s)

    def testSpellit(self):
        self.assertRegexp('spellit abc123!.%', 'ay bee see one two three '
                          'exclamation point period percent')
        self.assertNotError('config plugins.Filter.spellit.replaceLetters off')
        self.assertRegexp('spellit asasdfasdf12345@#$!%^',
                          'asasdfasdf one two three four five at pound '
                          'dollar sign exclamation point percent caret')
        self.assertNotError('config plugins.Filter.spellit.replaceNumbers off')
        self.assertRegexp('spellit asasdfasdf12345@#$!%^',
                          'asasdfasdf12345 at pound dollar sign exclamation '
                          'point percent caret')
        self.assertNotError('config '
                            'plugins.Filter.spellit.replacePunctuation off')
        self.assertResponse('spellit asasdfasdf12345@#$!%^',
                            'asasdfasdf12345@#$!%^')

    _rot13_encoder = codecs.getencoder('rot-13')
    def testOutfilter(self):
        s = self._rot13_encoder(self.nick)[0]
        self.assertNotError('outfilter rot13')
        self.assertResponse('rot13 foobar', '%s: foobar' % s)
        self.assertNotError('outfilter rot13')
        self.assertResponse('rot13 foobar', 'sbbone')
        self.assertNotError('outfilter')
        self.assertResponse('rot13 foobar', 'sbbone')
        self.assertNotError('outfilter ROT13')
        self.assertResponse('rot13 foobar', '%s: foobar' % s)
        self.assertNotError('outfilter')
        self.assertResponse('rot13 foobar', 'sbbone')

    def testOutfilterAction(self):
        s = self._rot13_encoder(self.nick)[0]
        self.assertNotError('outfilter rot13')
        self.assertResponse('rot13 foobar', '%s: foobar' % s)
        m = self.getMsg('action foobar')
        self.assertTrue(ircmsgs.isAction(m))
        s = ircmsgs.unAction(m)
        self.assertEqual(s, 'sbbone')

    def testGnu(self):
        self.assertResponse('gnu foo bar baz', 'GNU/foo GNU/bar GNU/baz')
        self.assertNotError('outfilter gnu')
        self.assertResponse('echo foo bar baz', 'GNU/foo GNU/bar GNU/baz')
        self.assertNotError('outfilter')

    def testShrink(self):
        self.assertResponse('shrink I love you', 'I l2e you')
        self.assertResponse('shrink internationalization', 'i18n')
        self.assertResponse('shrink "I love you"', 'I l2e you')
        self.assertResponse('shrink internationalization, localization',
                            'i18n, l10n')

    def testVowelrot(self):
        self.assertResponse('vowelrot foo bar baz', 'fuu ber bez')

    def testUwu(self):
        for _ in range(100):
            self.assertRegexp('uwu foo bar baz', 'foo baw baz( [uoUO]w[uoUO])?')
        self.assertRegexp('uwu FOO BAR BAZ', 'FOO BAW BAZ( [uoUO]w[uoUO])?')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
