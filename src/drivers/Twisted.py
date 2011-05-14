###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009, James Vega
# Copyright (c) 2011, Valentin Lorentz
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

import supybot.log as log
import supybot.conf as conf
import supybot.drivers as drivers
import supybot.ircmsgs as ircmsgs
from supybot.minecraftformat import DataBuffer, IncompleteDataError
import supybot.minecraftprotocol as minecraftprotocol
import supybot.minecraftmsgs as minecraftmsgs

from bravo.location import Location
from bravo.packets.beta import parse_packets, make_packet, make_error_packet

from twisted.names import client
from twisted.internet import reactor, error
from twisted.protocols.basic import LineReceiver
from twisted.internet.task import cooperate, deferLater, LoopingCall
from twisted.internet.protocol import ReconnectingClientFactory, Protocol


# This hack prevents the standard Twisted resolver from starting any
# threads, which allows for a clean shut-down in Twisted>=2.0
reactor.installResolver(client.createResolver())


try:
    from OpenSSL import SSL
    from twisted.internet import ssl
except ImportError:
    drivers.log.debug('PyOpenSSL is not available, '
                      'cannot connect to SSL servers.')
    SSL = None

class TwistedRunnerDriver(drivers.IrcDriver):
    def name(self):
        return self.__class__.__name__

    def run(self):
        try:
            reactor.iterate(conf.supybot.drivers.poll())
        except:
            drivers.log.exception('Uncaught exception outside reactor:')

class SupyIrcProtocol(LineReceiver):
    delimiter = '\n'
    MAX_LENGTH = 1024
    def __init__(self):
        self.mostRecentCall = reactor.callLater(0.1, self.checkIrcForMsgs)

    def lineReceived(self, line):
        msg = drivers.parseMsg(line)
        if msg is not None:
            self.irc.feedMsg(msg)

    def checkIrcForMsgs(self):
        if self.connected:
            msg = self.irc.takeMsg()
            while msg:
                self.transport.write(str(msg))
                msg = self.irc.takeMsg()
        self.mostRecentCall = reactor.callLater(0.1, self.checkIrcForMsgs)

    def connectionLost(self, r):
        self.mostRecentCall.cancel()
        if r.check(error.ConnectionDone):
            drivers.log.disconnect(self.factory.currentServer)
        else:
            drivers.log.disconnect(self.factory.currentServer, errorMsg(r))
        if self.irc.zombie:
            self.factory.stopTrying()
            while self.irc.takeMsg():
                continue
        else:
            self.irc.reset()

    def connectionMade(self):
        self.factory.resetDelay()
        self.irc.driver = self

    def die(self):
        drivers.log.die(self.irc)
        self.factory.stopTrying()
        self.transport.loseConnection()

    def reconnect(self, wait=None):
        # We ignore wait here, because we handled our own waiting.
        drivers.log.reconnect(self.irc.network)
        self.transport.loseConnection()

class SupyMcProtocol(Protocol):
    # From bravo server
    (STATE_UNAUTHENTICATED, STATE_CHALLENGED, STATE_AUTHENTICATED) = range(3)

    SUPPORTED_PROTOCOL = 11

    excess = ""
    packet = None

    state = STATE_UNAUTHENTICATED

    buf = ""
    parser = None
    handler = None

    player = None
    username = None

    def __init__(self):
        self.chunks = dict()
        self.windows = dict()
        self.wid = 1

        self.location = Location()

        self.handlers = {
            0: self.ping,
            1: self.login,
            2: self.handshake,
            3: self.chat,
            7: self.use,
            10: self.grounded,
            11: self.position,
            12: self.orientation,
            13: self.location_packet,
            14: self.digging,
            15: self.build,
            16: self.equip,
            18: self.animate,
            19: self.action,
            21: self.pickup,
            101: self.wclose,
            102: self.waction,
            104: self.inventory,
            106: self.wacknowledge,
            130: self.sign,
            255: self.quit,
        }


        self._ping_loop = LoopingCall(self.update_ping)

    def checkIrcForMsgs(self):
        if self.connected:
            msg = self.irc.takeMsg()
            while msg:
                if msg.command == 'PRIVMSG':
                    msg = make_packet("chat", message=msg.args[1])
                    self.transport.write(msg)
                msg = self.irc.takeMsg()
        self.mostRecentCall = reactor.callLater(0.1, self.checkIrcForMsgs)

    # Low-level packet handlers
    # Try not to hook these if possible, since they offer no convenient
    # abstractions or protections.

    def ping(self, container):
        """
        Hook for ping packets.
        """
        packet = make_packet("ping")
        self.transport.write(packet)

    def connectionMade(self):
        packet = make_packet("handshake", username='foo')
        self.transport.write(packet)

    def login(self, container):
        """
        Hook for login packets.

        Override this to customize how logins are handled. By default, this
        method will only confirm that the negotiated wire protocol is the
        correct version, and then it will run the ``authenticated()``
        callback.
        """

        container.entityId = container.protocol
        del container.protocol
        self.mostRecentCall = reactor.callLater(0.1, self.checkIrcForMsgs)
        packet = make_packet("chat", message="/login foobar")
        self.transport.write(packet)
        self._ping_loop.start(5)

    def handshake(self, container):
        """
        Hook for handshake packets.
        """
        packet = make_packet("login", protocol=11, username='ProgValbot', seed=0,
            dimension=0)
        self.transport.write(packet)

    _chat = re.compile(r'<(?P<nick>[^>]+)> (?P<message>.*)')
    def chat(self, container):
        """
        Hook for chat packets.
        """
        match = self._chat.match(container.message)
        if match is None:
            return
        else:
            msg = ircmsgs.privmsg('#minecraft',
                    match.group('message').encode('ascii', 'replace'),
                    prefix='%s!minecraft@minecraft' % str(match.group('nick')))
            self.irc.feedMsg(msg)

    def use(self, container):
        """
        Hook for use packets.
        """

    def grounded(self, container):
        """
        Hook for grounded packets.
        """

        self.location.grounded = bool(container.grounded)

    def position(self, container):
        """
        Hook for position packets.
        """

        old_position = self.location.x, self.location.y, self.location.z

        # Location represents the block the player is within
        self.location.x = int(container.position.x) if container.position.x > 0 else int(container.position.x) - 1
        self.location.y = int(container.position.y)
        self.location.z = int(container.position.z) if container.position.z > 0 else int(container.position.z) - 1
        # Stance is the current jumping position, plus a small offset of
        # around 0.1. In the Alpha server, it must between 0.1 and 1.65,
        # or the anti-grounded code kicks the client.
        self.location.stance = container.position.stance

        position = self.location.x, self.location.y, self.location.z

        self.grounded(container.grounded)

        if old_position != position:
            self.position_changed()

    def orientation(self, container):
        """
        Hook for orientation packets.
        """

        old_orientation = self.location.yaw, self.location.pitch

        self.location.yaw = container.orientation.rotation
        self.location.pitch = container.orientation.pitch

        orientation = self.location.yaw, self.location.pitch

        self.grounded(container.grounded)

        if old_orientation != orientation:
            self.orientation_changed()

    def location_packet(self, container):
        """
        Hook for location packets.
        """

        self.position(container)
        self.orientation(container)

    def digging(self, container):
        """
        Hook for digging packets.
        """

    def build(self, container):
        """
        Hook for build packets.
        """

    def equip(self, container):
        """
        Hook for equip packets.
        """

    def pickup(self, container):
        """
        Hook for pickup packets.
        """

    def animate(self, container):
        """
        Hook for animate packets.
        """

    def action(self, container):
        """
        Hook for action packets.
        """

    def wclose(self, container):
        """
        Hook for wclose packets.
        """

    def waction(self, container):
        """
        Hook for waction packets.
        """

    def inventory(self, container):
        """
        Hook for inventory packets.
        """

    def wacknowledge(self, container):
        """
        Hook for wacknowledge packets.
        """

    def sign(self, container):
        """
        Hook for sign packets.
        """

    def quit(self, container):
        """
        Hook for quit packets.

        By default, merely logs the quit message and drops the connection.

        Even if the connection is not dropped, it will be lost anyway since
        the client will close the connection. It's better to explicitly let it
        go here than to have zombie protocols.
        """

        log.info("Disconnected from server: %s" % container.message)
        self.transport.loseConnection()

    # Twisted-level data handlers and methods
    # Please don't override these needlessly, as they are pretty solid and
    # shouldn't need to be touched.

    def dataReceived(self, data):
        self.buf += data

        packets, self.buf = parse_packets(self.buf)

        for header, payload in packets:
            if header in self.handlers:
                log.debug('Packet: %i' % header)
                self.handlers[header](payload)

    def connectionLost(self, reason):
        if self._ping_loop.running:
            self._ping_loop.stop()


    # Event callbacks
    # These are meant to be overriden.

    def orientation_changed(self):
        """
        Called when the client moves.

        This callback is only for orientation, not position.
        """

        pass

    def position_changed(self):
        """
        Called when the client moves.

        This callback is only for position, not orientation.
        """

        pass

    # Convenience methods

    def update_ping(self):
        """
        Send a keepalive to the client.
        """
        packet = make_packet("ping")
        self.transport.write(packet)

    def error(self, message):
        """
        Error out.

        This method sends ``message`` to the client as a descriptive error
        message, then closes the connection.
        """

        self.transport.write(make_error_packet(message))
        self.transport.loseConnection()

def errorMsg(reason):
    return reason.getErrorMessage()

class SupyReconnectingFactory(ReconnectingClientFactory, drivers.ServersMixin):
    maxDelay = property(lambda self: conf.supybot.drivers.maxReconnectWait())
    def __init__(self, irc):
        self.irc = irc
        drivers.ServersMixin.__init__(self, irc)
        (server, port) = self._getNextServer()
        vhost = conf.supybot.protocols.irc.vhost()
        if self.networkGroup.get('ssl').value and \
                self.protocol is SupyIrcProtocol:
            self.connectSSL(server, port, vhost)
        else:
            self.connectTCP(server, port, vhost)

    def connectTCP(self, server, port, vhost):
        """Connect to the server with a standard TCP connection."""
        reactor.connectTCP(server, port, self, bindAddress=(vhost, 0))

    def connectSSL(self, server, port, vhost):
        """Connect to the server using an SSL socket."""
        drivers.log.info('Attempting an SSL connection.')
        if SSL:
            reactor.connectSSL(server, port, self,
                ssl.ClientContextFactory(), bindAddress=(vhost, 0))
        else:
            drivers.log.error('PyOpenSSL is not available. Not connecting.')

    def clientConnectionFailed(self, connector, r):
        drivers.log.connectError(self.currentServer, errorMsg(r))
        (connector.host, connector.port) = self._getNextServer()
        ReconnectingClientFactory.clientConnectionFailed(self, connector,r)

    def clientConnectionLost(self, connector, r):
        (connector.host, connector.port) = self._getNextServer()
        ReconnectingClientFactory.clientConnectionLost(self, connector, r)

    def startedConnecting(self, connector):
        drivers.log.connect(self.currentServer)

    def buildProtocol(self, addr):
        protocol = ReconnectingClientFactory.buildProtocol(self, addr)
        protocol.irc = self.irc
        return protocol

class SupyIrcReconnectingFactory(SupyReconnectingFactory):
    protocol = SupyIrcProtocol

class SupyMcReconnectingFactory(SupyReconnectingFactory):
    protocol = SupyMcProtocol

class Driver:
    def __init__(self, irc):
        if getattr(conf.supybot.networks, irc.network).minecraft():
            self = SupyMcReconnectingFactory(irc)
        else:
            self = SupyIrcReconnectingFactory(irc)

try:
    ignore(poller)
except NameError:
    poller = TwistedRunnerDriver()
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
