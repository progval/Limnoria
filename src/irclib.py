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

import copy
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

class IrcCallback(object):
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
        commandName = 'do' + msg.command.capitalize()
        if hasattr(self, commandName):
            method = getattr(self, commandName)
            try:
                method(irc, msg)
            except Exception, e:
                debug.recoverableException()
                s = 'Exception raised by %s.%s' % \
                    (self.__class__.__name__, method.im_func.func_name)
                debug.debugMsg(s)

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
    """
    #__slots__ = ('msgs', 'queue')
    def __init__(self):
        self.reset()

    def reset(self):
        self.msgs = set()
        self.queue = []

    def enqueueMsg(self, msg):
        if msg in self.msgs and not world.startup:
            debug.debugMsg('Not adding msg %s to queue' % msg, 'normal')
        else:
            self.msgs.add(msg)
            self.queue.append(msg)

    def dequeueMsg(self):
        if self.queue:
            msg = self.queue.pop(0)
            if msg in self.msgs:
                self.msgs.remove(msg)
            return msg
        else:
            return None

    def empty(self):
        return self.queue == []


###
# Maintains the state of IRC connection -- the most recent messages, the
# status of various modes (especially ops/halfops/voices) in channels, etc.
###
class Channel(object):
    #__slots__ = ('users', 'ops', 'halfops', 'voices')
    def __init__(self):
        self.topic = ''
        self.users = set()
        self.ops = set()
        self.halfops = set()
        self.voices = set()

    def removeUser(self, user):
        self.users.remove(user)
        self.ops.remove(user)
        self.halfops.remove(user)
        self.voices.remove(user)

class IrcState(object):
    """Maintains state of the Irc connection.  Should also become smarter.
    """
    #__slots__ = ('history', 'nicksToHostmasks', 'channels')
    def __init__(self):
        self.reset()

    def reset(self):
        self.history = []
        self.nicksToHostmasks = {}
        self.channels = {}

        #    def __getstate__(self):
        #        return [getattr(self, s) for s in self.__slots__]
        #
        #    def __setstate__(self, state):
        #        for (name, value) in zipiter(self.__slots__, state):
        #            setattr(name, value)

    def copy(self):
        ret = self.__class__()
        ret.history = copy.copy(self.history)
        ret.nicksToHostmasks = copy.copy(self.nicksToHostmasks)
        ret.channels = copy.copy(self.channels)
        return ret

    def addMsg(self, irc, msg):
        if len(self.history) > conf.minHistory + 10:
            del self.history[:10]
        self.history.append(msg)
        if ircutils.isUserHostmask(msg.prefix):
            self.nicksToHostmasks[msg.nick] = msg.prefix
        if msg.command == '352': # Response to a WHO command.
            (nick, user, host) = (msg.args[2], msg.args[5], msg.args[3])
            hostmask = '%s!%s@%s' % (nick, user, host)
            self.nicksToHostmasks[nick] = hostmask
        elif msg.command == 'JOIN':
            channels = [channel.lower() for channel in msg.args[0].split(',')]
            for channel in channels:
                if channel in self.channels:
                    # We're already on the channel.
                    self.channels[channel].users.add(msg.nick)
                else:
                    chan = Channel()
                    self.channels[channel] = chan
                    chan.users.add(msg.nick)
        elif msg.command == '353':
            (_, _, channel, users) = msg.args
            chan = self.channels[channel.lower()]
            users = [ircutils.nick(user) for user in users.split()]
            for user in users:
                if user[0] in '@%+':
                    (marker, user) = (user[0], user[1:])
                    if marker == '@':
                        chan.ops.add(user)
                    elif marker == '%':
                        chan.halfops.add(user)
                    elif marker == '+':
                        chan.voices.add(user)
                chan.users.add(user)
        elif msg.command == 'PART':
            for channel in msg.args[0].split(','):
                channel = channel.lower()
                chan = self.channels[channel]
                if msg.nick == irc.nick:
                    del self.channels[channel]
                else:
                    chan.removeUser(msg.nick)
        elif msg.command == 'KICK':
            (channel, users) = msg.args[:2]
            channel = channel.lower()
            chan = self.channels[channel]
            for user in users.split(','):
                chan.removeUser(user)
        elif msg.command == 'QUIT':
            for channel in self.channels.itervalues():
                channel.removeUser(msg.nick)
        elif msg.command == 'TOPIC':
            channel = msg.args[0].lower()
            chan = self.channels[channel]
            chan.topic = msg.args[1]
        elif msg.command == '332':
            channel = msg.args[1].lower()
            chan = self.channels[channel]
            chan.topic = msg.args[2]

    def getTopic(self, channel):
        return self.channels[channel.lower()].topic

    def nickToHostmask(self, nick):
        return self.nicksToHostmasks[nick]



###
# The basic class for handling a connection to an IRC server.  Accepts
# callbacks of the IrcCallback interface.  Public attributes include 'driver',
# 'queue', and 'state', in addition to the standard nick/user/ident attributes.
###
class Irc(object):
    """The base class for an IRC connection.

    Handles PING commands already.
    """
    _nickSetters = set(('001', '002', '003', '004', '250', '251', '252', '254',
                        '255', '265', '266', '372', '375', '376', '333', '353',
                        '332', '366'))
    def __init__(self, nick, user='', ident='', callbacks=None):
        world.ircs.append(self)
        self.nick = nick
        self.prefix = ''
        self.user = user or nick    # Default to nick if user isn't provided.
        self.ident = ident or nick  # Ditto.
        if callbacks is None:
            self.callbacks = []
        else:
            self.callbacks = callbacks
        self._nickmods = copy.copy(conf.nickmods)
        self.state = IrcState()
        self.queue = IrcMsgQueue()
        self.fastqueue = []
        self.lastping = time.time()
        self.lastTake = 0
        self.driver = None # The driver should set this later.
        self.queue.enqueueMsg(ircmsgs.user(self.user, self.ident))
        self.queue.enqueueMsg(ircmsgs.nick(self.nick))

    def reset(self):
        self._nickmods = copy.copy(conf.nickmods)
        self.state.reset()
        self.queue.reset()
        self.fastqueue = []
        self.queue.enqueueMsg(ircmsgs.user(self.user, self.ident))
        self.queue.enqueueMsg(ircmsgs.nick(self.nick))
        for callback in self.callbacks:
            callback.reset()

    def addCallback(self, callback):
        self.callbacks.append(callback)

    def removeCallback(self, name):
        ret = []
        toRemove = []
        for (i, cb) in enumerate(self.callbacks):
            if cb.name() == name:
                toRemove.append(i)
        for i in reviter(range(len(self.callbacks))):
            if toRemove and toRemove[-1] == i:
                toRemove.pop()
                ret.append(self.callbacks.pop(i))
        return ret

    def queueMsg(self, msg):
        self.queue.enqueueMsg(msg)

    def sendMsg(self, msg):
        self.fastqueue.append(msg)

    def takeMsg(self):
        now = time.time()
        msg = None
        if self.fastqueue:
            msg = self.fastqueue.pop(0)
        elif not self.queue.empty():
            if now - self.lastTake <= conf.throttleTime:
                debug.debugMsg('Irc.takeMsg throttling.', 'verbose')
            else:
                self.lastTake = now
                msg = self.queue.dequeueMsg()
        elif now > (self.lastping + conf.pingInterval):
            if now - self.lastTake <= conf.throttleTime:
                debug.debugMsg('Irc.takeMsg throttling.', 'verbose')
            else:
                self.lastping = now
                msg = ircmsgs.ping(str(int(now)))
        if msg:
            for callback in self.callbacks:
                #debug.printf(repr(msg))
                msg = callback.outFilter(self, msg)
                if msg is None:
                    s = 'outFilter %s returned None' % callbacks.name()
                    debug.debugMsg(s)
                    return None
            self.state.addMsg(self,ircmsgs.IrcMsg(msg=msg, prefix=self.prefix))
            s = '%s  %s' % (time.strftime(conf.timestampFormat), msg)
            debug.debugMsg(s, 'low')
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
        debug.debugMsg('%s  %s' % (time.strftime(conf.timestampFormat), msg),
                       'low')
        # First, make sure self.nick is always consistent with the server.
        if msg.command == 'NICK' and msg.nick == self.nick:
            if ircdb.users.hasUser(self.nick):
                ircdb.users.delUser(self.nick)
            self.nick = ircutils.nick(msg.args[0])
            (nick, user, domain) = ircutils.splitHostmask(msg.prefix)
            if ircdb.users.hasUser(self.prefix):
                ircdb.users.delUser(self.prefix)
            self.prefix = '%s!%s@%s' % (self.nick, user, domain)
        elif msg.command in self._nickSetters:
            newnick = ircutils.nick(msg.args[0])
            if self.nick != newnick:
                debug.printf('Hmm...self.nick != newnick.  Odd.')
                self.nick = newnick
        # Respond to PING requests.
        elif msg.command == 'PING':
            self.sendMsg(ircmsgs.pong(msg.args[0]))
        # Send new nicks on 433
        elif msg.command == '433' or msg.command == '432':
            self.sendMsg(ircmsgs.nick(self._nickmods.pop(0) % self.nick))
        if msg.nick == self.nick:
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

#        elif msg.command == 'ERROR':
#            if msg.args[0].startswith('Closing Link'):
#                self.driver.die()
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
                    debug.debugMsg(debugmsg)
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
        world.ircs.remove(self)

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
