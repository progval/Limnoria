###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

import supybot.conf as conf
from supybot.test import *

class BadWordsTestCase(PluginTestCase):
    plugins = ('BadWords', 'Utilities', 'Format', 'Filter')
    badwords = ('shit', 'ass', 'fuck')
    def tearDown(self):
        # .default() doesn't seem to be working for BadWords.words
        #default = conf.supybot.plugins.BadWords.words.default()
        #conf.supybot.plugins.BadWords.words.setValue(default)
        conf.supybot.plugins.BadWords.words.setValue([])

    def _test(self):
        for word in self.badwords:
            self.assertRegexp('echo %s' % word, '(?!%s)' % word)
            self.assertRegexp('echo [colorize %s]' % word, '(?!%s)' % word)
            self.assertRegexp('echo foo%sbar' % word, '(?!%s)' % word)
            self.assertRegexp('echo foo %s bar' % word, '(?!%s)' % word)
            self.assertRegexp('echo [format join "" %s]' % ' '.join(word),
                              '(?!%s)' % word)
            with conf.supybot.plugins.BadWords.requireWordBoundaries \
                    .context(True):
                self.assertRegexp('echo foo%sbar' % word, word)
                self.assertRegexp('echo foo %sbar' % word, word)
                self.assertRegexp('echo foo%s bar' % word, word)
                self.assertRegexp('echo foo %s bar' % word, '(?!%s)' % word)

    def _NegTest(self):
        for word in self.badwords:
            self.assertRegexp('echo %s' % word, word)
            self.assertRegexp('echo foo%sbar' % word, word)
            self.assertRegexp('echo [format join "" %s]' % ' '.join(word),word)

    def testAddbadwords(self):
        self.assertNotError('badwords add %s' % ' '.join(self.badwords))
        self._test()

    def testDefault(self):
        self._NegTest()

    def testRemovebadwords(self):
        self.assertNotError('badwords add %s' % ' '.join(self.badwords))
        self.assertNotError('badwords remove %s' % ' '.join(self.badwords))
        self._NegTest()

    def testList(self):
        self.assertNotError('badwords list')
        self.assertNotError('badwords add shit')
        self.assertNotError('badwords add ass')
        self.assertNotError('badwords add "fuck you"')
        self.assertResponse('badwords list', 'ass, fuck you, and shit')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

