#!/usr/bin/env python

###
# Copyright (c) 2003, Jeremiah Fincher
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
Gives the user the ability to schedule commands to run at a particular time,
or repeatedly run at a particular interval.
"""

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import supybot.plugins as plugins

import sets
import time

import supybot.conf as conf
import supybot.utils as utils
import supybot.privmsgs as privmsgs
import supybot.schedule as schedule
import supybot.callbacks as callbacks


class Scheduler(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.events = {}

    def _makeCommandFunction(self, irc, msg, command, remove=True):
        """Makes a function suitable for scheduling from command."""
        tokens = callbacks.tokenize(command)
        Owner = irc.getCallback('Owner')
        ambiguous = Owner.disambiguate(irc, tokens)
        if ambiguous:
            raise callbacks.Error, callbacks.ambiguousReply(ambiguous)
        def f():
            if remove:
                del self.events[str(f.eventId)]
            self.Proxy(irc.irc, msg, tokens)
        return f

    def add(self, irc, msg, args):
        """<seconds> <command>

        Schedules the command string <command> to run <seconds> seconds in the
        future.  For example, 'scheduler add [seconds 30m] "echo [cpu]"' will
        schedule the command "cpu" to be sent to the channel the schedule add
        command was given in (with no prefixed nick, a consequence of using
        echo).
        """
        (seconds, command) = privmsgs.getArgs(args, required=2)
        try:
            seconds = int(seconds)
        except ValueError:
            irc.error('Invalid seconds value: %r' % seconds)
            return
        f = self._makeCommandFunction(irc, msg, command)
        id = schedule.addEvent(f, time.time() + seconds)
        f.eventId = id
        self.events[str(id)] = command
        irc.replySuccess('Event #%s added.' % id)

    def remove(self, irc, msg, args):
        """<id>

        Removes the event scheduled with id <id> from the schedule.
        """
        id = privmsgs.getArgs(args)
        id = id.lower()
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

    def repeat(self, irc, msg, args):
        """<name> <seconds> <command>

        Schedules the command <command> to run every <seconds> seconds,
        starting now (i.e., the command runs now, and every <seconds> seconds
        thereafter).  <name> is a name by which the command can be
        unscheduled.
        """
        (name, seconds, command) = privmsgs.getArgs(args, required=3)
        name = name.lower()
        try:
            seconds = int(seconds)
        except ValueError:
            irc.error('Invalid seconds: %r' % seconds)
            return
        try:
            name = int(name)
            irc.error('Names must not be an integer.')
            return
        except ValueError:
            pass
        self.events[name] = command
        f = self._makeCommandFunction(irc, msg, command, remove=False)
        id = schedule.addPeriodicEvent(f, seconds, name)
        assert id == name
        # We don't reply because the command runs immediately.
        # But should we?  What if the command doesn't have visible output?
        # irc.replySuccess()

    def list(self, irc, msg, args):
        """takes no arguments

        Lists the currently scheduled events.
        """
        L = self.events.items()
        if L:
            L.sort()
            for (i, (name, command)) in enumerate(L):
                L[i] = '%s: %s' % (name, utils.dqrepr(command))
            irc.reply(utils.commaAndify(L))
        else:
            irc.reply('There are currently no scheduled commands.')


Class = Scheduler

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
