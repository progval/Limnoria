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
Gives the user the ability to schedule commands to run at a particular time,
or repeatedly run at a particular interval.
"""

import plugins

import time

import conf
import utils
import privmsgs
import schedule
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Scheduler')


class Scheduler(callbacks.Privmsg):
    def _makeCommandFunction(self, irc, msg, command):
        """Makes a function suitable for scheduling from command."""
        tokens = callbacks.tokenize(command)
        Owner = irc.getCallback('Owner')
        ambiguous = Owner.disambiguate(irc, tokens)
        if ambiguous:
            raise callbacks.Error, callbacks.ambiguousReply(ambiguous)
        def f():
            self.Proxy(irc.irc, msg, tokens)
        return f

    def add(self, irc, msg, args):
        """<seconds> <command>

        Schedules the command string <command> to run <seconds> seconds in the
        future.  For example, 'schedule add [seconds 30m] "echo [cpu]"' will
        schedule the command "cpu" to be sent to the channel the schedule add
        command was given in (with no prefixed nick, a consequence of using
        echo).
        """
        (seconds, command) = privmsgs.getArgs(args, required=2)
        try:
            seconds = int(seconds)
        except ValueError:
            irc.error(msg, 'Invalid seconds value: %r' % seconds)
            return
        f = self._makeCommandFunction(irc, msg, command)
        id = schedule.addEvent(f, time.time() + seconds)
        irc.reply(msg, '%s  Event #%s added.' % (conf.replySuccess, id))

    def remove(self, irc, msg, args):
        """<id>

        Removes the event scheduled with id <id> from the schedule.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            pass
        try:
            schedule.removeEvent(id)
            irc.reply(msg, conf.replySuccess)
        except KeyError:
            irc.error(msg, 'Invalid event id.')

    def repeat(self, irc, msg, args):
        """<name> <seconds> <command>

        Schedules the command <command> to run every <seconds> seconds,
        starting now (i.e., the command runs now, and every <seconds> seconds
        thereafter).  <name> is a name by which the command can be
        unscheduled.
        """
        (name, seconds, command) = privmsgs.getArgs(args, required=3)
        try:
            seconds = int(seconds)
        except ValueError:
            irc.error(msg, 'Invalid seconds: %r' % seconds)
            return
        f = self._makeCommandFunction(irc, msg, command)
        id = schedule.addPeriodicEvent(f, seconds, name)
        # We don't reply because the command runs immediately.
        # irc.reply(msg, conf.replySuccess)


Class = Scheduler

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
