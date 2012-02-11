###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009, James Vega
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

import os
import sys
import time
import threading
import subprocess

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Status')

class Status(callbacks.Plugin):
    def __init__(self, irc):
        self.__parent = super(Status, self)
        self.__parent.__init__(irc)
        # XXX It'd be nice if these could be kept in the registry.
        self.sentMsgs = 0
        self.recvdMsgs = 0
        self.sentBytes = 0
        self.recvdBytes = 0
        self.connected = {}

    def __call__(self, irc, msg):
        self.recvdMsgs += 1
        self.recvdBytes += len(msg)
        self.__parent.__call__(irc, msg)

    def outFilter(self, irc, msg):
        self.sentMsgs += 1
        self.sentBytes += len(msg)
        return msg

    def do001(self, irc, msg):
        self.connected[irc] = time.time()

    @internationalizeDocstring
    def status(self, irc, msg, args):
        """takes no arguments

        Returns the status of the bot.
        """
        networks = {}
        for Irc in world.ircs:
            networks.setdefault(Irc.network, []).append(Irc.nick)
        networks = networks.items()
        networks.sort()
        networks = [format(_('%s as %L'), net, nicks) for (net,nicks) in networks]
        L = [format(_('I am connected to %L.'), networks)]
        if world.profiling:
            L.append(_('I am currently in code profiling mode.'))
        irc.reply('  '.join(L))
    status = wrap(status)

    @internationalizeDocstring
    def threads(self, irc, msg, args):
        """takes no arguments

        Returns the current threads that are active.
        """
        threads = [t.getName() for t in threading.enumerate()]
        threads.sort()
        s = format(_('I have spawned %n; %n %b still currently active: %L.'),
                   (world.threadsSpawned, 'thread'),
                   (len(threads), 'thread'), len(threads), threads)
        irc.reply(s)
    threads = wrap(threads)

    @internationalizeDocstring
    def net(self, irc, msg, args):
        """takes no arguments

        Returns some interesting network-related statistics.
        """
        try:
            elapsed = time.time() - self.connected[irc.getRealIrc()]
            timeElapsed = utils.timeElapsed(elapsed)
        except KeyError:
            timeElapsed = _('an indeterminate amount of time')
        irc.reply(format(_('I have received %s messages for a total of %S.  '
                  'I have sent %s messages for a total of %S.  '
                  'I have been connected to %s for %s.'),
                  self.recvdMsgs, self.recvdBytes,
                  self.sentMsgs, self.sentBytes, irc.server, timeElapsed))
    net = wrap(net)

    @internationalizeDocstring
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
            children = _('My children have taken %.2f seconds of user time '
                       'and %.2f seconds of system time '
                       'for a total of %.2f seconds of CPU time.') % \
                       (childUser, childSystem, childUser+childSystem)
        else:
            children = ''
        activeThreads = threading.activeCount()
        response = _('I have taken %.2f seconds of user time and %.2f seconds '
                   'of system time, for a total of %.2f seconds of CPU '
                   'time.  %s') % (user, system, user + system, children)
        if self.registryValue('cpu.threads', target):
            response += format('I have spawned %n; I currently have %i still '
                               'running.',
                               (world.threadsSpawned, 'thread'), activeThreads)
        if self.registryValue('cpu.memory', target):
            mem = 'an unknown amount'
            pid = os.getpid()
            plat = sys.platform
            try:
                if plat.startswith('linux') or plat.startswith('sunos') or \
                   plat.startswith('freebsd') or plat.startswith('openbsd') or \
                   plat.startswith('darwin'):
                    cmd = 'ps -o rss -p %s' % pid
                    try:
                        inst = subprocess.Popen(cmd.split(), close_fds=True,
                                                stdin=file(os.devnull),
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)
                    except OSError:
                        irc.error(_('Unable to run ps command.'), Raise=True)
                    (out, foo) = inst.communicate()
                    inst.wait()
                    mem = int(out.splitlines()[1])
                elif sys.platform.startswith('netbsd'):
                    mem = int(os.stat('/proc/%s/mem' % pid)[7])
                response += format(_('  I\'m taking up %S of memory.'),
                        mem*1024)
            except Exception:
                self.log.exception('Uncaught exception in cpu.memory:')
        irc.reply(utils.str.normalizeWhitespace(response))
    cpu = wrap(cpu)

    @internationalizeDocstring
    def cmd(self, irc, msg, args):
        """takes no arguments

        Returns some interesting command-related statistics.
        """
        commands = 0
        callbacksPlugin = 0
        for cb in irc.callbacks:
            if isinstance(cb, callbacks.Plugin):
                callbacksPlugin += 1
                commands += len(cb.listCommands())
        s = format(_('I offer a total of %n in %n.  I have processed %n.'),
                   (commands, 'command'),
                   (callbacksPlugin, 'command-based', 'plugin'),
                   (world.commandsProcessed, 'command'))
        irc.reply(s)
    cmd = wrap(cmd)

    @internationalizeDocstring
    def commands(self, irc, msg, args):
        """takes no arguments

        Returns a list of the commands offered by the bot.
        """
        commands = set()
        for cb in irc.callbacks:
            if isinstance(cb, callbacks.Plugin):
                for command in cb.listCommands():
                    commands.add(command)
        irc.reply(format('%L', sorted(commands)))
    commands = wrap(commands)

    @internationalizeDocstring
    def uptime(self, irc, msg, args):
        """takes no arguments

        Returns the amount of time the bot has been running.
        """
        response = _('I have been running for %s.') % \
                   utils.timeElapsed(time.time() - world.startedAt)
        irc.reply(response)
    uptime = wrap(uptime)

    @internationalizeDocstring
    def server(self, irc, msg, args):
        """takes no arguments

        Returns the server the bot is on.
        """
        irc.reply(irc.server)
    server = wrap(server)


Class = Status

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
