##
# Copyright (c) 2019-2021, Valentin Lorentz
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
import supybot.ircdb as ircdb
import supybot.irclib as irclib
import supybot.drivers as drivers

class DriversTestCase(SupyTestCase):
    def tearDown(self):
        ircdb.networks.networks = {}

    def testValidStsPolicy(self):
        irc = irclib.Irc('test')
        net = ircdb.networks.getNetwork('test')
        net.addStsPolicy('example.com', 6697, 'duration=10,port=12345')
        net.addDisconnection('example.com')

        with conf.supybot.networks.test.servers.context(
                ['example.com:6667', 'example.org:6667']):

            driver = drivers.ServersMixin(irc)

            self.assertEqual(
                driver._getNextServer(),
                drivers.Server('example.com', 6697, None, True))
            driver.die()

            self.assertEqual(
                driver._getNextServer(),
                drivers.Server('example.org', 6667, None, False))
            driver.die()

            self.assertEqual(
                driver._getNextServer(),
                drivers.Server('example.com', 6697, None, True))

    def testExpiredStsPolicy(self):
        irc = irclib.Irc('test')
        net = ircdb.networks.getNetwork('test')
        net.addStsPolicy('example.com', 6697, 'duration=10')
        net.addDisconnection('example.com')

        timeFastForward(16)

        with conf.supybot.networks.test.servers.context(
                ['example.com:6667']):

            driver = drivers.ServersMixin(irc)

            self.assertEqual(
                driver._getNextServer(),
                drivers.Server('example.com', 6667, None, False))

    def testRescheduledStsPolicy(self):
        irc = irclib.Irc('test')
        net = ircdb.networks.getNetwork('test')
        net.addStsPolicy('example.com', 6697, 'duration=10')
        net.addDisconnection('example.com')

        with conf.supybot.networks.test.servers.context(
                ['example.com:6667', 'example.org:6667']):

            driver = drivers.ServersMixin(irc)

            timeFastForward(8)

            self.assertEqual(
                driver._getNextServer(),
                drivers.Server('example.com', 6697, None, True))
            driver.die()

            self.assertEqual(
                driver._getNextServer(),
                drivers.Server('example.org', 6667, None, False))
            driver.die()

            timeFastForward(8)

            self.assertEqual(
                driver._getNextServer(),
                drivers.Server('example.com', 6697, None, True))
