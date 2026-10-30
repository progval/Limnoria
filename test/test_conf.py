##
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

import supybot.conf as conf
import supybot.registry as registry
import supybot.ircutils as ircutils

import os
from unittest import mock


class SupyConfTestCase(SupyTestCase):
    def testJoinToOneChannel(self):
        orig = conf.supybot.networks.test.channels()
        channels = ircutils.IrcSet()
        channels.add("#bar")
        conf.supybot.networks.test.channels.setValue(channels)
        msgs = conf.supybot.networks.test.channels.joins()
        self.assertEqual(msgs[0].args, ("#bar",))
        conf.supybot.networks.test.channels.setValue(orig)

    def testJoinToManyChannels(self):
        orig = conf.supybot.networks.test.channels()
        channels = ircutils.IrcSet()
        input_list = []
        for x in range(1, 30):
            name = "#verylongchannelname" + str(x)
            channels.add(name)
            input_list.append(name)
        conf.supybot.networks.test.channels.setValue(channels)
        msgs = conf.supybot.networks.test.channels.joins()
        # Double check we split the messages
        self.assertEqual(len(msgs), 2)
        # Ensure all channel names are present
        chan_list = (msgs[0].args[0] + ',' + msgs[1].args[0]).split(',')
        self.assertCountEqual(input_list, chan_list)
        conf.supybot.networks.test.channels.setValue(orig)


class DirectoriesTestCase(SupyTestCase):
    def testDirectoryExpandsUser(self):
        home = os.path.expanduser('~')
        d = conf.Directory('~/limnoria-test-dir', 'help')
        mkdir = []
        with mock.patch('os.mkdir', mkdir.append), \
                mock.patch('os.path.exists', lambda path: False):
            self.assertEqual(d(), os.path.join(home, 'limnoria-test-dir'))
        self.assertEqual(mkdir, [os.path.join(home, 'limnoria-test-dir')])
        # The configured value itself is left untouched
        self.assertEqual(str(d), '~/limnoria-test-dir')

    def testPluginDirectoriesExpandUser(self):
        home = os.path.expanduser('~')
        orig = conf.supybot.directories.plugins()[:]
        try:
            conf.supybot.directories.plugins.set(
                '~/plugins, /opt/limnoria/plugins')
            self.assertEqual(conf.supybot.directories.plugins(),
                             [os.path.join(home, 'plugins'),
                              '/opt/limnoria/plugins'])
        finally:
            conf.supybot.directories.plugins.setValue(orig)
