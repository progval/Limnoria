###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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

import supybot.conf as conf

class ConfigTestCase(ChannelPluginTestCase):
    # We add utilities so there's something in supybot.plugins.
    plugins = ('Config', 'Utilities')
    def testGet(self):
        self.assertNotRegexp('config get supybot.reply', r'registry\.Group')
        self.assertResponse('config supybot.protocols.irc.throttleTime', '0.0')

    def testList(self):
        self.assertError('config list asldfkj')
        self.assertError('config list supybot.asdfkjsldf')
        self.assertNotError('config list supybot')
        self.assertNotError('config list supybot.replies')
        self.assertRegexp('config list supybot', r'@plugins.*@replies.*@reply')

    def testHelp(self):
        self.assertError('config help alsdkfj')
        self.assertError('config help supybot.alsdkfj')
        self.assertNotError('config help supybot') # We tell the user to list.
        self.assertNotError('config help supybot.plugins')
        self.assertNotError('config help supybot.replies.success')
        self.assertNotError('config help replies.success')

    def testHelpDoesNotAssertionError(self):
        self.assertNotRegexp('config help ' # Cont'd.
                             'supybot.commands.defaultPlugins.help',
                             'AssertionError')

    def testHelpExhaustively(self):
        L = conf.supybot.getValues(getChildren=True)
        for (name, v) in L:
            self.assertNotError('config help %s' % name)

    def testSearch(self):
        self.assertNotError('config search chars')
        self.assertNotError('config channel reply.whenAddressedBy.chars @')
        self.assertNotRegexp('config search chars', self.channel)

    def testDefault(self):
        self.assertNotError('config default '
                            'supybot.replies.genericNoCapability')

    def testConfigErrors(self):
        self.assertRegexp('config supybot.replies.', 'not a valid')
        self.assertRegexp('config supybot.repl', 'not a valid')
        self.assertRegexp('config supybot.reply.withNickPrefix 123',
                          'True or False.*, not \'123\'.')
        self.assertRegexp('config supybot.replies foo', 'settable')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

