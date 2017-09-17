###
# Copyright (c) 2004, Jeremiah Fincher
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

class DebugTestCase(PluginTestCase):
    plugins = ('Debug',)


    def testShellForbidden(self):
        self.assertResponse('debug eval 1+2', '3')
        self.assertResponse('debug simpleeval 1+2', '3')
        self.assertResponse('debug exec irc.reply(1+2)', '3')
        while self.irc.takeMsg():
            pass
        self.assertNotError('debug environ')
        with conf.supybot.commands.allowShell.context(False):
            self.assertRegexp('debug eval 1+2',
                    'Error:.*not available.*supybot.commands.allowShell')
            self.assertRegexp('debug simpleeval 1+2',
                    'Error:.*not available.*supybot.commands.allowShell')
            self.assertRegexp('debug exec irc.reply(1+2)',
                    'Error:.*not available.*supybot.commands.allowShell')
            self.assertRegexp('debug environ',
                    'Error:.*not available.*supybot.commands.allowShell')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
