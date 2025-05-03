###
# Copyright (c) 2002-2005 Jeremiah Fincher
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

import re
import copy
import time
import enum
import random
import base64
import textwrap
import warnings
import collections

try:
    class crypto:
        import cryptography
        from cryptography.hazmat.primitives.serialization \
            import load_pem_private_key
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
        from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
        from cryptography.hazmat.primitives.hashes import SHA256
except ImportError:
    crypto = None

try:
    import pyxmpp2_scram as scram
except ImportError:
    scram = None

from . import conf, ircdb, ircmsgs, ircutils, log, utils, world
from .drivers import Server
from .utils.str import rsplit
from .utils.iter import chain
from .utils.structures import smallqueue, RingBuffer, ExpiringDict

MAX_LINE_SIZE = 512 # Including \r\n, but excluding server_tags

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

    def dispatchCommand(self, command, args=None):
        """Given a string 'command', dispatches to doCommand."""
        if args is None:
            warnings.warn(
                "dispatchCommand now takes an 'args' attribute, which is "
                "a list of the command's arguments (ie. IrcMsg.args).",
                DeprecationWarning)
            args = []

        command = command.upper()
        subcommand = None
        method = None

        # Dispatch on command + subcommand, if there is a subcommand, and
        # a method with the matching name exists
        if command in ('FAIL', 'WARN', 'NOTE') and len(args) >= 1:
            subcommand = args[0]
        elif command in ('CAP',) and len(args) >= 2:
            # Note: this only covers the server-to-client format
            subcommand = args[1]

        command = command.capitalize()

        if subcommand is not None:
            subcommand = subcommand.capitalize()
            method = getattr(self, 'do' + command + subcommand, None)

        # If not dispatched on command + subcommand, then dispatch on command
        if method is None:
            method = getattr(self, 'do' + command, None)

        return method


class IrcCallback(IrcCommandDispatcher, log.Firewalled):
    """Base class for standard callbacks.

    Callbacks derived from this class should have methods of the form
    "doCommand" -- doPrivmsg, doNick, do433, etc.  These will be called
    on matching messages.
    """
    callAfter = ()
    callBefore = ()
    echoMessage = False
    echo_message = False  # deprecated alias of echoMessage
    __firewalled__ = {'die': None,
                      'reset': None,
                      '__call__': None,
                      'inFilter': lambda self, irc, msg: msg,
                      'outFilter': lambda self, irc, msg: msg,
                      'postTransition': None,
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

    def postTransition(self, irc, msg, from_state, to_state):
        """Called when the state of the IRC connection changes.

        `msg` is the message that triggered the transition, if any."""
        pass

    def __call__(self, irc, msg):
        """Used for handling each message."""
        if not self.echoMessage and not self.echo_message \
                and msg.command in ('PRIVMSG', 'NOTICE', 'TAGMSG') \
                and ('label' in msg.server_tags
                     or msg.tagged('emulatedEcho')):
            # This is an echo of a message we sent; and the plugin didn't
            # opt-in to receiving echos; ignoring it.
            # `'label' in msg.server_tags` detects echos when labeled-response
            # is enabled; and `msg.tag('emulatedEcho')` detects simulated
            # echos. As we don't enable real echo-message unless
            # labeled-response is enabled; this is an exhaustive check of echos
            # in all cases.
            # See "When a client sends a private message to its own nick" at
            # <https://ircv3.net/specs/extensions/labeled-response>
            return
        method = self.dispatchCommand(msg.command, msg.args)
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
_high = frozenset(['MODE', 'KICK', 'PONG', 'NICK', 'PASS', 'CAPAB', 'REMOVE'])
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
    """Represents the known state of an IRC channel.

    .. attribute:: topic

        The topic of a channel (possibly the empty stringà

        :type: str

    .. attribute:: created

        Timestamp of the channel creation, according to the server.

        :type: int

    .. attribute:: ops

        Set of the nicks of all the operators of the channel.

        :type: ircutils.IrcSet[str]

    .. attribute:: halfops

        Set of the nicks of all the half-operators of the channel.

        :type: ircutils.IrcSet[str]

    .. attribute:: voices

        Set of the nicks of all the voiced users of the channel.

        :type: ircutils.IrcSet[str]

    .. attribute:: users

        Set of the nicks of all the users in the channel.

        :type: ircutils.IrcSet[str]

    .. attribute:: bans

        Set of the all the banmasks set in the channel.

        :type: ircutils.IrcSet[str]

    .. attribute:: modes

        Dict of all the modes set in the channel, with they value, if any.
        This excludes the following modes: ovhbeq

        :type: Dict[str, Optional[str]]
    """

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
        """Returns whether the given nick is an op."""
        return nick in self.ops

    def isOpPlus(self, nick):
        """Returns whether the given nick is an op."""
        return nick in self.ops

    def isVoice(self, nick):
        """Returns whether the given nick is voiced."""
        return nick in self.voices

    def isVoicePlus(self, nick):
        """Returns whether the given nick is voiced, an halfop, or an op."""
        return nick in self.voices or nick in self.halfops or nick in self.ops

    def isHalfop(self, nick):
        """Returns whether the given nick is an halfop."""
        return nick in self.halfops

    def isHalfopPlus(self, nick):
        """Returns whether the given nick is an halfop, or an op."""
        return nick in self.halfops or nick in self.ops

    def addUser(self, user, prefix_chars='@%+&~!'):
        "Adds a given user to the ChannelState.  Power prefixes are handled."
        nick = user.lstrip(prefix_chars)
        if not nick:
            return
        # & is used to denote protected users in UnrealIRCd
        # ~ is used to denote channel owner in UnrealIRCd
        # ! is used to denote protected users in UltimateIRCd
        while user and user[0] in prefix_chars:
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


Batch = collections.namedtuple('Batch', 'name type arguments messages parent_batch')
"""Represents a batch of messages, see
<https://ircv3.net/specs/extensions/batch-3.2>

Only access attributes by their name and do not create Batch objects
in plugins; so we can extend the structure without breaking plugins."""


class IrcStateFsm(object):
    '''Finite State Machine keeping track of what part of the connection
    initialization we are in.'''
    __slots__ = ('state',)

    @enum.unique
    class States(enum.Enum):
        """Enumeration of all the states of an IRC connection."""

        UNINITIALIZED = 10
        '''Nothing received yet (except server notices)'''

        INIT_CAP_NEGOTIATION = 20
        '''Sent CAP LS, did not send CAP END yet'''

        INIT_SASL = 30
        '''In an AUTHENTICATE session'''

        INIT_WAITING_MOTD = 50
        '''Waiting for start of MOTD'''

        INIT_MOTD = 60
        '''Waiting for end of MOTD'''

        CONNECTED = 70
        '''Normal state of the connections'''

        CONNECTED_SASL = 80
        '''Doing SASL authentication in the middle of a connection.'''

        SHUTTING_DOWN = 100

    def __init__(self):
        self.reset()

    def reset(self):
        if getattr(self, 'state', None) is not None:
            log.debug('resetting from %s to %s',
                self.state, self.States.UNINITIALIZED)
        self.state = self.States.UNINITIALIZED

    def _transition(self, irc, msg, to_state, expected_from=None):
        """Transitions to state `to_state`.

        If `expected_from` is not `None`, first checks the current state is
        in the set.

        After the transition, calls the
        `postTransition(irc, msg, from_state, to_state)` method of all objects
        in `irc.callbacks`.

        `msg` may be None if the transition isn't triggered by a message, but
        `irc` may not."""
        from_state = self.state
        if expected_from is None or from_state in expected_from:
            log.debug('transition from %s to %s', self.state, to_state)
            self.state = to_state
            for callback in reversed(irc.callbacks):
                msg = callback.postTransition(irc, msg, from_state, to_state)
        else:
            raise ValueError('unexpected transition to %s while in state %s' %
                (to_state, self.state))

    def expect_state(self, expected_states):
        if self.state not in expected_states:
            raise ValueError(('Connection in state %s, but expected to be '
                              'in state %s') % (self.state, expected_states))

    def on_init_messages_sent(self, irc):
        '''As soon as USER/NICK/CAP LS are sent'''
        self._transition(irc, None, self.States.INIT_CAP_NEGOTIATION, [
            self.States.UNINITIALIZED,
        ])

    def on_sasl_start(self, irc, msg):
        '''Whenever we initiate a SASL transaction.'''
        if self.state == self.States.INIT_CAP_NEGOTIATION:
            self._transition(irc, msg, self.States.INIT_SASL)
        elif self.state == self.States.CONNECTED:
            self._transition(irc, msg, self.States.CONNECTED_SASL)
        else:
            raise ValueError('Started SASL while in state %s' % self.state)

    def on_sasl_auth_finished(self, irc, msg):
        '''When sasl auth either succeeded or failed.'''
        if self.state == self.States.INIT_SASL:
            self._transition(irc, msg, self.States.INIT_CAP_NEGOTIATION)
        elif self.state == self.States.CONNECTED_SASL:
            self._transition(irc, msg, self.States.CONNECTED)
        else:
            raise ValueError('Finished SASL auth while in state %s' % self.state)

    def on_cap_end(self, irc, msg):
        '''When we send CAP END'''
        self._transition(irc, msg, self.States.INIT_WAITING_MOTD, [
            self.States.INIT_CAP_NEGOTIATION,
        ])

    def on_start_motd(self, irc, msg):
        '''On 375 (RPL_MOTDSTART)'''
        self._transition(irc, msg, self.States.INIT_MOTD, [
            self.States.INIT_CAP_NEGOTIATION,
            self.States.INIT_WAITING_MOTD,
            self.States.CONNECTED,
            self.States.CONNECTED_SASL,
        ])

    def on_end_motd(self, irc, msg):
        '''On 376 (RPL_ENDOFMOTD) or 422 (ERR_NOMOTD)'''
        self._transition(irc, msg, self.States.CONNECTED, [
            self.States.INIT_CAP_NEGOTIATION,
            self.States.INIT_WAITING_MOTD,
            self.States.INIT_MOTD,
            self.States.CONNECTED,
            self.States.CONNECTED_SASL,
        ])

    def on_shutdown(self, irc, msg):
        self._transition(irc, msg, self.States.SHUTTING_DOWN)

class IrcState(IrcCommandDispatcher, log.Firewalled):
    """Maintains state of the Irc connection.  Should also become smarter.

    .. attribute:: fsm

        A finite-state machine representing the current state of the IRC
        connection: various steps while connecting, then remains in the
        CONNECTED state (or CONNECTED_SASL when doing SASL in the middle of a
        connection).

        :type: IrcStateFsm

    .. attribute:: capabilities_req

        Set of all capabilities requested from the server.
        See <https://ircv3.net/specs/core/capability-negotiation>

        :type: Set[str]

    .. attribute:: capabilities_ack

        Set of all capabilities requested from and acknowledged by the
        server. See <https://ircv3.net/specs/core/capability-negotiation>

        :type: Set[str]

    .. attribute:: capabilities_nak

        Set of all capabilities requested from and refused by the server.
        This should always be empty unless the bot, a plugin, or the server is
        misbehaving. See <https://ircv3.net/specs/core/capability-negotiation>

        :type: Set[str]

    .. attribute:: capabilities_ls

        Stores all the capabilities advertised by the server, as well as their
        value, if any.

        :type: Dict[str, Optional[str]]

    .. attribute:: ircd

        Identification string of the software running the server we are
        connected to. See
        <https://defs.ircdocs.horse/defs/numerics.html#rpl-myinfo-004>

        :type: str

    .. attribute:: supported

        Stores the value of ISUPPORT sent when connecting.
        See <https://defs.ircdocs.horse/defs/isupport.html> for the list of
        keys.

        :type: utils.InsensitivePreservingDict[str, Any]

    .. attribute:: history

        History of messages received from the network. Automatically discards
        messages so it doesn't exceed
        ``supybot.protocols.irc.maxHistoryLength``.

        :type: RingBuffer[ircmsgs.IrcMsg]

    .. attribute:: channels

        Store channel states.

        :type: ircutils.IrcDict[str, ChannelState]

    .. attribute:: nicksToHostmasks

        Stores the last hostmask of a seen nick.

        :type: ircutils.IrcDict[str, str]

    .. attribute:: nicksToAccounts

        Stores the current services account name of a seen nick (or
        :const:`None` for un-identified nicks)

        :type: ircutils.IrcDict[str, Optional[str]]
    """
    __firewalled__ = {'addMsg': None}


    def __init__(self, history=None, supported=None,
                 nicksToHostmasks=None, channels=None,
                 capabilities_req=None,
                 capabilities_ack=None, capabilities_nak=None,
                 capabilities_ls=None,
                 nicksToAccounts=None):
        self.fsm = IrcStateFsm()
        if history is None:
            history = RingBuffer(conf.supybot.protocols.irc.maxHistoryLength())
        if supported is None:
            supported = utils.InsensitivePreservingDict()
        if nicksToHostmasks is None:
            nicksToHostmasks = ircutils.IrcDict()
        if nicksToAccounts is None:
            nicksToAccounts = ircutils.IrcDict()
        if channels is None:
            channels = ircutils.IrcDict()
        self.capabilities_req = capabilities_req or set()
        self.capabilities_ack = capabilities_ack or set()
        self.capabilities_nak = capabilities_nak or set()
        self.capabilities_ls = capabilities_ls or {}
        self.ircd = None
        self.supported = supported
        self.history = history
        self.channels = channels
        self.nicksToHostmasks = nicksToHostmasks
        self.nicksToAccounts = nicksToAccounts

        # Batches usually finish and are way shorter than 3600s, but
        # we need to:
        # * keep them in case the connection breaks (and reset() can't
        #   clear the list itself)
        # * make sure to avoid leaking memory in general
        self.batches = ExpiringDict(timeout=3600)

    def reset(self):
        """Resets the state to normal, unconnected state."""
        self.fsm.reset()
        self.history.reset()
        self.history.resize(conf.supybot.protocols.irc.maxHistoryLength())
        self.ircd = None
        self.channels.clear()
        self.supported.clear()
        self.nicksToHostmasks.clear()
        self.nicksToAccounts.clear()
        self.capabilities_req = set()
        self.capabilities_ack = set()
        self.capabilities_nak = set()
        self.capabilities_ls = {}

        # Don't clear batches right now. reset() is called on ERROR messages,
        # which may be part of a BATCH so we need to remember that batch.
        # At worst, the batch will expire in the near future, as self.batches
        # is an instance of ExpiringDict.
        # If we did clear the batch, then this would happen:
        # 1. IrcState.addMsg() would crash on the ERROR, because its batch
        #    server-tag references an unknown batch, so it would not set the
        #    'batch' supybot-tag
        # 2. Irc.doBatch would crash on the closing BATCH, for the same reason
        # 3. Owner.doBatch would crash because it expects the batch
        #    supybot-tag to be set, but it wasn't because of 1
        #self.batches.clear()

    def __reduce__(self):
        return (self.__class__, (self.history, self.supported,
                                 self.nicksToHostmasks,
                                 self.nicksToAccounts,
                                 self.channels))

    def __eq__(self, other):
        return self.history == other.history and \
               self.channels == other.channels and \
               self.supported == other.supported and \
               self.nicksToHostmasks == other.nicksToHostmasks and \
               self.nicksToAccounts == other.nicksToAccounts and \
               self.batches == other.batches

    def __ne__(self, other):
        return not self == other

    def copy(self):
        ret = self.__class__()
        ret.history = copy.deepcopy(self.history)
        ret.nicksToHostmasks = copy.deepcopy(self.nicksToHostmasks)
        ret.nicksToAccounts = copy.deepcopy(self.nicksToAccounts)
        ret.channels = copy.deepcopy(self.channels)
        ret.batches = copy.deepcopy(self.batches)
        return ret

    def addMsg(self, irc, msg):
        """Updates the state based on the irc object and the message."""
        self.history.append(msg)
        if ircutils.isUserHostmask(msg.prefix) and not msg.command == 'NICK':
            self.nicksToHostmasks[msg.nick] = msg.prefix
        if 'account' in msg.server_tags:
            self.nicksToAccounts[msg.nick] = msg.server_tags['account']
        if 'batch' in msg.server_tags:
            batch_name = msg.server_tags['batch']
            assert batch_name in self.batches, \
                'Server references undeclared batch %r' % batch_name
            for batch in self.getParentBatches(msg):
                batch.messages.append(msg)
        method = self.dispatchCommand(msg.command, msg.args)
        if method is not None:
            method(irc, msg)

    def getTopic(self, channel):
        """Returns the topic for a given channel."""
        return self.channels[channel].topic

    def nickToHostmask(self, nick):
        """Returns the hostmask for a given nick."""
        return self.nicksToHostmasks[nick]

    def nickToAccount(self, nick):
        """Returns the account for a given nick, or None if the nick is logged
        out. Raises :exc:`KeyError` if the nick was not seen or its account is
        not known yet."""
        return self.nicksToAccounts[nick]

    def getParentBatches(self, msg):
        """Given an IrcMsg, returns a list of all batches that contain it,
        innermost first.

        Raises ValueError if ``msg`` is not in a batch;
        or if it is in a batch that has already ended.
        This restriction may be relaxed in the future.

        This means that you should not call ``getParentBatches``
        on a message that was already processed.

        For example, assume Limnoria received the following::

            :irc.host BATCH +outer example.com/foo
            @batch=outer :irc.host BATCH +inner example.com/bar
            @batch=inner :nick!user@host PRIVMSG #channel :Hi
            @batch=outer :irc.host BATCH -inner
            :irc.host BATCH -outer

        If you call getParentBatches on any of the middle three messages,
        you get ``[Batch(name='inner', ...), Batch(name='outer', ...)]``.
        And if you call getParentBatches on either the first or the last
        message, you get ``[Batch(name='outer', ...)]``

        And you may only call `getParentBatches`` on the PRIVMSG
        if only the first three messages were processed.
        """
        batch = msg.tagged('batch')
        if not batch:
            # msg is not a BATCH command
            batch_name = msg.server_tags.get('batch')
            if batch_name:
                batch = self.batches.get(batch_name)
                if not batch:
                    raise ValueError(
                        'Called getParentBatches for a message in a batch that '
                        'already ended.'
                    )
            else:
                raise ValueError(
                    'Called getParentBatches for a message not in a batch.')

        batches = []
        while batch:
            batches.append(batch)
            batch = batch.parent_batch

        return batches

    def getClientTagDenied(self, tag):
        """Returns whether the given tag is denied by the server, according
        to its CLIENTTAGDENY policy.
        This is only informative, and servers may still allow or deny tags
        at their discretion.

        For details, see the RPL_ISUPPORT section in
        <https://ircv3.net/specs/extensions/message-tags>
        """
        tag = tag.lstrip("+")

        denied_tags = self.supported.get('CLIENTTAGDENY')
        if not denied_tags:
            return False
        denied_tags = denied_tags.split(',')
        if '*' in denied_tags:
            # All tags are denied by default, check the whitelist
            return ('-' + tag) not in denied_tags
        else:
            return tag in denied_tags

    def do004(self, irc, msg):
        """Handles parsing the 004 reply

        Supported user and channel modes are cached"""
        # msg.args = [nick, server, ircd-version, umodes, modes,
        #             modes that require arguments? (non-standard)]
        self.ircd = msg.args[2] if len(msg.args) > 2 else msg.args[1]

        # The conditionals are for Twitch, which doesn't send umodes or
        # chanmodes.
        if len(msg.args) > 3:
            self.supported['umodes'] = frozenset(msg.args[3])
        if len(msg.args) > 4:
            self.supported['chanmodes'] = frozenset(msg.args[4])

    _005converters = utils.InsensitivePreservingDict({
        'modes': lambda s: int(s) if s else None,  # it's optional
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

        if len(msg.args) != 9 or msg.args[1] != '1':
            return
        # irc.nick 1 user ip host nick status account gecos
        (n, t, user, ip, host, nick, status, account, gecos) = msg.args
        hostmask = '%s!%s@%s' % (nick, user, host)
        self.nicksToHostmasks[nick] = hostmask
        if account == '0':
            # logged out
            self.nicksToAccounts[nick] = None
        else:
            self.nicksToAccounts[nick] = account

    def do353(self, irc, msg):
        # NAMES reply.
        (__, type, channel, items) = msg.args
        if channel not in self.channels:
            self.channels[channel] = ChannelState()
        c = self.channels[channel]

        # Set of prefixes servers may append before a NAMES reply when
        # the user is op/halfop/voice/...
        # https://datatracker.ietf.org/doc/html/draft-hardy-irc-isupport-00#section-4.15
        prefix = self.supported.get('PREFIX')
        if prefix is None:
            prefix_chars = '@%+&~!'  # see the comments in addUser
        else:
            prefix_chars = ''.join(prefix.values())

        for item in items.split():
            stripped_item = item.lstrip(prefix_chars)
            item_prefix = item[0:-len(stripped_item)]
            if ircutils.isUserHostmask(stripped_item):
                # https://ircv3.net/specs/extensions/userhost-in-names
                nick = ircutils.nickFromHostmask(stripped_item)
                self.nicksToHostmasks[nick] = stripped_item
                name = item_prefix + nick
            else:
                name = item
            c.addUser(name, prefix_chars=prefix_chars)

        if type == '@':
            c.modes['s'] = None

    def doChghost(self, irc, msg):
        # https://ircv3.net/specs/extensions/chghost
        (user, host) = msg.args
        nick = msg.nick
        hostmask = '%s!%s@%s' % (nick, user, host)
        self.nicksToHostmasks[nick] = hostmask

    def doAccount(self, irc, msg):
        # https://ircv3.net/specs/extensions/account-notify
        account = msg.args[0]
        if account == '*':
            self.nicksToAccounts[msg.nick] = None
        else:
            self.nicksToAccounts[msg.nick] = account

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
        if 'extended-join' in self.capabilities_ack:
            account = msg.args[1]
            if account == '*':
                self.nicksToAccounts[msg.nick] = None
            else:
                self.nicksToAccounts[msg.nick] = account

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
        if irc.isChannel(channel): # There can be user modes, as well.
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
        if msg.nick in self.nicksToAccounts:
            del self.nicksToAccounts[msg.nick]

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

        try:
            self.nicksToAccounts[newNick] = self.nicksToAccounts[oldNick]
            del self.nicksToAccounts[oldNick]
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

            # Both are possibly None:
            parent_batch_name = msg.server_tags.get("batch")
            parent_batch = self.batches.get(parent_batch_name)

            batch = Batch(
                name=batch_name,
                type=batch_type,
                arguments=batch_arguments,
                messages=[msg],
                parent_batch=parent_batch
            )
            msg.tag('batch', batch)
            self.batches[batch_name] = batch
        elif msg.args[0].startswith('-'):
            batch = self.batches.pop(batch_name)
            batch.messages.append(msg)
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

    .. attribute:: zombie

        Whether or not this object represents a living IRC connection.

        :type: bool

    .. attribute:: network

        The name of the network this object is connected to.

        :type: str

    .. attribute:: startedAt

        When this connection was (re)started.

        :type: float

    .. attribute:: callbacks

        List of all callbacks (ie. plugins) currently loaded

        :type: List[IrcCallback]

    .. attribute:: queue

        Queue of messages waiting to be sent. Plugins should use the
        ``queueMsg`` method instead of accessing this directly.

        :type: IrcMsgQueue

    .. attribute:: fastqueue

        Same as ``queue``, but for messages with high priority. Plugins should
        use the ``sendMsg`` method instead of accessing this directly (or
        `queueMsg` if the message isn't high priority).

        :type: smallqueue

    .. attribute:: driver

        Driver of the IRC connection (normally, a
        :py:class:`supybot.drivers.Socket.SocketDriver` object).
        Plugins normally do not need to access this.

    .. attribute:: startedSync

        When joining a channel, a ``'#channel': time.time()`` entry is added
        to this dict, which is then removed when the join is completed.
        Plugins should not change this value, it is automatically handled when
        they send a JOIN.

        :type: ircutils.IrcDict[str, float]

    .. attribute:: monitoring

        A dict with nicks as keys and the number of plugins monitoring this
        nick as value.
        Plugins should not access this directly, and should use the ``monitor``
        and ``unmonitor`` methods instead.

        :type: ircutils.IrcDict[str, int]

    .. attribute:: state

        An :py:class:`supybot.irclib.IrcState` object, which stores all the
        known information about the connection with the IRC network.

        :type: supybot.irclib.IrcState
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

        # Messages of batches that are currently in one self.queue (not
        # self.fastqueue).
        # This works by adding only the first message of a batch in a queue,
        # and when self.takeMsg pops that message from the queue, it will
        # also pop the whole batch from self._queued_batches and atomically
        # add it to self.fastqueue
        self._queued_batches = {}

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
        """Returns whether the given argument is a valid nick on this
        network.
        """
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
        if msg.command.upper() == 'BATCH':
            log.error('Tried to send a BATCH message using queueMsg '
                      'instead of queueBatch: %r', msg)
        if not self.zombie:
            return self.queue.enqueue(msg)
        else:
            log.warning('Refusing to queue %r; %s is a zombie.', msg, self)
            return False

    def sendMsg(self, msg):
        """Queues a message to be sent to the server *immediately*"""
        if msg.command.upper() == 'BATCH':
            log.error('Tried to send a BATCH message using sendMsg '
                      'instead of queueBatch: %r', msg)
        if not self.zombie:
            self.fastqueue.enqueue(msg)
        else:
            log.warning('Refusing to send %r; %s is a zombie.', msg, self)

    def queueBatch(self, msgs):
        """Queues a batch of messages to be sent to the server.
        See <https://ircv3.net/specs/extensions/batch-3.2>

        queueMsg/sendMsg must not be used repeatedly to send a batch, because
        they do not guarantee the batch is send atomically, which is
        required because "Clients MUST NOT send messages other than PRIVMSG
        while a multiline batch is open."
        -- <https://ircv3.net/specs/extensions/multiline>
        """
        if not conf.supybot.protocols.irc.experimentalExtensions():
            raise ValueError(
                'queueBatch is disabled because it depends on draft '
                'IRC specifications. If you know what you are doing, '
                'set supybot.protocols.irc.experimentalExtensions.')

        if len(msgs) < 2:
            raise ValueError(
                'queueBatch called with less than two messages.')
        if msgs[0].command.upper() != 'BATCH' or msgs[0].args[0][0] != '+':
            raise ValueError(
                'queueBatch called with non-"BATCH +" as first message.')
        if msgs[-1].command.upper() != 'BATCH' or msgs[-1].args[0][0] != '-':
            raise ValueError(
                'queueBatch called with non-"BATCH -" as last message.')

        batch_name = msgs[0].args[0][1:]

        if msgs[-1].args[0][1:] != batch_name:
            raise ValueError(
                'queueBatch called with mismatched BATCH name args.')
        if any(msg.server_tags['batch'] != batch_name for msg in msgs[1:-1]):
            raise ValueError(
                'queueBatch called with mismatched batch names.')
            return
        if batch_name in self._queued_batches:
            raise ValueError(
                'queueBatch called with a batch name already in flight')

        self._queued_batches[batch_name] = msgs

        # Enqueue only the start of the batch. When takeMsg sees it, it will
        # enqueue the full batch in self.fastqueue.
        # We don't enqueue the full batch in self.fastqueue here, because
        # there is no reason for this batch to jump in front of all other
        # queued messages.
        # TODO: the batch will be ordered with the priority of a BATCH
        # message (ie. normal), but if the batch is made only of low-priority
        # messages like PRIVMSG, it should have that priority.
        # (or maybe order on the batch type instead of commands inside
        # the batch?)
        self.queue.enqueue(msgs[0])

    def _truncateMsg(self, msg):
        msg_str = str(msg)
        if msg_str[0] == '@':
            (msg_tags_str, msg_rest_str) = msg_str.split(' ', 1)
            msg_tags_str += ' '
        else:
            msg_tags_str = ''
            msg_rest_str = msg_str
        msg_rest_bytes = msg_rest_str.encode()
        if len(msg_rest_bytes) > MAX_LINE_SIZE:
            # Yes, this violates the contract, but at this point it doesn't
            # matter.  That's why we gotta go munging in private attributes
            #
            # I'm changing this to a log.debug to fix a possible loop in
            # the LogToIrc plugin.  Since users can't do anything about
            # this issue, there's no fundamental reason to make it a
            # warning.
            log.debug('Truncating %r, message is too long.', msg)

            # Truncate to 512 bytes (minus 2 for '\r\n')
            msg_rest_bytes = msg_rest_bytes[:MAX_LINE_SIZE-2]

            # The above truncation may have truncated in the middle of a
            # multi-byte character.
            # I was about to write a UTF-8 decoder here just to trim them
            # properly, but fortunately there is a neat trick to trim it
            # while decoding: just ignore invalid bytes!
            # https://stackoverflow.com/a/1820949/539465
            msg_rest_str = msg_rest_bytes.decode(errors="ignore")

            msg._str = msg_tags_str + msg_rest_str + '\r\n'
            msg._len = len(str(msg))
        # TODO: truncate tags

    def takeMsg(self):
        """Called by the IrcDriver; takes a message to be sent."""
        if not self.callbacks:
            log.critical('No callbacks in %s.', self)
        now = time.time()
        msg = None
        if self.fastqueue:
            msg = self.fastqueue.dequeue()
        elif self.queue:
            if now-self.lastTake < conf.supybot.protocols.irc.throttleTime():
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
            # Copy the msg before altering it back. Without a copy, it
            # can cause all sorts of issues if the msg is reused (eg. Relay
            # sends the same message object to the same network, so when
            # sending the msg for the second time, it would already be
            # tagged with emulatedEcho and fail the assertion; or it can be
            # added a label because we have labeled-response on a network)
            msg = ircmsgs.IrcMsg(msg=msg)

            if msg.command.upper() == 'BATCH':
                if not conf.supybot.protocols.irc.experimentalExtensions():
                    log.error('Dropping outgoing batch. '
                              'supybot.protocols.irc.experimentalExtensions '
                              'is disabled, so plugins should not send '
                              'batches. This is a bug, please report it.')
                    return None
                if msg.args[0].startswith('+'):
                    # Start of a batch; created by self.queueBatch. We need to
                    # *prepend* the rest of the batch to the fastqueue
                    # so that no other message is sent while the batch is
                    # open.
                    # "Clients MUST NOT send messages other than PRIVMSG while
                    # a multiline batch is open."
                    # -- <https://ircv3.net/specs/extensions/multiline>
                    #
                    # (Yes, *prepend* to the queue. Fortunately, it should be
                    # empty, because BATCH cannot be queued in the fastqueue
                    # and we just got a BATCH, which means it's from the
                    # regular queue, which means the fastqueue is empty.
                    # But let's not take any risk, eg. if race condition
                    # with a plugin appending directly to the fastqueue.)
                    batch_name = msg.args[0][1:]
                    batch_messages = self._queued_batches.pop(batch_name)
                    if batch_messages[0] != msg:
                        log.error('Enqueue "BATCH +" message does not match '
                                  'the one of the batch in flight.')
                    self.fastqueue[:0] = batch_messages[1:]

            if not world.testing and 'label' not in msg.server_tags \
                    and 'labeled-response' in self.state.capabilities_ack:
                # Not adding labels while testing, because it would break
                # all plugin tests using IrcMsg equality (unless they
                # explicitly add the label, but it becomes a burden).
                msg.server_tags['label'] = ircutils.makeLabel()
                msg._len = msg._str = None
            for callback in reversed(self.callbacks):
                self._setMsgChannel(msg)
                try:
                    msg = callback.outFilter(self, msg)
                except:
                    log.exception('Uncaught exception in outFilter:')
                    continue
                if msg is None:
                    log.debug('%s.outFilter returned None.', callback.name())
                    return self.takeMsg()
                world.debugFlush()

            self._truncateMsg(msg)

            if msg.command.upper() in ('PRIVMSG', 'NOTICE', 'TAGMSG') \
                    and 'echo-message' not in self.state.capabilities_ack:
                # echo-message is not implemented by server; let's emulate it
                # here, just before sending it to the driver.
                assert not msg.tagged('receivedAt')
                if not world.testing:
                    assert not msg.tagged('emulatedEcho')

                msg.tag('emulatedEcho', True)
                self.feedMsg(msg, tag=False)
            else:
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

    def _tagMsg(self, msg):
        """Sets attribute on an incoming IRC message. Will usually only be
        called by feedMsg, but may be useful in tests as well."""
        msg.tag('receivedBy', self)
        msg.tag('receivedOn', self.network)
        msg.tag('receivedAt', time.time())

        self._setMsgChannel(msg)

    def _setMsgChannel(self, msg):
        channel = None
        if msg.args:
            channel = msg.args[0]
            if msg.command in ('NOTICE', 'PRIVMSG') and \
                    not conf.supybot.protocols.irc.strictRfc():
                channel = self.stripChannelPrefix(channel)
        if not self.isChannel(channel):
            channel = None
        msg.channel = channel

    def stripChannelPrefix(self, channel):
        statusmsg_chars = self.state.supported.get('statusmsg', '')
        return channel.lstrip(statusmsg_chars)

    _numericErrorCommandRe = re.compile(r'^[45][0-9][0-9]$')
    def feedMsg(self, msg, tag=True):
        """Called by the IrcDriver; feeds a message received.

        `tag=False` is used when simulating echo messages, to skip adding
        received* tags."""
        if tag:
            self._tagMsg(msg)
        channel = msg.channel  # used by dynamicScope (ew)

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
        method = self.dispatchCommand(msg.command, msg.args)
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
            try:
                callback.reset()
            except Exception:
                log.exception('Uncaught exception in %r.reset()', callback)
        self._queueConnectMessages()

    def _setNonResettingVariables(self):
        # Configuration stuff.
        network_config = conf.supybot.networks.get(self.network)
        def get_value(name):
            return getattr(network_config, name)() or \
                getattr(conf.supybot, name)()
        self.nick = get_value('nick')
        # Expand variables like $version in realname.
        self.user = ircutils.standardSubstitute(self, None, get_value('user'))
        self.ident = get_value('ident')
        self.alternateNicks = conf.supybot.nick.alternates()[:]
        self.triedNicks = ircutils.IrcSet()
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
        if self.requireStarttls:
            log.error(('STARTTLS is no longer supported. Set '
                'supybot.networks.%s.requireStarttls to False '
                'to disable it, and use supybot.networks.%s.ssl '
                'instead.') % (self.network, self.network))
            self.driver.die()
            self._reallyDie()
            return
        self.resetSasl()

    def resetSasl(self):
        network_config = conf.supybot.networks.get(self.network)
        self.sasl_authenticated = False
        self.sasl_username = network_config.sasl.username()
        self.sasl_password = network_config.sasl.password()
        self.sasl_ecdsa_key = network_config.sasl.ecdsa_key()
        self.sasl_scram_state = {'step': 'uninitialized'}
        self.authenticate_decoder = None
        self.sasl_next_mechanisms = []
        self.sasl_current_mechanism = None
        for mechanism in network_config.sasl.mechanisms():
            if mechanism == 'ecdsa-nist256p-challenge':
                if not crypto:
                    log.debug('Skipping SASL %s, crypto module '
                              'is not available',
                              mechanism)
                elif not self.sasl_username or not self.sasl_ecdsa_key:
                    log.debug('Skipping SASL %s, missing username and/or key',
                              mechanism)
                else:
                    self.sasl_next_mechanisms.append(mechanism)
            elif mechanism == 'external':
                if not network_config.certfile() and \
                        not conf.supybot.protocols.irc.certfile():
                    log.debug('Skipping SASL %s, missing cert file',
                              mechanism)
                else:
                    self.sasl_next_mechanisms.append(mechanism)
            elif mechanism.startswith('scram-'):
                if not scram:
                    log.debug('Skipping SASL %s, scram module '
                              'is not available',
                              mechanism)
                elif not self.sasl_username or not self.sasl_password:
                    log.debug('Skipping SASL %s, missing username and/or '
                              'password',
                              mechanism)
                else:
                    self.sasl_next_mechanisms.append(mechanism)
            elif mechanism == 'plain':
                if not self.sasl_username or not self.sasl_password:
                    log.debug('Skipping SASL %s, missing username and/or '
                              'password',
                              mechanism)
                else:
                    self.sasl_next_mechanisms.append(mechanism)

    # Note: echo-message is only requested if labeled-response is available.
    REQUEST_CAPABILITIES = set(['account-notify', 'extended-join',
        'multi-prefix', 'metadata-notify', 'account-tag',
        'userhost-in-names', 'invite-notify', 'server-time',
        'chghost', 'batch', 'away-notify', 'message-tags',
        'msgid', 'setname', 'labeled-response', 'echo-message',
        'sasl', 'standard-replies'])
    """IRCv3 capabilities requested when they are available.

    echo-message is special-cased to be requested only with labeled-response.

    To check if a capability was negotiated, use `irc.state.capabilities_ack`.
    """

    REQUEST_EXPERIMENTAL_CAPABILITIES = set(['draft/account-registration',
        'draft/multiline'])
    """Like REQUEST_CAPABILITIES, but these capabilities are only requested
    if supybot.protocols.irc.experimentalExtensions is enabled."""

    def _queueConnectMessages(self):
        if self.zombie:
            self.driver.die()
            self._reallyDie()

            return

        self.sendMsg(ircmsgs.IrcMsg(command='CAP', args=('LS', '302')))

        self.sendAuthenticationMessages()

        self.state.fsm.on_init_messages_sent(self)

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

    def capUpkeep(self, msg):
        """
        Called after getting a CAP ACK/NAK to check it's consistent with what
        was requested, and to end the cap negotiation when we received all the
        ACK/NAKs we were waiting for.

        `msg` is the message that triggered this call."""
        self.state.fsm.expect_state([
            # Normal CAP ACK / CAP NAK during cap negotiation:
            IrcStateFsm.States.INIT_CAP_NEGOTIATION,
            # Sigyn sends CAP REQ when it sees RPL_SASLSUCCESS, so we get the
            # CAP ACK while waiting for MOTD on some IRCds (eg. InspIRCd):
            IrcStateFsm.States.INIT_WAITING_MOTD,
            IrcStateFsm.States.INIT_MOTD,
            # CAP ACK / CAP NAK after a CAP NEW (probably):
            IrcStateFsm.States.CONNECTED,
        ])

        capabilities_responded = (self.state.capabilities_ack |
            self.state.capabilities_nak)
        if not capabilities_responded <= self.state.capabilities_req:
            log.error('Server responded with unrequested ACK/NAK '
                      'capabilities: req=%r, ack=%r, nak=%r',
                      self.state.capabilities_req,
                      self.state.capabilities_ack,
                      self.state.capabilities_nak)
            self.driver.reconnect(wait=True)
        elif capabilities_responded == self.state.capabilities_req:
            log.debug('Got all capabilities ACKed/NAKed')
            # We got all the capabilities we asked for
            if 'sasl' in self.state.capabilities_ack:
                if self.state.fsm.state in [
                        IrcStateFsm.States.INIT_CAP_NEGOTIATION,
                        IrcStateFsm.States.CONNECTED]:
                    self._maybeStartSasl(msg)
                else:
                    pass # Already in the middle of a SASL auth
            elif self.state.fsm.state != IrcStateFsm.States.CONNECTED:
                # If we are still in the initial cap negotiation (ie. if this
                # is not in response to a 'CAP NEW'), send a CAP END so the
                # server sends us the MOTD
                self.endCapabilityNegociation(msg)
        else:
            log.debug('Waiting for ACK/NAK of capabilities: %r',
                      self.state.capabilities_req - capabilities_responded)
            pass # Do nothing, we'll get more

    def endCapabilityNegociation(self, msg):
        self.state.fsm.on_cap_end(self, msg)
        self.sendMsg(ircmsgs.IrcMsg(command='CAP', args=('END',)))

    def sendSaslString(self, string):
        for chunk in ircutils.authenticate_generator(string):
            self.sendMsg(ircmsgs.IrcMsg(command='AUTHENTICATE',
                args=(chunk,)))

    def tryNextSaslMechanism(self, msg):
        self.state.fsm.expect_state([
            IrcStateFsm.States.INIT_SASL,
            IrcStateFsm.States.CONNECTED_SASL,
        ])
        log.debug('Next SASL mechanisms: %s', self.sasl_next_mechanisms)
        if self.sasl_next_mechanisms:
            self.sasl_current_mechanism = self.sasl_next_mechanisms.pop(0)
            self.sendMsg(ircmsgs.IrcMsg(command='AUTHENTICATE',
                args=(self.sasl_current_mechanism.upper(),)))
        elif conf.supybot.networks.get(self.network).sasl.required():
            log.error('None of the configured SASL mechanisms succeeded, '
                    'aborting connection.')
        else:
            self.sasl_current_mechanism = None
            self.state.fsm.on_sasl_auth_finished(self, msg)
            if self.state.fsm.state == IrcStateFsm.States.INIT_CAP_NEGOTIATION:
                self.endCapabilityNegociation(msg)

    def _maybeStartSasl(self, msg):
        if not self.sasl_authenticated and \
                'sasl' in self.state.capabilities_ack:
            self.startSasl(msg)

    def startSasl(self, msg):
        self.state.fsm.on_sasl_start(self, msg)
        assert 'sasl' in self.state.capabilities_ls, (
            'Starting SASL without receiving "CAP LS sasl" or '
            '"CAP NEW sasl" first.')
        self.resetSasl()
        s = self.state.capabilities_ls['sasl']
        if s is not None:
            available = set(map(str.lower, s.split(',')))
            self.sasl_next_mechanisms = [
                    x for x in self.sasl_next_mechanisms
                    if x.lower() in available]
        self.tryNextSaslMechanism(msg)

    def doAuthenticate(self, msg):
        self.state.fsm.expect_state([
            IrcStateFsm.States.INIT_SASL,
            IrcStateFsm.States.CONNECTED_SASL,
        ])
        if not self.authenticate_decoder:
            self.authenticate_decoder = ircutils.AuthenticateDecoder()
        self.authenticate_decoder.feed(msg)
        if not self.authenticate_decoder.ready:
            return # Waiting for other messages
        string = self.authenticate_decoder.get()
        self.authenticate_decoder = None

        mechanism = self.sasl_current_mechanism
        if mechanism == 'ecdsa-nist256p-challenge':
            self._doAuthenticateEcdsa(msg, string)
        elif mechanism == 'external':
            self.sendSaslString(b'')
        elif mechanism.startswith('scram-'):
            step = self.sasl_scram_state['step']
            try:
                if step == 'uninitialized':
                    log.debug('%s: starting SCRAM.',
                            self.network)
                    self._doAuthenticateScramFirst(msg, mechanism)
                elif step == 'first-sent':
                    log.debug('%s: received SCRAM challenge.',
                            self.network)
                    self._doAuthenticateScramChallenge(string)
                elif step == 'final-sent':
                    log.debug('%s: finishing SCRAM.',
                            self.network)
                    self._doAuthenticateScramFinish(msg, string)
                else:
                    assert False
            except scram.ScramException:
                self.sendMsg(ircmsgs.IrcMsg(command='AUTHENTICATE',
                    args=('*',)))
                self.tryNextSaslMechanism(msg)
        elif mechanism == 'plain':
            authstring = b'\0'.join([
                self.sasl_username.encode('utf-8'),
                self.sasl_username.encode('utf-8'),
                self.sasl_password.encode('utf-8'),
            ])
            self.sendSaslString(authstring)

    def _doAuthenticateEcdsa(self, msg, string):
        if string == b'':
            self.sendSaslString(self.sasl_username.encode('utf-8'))
            return

        try:
            with open(self.sasl_ecdsa_key, 'rb') as fd:
                private_key = crypto.load_pem_private_key(
                    fd.read(),password=None, backend=crypto.default_backend())
            authstring = private_key.sign(
                string, crypto.ECDSA(crypto.Prehashed(crypto.SHA256())))
            self.sendSaslString(authstring)
        except (OSError, ValueError):
            self.sendMsg(ircmsgs.IrcMsg(command='AUTHENTICATE',
                args=('*',)))
            self.tryNextSaslMechanism(msg)

    def _doAuthenticateScramFirst(self, msg, mechanism):
        """Handle sending the client-first message of SCRAM auth."""
        hash_name = mechanism[len('scram-'):]
        if hash_name.endswith('-plus'):
            hash_name = hash_name[:-len('-plus')]
        hash_name = hash_name.upper()
        if hash_name not in scram.HASH_FACTORIES:
            log.debug('%s: SCRAM hash %r not supported, aborting.',
                    self.network, hash_name)
            self.tryNextSaslMechanism(msg)
            return
        authenticator = scram.SCRAMClientAuthenticator(hash_name,
                channel_binding=False)
        self.sasl_scram_state['authenticator'] = authenticator
        client_first = authenticator.start({
            'username': self.sasl_username,
            'password': self.sasl_password,
            })
        self.sendSaslString(client_first)
        self.sasl_scram_state['step'] = 'first-sent'

    def _doAuthenticateScramChallenge(self, challenge):
        client_final = self.sasl_scram_state['authenticator'] \
                .challenge(challenge)
        self.sendSaslString(client_final)
        self.sasl_scram_state['step'] = 'final-sent'

    def _doAuthenticateScramFinish(self, msg, data):
        try:
            res = self.sasl_scram_state['authenticator'] \
                    .finish(data)
        except scram.BadSuccessException as e:
            log.warning('%s: SASL authentication failed with SCRAM error: %e',
                    self.network, e)
            self.sendMsg(ircmsgs.IrcMsg(command='AUTHENTICATE',
                args=('*',)))
            self.tryNextSaslMechanism(msg)
        else:
            self.sendSaslString(b'')
            self.sasl_scram_state['step'] = 'authenticated'

    def do903(self, msg):
        log.info('%s: SASL authentication successful', self.network)
        self.sasl_authenticated = True
        self.state.fsm.on_sasl_auth_finished(self, msg)
        if self.state.fsm.state == IrcStateFsm.States.INIT_CAP_NEGOTIATION:
            self.endCapabilityNegociation(msg)

    def do904(self, msg):
        log.warning('%s: SASL authentication failed (mechanism: %s): %s',
                self.network, self.sasl_current_mechanism, msg.args[-1])
        self.tryNextSaslMechanism(msg)

    def do905(self, msg):
        log.warning('%s: SASL authentication failed because the username or '
                    'password is too long.', self.network)
        self.tryNextSaslMechanism(msg)

    def do906(self, msg):
        log.warning('%s: SASL authentication aborted', self.network)
        if self.state.fsm.state == IrcStateFsm.States.INIT_WAITING_MOTD:
            # This 906 was triggered by sending 'CAP END' after we exhausted
            # all authentication mechanism; so it does not make sense to try
            # self.tryNextSaslMechanism() again. And it would crash anyway,
            # because it does not expect the connection to be in this state.
            pass
        else:
            self.tryNextSaslMechanism(msg)

    def do907(self, msg):
        log.warning('%s: Attempted SASL authentication when we were already '
                    'authenticated.', self.network)
        self.tryNextSaslMechanism(msg)

    def do908(self, msg):
        log.info('%s: Supported SASL mechanisms: %s',
                 self.network, msg.args[1])

    def doCapAck(self, msg):
        if len(msg.args) != 3:
            log.warning('Bad CAP ACK from server: %r', msg)
            return
        caps = msg.args[2].split()
        assert caps, 'Empty list of capabilities'
        log.debug('%s: Server acknowledged capabilities: %s',
                 self.network, caps)
        self.state.capabilities_ack.update(caps)

        self.capUpkeep(msg)

    def doCapNak(self, msg):
        if len(msg.args) != 3:
            log.warning('Bad CAP NAK from server: %r', msg)
            return
        caps = msg.args[2].split()
        assert caps, 'Empty list of capabilities'
        self.state.capabilities_nak.update(caps)
        log.warning('%s: Server refused capabilities: %s',
                    self.network, caps)
        self.capUpkeep(msg)

    def _onCapSts(self, policy, msg):
        tls_connection = self.driver.currentServer.force_tls_verification \
            or self.driver.ssl
        secure_connection = self.driver.currentServer.force_tls_verification \
            or (self.driver.ssl and self.driver.anyCertValidationEnabled())

        parsed_policy = ircutils.parseStsPolicy(
            log, policy, tls_connection=tls_connection)
        if parsed_policy is None:
            # There was an error (and it was logged). Ignore it and proceed
            # with the connection.
            # Currently this shouldn't happen, but let's future-proof it, eg.
            # in case https://github.com/ircv3/ircv3-specifications/pull/390
            # gets adopted.
            return

        if secure_connection:
            # TLS is enabled and certificate is verified; write the STS policy
            # in stone.
            # For future-proofing (because we don't want to write an invalid
            # value), we write the raw policy received from the server instead
            # of the parsed one.
            log.debug('Storing STS policy for %s (TLS port %s): %s',
                self.driver.currentServer.hostname,
                self.driver.currentServer.port,
                policy)
            ircdb.networks.getNetwork(self.network).addStsPolicy(
                self.driver.currentServer.hostname,
                self.driver.currentServer.port,
                policy)
        elif self.driver.ssl:
            # SSL enabled, but certificates are not checked -> reconnect on the
            # same port and check certificates, before storing the STS policy.
            hostname = self.driver.currentServer.hostname
            port = self.driver.currentServer.port
            attempt = self.driver.currentServer.attempt

            log.info('Got STS policy over insecure TLS connection; '
                     'reconnecting to check certificates. %r',
                     self.driver.currentServer)
            # Reconnect to the server, but with TLS *and* certificate
            # validation this time.
            self.state.fsm.on_shutdown(self, msg)

            self.driver.reconnect(
                server=Server(hostname, port, attempt, True),
                wait=True)
        else:
            hostname = self.driver.currentServer.hostname
            attempt = self.driver.currentServer.attempt

            log.info('Got STS policy over insecure (cleartext) connection; '
                     'reconnecting to secure port. %r',
                     self.driver.currentServer)
            # Reconnect to the server, but with TLS *and* certificate
            # validation this time.
            self.state.fsm.on_shutdown(self, msg)

            self.driver.reconnect(
                server=Server(hostname, parsed_policy['port'], attempt, True),
                wait=True)

    def _addCapabilities(self, capstring, msg):
        for item in capstring.split():
            while item.startswith(('=', '~')):
                item = item[1:]
            if '=' in item:
                (cap, value) = item.split('=', 1)
                if cap == 'sts':
                    self._onCapSts(value, msg)
                self.state.capabilities_ls[cap] = value
            else:
                if item == 'sts':
                    log.error('Got "sts" capability without value. Aborting '
                              'connection.')
                    self.driver.reconnect(wait=True)
                self.state.capabilities_ls[item] = None


    def doCapLs(self, msg):
        if len(msg.args) == 4:
            # Multi-line LS
            if msg.args[2] != '*':
                log.warning('Bad CAP LS from server: %r', msg)
                return
            self._addCapabilities(msg.args[3], msg)
        elif len(msg.args) == 3: # End of LS
            self._addCapabilities(msg.args[2], msg)
            if self.state.fsm.state == IrcStateFsm.States.SHUTTING_DOWN:
                return
            self.state.fsm.expect_state([
                # Normal case:
                IrcStateFsm.States.INIT_CAP_NEGOTIATION,
                # Should only happen if a plugin sends a CAP LS (which they
                # shouldn't do):
                IrcStateFsm.States.CONNECTED,
                IrcStateFsm.States.CONNECTED_SASL,
            ])
            # Normally at this point, self.state.capabilities_ack should be
            # empty; but let's just make sure we're not requesting the same
            # caps twice for no reason.
            want_capabilities = self.REQUEST_CAPABILITIES
            if conf.supybot.protocols.irc.experimentalExtensions():
                want_capabilities |= self.REQUEST_EXPERIMENTAL_CAPABILITIES
            new_caps = (
                set(self.state.capabilities_ls) &
                want_capabilities -
                self.state.capabilities_ack)
            # NOTE: Capabilities are requested in alphabetic order, because
            # sets are unordered, and their "order" is nondeterministic.
            # This is needed for the tests.
            if new_caps:
                self.requestCapabilities(new_caps)
            else:
                self.endCapabilityNegociation(msg)
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
        # Note that in theory, this method may be called at any time, even
        # before CAP END (or even before the initial CAP LS).
        if len(msg.args) != 3:
            log.warning('Bad CAP NEW from server: %r', msg)
            return
        caps = msg.args[2].split()
        assert caps, 'Empty list of capabilities'
        self._addCapabilities(msg.args[2], msg)
        if self.state.fsm.state == IrcStateFsm.States.SHUTTING_DOWN:
            return
        common_supported_unrequested_capabilities = (
                set(self.state.capabilities_ls) &
                self.REQUEST_CAPABILITIES -
                self.state.capabilities_ack)
        if common_supported_unrequested_capabilities:
            self.requestCapabilities(common_supported_unrequested_capabilities)

    def requestCapabilities(self, caps):
        """Takes an iterable of IRCv3 capabilities, and requests them to the
        server using CAP REQ.

        This is mostly just used during connection registration or when the
        server sends CAP NEW; but plugins may use it as well to request custom
        capabilities. They should make sure these capabilities cannot
        negatively impact other plugins, though."""
        caps = list(sorted(caps))
        cap_lines = []
        if 'echo-message' in caps \
                and 'labeled-response' not in self.state.capabilities_ack:
            # Make sure echo-message is never requested unless we either have
            # labeled-response already, or we request it *on the same line*
            # so they are both accepted or both rejected). The reason for this
            # is that this is required to properly deal with PRIVMSGs sent to
            # oneself.
            # See "When a client sends a private message to its own nick" at
            # <https://ircv3.net/specs/extensions/labeled-response>
            caps.remove('echo-message')
            if 'labeled-response' in caps:
                caps.remove('labeled-response')
                # This makes sure they are always on the same line (which
                # happens to be the first):
                caps = ['echo-message', 'labeled-response'] + caps

        self.state.capabilities_req |= set(caps)

        caps = ' '.join(caps)
        # textwrap works here because in ASCII, all chars are 1 bytes:
        cap_lines = textwrap.wrap(
            caps, MAX_LINE_SIZE-len('CAP REQ :'),
            break_long_words=False, break_on_hyphens=False)
        for cap_line in cap_lines:
            self.sendMsg(ircmsgs.IrcMsg(command='CAP',
                args=('REQ', cap_line)))

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
            if nick not in self.triedNicks:
                self.triedNicks.add(nick)
                return nick

        nick = conf.supybot.nick()
        network_nick = conf.supybot.networks.get(self.network).nick()
        if network_nick != '':
            nick = network_nick
        ret = nick
        L = list(nick)
        while len(L) <= 3:
            L.append('`')
        while ret in self.triedNicks:
            L[random.randrange(len(L))] = utils.iter.choice('0123456789')
            ret = ''.join(L)
        self.triedNicks.add(ret)
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

    def do375(self, msg):
        self.state.fsm.on_start_motd(self, msg)
        log.info('Got start of MOTD from %s', self.server)

    def do376(self, msg):
        self.state.fsm.on_end_motd(self, msg)
        log.info('Got end of MOTD from %s', self.server)
        self.afterConnect = True
        # Let's reset nicks in case we had to use a weird one.
        self.alternateNicks = conf.supybot.nick.alternates()[:]

        self._setUmodes()

    do377 = do422 = do376

    def _setUmodes(self):
        # Get the configured umodes
        umodes = conf.supybot.networks.get(self.network).umodes()
        if umodes == '':
            umodes = conf.supybot.protocols.irc.umodes()

        # Add the bot mode if the server advertizes one;
        # and if the configured umode doesn't already have it
        # explicitly set or unset
        bot_mode = self.state.supported.get("BOT")
        if bot_mode and len(bot_mode) == 1:
            if bot_mode not in umodes:
                umodes += "+" + bot_mode

        # Filter out umodes not supported by the server
        supported = self.state.supported.get('umodes')
        if supported:
            acceptedchars = supported.union('+-')
            umodes = ''.join([m for m in umodes if m in acceptedchars])

        # Send the umodes
        if umodes:
            log.info('Sending user modes to %s: %s', self.network, umodes)
            self.sendMsg(ircmsgs.mode(self.nick, umodes))

    def do43x(self, msg, problem):
        if not self.afterConnect:
            self.triedNicks.add(self.nick)
            newNick = self._getNextNick()
            assert newNick != self.nick, \
                (self.nick, self.alternateNicks, self.triedNicks)
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
            self.queueMsg(ircmsgs.who(channel, args=('%tuhnairf,1',))) # Ends with 315.
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
