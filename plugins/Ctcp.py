#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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
Handles standard CTCP responses to PING, TIME, SOURCE, VERSION, USERINFO, 
and FINGER.
"""

from baseplugin import *

import os
import sys
import time

sys.path.append(os.pardir)

import debug
import ircmsgs
import callbacks

notice = ircmsgs.notice

class Ctcp(callbacks.PrivmsgRegexp):
    public = False
    def ping(self, irc, msg, match):
        "\x01PING (.*)\x01"
        debug.msg('Received CTCP PING from %s' % msg.nick, 'normal')
        irc.queueMsg(notice(msg.nick, '\x01PING %s\x01' % match.group(1)))

    def version(self, irc, msg, match):
        "\x01VERSION\x01"
        debug.msg('Received CTCP VERSION from %s' % msg.nick, 'normal')
        s = '\x01VERSION SupyBot %s\x01' % world.version
        irc.queueMsg(notice(msg.nick, s))

    def userinfo(self, irc, msg, match):
        "\x01USERINFO\x01"
        debug.msg('Received CTCP USERINFO from %s' % msg.nick, 'normal')
        irc.queueMsg(notice(msg.nick, '\x01USERINFO\x01'))

    def time(self, irc, msg, match):
        "\x01TIME\x01"
        debug.msg('Received CTCP TIME from %s' % msg.nick, 'normal')
        irc.queueMsg(notice(msg.nick, '\x01%s\x01' % time.ctime()))

    def finger(self, irc, msg, match):
        "\x01FINGER\x01"
        debug.msg('Received CTCP FINGER from %s' % msg.nick, 'normal')
        s = '\x01SupyBot, the best Python bot in existence!\x01'
        irc.queueMsg(notice(msg.nick, s))

    def source(self, irc, msg, match):
        "\x01SOURCE\x01"
        debug.msg('Received CTCP SOURCE from %s' % msg.nick, 'normal')
        s = 'http://www.sourceforge.net/projects/supybot/'
        irc.queueMsg(notice(msg.nick, s))

Class = Ctcp
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
