###
# Copyright (c) 2003, Daniel DiPaolo
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
The Dunno module is used to spice up the reply when given an invalid command
with random 'I dunno'-like responses.  If you want something spicier than
'<x> is not a valid command'-like responses, use this plugin.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.strike

__contributors__ = {
    supybot.authors.jemfinch: ['Flatfile DB implementation.'],
    }

import os
import csv
import sets
import time
import random
import itertools

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.plugins as plugins
import supybot.registry as registry
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

conf.registerPlugin('Dunno')
conf.registerChannelValue(conf.supybot.plugins.Dunno, 'prefixNick',
    registry.Boolean(True, """Determines whether the bot will prefix the nick
    of the user giving an invalid command to the "dunno" response."""))

class Dunno(plugins.ChannelIdDatabasePlugin):
    """This plugin was written initially to work with MoobotFactoids, the two
    of them to provide a similar-to-moobot-and-blootbot interface for factoids.
    Basically, it replaces the standard 'Error: <X> is not a valid command.'
    messages with messages kept in a database, able to give more personable
    responses."""
    callAfter = ['MoobotFactoids']
    def invalidCommand(self, irc, msg, tokens):
        channel = msg.args[0]
        if ircutils.isChannel(channel):
            dunno = self.db.random(channel)
            if dunno is not None:
                dunno = dunno.text
                prefixName = self.registryValue('prefixNick', channel)
                env = {'command': tokens[0]}
                dunno = ircutils.standardSubstitute(irc, msg, dunno, env=env)
                irc.reply(dunno, prefixName=prefixName)


Class = Dunno

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
