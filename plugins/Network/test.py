###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

class NetworkTestCase(PluginTestCase):
    plugins = ['Network', 'Utilities', 'String', 'Misc']
    def testNetworks(self):
        self.assertNotError('networks')

    def testCommand(self):
        self.assertResponse('network command %s echo 1' % self.irc.network,
                            '1')
        # empty args should be allowed, see
        # https://github.com/progval/Limnoria/issues/1541
        self.assertResponse('network command %s len ""' % self.irc.network, '0')

    def testCommandRoutesBackToCaller(self):
        self.otherIrc = getTestIrc("testnet1")
        # This will fail with timeout if the response never comes back
        self.assertResponse(
            'network command testnet1 echo $network', 'testnet1')

    def testCommandRoutesErrorsBackToCaller(self):
        self.otherIrc = getTestIrc("testnet2")
        self.assertRegexp(
            f'network command testnet2 re s/.*// test',
            'I tried to send you an empty message')

    def testCommandRoutesMoreBackToCaller(self):
        self.otherIrc = getTestIrc("testnet3")
        self.assertNotError('clearmores')
        self.assertError('more')
        self.assertRegexp(
            f'network command testnet3 echo {"Hello"*300}',
            r'Hello.*\(\d+ more messages\)')
        self.assertRegexp(
            'more',
            r'Hello.*\(\d+ more messages\)')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

