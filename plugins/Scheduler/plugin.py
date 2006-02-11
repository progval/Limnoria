###
# Copyright (c) 2003-2004, Jeremiah Fincher
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

import time

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.schedule as schedule
import supybot.callbacks as callbacks

class Scheduler(callbacks.Plugin):
    def __init__(self, irc):
        self.__parent = super(Scheduler, self)
        self.__parent.__init__(irc)
        self.events = {}

    def _makeCommandFunction(self, irc, msg, command, remove=True):
        """Makes a function suitable for scheduling from command."""
        tokens = callbacks.tokenize(command)
        def f():
            if remove:
                del self.events[str(f.eventId)]
            self.Proxy(irc.irc, msg, tokens)
        return f

    def add(self, irc, msg, args, seconds, command):
        """<seconds> <command>

        Schedules the command string <command> to run <seconds> seconds in the
        future.  For example, 'scheduler add [seconds 30m] "echo [cpu]"' will
        schedule the command "cpu" to be sent to the channel the schedule add
        command was given in (with no prefixed nick, a consequence of using
        echo).  Do pay attention to the quotes in that example.
        """
        f = self._makeCommandFunction(irc, msg, command)
        id = schedule.addEvent(f, time.time() + seconds)
        f.eventId = id
        self.events[str(id)] = command
        irc.replySuccess(format('Event #%i added.', id))
    add = wrap(add, ['positiveInt', 'text'])

    def remove(self, irc, msg, args, id):
        """<id>

        Removes the event scheduled with id <id> from the schedule.
        """
        if id in self.events:
            del self.events[id]
            try:
                id = int(id)
            except ValueError:
                pass
            try:
                schedule.removeEvent(id)
                irc.replySuccess()
            except KeyError:
                irc.error('Invalid event id.')
        else:
            irc.error('Invalid event id.')
    remove = wrap(remove, ['lowered'])

    def repeat(self, irc, msg, args, name, seconds, command):
        """<name> <seconds> <command>

        Schedules the command <command> to run every <seconds> seconds,
        starting now (i.e., the command runs now, and every <seconds> seconds
        thereafter).  <name> is a name by which the command can be
        unscheduled.
        """
        name = name.lower()
        if name in self.events:
            irc.error('There is already an event with that name, please '
                      'choose another name.', Raise=True)
        self.events[name] = command
        f = self._makeCommandFunction(irc, msg, command, remove=False)
        id = schedule.addPeriodicEvent(f, seconds, name)
        assert id == name
        # We don't reply because the command runs immediately.
        # But should we?  What if the command doesn't have visible output?
        # irc.replySuccess()
    repeat = wrap(repeat, ['nonInt', 'positiveInt', 'text'])

    def list(self, irc, msg, args):
        """takes no arguments

        Lists the currently scheduled events.
        """
        L = self.events.items()
        if L:
            L.sort()
            for (i, (name, command)) in enumerate(L):
                L[i] = format('%s: %q', name, command)
            irc.reply(format('%L', L))
        else:
            irc.reply('There are currently no scheduled commands.')
    list = wrap(list)


Class = Scheduler

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
