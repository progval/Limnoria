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
The Success plugin spices up success replies just like Dunno spices up
"no such command" replies.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import time

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.registry as registry
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

conf.registerPlugin('Success')
conf.registerChannelValue(conf.supybot.plugins.Success, 'prefixNick',
    registry.Boolean(True, """Determines whether the bot will prefix the nick
    of the user giving an invalid command to the success response."""))

class Success(plugins.ChannelIdDatabasePlugin):
    """This plugin was written initially to work with MoobotFactoids, the two
    of them to provide a similar-to-moobot-and-blootbot interface for factoids.
    Basically, it replaces the standard 'Error: <X> is not a valid command.'
    messages with messages kept in a database, able to give more personable
    responses."""
    def __init__(self):
        self.__parent = super(Success, self)
        self.__parent.__init__()
        self.target = None
        pluginSelf = self
        self.originalClass = conf.supybot.replies.success.__class__
        class MySuccessClass(self.originalClass):
            def __call__(self):
                ret = pluginSelf.db.random(pluginSelf.target)
                if ret is None:
                    try:
                        self.__class__ = pluginSelf.originalClass
                        ret = self()
                    finally:
                        self.__class__ = MySuccessClass
                else:
                    ret = ret.text
                return ret

            def get(self, attr):
                if ircutils.isChannel(attr):
                    pluginSelf.target = attr
                return self
        conf.supybot.replies.success.__class__ = MySuccessClass

    def die(self):
        self.__parent.die()
        conf.supybot.replies.success.__class__ = self.originalClass

    def inFilter(self, irc, msg):
        # We need the target, but we need it before Owner.doPrivmsg is called,
        # so this seems like the only way to do it.
        self.target = msg.args[0]
        return msg


Class = Success

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
