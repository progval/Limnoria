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
import plugins

import os
import sys
import sets
import time
import threading
from itertools import islice, ifilter

import conf
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

class UptimeDB(object):
    def __init__(self, filename='uptimes'):
        self.filename = os.path.join(conf.dataDir, filename)
        if os.path.exists(self.filename):
            fd = file(self.filename)
            s = fd.read()
            fd.close()
            s = s.replace('\n', ' ')
            self.uptimes = eval(s)
        else:
            self.uptimes = []

    def die(self):
        fd = file(self.filename, 'w')
        fd.write(repr(self.top(50)))
        fd.write('\n')
        fd.close()

    def add(self):
        if not any(lambda t: t[0] == world.startedAt, self.uptimes):
            self.uptimes.append((world.startedAt, None))

    def top(self, n=3):
        def decorator(t):
            if t[1] is None:
                return 0.0
            else:
                t[1] - t[0]
        def invertCmp(cmp):
            def f(x, y):
                return -cmp(x, y)
            return f
        def notNone(t):
            return t[1] is not None
        utils.sortBy(decorator, self.uptimes, cmp=invertCmp(cmp))
        return list(islice(ifilter(notNone, self.uptimes), 3))

    def update(self):
        for (i, t) in enumerate(self.uptimes):
            if t[0] == world.startedAt:
                self.uptimes[i] = (t[0], time.time())
        

class Status(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.sentMsgs = 0
        self.recvdMsgs = 0
        self.sentBytes = 0
        self.recvdBytes = 0
        self.uptimes = UptimeDB()
        self.uptimes.add()

    def inFilter(self, irc, msg):
        self.uptimes.update()
        self.recvdMsgs += 1
        self.recvdBytes += len(msg)
        return msg

    def outFilter(self, irc, msg):
        self.sentMsgs += 1
        self.sentBytes += len(msg)
        return msg

    def die(self):
        self.uptimes.update()
        self.uptimes.die()

    def bestuptime(self, irc, msg, args):
        """takes no arguments

        Returns the highest uptimes attained by the bot.
        """
        L = self.uptimes.top()
        if not L:
            irc.error(msg, 'I don\'t have enough data to answer that.')
            return
        def format((started, ended)):
            return '%s until %s; up for %s' % \
                   (time.strftime(conf.humanTimestampFormat,
                                  time.localtime(started)),
                    time.strftime(conf.humanTimestampFormat,
                                  time.localtime(ended)),
                    utils.timeElapsed(ended-started))
        L = map(format, L)
        irc.reply(msg, utils.commaAndify(L))

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
        now = time.time()
        timeRunning = now - world.startedAt
        if user+system > timeRunning:
            irc.error(msg, 'I seem to be running on a platform without an '
                           'accurate way of determining how long I\'ve been '
                           'running.')
            return
        activeThreads = threading.activeCount()
        response = 'I have taken %s seconds of user time and %s seconds of '\
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
            (utils.nItems(commands, 'command'),
             utils.nItems(callbacksPrivmsg, 'plugin', 'command-based'),
             utils.nItems(world.commandsProcessed, 'command'))
        irc.reply(msg, s)

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
        irc.reply(msg, utils.commaAndify(commands))

    def uptime(self, irc, msg, args):
        """takes no arguments.

        Returns the amount of time the bot has been running.
        """
        response = 'I have been running for %s.' % \
                   utils.timeElapsed(time.time() - world.startedAt)
        irc.reply(msg, response)


Class = Status

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
