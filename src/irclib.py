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

from fix import *
from structures import queue, RingBuffer

import copy
import sets
import time
import atexit

import conf
import debug
import world
import ircdb
import ircmsgs
import ircutils

###
# The base class for a callback to be registered with an Irc object.  Shows
# the required interface for callbacks -- name(),
# inFilter(irc, msg), outFilter(irc, msg), and __call__(irc, msg) [used so
# functions can be used as callbacks conceivable, and so if refactoring ever
# changes the nature of the callbacks from classes to functions, syntactical
# changes elsewhere won't be required.
###

class IrcCommandDispatcher(object):
    """Base class for classes that must dispatch on a command."""
    def dispatchCommand(self, command):
        return getattr(self, 'do' + command.capitalize(), None)

class IrcCallback(IrcCommandDispatcher):
    """Base class for standard callbacks.

    Callbacks derived from this class should have methods of the form
    "doCommand" -- doPrivmsg, doNick, do433, etc.  These will be called
    on matching messages.
    """
    def name(self):
        return self.__class__.__name__

    def inFilter(self, irc, msg):
        return msg

    def outFilter(self, irc, msg):
        return msg

    def __call__(self, irc, msg):
        method = self.dispatchCommand(msg.command)
        if method is not None:
            try:
                method(irc, msg)
            except Exception:
                debug.recoverableException()
                s = 'Exception raised by %s.%s' % \
                    (self.__class__.__name__, method.im_func.func_name)
                debug.msg(s)

    def reset(self):
        pass

    def die(self):
        pass

###
# Basic queue for IRC messages.  It doesn't presently (but should at some
# later point) reorder messages based on priority or penalty calculations.
###
class IrcMsgQueue(object):
    """Class for a queue of IrcMsgs.  Eventually, it should be smart.

    Probably smarter than it is now, though it's gotten quite a bit smarter
    than it originally was.  A method to "score" methods, and a heapq to
    maintain a priority queue of the messages would be the ideal way to do
    intelligent queueing.
    """
    __slots__ = ('msgs', 'highpriority', 'normal', 'lowpriority')
    def __init__(self):
        self.reset()

    def reset(self):
        self.highpriority = queue()
        self.normal = queue()
        self.lowpriority = queue()
        self.msgs = sets.Set()

    def enqueue(self, msg):
        if msg in self.msgs:
            if not world.startup:
                debug.msg('Not adding msg %s to queue' % msg, 'normal')
        else:
            self.msgs.add(msg)
            if msg.command in ('MODE', 'KICK', 'PONG'):
                self.highpriority.enqueue(msg)
            elif msg.command in ('PING',):
                self.lowpriority.enqueue(msg)
            else:
                self.normal.enqueue(msg)

    def dequeue(self):
        if self.highpriority:
            msg = self.highpriority.dequeue()
        elif self.normal:
            msg = self.normal.dequeue()
        elif self.lowpriority:
            msg = self.lowpriority.dequeue()
        else:
            msg = None
        if msg:
            self.msgs.remove(msg)
        return msg

    def __nonzero__(self):
        return bool(self.highpriority or self.normal or self.lowpriority)


###
# Maintains the state of IRC connection -- the most recent messages, the
# status of various modes (especially ops/halfops/voices) in channels, etc.
###
class Channel(object):
    __slots__ = ('users', 'ops', 'halfops', 'voices', 'topic')
    def __init__(self):
        self.topic = ''
        self.users = ircutils.IrcSet() # sets.Set()
        self.ops = ircutils.IrcSet() # sets.Set()
        self.halfops = ircutils.IrcSet() # sets.Set()
        self.voices = ircutils.IrcSet() # sets.Set()

    def addUser(self, user):
        nick = user.lstrip('@%+')
        while user and user[0] in '@%+':
            (marker, user) = (user[0], user[1:])
            if marker == '@':
                self.ops.add(nick)
            elif marker == '%':
                self.halfops.add(nick)
            elif marker == '+':
                self.voices.add(nick)
        self.users.add(nick)

    def replaceUser(self, oldNick, newNick):
        # Note that this doesn't have to have the sigil (@%+) that users
        # have to have for addUser; it just changes the name of the user
        # without changing any of his categories.
        for s in (self.users, self.ops, self.halfops, self.voices):
            if oldNick in s:
                s.discard(oldNick)
                s.add(newNick)

    def removeUser(self, user):
        self.users.discard(user)
        self.ops.discard(user)
        self.halfops.discard(user)
        self.voices.discard(user)

    def __getstate__(self):
        return [getattr(self, name) for name in self.__slots__]

    def __setstate__(self, t):
        for (name, value) in zip(self.__slots__, t):
            setattr(self, name, value)

    def __eq__(self, other):
        ret = True
        for name in self.__slots__:
            ret = ret and getattr(self, name) == getattr(other, name)
        return ret

    def __ne__(self, other):
        # This shouldn't even be necessary, grr...
        return not self == other

class IrcState(IrcCommandDispatcher):
    """Maintains state of the Irc connection.  Should also become smarter.
    """
    __slots__ = ('history', 'nicksToHostmasks', 'channels')
    def __init__(self):
        self.history = RingBuffer(conf.maxHistory)
        self.reset()

    def reset(self):
        self.history.reset()
        self.nicksToHostmasks = ircutils.IrcDict()
        self.channels = ircutils.IrcDict()

    def __getstate__(self):
        return map(lambda name: getattr(self, name), self.__slots__)

    def __setstate__(self, t):
        for (name, value) in zip(self.__slots__, t):
            setattr(self, name, value)

    def __eq__(self, other):
        ret = True
        for name in self.__slots__:
            ret = ret and getattr(self, name) == getattr(other, name)
        return ret

    def __ne__(self, other):
        return not self == other

    def copy(self):
        ret = self.__class__()
        ret.history = copy.copy(self.history)
        ret.nicksToHostmasks = copy.copy(self.nicksToHostmasks)
        ret.channels = copy.copy(self.channels)
        return ret

    def addMsg(self, irc, msg):
        self.history.append(msg)
        if ircutils.isUserHostmask(msg.prefix) and not msg.command == 'NICK':
            self.nicksToHostmasks[msg.nick] = msg.prefix
        method = self.dispatchCommand(msg.command)
        if method is not None:
            method(irc, msg)

    def getTopic(self, channel):
        return self.channels[channel].topic

    def nickToHostmask(self, nick):
        return self.nicksToHostmasks[nick]

    def do352(self, irc, msg):
        (nick, user, host) = (msg.args[2], msg.args[5], msg.args[3])
        hostmask = '%s!%s@%s' % (nick, user, host)
        self.nicksToHostmasks[nick] = hostmask

    def doJoin(self, irc, msg):
        for channel in msg.args[0].split(','):
            if channel in self.channels:
                self.channels[channel].addUser(msg.nick)
            else:
                chan = Channel()
                chan.addUser(msg.nick)
                self.channels[channel] = chan

    def do353(self, irc, msg):
        (_, _, channel, users) = msg.args
        chan = self.channels[channel]
        users = users.split()
        for user in users:
            chan.addUser(user)

    def doPart(self, irc, msg):
        for channel in msg.args[0].split(','):
            chan = self.channels[channel]
            if msg.nick == irc.nick:
                del self.channels[channel]
            else:
                chan.removeUser(msg.nick)

    def doKick(self, irc, msg):
        (channel, users) = msg.args[:2]
        chan = self.channels[channel]
        for user in users.split(','):
            chan.removeUser(user)

    def doQuit(self, irc, msg):
        for channel in self.channels.itervalues():
            channel.removeUser(msg.nick)

    def doTopic(self, irc, msg):
        chan = self.channels[msg.args[0]]
        chan.topic = msg.args[1]

    def do332(self, irc, msg):
        chan = self.channels[msg.args[1]]
        chan.topic = msg.args[2]

    def doNick(self, irc, msg):
        newNick = msg.args[0]
        oldNick = msg.nick
        try:
            if msg.user and msg.host:
                # Nick messages being handed out from the bot itself won't
                # have the necessary prefix to make a hostmask.
                newHostmask = ircutils.joinHostmask(newNick,msg.user,msg.host)
                self.nicksToHostmasks[newNick] = newHostmask
            del self.nicksToHostmasks[oldNick]
        except KeyError:
            pass
        for channel in self.channels.itervalues():
            channel.replaceUser(oldNick, newNick)



###
# The basic class for handling a connection to an IRC server.  Accepts
# callbacks of the IrcCallback interface.  Public attributes include 'driver',
# 'queue', and 'state', in addition to the standard nick/user/ident attributes.
###
class Irc(object):
    """The base class for an IRC connection.

    Handles PING commands already.
    """
    _nickSetters = sets.Set(['001', '002', '003', '004', '250', '251', '252',
                             '254', '255', '265', '266', '372', '375', '376',
                             '333', '353', '332', '366'])
    def __init__(self, nick, user='', ident='', password='', callbacks=None):
        world.ircs.append(self)
        self.nick = nick
        self.password = password
        self.user = user or nick    # Default to nick if user isn't provided.
        self.ident = ident or nick  # Ditto.
        self.prefix = '%s!%s@%s' % (nick, ident, 'unset.domain')
        if callbacks is None:
            self.callbacks = []
        else:
            self.callbacks = callbacks
        self.state = IrcState()
        self.queue = IrcMsgQueue()
        self._nickmods = copy.copy(conf.nickmods)
        self.lastTake = 0
        self.fastqueue = queue()
        self.lastping = time.time()
        self.outstandingPing = False
        self.driver = None # The driver should set this later.
        if self.password:
            self.queue.enqueue(ircmsgs.password(self.password))
        self.queue.enqueue(ircmsgs.nick(self.nick))
        self.queue.enqueue(ircmsgs.user(self.ident, self.user))

    def reset(self):
        self._nickmods = copy.copy(conf.nickmods)
        self.state.reset()
        self.queue.reset()
        self.lastping = time.time()
        self.outstandingPing = False
        self.fastqueue = queue()
        if self.password:
            self.queue.enqueue(ircmsgs.password(self.password))
        self.queue.enqueue(ircmsgs.nick(self.nick))
        self.queue.enqueue(ircmsgs.user(self.ident, self.user))
        for callback in self.callbacks:
            callback.reset()

    def addCallback(self, callback):
        self.callbacks.append(callback)

    def getCallback(self, name):
        name = name.lower()
        for callback in self.callbacks:
            if callback.name().lower() == name:
                return callback
        else:
            return None

    def removeCallback(self, name):
        (bad, good) = partition(lambda cb: cb.name() == name, self.callbacks)
        self.callbacks[:] = good
        return bad

    def queueMsg(self, msg):
        self.queue.enqueue(msg)

    def sendMsg(self, msg):
        self.fastqueue.enqueue(msg)

    def takeMsg(self):
        now = time.time()
        msg = None
        if self.fastqueue:
            msg = self.fastqueue.dequeue()
        elif self.queue:
            if not world.testing and now - self.lastTake <= conf.throttleTime:
                debug.msg('Irc.takeMsg throttling.', 'verbose')
            else:
                self.lastTake = now
                msg = self.queue.dequeue()
        elif now > (self.lastping + conf.pingInterval):
            if self.outstandingPing:
                debug.msg('Reconnecting, ping not replied to.', 'normal')
                self.driver.reconnect()
            else:
                self.lastping = now
                now = str(int(now))
                self.outstandingPing = True
                self.queueMsg(ircmsgs.ping(now))
        if msg:
            for callback in self.callbacks:
                #debug.printf(repr(msg))
                try:
                    outFilter = getattr(callback, 'outFilter')
                except AttributeError, e:
                    continue
                try:
                    msg = outFilter(self, msg)
                except:
                    debug.recoverableException()
                    continue
                if msg is None:
                    s = 'outFilter %s returned None' % callback.name()
                    debug.msg(s)
                    return None
            self.state.addMsg(self,ircmsgs.IrcMsg(msg=msg, prefix=self.prefix))
            s = '%s  %s' % (time.strftime(conf.logTimestampFormat), msg)
            debug.msg(s, 'low')
            if msg.command == 'NICK':
                # We don't want a race condition where the server's NICK
                # back to us is lost and someone else steals our nick and uses
                # it to abuse our 'owner' power we give to ourselves.  Ergo, on
                # outgoing messages that change our nick, we pre-emptively
                # delete the 'owner' user we setup for ourselves.
                if ircdb.users.hasUser(self.nick):
                    ircdb.users.delUser(self.nick)
            return msg
        else:
            return None

    def feedMsg(self, msg):
        debug.msg('%s  %s'%(time.strftime(conf.logTimestampFormat), msg),'low')
        # Yeah, so this is odd.  Some networks (oftc) seem to give us certain
        # messages with our nick instead of our prefix.  We'll fix that here.
        if msg.prefix == self.nick:
            debug.msg('Got one of those odd nick-instead-of-prefix msgs.')
            msg = ircmsgs.IrcMsg(prefix=self.prefix,
                                 command=msg.command,
                                 args=msg.args)
        # First, make sure self.nick is always consistent with the server.
        if msg.command == 'NICK' and msg.nick == self.nick:
            if ircdb.users.hasUser(self.nick):
                ircdb.users.delUser(self.nick)
            if ircdb.users.hasUser(self.prefix):
                ircdb.users.delUser(self.prefix)
            self.nick = msg.args[0]
            (nick, user, domain) = ircutils.splitHostmask(msg.prefix)
            self.prefix = '%s!%s@%s' % (self.nick, user, domain)
        # Respond to PING requests.
        if msg.command == 'PING':
            self.sendMsg(ircmsgs.pong(msg.args[0]))
        if msg.command == 'PONG':
            self.outstandingPing = False
        # Send new nicks on 433
        if msg.command == '433' or msg.command == '432':
            self.sendMsg(ircmsgs.nick(self._nickmods.pop(0) % self.nick))
        if msg.nick == self.nick:
            self.prefix = msg.prefix
            if ircdb.users.hasUser(self.nick):
                u = ircdb.users.getUser(self.nick)
                if not u.hasHostmask(msg.prefix):
                    u.addHostmask(msg.prefix)
                    ircdb.users.setUser(self.nick, u)
            else:
                u = ircdb.IrcUser(capabilities=['owner'], password=mktemp(),
                                  hostmasks=[msg.prefix])
                ircdb.users.setUser(self.nick, u)
                atexit.register(lambda: catch(ircdb.users.delUser(self.nick)))
        if msg.command == 'ERROR':
            if msg.args[0].startswith('Closing Link'):
                if hasattr(self.driver, 'scheduleReconnect'):
                    self.driver.scheduleReconnect()
                if self.driver:
                    self.driver.die()
        if msg.command in self._nickSetters:
            #debug.printf('msg.command in self._nickSetters')
            newnick = msg.args[0]
            if self.nick != newnick:
                debug.printf('Hmm...self.nick != newnick.  Odd.')
            self.nick = newnick
        # Now update the IrcState object.
        try:
            self.state.addMsg(self, msg)
        except:
            debug.recoverableException()
        # Now call the callbacks.
        for callback in self.callbacks:
            try:
                m = callback.inFilter(self, msg)
                if not m:
                    debugmsg = 'inFilter %s returned None' % callback.name()
                    debug.msg(debugmsg)
                msg = m
            except:
                debug.recoverableException()
        for callback in self.callbacks:
            try:
                if callback is not None:
                    callback(self, msg)
            except:
                debug.recoverableException()

    def die(self):
        for callback in self.callbacks:
            callback.die()
        if self.driver is not None:
            self.driver.die()
        if self in world.ircs:
            world.ircs.remove(self)

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
