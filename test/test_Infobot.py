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

import supybot.plugins.Infobot
confirms = supybot.plugins.Infobot.confirms
dunnos = supybot.plugins.Infobot.dunnos
ibot = conf.supybot.plugins.Infobot

class InfobotTestCase(ChannelPluginTestCase):
    plugins = ('Infobot',)
    _endRe = re.compile(r'!|, \S+\.|\.')
    def testIsSnarf(self):
        learn = ibot.unaddressed.snarfDefinitions()
        answer = ibot.unaddressed.answerQuestions()
        try:
            ibot.unaddressed.snarfDefinitions.setValue(True)
            ibot.unaddressed.answerQuestions.setValue(True)
            self.assertSnarfNoResponse('foo is at http://bar.com/', 2)
            self.assertRegexp('infobot stats', '1 modification')
            self.assertRegexp('infobot status', '1 modification')
            self.assertSnarfRegexp('foo?', r'foo.*is.*http://bar.com/')
            self.assertSnarfNoResponse('foo is at http://baz.com/', 2)
            self.assertSnarfNotRegexp('foo?', 'baz')
            m = self.getMsg('bar is at http://foo.com/')
            self.failUnless(self._endRe.sub('', m.args[1]) in confirms)
            self.assertRegexp('bar?', r'bar.*is.*http://foo.com/')
            self.assertRegexp('what was bar?', r'http://foo.com/')
        finally:
            ibot.unaddressed.snarfDefinitions.setValue(learn)
            ibot.unaddressed.answerQuestions.setValue(answer)

    def testNormalize(self):
        learn = ibot.unaddressed.snarfDefinitions()
        answer = ibot.unaddressed.answerQuestions()
        try:
            ibot.unaddressed.snarfDefinitions.setValue(True)
            ibot.unaddressed.answerQuestions.setValue(True)
            self.assertSnarfNoResponse('foo is at http://bar.com/', 2)
            self.assertSnarfRegexp('what\'s foo?', r'foo.*is.*http://bar.com/')
            self.assertSnarfRegexp('wtf\'s foo?', r'foo.*is.*http://bar.com/')
            self.assertSnarfRegexp('who\'s foo?', r'foo.*is.*http://bar.com/')
            self.assertSnarfRegexp('where\'s foo?',r'foo.*is.*http://bar.com/')
            self.assertSnarfNoResponse('i am a tool', 2)
            self.assertRegexp('%s?' % self.nick, r'is.*tool')
            self.assertSnarfNoResponse('my bot is a tool', 2)
            self.assertRegexp('%s\'s bot?' % self.nick, r'is.*tool')
            self.assertSnarfNoResponse('your name is weird', 2)
            self.assertRegexp('%s\'s name?' % self.irc.nick, r'is.*weird')
        finally:
            ibot.unaddressed.snarfDefinitions.setValue(learn)
            ibot.unaddressed.answerQuestions.setValue(answer)

    def testAreSnarf(self):
        learn = ibot.unaddressed.snarfDefinitions()
        answer = ibot.unaddressed.answerQuestions()
        try:
            ibot.unaddressed.snarfDefinitions.setValue(True)
            ibot.unaddressed.answerQuestions.setValue(True)
            self.assertSnarfNoResponse('bars are dirty', 2)
            self.assertSnarfRegexp('bars?', 'bars.*are.*dirty')
            self.assertSnarfNoResponse('bars are not dirty', 2)
            self.assertSnarfNotRegexp('bars?', 'not')
            self.assertSnarfRegexp('what were bars?', 'dirty')
        finally:
            ibot.unaddressed.snarfDefinitions.setValue(learn)
            ibot.unaddressed.answerQuestions.setValue(answer)

    def testIsResponses(self):
        learn = ibot.unaddressed.snarfDefinitions()
        answer = ibot.unaddressed.answerQuestions()
        try:
            ibot.unaddressed.snarfDefinitions.setValue(True)
            ibot.unaddressed.answerQuestions.setValue(True)
            self.assertSnarfNoResponse('foo is bar', 2)
            self.assertSnarfRegexp('foo?', 'foo.*is.*bar')
            self.assertSnarfNoResponse('when is foo?', 2)
            self.assertSnarfNoResponse('why is foo?', 2)
            self.assertSnarfNoResponse('why foo?', 2)
            self.assertSnarfNoResponse('when is foo?', 2)
        finally:
            ibot.unaddressed.snarfDefinitions.setValue(learn)
            ibot.unaddressed.answerQuestions.setValue(answer)

    def testAnswerUnaddressed(self):
        answer = ibot.unaddressed.answerQuestions()
        try:
            ibot.unaddressed.answerQuestions.setValue(True)
            self.assertSnarfNoResponse('foo is bar')
            self.assertSnarfRegexp('foo?', 'foo.*is.*bar')
            ibot.unaddressed.answerQuestions.setValue(False)
            self.assertSnarfNoResponse('foo?', 2)
        finally:
            ibot.unaddressed.answerQuestions.setValue(answer)

    def testReplaceFactoid(self):
        answer = ibot.unaddressed.answerQuestions()
        learn = ibot.unaddressed.snarfDefinitions()
        try:
            ibot.unaddressed.answerQuestions.setValue(True)
            ibot.unaddressed.snarfDefinitions.setValue(True)
            self.assertSnarfNoResponse('forums are good')
            self.assertSnarfRegexp('forums?', r'forums.*are.*good')
            self.assertNotError('no, forums are evil')
            self.assertSnarfRegexp('forums?', r'forums.*.are.*evil')
        finally:
            ibot.unaddressed.answerQuestions.setValue(answer)
            ibot.unaddressed.snarfDefinitions.setValue(learn)

    def testDoubleIsAre(self):
        answer = ibot.unaddressed.answerQuestions()
        learn = ibot.unaddressed.snarfDefinitions()
        try:
            ibot.unaddressed.answerQuestions.setValue(True)
            ibot.unaddressed.snarfDefinitions.setValue(True)
            self.assertSnarfNoResponse('foo is <reply> foo is bar')
            self.assertSnarfRegexp('foo?', 'foo is bar')
            self.assertSnarfNoResponse('bars are <reply> bars are good')
            self.assertSnarfRegexp('bars?', 'bars are good')
            self.assertSnarfNoResponse('bees are <reply> honey is good')
            self.assertSnarfRegexp('bees?', 'honey is good')
            self.assertSnarfNoResponse('food is <reply> tacos are good')
            self.assertSnarfRegexp('food?', 'tacos are good')
        finally:
            ibot.unaddressed.answerQuestions.setValue(answer)
            ibot.unaddressed.snarfDefinitions.setValue(learn)

    def testNoKarmaDunno(self):
        self.assertNoResponse('foo++')

    def testPredefinedFactoids(self):
        self.assertSnarfNoResponse('what?', 3)
        self.assertRegexp('roses?', 'roses are red')

    def testAddressedQuestions(self):
        self.assertSnarfNoResponse('hi is <reply>Hello, $who.')
        self.assertSnarfNoResponse('hi')
        self.assertRegexp('hi', 'Hello')

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
