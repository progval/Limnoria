###
# Copyright (c) 2002-2005 Jeremiah Fincher
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

import re
import copy
import time
import random
import base64
import collections

try:
    from ecdsa import SigningKey, BadDigestError
    ecdsa = True
except ImportError:
    ecdsa = False

from . import conf, ircdb, ircmsgs, ircutils, log, utils, world
from .utils.str import rsplit
from .utils.iter import chain
from .utils.structures import smallqueue, RingBuffer

###
# The base class for a callback to be registered with an Irc object.  Shows
# the required interface for callbacks -- name(),
# inFilter(irc, msg), outFilter(irc, msg), and __call__(irc, msg) [used so as
# to make functions used as callbacks conceivable, and so if refactoring ever
# changes the nature of the callbacks from classes to functions, syntactical
# changes elsewhere won't be required.]
###

class IrcCommandDispatcher(object):
    """Base class for classes that must dispatch on a command."""
    def dispatchCommand(self, command):
        """Given a string 'command', dispatches to doCommand."""
        return getattr(self, 'do' + command.capitalize(), None)


class IrcCallback(IrcCommandDispatcher, log.Firewalled):
    """Base class for standard callbacks.

    Callbacks derived from this class should have methods of the form
    "doCommand" -- doPrivmsg, doNick, do433, etc.  These will be called
    on matching messages.
    """
    callAfter = ()
    callBefore = ()
    __firewalled__ = {'die': None,
                      'reset': None,
                      '__call__': None,
                      'inFilter': lambda self, irc, msg: msg,
                      'outFilter': lambda self, irc, msg: msg,
                      'name': lambda self: self.__class__.__name__,
                      'callPrecedence': lambda self, irc: ([], []),
                      }

    def __init__(self, *args, **kwargs):
        #object doesn't take any args, so the buck stops here.
        #super(IrcCallback, self).__init__(*args, **kwargs)
        pass

    def __repr__(self):
        return '<%s %s %s>' % \
               (self.__class__.__name__, self.name(), object.__repr__(self))

    def name(self):
        """Returns the name of the callback."""
        return self.__class__.__name__

    def callPrecedence(self, irc):
        """Returns a pair of (callbacks to call before me,
                              callbacks to call after me)"""
        after = []
        before = []
        for name in self.callBefore:
            cb = irc.getCallback(name)
            if cb is not None:
                after.append(cb)
        for name in self.callAfter:
            cb = irc.getCallback(name)
            if cb is not None:
                before.append(cb)
        assert self not in after, '%s was in its own after.' % self.name()
        assert self not in before, '%s was in its own before.' % self.name()
        return (before, after)

    def inFilter(self, irc, msg):
        """Used for filtering/modifying messages as they're entering.

        ircmsgs.IrcMsg objects are immutable, so this method is expected to
        return another ircmsgs.IrcMsg object.  Obviously the same IrcMsg
        can be returned.
        """
        return msg

    def outFilter(self, irc, msg):
        """Used for filtering/modifying messages as they're leaving.

        As with inFilter, an IrcMsg is returned.
        """
        return msg

    def __call__(self, irc, msg):
        """Used for handling each message."""
        method = self.dispatchCommand(msg.command)
        if method is not None:
            method(irc, msg)

    def reset(self):
        """Resets the callback.  Called when reconnecting to the server."""
        pass

    def die(self):
        """Makes the callback die.  Called when the parent Irc object dies."""
        pass

###
# Basic queue for IRC messages.  It doesn't presently (but should at some
# later point) reorder messages based on priority or penalty calculations.
###
_high = frozenset(['MODE', 'KICK', 'PONG', 'NICK', 'PASS', 'CAPAB'])
_low = frozenset(['PRIVMSG', 'PING', 'WHO', 'NOTICE', 'JOIN'])
class IrcMsgQueue(object):
    """Class for a queue of IrcMsgs.  Eventually, it should be smart.

    Probably smarter than it is now, though it's gotten quite a bit smarter
    than it originally was.  A method to "score" methods, and a heapq to
    maintain a priority queue of the messages would be the ideal way to do
    intelligent queuing.

    As it stands, however, we simply keep track of 'high priority' messages,
    'low priority' messages, and normal messages, and just make sure to return
    the 'high priority' ones before the normal ones before the 'low priority'
    ones.
    """
    __slots__ = ('msgs', 'highpriority', 'normal', 'lowpriority', 'lastJoin')
    def __init__(self, iterable=()):
        self.reset()
        for msg in iterable:
            self.enqueue(msg)

    def reset(self):
        """Clears the queue."""
        self.lastJoin = 0
        self.highpriority = smallqueue()
        self.normal = smallqueue()
        self.lowpriority = smallqueue()

    def enqueue(self, msg):
        """Enqueues a given message."""
        if msg in self and \
           conf.supybot.protocols.irc.queuing.duplicates():
            s = str(msg).strip()
            log.info('Not adding message %q to queue, already added.', s)
            return False
        else:
            if msg.command in _high:
                self.highpriority.enqueue(msg)
            elif msg.command in _low:
                self.lowpriority.enqueue(msg)
            else:
                self.normal.enqueue(msg)
            return True

    def dequeue(self):
        """Dequeues a given message."""
        msg = None
        if self.highpriority:
            msg = self.highpriority.dequeue()
        elif self.normal:
            msg = self.normal.dequeue()
        elif self.lowpriority:
            msg = self.lowpriority.dequeue()
            if msg.command == 'JOIN':
                limit = conf.supybot.protocols.irc.queuing.rateLimit.join()
                now = time.time()
                if self.lastJoin + limit <= now:
                    self.lastJoin = now
                else:
                    self.lowpriority.enqueue(msg)
                    msg = None
        return msg

    def __contains__(self, msg):
        return msg in self.normal or \
               msg in self.lowpriority or \
               msg in self.highpriority

    def __bool__(self):
        return bool(self.highpriority or self.normal or self.lowpriority)
    __nonzero__ = __bool__

    def __len__(self):
        return len(self.highpriority)+len(self.lowpriority)+len(self.normal)

    def __repr__(self):
        name = self.__class__.__name__
        return '%s(%r)' % (name, list(chain(self.highpriority,
                                            self.normal,
                                            self.lowpriority)))
    __str__ = __repr__


###
# Maintains the state of IRC connection -- the most recent messages, the
# status of various modes (especially ops/halfops/voices) in channels, etc.
###
class ChannelState(utils.python.Object):
    __slots__ = ('users', 'ops', 'halfops', 'bans',
                 'voices', 'topic', 'modes', 'created')
    def __init__(self):
        self.topic = ''
        self.created = 0
        self.ops = ircutils.IrcSet()
        self.bans = ircutils.IrcSet()
        self.users = ircutils.IrcSet()
        self.voices = ircutils.IrcSet()
        self.halfops = ircutils.IrcSet()
        self.modes = {}

    def isOp(self, nick):
        return nick in self.ops
    def isOpPlus(self, nick):
        return nick in self.ops
    def isVoice(self, nick):
        return nick in self.voices
    def isVoicePlus(self, nick):
        return nick in self.voices or nick in self.halfops or nick in self.ops
    def isHalfop(self, nick):
        return nick in self.halfops
    def isHalfopPlus(self, nick):
        return nick in self.halfops or nick in self.ops

    def addUser(self, user):
        "Adds a given user to the ChannelState.  Power prefixes are handled."
        nick = user.lstrip('@%+&~!')
        if not nick:
            return
        # & is used to denote protected users in UnrealIRCd
        # ~ is used to denote channel owner in UnrealIRCd
        # ! is used to denote protected users in UltimateIRCd
        while user and user[0] in '@%+&~!':
            (marker, user) = (user[0], user[1:])
            assert user, 'Looks like my caller is passing chars, not nicks.'
            if marker in '@&~!':
                self.ops.add(nick)
            elif marker == '%':
                self.halfops.add(nick)
            elif marker == '+':
                self.voices.add(nick)
        self.users.add(nick)

    def replaceUser(self, oldNick, newNick):
        """Changes the user oldNick to newNick; used for NICK changes."""
        # Note that this doesn't have to have the sigil (@%+) that users
        # have to have for addUser; it just changes the name of the user
        # without changing any of their categories.
        for s in (self.users, self.ops, self.halfops, self.voices):
            if oldNick in s:
                s.remove(oldNick)
                s.add(newNick)

    def removeUser(self, user):
        """Removes a given user from the channel."""
        self.users.discard(user)
        self.ops.discard(user)
        self.halfops.discard(user)
        self.voices.discard(user)

    def setMode(self, mode, value=None):
        assert mode not in 'ovhbeq'
        self.modes[mode] = value

    def unsetMode(self, mode):
        assert mode not in 'ovhbeq'
        if mode in self.modes:
            del self.modes[mode]

    def doMode(self, msg):
        def getSet(c):
            if c == 'o':
                Set = self.ops
            elif c == 'v':
                Set = self.voices
            elif c == 'h':
                Set = self.halfops
            elif c == 'b':
                Set = self.bans
            else: # We don't care yet, so we'll just return an empty set.
                Set = set()
            return Set
        for (mode, value) in ircutils.separateModes(msg.args[1:]):
            (action, modeChar) = mode
            if modeChar in 'ovhbeq': # We don't handle e or q yet.
                Set = getSet(modeChar)
                if action == '-':
                    Set.discard(value)
                elif action == '+':
                    Set.add(value)
            else:
                if action == '+':
                    self.setMode(modeChar, value)
                else:
                    assert action == '-'
                    self.unsetMode(modeChar)

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

Batch = collections.namedtuple('Batch', 'type arguments messages')

class IrcState(IrcCommandDispatcher, log.Firewalled):
    """Maintains state of the Irc connection.  Should also become smarter.
    """
    __firewalled__ = {'addMsg': None}
    def __init__(self, history=None, supported=None,
                 nicksToHostmasks=None, channels=None,
                 capabilities_ack=None, capabilities_nak=None,
                 capabilities_ls=None):
        if history is None:
            history = RingBuffer(conf.supybot.protocols.irc.maxHistoryLength())
        if supported is None:
            supported = utils.InsensitivePreservingDict()
        if nicksToHostmasks is None:
            nicksToHostmasks = ircutils.IrcDict()
        if channels is None:
            channels = ircutils.IrcDict()
        self.capabilities_ack = capabilities_ack or set()
        self.capabilities_nak = capabilities_nak or set()
        self.capabilities_ls = capabilities_ls or {}
        self.ircd = None
        self.supported = supported
        self.history = history
        self.channels = channels
        self.nicksToHostmasks = nicksToHostmasks
        self.batches = {}

    def reset(self):
        """Resets the state to normal, unconnected state."""
        self.history.reset()
        self.channels.clear()
        self.supported.clear()
        self.nicksToHostmasks.clear()
        self.history.resize(conf.supybot.protocols.irc.maxHistoryLength())
        self.batches = {}

    def __reduce__(self):
        return (self.__class__, (self.history, self.supported,
                                 self.nicksToHostmasks, self.channels))

    def __eq__(self, other):
        return self.history == other.history and \
               self.channels == other.channels and \
               self.supported == other.supported and \
               self.nicksToHostmasks == other.nicksToHostmasks and \
               self.batches == other.batches

    def __ne__(self, other):
        return not self == other

    def copy(self):
        ret = self.__class__()
        ret.history = copy.deepcopy(self.history)
        ret.nicksToHostmasks = copy.deepcopy(self.nicksToHostmasks)
        ret.channels = copy.deepcopy(self.channels)
        ret.batches = copy.deepcopy(self.batches)
        return ret

    def addMsg(self, irc, msg):
        """Updates the state based on the irc object and the message."""
        self.history.append(msg)
        if ircutils.isUserHostmask(msg.prefix) and not msg.command == 'NICK':
            self.nicksToHostmasks[msg.nick] = msg.prefix
        if 'batch' in msg.server_tags:
            batch = msg.server_tags['batch']
            assert batch in self.batches, \
                    'Server references undeclared batch %s' % batch
            self.batches[batch].messages.append(msg)
        method = self.dispatchCommand(msg.command)
        if method is not None:
            method(irc, msg)

    def getTopic(self, channel):
        """Returns the topic for a given channel."""
        return self.channels[channel].topic

    def nickToHostmask(self, nick):
        """Returns the hostmask for a given nick."""
        return self.nicksToHostmasks[nick]

    def do004(self, irc, msg):
        """Handles parsing the 004 reply

        Supported user and channel modes are cached"""
        # msg.args = [nick, server, ircd-version, umodes, modes,
        #             modes that require arguments? (non-standard)]
        self.ircd = msg.args[2]
        self.supported['umodes'] = frozenset(msg.args[3])
        self.supported['chanmodes'] = frozenset(msg.args[4])

    _005converters = utils.InsensitivePreservingDict({
        'modes': int,
        'keylen': int,
        'nicklen': int,
        'userlen': int,
        'hostlen': int,
        'kicklen': int,
        'awaylen': int,
        'silence': int,
        'topiclen': int,
        'channellen': int,
        'maxtargets': int,
        'maxnicklen': int,
        'maxchannels': int,
        'watch': int, # DynastyNet, EnterTheGame
        })
    def _prefixParser(s):
        if ')' in s:
            (left, right) = s.split(')')
            assert left[0] == '(', 'Odd PREFIX in 005: %s' % s
            left = left[1:]
            assert len(left) == len(right), 'Odd PREFIX in 005: %s' % s
            return dict(list(zip(left, right)))
        else:
            return dict(list(zip('ovh', s)))
    _005converters['prefix'] = _prefixParser
    del _prefixParser
    def _maxlistParser(s):
        modes = ''
        limits = []
        pairs = s.split(',')
        for pair in pairs:
            (mode, limit) = pair.split(':', 1)
            modes += mode
            limits += (int(limit),) * len(mode)
        return dict(list(zip(modes, limits)))
    _005converters['maxlist'] = _maxlistParser
    del _maxlistParser
    def _maxbansParser(s):
        # IRCd using a MAXLIST style string (IRCNet)
        if ':' in s:
            modes = ''
            limits = []
            pairs = s.split(',')
            for pair in pairs:
                (mode, limit) = pair.split(':', 1)
                modes += mode
                limits += (int(limit),) * len(mode)
            d = dict(list(zip(modes, limits)))
            assert 'b' in d
            return d['b']
        else:
            return int(s)
    _005converters['maxbans'] = _maxbansParser
    del _maxbansParser
    def do005(self, irc, msg):
        for arg in msg.args[1:-1]: # 0 is nick, -1 is "are supported"
            if '=' in arg:
                (name, value) = arg.split('=', 1)
                converter = self._005converters.get(name, lambda x: x)
                try:
                    self.supported[name] = converter(value)
                except Exception:
                    log.exception('Uncaught exception in 005 converter:')
                    log.error('Name: %s, Converter: %s', name, converter)
            else:
                self.supported[arg] = None

    def do352(self, irc, msg):
        # WHO reply.

        (nick, user, host) = (msg.args[5], msg.args[2], msg.args[3])
        hostmask = '%s!%s@%s' % (nick, user, host)
        self.nicksToHostmasks[nick] = hostmask

    def do354(self, irc, msg):
        # WHOX reply.

        if len(msg.args) != 6 or msg.args[1] != '1':
            return

        (__, ___, user, host, nick, ___) = msg.args
        hostmask = '%s!%s@%s' % (nick, user, host)
        self.nicksToHostmasks[nick] = hostmask

    def do353(self, irc, msg):
        # NAMES reply.
        (__, type, channel, items) = msg.args
        if channel not in self.channels:
            self.channels[channel] = ChannelState()
        c = self.channels[channel]
        for item in items.split():
            if ircutils.isUserHostmask(item):
                name = ircutils.nickFromHostmask(item)
                self.nicksToHostmasks[name] = name
            else:
                name = item
            c.addUser(name)
        if type == '@':
            c.modes['s'] = None

    def doChghost(self, irc, msg):
        (user, host) = msg.args
        nick = msg.nick
        hostmask = '%s!%s@%s' % (nick, user, host)
        self.nicksToHostmasks[nick] = hostmask

    def doJoin(self, irc, msg):
        for channel in msg.args[0].split(','):
            if channel in self.channels:
                self.channels[channel].addUser(msg.nick)
            elif msg.nick: # It must be us.
                chan = ChannelState()
                chan.addUser(msg.nick)
                self.channels[channel] = chan
                # I don't know why this assert was here.
                #assert msg.nick == irc.nick, msg

    def do367(self, irc, msg):
        # Example:
        # :server 367 user #chan some!random@user evil!channel@op 1356276459
        try:
            state = self.channels[msg.args[1]]
        except KeyError:
            # We have been kicked of the channel before the server replied to
            # the MODE +b command.
            pass
        else:
            state.bans.add(msg.args[2])

    def doMode(self, irc, msg):
        channel = msg.args[0]
        if ircutils.isChannel(channel): # There can be user modes, as well.
            try:
                chan = self.channels[channel]
            except KeyError:
                chan = ChannelState()
                self.channels[channel] = chan
            chan.doMode(msg)

    def do324(self, irc, msg):
        channel = msg.args[1]
        try:
            chan = self.channels[channel]
        except KeyError:
            chan = ChannelState()
            self.channels[channel] = chan
        for (mode, value) in ircutils.separateModes(msg.args[2:]):
            modeChar = mode[1]
            if mode[0] == '+' and mode[1] not in 'ovh':
                chan.setMode(modeChar, value)
            elif mode[0] == '-' and mode[1] not in 'ovh':
                chan.unsetMode(modeChar)

    def do329(self, irc, msg):
        # This is the last part of an empty mode.
        channel = msg.args[1]
        try:
            chan = self.channels[channel]
        except KeyError:
            chan = ChannelState()
            self.channels[channel] = chan
        chan.created = int(msg.args[2])

    def doPart(self, irc, msg):
        for channel in msg.args[0].split(','):
            try:
                chan = self.channels[channel]
            except KeyError:
                continue
            if ircutils.strEqual(msg.nick, irc.nick):
                del self.channels[channel]
            else:
                chan.removeUser(msg.nick)

    def doKick(self, irc, msg):
        (channel, users) = msg.args[:2]
        chan = self.channels[channel]
        for user in users.split(','):
            if ircutils.strEqual(user, irc.nick):
                del self.channels[channel]
                return
            else:
                chan.removeUser(user)

    def doQuit(self, irc, msg):
        channel_names = ircutils.IrcSet()
        for (name, channel) in self.channels.items():
            if msg.nick in channel.users:
                channel_names.add(name)
                channel.removeUser(msg.nick)
        # Remember which channels the user was on
        msg.tag('channels', channel_names)
        if msg.nick in self.nicksToHostmasks:
            # If we're quitting, it may not be.
            del self.nicksToHostmasks[msg.nick]

    def doTopic(self, irc, msg):
        if len(msg.args) == 1:
            return # Empty TOPIC for information.  Does not affect state.
        try:
            chan = self.channels[msg.args[0]]
            chan.topic = msg.args[1]
        except KeyError:
            pass # We don't have to be in a channel to send a TOPIC.

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
        channel_names = ircutils.IrcSet()
        for (name, channel) in self.channels.items():
            if msg.nick in channel.users:
                channel_names.add(name)
            channel.replaceUser(oldNick, newNick)
        msg.tag('channels', channel_names)

    def doBatch(self, irc, msg):
        batch_name = msg.args[0][1:]
        if msg.args[0].startswith('+'):
            batch_type = msg.args[1]
            batch_arguments = tuple(msg.args[2:])
            self.batches[batch_name] = Batch(type=batch_type,
                    arguments=batch_arguments, messages=[])
        elif msg.args[0].startswith('-'):
            batch = self.batches.pop(batch_name)
            msg.tag('batch', batch)
        else:
            assert False, msg.args[0]

    def doAway(self, irc, msg):
        channel_names = ircutils.IrcSet()
        for (name, channel) in self.channels.items():
            if msg.nick in channel.users:
                channel_names.add(name)
        msg.tag('channels', channel_names)


###
# The basic class for handling a connection to an IRC server.  Accepts
# callbacks of the IrcCallback interface.  Public attributes include 'driver',
# 'queue', and 'state', in addition to the standard nick/user/ident attributes.
###
_callbacks = []
class Irc(IrcCommandDispatcher, log.Firewalled):
    """The base class for an IRC connection.

    Handles PING commands already.
    """
    __firewalled__ = {'die': None,
                      'feedMsg': None,
                      'takeMsg': None,}
    _nickSetters = set(['001', '002', '003', '004', '250', '251', '252',
                        '254', '255', '265', '266', '372', '375', '376',
                        '333', '353', '332', '366', '005'])
    # We specifically want these callbacks to be common between all Ircs,
    # that's why we don't do the normal None default with a check.
    def __init__(self, network, callbacks=_callbacks):
        self.zombie = False
        world.ircs.append(self)
        self.network = network
        self.startedAt = time.time()
        self.callbacks = callbacks
        self.state = IrcState()
        self.queue = IrcMsgQueue()
        self.fastqueue = smallqueue()
        self.driver = None # The driver should set this later.
        self._setNonResettingVariables()
        self._queueConnectMessages()
        self.startedSync = ircutils.IrcDict()
        self.monitoring = ircutils.IrcDict()

    def isChannel(self, s):
        """Helper function to check whether a given string is a channel on
        the network this Irc object is connected to."""
        kw = {}
        if 'chantypes' in self.state.supported:
            kw['chantypes'] = self.state.supported['chantypes']
        if 'channellen' in self.state.supported:
            kw['channellen'] = self.state.supported['channellen']
        return ircutils.isChannel(s, **kw)

    def isNick(self, s):
        kw = {}
        if 'nicklen' in self.state.supported:
            kw['nicklen'] = self.state.supported['nicklen']
        return ircutils.isNick(s, **kw)

    # This *isn't* threadsafe!
    def addCallback(self, callback):
        """Adds a callback to the callbacks list.

        :param callback: A callback object
        :type callback: supybot.irclib.IrcCallback
        """
        assert not self.getCallback(callback.name())
        self.callbacks.append(callback)
        # This is the new list we're building, which will be tsorted.
        cbs = []
        # The vertices are self.callbacks itself.  Now we make the edges.
        edges = set()
        for cb in self.callbacks:
            (before, after) = cb.callPrecedence(self)
            assert cb not in after, 'cb was in its own after.'
            assert cb not in before, 'cb was in its own before.'
            for otherCb in before:
                edges.add((otherCb, cb))
            for otherCb in after:
                edges.add((cb, otherCb))
        def getFirsts():
            firsts = set(self.callbacks) - set(cbs)
            for (before, after) in edges:
                firsts.discard(after)
            return firsts
        firsts = getFirsts()
        while firsts:
            # Then we add these to our list of cbs, and remove all edges that
            # originate with these cbs.
            for cb in firsts:
                cbs.append(cb)
                edgesToRemove = []
                for edge in edges:
                    if edge[0] is cb:
                        edgesToRemove.append(edge)
                for edge in edgesToRemove:
                    edges.remove(edge)
            firsts = getFirsts()
        assert len(cbs) == len(self.callbacks), \
               'cbs: %s, self.callbacks: %s' % (cbs, self.callbacks)
        self.callbacks[:] = cbs

    def getCallback(self, name):
        """Gets a given callback by name."""
        name = name.lower()
        for callback in self.callbacks:
            if callback.name().lower() == name:
                return callback
        else:
            return None

    def removeCallback(self, name):
        """Removes a callback from the callback list."""
        name = name.lower()
        def nameMatches(cb):
            return cb.name().lower() == name
        (bad, good) = utils.iter.partition(nameMatches, self.callbacks)
        self.callbacks[:] = good
        return bad

    def queueMsg(self, msg):
        """Queues a message to be sent to the server."""
        if not self.zombie:
            return self.queue.enqueue(msg)
        else:
            log.warning('Refusing to queue %r; %s is a zombie.', msg, self)
            return False

    def sendMsg(self, msg):
        """Queues a message to be sent to the server *immediately*"""
        if not self.zombie:
            self.fastqueue.enqueue(msg)
        else:
            log.warning('Refusing to send %r; %s is a zombie.', msg, self)

    def takeMsg(self):
        """Called by the IrcDriver; takes a message to be sent."""
        if not self.callbacks:
            log.critical('No callbacks in %s.', self)
        now = time.time()
        msg = None
        if self.fastqueue:
            msg = self.fastqueue.dequeue()
        elif self.queue:
            if now-self.lastTake <= conf.supybot.protocols.irc.throttleTime():
                log.debug('Irc.takeMsg throttling.')
            else:
                self.lastTake = now
                msg = self.queue.dequeue()
        elif self.afterConnect and \
             conf.supybot.protocols.irc.ping() and \
             now > self.lastping + conf.supybot.protocols.irc.ping.interval():
            if self.outstandingPing:
                s = 'Ping sent at %s not replied to.' % \
                    log.timestamp(self.lastping)
                log.warning(s)
                self.feedMsg(ircmsgs.error(s))
                self.driver.reconnect()
            elif not self.zombie:
                self.lastping = now
                now = str(int(now))
                self.outstandingPing = True
                self.queueMsg(ircmsgs.ping(now))
        if msg:
            for callback in reversed(self.callbacks):
                msg = callback.outFilter(self, msg)
                if msg is None:
                    log.debug('%s.outFilter returned None.', callback.name())
                    return self.takeMsg()
                world.debugFlush()
            if len(str(msg)) > 512:
                # Yes, this violates the contract, but at this point it doesn't
                # matter.  That's why we gotta go munging in private attributes
                #
                # I'm changing this to a log.debug to fix a possible loop in
                # the LogToIrc plugin.  Since users can't do anything about
                # this issue, there's no fundamental reason to make it a
                # warning.
                log.debug('Truncating %r, message is too long.', msg)
                msg._str = msg._str[:500] + '\r\n'
                msg._len = len(str(msg))
            # I don't think we should do this.  Why should it matter?  If it's
            # something important, then the server will send it back to us,
            # and if it's just a privmsg/notice/etc., we don't care.
            # On second thought, we need this for testing.
            if world.testing:
                self.state.addMsg(self, msg)
            log.debug('Outgoing message (%s): %s', self.network, str(msg).rstrip('\r\n'))
            return msg
        elif self.zombie:
            # We kill the driver here so it doesn't continue to try to
            # take messages from us.
            self.driver.die()
            self._reallyDie()
        else:
            return None

    _numericErrorCommandRe = re.compile(r'^[45][0-9][0-9]$')
    def feedMsg(self, msg):
        """Called by the IrcDriver; feeds a message received."""
        msg.tag('receivedBy', self)
        msg.tag('receivedOn', self.network)
        msg.tag('receivedAt', time.time())
        if msg.args and self.isChannel(msg.args[0]):
            channel = msg.args[0]
        else:
            channel = None
        preInFilter = str(msg).rstrip('\r\n')
        log.debug('Incoming message (%s): %s', self.network, preInFilter)

        # Yeah, so this is odd.  Some networks (oftc) seem to give us certain
        # messages with our nick instead of our prefix.  We'll fix that here.
        if msg.prefix == self.nick:
            log.debug('Got one of those odd nick-instead-of-prefix msgs.')
            msg = ircmsgs.IrcMsg(prefix=self.prefix, msg=msg)

        # This catches cases where we know our own nick (from sending it to the
        # server) but we don't yet know our prefix.
        if msg.nick == self.nick and self.prefix != msg.prefix:
            self.prefix = msg.prefix

        # This keeps our nick and server attributes updated.
        if msg.command in self._nickSetters:
            if msg.args[0] != self.nick:
                self.nick = msg.args[0]
                log.debug('Updating nick attribute to %s.', self.nick)
            if msg.prefix != self.server:
                self.server = msg.prefix
                log.debug('Updating server attribute to %s.', self.server)

        # Dispatch to specific handlers for commands.
        method = self.dispatchCommand(msg.command)
        if method is not None:
            method(msg)
        elif self._numericErrorCommandRe.search(msg.command):
            log.error('Unhandled error message from server: %r' % msg)

        # Now update the IrcState object.
        try:
            self.state.addMsg(self, msg)
        except:
            log.exception('Exception in update of IrcState object:')

        # Now call the callbacks.
        world.debugFlush()
        for callback in self.callbacks:
            try:
                m = callback.inFilter(self, msg)
                if not m:
                    log.debug('%s.inFilter returned None', callback.name())
                    return
                msg = m
            except:
                log.exception('Uncaught exception in inFilter:')
            world.debugFlush()
        postInFilter = str(msg).rstrip('\r\n')
        if postInFilter != preInFilter:
            log.debug('Incoming message (post-inFilter): %s', postInFilter)
        for callback in self.callbacks:
            try:
                if callback is not None:
                    callback(self, msg)
            except:
                log.exception('Uncaught exception in callback:')
            world.debugFlush()

    def die(self):
        """Makes the Irc object *promise* to die -- but it won't die (of its
        own volition) until all its queues are clear.  Isn't that cool?"""
        self.zombie = True
        if not self.afterConnect:
            self._reallyDie()

    # This is useless because it's in world.ircs, so it won't be deleted until
    # the program exits.  Just figured you might want to know.
    #def __del__(self):
    #    self._reallyDie()

    def reset(self):
        """Resets the Irc object.  Called when the driver reconnects."""
        self._setNonResettingVariables()
        self.state.reset()
        self.queue.reset()
        self.fastqueue.reset()
        self.startedSync.clear()
        for callback in self.callbacks:
            callback.reset()
        self._queueConnectMessages()

    def _setNonResettingVariables(self):
        # Configuration stuff.
        network_config = conf.supybot.networks.get(self.network)
        def get_value(name):
            return getattr(network_config, name)() or \
                getattr(conf.supybot, name)()
        self.nick = get_value('nick')
        self.user = get_value('user')
        self.ident = get_value('ident')
        self.alternateNicks = conf.supybot.nick.alternates()[:]
        self.password = network_config.password()
        self.prefix = '%s!%s@%s' % (self.nick, self.ident, 'unset.domain')
        # The rest.
        self.lastTake = 0
        self.server = 'unset'
        self.afterConnect = False
        self.startedAt = time.time()
        self.lastping = time.time()
        self.outstandingPing = False
        self.capNegociationEnded = False
        self.requireStarttls = not network_config.ssl() and \
                network_config.requireStarttls()
        self.resetSasl()

    def resetSasl(self):
        network_config = conf.supybot.networks.get(self.network)
        self.sasl_authenticated = False
        self.sasl_username = network_config.sasl.username()
        self.sasl_password = network_config.sasl.password()
        self.sasl_ecdsa_key = network_config.sasl.ecdsa_key()
        self.authenticate_decoder = None
        self.sasl_next_mechanisms = []
        self.sasl_current_mechanism = None

        for mechanism in network_config.sasl.mechanisms():
            if mechanism == 'ecdsa-nist256p-challenge' and \
                    ecdsa and self.sasl_username and self.sasl_ecdsa_key:
                self.sasl_next_mechanisms.append(mechanism)
            elif mechanism == 'external' and (
                    network_config.certfile() or
                    conf.supybot.protocols.irc.certfile()):
                self.sasl_next_mechanisms.append(mechanism)
            elif mechanism == 'plain' and \
                    self.sasl_username and self.sasl_password:
                self.sasl_next_mechanisms.append(mechanism)

        if self.sasl_next_mechanisms:
            self.REQUEST_CAPABILITIES.add('sasl')


    REQUEST_CAPABILITIES = set(['account-notify', 'extended-join',
        'multi-prefix', 'metadata-notify', 'account-tag',
        'userhost-in-names', 'invite-notify', 'server-time',
        'chghost', 'batch', 'away-notify'])

    def _queueConnectMessages(self):
        if self.zombie:
            self.driver.die()
            self._reallyDie()

            return

        self.sendMsg(ircmsgs.IrcMsg(command='CAP', args=('LS', '302')))

        if self.requireStarttls:
            self.sendMsg(ircmsgs.IrcMsg(command='STARTTLS'))
        else:
            self.sendAuthenticationMessages()

    def do670(self, irc, msg):
        """STARTTLS accepted."""
        log.info('%s: Starting TLS session.', self.network)
        self.requireStarttls = False
        self.driver.starttls()
        self.sendAuthenticationMessages()
    def do691(self, irc, msg):
        """STARTTLS refused."""
        log.error('%s: Server refused STARTTLS: %s', self.network, msg.args[0])
        self.feedMsg(ircmsgs.error('STARTTLS upgrade refused by the server'))
        self.driver.reconnect()

    def sendAuthenticationMessages(self):
        # Notes:
        # * using sendMsg instead of queueMsg because these messages cannot
        #   be throttled.

        if self.password:
            log.info('%s: Queuing PASS command, not logging the password.',
                     self.network)
            self.sendMsg(ircmsgs.password(self.password))

        log.debug('%s: Sending NICK command, nick is %s.',
                  self.network, self.nick)

        self.sendMsg(ircmsgs.nick(self.nick))

        log.debug('%s: Sending USER command, ident is %s, user is %s.',
                  self.network, self.ident, self.user)

        self.sendMsg(ircmsgs.user(self.ident, self.user))

    def endCapabilityNegociation(self):
        if not self.capNegociationEnded:
            self.capNegociationEnded = True
            self.sendMsg(ircmsgs.IrcMsg(command='CAP', args=('END',)))

    def sendSaslString(self, string):
        for chunk in ircutils.authenticate_generator(string):
            self.sendMsg(ircmsgs.IrcMsg(command='AUTHENTICATE',
                args=(chunk,)))

    def tryNextSaslMechanism(self):
        if self.sasl_next_mechanisms:
            self.sasl_current_mechanism = self.sasl_next_mechanisms.pop(0)
            self.sendMsg(ircmsgs.IrcMsg(command='AUTHENTICATE',
                args=(self.sasl_current_mechanism.upper(),)))
        else:
            self.sasl_current_mechanism = None
            self.endCapabilityNegociation()

    def filterSaslMechanisms(self, available):
        available = set(map(str.lower, available))
        self.sasl_next_mechanisms = [
                x for x in self.sasl_next_mechanisms
                if x.lower() in available]

    def doAuthenticate(self, msg):
        if not self.authenticate_decoder:
            self.authenticate_decoder = ircutils.AuthenticateDecoder()
        self.authenticate_decoder.feed(msg)
        if not self.authenticate_decoder.ready:
            return # Waiting for other messages
        string = self.authenticate_decoder.get()
        self.authenticate_decoder = None

        mechanism = self.sasl_current_mechanism
        if mechanism == 'ecdsa-nist256p-challenge':
            if string == b'':
                self.sendSaslString(self.sasl_username.encode('utf-8'))
                return
            try:
                with open(self.sasl_ecdsa_key) as fd:
                    private_key = SigningKey.from_pem(fd.read())
                authstring = private_key.sign(base64.b64decode(msg.args[0].encode()))
                self.sendSaslString(authstring)
            except (BadDigestError, OSError, ValueError):
                self.sendMsg(ircmsgs.IrcMsg(command='AUTHENTICATE',
                    args=('*',)))
                self.tryNextSaslMechanism()
        elif mechanism == 'external':
            self.sendSaslString(b'')
        elif mechanism == 'plain':
            authstring = b'\0'.join([
                self.sasl_username.encode('utf-8'),
                self.sasl_username.encode('utf-8'),
                self.sasl_password.encode('utf-8'),
            ])
            self.sendSaslString(authstring)

    def do903(self, msg):
        log.info('%s: SASL authentication successful', self.network)
        self.sasl_authenticated = True
        self.endCapabilityNegociation()

    def do904(self, msg):
        log.warning('%s: SASL authentication failed', self.network)
        self.tryNextSaslMechanism()

    def do905(self, msg):
        log.warning('%s: SASL authentication failed because the username or '
                    'password is too long.', self.network)
        self.tryNextSaslMechanism()

    def do906(self, msg):
        log.warning('%s: SASL authentication aborted', self.network)
        self.tryNextSaslMechanism()

    def do907(self, msg):
        log.warning('%s: Attempted SASL authentication when we were already '
                    'authenticated.', self.network)
        self.tryNextSaslMechanism()

    def do908(self, msg):
        log.info('%s: Supported SASL mechanisms: %s',
                 self.network, msg.args[1])
        self.filterSaslMechanisms(set(msg.args[1].split(',')))

    def doCap(self, msg):
        subcommand = msg.args[1]
        if subcommand == 'ACK':
            self.doCapAck(msg)
        elif subcommand == 'NAK':
            self.doCapNak(msg)
        elif subcommand == 'LS':
            self.doCapLs(msg)
        elif subcommand == 'DEL':
            self.doCapDel(msg)
        elif subcommand == 'NEW':
            self.doCapNew(msg)
    def doCapAck(self, msg):
        if len(msg.args) != 3:
            log.warning('Bad CAP ACK from server: %r', msg)
            return
        caps = msg.args[2].split()
        assert caps, 'Empty list of capabilities'
        log.debug('%s: Server acknowledged capabilities: %L',
                 self.network, caps)
        self.state.capabilities_ack.update(caps)

        if 'sasl' in caps:
            self.tryNextSaslMechanism()
        else:
            self.endCapabilityNegociation()
    def doCapNak(self, msg):
        if len(msg.args) != 3:
            log.warning('Bad CAP NAK from server: %r', msg)
            return
        caps = msg.args[2].split()
        assert caps, 'Empty list of capabilities'
        self.state.capabilities_nak.update(caps)
        log.warning('%s: Server refused capabilities: %L',
                    self.network, caps)
        self.endCapabilityNegociation()
    def _addCapabilities(self, capstring):
        for item in capstring.split():
            while item.startswith(('=', '~')):
                item = item[1:]
            if '=' in item:
                (cap, value) = item.split('=', 1)
                self.state.capabilities_ls[cap] = value
            else:
                self.state.capabilities_ls[item] = None
    def doCapLs(self, msg):
        if len(msg.args) == 4:
            # Multi-line LS
            if msg.args[2] != '*':
                log.warning('Bad CAP LS from server: %r', msg)
                return
            self._addCapabilities(msg.args[3])
        elif len(msg.args) == 3: # End of LS
            self._addCapabilities(msg.args[2])
            common_supported_capabilities = set(self.state.capabilities_ls) & \
                    self.REQUEST_CAPABILITIES
            if 'sasl' in self.state.capabilities_ls:
                s = self.state.capabilities_ls['sasl']
                if s is not None:
                    self.filterSaslMechanisms(set(s.split(',')))
            if 'starttls' not in self.state.capabilities_ls and \
                    self.requireStarttls:
                log.error('%s: Server does not support STARTTLS.', self.network)
                self.feedMsg(ircmsgs.error('STARTTLS upgrade not supported '
                    'by the server'))
                self.die()
                return
            # NOTE: Capabilities are requested in alphabetic order, because
            # sets are unordered, and their "order" is nondeterministic.
            # This is needed for the tests.
            if common_supported_capabilities:
                caps = ' '.join(sorted(common_supported_capabilities))
                self.sendMsg(ircmsgs.IrcMsg(command='CAP',
                    args=('REQ', caps)))
            else:
                self.endCapabilityNegociation()
        else:
            log.warning('Bad CAP LS from server: %r', msg)
            return
    def doCapDel(self, msg):
        if len(msg.args) != 3:
            log.warning('Bad CAP DEL from server: %r', msg)
            return
        caps = msg.args[2].split()
        assert caps, 'Empty list of capabilities'
        for cap in caps:
            # The spec says "If capability negotiation 3.2 was used, extensions
            # listed MAY contain values." for CAP NEW and CAP DEL
            cap = cap.split('=')[0]
            try:
                del self.state.capabilities_ls[cap]
            except KeyError:
                pass
            try:
                self.state.capabilities_ack.remove(cap)
            except KeyError:
                pass
    def doCapNew(self, msg):
        if len(msg.args) != 3:
            log.warning('Bad CAP NEW from server: %r', msg)
            return
        caps = msg.args[2].split()
        assert caps, 'Empty list of capabilities'
        self._addCapabilities(msg.args[2])
        if not self.sasl_authenticated and 'sasl' in self.state.capabilities_ls:
            self.resetSasl()
            s = self.state.capabilities_ls['sasl']
            if s is not None:
                self.filterSaslMechanisms(set(s.split(',')))
        common_supported_unrequested_capabilities = (
                set(self.state.capabilities_ls) &
                self.REQUEST_CAPABILITIES -
                self.state.capabilities_ack)
        if common_supported_unrequested_capabilities:
            caps = ' '.join(sorted(common_supported_unrequested_capabilities))
            self.sendMsg(ircmsgs.IrcMsg(command='CAP',
                args=('REQ', caps)))

    def monitor(self, targets):
        """Increment a counter of how many callbacks monitor each target;
        and send a MONITOR + to the server if the target is not yet
        monitored."""
        if isinstance(targets, str):
            targets = [targets]
        not_yet_monitored = set()
        for target in targets:
            if target in self.monitoring:
                self.monitoring[target] += 1
            else:
                not_yet_monitored.add(target)
                self.monitoring[target] = 1
        if not_yet_monitored:
            self.queueMsg(ircmsgs.monitor('+', not_yet_monitored))
        return not_yet_monitored

    def unmonitor(self, targets):
        """Decrements a counter of how many callbacks monitor each target;
        and send a MONITOR - to the server if the counter drops to 0."""
        if isinstance(targets, str):
            targets = [targets]
        should_be_unmonitored = set()
        for target in targets:
            self.monitoring[target] -= 1
            if self.monitoring[target] == 0:
                del self.monitoring[target]
                should_be_unmonitored.add(target)
        if should_be_unmonitored:
            self.queueMsg(ircmsgs.monitor('-', should_be_unmonitored))
        return should_be_unmonitored

    def _getNextNick(self):
        if self.alternateNicks:
            nick = self.alternateNicks.pop(0)
            if '%s' in nick:
                network_nick = conf.supybot.networks.get(self.network).nick()
                if network_nick == '':
                    nick %= conf.supybot.nick()
                else:
                    nick %= network_nick
            return nick
        else:
            nick = conf.supybot.nick()
            network_nick = conf.supybot.networks.get(self.network).nick()
            if network_nick != '':
                nick = network_nick
            ret = nick
            L = list(nick)
            while len(L) <= 3:
                L.append('`')
            while ircutils.strEqual(ret, nick):
                L[random.randrange(len(L))] = utils.iter.choice('0123456789')
                ret = ''.join(L)
            return ret

    def do002(self, msg):
        """Logs the ircd version."""
        (beginning, version) = rsplit(msg.args[-1], maxsplit=1)
        log.info('Server %s has version %s', self.server, version)

    def doPing(self, msg):
        """Handles PING messages."""
        self.sendMsg(ircmsgs.pong(msg.args[0]))

    def doPong(self, msg):
        """Handles PONG messages."""
        self.outstandingPing = False

    def do376(self, msg):
        log.info('Got end of MOTD from %s', self.server)
        self.afterConnect = True
        # Let's reset nicks in case we had to use a weird one.
        self.alternateNicks = conf.supybot.nick.alternates()[:]
        umodes = conf.supybot.networks.get(self.network).umodes()
        if umodes == '':
            umodes = conf.supybot.protocols.irc.umodes()
        supported = self.state.supported.get('umodes')
        if supported:
            acceptedchars = supported.union('+-')
            umodes = ''.join([m for m in umodes if m in acceptedchars])
        if umodes:
            log.info('Sending user modes to %s: %s', self.network, umodes)
            self.sendMsg(ircmsgs.mode(self.nick, umodes))
    do377 = do422 = do376

    def do43x(self, msg, problem):
        if not self.afterConnect:
            newNick = self._getNextNick()
            assert newNick != self.nick
            log.info('Got %s: %s %s.  Trying %s.',
                     msg.command, self.nick, problem, newNick)
            self.sendMsg(ircmsgs.nick(newNick))
    def do437(self, msg):
        self.do43x(msg, 'is temporarily unavailable')
    def do433(self, msg):
        self.do43x(msg, 'is in use')
    def do432(self, msg):
        self.do43x(msg, 'is not a valid nickname')

    def doJoin(self, msg):
        if msg.nick == self.nick:
            channel = msg.args[0]
            self.queueMsg(ircmsgs.who(channel, args=('%tuhna,1',))) # Ends with 315.
            self.queueMsg(ircmsgs.mode(channel)) # Ends with 329.
            for channel in msg.args[0].split(','):
                self.queueMsg(ircmsgs.mode(channel, '+b'))
            self.startedSync[channel] = time.time()

    def do315(self, msg):
        channel = msg.args[1]
        if channel in self.startedSync:
            now = time.time()
            started = self.startedSync.pop(channel)
            elapsed = now - started
            log.info('Join to %s on %s synced in %.2f seconds.',
                     channel, self.network, elapsed)

    def doError(self, msg):
        """Handles ERROR messages."""
        log.warning('Error message from %s: %s', self.network, msg.args[0])
        if not self.zombie:
           if msg.args[0].lower().startswith('closing link'):
              self.driver.reconnect()
           elif 'too fast' in msg.args[0]: # Connecting too fast.
              self.driver.reconnect(wait=True)

    def doNick(self, msg):
        """Handles NICK messages."""
        if msg.nick == self.nick:
            newNick = msg.args[0]
            self.nick = newNick
            (nick, user, domain) = ircutils.splitHostmask(msg.prefix)
            self.prefix = ircutils.joinHostmask(self.nick, user, domain)
        elif conf.supybot.followIdentificationThroughNickChanges():
            # We use elif here because this means it's someone else's nick
            # change, not our own.
            try:
                id = ircdb.users.getUserId(msg.prefix)
                u = ircdb.users.getUser(id)
            except KeyError:
                return
            if u.auth:
                (_, user, host) = ircutils.splitHostmask(msg.prefix)
                newhostmask = ircutils.joinHostmask(msg.args[0], user, host)
                for (i, (when, authmask)) in enumerate(u.auth[:]):
                    if ircutils.strEqual(msg.prefix, authmask):
                        log.info('Following identification for %s: %s -> %s',
                                 u.name, authmask, newhostmask)
                        u.auth[i] = (u.auth[i][0], newhostmask)
                        ircdb.users.setUser(u)

    def _reallyDie(self):
        """Makes the Irc object die.  Dead."""
        log.info('Irc object for %s dying.', self.network)
        # XXX This hasattr should be removed, I'm just putting it here because
        #     we're so close to a release.  After 0.80.0 we should remove this
        #     and fix whatever AttributeErrors arise in the drivers themselves.
        if self.driver is not None and hasattr(self.driver, 'die'):
            self.driver.die()
        if self in world.ircs:
            world.ircs.remove(self)
            # Only kill the callbacks if we're the last Irc.
            if not world.ircs:
                for cb in self.callbacks:
                    cb.die()
                # If we shared our list of callbacks, this ensures that
                # cb.die() is only called once for each callback.  It's
                # not really necessary since we already check to make sure
                # we're the only Irc object, but a little robustitude never
                # hurt anybody.
                log.debug('Last Irc, clearing callbacks.')
                self.callbacks[:] = []
        else:
            log.warning('Irc object killed twice: %s', utils.stackTrace())

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        # We check isinstance here, so that if some proxy object (like those
        # defined in callbacks.py) has overridden __eq__, it takes precedence.
        if isinstance(other, self.__class__):
            return id(self) == id(other)
        else:
            return other.__eq__(self)

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return 'Irc object for %s' % self.network

    def __repr__(self):
        return '<irclib.Irc object for %s>' % self.network


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
