###
# Copyright (c) 2002-2005, Jeremiah Fincher
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
Schedule plugin with a subclass of drivers.IrcDriver in order to be run as a
Supybot driver.
"""

import time
import heapq

import supybot.log as log
import supybot.world as world
import supybot.drivers as drivers

class mytuple(tuple):
    def __cmp__(self, other):
        return cmp(self[0], other[0])
    def __le__(self, other):
        return self[0] <= other[0]
    def __lt__(self, other):
        return self[0] < other[0]
    def __gt__(self, other):
        return self[0] > other[0]
    def __ge__(self, other):
        return self[0] >= other[0]

class Schedule(drivers.IrcDriver):
    """An IrcDriver to handling scheduling of events.

    Events, in this case, are functions accepting no arguments.
    """
    def __init__(self):
        drivers.IrcDriver.__init__(self)
        self.schedule = []
        self.events = {}
        self.counter = 0

    def reset(self):
        self.events.clear()
        self.schedule[:] = []
        # We don't reset the counter here because if someone has held an id of
        # one of the nuked events, we don't want him removing new events with
        # his old id.

    def name(self):
        return 'Schedule'

    def addEvent(self, f, t, name=None, args=[], kwargs={}):
        """Schedules an event f to run at time t.

        name must be hashable and not an int.
        """
        if name is None:
            name = self.counter
            self.counter += 1
        assert name not in self.events, \
               'An event with the same name has already been scheduled.'
        self.events[name] = f
        heapq.heappush(self.schedule, mytuple((t, name, args, kwargs)))
        return name

    def removeEvent(self, name):
        """Removes the event with the given name from the schedule."""
        f = self.events.pop(name)
        self.schedule = [x for x in self.schedule if f != name]
        # We must heapify here because the heap property may not be preserved
        # by the above list comprehension.  We could, conceivably, just mark
        # the elements of the heap as removed and ignore them when we heappop,
        # but that would only save a constant factor (we're already linear for
        # the listcomp) so I'm not worried about it right now.
        heapq.heapify(self.schedule)
        return f

    def rescheduleEvent(self, name, t):
        f = self.removeEvent(name)
        self.addEvent(f, t, name=name)

    def addPeriodicEvent(self, f, t, name=None, now=True):
        """Adds a periodic event that is called every t seconds."""
        def wrapper():
            try:
                f()
            finally:
                # Even if it raises an exception, let's schedule it.
                return self.addEvent(wrapper, time.time() + t, name)
        if now:
            return wrapper()
        else:
            return self.addEvent(wrapper, time.time() + t, name)

    removePeriodicEvent = removeEvent

    def run(self):
        if len(drivers._drivers) == 1 and not world.testing:
            log.error('Schedule is the only remaining driver, '
                      'why do we continue to live?')
            time.sleep(1) # We're the only driver; let's pause to think.
        while self.schedule and self.schedule[0][0] < time.time():
            (t, name, args, kwargs) = heapq.heappop(self.schedule)
            f = self.events[name]
            del self.events[name]
            try:
                f(*args, **kwargs)
            except Exception, e:
                log.exception('Uncaught exception in scheduled function:')

if 'ignore' in globals():
    globals()['ignore'](schedule)
else:
    schedule = Schedule()

addEvent = schedule.addEvent
removeEvent = schedule.removeEvent
rescheduleEvent = schedule.rescheduleEvent
addPeriodicEvent = schedule.addPeriodicEvent
removePeriodicEvent = removeEvent
run = schedule.run


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
