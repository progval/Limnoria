#!/usr/bin/python

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
A simple module to handle various informational commands querying the bot's
current status and statistics.
"""
from baseplugin import *

import os

import utils
import world
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Status')

example = utils.wrapLines("""
Add an example IRC session using this module here.
""")

class Status(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.sentMsgs = 0
        self.recvdMsgs = 0
        self.sentBytes = 0
        self.recvdBytes = 0

    def inFilter(self, irc, msg):
        self.recvdMsgs += 1
        self.recvdBytes += len(str(msg))
        return msg

    def outFilter(self, irc, msg):
        self.sentMsgs += 1
        self.sentBytes += len(str(msg))
        return msg

    def netstats(self, irc, msg, args):
        """takes no arguments

        Returns some interesting network-related statistics.
        """
        irc.reply(msg,
                   'I have received %s messages for a total of %s bytes.  '\
                   'I have sent %s messages for a total of %s bytes.' %\
                   (self.recvdMsgs, self.recvdBytes,
                    self.sentMsgs, self.sentBytes))

    def cpustats(self, irc, msg, args):
        """takes no arguments

        Returns some interesting CPU-related statistics on the bot.
        """
        (user, system, childUser, childSystem, elapsed) = os.times()
        timeRunning = time.time() - world.startedAt
        activeThreads = threading.activeCount()
        response ='I have taken %s seconds of user time and %s seconds of '\
                  'system time, for a total of %s seconds of CPU time.  My '\
                  'children have taken %s seconds of user time and %s seconds'\
                  ' of system time for a total of %s seconds of CPU time.  ' \
                  'I\'ve taken a total of %s%% of this computer\'s time.  ' \
                  'Out of %s I have %s active.  ' % \
                    (user, system, user + system,
                     childUser, childSystem, childUser + childSystem,
                     (user+system+childUser+childSystem)/timeRunning,
                     utils.nItems(world.threadsSpawned, 'thread', 'spawned'),
                     activeThreads)
        irc.reply(msg, response)

    def cmdstats(self, irc, msg, args):
        """takes no arguments

        Returns some interesting command-related statistics.
        """
        commands = sets.Set()
        callbacksPrivmsgs = 0
        for cb in irc.callbacks:
            if isinstance(cb, callbacks.Privmsg) and cb.public:
                callbacksPrivmsgs += 1
                for attr in dir(cb):
                    if cb.isCommand(attr):
                        commands.add(attr)
        commands = list(commands)
        commands.sort()
        s = 'I offer a total of %s in %s.  ' \
            'I have processed %s.  My public commands include %s.' % \
            (utils.nItems(len(commands), 'command'),
             utils.nItems(callbacksPrivmsgs, 'plugin', 'command-based'),
             utils.nItems(world.commandsProcessed, 'command'),
             utils.commaAndify(commands))
        irc.reply(msg, s)

    def uptime(self, irc, msg, args):
        """takes no arguments.

        Returns the amount of time the bot has been running.
        """
        response = 'I have been running for %s.' % \
                   utils.timeElapsed(time.time() - world.startedAt)
        irc.reply(msg, response)


Class = Status

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
