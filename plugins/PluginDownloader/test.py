###
# Copyright (c) 2011, Valentin Lorentz
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

import os
import sys
import shutil

from supybot.test import *
import supybot.utils.minisix as minisix

pluginsPath = '%s/test-plugins' % os.getcwd()

class PluginDownloaderTestCase(PluginTestCase):
    plugins = ('PluginDownloader',)
    config = {'supybot.directories.plugins': [pluginsPath]}

    def setUp(self):
        PluginTestCase.setUp(self)
        try:
            shutil.rmtree(pluginsPath)
        except:
            pass
        os.mkdir(pluginsPath)

    def tearDown(self):
        try:
            shutil.rmtree(pluginsPath)
        finally:
            PluginTestCase.tearDown(self)

    def _testPluginInstalled(self, name):
        assert os.path.isdir(pluginsPath + '/%s/' % name)
        assert os.path.isfile(pluginsPath + '/%s/plugin.py' % name)
        assert os.path.isfile(pluginsPath + '/%s/config.py' % name)

    def testRepolist(self):
        self.assertRegexp('repolist', '(.*, )?ProgVal(, .*)?')
        self.assertRegexp('repolist', '(.*, )?quantumlemur(, .*)?')
        self.assertRegexp('repolist ProgVal', '(.*, )?AttackProtector(, .*)?')

    def testInstallProgVal(self):
        self.assertError('plugindownloader install ProgVal Darcs')
        self.assertNotError('plugindownloader install ProgVal AttackProtector')
        self.assertError('plugindownloader install ProgVal Darcs')
        self._testPluginInstalled('AttackProtector')

    def testShellForbidden(self):
        with conf.supybot.commands.allowShell.context(False):
            self.assertRegexp('plugindownloader install ProgVal Darcs',
                    'Error:.*not available.*supybot.commands.allowShell')

    def testInstallQuantumlemur(self):
        self.assertError('plugindownloader install quantumlemur AttackProtector')
        self.assertNotError('plugindownloader install quantumlemur Listener')
        self.assertError('plugindownloader install quantumlemur AttackProtector')
        self._testPluginInstalled('Listener')

    def testInstallStepnem(self):
        self.assertNotError('plugindownloader install stepnem Freenode')
        self._testPluginInstalled('Freenode')

    def testInstallNanotubeBitcoin(self):
        self.assertNotError('plugindownloader install nanotube-bitcoin GPG')
        self._testPluginInstalled('GPG')

    def testInstallMtughanWeather(self):
        self.assertNotError('plugindownloader install mtughan-weather '
                            'WunderWeather')
        self._testPluginInstalled('WunderWeather')

    def testInstallSpiderDave(self):
        self.assertNotError('plugindownloader install SpiderDave Pastebin')
        self._testPluginInstalled('Pastebin')

    def testInstallNonAsciiInit(self):
        self.assertNotError('plugindownloader install Hoaas DuckDuckGo')
        self._testPluginInstalled('DuckDuckGo')

    def testInfo(self):
        self.assertResponse('plugindownloader info ProgVal Twitter',
                'Advanced Twitter plugin for Supybot, with capabilities '
                'handling, and per-channel user account.')

    if minisix.PY3:
        def test_2to3(self):
            self.assertRegexp('plugindownloader install SpiderDave Pastebin',
                    'convert')
            self.assertNotError('load Pastebin')

if not network:
    class PluginDownloaderTestCase(PluginTestCase):
        pass

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
