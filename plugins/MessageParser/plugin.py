###
# Copyright (c) 2010, Daniel Folkinshteyn
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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import re

## will add db stuff later

class MessageParser(callbacks.PluginRegexp):
    """This plugin can set regexp triggers to activate the bot.
    Use 'add' command to add regexp trigger, 'remove' to remove."""
    threaded = True
    regexps = ['regexpSnarfer']
    def __init__(self, irc):
        self.__parent = super(MessageParser, self)
        self.__parent.__init__(irc)
    
    def regexpSnarfer(self, irc, msg, match):
        r".*"
        channel = msg.args[0]
        msgtext = match.group(0)
        if not irc.isChannel(channel):
            return
        if self.registryValue('enable', channel):
            if re.search('some stuff', msgtext):
                irc.reply('some stuff detected', prefixNick=False)
    regexpSnarfer = urlSnarfer(regexpSnarfer)

Class = MessageParser


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
