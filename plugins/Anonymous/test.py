###
# Copyright (c) 2005, Daniel DiPaolo
# Copyright (c) 2010, James McCoy
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

class AnonymousTestCase(ChannelPluginTestCase):
    plugins = ('Anonymous',)
    def testSay(self):
        self.assertError('anonymous say %s I love you!' % self.channel)
        self.assertError('anonymous say %s I love you!' % self.nick)
        origreg = conf.supybot.plugins.Anonymous.requireRegistration()
        origpriv = conf.supybot.plugins.Anonymous.allowPrivateTarget()
        try:
            conf.supybot.plugins.Anonymous.requireRegistration.setValue(False)
            m = self.assertNotError('anonymous say %s foo!' % self.channel)
            self.assertEqual(m.args[1], 'foo!')
            conf.supybot.plugins.Anonymous.allowPrivateTarget.setValue(True)
            m = self.assertNotError('anonymous say %s foo!' % self.nick)
            self.assertEqual(m.args[1], 'foo!')
        finally:
            conf.supybot.plugins.Anonymous.requireRegistration.setValue(origreg)
            conf.supybot.plugins.Anonymous.allowPrivateTarget.setValue(origpriv)

    def testAction(self):
        m = self.assertError('anonymous do %s loves you!' % self.channel)
        try:
            orig = conf.supybot.plugins.Anonymous.requireRegistration()
            conf.supybot.plugins.Anonymous.requireRegistration.setValue(False)
            m = self.assertNotError('anonymous do %s loves you!'%self.channel)
            self.assertEqual(m.args, ircmsgs.action(self.channel,
                                                    'loves you!').args)
        finally:
            conf.supybot.plugins.Anonymous.requireRegistration.setValue(orig)


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
