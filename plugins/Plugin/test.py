###
# Copyright (c) 2005, Jeremiah Fincher
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

import supybot
from supybot.test import *

class PluginTestCase(PluginTestCase):
    plugins = ('Plugin', 'Utilities', 'Admin', 'Format')
    def testPlugin(self):
        self.assertRegexp('plugin ignore', 'available.*Utilities plugin')
        self.assertResponse('echo [plugin ignore]', 'Utilities')

    def testPlugins(self):
        self.assertRegexp('plugins join', '(Format.*Admin|Admin.*Format)')
        self.assertRegexp('plugins plugin', 'Plugin')
        self.assertNotRegexp('plugins ignore add', 'Utilities')
        self.assertNotRegexp('plugins ignore', 'Admin')

    def testHelp(self):
        self.assertRegexp('plugin help plugin', 'manage their plugins')

    def testAuthor(self):
        self.assertRegexp('plugin author plugin', 'jemfinch')
        self.assertRegexp('plugin author plugin', 'maintained by %s' %
                          supybot.authors.limnoria_core.name)

    def testContributors(self):
        # Test ability to list contributors
        self.assertNotError('contributors Plugin')

        # Test ability to list contributions
        # As of 2019-10-19 there is no more distinction between commands and non-commands
        self.assertRegexp('contributors Plugin skorobeus',
                          'original contributors command')
        self.assertRegexp('contributors Plugin Kevin Murphy',
                          'original contributors command')
        self.assertRegexp('contributors Plugin James Lu',
                          'refactored contributors command')

        # Test handling of the plugin author, who is usually not listed in __contributors__
        self.assertRegexp('contributors Plugin jemfinch',
                          'wrote the Plugin plugin')
        self.assertRegexp('contributors Plugin Jeremy Fincher',
                          'wrote the Plugin plugin')

        # TODO: test handling of a person with multiple contributions to a command

        # Test handling of invalid plugin
        self.assertRegexp('contributors InvalidPlugin', 'not a valid plugin')

        # Test handling of unknown person. As of 2019-10-19 it doesn't matter whether
        # they're listed in supybot.authors or not.
        self.assertRegexp('contributors Plugin noname',
                          'not listed as a contributor')
        self.assertRegexp('contributors Plugin bwp',
                          'not listed as a contributor')

    def testContributorsIsCaseInsensitive(self):
        self.assertNotError('contributors Plugin Skorobeus')
        self.assertNotError('contributors Plugin sKoRoBeUs')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
