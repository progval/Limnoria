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

"""
This is a plugin for handling Freenode-specific things.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.unknown
__contributors__ = {}

import supybot.plugins as plugins

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('Freenode', True)

Freenode = conf.registerPlugin('Freenode')
conf.registerGlobalValue(Freenode, 'identifyMsg', registry.Boolean(False, """
    Determines whether the bot will tell the server to let it know when
    messages are coming from unidentified users."""))
conf.registerGlobalValue(Freenode, 'ignoreUnidentified', registry.Boolean(False,
    """Determines whether the bot will ignore users who have not identified to
    NickServ."""))

class Freenode(callbacks.Privmsg):
    def __init__(self):
        self.__parent = super(Freenode, self)
        self.__parent.__init__()

    def do290(self, irc, msg):
        assert 'IDENTIFY-MSG' in msg.args[1]
        irc._Freenode_capabed = True

    def do376(self, irc, msg):
        if self.registryValue('identifyMsg'):
            irc.queueMsg(ircmsgs.IrcMsg('CAPAB IDENTIFY-MSG'))

    def inFilter(self, irc, msg):
        if getattr(irc,'_Freenode_capabed',None) and msg.command == 'PRIVMSG':
            first = msg.args[1][0]
            rest = msg.args[1][1:]
            msg.tag('identified', first == '+')
            if self.registryValue('ignoreUnidentified') and not msg.identified:
                self.log.info('Ignoring %s, not identified.', msg.nick)
                msg = None
            else:
                msg = ircmsgs.privmsg(msg.args[0], rest, msg=msg)
                assert msg.receivedAt and msg.receivedOn and msg.receivedBy
        return msg


Class = Freenode

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
