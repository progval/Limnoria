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

    def testContributors(self):
        # Test ability to list contributors
        self.assertNotError('contributors Plugin')
        # Test ability to list contributions
        # Verify that when a single command contribution has been made,
        # the word "command" is properly not pluralized.
        # Note: This will break if the listed person ever makes more than
        # one contribution to the Plugin plugin
        self.assertRegexp('contributors Plugin skorobeus', 'command')
        # Test handling of pluralization of "command" when person has
        # contributed more than one command to the plugin.
        # -- Need to create this case, check it with the regexp 'commands'
        # Test handling of invalid plugin
        self.assertRegexp('contributors InvalidPlugin', 'not a valid plugin')
        # Test handling of invalid person
        self.assertRegexp('contributors Plugin noname',
                          'not a registered contributor')
        # Test handling of valid person with no contributions
        # Note: This will break if the listed person ever makes a contribution
        # to the Plugin plugin
        self.assertRegexp('contributors Plugin bwp',
                          'listed as a contributor')

    def testContributorsIsCaseInsensitive(self):
        self.assertNotError('contributors Plugin Skorobeus')
        self.assertNotError('contributors Plugin sKoRoBeUs')


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
