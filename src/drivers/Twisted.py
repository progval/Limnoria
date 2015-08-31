###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
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

from .. import conf, drivers

from twisted.names import client
from twisted.internet import reactor, error
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ReconnectingClientFactory


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

def errorMsg(reason):
    return reason.getErrorMessage()

class SupyReconnectingFactory(ReconnectingClientFactory, drivers.ServersMixin):
    maxDelay = property(lambda self: conf.supybot.drivers.maxReconnectWait())
    protocol = SupyIrcProtocol
    def __init__(self, irc):
        drivers.log.warning('Twisted driver is deprecated. You should '
                            'consider switching to Socket (set '
                            'supybot.drivers.module to Socket).')
        self.irc = irc
        drivers.ServersMixin.__init__(self, irc)
        (server, port) = self._getNextServer()
        vhost = conf.supybot.protocols.irc.vhost()
        if self.networkGroup.get('ssl').value:
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

Driver = SupyReconnectingFactory
poller = TwistedRunnerDriver()

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
