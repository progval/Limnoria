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
A simple module to handle various informational commands querying the bot's
current status and statistics.
"""
__revision__ = "$Id$"

import plugins

import os
import sys
import sets
import time
import threading
from itertools import islice, ifilter, imap

import conf
import utils
import world
import privmsgs
import callbacks


class Status(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.sentMsgs = 0
        self.recvdMsgs = 0
        self.sentBytes = 0
        self.recvdBytes = 0

    def __call__(self, irc, msg):
        self.recvdMsgs += 1
        self.recvdBytes += len(msg)
        callbacks.Privmsg.__call__(self, irc, msg)

    def outFilter(self, irc, msg):
        self.sentMsgs += 1
        self.sentBytes += len(msg)
        return msg

    def net(self, irc, msg, args):
        """takes no arguments

        Returns some interesting network-related statistics.
        """
        irc.reply('I have received %s messages for a total of %s bytes.  '
                  'I have sent %s messages for a total of %s bytes.' %
                  (self.recvdMsgs, self.recvdBytes,
                   self.sentMsgs, self.sentBytes))

    def cpu(self, irc, msg, args):
        """takes no arguments

        Returns some interesting CPU-related statistics on the bot.
        """
        (user, system, childUser, childSystem, elapsed) = os.times()
        now = time.time()
        timeRunning = now - world.startedAt
        if user+system < timeRunning+1: # Fudge for FPU inaccuracies.
            children = 'My children have taken %.2f seconds of user time ' \
                       'and %.2f seconds of system time ' \
                       'for a total of %.2f seconds of CPU time.  ' % \
                       (childUser, childSystem, childUser+childSystem)
        else:
            children = ''
        activeThreads = threading.activeCount()
        response = ('I have taken %.2f seconds of user time and %.2f seconds '
                    'of system time, for a total of %.2f seconds of CPU '
                    'time.  %s'
                    'I have spawned %s; I currently have %s still running.' % 
                    (user, system, user + system, children,
                     utils.nItems('thread', world.threadsSpawned),
                     activeThreads))
        mem = 'an unknown amount'
        pid = os.getpid()
        plat = sys.platform
        try:
            if plat.startswith('linux') or plat.startswith('sunos') or \
               plat.startswith('freebsd') or plat.startswith('openbsd') or \
               plat.startswith('darwin'):
                try:
                    r = os.popen('ps -o rss -p %s' % pid)
                    r.readline() # VSZ Header.
                    mem = r.readline().strip()
                finally:
                    r.close()
            elif sys.platform.startswith('netbsd'):
                mem = '%s kB' % os.stat('/proc/%s/mem')[7]
            response += '  I\'m taking up %s kB of memory.' % mem
        except Exception:
            self.log.exception('Uncaught exception in cpu:')
        irc.reply(response)

    def cmd(self, irc, msg, args):
        """takes no arguments

        Returns some interesting command-related statistics.
        """
        commands = 0
        callbacksPrivmsg = 0
        for cb in irc.callbacks:
            if isinstance(cb, callbacks.Privmsg) and cb.public:
                if not isinstance(cb, callbacks.PrivmsgRegexp):
                    callbacksPrivmsg += 1
                for attr in dir(cb):
                    if cb.isCommand(attr) and \
                       attr == callbacks.canonicalName(attr):
                        commands += 1
        s = 'I offer a total of %s in %s.  I have processed %s.' % \
            (utils.nItems('command', commands),
             utils.nItems('plugin', callbacksPrivmsg, 'command-based'),
             utils.nItems('command', world.commandsProcessed))
        irc.reply(s)

    def commands(self, irc, msg, args):
        """takes no arguments

        Returns a list of the commands offered by the bot.
        """
        commands = sets.Set()
        for cb in irc.callbacks:
            if isinstance(cb, callbacks.Privmsg) and \
               not isinstance(cb, callbacks.PrivmsgRegexp) and cb.public:
                for attr in dir(cb):
                    if cb.isCommand(attr) and \
                       attr == callbacks.canonicalName(attr):
                        commands.add(attr)
        commands = list(commands)
        commands.sort()
        irc.reply(utils.commaAndify(commands))

    def uptime(self, irc, msg, args):
        """takes no arguments

        Returns the amount of time the bot has been running.
        """
        response = 'I have been running for %s.' % \
                   utils.timeElapsed(time.time() - world.startedAt)
        irc.reply(response)

    def server(self, irc, msg, args):
        """takes no arguments

        Returns the server the bot is on.
        """
        irc.reply(irc.server)


Class = Status

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
