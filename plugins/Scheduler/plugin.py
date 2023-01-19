###
# Copyright (c) 2003-2004, Jeremiah Fincher
# Copyright (c) 2010-2021, Valentin Lorentz
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
import os
import math
import shutil
import tempfile

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.schedule as schedule
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization('Scheduler')
import supybot.world as world

import supybot.utils.minisix as minisix
pickle = minisix.pickle

datadir = conf.supybot.directories.data()
filename = conf.supybot.directories.data.dirize('Scheduler.pickle')

class Scheduler(callbacks.Plugin):
    """This plugin allows you to schedule commands to execute at a later time."""
    def __init__(self, irc):
        self.__parent = super(Scheduler, self)
        self.__parent.__init__(irc)
        self.events = {}
        self._restoreEvents(irc)
        world.flushers.append(self._flush)

    def _getNextRunIn(self, first_run, now, period, not_right_now=False):
        next_run_in = period - ((now - first_run) % period)
        if not_right_now and next_run_in < 5:
            # don't run immediatly, it might overwhelm the bot on
            # startup.
            next_run_in += period
        return next_run_in

    def _restoreEvents(self, irc):
        try:
            pkl = open(filename, 'rb')
            try:
                eventdict = pickle.load(pkl)
            except Exception as e:
                self.log.debug('Unable to load pickled data: %s', e)
                return
            finally:
                pkl.close()
        except IOError as e:
            self.log.debug('Unable to open pickle file: %s', e)
            return
        for name, event in eventdict.items():
            # old DBs don't have the "network", let's take the current network
            # instead.
            network = event.get('network', irc.network)
            try:
                if event['type'] == 'single': # non-repeating event
                    n = None
                    if schedule.schedule.counter > int(name):
                        # counter not reset, we're probably reloading the plugin
                        # though we'll never know for sure, because other
                        # plugins can schedule stuff, too.
                        n = int(name)
                    # Here we use event.get() method instead of event[]
                    # This is to maintain compatibility with older bots
                    # lacking 'is_reminder' in their event dicts
                    is_reminder = event.get('is_reminder', False)
                    self._add(network, event['msg'], event['time'], event['command'],
                              is_reminder, n)
                elif event['type'] == 'repeat': # repeating event
                    now = time.time()
                    first_run = event.get('first_run')
                    if first_run is None:
                        # old DBs don't have a "first_run"; let's take "now" as
                        # first_run.
                        first_run = now

                    # Preserve the offset over restarts; eg. if event['time']
                    # is 24hours, we want to keep running the command at the
                    # same time of day.
                    next_run_in = self._getNextRunIn(
                        first_run, now, event['time'], not_right_now=True)

                    self._repeat(network, event['msg'], name,
                                 event['time'], event['command'], first_run, next_run_in)
            except AssertionError as e:
                if str(e) == 'An event with the same name has already been scheduled.':
                    # we must be reloading the plugin, event is still scheduled
                    self.log.info('Event %s already exists, adding to dict.', name)
                    self.events[name] = event
                else:
                    raise

    def _flush(self):
        try:
            pklfd, tempfn = tempfile.mkstemp(suffix='scheduler', dir=datadir)
            pkl = os.fdopen(pklfd, 'wb')
            try:
                pickle.dump(self.events, pkl)
            except Exception as e:
                self.log.warning('Unable to store pickled data: %s', e)
            pkl.close()
            shutil.move(tempfn, filename)
        except (IOError, shutil.Error) as e:
            self.log.warning('File error: %s', e)

    def die(self):
        self._flush()
        world.flushers.remove(self._flush)
        self.__parent.die()

    def _makeCommandFunction(self, network, msg, command, remove=True):
        """Makes a function suitable for scheduling from command."""
        def f():
            # If the network isn't available, pick any other one
            irc = world.getIrc(network) or world.ircs[0]
            tokens = callbacks.tokenize(command,
                channel=msg.channel, network=irc.network)
            if remove:
                del self.events[str(f.eventId)]

            # A previous run of the command may have set 'ignored' to True,
            # causing this run to not include response from nested commands;
            # as NestedCommandsIrcProxy.reply() would confuse it with the
            # subcommand setting 'ignored' to True itself.
            msg.tag('ignored', False)

            self.Proxy(irc, msg, tokens)
        return f

    def _makeReminderFunction(self, network, msg, text):
        """Makes a function suitable for scheduling text"""
        def f():
            # If the network isn't available, pick any other one
            irc = world.getIrc(network) or world.ircs[0]
            replyIrc = callbacks.ReplyIrcProxy(irc, msg)
            replyIrc.reply(_('Reminder: %s') % text, msg=msg, prefixNick=True)
            del self.events[str(f.eventId)]
        return f

    def _add(self, network, msg, t, command, is_reminder=False, name=None):
        if is_reminder:
            f = self._makeReminderFunction(network, msg, command)
        else:
            f = self._makeCommandFunction(network, msg, command)
        id = schedule.addEvent(f, t, name)
        f.eventId = id
        self.events[str(id)] = {'command':command,
                                'is_reminder':is_reminder,
                                'msg':msg,
                                'network':network,
                                'time':t,
                                'type':'single'}
        return id

    @internationalizeDocstring
    def add(self, irc, msg, args, seconds, command):
        """<seconds> <command>

        Schedules the command string <command> to run <seconds> seconds in the
        future.  For example, 'scheduler add [seconds 30m] "echo [cpu]"' will
        schedule the command "cpu" to be sent to the channel the schedule add
        command was given in (with no prefixed nick, a consequence of using
        echo).  Do pay attention to the quotes in that example.
        """
        t = time.time() + seconds
        id = self._add(irc.network, msg, t, command)
        irc.replySuccess(format(_('Event #%i added.'), id))
    add = wrap(add, ['positiveInt', 'text'])

    @internationalizeDocstring
    def remind(self, irc, msg, args, seconds, text):
        """ <seconds> <text>

        Sets a reminder with string <text> to run <seconds> seconds in the
        future. For example, 'scheduler remind [seconds 30m] "Hello World"'
        will return '<nick> Reminder: Hello World' 30 minutes after being set.
        """
        t = time.time() + seconds
        id = self._add(irc.network, msg, t, text, is_reminder=True)
        irc.replySuccess(format(_('Reminder Event #%i added.'), id))
    remind = wrap(remind, ['positiveInt', 'text'])

    @internationalizeDocstring
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
                irc.error(_('Invalid event id.'))
        else:
            irc.error(_('Invalid event id.'))
    remove = wrap(remove, ['lowered'])

    def _repeat(self, network, msg, name, seconds, command, first_run, next_run_in):
        f = self._makeCommandFunction(network, msg, command, remove=False)
        f_wrapper = schedule.schedule.makePeriodicWrapper(f, seconds, name)
        assert first_run is not None
        id = schedule.addEvent(f_wrapper, time.time() + next_run_in, name)
        assert id == name
        self.events[name] = {'command':command,
                             'msg':msg,
                             'network':network,
                             'time':seconds,
                             'type':'repeat',
                             'first_run': first_run,
                             }

    @internationalizeDocstring
    def repeat(self, irc, msg, args, optlist, name, seconds, command):
        """[--delay <delay>] <name> <seconds> <command>

        Schedules the command <command> to run every <seconds> seconds,
        starting now (i.e., the command runs now, and every <seconds> seconds
        thereafter).  <name> is a name by which the command can be
        unscheduled.
        If --delay is given, starts in <delay> seconds instead of now.
        """
        opts = dict(optlist)
        name = name.lower()
        if name in self.events:
            irc.error(_('There is already an event with that name, please '
                      'choose another name.'), Raise=True)
        next_run_in = opts.get('delay', 0)
        first_run = time.time() + next_run_in
        self._repeat(
            irc.network, msg, name, seconds, command, first_run, next_run_in)
        # We don't reply because the command runs immediately.
        # But should we?  What if the command doesn't have visible output?
        # irc.replySuccess()
    repeat = wrap(repeat, [
        getopts({'delay': 'positiveInt'}),
        'nonInt', 'positiveInt', 'text'])

    @internationalizeDocstring
    def list(self, irc, msg, args):
        """takes no arguments

        Lists the currently scheduled events.
        """
        L = list(self.events.items())
        if L:
            L.sort()
            replies = []
            now = time.time()
            for (i, (name, event)) in enumerate(L):
                if event['type'] == 'single':
                    replies.append(format('%s (in %T): %q', name,
                        event['time'] - now, event['command']))
                else:
                    next_run_in = self._getNextRunIn(
                        event['first_run'], now, event['time'])
                    replies.append(format('%s (every %T, next run in %T): %q',
                        name, event['time'], next_run_in, event['command']))
            irc.reply(format('%L', replies))
        else:
            irc.reply(_('There are currently no scheduled commands.'))
    list = wrap(list)


Class = Scheduler

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
