#!/usr/bin/env python

###
# Copyright (c) 2002-2004, Jeremiah Fincher
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

import supybot.plugins as plugins

import os
import sys
import sets
import time
import os.path
import threading
from itertools import islice, ifilter, imap

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks

conf.registerPlugin('Status')
conf.registerGroup(conf.supybot.plugins.Status, 'cpu')
conf.registerChannelValue(conf.supybot.plugins.Status.cpu, 'children',
    registry.Boolean(True, """Determines whether the cpu command will list the
    time taken by children as well as the bot's process."""))
conf.registerChannelValue(conf.supybot.plugins.Status.cpu, 'threads',
    registry.Boolean(False, """Determines whether the cpu command will provide
    the number of threads spawned and active."""))
conf.registerChannelValue(conf.supybot.plugins.Status.cpu, 'memory',
    registry.Boolean(True, """Determines whether the cpu command will report
    the amount of memory being used by the bot."""))

class Status(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.sentMsgs = 0
        self.recvdMsgs = 0
        self.sentBytes = 0
        self.recvdBytes = 0
        self.connected = {}

    def __call__(self, irc, msg):
        self.recvdMsgs += 1
        self.recvdBytes += len(msg)
        callbacks.Privmsg.__call__(self, irc, msg)

    def outFilter(self, irc, msg):
        self.sentMsgs += 1
        self.sentBytes += len(msg)
        return msg

    def do001(self, irc, msg):
        self.connected[irc] = time.time()

    def status(self, irc, msg, args):
        """takes no arguments

        Returns the status of the bot.
        """
        networks = {}
        for Irc in world.ircs:
            networks.setdefault(Irc.network, []).append(Irc.nick)
        networks = networks.items()
        networks.sort()
        networks = ['%s as %s' % (net, utils.commaAndify(nicks))
                    for (net, nicks) in networks]
        L = ['I am connected to %s.' % utils.commaAndify(networks)]
        if world.profiling:
            L.append('I am currently in code profiling mode.')
        irc.reply('  '.join(L))

    def threads(self, irc, msg, args):
        """takes no arguments

        Returns the current threads that are active.
        """
        threads = [t.getName() for t in threading.enumerate()]
        threads.sort()
        s = 'I have spawned %s; %s %s still currently active: %s.' % \
            (utils.nItems('thread', world.threadsSpawned),
             utils.nItems('thread', len(threads)), utils.be(len(threads)),
             utils.commaAndify(threads))
        irc.reply(s)

    def net(self, irc, msg, args):
        """takes no arguments

        Returns some interesting network-related statistics.
        """
        try:
            elapsed = time.time() - self.connected[irc.getRealIrc()]
            timeElapsed = utils.timeElapsed(elapsed)
        except KeyError:
            timeElapsed = 'an indeterminate amount of time'
        irc.reply('I have received %s messages for a total of %s bytes.  '
                  'I have sent %s messages for a total of %s bytes.  '
                  'I have been connected to %s for %s.' %
                  (self.recvdMsgs, self.recvdBytes,
                   self.sentMsgs, self.sentBytes, irc.server, timeElapsed))

    def cpu(self, irc, msg, args):
        """takes no arguments

        Returns some interesting CPU-related statistics on the bot.
        """
        (user, system, childUser, childSystem, elapsed) = os.times()
        now = time.time()
        target = msg.args[0]
        timeRunning = now - world.startedAt
        if self.registryValue('cpu.children', target) and \
           user+system < timeRunning+1: # Fudge for FPU inaccuracies.
            children = 'My children have taken %.2f seconds of user time ' \
                       'and %.2f seconds of system time ' \
                       'for a total of %.2f seconds of CPU time.  ' % \
                       (childUser, childSystem, childUser+childSystem)
        else:
            children = ''
        activeThreads = threading.activeCount()
        response = 'I have taken %.2f seconds of user time and %.2f seconds ' \
                   'of system time, for a total of %.2f seconds of CPU ' \
                   'time.  %s' % (user, system, user + system, children)
        if self.registryValue('cpu.threads', target):
            spawned = utils.nItems('thread', world.threadsSpawned)
            response += 'I have spawned %s; I currently have %s still ' \
                        'running.' % (spawned, activeThreads)
        if self.registryValue('cpu.memory', target):
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
                    mem = '%s kB' % os.stat('/proc/%s/mem' % pid)[7]
                response += '  I\'m taking up %s kB of memory.' % mem
            except Exception:
                self.log.exception('Uncaught exception in cpu.memory:')
        irc.reply(utils.normalizeWhitespace(response))

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

    def logfile(self, irc, msg, args):
        """[<logfile>]

        Returns the size of the various logfiles in use.  If given a specific
        logfile, returns only the size of that logfile.
        """
        filenameArg = privmsgs.getArgs(args, required=0, optional=1)
        if filenameArg:
            if not filenameArg.endswith('.log'):
                irc.error('That filename doesn\'t appear to be a log.')
                return
            filenameArg = os.path.basename(filenameArg)
        ret = []
        dirname = conf.supybot.directories.log()
        for (dirname,_,filenames) in os.walk(dirname):
            if filenameArg:
                if filenameArg in filenames:
                    filename = os.path.join(dirname, filenameArg)
                    stats = os.stat(filename)
                    ret.append('%s: %s' % (filename, stats.st_size))
            else:
                for filename in filenames:
                    stats = os.stat(os.path.join(dirname, filename))
                    ret.append('%s: %s' % (filename, stats.st_size))
        if ret:
            ret.sort()
            irc.reply(utils.commaAndify(ret))
        else:
            irc.error('I couldn\'t find any logfiles.')


Class = Status

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
