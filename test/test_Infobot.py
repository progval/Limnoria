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

import supybot.plugins.Infobot
confirms = supybot.plugins.Infobot.confirms
dunnos = supybot.plugins.Infobot.dunnos

class InfobotTestCase(ChannelPluginTestCase):
    plugins = ('Infobot',)
    _endRe = re.compile(r'!|, \S+\.|\.')
    def testIsSnarf(self):
        ibot = conf.supybot.plugins.Infobot
        learn = ibot.snarfUnaddressedDefinitions()
        answer = ibot.answerUnaddressedQuestions()
        try:
            ibot.snarfUnaddressedDefinitions.setValue(True)
            ibot.answerUnaddressedQuestions.setValue(True)
            self.assertSnarfNoResponse('foo is at http://bar.com/', 2)
            self.assertSnarfRegexp('foo?', r'foo.*is.*http://bar.com/')
            self.assertSnarfNoResponse('foo is at http://baz.com/', 2)
            self.assertSnarfNotRegexp('foo?', 'baz')
            m = self.getMsg('bar is at http://foo.com/')
            self.failUnless(self._endRe.sub('', m.args[1]) in confirms)
            self.assertRegexp('bar?', r'bar.*is.*http://foo.com/')
        finally:
            ibot.snarfUnaddressedDefinitions.setValue(learn)
            ibot.answerUnaddressedQuestions.setValue(answer)

    def testAreSnarf(self):
        ibot = conf.supybot.plugins.Infobot
        learn = ibot.snarfUnaddressedDefinitions()
        answer = ibot.answerUnaddressedQuestions()
        try:
            ibot.snarfUnaddressedDefinitions.setValue(True)
            ibot.answerUnaddressedQuestions.setValue(True)
            self.assertSnarfNoResponse('bars are dirty', 2)
            self.assertSnarfRegexp('bars?', 'bars.*are.*dirty')
            self.assertSnarfNoResponse('bars are not dirty', 2)
            self.assertSnarfNotRegexp('bars?', 'not')
        finally:
            ibot.snarfUnaddressedDefinitions.setValue(learn)
            ibot.answerUnaddressedQuestions.setValue(answer)

    def testIsResponses(self):
        ibot = conf.supybot.plugins.Infobot
        learn = ibot.snarfUnaddressedDefinitions()
        answer = ibot.answerUnaddressedQuestions()
        try:
            ibot.snarfUnaddressedDefinitions.setValue(True)
            ibot.answerUnaddressedQuestions.setValue(True)
            self.assertSnarfNoResponse('foo is bar', 2)
            self.assertSnarfRegexp('foo?', 'foo.*is.*bar')
            self.assertSnarfNoResponse('when is foo?', 2)
            self.assertSnarfNoResponse('why is foo?', 2)
            self.assertSnarfNoResponse('why foo?', 2)
            self.assertSnarfNoResponse('when is foo?', 2)
        finally:
            ibot.snarfUnaddressedDefinitions.setValue(learn)
            ibot.answerUnaddressedQuestions.setValue(answer)

    def testAnswerUnaddressed(self):
        ibot = conf.supybot.plugins.Infobot
        answer = ibot.answerUnaddressedQuestions()
        try:
            ibot.answerUnaddressedQuestions.setValue(True)
            self.assertSnarfNoResponse('foo is bar')
            self.assertSnarfRegexp('foo?', 'bar')
            ibot.answerUnaddressedQuestions.setValue(False)
            self.assertSnarfNoResponse('foo?', 2)
        finally:
            ibot.answerUnaddressedQuestions.setValue(answer)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
