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
Used to send periodic messages to IRC, which sometimes helps with network lag.
Really, we only have this because MozBot has this, and it was easy for jemfinch
to write.  It also shows how much better our plugin interface and configuration
API is.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jemfinch

import supybot.plugins as plugins

import time

import supybot.log as log
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
    conf.registerPlugin('KeepAlive', True)

conf.registerPlugin('KeepAlive', True)
conf.registerGlobalValue(conf.supybot.plugins.KeepAlive, 'period',
    registry.PositiveInteger(300, """Determines how long (in seconds) the
    plugin should wait between sending keepalive messages."""))
conf.registerGlobalValue(conf.supybot.plugins.KeepAlive, 'target',
    registry.String('', """Determines who (or what channel) the bot will send
    its keepalive messages to."""))
conf.registerGlobalValue(conf.supybot.plugins.KeepAlive, 'notice',
    registry.Boolean(True, """Determines whether the bot will send its
    keepalive messages as NOTICEs.  This defaults to True because according to
    the IRC protocol, NOTICEs are not allowed to evoke automated responses, so
    this is slightly superior to a PRIVMSG."""))

class KeepAlive(callbacks.Privmsg):
    def __init__(self):
        self.keepaliveId = 0
        self.lastKeepalive = time.time()
        callbacks.Privmsg.__init__(self)
        
    def __call__(self, irc, msg):
        period = self.registryValue('period')
        if irc.afterConnect:
            now = time.time()
            if now - self.lastKeepalive > period:
                self.lastKeepalive = now
                target = self.registryValue('target')
                if not target:
                    return
                if self.registryValue('notice'):
                    maker = ircmsgs.notice
                else:
                    maker = ircmsgs.privmsg
                self.keepaliveId += 1
                m = maker(target, 'Keepalive message #%s.' % self.keepaliveId)
                irc.queueMsg(m)
                self.log.info('Sent keepalive message #%s at %s.',
                              self.keepaliveId, log.timestamp(now))
                


Class = KeepAlive

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
