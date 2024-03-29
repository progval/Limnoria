###
# Copyright (c) 2004-2005, Jeremiah Fincher
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

class LimiterTestCase(ChannelPluginTestCase):
    plugins = ('Limiter',)
    config = {'supybot.plugins.Limiter.enable': True}
    def testEnforceLimit(self):
        origMin = conf.supybot.plugins.Limiter.minimumExcess()
        origMax = conf.supybot.plugins.Limiter.maximumExcess()
        try:
            conf.supybot.plugins.Limiter.minimumExcess.setValue(5)
            conf.supybot.plugins.Limiter.maximumExcess.setValue(10)
            self.irc.feedMsg(ircmsgs.join('#foo', prefix='foo!root@host'))
            m = self.irc.takeMsg()
            self.assertEqual(m, ircmsgs.limit('#foo', 1+10))
            self.irc.feedMsg(ircmsgs.join('#foo', prefix='bar!root@host'))
            m = self.irc.takeMsg()
            self.assertIsNone(m)
            conf.supybot.plugins.Limiter.maximumExcess.setValue(7)
            self.irc.feedMsg(ircmsgs.part('#foo', prefix='bar!root@host'))
            m = self.irc.takeMsg()
            self.assertEqual(m, ircmsgs.limit('#foo', 1+5))
        finally:
            conf.supybot.plugins.Limiter.minimumExcess.setValue(origMin)
            conf.supybot.plugins.Limiter.maximumExcess.setValue(origMax)


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
