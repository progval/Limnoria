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
Removes all bold output by the bot.
"""

__revision__ = "$Id$"

import plugins

import re

import ircmsgs
import callbacks


def configure(onStart):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    conf.registerPlugin('KillBold', True)

# For some stupid reason, this doesn't work.
## boldre = re.compile('(?:\x02([^\x02\x03\x0f]*\x03))|'
##                     '(?:\x02([^\x02\x0f]*)(?:[\x02\x0f]|$))')
boldre1 = re.compile('(?:\x02([^\x02\x03\x0f]*\x03))')
boldre2 = re.compile('(?:\x02([^\x02\x0f]*)(?:[\x02\x0f]|$))')

class KillBold(callbacks.Privmsg):
    priority = 10
    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            s = boldre1.sub(r'\1', msg.args[1])
            s = boldre2.sub(r'\1', s)
            return ircmsgs.privmsg(msg.args[0], s)
        else:
            return msg

Class = KillBold

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
