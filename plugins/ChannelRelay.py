#!/usr/bin/python

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
This plugin is useful for relaying messages from one channel on a network to
another channel on the same network.  If you're interested in relaying messages
between channels on different networks, check out the Relay plugin.
"""

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import plugins

import re

import conf
import utils
import irclib
import ircmsgs
import privmsgs
import registry
import callbacks

class ValidChannelOrNothing(conf.ValidChannel):
    """Value must be either a valid IRC channel or the empty string."""
    def setValue(self, v):
        try:
            conf.ValidChannel.setValue(self, v)
        except registry.InvalidRegistryValue:
            registry.Value.setValue(self, '')
            
conf.registerPlugin('ChannelRelay')
conf.registerGlobalValue(conf.supybot.plugins.ChannelRelay, 'source',
    ValidChannelOrNothing('', """Determines the channel that the bot will look
    for messages to relay from.  Messages matching
    supybot.plugins.ChannelRelay.regexp will be relayed to the target channel
    specified by supybot.plugins.ChannelRelay.target."""))
conf.registerGlobalValue(conf.supybot.plugins.ChannelRelay, 'target',
    ValidChannelOrNothing('', """Determines the channel that the bot will send
    messages from the other channel.  Messages matching
    supybot.plugins.ChannelRelay.regexp will be relayed to this channel from
    the source channel."""))
conf.registerGlobalValue(conf.supybot.plugins.ChannelRelay, 'regexp',
    registry.Regexp(None, """Determines what regular expression
    should be matched against messages to determine whether they should be
    relayed from the source channel to the target channel.  By default, the
    value is m/./, which means that all non-empty messages will be
    relayed."""))
if conf.supybot.plugins.ChannelRelay.regexp() is None:
    conf.supybot.plugins.ChannelRelay.regexp.set('m/./')
conf.registerGlobalValue(conf.supybot.plugins.ChannelRelay, 'fancy',
    registry.Boolean(True, """Determines whether the bot should relay the
    messages in fancy form (i.e., including the nick of the sender of the
    messages) or non-fancy form (i.e., without the nick of the sender of the
    messages)."""))
conf.registerGlobalValue(conf.supybot.plugins.ChannelRelay, 'prefix',
    registry.String('', """Determines what prefix should be prepended to the
    relayed messages."""))

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn, output
    conf.registerPlugin('ChannelRelay', True)

class ChannelRelay(callbacks.Privmsg):
    def shouldRelay(self, msg):
        source = self.registryValue('source')
        if source:
            assert msg.command == 'PRIVMSG'
            return msg.args[0] == source and \
                   bool(self.registryValue('regexp').search(msg.args[1]))
        else:
            return False

    def doPrivmsg(self, irc, msg):
        if self.shouldRelay(msg):
            target = self.registryValue('target')
            if target and target in irc.state.channels:
                if self.registryValue('fancy'):
                    s = ircmsgs.prettyPrint(msg)
                else:
                    s = msg.args[1]
                s = self.registryValue('prefix') + s
                irc.queueMsg(ircmsgs.privmsg(target, s))
    
    def do376(self, irc, msg):
        source = self.registryValue('source')
        target = self.registryValue('target')
        if source and target:
            irc.queueMsg(ircmsgs.joins([source, target]))


Class = ChannelRelay

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
